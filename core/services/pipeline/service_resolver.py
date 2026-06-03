"""Resolve an agent's service configuration from the database.

All DB access for the pipeline lives here. These functions read the agent's
published config, resolve providers + models + voice, and decrypt API keys into
a JSON-serializable "service spec" shape:

    {provider_name, api_key, model_name, metadata, model_meta_data}

This is the read/decrypt half of the pipeline; the construct half is `service_factory.py`
(which turns these specs into Pipecat service instances, with no DB access).

`resolve_agent_services` produces the full Redis-cached prefetch dict (the same shape
the subprocess receives), and is the single source of truth shared by
`PipelineParams.from_agent` and `PipelineParams.serialize_for_prefetch`.

Schema note: this matches the current Tone data model — `Agent.published_config_id`
→ `AgentConfig` (with JSONB `llm_settings`/`stt_settings`/`voice_settings`), providers
via `ModelProvider.slug`, model names via `Model.name`, voices via `ModelVoice.voice_id`,
and per-provider/org keys via `ApiKey(provider_id, service_type, encrypted_key)`. (This
is the logic that previously lived in `agent_runtime_resolver`, adapted to the
resolve→build split.)
"""

import time as _time
from typing import Any, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.context import get_current_org_id
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.utils.encryption import decrypt

# Transport-specific cache key suffixes tried (in order) when no transport_type is given.
CACHE_FALLBACK_SUFFIXES = ("twilio", "telnyx", "plivo", "exotel", "none")
CACHE_TTL_SECONDS = 1800

# Settings keys that are routing/selection metadata, not provider params. They are
# preserved in the spec metadata (the factory reads voice_id/language), but callers
# that want only the free-form provider params can use this set.
_SELECTION_KEYS = {"provider_id", "model_id", "model", "voice_id", "language", "language_code"}


def _resolve_org_id(org_id):
    return org_id or get_current_org_id()


def _to_uuid(v: Any) -> Optional[UUID]:
    if v is None:
        return None
    if isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except (ValueError, TypeError, AttributeError):
        return None


def _looks_like_uuid(value: Any) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_agent_config(db: Session, agent: Any) -> Optional[AgentConfig]:
    """Get the published config for the given agent (Agent model or agent_id).

    Resolves via `Agent.published_config_id`; falls back to the agent's default/latest
    config so edit-mode previews (which may not be published yet) still work.
    """
    agent_id = agent.id if hasattr(agent, "id") else agent
    cfg = (
        db.query(AgentConfig)
        .join(Agent, Agent.published_config_id == AgentConfig.id)
        .filter(Agent.id == agent_id)
        .first()
    )
    if cfg:
        return cfg
    return (
        db.query(AgentConfig)
        .filter(AgentConfig.agent_id == agent_id)
        .order_by(AgentConfig.is_default.desc(), AgentConfig.version.desc())
        .first()
    )


def _build_spec(provider, model_name, api_key, metadata) -> Optional[dict]:
    """Assemble the {provider_name, api_key, model_name, metadata, model_meta_data} spec."""
    if not provider or not api_key:
        return None
    return {
        "provider_name": (provider.slug or "").strip().lower(),
        "api_key": api_key,
        "model_name": model_name,
        "metadata": metadata,
        "model_meta_data": {},
    }


