"""AuthService — rewritten to match the tone-test auth schema.

Uses:
  * ``User`` (rich profile with org_id FK, password_hash, first_name, etc.)
  * ``Organization`` (subscription_tier, status, settings, …)
  * ``Member`` (organization_members analog — id, user_id, org_id, role,
    is_default, joined_at)
  * ``Invite`` (organization_invitations analog — token, expires_at,
    accepted_at, invited_by directly on the row)
  * ``EmailRequest`` (existing tone table — stores verification and
    password-reset tokens via the ``purpose`` discriminator since tone
    has no Redis cache layer like tone-test does)

Tokens stored in EmailRequest are hashed (sha256) so the raw token is
never persisted — it is only sent over the wire to the user.
"""

import logging
import secrets
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, get_args

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.config import settings
from core.middleware.auth import jwt_manager
from core.models.email_request import EmailRequest
from core.models.invite import Invite
from core.models.member import Member
from core.models.organization import Organization
from core.models.user import User
from core.services.base import BaseService
from core.services.session_service import SessionService
from core.utils.auth_helpers import coerce_uuid, hash_token, utcnow
from core.utils.device import DeviceContext
from core.utils.email_domain import assert_business_email
from core.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────

# Shared with SessionService via core.utils.auth_helpers. The legacy
# names below are kept as module-level aliases because EE imports them
# (``from core.services.auth_service import _user_uuid``).
_now = utcnow
_hash_token = hash_token
_user_uuid = coerce_uuid


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return slug[:50] or "org"


# Typed application exceptions for org-scoped writes. Kept module-local so a
# service method can signal "no org on this request" / "org row missing"
# without importing HTTP concepts. The route layer translates these to the
# appropriate HTTP status (400 / 404). See backend coding standards:
# ``.claude/skills/code-generator/backend-code-generator.md`` (service stays
# transport-agnostic).
class OrganizationContextMissingError(Exception):
    """Service method needs an org context but the caller didn't supply one."""


class OrganizationNotFoundError(Exception):
    """The org id resolved from context does not match a row in ``organizations``."""


# Upper bound for ``top_k`` — DeepEval's retrieval loop is O(top_k) per
# question, and beyond ~50 the contextual_relevancy math turns useless.
_EVAL_TOP_K_MAX = 50
# Cap ``max_context_chars`` to a value that fits comfortably in every model
# we ship with (128k-token models @ ~4 chars/token → ~500k chars). Keep the
# ceiling well below that so a typo can't OOM a worker.
_EVAL_MAX_CONTEXT_CHARS_MAX = 400_000
_EVAL_JUDGE_ENGINE_ALLOWED: frozenset[str] = frozenset({"deepeval", "legacy"})


