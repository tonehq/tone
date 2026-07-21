"""Organization ``settings`` JSONB helpers — the single source of truth for reading typed
values out of the org settings bag so a key name/default is never duplicated across callers.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

# Key in ``Organization.settings`` holding the org's default scheduling timezone (IANA name,
# e.g. "America/New_York"). Kept in sync with the frontend org settings form.
SCHEDULING_TIMEZONE_KEY = "scheduling_timezone"
DEFAULT_SCHEDULING_TIMEZONE = "UTC"


def get_scheduling_timezone(settings: Optional[Mapping[str, Any]]) -> str:
    """Return the org's default scheduling timezone (IANA), falling back to ``UTC``.

    ``settings`` is the org's ``settings`` JSONB (or ``None``). This is the ONE resolver —
    every caller that needs the org's default scheduling timezone goes through it.
    """
    value = (settings or {}).get(SCHEDULING_TIMEZONE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_SCHEDULING_TIMEZONE
