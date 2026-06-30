"""OAuth provider catalog — DB-backed.

Provider descriptors live in the ``app_integrations`` table. These helpers read
from that table (org-scoped) and produce the same dict shapes the rest of the
OAuth code already expects, so callers only had to gain ``db`` + ``org_id``
arguments — no further changes.

Secrets are resolved lazily from env vars referenced by the row's
``client_id_env_key`` / ``client_secret_env_key`` columns, mirroring the
behaviour of the previous hardcoded catalog.

All descriptors come from the ``app_integrations`` table — see
``dev/seed_app_integrations.py`` for the seed shape and
``core/models/app_integration.py`` for the column model.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.models.app_integration import AppIntegration

# Grouping labels for the catalog UI. Kept here (constants only) so frontend-
# adjacent code doesn't have to import a model just to namespace categories.
CATEGORY_GOOGLE = "google"
CATEGORY_PRODUCTIVITY = "productivity"
CATEGORY_DEV_CRM = "dev_crm"

# Maps a built-in tool_type to the OAuth provider whose scopes it requires.
# This is a code-level association (built-in tools are defined in code, not
# in the DB) so the map stays static — it's not catalog data.
TOOL_TYPE_TO_PROVIDER: Dict[str, str] = {
    "google_calendar": "google_calendar",
    "google_sheets": "google_sheets",
}


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────


def _row_by_slug(db: Session, org_id, slug: str) -> Optional[AppIntegration]:
    """Fetch the ``app_integrations`` row for ``(org, slug)`` or ``None``."""
    return (
        db.query(AppIntegration)
        .filter(
            AppIntegration.organization_id == org_id,
            AppIntegration.slug == slug,
        )
        .first()
    )


def _row_to_config(row: AppIntegration) -> Dict[str, Any]:
    """Project a row into the dict shape OAuth flows expect.

    Secrets (``client_id`` / ``client_secret``) come from the row's
    encrypted blob — see :meth:`AppIntegration.credentials`. Fields that
    aren't yet modelled as columns (``userinfo_url``, ``scope_delimiter``,
    ``token_auth``) fall back to sane defaults; they can be promoted to
    columns later without breaking callers.
    """
    creds = row.credentials()
    return {
        "slug": row.slug,
        "display_name": row.display_name,
        "description": row.description or "",
        "category": row.category or CATEGORY_PRODUCTIVITY,
        "auth_type": row.auth_type,
        "auth_url": row.auth_url,
        "token_url": row.token_url,
        "userinfo_url": row.userinfo_url,
        "scopes": list(row.scopes or []),
        "scope_delimiter": " ",
        "use_pkce": bool(row.pkce_required),
        "token_auth": "body",
        "extra_authorize_params": dict(row.extra_auth_params or {}),
        "client_id": creds.get("client_id"),
        "client_secret": creds.get("client_secret"),
    }


# ──────────────────────────────────────────────────────────────────────
# Public lookups (all take db + org_id)
# ──────────────────────────────────────────────────────────────────────


def get_provider_config(db: Session, org_id, provider: str) -> Optional[Dict[str, Any]]:
    """Return a fully-resolved provider config (with secrets), or ``None``."""
    row = _row_by_slug(db, org_id, provider)
    return _row_to_config(row) if row else None


def get_provider_scopes(db: Session, org_id, provider: str) -> List[str]:
    """Return the scope list a provider declares (empty if unknown)."""
    row = _row_by_slug(db, org_id, provider)
    return list(row.scopes or []) if row else []


def is_configured(db: Session, org_id, provider: str) -> bool:
    """A provider is configured iff its referenced env vars are set.

    Delegates to :meth:`AppIntegration.is_configured` so the env-var rules
    live in exactly one place.
    """
    row = _row_by_slug(db, org_id, provider)
    return bool(row and row.is_configured())


def get_supported_providers(db: Session, org_id) -> List[str]:
    """Slugs of every enabled provider in the org's catalog."""
    rows = (
        db.query(AppIntegration)
        .filter(
            AppIntegration.organization_id == org_id,
            AppIntegration.is_enabled.is_(True),
        )
        .order_by(AppIntegration.sort_order, AppIntegration.display_name)
        .all()
    )
    return [r.slug for r in rows]


def get_catalog(db: Session, org_id) -> List[Dict[str, Any]]:
    """Public, secret-free catalog for the frontend integrations grid."""
    rows = (
        db.query(AppIntegration)
        .filter(
            AppIntegration.organization_id == org_id,
            AppIntegration.is_enabled.is_(True),
        )
        .order_by(AppIntegration.sort_order, AppIntegration.display_name)
        .all()
    )
    return [
        {
            # ``id`` + ``is_default`` are surfaced so the integrations grid can
            # route to the edit page and decide whether the Delete option is
            # available (default rows are seed-managed and protected).
            "id": str(r.id),
            "is_default": bool(r.is_default),
            "slug": r.slug,
            "display_name": r.display_name,
            "description": r.description or "",
            "category": r.category or CATEGORY_PRODUCTIVITY,
            "auth_type": r.auth_type,
            "scopes": list(r.scopes or []),
            "configured": r.is_configured(),
        }
        for r in rows
    ]


def provider_for_tool_type(tool_type: Optional[str]) -> Optional[str]:
    """Resolve the OAuth provider slug whose scopes a built-in tool_type
    requires. Static map — not catalog data."""
    if not tool_type:
        return None
    return TOOL_TYPE_TO_PROVIDER.get(tool_type)


# Source of truth for these descriptors now lives in
# ``dev/seed_app_integrations.py`` (seeded into ``app_integrations``). The
# previous hardcoded ``OAUTH_PROVIDERS`` dict was removed once the DB-backed
# lookups above became the only readers.
