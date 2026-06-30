"""Settings-aware env-var lookup for catalog descriptors.

App integrations reference env vars by name (``client_id_env_key`` etc.).
Reading those directly via :func:`os.getenv` only finds secrets that were
loaded via ``.env`` or the process environment — it misses anything coming
from Infisical, which Tone's :data:`shared.config.settings` ingests on boot.

This helper consults :data:`settings` first (so Infisical-sourced secrets are
visible) and falls back to ``os.getenv`` for env vars that aren't declared
as Settings attributes (custom integrations added by admins).
"""

import os
from typing import Optional


def resolve_env(key: Optional[str]) -> str:
    """Return the value of an env var, looking through Tone's settings first.

    Lazy-imports :mod:`shared.config` so the module can be safely used from
    SQLAlchemy models (which are imported very early in app boot).
    """
    if not key:
        return ""
    try:
        from shared.config import settings

        value = getattr(settings, key, None)
        if value:
            return str(value)
    except Exception:
        # If settings can't be imported (e.g. during a migration), fall back
        # to a plain environment lookup so this helper stays side-effect-free.
        pass
    return os.getenv(key) or ""
