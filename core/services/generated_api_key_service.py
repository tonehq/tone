"""GeneratedApiKeyService — customer-facing programmatic-access API keys.

CRUD + the Bearer-token auth-path resolver (``resolve_bearer_key``) that lets the
middleware treat an ``Authorization: Bearer tone_sk_...`` request as an authenticated
call from the key's org. Keys are hashed (SHA-256); plaintext is returned exactly once
on creation and is never stored.

Reuses ``BaseService`` (org scoping, ``get_or_404``) and ``apply_search_sort_pagination``
(list). Never touches the ``ApiKey`` model — that is a different resource (provider creds).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from core.models.enums import Role
from core.models.generated_api_key import GeneratedApiKey
from core.services.base import BaseService
from core.services.common.list_query import apply_search_sort_pagination


# Prefix carried by every key we mint — lets the auth path route on the shape of
# the incoming Bearer without a wasted JWT decode.
KEY_PREFIX = "tone_sk_"

# Authority ordering of the org roles a key can carry. A key can never be minted
# with a higher-ranked role than the creating user's own role, so a member can't
# escalate by issuing an admin/owner key. Kept here (rather than a shared guard)
# because API-key capping is the only place today that needs a role *ordering*
# — the route guards only need set membership.
_ROLE_RANK = {
    Role.OBSERVER.value: 0,
    Role.MEMBER.value: 1,
    Role.ADMIN.value: 2,
    Role.OWNER.value: 3,
}
VALID_API_KEY_ROLES = set(_ROLE_RANK)
# How many characters of the full key are safe to persist for display/masking.
DISPLAY_PREFIX_LEN = 12
# Coalesce ``last_used_at`` writes to at most one per interval per key so hot
# keys don't contend on a single row for every request.
LAST_USED_COALESCE_SECONDS = 60


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class GeneratedApiKeyService(BaseService):
    """Manage customer-facing API keys and resolve them on the auth path."""

    # ------------------------------------------------------------------
    # Key minting
    # ------------------------------------------------------------------

    def _generate_key(self) -> Tuple[str, str, str]:
        """Return ``(full_key, key_hash, key_prefix)``. Full key is only ever
        surfaced to the router-of-creation; nothing else should see it."""
        secret = secrets.token_urlsafe(32)
        full_key = f"{KEY_PREFIX}{secret}"
        return full_key, _hash_key(full_key), full_key[:DISPLAY_PREFIX_LEN]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _resolve_key_role(self, role: str, creator_role: Optional[str]) -> str:
        """Validate the requested key ``role`` and cap it at ``creator_role``.

        Raises 422 for an unknown role and 403 when the caller tries to mint a key
        stronger than their own role (privilege escalation). ``creator_role`` may
        be ``None`` for a legacy/unknown caller — treated as the lowest authority
        so it can only ever mint an observer key.
        """
        requested = (role or "").strip().lower()
        if requested not in _ROLE_RANK:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid role. Must be one of: {', '.join(sorted(_ROLE_RANK))}.",
            )
        creator = (creator_role or "").strip().lower()
        creator_rank = _ROLE_RANK.get(creator, min(_ROLE_RANK.values()))
        if _ROLE_RANK[requested] > creator_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot create an API key with more privileges than your own role.",
            )
        return requested

    def create_api_key(
        self,
        *,
        name: str,
        role: str,
        creator_role: Optional[str],
        expires_at: Optional[datetime] = None,
    ) -> Tuple[GeneratedApiKey, str]:
        """Mint a new key. Returns ``(orm_row, full_plaintext_key)`` — the router
        includes the plaintext in the one-time create response and drops it.

        ``role`` is the authority the minted key will carry; it is validated
        against the known roles and **capped at ``creator_role``** so a caller can
        never issue a key more powerful than themselves.
        """
        clean_name = (name or "").strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name is required.",
            )
        if len(clean_name) > 120:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must be 120 characters or fewer.",
            )
        key_role = self._resolve_key_role(role, creator_role)
        if expires_at is not None:
            # Normalize naive datetimes to UTC so the ``> utcnow()`` check below
            # is comparing apples to apples.
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Expiry must be in the future.",
                )

        full_key, key_hash, key_prefix = self._generate_key()
        row = GeneratedApiKey(
            organization_id=self.org_id,
            created_by_user_id=self.user_id,
            name=clean_name,
            role=key_role,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as exc:
            # The partial unique index rejects "another active key with the same
            # name in this org". Any other integrity failure is bubbled up as
            # the same 409 — the client only cares that the name conflicted.
            self.db.rollback()
            logger.exception("[generated-api-key] create failed for name={}", clean_name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active API key with this name already exists.",
            ) from exc
        self.db.refresh(row)
        logger.info(
            "[generated-api-key] created id={} name={} org={}",
            row.id, clean_name, self.org_id,
        )
        return row, full_key

    def list_api_keys(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Paginated org-scoped list. Excludes hard-deleted rows; revoked rows stay
        visible so users can see their revocation history."""
        query = self.query(GeneratedApiKey).filter(GeneratedApiKey.deleted_at.is_(None))
        rows, total = apply_search_sort_pagination(
            query,
            search=search,
            search_fields=[GeneratedApiKey.name, GeneratedApiKey.key_prefix],
            sort_by=sort_by,
            sort_order=sort_order,
            sort_map={
                "name": GeneratedApiKey.name,
                "created_at": GeneratedApiKey.created_at,
                "last_used_at": GeneratedApiKey.last_used_at,
                "expires_at": GeneratedApiKey.expires_at,
            },
            page_no=page_no,
            page_size=page_size,
        )
        return {
            "data": [r.to_dict() for r in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }

    def get_api_key(self, api_key_id: UUID) -> GeneratedApiKey:
        return self.get_or_404(GeneratedApiKey, api_key_id, name="API key")

    def revoke_api_key(self, api_key_id: UUID) -> GeneratedApiKey:
        """Soft-revoke — key stays visible in the UI but no longer authenticates.
        Idempotent: re-revoking an already-revoked key is a no-op."""
        row = self.get_or_404(GeneratedApiKey, api_key_id, name="API key")
        if row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            row.is_active = False
            self.db.commit()
            self.db.refresh(row)
            logger.info("[generated-api-key] revoked id={}", api_key_id)
        return row

    def delete_api_key(self, api_key_id: UUID) -> Dict[str, str]:
        """Hard delete — removes the row and frees its slot in the unique-hash
        index. After delete the same plaintext (in the unlikely event of a
        collision) could theoretically be issued again by ``token_urlsafe``."""
        row = self.get_or_404(GeneratedApiKey, api_key_id, name="API key")
        self.db.delete(row)
        self.db.commit()
        logger.info("[generated-api-key] deleted id={}", api_key_id)
        return {"message": "API key deleted."}

    # ------------------------------------------------------------------
    # Response shape (public formatter — mirrors api-conventions.md)
    # ------------------------------------------------------------------

    def api_key_response(self, row: GeneratedApiKey) -> dict:
        return row.to_dict()

    # ------------------------------------------------------------------
    # Auth-path resolver (called by middleware, no org scoping applied)
    # ------------------------------------------------------------------

    def resolve_bearer_key(self, raw_key: str) -> Optional[GeneratedApiKey]:
        """Return the row iff the key is live (active, not revoked, not expired).

        Called from ``core.middleware.auth`` — MUST NOT be org-scoped: the
        request has not yet resolved a tenant. The row's ``organization_id``
        becomes the tenant. Any invalid state → None (middleware turns that into
        401 with a consistent message)."""
        if not raw_key or not raw_key.startswith(KEY_PREFIX):
            return None
        row = (
            self.db.query(GeneratedApiKey)
            .filter(GeneratedApiKey.key_hash == _hash_key(raw_key))
            .first()
        )
        if row is None:
            return None
        if not row.is_active or row.revoked_at is not None:
            return None
        if row.deleted_at is not None:
            return None
        if row.expires_at is not None and row.expires_at <= datetime.now(timezone.utc):
            return None
        return row

    def touch_last_used(self, api_key_id: UUID) -> None:
        """Best-effort bump of ``last_used_at`` — never fails the caller.

        Coalesced to one write per key per ``LAST_USED_COALESCE_SECONDS`` to keep
        hot keys from contending on a single row. Uses a filtered UPDATE so we
        don't need to load-then-save the row."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(
                seconds=LAST_USED_COALESCE_SECONDS
            )
            self.db.query(GeneratedApiKey).filter(
                GeneratedApiKey.id == api_key_id,
                (
                    GeneratedApiKey.last_used_at.is_(None)
                    | (GeneratedApiKey.last_used_at < cutoff)
                ),
            ).update(
                {GeneratedApiKey.last_used_at: func.now()},
                synchronize_session=False,
            )
            self.db.commit()
        except Exception:
            # Best-effort — a bookkeeping failure must not break a real request.
            self.db.rollback()
            logger.exception("[generated-api-key] touch_last_used failed id={}", api_key_id)