def _resolve_specs_from_config(
    db: Session, org_id, config: AgentConfig
) -> Tuple[Optional[dict], Optional[dict], Optional[dict], bool]:
    """Resolve the llm/stt/tts service specs (+ is_s2s) from an AgentConfig.

    Reads the JSONB `llm_settings`/`stt_settings`/`voice_settings`, resolves each
    provider slug, model name, voice id, and decrypted API key, and returns three
    spec dicts (any of which may be None if not configured).
    """
    llm_settings = config.llm_settings or {}
    stt_settings = config.stt_settings or {}
    voice_settings = config.voice_settings or {}

    llm_pid = _to_uuid(llm_settings.get("provider_id"))
    stt_pid = _to_uuid(stt_settings.get("provider_id"))
    tts_pid = _to_uuid(voice_settings.get("provider_id"))
    provider_ids = {p for p in (llm_pid, stt_pid, tts_pid) if p}

    llm_mid = _to_uuid(llm_settings.get("model_id"))
    stt_model_literal = stt_settings.get("model")
    stt_mid = _to_uuid(stt_settings.get("model_id"))
    tts_mid = _to_uuid(voice_settings.get("model_id"))
    model_ids = {m for m in (llm_mid, stt_mid, tts_mid) if m}

    voice_id_raw = voice_settings.get("voice_id")
    voice_uuid = _to_uuid(voice_id_raw)

    providers = (
        db.query(ModelProvider).filter(ModelProvider.id.in_(provider_ids)).all() if provider_ids else []
    )
    provider_by_id = {p.id: p for p in providers}

    models = db.query(Model).filter(Model.id.in_(model_ids)).all() if model_ids else []
    model_by_id = {m.id: m for m in models}

    keys = (
        db.query(ApiKey)
        .filter(
            ApiKey.provider_id.in_(provider_ids),
            ApiKey.organization_id == org_id,
            ApiKey.is_active.is_(True),
        )
        .order_by(ApiKey.is_default.desc())
        .all()
        if (provider_ids and org_id)
        else []
    )
    key_by_provider_service: dict = {}
    for k in keys:
        key_by_provider_service.setdefault((k.provider_id, k.service_type), k)

    voice_row = (
        db.query(ModelVoice).filter(ModelVoice.id == voice_uuid).first() if voice_uuid else None
    )

    def _mname(mid):
        m = model_by_id.get(mid)
        return m.name if m else None

    def _key(pid, service_type):
        ak = key_by_provider_service.get((pid, service_type))
        if not ak:
            # Fallback: a key with NULL service_type covers all services for the provider.
            ak = key_by_provider_service.get((pid, None))
        if not ak:
            return None
        try:
            return decrypt(ak.encrypted_key)
        except Exception as e:
            logger.warning("[resolver] decrypt failed for api_key %s: %s", ak.id, e)
            return None

    # ── LLM ──
    llm_metadata = dict(llm_settings)
    is_s2s = bool(llm_metadata.get("is_s2s"))
    if is_s2s and config.system_prompt_template:
        llm_metadata["system_prompt"] = config.system_prompt_template
    llm_spec = _build_spec(
        provider_by_id.get(llm_pid),
        _mname(llm_mid),
        _key(llm_pid, "llm") if llm_pid else None,
        llm_metadata,
    )

    # ── STT ──
    stt_spec = _build_spec(
        provider_by_id.get(stt_pid),
        stt_model_literal or _mname(stt_mid),
        _key(stt_pid, "stt") if stt_pid else None,
        dict(stt_settings),
    )

    # ── TTS ──
    resolved_voice = (voice_row.voice_id if voice_row else None) or (
        voice_id_raw if (voice_id_raw and not _looks_like_uuid(voice_id_raw)) else None
    )
    tts_metadata = dict(voice_settings)
    tts_metadata["voice_id"] = resolved_voice
    # The factory reads metadata["language"]; prefer the language *code* (e.g. "en")
    # over the display name (e.g. "English"), which Pipecat's Language enum rejects.
    tts_language = voice_settings.get("language_code") or voice_settings.get("language")
    if tts_language:
        tts_metadata["language"] = tts_language
    tts_spec = _build_spec(
        provider_by_id.get(tts_pid),
        _mname(tts_mid),
        _key(tts_pid, "tts") if tts_pid else None,
        tts_metadata,
    )

    return llm_spec, stt_spec, tts_spec, is_s2s


def resolve_service_spec(
    db: Session, org_id, agent: Any, config: Optional[AgentConfig], service_type: str
) -> Optional[dict]:
    """Resolve one LLM/STT/TTS service spec for an agent (non-prefetched path)."""
    org_id = _resolve_org_id(org_id)
    if config is None:
        config = get_agent_config(db, agent)
    if not config:
        return None
    org_id = org_id or getattr(config, "organization_id", None) or getattr(agent, "organization_id", None)
    llm_spec, stt_spec, tts_spec, _ = _resolve_specs_from_config(db, org_id, config)
    return {"llm": llm_spec, "stt": stt_spec, "tts": tts_spec}.get(service_type)