def _validate_eval_settings_patch(
    patch: Dict[str, Any],
    *,
    supported_metrics: set,
    allowed_keys: set,
    error_cls: type,
) -> Dict[str, Any]:
    """Return a cleaned copy of ``patch`` with every value validated + typed.

    Unknown keys are rejected (typos would otherwise silently persist to
    JSONB). Every value must satisfy the same range/whitelist checks the
    resolver enforces on read — surfaced BEFORE the write so a bad value
    never lands in the DB. Raises ``error_cls`` (aliased to keep this helper
    import-cycle-free) with a clear per-field message.

    ``None`` for any field is a valid signal — the caller wants to CLEAR
    that key so the resolver falls back to env / hardcoded default. Nulls
    are passed through unchanged; the merge step deletes the key from the
    stored JSONB rather than persisting ``null``.
    """
    if not isinstance(patch, dict):
        raise error_cls("eval settings payload must be a JSON object")

    unknown = set(patch) - allowed_keys
    if unknown:
        raise error_cls(
            f"unknown eval settings key(s): {sorted(unknown)}. "
            f"Allowed: {sorted(allowed_keys)}"
        )

    cleaned: Dict[str, Any] = {}

    def _passthrough_null(key: str) -> bool:
        """Return True if the caller explicitly cleared ``key`` (patch value is
        ``None``); records the intent so the caller can delete-on-merge."""
        if key in patch and patch[key] is None:
            cleaned[key] = None
            return True
        return False

    if not _passthrough_null("auto_run_enabled") and "auto_run_enabled" in patch:
        value = patch["auto_run_enabled"]
        if not isinstance(value, bool):
            raise error_cls("auto_run_enabled must be a boolean")
        cleaned["auto_run_enabled"] = value

    for key in ("generation_model", "answer_model", "judge_model"):
        if _passthrough_null(key):
            continue
        if key in patch:
            value = patch[key]
            if not isinstance(value, str) or not value.strip():
                raise error_cls(f"{key} must be a non-empty string")
            cleaned[key] = value.strip()

    if not _passthrough_null("judge_engine") and "judge_engine" in patch:
        value = patch["judge_engine"]
        if not isinstance(value, str) or value.strip() not in _EVAL_JUDGE_ENGINE_ALLOWED:
            raise error_cls(
                f"judge_engine must be one of {sorted(_EVAL_JUDGE_ENGINE_ALLOWED)}"
            )
        cleaned["judge_engine"] = value.strip()

    if not _passthrough_null("top_k") and "top_k" in patch:
        value = patch["top_k"]
        if isinstance(value, bool) or not isinstance(value, int) or not (
            0 < value <= _EVAL_TOP_K_MAX
        ):
            raise error_cls(
                f"top_k must be an integer in (0, {_EVAL_TOP_K_MAX}]"
            )
        cleaned["top_k"] = value

    if not _passthrough_null("max_context_chars") and "max_context_chars" in patch:
        value = patch["max_context_chars"]
        if isinstance(value, bool) or not isinstance(value, int) or not (
            0 < value <= _EVAL_MAX_CONTEXT_CHARS_MAX
        ):
            raise error_cls(
                f"max_context_chars must be an integer in (0, {_EVAL_MAX_CONTEXT_CHARS_MAX}]"
            )
        cleaned["max_context_chars"] = value

    if not _passthrough_null("metric_threshold") and "metric_threshold" in patch:
        value = patch["metric_threshold"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (
            0.0 < float(value) <= 1.0
        ):
            raise error_cls("metric_threshold must be a number in (0.0, 1.0]")
        cleaned["metric_threshold"] = float(value)

    if not _passthrough_null("metrics_enabled") and "metrics_enabled" in patch:
        value = patch["metrics_enabled"]
        if not isinstance(value, list) or not value:
            raise error_cls("metrics_enabled must be a non-empty list of metric names")
        cleaned_list: list[str] = []
        for name in value:
            if not isinstance(name, str) or not name.strip():
                raise error_cls("metrics_enabled entries must be non-empty strings")
            slug = name.strip()
            if slug not in supported_metrics:
                raise error_cls(
                    f"unknown metric '{slug}'. Supported: {sorted(supported_metrics)}"
                )
            if slug not in cleaned_list:
                cleaned_list.append(slug)
        cleaned["metrics_enabled"] = cleaned_list

    if not _passthrough_null("metric_thresholds") and "metric_thresholds" in patch:
        value = patch["metric_thresholds"]
        if not isinstance(value, dict):
            raise error_cls("metric_thresholds must be an object mapping metric name → number")
        cleaned_map: Dict[str, float] = {}
        for name, threshold in value.items():
            if not isinstance(name, str) or name.strip() not in supported_metrics:
                raise error_cls(
                    f"metric_thresholds key '{name}' is not a supported metric. "
                    f"Supported: {sorted(supported_metrics)}"
                )
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not (
                0.0 < float(threshold) <= 1.0
            ):
                raise error_cls(
                    f"metric_thresholds['{name}'] must be a number in (0.0, 1.0]"
                )
            cleaned_map[name.strip()] = float(threshold)
        cleaned["metric_thresholds"] = cleaned_map

    return cleaned


# Canonical enums for the onboarding wizard. Mirrored in
# frontend/src/constants/onboarding.ts — keep the two in sync.
OnboardingUseCase = Literal[
    "customer_support",
    "sales",
    "lead_qualification",
    "appointment_booking",
    "feedback_collection",
    "other",
]

OnboardingIndustry = Literal[
    "software",
    "ecommerce",
    "healthcare",
    "financial_services",
    "real_estate",
    "education",
    "travel_hospitality",
    "insurance",
    "legal",
    "marketing",
    "manufacturing",
    "non_profit",
    "other",
]

ONBOARDING_USE_CASES: Tuple[str, ...] = get_args(OnboardingUseCase)
ONBOARDING_INDUSTRIES: Tuple[str, ...] = get_args(OnboardingIndustry)

# Roles allowed to complete onboarding — the invitee flow is separate.
_ONBOARDING_ADMIN_ROLES = frozenset({"owner", "admin"})


class AuthService(BaseService):
    def __init__(
        self,
        db: Session,
        user_id: Optional[Union[str, uuid.UUID]] = None,
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ):
        super().__init__(db, user_id, org_id=org_id)

    # ── Common helpers ───────────────────────────────────────────────

    def _get_user_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .first()
        )

    def _membership_for(
        self,
        user_id: Union[str, uuid.UUID],
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Optional[Member]:
        uid = _user_uuid(user_id)
        if not uid:
            return None
        # When an active org/tenant is supplied (e.g. the switched workspace from
        # the JWT), prefer THAT membership so /organization/me + /auth/me reflect
        # the currently-active org rather than the user's default one. This is the
        # fix for the switcher/dashboard showing the default org's data a few
        # seconds after load. Falls back to default resolution if the user is not
        # a member of the supplied org.
        if org_id:
            oid = _user_uuid(org_id)
            if oid:
                member = (
                    self.db.query(Member)
                    .filter(Member.user_id == uid, Member.organization_id == oid)
                    .first()
                )
                if member:
                    return member
        # Prefer the default membership; fall back to any membership.
        member = (
            self.db.query(Member)
            .filter(Member.user_id == uid, Member.is_default.is_(True))
            .first()
        )
        if member:
            return member
        return self.db.query(Member).filter(Member.user_id == uid).first()

    def _resolve_member_org_role(
        self,
        user: User,
        organization: Optional[Organization] = None,
    ) -> Tuple[Optional[Organization], Optional[str], Optional[str]]:
        """Return ``(org_obj, org_id_str, role)`` for a token payload."""
        member = self._membership_for(user.id)
        org_obj = organization
        if not org_obj and member:
            org_obj = (
                self.db.query(Organization)
                .filter(Organization.id == member.organization_id)
                .first()
            )
        org_id = str(org_obj.id) if org_obj else (
            str(user.organization_id) if user.organization_id else None
        )
        role = member.role if member else user.role
        return org_obj, org_id, role

    def _resolve_refresh_org_role(
        self,
        user: User,
        requested_org_id: Optional[str],
    ) -> Tuple[Optional[Organization], Optional[str], Optional[str]]:
        """Org/role for a token rotation.

        Preserves the org the incoming refresh token was minted for (e.g. the
        org the user switched into) as long as they are still a member of it —
        so a silent ``/auth/refresh`` does not revert them to their default
        org. Falls back to the default membership when the requested org is
        absent or membership has since been revoked.
        """
        if requested_org_id:
            oid = _user_uuid(requested_org_id)
            member = (
                self.db.query(Member)
                .filter(Member.user_id == user.id, Member.organization_id == oid)
                .first()
                if oid
                else None
            )
            if member:
                org_obj = (
                    self.db.query(Organization)
                    .filter(Organization.id == oid)
                    .first()
                )
                if org_obj:
                    return org_obj, str(org_obj.id), member.role
        return self._resolve_member_org_role(user)

    def _token_response(
        self,
        user: User,
        org_obj: Optional[Organization],
        role: Optional[str],
        access_token: str,
        refresh_token: str,
        email_verification_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_payload = user.to_dict()
        if role:
            user_payload["role"] = role
        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_manager.access_token_expire_seconds(),
            "user": user_payload,
            "organization": org_obj.to_dict() if org_obj else None,
            "role": role,
        }
        if email_verification_token:
            payload["email_verification_token"] = email_verification_token
        return payload

    def _build_auth_tokens(
        self,
        user: User,
        organization: Optional[Organization] = None,
        email_verification_token: Optional[str] = None,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        """Mint a fresh access+refresh pair AND record a new session row.

        Used for login / signup / accept-invite. The refresh-token flow has
        its own path (see ``refresh_tokens``) so it can rotate without
        creating a new session row.
        """
        org_obj, org_id, role = self._resolve_member_org_role(user, organization)

        session_id = uuid.uuid4()
        family = uuid.uuid4()
        access_token = jwt_manager.create_access_token(
            user_id=str(user.id),
            email=user.email,
            org_id=org_id,
            role=role,
            session_id=session_id,
        )
        refresh_token = jwt_manager.create_refresh_token(
            user_id=str(user.id),
            email=user.email,
            session_id=session_id,
            family=family,
            org_id=org_id,
        )
        SessionService(self.db).create_session(
            user_id=user.id,
            organization_id=org_obj.id if org_obj else user.organization_id,
            refresh_token=refresh_token,
            expires_at=_now() + jwt_manager.refresh_token_ttl(),
            device=device,
            session_id=session_id,
            family=family,
        )
        # Every caller commits *before* invoking this method (to persist the
        # user / membership / last_login_at update). The session row above
        # is added after those commits, so we commit again here — otherwise
        # ``get_db()`` closes the session and the row is silently dropped.
        self.db.commit()

        return self._token_response(
            user, org_obj, role, access_token, refresh_token, email_verification_token,
        )

    def ensure_default_organization(self) -> Organization:
        default_org_id = uuid.UUID(settings.DEFAULT_ORG_ID)
        org = (
            self.db.query(Organization)
            .filter(Organization.id == default_org_id)
            .first()
        )
        if org:
            return org
        org = Organization(
            id=default_org_id,
            name="Default Organization",
            slug="default",
            description="Default organization",
        )
        self.db.add(org)
        self.db.flush()
        return org

    # ── EmailRequest-backed token store ──────────────────────────────

    def _store_token(
        self,
        user: User,
        purpose: str,
        ttl: timedelta,
        template_context: Optional[Dict[str, Any]] = None,
        raw_token: Optional[str] = None,
    ) -> Tuple[EmailRequest, str]:
        # Invalidate any prior pending requests of same purpose for this email.
        self.db.query(EmailRequest).filter(
            EmailRequest.to_email == user.email,
            EmailRequest.purpose == purpose,
            EmailRequest.delivery_status == "pending",
        ).update({"delivery_status": "expired"}, synchronize_session=False)

        # Most callers want the default 32-byte URL-safe token; short
        # human-typed codes (e.g. signin codes) pass their own.
        if raw_token is None:
            raw_token = secrets.token_urlsafe(32)
        req = EmailRequest(
            organization_id=user.organization_id,
            to_email=user.email,
            user_id=user.id,
            purpose=purpose,
            template_context=template_context,
            delivery_status="pending",
            token_hash=_hash_token(raw_token),
            expires_at=_now() + ttl,
        )
        self.db.add(req)
        self.db.flush()
        return req, raw_token

    def _consume_token(self, raw_token: str, purpose: str) -> Optional[EmailRequest]:
        token_hash = _hash_token(raw_token)
        req = (
            self.db.query(EmailRequest)
            .filter(
                EmailRequest.token_hash == token_hash,
                EmailRequest.purpose == purpose,
                EmailRequest.delivery_status.in_(["pending", "sent"]),
                EmailRequest.expires_at > _now(),
            )
            .first()
        )
        if req:
            req.delivery_status = "consumed"
        return req

    def _consume_token_for_email(
        self,
        raw_token: str,
        purpose: str,
        email: str,
    ) -> Optional[EmailRequest]:
        """Variant of ``_consume_token`` scoped to an email.

        Used for short, low-entropy tokens like 6-digit sign-in codes where
        two users could plausibly hold the same value at once. Looking up
        by ``(token_hash, to_email)`` removes the cross-user collision risk.
        """
        token_hash = _hash_token(raw_token)
        req = (
            self.db.query(EmailRequest)
            .filter(
                EmailRequest.token_hash == token_hash,
                EmailRequest.purpose == purpose,
                EmailRequest.to_email == email,
                EmailRequest.delivery_status.in_(["pending", "sent"]),
                EmailRequest.expires_at > _now(),
            )
            .first()
        )
        if req:
            req.delivery_status = "consumed"
        return req

    # ── Login finalisation (shared by password + code login) ─────────

    def _finalize_login(
        self,
        user: User,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        """Update ``last_login_at`` and mint a token pair for ``user``.

        Shared by password login and code-based login so both flows behave
        identically once the user has been authenticated.
        """
        user.last_login_at = _now()
        self.db.commit()
        self.db.refresh(user)

        member = self._membership_for(user.id)
        org = (
            self.db.query(Organization)
            .filter(Organization.id == member.organization_id)
            .first()
            if member
            else None
        )
        return self._build_auth_tokens(user, org, device=device)

    # ── Signup ────────────────────────────────────────────────────────

    def signup_v2(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        organization_name: Optional[str] = None,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        assert_business_email(email)
        if self._get_user_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Every new signup gets a fresh org they own; the workspace name and
        # onboarding fields (industry, use_case) are collected in the
        # onboarding wizard via /auth/onboarding. Placeholder name used until
        # the user completes step 1 of onboarding.
        provided_name = (organization_name or "").strip()
        placeholder_name = (first_name or "").strip() + "'s Workspace" if (first_name or "").strip() else "My Workspace"
        org_display = provided_name or placeholder_name
        org_slug = _slugify(org_display) or "workspace"
        existing_slug = (
            self.db.query(Organization).filter(Organization.slug == org_slug).first()
        )
        if existing_slug:
            org_slug = f"{org_slug}-{secrets.token_hex(3)}"

        org = Organization(
            name=org_display,
            slug=org_slug,
            subscription_tier="free",
            status="active",
            onboarding_completed=False,
        )
        self.db.add(org)
        self.db.flush()
        user_role = "owner"

        user = User(
            organization_id=org.id,
            email=email,
            password_hash=hash_password(password),
            first_name=first_name or None,
            last_name=last_name or None,
            role=user_role,
            is_active=True,
            is_verified=False,
            auth_provider="local",
        )
        self.db.add(user)
        self.db.flush()

        member = Member(
            user_id=user.id,
            organization_id=org.id,
            role=user_role,
            is_default=True,
        )
        self.db.add(member)

        # Email verification token.
        _, raw_token = self._store_token(user, "verification", ttl=timedelta(hours=24))
        verification_url = f"{settings.APPLICATION_URL}/verify-email?token={raw_token}"
        try:
            from core.services.email_service import MailService
            MailService().send_signup_email(
                email, verification_url, first_name or email.split("@")[0]
            )
        except Exception:
            logger.exception("Failed to send signup verification email to %s", email)

        self.db.commit()
        self.db.refresh(user)
        return self._build_auth_tokens(
            user, org, email_verification_token=raw_token, device=device,
        )

    # ── Onboarding ───────────────────────────────────────────────────

    def complete_onboarding(
        self,
        user_id: Union[str, uuid.UUID],
        workspace_name: str,
        use_case: str,
        industry: Optional[str] = None,
        invites: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[Organization, List[str], List[Dict[str, str]]]:
        """Finish the post-signup onboarding wizard.

        Returns the updated org and the invite fan-out results as separate
        values so callers can shape the response themselves (see
        ``onboarding_response`` for the default shape). The org update
        commits before invites fire — each invite is its own transaction
        via ``invite_user_to_organization`` — so a bad email cannot roll
        back the org rename or previously-sent invites.
        """
        workspace_name = (workspace_name or "").strip()
        if not workspace_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workspace name is required",
            )
        use_case = (use_case or "").strip()
        if not use_case:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use case is required",
            )

        member = self._membership_for(user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No workspace found for user",
            )
        if member.role not in _ONBOARDING_ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners or admins can complete onboarding",
            )

        org = (
            self.db.query(Organization)
            .filter(Organization.id == member.organization_id)
            .first()
        )
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        org.name = workspace_name
        new_slug = _slugify(workspace_name)
        if new_slug != org.slug:
            clash = (
                self.db.query(Organization)
                .filter(Organization.slug == new_slug, Organization.id != org.id)
                .first()
            )
            if clash:
                new_slug = f"{new_slug}-{secrets.token_hex(3)}"
            org.slug = new_slug
        org.use_case = use_case
        org.industry = (industry or "").strip() or None
        org.onboarding_completed = True
        self.db.commit()
        self.db.refresh(org)
        logger.info(
            "[onboarding] org=%s renamed=%r use_case=%s industry=%s",
            org.id, org.name, org.use_case, org.industry,
        )

        invites_sent: List[str] = []
        invites_failed: List[Dict[str, str]] = []
        for entry in invites or []:
            email = (entry.get("email") or "").strip()
            role = (entry.get("role") or "developer").strip() or "developer"
            if not email:
                continue
            try:
                self.invite_user_to_organization(
                    email=email,
                    role=role,
                    invited_by=user_id,
                    organization_id=org.id,
                )
                invites_sent.append(email)
            except HTTPException as exc:
                invites_failed.append({"email": email, "error": exc.detail})
            except Exception as exc:
                logger.exception("Failed to invite %s during onboarding", email)
                invites_failed.append({"email": email, "error": str(exc)})

        return org, invites_sent, invites_failed

    def onboarding_response(
        self,
        org: Organization,
        invites_sent: List[str],
        invites_failed: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        return {
            "organization": org.to_dict(),
            "invites_sent": invites_sent,
            "invites_failed": invites_failed,
        }

    # ── Login / Refresh / Logout ─────────────────────────────────────

    def login_v2(
        self,
        email: str,
        password: str,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        user = self._get_user_by_email(email)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email before logging in",
            )

        return self._finalize_login(user, device=device)

    # ── Sign-in with email code (passwordless) ───────────────────────

    SIGNIN_CODE_PURPOSE = "signin_code"
    SIGNIN_CODE_TTL = timedelta(minutes=10)
    SIGNIN_CODE_LENGTH = 6

    @classmethod
    def _generate_signin_code(cls) -> str:
        """Cryptographically random numeric code, zero-padded."""
        upper = 10 ** cls.SIGNIN_CODE_LENGTH
        return f"{secrets.randbelow(upper):0{cls.SIGNIN_CODE_LENGTH}d}"

    def request_signin_code(self, email: str) -> Dict[str, str]:
        """Issue a one-time sign-in code to ``email``.

        Returns the same generic payload regardless of whether the email
        exists, the account is inactive, or the account is unverified —
        callers must not be able to enumerate users via this endpoint.
        """
        generic_response = {
            "message": "If the email exists, a sign-in code has been sent",
        }

        user = self._get_user_by_email(email)
        if not user or not user.is_active or not user.is_verified:
            return generic_response

        code = self._generate_signin_code()
        self._store_token(
            user,
            purpose=self.SIGNIN_CODE_PURPOSE,
            ttl=self.SIGNIN_CODE_TTL,
            raw_token=code,
        )

        try:
            from core.services.email_service import MailService
            display_name = user.first_name or user.email.split("@")[0]
            MailService().send_signin_code_email(user.email, code, display_name)
        except Exception:
            logger.exception("Failed to send sign-in code email to %s", email)

        self.db.commit()
        return generic_response

    def verify_signin_code(
        self,
        email: str,
        code: str,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        if not email or not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email and code are required",
            )
        # Normalise: codes are digits-only of fixed length; whitespace and
        # accidental separators (e.g. "123 456", "123-456") shouldn't fail.
        normalised = "".join(ch for ch in code if ch.isdigit())
        if len(normalised) != self.SIGNIN_CODE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired sign-in code",
            )

        req = self._consume_token_for_email(
            normalised, self.SIGNIN_CODE_PURPOSE, email,
        )
        if not req or not req.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired sign-in code",
            )

        user = self.db.query(User).filter(User.id == req.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated",
            )

        return self._finalize_login(user, device=device)

    def refresh_tokens(
        self,
        refresh_token: str,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        """Rotate the refresh token on an existing session.

        The session's ``id`` (== refresh-token ``jti``) and
        ``refresh_token_family`` are preserved across rotation; only the
        stored hash and ``last_used_at`` move forward. If the presented
        token no longer matches the stored hash, the whole family is
        revoked (``SessionService.rotate_session`` handles that).
        """
        payload = jwt_manager.decode_refresh_token(refresh_token)
        user_id = _user_uuid(payload.get("user_id"))
        session_id = _user_uuid(payload.get("jti"))
        family = _user_uuid(payload.get("family"))
        if not user_id or not session_id or not family:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Keep the org the token was minted for (e.g. after an org switch)
        # instead of always reverting to the default membership.
        org_obj, org_id, role = self._resolve_refresh_org_role(user, payload.get("org_id"))

        new_access_token = jwt_manager.create_access_token(
            user_id=str(user.id),
            email=user.email,
            org_id=org_id,
            role=role,
            session_id=session_id,
        )
        new_refresh_token = jwt_manager.create_refresh_token(
            user_id=str(user.id),
            email=user.email,
            session_id=session_id,
            family=family,
            org_id=org_id,
        )

        rotated = SessionService(self.db).rotate_session(
            session_id=session_id,
            presented_refresh_token=refresh_token,
            new_refresh_token=new_refresh_token,
            device=device,
        )
        if rotated is None:
            self.db.commit()  # persist any reuse-triggered family revocation
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is no longer valid. Please log in again.",
            )

        self.db.commit()
        return self._token_response(user, org_obj, role, new_access_token, new_refresh_token)

    def logout(
        self,
        refresh_token: Optional[str] = None,
    ) -> Dict[str, str]:
        """Revoke the session that issued ``refresh_token``.

        Idempotent: if the token is missing, malformed, expired, or its
        session was already revoked, we still return ``200`` — the client
        has already discarded the tokens locally and the user is logged
        out from their perspective. We never reveal *why* logout was a
        no-op (avoid leaking session-existence to a stolen token).
        """
        if refresh_token:
            SessionService(self.db).revoke_session_by_refresh_token(
                refresh_token, reason="user_logout",
            )
            self.db.commit()
        return {"message": "Logged out successfully"}

    # ── Email verification ───────────────────────────────────────────

    def verify_email_by_token(self, token: str) -> Dict[str, Any]:
        req = self._consume_token(token, "verification")
        if not req or not req.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )
        user = self.db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.is_verified = True
        self.db.commit()
        return {"message": "Email verified successfully", "user": user.to_dict()}

    def resend_verification_email(self, email: str) -> Dict[str, str]:
        user = self._get_user_by_email(email)
        if not user:
            # Don't disclose whether the email exists.
            return {"message": "If the email exists, a verification link has been sent"}
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )
        _, raw_token = self._store_token(user, "verification", ttl=timedelta(hours=24))
        try:
            from core.services.email_service import MailService
            url = f"{settings.APPLICATION_URL}/verify-email?token={raw_token}"
            MailService().send_signup_email(
                user.email, url, user.first_name or user.email.split("@")[0]
            )
        except Exception:
            logger.exception("Failed to send verification email to %s", email)
        self.db.commit()
        return {"message": "If the email exists, a verification link has been sent"}

    # ── Password reset & change ──────────────────────────────────────

    def request_password_reset(self, email: str) -> Dict[str, str]:
        return self.forgot_password(email)

    def forgot_password(self, email: str) -> Dict[str, str]:
        user = self._get_user_by_email(email)
        if not user:
            return {"message": "If the email exists, you will receive a password reset link"}
        _, raw_token = self._store_token(user, "reset", ttl=timedelta(hours=1))
        try:
            from core.services.email_service import MailService
            url = f"{settings.APPLICATION_URL}/reset-password?token={raw_token}"
            MailService().send_forgot_password_email(email, url)
        except Exception:
            logger.exception("Failed to send password reset email to %s", email)
        self.db.commit()
        return {"message": "If the email exists, you will receive a password reset link"}

    def reset_password_by_token(self, token: str, new_password: str) -> Dict[str, str]:
        if not new_password or len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )
        req = self._consume_token(token, "reset")
        if not req or not req.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        user = self.db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.password_hash = hash_password(new_password)
        SessionService(self.db).revoke_all_for_user(user.id, reason="password_reset")
        self.db.commit()
        return {"message": "Password reset successfully"}

    def change_password_for_user(
        self,
        user_id: Union[str, uuid.UUID],
        new_password: str,
    ) -> Dict[str, str]:
        if not new_password or len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters",
            )
        uid = _user_uuid(user_id)
        user = self.db.query(User).filter(User.id == uid).first() if uid else None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.password_hash = hash_password(new_password)
        SessionService(self.db).revoke_all_for_user(user.id, reason="password_change")
        self.db.commit()
        return {"message": "Password changed successfully"}

    # ── Invitations ──────────────────────────────────────────────────

    def invite_user_to_organization(
        self,
        email: str,
        role: str,
        invited_by: Union[str, uuid.UUID],
        organization_id: Optional[Union[str, uuid.UUID]] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert_business_email(email)
        inviter_uuid = _user_uuid(invited_by)
        if not inviter_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid inviter id",
            )
        org_uuid = _user_uuid(organization_id) if organization_id else None
        if not org_uuid:
            inviter = self.db.query(User).filter(User.id == inviter_uuid).first()
            org_uuid = inviter.organization_id if inviter else None
        if not org_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization could not be determined",
            )

        # Already a member?
        existing_member = (
            self.db.query(Member)
            .join(User, Member.user_id == User.id)
            .filter(User.email == email, Member.organization_id == org_uuid)
            .first()
        )
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

        # Reuse pending invite if one exists; otherwise create.
        existing_invite = (
            self.db.query(Invite)
            .filter(
                Invite.email == email,
                Invite.organization_id == org_uuid,
                Invite.status == "pending",
            )
            .first()
        )

        token = secrets.token_urlsafe(32)
        expires_at = _now() + timedelta(days=7)

        if existing_invite:
            existing_invite.token = token
            existing_invite.expires_at = expires_at
            existing_invite.role = role
            if name:
                existing_invite.name = name
            invite = existing_invite
        else:
            invite = Invite(
                organization_id=org_uuid,
                email=email,
                name=name,
                role=role,
                token=token,
                invited_by=inviter_uuid,
                status="pending",
                expires_at=expires_at,
            )
            self.db.add(invite)

        self.db.flush()

        invite_url = f"{settings.APPLICATION_URL}/accept-invite?token={token}"
        try:
            from core.services.email_service import MailService
            MailService().send_invite_email(email, invite_url)
        except Exception:
            logger.exception("Failed to send invite email to %s", email)

        self.db.commit()
        self.db.refresh(invite)
        return invite.to_dict()

    def validate_invitation_by_token(self, token: str) -> Dict[str, Any]:
        invite = self.db.query(Invite).filter(Invite.token == token).first()
        if not invite or not invite.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation",
            )
        existing_user = self._get_user_by_email(invite.email)
        org = (
            self.db.query(Organization)
            .filter(Organization.id == invite.organization_id)
            .first()
        )
        return {
            "valid": True,
            "email": invite.email,
            "role": invite.role,
            "organization_id": str(invite.organization_id),
            "organization_name": org.name if org else None,
            "account_exists": bool(existing_user and existing_user.password_hash),
        }

    def accept_invitation_by_token(
        self,
        token: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        current_user_id: Optional[Union[str, uuid.UUID]] = None,
        device: Optional[DeviceContext] = None,
    ) -> Dict[str, Any]:
        invite = self.db.query(Invite).filter(Invite.token == token).first()
        if not invite or not invite.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation",
            )

        org_id = invite.organization_id

        target_user: Optional[User] = None
        current_uid = _user_uuid(current_user_id)
        if current_uid:
            target_user = self.db.query(User).filter(User.id == current_uid).first()
            if target_user and target_user.email != invite.email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This invitation was sent to a different email address.",
                )

        existing_user = self._get_user_by_email(invite.email)
        if not target_user:
            target_user = existing_user

        if target_user and target_user.password_hash:
            # Existing account — just add membership.
            existing_member = (
                self.db.query(Member)
                .filter(
                    Member.user_id == target_user.id,
                    Member.organization_id == org_id,
                )
                .first()
            )
            if not existing_member:
                self.db.add(
                    Member(
                        user_id=target_user.id,
                        organization_id=org_id,
                        role=invite.role,
                        is_default=False,
                    )
                )
            invite.status = "accepted"
            invite.accepted_at = _now()
            self.db.commit()

            if current_uid == target_user.id:
                org = self.db.query(Organization).filter(Organization.id == org_id).first()
                return self._build_auth_tokens(target_user, org, device=device)
            return {
                "message": "You have been added to the organization. Please sign in to continue.",
                "account_exists": True,
                "email": invite.email,
                "requires_login": True,
            }

        # Need to create / complete an account.
        if not password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="password is required to create a new account",
            )
        password_hash = hash_password(password)
        if target_user and not target_user.password_hash:
            target_user.password_hash = password_hash
            if first_name:
                target_user.first_name = first_name
            if last_name:
                target_user.last_name = last_name
            target_user.is_verified = True
            user = target_user
        else:
            user = User(
                organization_id=org_id,
                email=invite.email,
                password_hash=password_hash,
                first_name=first_name,
                last_name=last_name,
                role=invite.role,
                is_active=True,
                is_verified=True,
                auth_provider="local",
            )
            self.db.add(user)
            self.db.flush()

        self.db.add(
            Member(
                user_id=user.id,
                organization_id=org_id,
                role=invite.role,
                is_default=True,
            )
        )
        invite.status = "accepted"
        invite.accepted_at = _now()
        self.db.commit()
        self.db.refresh(user)

        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        return self._build_auth_tokens(user, org, device=device)

    def cancel_invitation(self, invite_id: Union[str, uuid.UUID]) -> Dict[str, str]:
        uid = _user_uuid(invite_id)
        invite = self.db.query(Invite).filter(Invite.id == uid).first() if uid else None
        if not invite or invite.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending invitation not found",
            )
        self.db.delete(invite)
        self.db.commit()
        return {"message": "Invitation cancelled successfully"}

    def resend_invitation(self, invite_id: Union[str, uuid.UUID]) -> Dict[str, str]:
        uid = _user_uuid(invite_id)
        invite = self.db.query(Invite).filter(Invite.id == uid).first() if uid else None
        if not invite or invite.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending invitation not found",
            )
        invite.token = secrets.token_urlsafe(32)
        invite.expires_at = _now() + timedelta(days=7)
        self.db.commit()
        try:
            from core.services.email_service import MailService
            invite_url = f"{settings.APPLICATION_URL}/accept-invite?token={invite.token}"
            MailService().send_invite_email(invite.email, invite_url)
        except Exception:
            logger.exception("Failed to resend invite to %s", invite.email)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Couldn't send the invitation email. Please try again.",
            )
        return {"message": "Invitation re-sent successfully"}

    # ── Membership / org views ───────────────────────────────────────

    def get_user_me(self, user_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        uid = _user_uuid(user_id)
        user = self.db.query(User).filter(User.id == uid).first() if uid else None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user.to_dict()

    UPDATABLE_PROFILE_FIELDS = ("first_name", "last_name", "avatar_url")

    def update_user_me(
        self,
        user_id: Union[str, uuid.UUID],
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        uid = _user_uuid(user_id)
        user = self.db.query(User).filter(User.id == uid).first() if uid else None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        for field in self.UPDATABLE_PROFILE_FIELDS:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        self.db.commit()
        self.db.refresh(user)
        return user.to_dict()

    def get_organization_me(
        self,
        user_id: Union[str, uuid.UUID],
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Optional[Dict[str, Any]]:
        member = self._membership_for(user_id, org_id)
        if not member:
            return None
        org = (
            self.db.query(Organization)
            .filter(Organization.id == member.organization_id)
            .first()
        )
        return org.to_dict() if org else None

    def get_all_users_for_organization(
        self,
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> List[Dict[str, Any]]:
        target_org = _user_uuid(org_id) if org_id else _user_uuid(self.org_id)
        if not target_org:
            return []
        rows = (
            self.db.query(Member, User)
            .join(User, Member.user_id == User.id)
            .filter(Member.organization_id == target_org)
            .all()
        )
        result = []
        for member, user in rows:
            entry = user.to_dict()
            # The FE's OrganizationMemberApi type reads `user_id`, `username`,
            # `status`, and `member_id` — aliases for backward compatibility
            # with the pre-v2 list shape.
            entry.update(
                {
                    "member_id": str(member.id),
                    "user_id": str(user.id),
                    "username": (
                        f"{user.first_name or ''} {user.last_name or ''}".strip()
                        or user.email.split("@")[0]
                    ),
                    "status": "active" if user.is_active else "inactive",
                    "role": member.role,
                    "is_default": member.is_default,
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                }
            )
            result.append(entry)
        return result

    def get_all_invited_users_for_organization(
        self,
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> List[Dict[str, Any]]:
        target_org = _user_uuid(org_id) if org_id else _user_uuid(self.org_id)
        if not target_org:
            return []
        invites = (
            self.db.query(Invite)
            .filter(Invite.organization_id == target_org, Invite.status == "pending")
            .all()
        )
        # FE's InvitationsTable reads `member_id` from each row — alias for
        # backward compatibility with the pre-v2 list shape.
        result = []
        for i in invites:
            row = i.to_dict()
            row["member_id"] = row["id"]
            result.append(row)
        return result

    def remove_user_from_organization(
        self,
        user_id: Union[str, uuid.UUID],
        org_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Dict[str, str]:
        uid = _user_uuid(user_id)
        target_org = _user_uuid(org_id) if org_id else _user_uuid(self.org_id)
        if not uid or not target_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id and organization_id are required",
            )
        member = (
            self.db.query(Member)
            .filter(Member.user_id == uid, Member.organization_id == target_org)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found",
            )
        if member.role == "owner":
            owners = (
                self.db.query(Member)
                .filter(Member.organization_id == target_org, Member.role == "owner")
                .count()
            )
            if owners <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner",
                )
        self.db.delete(member)
        self.db.commit()
        return {"message": "Member removed successfully"}

    def update_member_role(
        self,
        member_id: Union[str, uuid.UUID],
        new_role: str,
    ) -> Dict[str, Any]:
        mid = _user_uuid(member_id)
        member = self.db.query(Member).filter(Member.id == mid).first() if mid else None
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )
        # Prevent demoting the last owner.
        if member.role == "owner" and new_role != "owner":
            owners = (
                self.db.query(Member)
                .filter(Member.organization_id == member.organization_id, Member.role == "owner")
                .count()
            )
            if owners <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change role of the last owner",
                )
        member.role = new_role
        self.db.commit()
        return {
            "member_id": str(member.id),
            "role": member.role,
            "message": "Role updated successfully",
        }

    def get_roles_by_scope(self) -> List[Dict[str, str]]:
        return [
            {"role": "owner", "description": "Full access to organization"},
            {"role": "admin", "description": "Administrative access"},
            {"role": "developer", "description": "Standard developer access"},
            {"role": "observer", "description": "Read-only access"},
        ]

    # ── Organization settings ────────────────────────────────────────

    def get_organization_settings(self) -> Dict[str, Any]:
        target_org = _user_uuid(self.org_id)
        if not target_org:
            return {}
        org = self.db.query(Organization).filter(Organization.id == target_org).first()
        return org.settings or {} if org else {}

    def update_organization_settings(
        self,
        new_settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        target_org = _user_uuid(self.org_id)
        if not target_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization context required",
            )
        org = self.db.query(Organization).filter(Organization.id == target_org).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )
        # Merge (read-modify-write) rather than replace so a partial update — e.g. saving
        # only the scheduling timezone — never clobbers other settings keys. Reassign a new
        # dict so SQLAlchemy detects the JSONB change.
        merged = {**(org.settings or {}), **(new_settings or {})}
        org.settings = merged
        self.db.commit()
        return {"message": "Settings updated successfully", "settings": merged}

    # ── Organization eval settings ───────────────────────────────────

    def get_organization_eval_settings(self) -> Dict[str, Any]:
        """Return the org's raw ``eval_settings`` JSONB (or ``{}``).

        Returns the raw stored keys — NOT the resolved fallback chain — so
        the UI can distinguish "not set" from "set to the default value".
        Callers that need resolved values use
        :func:`core.services.org_settings.get_eval_settings`.
        """
        target_org = _user_uuid(self.org_id)
        if not target_org:
            return {}
        org = self.db.query(Organization).filter(Organization.id == target_org).first()
        return org.eval_settings or {} if org else {}

    def update_organization_eval_settings(
        self,
        patch: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate ``patch`` and merge into the org's ``eval_settings`` JSONB.

        Read-modify-write semantics — a partial update never clobbers unset
        keys. Passing an empty patch (``{}``) is a no-op that returns the
        current settings. A key whose value is ``None`` is CLEARED (removed
        from the stored JSONB) so the resolver falls through to env / hardcoded
        default — that is how the UI's "revert to fallback" action is expressed.

        Raises typed application exceptions (``InvalidEvalSettingsError``,
        ``OrganizationContextMissingError``, ``OrganizationNotFoundError``)
        — never ``HTTPException``. Per backend coding standards the service
        stays transport-agnostic; the route layer translates to HTTP status.
        """
        # Local imports keep this optional path lazy — the resolver +
        # validation code is only pulled in on write, not on every hot-path
        # auth check that instantiates AuthService.
        from core.services.evals.deepeval.metric_registry import SUPPORTED_METRICS
        from core.services.evals.errors import InvalidEvalSettingsError
        from core.services.org_settings import EVAL_SETTINGS_KEYS

        target_org = _user_uuid(self.org_id)
        if not target_org:
            raise OrganizationContextMissingError(
                "Organization context required to update eval settings"
            )
        org = self.db.query(Organization).filter(Organization.id == target_org).first()
        if not org:
            raise OrganizationNotFoundError(
                f"Organization {target_org} not found"
            )

        validated = _validate_eval_settings_patch(
            patch or {},
            supported_metrics=set(SUPPORTED_METRICS.keys()),
            allowed_keys=set(EVAL_SETTINGS_KEYS),
            error_cls=InvalidEvalSettingsError,
        )

        # Merge — new dict reassignment so SQLAlchemy detects the JSONB change.
        # Keys whose validated value is None are DELETED from the merged
        # payload; that's the "revert this field to fallback" semantic the
        # frontend uses when the user clears an input.
        merged = dict(org.eval_settings or {})
        for key, value in validated.items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        org.eval_settings = merged
        self.db.commit()
        return {"message": "Eval settings updated successfully", "eval_settings": merged}

    # ── Compatibility shims for older callers ────────────────────────

    def login(self, email: str, password: str) -> Dict[str, Any]:
        return self.login_v2(email, password)

    def signup(
        self,
        email: str,
        password: str,
        username: Optional[str] = None,
        profile: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        profile = profile or {}
        first_name = profile.get("first_name") or (username or email.split("@")[0])
        last_name = profile.get("last_name") or ""
        return self.signup_v2(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            organization_name=profile.get("org_name"),
        )

    def accept_forgot_password(
        self,
        email: str,
        password: str,
        token: str,
    ) -> Dict[str, str]:
        # Legacy GET-based reset that included the email — token alone is
        # sufficient, so we ignore the email parameter.
        return self.reset_password_by_token(token, password)

    def verify_user_email(
        self,
        email: str,
        code: str,
        user_id: Union[str, uuid.UUID, int],
    ) -> Dict[str, Any]:
        # Legacy code-based verification was removed in v2; treat the
        # ``code`` parameter as the new opaque token.
        return self.verify_email_by_token(code)

    def signup_with_firebase(
        self,
        firebase_token: str,
        email: str,
        profile: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Firebase signup is not supported on the v2 auth schema",
        )

    # Access-request methods preserved as 501s so old API surface still
    # returns a recognisable error rather than a 500.
    def get_access_requests(self) -> List[Dict[str, Any]]:
        return []

    def handle_access_request(self, *args, **kwargs) -> Dict[str, str]:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Organization access requests are not supported on the v2 auth schema",
        )
