"""Business logic for the ``app_integrations`` catalog.

App integrations are the global list of third-party providers Tone supports
(e.g. Google Calendar, HubSpot, GitHub). One row per provider. Live OAuth
tokens for actual user authorizations live in ``oauth_connections`` and
reference an integration by FK.

Secrets are never persisted here. ``client_id_env_key`` /
``client_secret_env_key`` are the *names* of environment variables that hold
the credentials — the values stay in env / Infisical so they can be rotated
and audited independently of the DB.
"""

import re
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, or_

from core.models.app_integration import AppIntegration
from core.services.base import BaseService


# Allowed values for the ``auth_type`` column. Kept here (not in the model) so
# the validation error message is closer to where it's enforced and easy to
# extend without an Alembic migration. ``auth_type`` is the *single* field
# describing both the high-level flow and the credential format — there is no
# separate "credential type" column, by design (one source of truth).
_ALLOWED_AUTH_TYPES = {"oauth", "api_key", "bearer_token", "none"}

# Lowercase alphanumerics plus ``-`` and ``_``, 2–64 chars. Matches the URL-safe
# slug shape used elsewhere in the catalog (e.g. ``google_calendar``, ``hubspot``).
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,63}$")

_ALLOWED_SORT_FIELDS = {"slug", "display_name", "category", "sort_order", "created_at", "updated_at"}

# Single source of truth for which model columns the API may set on either
# create or update. Adding a new column? Append it here and both paths pick it
# up automatically — no risk of create/update drifting out of sync.
_PERSISTABLE_FIELDS: tuple = (
    "slug", "display_name", "description", "category", "icon_url",
    "auth_type", "auth_url", "token_url", "userinfo_url",
    "scopes", "extra_auth_params",
    "pkce_required",
    "is_enabled", "sort_order",
)

# Credential fields the API accepts inline. They are NEVER persisted as plain
# columns — they're encrypted into ``app_integrations.encrypted_credentials``
# via :meth:`AppIntegration.set_credentials` and stripped from the payload
# before the regular field-copy loop runs.
_CREDENTIAL_FIELDS: tuple = ("client_id", "client_secret")

# Defaults applied on insert when the caller omits a field. Kept separate from
# the model's column defaults so the API contract is explicit and stable even
# if the column defaults are ever loosened.
_CREATE_DEFAULTS: Dict[str, Any] = {
    "pkce_required": True,
    "is_enabled": True,
    "sort_order": 100,
}


