"""Resolve an agent's service configuration from the database.

All DB access for the pipeline lives here. These functions read the agent config,
resolve service providers + models, and decrypt API keys into a JSON-serializable
"service spec" shape:

    {provider_name, api_key, model_name, metadata, model_meta_data}

This is the read/decrypt half of the pipeline; the construct half is `service_factory.py`
(which turns these specs into Pipecat service instances, with no DB access).

`resolve_agent_services` produces the full Redis-cached prefetch dict (the same shape
the subprocess receives), and is the single source of truth shared by
`PipelineParams.from_agent` and `PipelineParams.serialize_for_prefetch`.

Moved verbatim from the old AgentFactoryService (the methods are now module functions
taking an explicit `db`/`org_id` instead of `self`).
"""

import time as _time
from typing import Any, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from core.context import get_current_org_id
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.models import Model
from core.models.service import Service
from core.models.service_provider import ServiceProvider
from core.models.voice import Voice
from core.utils.encryption import decrypt

# Transport-specific cache key suffixes tried (in order) when no transport_type is given.
CACHE_FALLBACK_SUFFIXES = ("twilio", "telnyx", "plivo", "exotel", "none")
CACHE_TTL_SECONDS = 1800


def _resolve_org_id(org_id):
    return org_id or get_current_org_id()


def get_agent_config(db: Session, agent: Any) -> Optional[AgentConfig]:
    """Get the active agent config for the given agent (Agent model or agent_id)."""
    agent_id = agent.id if hasattr(agent, "id") else agent
    return (
        db.query(AgentConfig)
        .filter(
            AgentConfig.agent_id == agent_id,
            AgentConfig.status == "active",
        )
        .first()
    )


def get_service_and_credentials(
    db: Session, org_id, service_id: Optional[int], service_type: str
) -> Optional[Tuple[Model, ServiceProvider, str]]:
    """Get the first active Model for the given service and type, plus decrypted API key.

    service_id refers to services.id (not service_providers.id).
    Returns (Model, ServiceProvider, decrypted_api_key) or None.
    """
    org_id = _resolve_org_id(org_id)
    if not service_id:
        return None

    # Look up the Service record to get service_provider_id and api_key_id
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return None

    service_provider_id = service.service_provider_id

    result = (
        db.query(Model, ServiceProvider)
        .join(ServiceProvider, Model.service_provider_id == ServiceProvider.id)
        .filter(
            Model.service_provider_id == service_provider_id,
            Model.service_type == service_type,
            Model.status == "active",
        )
        .first()
    )
    if not result:
        return None
    svc, provider = result

    # Prefer API key from Service record, then fallback to provider-level
    api_key_id = service.api_key_id
    if not api_key_id:
        q = db.query(ApiKey.id).filter(ApiKey.service_provider_id == service_provider_id)
        if org_id:
            q = q.filter(ApiKey.organization_id == org_id)
        api_key_id = q.order_by(ApiKey.id.desc()).limit(1).scalar()

    api_key_value = None
    if api_key_id:
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if api_key and api_key.api_key_encrypted:
            try:
                api_key_value = decrypt(api_key.api_key_encrypted)
            except Exception as e:
                logger.warning("Failed to decrypt API key for model %s: %s", svc.id, e)
    if not api_key_value:
        return None
    return (svc, provider, api_key_value)


def get_model_name_by_id(db: Session, model_id: Any) -> Optional[str]:
    """Look up a Model record by ID and return its name, or None if not found."""
    if model_id is None:
        return None
    try:
        model_record = db.query(Model).filter(Model.id == int(model_id)).first()
        return model_record.name if model_record else None
    except (TypeError, ValueError):
        return None


