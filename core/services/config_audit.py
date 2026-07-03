"""Audit agent_configs for provider/model_id mismatches.

A settings dict like ``{"provider_id": <deepgram>, "model_id": <parakeet model>}``
is corrupt: the resolver would read the wrong model row's ``base_url`` and
silently redirect the service (staging incident 2026-07-03 — Deepgram STT
connected to the parakeet k8s URL and transcribed nothing). The save path now
prevents new mismatches (``AgentService._reconcile_target_model_ids``) and the
resolver skips base_url injection on mismatch, but rows written before those
guards may still exist in other environments. This module makes them visible:

* ``find_provider_model_mismatches(db)`` — returns the offending rows.
* ``log_provider_model_mismatches(db)`` — logs each as a warning.
* CLI: ``python -m core.services.config_audit`` — prints a report; exits 1 if
  any mismatches are found. Run it once per environment (staging/prod) as a
  post-deploy check to confirm no legacy corrupt rows remain.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent_config import AgentConfig
from core.models.model import Model
from core.models.model_provider import ModelProvider

# Per-service settings JSONB column → the Model.kind it may reference.
SETTINGS_MODEL_KINDS = (
    ("llm_settings", "llm"),
    ("stt_settings", "stt"),
    ("voice_settings", "tts"),
)


def _as_uuid(value: Any) -> Optional[UUID]:
    try:
        return UUID(str(value)) if value else None
    except (ValueError, TypeError, AttributeError):
        return None


def find_provider_model_mismatches(db: Session) -> List[Dict[str, Any]]:
    """Scan all non-deleted agent_configs for settings whose ``model_id`` points
    at a model row of a different provider than ``settings.provider_id`` (or at
    no model row at all). Returns one dict per offending settings key.
    """
    configs = (
        db.query(AgentConfig).filter(AgentConfig.deleted_at.is_(None)).all()
    )

    referenced_model_ids = set()
    for cfg in configs:
        for settings_key, _kind in SETTINGS_MODEL_KINDS:
            settings = getattr(cfg, settings_key, None) or {}
            if isinstance(settings, dict):
                mid = _as_uuid(settings.get("model_id"))
                if mid:
                    referenced_model_ids.add(mid)

    model_by_id = {}
    if referenced_model_ids:
        rows = db.query(Model).filter(Model.id.in_(referenced_model_ids)).all()
        model_by_id = {m.id: m for m in rows}

    provider_slugs = {
        p.id: p.slug for p in db.query(ModelProvider).all()
    }

    mismatches: List[Dict[str, Any]] = []
    for cfg in configs:
        for settings_key, _kind in SETTINGS_MODEL_KINDS:
            settings = getattr(cfg, settings_key, None) or {}
            if not isinstance(settings, dict):
                continue
            provider_id = _as_uuid(settings.get("provider_id"))
            model_id = _as_uuid(settings.get("model_id"))
            if not provider_id or not model_id:
                continue
            model = model_by_id.get(model_id)
            if model is not None and model.provider_id == provider_id:
                continue
            mismatches.append({
                "agent_id": str(cfg.agent_id),
                "agent_config_id": str(cfg.id),
                "version": cfg.version,
                "settings_key": settings_key,
                "provider_id": str(provider_id),
                "provider_slug": provider_slugs.get(provider_id),
                "model_id": str(model_id),
                "model_name": model.name if model else None,
                "model_provider_id": str(model.provider_id) if model else None,
                "model_provider_slug": (
                    provider_slugs.get(model.provider_id) if model else None
                ),
                "reason": "model_not_found" if model is None else "provider_mismatch",
            })
    return mismatches


def log_provider_model_mismatches(db: Session) -> int:
    """Log every provider/model_id mismatch as a warning and return the count."""
    mismatches = find_provider_model_mismatches(db)
    for m in mismatches:
        logger.warning(
            "[config-audit] agent={} config={} v{} {}: model_id={} ({}, provider={}) "
            "does not belong to provider_id={} ({}) — reason={}",
            m["agent_id"], m["agent_config_id"], m["version"], m["settings_key"],
            m["model_id"], m["model_name"], m["model_provider_slug"],
            m["provider_id"], m["provider_slug"], m["reason"],
        )
    if mismatches:
        logger.warning(
            "[config-audit] {} provider/model_id mismatch(es) found in agent_configs "
            "— these agents may connect their STT/LLM/TTS service to the wrong base_url",
            len(mismatches),
        )
    else:
        logger.info("[config-audit] no provider/model_id mismatches in agent_configs")
    return len(mismatches)


if __name__ == "__main__":
    import json
    import sys

    from core.database.session import get_db_context

    with get_db_context() as _db:
        _rows = find_provider_model_mismatches(_db)
    print(json.dumps(_rows, indent=2))
    print(f"{len(_rows)} mismatch(es) found")
    sys.exit(1 if _rows else 0)