class AppIntegrationService(BaseService):
    """CRUD + listing for ``app_integrations`` rows.

    The table is a global catalog (no ``organization_id``), so ``self.query``
    returns an unfiltered base query — multi-tenancy is enforced at the
    OAuth-connection layer, not here.
    """

    # ──────────────────────────────────────────────────────────────────
    # Create / Update
    # ──────────────────────────────────────────────────────────────────

    def create_app_integration(self, data: Dict[str, Any]) -> AppIntegration:
        """Insert a new integration row.

        Required: ``slug``, ``display_name``, ``auth_type``.
        Optional: every other column. Unknown keys are silently ignored.
        ``is_default`` is reserved for seeds and forced to ``False`` here.
        Credentials (``client_id`` / ``client_secret``), when supplied, are
        moved into the encrypted blob before the row is persisted.
        """
        payload = self._validated_payload(data, require_slug=True)
        self._check_duplicate_slug(payload["slug"])

        credentials = _pop_credentials(payload)
        values: Dict[str, Any] = {**_CREATE_DEFAULTS}
        for field in _PERSISTABLE_FIELDS:
            if field in payload:
                values[field] = payload[field]

        integration = AppIntegration(
            **values,
            is_default=False,
            created_by_user_id=self.user_id,
            # Explicit assignment — relying on ``OrgScopedModel``'s
            # ``default=get_current_org_id`` is unreliable because the
            # contextvar isn't always set in worker threads. The service
            # already knows the org from the JWT claims, so use that.
            organization_id=self.org_id,
        )
        if credentials:
            integration.set_credentials(credentials)
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update_app_integration(self, integration_id, data: Dict[str, Any]) -> AppIntegration:
        """Patch persistable columns on an existing integration.

        ``slug`` may change but must remain unique. ``is_default`` and
        ``created_by_user_id`` are intentionally excluded from
        :data:`_PERSISTABLE_FIELDS` so they can't be flipped via the API.
        Credentials, when supplied, are merged into the encrypted blob —
        omitting a credential field leaves the stored value untouched.
        """
        integration = self.get_app_integration(integration_id)
        payload = self._validated_payload(data, require_slug=False)

        if "slug" in payload and payload["slug"] != integration.slug:
            self._check_duplicate_slug(payload["slug"], exclude_id=integration.id)

        credentials = _pop_credentials(payload)
        for field in _PERSISTABLE_FIELDS:
            if field in payload:
                setattr(integration, field, payload[field])
        if credentials:
            integration.set_credentials(credentials)

        self.db.commit()
        self.db.refresh(integration)
        return integration

    # ──────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────

    def get_app_integration(self, integration_id) -> AppIntegration:
        """Return the integration or 404."""
        integration = self.query(AppIntegration).filter(AppIntegration.id == integration_id).first()
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="App integration not found",
            )
        return integration

    def list_app_integrations(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        auth_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        is_default: Optional[bool] = None,
        sort_by: str = "sort_order",
        sort_order: str = "asc",
        page: int = 1,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Paginated catalog listing with search + filters.

        Sort fields are validated against an allow-list so callers can't reach
        into private columns. One DB query for the rows, one ``count()`` for
        the total — no per-row queries.
        """
        q = self.query(AppIntegration)

        if search:
            term = f"%{search.strip().lower()}%"
            q = q.filter(or_(
                AppIntegration.slug.ilike(term),
                AppIntegration.display_name.ilike(term),
                AppIntegration.description.ilike(term),
            ))
        if category:
            q = q.filter(AppIntegration.category == category)
        if auth_type:
            q = q.filter(AppIntegration.auth_type == auth_type)
        if is_enabled is not None:
            q = q.filter(AppIntegration.is_enabled == bool(is_enabled))
        if is_default is not None:
            q = q.filter(AppIntegration.is_default == bool(is_default))

        sort_field = sort_by if sort_by in _ALLOWED_SORT_FIELDS else "sort_order"
        direction = desc if sort_order.lower() == "desc" else asc
        q = q.order_by(direction(getattr(AppIntegration, sort_field)), asc(AppIntegration.display_name))

        total = q.count()

        if page_size:
            page = max(int(page), 1)
            offset = (page - 1) * int(page_size)
            rows = q.offset(offset).limit(int(page_size)).all()
        else:
            page, page_size, rows = 1, total, q.all()

        return {
            "items": [self.app_integration_response(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ──────────────────────────────────────────────────────────────────
    # Delete
    # ──────────────────────────────────────────────────────────────────

    def delete_app_integration(self, integration_id) -> Dict[str, str]:
        """Hard-delete an integration.

        Tone-shipped (``is_default = true``) rows are protected — admins can
        disable them via ``is_enabled = false`` instead, which preserves the
        seed contract and any FK references from ``oauth_connections``.
        """
        integration = self.get_app_integration(integration_id)
        if integration.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default integrations cannot be deleted; disable them instead",
            )
        self.db.delete(integration)
        self.db.commit()
        return {"detail": "App integration deleted"}

    # ──────────────────────────────────────────────────────────────────
    # Response formatter
    # ──────────────────────────────────────────────────────────────────

    def app_integration_response(self, integration: AppIntegration) -> Dict[str, Any]:
        """Public, secret-free shape returned to API callers.

        ``is_configured`` is derived from the env vars referenced by the row,
        so the UI can show "Connect" only for integrations whose credentials
        are actually present in this deployment. Pure in-memory work — no DB.
        """
        return {
            "id": str(integration.id),
            "slug": integration.slug,
            "display_name": integration.display_name,
            "description": integration.description,
            "category": integration.category,
            "icon_url": integration.icon_url,
            "auth_type": integration.auth_type,
            "auth_url": integration.auth_url,
            "token_url": integration.token_url,
            "userinfo_url": integration.userinfo_url,
            "scopes": integration.scopes,
            "extra_auth_params": integration.extra_auth_params,
            # Secrets are NEVER returned. ``has_credentials`` tells the UI
            # whether the row has stored creds so it can decide between
            # "Connect" and "Configure credentials first" affordances.
            "has_credentials": integration.has_credentials(),
            "pkce_required": integration.pkce_required,
            "is_enabled": integration.is_enabled,
            "is_default": integration.is_default,
            "is_configured": integration.is_configured(),
            "sort_order": integration.sort_order,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers — validation
    # ──────────────────────────────────────────────────────────────────

    def _validated_payload(self, data: Dict[str, Any], *, require_slug: bool) -> Dict[str, Any]:
        """Normalize + validate input common to create and update.

        Returns a sanitized dict with whitespace-trimmed strings and a
        lowercased slug. Delegates per-field checks to small focused
        validators so each rule lives in exactly one place.
        """
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a JSON object",
            )

        payload = dict(data)
        _validate_slug(payload, required=require_slug)
        _validate_required_string(payload, "display_name", required=require_slug, max_len=120)
        _validate_auth_type(payload, required=require_slug)
        _validate_json_type(payload, "scopes", list, "a list of strings")
        _validate_json_type(payload, "extra_auth_params", dict, "an object")
        for cred_key in _CREDENTIAL_FIELDS:
            if cred_key in payload and payload[cred_key] is not None:
                if not isinstance(payload[cred_key], str):
                    raise _bad_request(f"{cred_key} must be a string")
        return payload

    def _check_duplicate_slug(self, slug: str, exclude_id=None) -> None:
        q = self.query(AppIntegration).filter(AppIntegration.slug == slug)
        if exclude_id is not None:
            q = q.filter(AppIntegration.id != exclude_id)
        if q.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An integration with slug '{slug}' already exists",
            )


# ─────────────────────────────────────────────────────────────────────
# Module-level helpers (pure, no DB access)
# ─────────────────────────────────────────────────────────────────────


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _validate_slug(payload: Dict[str, Any], *, required: bool) -> None:
    """Trim, lowercase, and pattern-check the slug in-place."""
    value = payload.get("slug")
    if value is None:
        if required:
            raise _bad_request("slug is required")
        return
    slug = str(value).strip().lower()
    if not _SLUG_PATTERN.match(slug):
        raise _bad_request("slug must be 2–64 chars of lowercase letters, digits, '-' or '_'")
    payload["slug"] = slug


def _validate_required_string(payload: Dict[str, Any], key: str, *, required: bool, max_len: int) -> None:
    """Trim a string field and enforce non-empty + length when present."""
    value = payload.get(key)
    if value is None:
        if required:
            raise _bad_request(f"{key} is required")
        return
    trimmed = str(value).strip()
    if not trimmed:
        raise _bad_request(f"{key} cannot be empty")
    if len(trimmed) > max_len:
        raise _bad_request(f"{key} must be at most {max_len} characters")
    payload[key] = trimmed


def _validate_auth_type(payload: Dict[str, Any], *, required: bool) -> None:
    """Normalize and constrain ``auth_type`` to the allowed set."""
    value = payload.get("auth_type")
    if value is None:
        if required:
            raise _bad_request("auth_type is required")
        return
    auth_type = str(value).strip().lower()
    if auth_type not in _ALLOWED_AUTH_TYPES:
        raise _bad_request(f"auth_type must be one of: {sorted(_ALLOWED_AUTH_TYPES)}")
    payload["auth_type"] = auth_type


def _pop_credentials(payload: Dict[str, Any]) -> Dict[str, str]:
    """Extract and remove credential fields from ``payload``.

    Returns a dict of ``{client_id, client_secret}`` containing only the keys
    the caller supplied with non-empty values. The caller hands this to
    :meth:`AppIntegration.set_credentials` which encrypts and merges.
    Mutates ``payload`` so the regular field-copy loop never sees these keys.
    """
    out: Dict[str, str] = {}
    for key in _CREDENTIAL_FIELDS:
        if key in payload:
            value = payload.pop(key)
            if isinstance(value, str) and value.strip():
                out[key] = value.strip()
    return out


def _validate_json_type(payload: Dict[str, Any], key: str, expected_type: type, human_name: str) -> None:
    """Reject obviously-wrong JSON shapes (e.g. a string passed where a list is expected)."""
    value = payload.get(key)
    if value is None or key not in payload:
        return
    if not isinstance(value, expected_type):
        raise _bad_request(f"{key} must be {human_name}")


# ``_is_configured`` was inlined here historically. It now lives as
# :meth:`AppIntegration.is_configured` so the catalog readers in
# ``oauth_providers.py`` share the same logic without an import cycle.
