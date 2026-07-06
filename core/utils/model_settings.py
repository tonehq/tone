"""Shared facts about the per-service model settings on ``AgentConfig``.

The save-path guard (``AgentService._reconcile_target_model_ids``) and the audit
(``config_audit.find_provider_model_mismatches``) are two sides of the same
concern: the audit exists to find exactly the provider/model_id mismatches the
guard is meant to prevent. They must therefore enumerate the same settings
blocks and coerce ids the same way, so both live here rather than being copied
into each module (where they could silently drift apart).
"""

from typing import Any, Optional
from uuid import UUID

# Per-service settings JSONB column on ``AgentConfig`` → the ``Model.kind`` it
# may reference.
SETTINGS_MODEL_KINDS = (
    ("llm_settings", "llm"),
    ("stt_settings", "stt"),
    ("voice_settings", "tts"),
)


def as_uuid(value: Any) -> Optional[UUID]:
    """Best-effort coerce a settings value into a ``UUID`` (``None`` on any
    non-uuid input, so callers can treat missing/garbage ids uniformly)."""
    try:
        return UUID(str(value)) if value else None
    except (ValueError, TypeError, AttributeError):
        return None