def get_model_name_from_voice(db: Session, provider_id: int, voice_id: str) -> Optional[str]:
    """Look up a Voice record by provider and voice_id, then resolve its model name.

    Used by providers like Rime and Sarvam where the model is determined by the voice.
    """
    if not voice_id:
        return None
    voice = (
        db.query(Voice)
        .filter(Voice.service_provider_id == provider_id, Voice.voice_id == voice_id)
        .first()
    )
    if not voice or not voice.model_id:
        return None
    return get_model_name_by_id(db, voice.model_id)


def resolve_service_spec(
    db: Session, org_id, agent: Any, config: AgentConfig, service_type: str
) -> Optional[dict]:
    """Resolve one LLM/STT/TTS service spec from an AgentConfig (non-prefetched path).

    Mirrors the old get_*_for_agent config branches, including the S2S system_prompt
    injection (llm) and Rime/Sarvam voice->model resolution (tts).
    """
    service_id_attr = {"llm": "llm_service_id", "stt": "stt_service_id", "tts": "tts_service_id"}[service_type]
    metadata_attr = {"llm": "llm_metadata", "stt": "stt_metadata", "tts": "tts_metadata"}[service_type]
    service_id = getattr(config, service_id_attr, None)
    if not service_id:
        return None
    result = get_service_and_credentials(db, org_id, service_id, service_type)
    if not result:
        return None
    svc, provider, api_key = result
    metadata = (getattr(config, metadata_attr, None) or {}) if hasattr(config, metadata_attr) else {}
    model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
    model = get_model_name_by_id(db, metadata.get("model_id"))
    provider_name = (provider.name or "").strip().lower()

    if service_type == "llm":
        # For S2S, inject system_prompt so the LLM builder can use it
        if metadata.get("is_s2s") and config.system_prompt:
            metadata = dict(metadata)
            metadata["system_prompt"] = config.system_prompt
    elif service_type == "tts":
        # For Rime and Sarvam, the model is determined by the voice
        if provider_name in ("rime", "sarvam") and metadata.get("voice_id"):
            voice_model = get_model_name_from_voice(db, provider.id, metadata["voice_id"])
            if voice_model:
                model = voice_model

    return {
        "provider_name": provider_name,
        "api_key": api_key,
        "model_name": model,
        "metadata": metadata,
        "model_meta_data": model_meta,
    }