def _resolve_telephony_creds(db: Session, org_id, transport_type: str, agent: Any) -> Optional[dict]:
    """Fetch telephony provider credentials from the org's Channel (encrypted_config).

    Channels store credentials keyed by `channel_type` ("twilio"/"telnyx"/"plivo"/"exotel")
    in an encrypted JSONB blob. Returns the decrypted config dict (e.g. account_sid/auth_token
    for Twilio) or None.
    """
    from core.models.channel import Channel
    from core.utils.encryption import decrypt_json

    q = db.query(Channel).filter(Channel.channel_type == transport_type)
    org = org_id or getattr(agent, "organization_id", None)
    if org:
        q = q.filter(Channel.organization_id == org)
    channel = q.first()
    if not channel or not channel.encrypted_config:
        return None
    try:
        return decrypt_json(channel.encrypted_config) or None
    except Exception as e:
        logger.warning("[resolver] telephony cred decrypt failed for %s: %s", transport_type, e)
        return None


def resolve_agent_services(
    db: Session, agent: Any, transport_type: str = None, org_id=None
) -> Optional[dict]:
    """Pre-fetch all data needed to build LLM/STT/TTS services into a JSON-serializable dict.

    If transport_type is provided, also fetches telephony credentials in the same DB session.
    Returns None if config or any required service is missing. Results are cached in Redis
    keyed by agent_id + transport_type.

    This is the single resolution path shared by PipelineParams.from_agent and
    PipelineParams.serialize_for_prefetch.
    """
    from core.services.redis_service import cache_get, cache_set

    org_id = _resolve_org_id(org_id)
    _t_ser = _time.monotonic()

    agent_id = agent.id if hasattr(agent, "id") else agent
    cache_key = f"agent_bot_data:{agent_id}:{transport_type or 'none'}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("[TIMING] serialize: CACHE HIT for agent_id=%s (+%.3fs)", agent_id, _time.monotonic() - _t_ser)
        return cached

    config = get_agent_config(db, agent)
    if not config or not config.system_prompt_template:
        return None

    org_id = org_id or getattr(config, "organization_id", None) or getattr(agent, "organization_id", None)

    llm_spec, stt_spec, tts_spec, is_s2s = _resolve_specs_from_config(db, org_id, config)
    if not llm_spec:
        return None
    if not is_s2s and (not stt_spec or not tts_spec):
        return None

    messages = [{"role": "system", "content": config.system_prompt_template}]
    if getattr(config, "first_message", None) and config.first_message.strip():
        messages.append({"role": "assistant", "content": config.first_message.strip()})

    result = {
        "llm": llm_spec,
        "stt": stt_spec,
        "tts": tts_spec,
        "is_s2s": is_s2s,
        "messages": messages,
        "end_call_message": getattr(config, "end_call_message", None),
    }

    if transport_type:
        telephony_creds = _resolve_telephony_creds(db, org_id, transport_type, agent)
        if telephony_creds:
            result["_telephony_creds"] = telephony_creds

    cache_set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
    logger.info(
        "[TIMING] serialize: CACHE MISS — stored in Redis for agent_id=%s (+%.3fs)",
        agent_id,
        _time.monotonic() - _t_ser,
    )
    return result


def resolve_agent_services_with_fallback(db: Session, agent: Any, org_id=None) -> Optional[dict]:
    """Resolve agent services trying transport-specific Redis cache keys first.

    Used when no transport_type is known (e.g. the in-process /ws/test + WebRTC paths).
    Falls back to a fresh resolution under the 'none' key.
    """
    from core.services.redis_service import cache_get

    agent_id = agent.id if hasattr(agent, "id") else agent
    for transport_suffix in CACHE_FALLBACK_SUFFIXES:
        cache_key = f"agent_bot_data:{agent_id}:{transport_suffix}"
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("[TIMING] using Redis-cached service data from key=%s (no DB queries)", cache_key)
            return cached
    return resolve_agent_services(db, agent, transport_type=None, org_id=org_id)
