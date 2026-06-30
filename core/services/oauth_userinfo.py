"""Best-effort account-email lookup behind a freshly issued OAuth access token.

The OAuth callback uses this to populate ``OAuthConnection.public_metadata
.user_email`` so the MCP / tool connection picker can render two connections
to the same provider as distinct rows (``alice@a.com (hubspot)`` vs
``bob@b.com (hubspot)``) rather than two identical "HubSpot" entries.

Two paths are tried, in order:

1. **Provider-specific quirk** in :data:`_PROVIDER_USERINFO_QUIRKS`. Used for
   providers whose userinfo endpoints diverge from the OIDC convention —
   HubSpot today, and any future provider that needs a custom URL, a non-Bearer
   auth style, or a non-``email`` response field. Adding a new provider here
   is a single dict entry — no DB migration, no form change.

2. **Generic OIDC fetch** using the catalog's ``userinfo_url`` with a Bearer
   header, reading the top-level ``email`` field. Handles Google and every
   other provider that follows the convention.

All network and parse failures swallow to ``None``: the email is purely a UI
disambiguator, never an auth gate, so it must not be able to break the OAuth
callback.
"""

from typing import Any, Dict, Optional

import httpx


# Each entry overrides how we fetch the email for a given provider slug.
# Fields:
#   url          — endpoint to call. May contain a ``{access_token}`` placeholder
#                  when the token rides in the URL path instead of a header.
#   auth_style   — ``"bearer"`` (Authorization header) or ``"token_in_url"``
#                  (no header; token already in the URL).
#   email_field  — dot-path into the JSON response, e.g. ``"user"`` for
#                  HubSpot's token-info shape ``{"user": "a@b.com", ...}`` or
#                  ``"user.email"`` for providers that nest it one level deep.
_PROVIDER_USERINFO_QUIRKS: Dict[str, Dict[str, str]] = {
    "hubspot": {
        "url": "https://api.hubapi.com/oauth/v1/access-tokens/{access_token}",
        "auth_style": "token_in_url",
        "email_field": "user",
    },
}


def _get_dotted(payload: Any, path: str) -> Optional[str]:
    """Resolve a dot-path (``a.b.c``) against a nested dict. Returns ``None``
    for any missing segment or non-string leaf so callers can rely on the
    return type without re-checking."""
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur if isinstance(cur, str) else None


def fetch_user_email(
    provider_slug: str,
    access_token: str,
    fallback_userinfo_url: Optional[str],
) -> Optional[str]:
    """Return the account email behind ``access_token`` or ``None``.

    See the module docstring for the resolution order.
    """
    quirk = _PROVIDER_USERINFO_QUIRKS.get(provider_slug)
    if quirk:
        try:
            url = quirk["url"].format(access_token=access_token)
            headers = (
                {"Authorization": f"Bearer {access_token}"}
                if quirk.get("auth_style") == "bearer"
                else {}
            )
            with httpx.Client() as client:
                response = client.get(url, headers=headers)
                if response.status_code == 200:
                    return _get_dotted(response.json(), quirk["email_field"])
        except Exception:
            return None
        return None

    if not fallback_userinfo_url:
        return None
    try:
        with httpx.Client() as client:
            response = client.get(
                fallback_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, dict):
                    email = payload.get("email")
                    return email if isinstance(email, str) else None
    except Exception:
        return None
    return None