def resolve_agent_services(
    db: Session, agent: Any, transport_type: str = None, org_id=None
) -> Optional[dict]:
    """Pre-fetch all data needed to build LLM/STT/TTS services into a JSON-serializable dict.

    Uses bulk queries to minimize DB round-trips. If transport_type is provided, also fetches
    telephony credentials in the same DB session. Returns None if config or any required
    service is missing. Results are cached in Redis keyed by agent_id + transport_type.

    This is the single resolution path shared by PipelineParams.from_agent and
    PipelineParams.serialize_for_prefetch.
    """
    from sqlalchemy import and_, or_

    from core.services.redis_service import cache_get, cache_set

    org_id = _resolve_org_id(org_id)
    _t_ser = _time.monotonic()

    # Check Redis cache first
    agent_id = agent.id if hasattr(agent, "id") else agent
    cache_key = f"agent_bot_data:{agent_id}:{transport_type or 'none'}"
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("[TIMING] serialize: CACHE HIT for agent_id=%s (+%.3fs)", agent_id, _time.monotonic() - _t_ser)
        return cached

    # Query 1: Get agent config
    config = get_agent_config(db, agent)
    if not config or not config.system_prompt:
        return None

    llm_metadata = (config.llm_metadata or {}) if hasattr(config, "llm_metadata") else {}
    stt_metadata = (config.stt_metadata or {}) if hasattr(config, "stt_metadata") else {}
    tts_metadata = (config.tts_metadata or {}) if hasattr(config, "tts_metadata") else {}

    # Detect S2S: check if llm_metadata flags this as a speech-to-speech model
    is_s2s = bool(llm_metadata.get("is_s2s"))

    # For S2S, inject system_prompt into llm_metadata so the LLM builder can use it
    if is_s2s and config.system_prompt:
        llm_metadata = dict(llm_metadata)  # don't mutate the original
        llm_metadata["system_prompt"] = config.system_prompt

    # Collect all service IDs (these point to services.id, not service_providers.id)
    service_id_map = {
        "llm": config.llm_service_id,
        "stt": config.stt_service_id,
        "tts": config.tts_service_id,
    }
    all_svc_ids = [sid for sid in service_id_map.values() if sid]
    # S2S only needs LLM; standard pipeline needs all 3
    if not config.llm_service_id:
        return None
    if not is_s2s and len(all_svc_ids) < 3:
        return None

    # Query 1.5: Resolve service IDs to service_provider_ids and api_key_ids
    svc_records = db.query(Service).filter(Service.id.in_(all_svc_ids)).all()
    svc_lookup = {s.id: s for s in svc_records}
    sp_id_map = {}
    svc_api_key_map = {}  # service_id -> api_key_id from Service record
    for stype, svc_id in service_id_map.items():
        if svc_id and svc_id in svc_lookup:
            sp_id_map[stype] = svc_lookup[svc_id].service_provider_id
            if svc_lookup[svc_id].api_key_id:
                svc_api_key_map[svc_id] = svc_lookup[svc_id].api_key_id
    all_sp_ids = list(set(sp_id_map.values()))

    # Collect model_ids for name resolution (needed before Q2)
    metadata_map = {"llm": llm_metadata, "stt": stt_metadata, "tts": tts_metadata}
    model_name_ids = set()
    for stype, meta in metadata_map.items():
        mid = meta.get("model_id")
        if mid is not None:
            model_name_ids.add(int(mid))

    # Query 2: Bulk fetch Models + ServiceProviders + model names (merged Q2+Q4)
    q2_conditions = [and_(Model.service_provider_id.in_(all_sp_ids), Model.status == "active")]
    if model_name_ids:
        q2_conditions.append(Model.id.in_(model_name_ids))
    rows = (
        db.query(Model, ServiceProvider)
        .join(ServiceProvider, Model.service_provider_id == ServiceProvider.id)
        .filter(or_(*q2_conditions))
        .all()
    )

    # Index by (service_provider_id, service_type) + build model_name_map from same results
    model_map = {}
    api_key_ids = set()
    model_name_map = {}
    for svc, provider in rows:
        model_name_map[svc.id] = svc.name
        key = (svc.service_provider_id, svc.service_type)
        if key not in model_map:
            model_map[key] = (svc, provider)
            # Get API key from Service record, then fallback to provider-level
            matched_svc_id = None
            for sid, s in svc_lookup.items():
                if s.service_provider_id == svc.service_provider_id:
                    matched_svc_id = sid
                    break
            svc_api_key = svc_api_key_map.get(matched_svc_id) if matched_svc_id else None
            if svc_api_key:
                api_key_ids.add(svc_api_key)
            else:
                fallback_q = db.query(ApiKey.id).filter(
                    ApiKey.service_provider_id == svc.service_provider_id,
                    ApiKey.status == "active",
                )
                if org_id:
                    fallback_q = fallback_q.filter(ApiKey.organization_id == org_id)
                fallback_key_id = fallback_q.order_by(ApiKey.id.desc()).limit(1).scalar()
                if fallback_key_id:
                    api_key_ids.add(fallback_key_id)
                    svc_api_key_map[matched_svc_id] = fallback_key_id

    # Query 3: Bulk fetch ApiKeys + telephony keys (merged Q3 + telephony creds)
    api_key_map = {}
    telephony_creds = {}

    q3_filters = []
    if api_key_ids:
        q3_filters.append(ApiKey.id.in_(api_key_ids))
    if transport_type:
        telephony_sp_subq = (
            db.query(ServiceProvider.id)
            .filter(ServiceProvider.name == transport_type)
            .scalar_subquery()
        )
        telephony_filter = ApiKey.service_provider_id == telephony_sp_subq
        if org_id:
            telephony_filter = and_(telephony_filter, ApiKey.organization_id == org_id)
        q3_filters.append(telephony_filter)

    # Try channels table first for telephony creds (org-scoped)
    if transport_type == "twilio" and hasattr(agent, "organization_id") and agent.organization_id:
        from core.models.channel import Channel
        from core.models.enums import ChannelType

        channel = (
            db.query(Channel)
            .filter(Channel.type == ChannelType.TWILIO, Channel.organization_id == agent.organization_id)
            .first()
        )
        if channel and channel.meta_data:
            meta = channel.meta_data
            account_sid = meta.get("account_sid")
            auth_token = meta.get("auth_token")
            if account_sid and auth_token:
                telephony_creds = {"account_sid": account_sid, "auth_token": auth_token}

    if q3_filters:
        all_api_keys = db.query(ApiKey).filter(or_(*q3_filters)).all()
        for ak in all_api_keys:
            if not ak.api_key_encrypted:
                continue
            try:
                decrypted = decrypt(ak.api_key_encrypted)
                if ak.id in api_key_ids:
                    api_key_map[ak.id] = decrypted
                elif not telephony_creds:
                    additional = ak.additional_credentials or {}
                    key_type = additional.get("key_type")
                    if key_type:
                        telephony_creds[key_type] = decrypted
            except Exception as e:
                logger.warning("Failed to decrypt API key %s: %s", ak.id, e)

    # Build service data dicts
    def _build_service_data(stype, metadata):
        sp_id = sp_id_map.get(stype)
        if not sp_id:
            return None
        entry = model_map.get((sp_id, stype))
        if not entry:
            return None
        svc, provider = entry
        # Look up API key from Service record (via svc_api_key_map), not Model
        svc_id = service_id_map.get(stype)
        svc_ak_id = svc_api_key_map.get(svc_id) if svc_id else None
        api_key = api_key_map.get(svc_ak_id) if svc_ak_id else None
        if not api_key:
            return None
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        mid = metadata.get("model_id")
        model_name = model_name_map.get(int(mid)) if mid is not None else None
        return {
            "provider_name": (provider.name or "").strip().lower(),
            "api_key": api_key,
            "model_name": model_name,
            "metadata": metadata,
            "model_meta_data": model_meta,
        }

    llm_data = _build_service_data("llm", llm_metadata)
    stt_data = _build_service_data("stt", stt_metadata) if config.stt_service_id else None
    tts_data = _build_service_data("tts", tts_metadata) if config.tts_service_id else None

    if not llm_data:
        return None
    if not is_s2s and (not stt_data or not tts_data):
        return None

    messages = [{"role": "system", "content": config.system_prompt}]
    if getattr(config, "first_message", None) and config.first_message.strip():
        messages.append({"role": "assistant", "content": config.first_message.strip()})

    result = {
        "llm": llm_data,
        "stt": stt_data,
        "tts": tts_data,
        "is_s2s": is_s2s,
        "messages": messages,
        "end_call_message": getattr(config, "end_call_message", None),
    }
    if telephony_creds:
        result["_telephony_creds"] = telephony_creds

    # Cache the result in Redis (TTL: 30 minutes)
    cache_set(cache_key, result, ttl_seconds=CACHE_TTL_SECONDS)
    logger.info("[TIMING] serialize: CACHE MISS — stored in Redis for agent_id=%s (+%.3fs)", agent_id, _time.monotonic() - _t_ser)

    return result


def resolve_agent_services_with_fallback(db: Session, agent: Any, org_id=None) -> Optional[dict]:
    """Resolve agent services trying transport-specific Redis cache keys first.

    Used when no transport_type is known (e.g. the in-process /ws/test + WebRTC paths).
    Mirrors the old get_agent_bot_data cache read-back loop, then falls back to a fresh
    resolution under the 'none' key.
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
