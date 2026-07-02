"""Shared auth-type vocabulary for ``tools`` and ``mcp_servers``.

Both tables carry an ``auth_type`` string column. Keeping the canonical set in
one place means:

* frontend + backend agree on the same enum values,
* the "is this OAuth?" branch is the same rule everywhere (``auth_type == 'oauth'``),
* legacy variants (``bearer_token``, ``basic_auth``) map to their canonical form
  in exactly one place — see :func:`normalize_auth_type`.
"""

from typing import Optional


AUTH_TYPE_NONE = "none"
AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_BEARER = "bearer"
AUTH_TYPE_BASIC = "basic"
AUTH_TYPE_OAUTH = "oauth"

VALID_AUTH_TYPES = frozenset({
    AUTH_TYPE_NONE,
    AUTH_TYPE_API_KEY,
    AUTH_TYPE_BEARER,
    AUTH_TYPE_BASIC,
    AUTH_TYPE_OAUTH,
})

# Historical values still present in some rows / payloads. Kept out of
# ``VALID_AUTH_TYPES`` so new writes can't reintroduce them.
_LEGACY_ALIASES = {
    "bearer_token": AUTH_TYPE_BEARER,
    "basic_auth": AUTH_TYPE_BASIC,
}


def normalize_auth_type(value: Optional[str]) -> str:
    """Return the canonical auth-type string. ``None``/empty maps to ``'none'``."""
    if not value:
        return AUTH_TYPE_NONE
    return _LEGACY_ALIASES.get(value, value)
