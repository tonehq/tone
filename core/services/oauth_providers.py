"""OAuth provider catalog — the single source of truth for supported integrations.

Each entry is a *descriptor* the authorize/callback/refresh flows read at runtime. Adding a new
product is a config change here (plus client credentials in settings), not a code change in the
flow. Secrets (client_id/client_secret) are resolved lazily from ``settings`` so importing this
module never requires them to be present; a provider whose credentials are missing is simply
reported as ``configured: false`` in the public catalog and cannot be authorized.

Descriptor fields:
  - ``slug``            : stable identifier used everywhere (DB ``provider_slug``, URLs)
  - ``display_name``    : human label
  - ``description``     : one-line catalog blurb
  - ``category``        : grouping for the UI ("google" | "productivity" | "dev_crm")
  - ``auth_type``       : always "oauth" here (api_key/bearer providers live elsewhere)
  - ``auth_url`` / ``token_url`` / ``userinfo_url`` (optional)
  - ``scopes``          : LIST of scope strings the authorize request asks for
  - ``scope_delimiter`` : how scopes are joined in the request (Google=" ", Linear=",")
  - ``use_pkce``        : whether the authorize/token exchange uses PKCE (S256)
  - ``token_auth``      : "body" (client creds in form body) | "basic" (HTTP Basic header)
  - ``extra_authorize_params`` : provider-specific query params (e.g. Notion ``owner=user``)
  - ``client_id`` / ``client_secret`` : zero-arg lambdas resolving from ``settings``
"""

from typing import Any, Dict, List, Optional

from core.config import settings

# Grouping labels for the catalog UI.
CATEGORY_GOOGLE = "google"
CATEGORY_PRODUCTIVITY = "productivity"
CATEGORY_DEV_CRM = "dev_crm"

_GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v2/userinfo"

OAUTH_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "google_calendar": {
        "display_name": "Google Calendar",
        "description": "Create events, check availability, and manage schedules from voice calls.",
        "category": CATEGORY_GOOGLE,
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": _GOOGLE_USERINFO,
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        # offline access + forced consent so Google returns a refresh token.
        "extra_authorize_params": {"access_type": "offline", "prompt": "consent"},
        "client_id": lambda: settings.GOOGLE_CLIENT_ID,
        "client_secret": lambda: settings.GOOGLE_CLIENT_SECRET,
    },
    "google_sheets": {
        "display_name": "Google Sheets",
        "description": "Read and write spreadsheet data during conversations.",
        "category": CATEGORY_GOOGLE,
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": _GOOGLE_USERINFO,
        "scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        "extra_authorize_params": {"access_type": "offline", "prompt": "consent"},
        "client_id": lambda: settings.GOOGLE_CLIENT_ID,
        "client_secret": lambda: settings.GOOGLE_CLIENT_SECRET,
    },
}

# Maps a built-in tool_type to the OAuth provider whose scopes it requires. Backend mirror of the
# frontend ``TOOL_TYPE_OAUTH_PROVIDER`` map; used for scope validation when a tool is configured.
TOOL_TYPE_TO_PROVIDER: Dict[str, str] = {
    "google_calendar": "google_calendar",
    "google_sheets": "google_sheets",
}

# Defaults applied to any descriptor field a provider omits.
_DEFAULTS: Dict[str, Any] = {
    "auth_type": "oauth",
    "userinfo_url": None,
    "scopes": [],
    "scope_delimiter": " ",
    "use_pkce": False,
    "token_auth": "body",
    "extra_authorize_params": {},
}


def _raw(provider: str) -> Optional[Dict[str, Any]]:
    return OAUTH_PROVIDERS.get(provider)


def get_provider_config(provider: str) -> Optional[Dict[str, Any]]:
    """Return a fully-resolved provider config (with secrets), or ``None`` if unknown.

    Secrets are resolved here; callers must treat the result as sensitive and never expose it.
    """
    raw = _raw(provider)
    if not raw:
        return None
    return {
        "slug": provider,
        "display_name": raw.get("display_name", provider.replace("_", " ").title()),
        "description": raw.get("description", ""),
        "category": raw.get("category", CATEGORY_PRODUCTIVITY),
        "auth_type": raw.get("auth_type", _DEFAULTS["auth_type"]),
        "auth_url": raw["auth_url"],
        "token_url": raw["token_url"],
        "userinfo_url": raw.get("userinfo_url", _DEFAULTS["userinfo_url"]),
        "scopes": list(raw.get("scopes", _DEFAULTS["scopes"])),
        "scope_delimiter": raw.get("scope_delimiter", _DEFAULTS["scope_delimiter"]),
        "use_pkce": raw.get("use_pkce", _DEFAULTS["use_pkce"]),
        "token_auth": raw.get("token_auth", _DEFAULTS["token_auth"]),
        "extra_authorize_params": dict(raw.get("extra_authorize_params", {})),
        "client_id": raw["client_id"](),
        "client_secret": raw["client_secret"](),
    }


def get_provider_scopes(provider: str) -> List[str]:
    """Return the scope list a provider declares (empty list if unknown or scopeless)."""
    raw = _raw(provider)
    if not raw:
        return []
    return list(raw.get("scopes", []))


def is_configured(provider: str) -> bool:
    """A provider is configured iff its client credentials are present in settings."""
    raw = _raw(provider)
    if not raw:
        return False
    try:
        return bool(raw["client_id"]() and raw["client_secret"]())
    except Exception:
        return False


def get_supported_providers() -> List[str]:
    return list(OAUTH_PROVIDERS.keys())


def get_catalog() -> List[Dict[str, Any]]:
    """Public, secret-free catalog for the frontend integrations grid."""
    catalog: List[Dict[str, Any]] = []
    for slug, raw in OAUTH_PROVIDERS.items():
        catalog.append(
            {
                "slug": slug,
                "display_name": raw.get("display_name", slug.replace("_", " ").title()),
                "description": raw.get("description", ""),
                "category": raw.get("category", CATEGORY_PRODUCTIVITY),
                "auth_type": raw.get("auth_type", _DEFAULTS["auth_type"]),
                "scopes": list(raw.get("scopes", [])),
                "configured": is_configured(slug),
            }
        )
    return catalog


def provider_for_tool_type(tool_type: Optional[str]) -> Optional[str]:
    """Resolve the OAuth provider slug whose scopes a built-in tool_type requires."""
    if not tool_type:
        return None
    return TOOL_TYPE_TO_PROVIDER.get(tool_type)
