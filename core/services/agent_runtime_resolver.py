from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.models.phone_number import PhoneNumber
from core.services.pipeline_builders.base import BuildContext
from core.services.pipeline_builders.llm_builders import LLM_BUILDERS
from core.services.pipeline_builders.stt_builders import STT_BUILDERS
from core.services.pipeline_builders.tts_builders import HTTP_TTS_PROVIDERS, TTS_BUILDERS
from core.utils.encryption import decrypt


def _looks_like_uuid(value: Any) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _to_uuid(v: Any) -> Optional[UUID]:
    if v is None:
        return None
    if isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except (ValueError, TypeError, AttributeError):
        return None


def resolve_agent_runtime(to_number: str) -> Optional[Dict[str, Any]]:
    if not to_number:
        return None

    with get_db_context() as db:
        row = (
            db.query(PhoneNumber, Agent, AgentConfig)
            .join(Agent, PhoneNumber.agent_id == Agent.id)
            .join(AgentConfig, Agent.published_config_id == AgentConfig.id)
            .filter(PhoneNumber.number == to_number)
            .first()
        )
        if not row:
            logger.info(f"[resolver] no phone_number→agent→config chain for to_number={to_number}")
            return None
        pn, agent, ac = row

        org_id = agent.organization_id

        llm_settings = ac.llm_settings or {}
        stt_settings = ac.stt_settings or {}
        voice_settings = ac.voice_settings or {}

        llm_provider_id = _to_uuid(llm_settings.get("provider_id"))
        stt_provider_id = _to_uuid(stt_settings.get("provider_id"))
        tts_provider_id = _to_uuid(voice_settings.get("provider_id"))
        provider_ids = {p for p in (llm_provider_id, stt_provider_id, tts_provider_id) if p}

        llm_model_id = _to_uuid(llm_settings.get("model_id"))
        stt_model_literal = stt_settings.get("model")
        stt_model_id = _to_uuid(stt_settings.get("model_id"))
        tts_model_id = _to_uuid(voice_settings.get("model_id"))
        model_ids = {m for m in (llm_model_id, stt_model_id, tts_model_id) if m}

        voice_id_raw = voice_settings.get("voice_id")
        voice_uuid = _to_uuid(voice_id_raw)

        providers = (
            db.query(ModelProvider).filter(ModelProvider.id.in_(provider_ids)).all()
            if provider_ids
            else []
        )
        provider_by_id = {p.id: p for p in providers}

        models = (
            db.query(Model).filter(Model.id.in_(model_ids)).all()
            if model_ids
            else []
        )
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
            if provider_ids
            else []
        )
        key_by_provider_service: Dict = {}
        for k in keys:
            key_by_provider_service.setdefault((k.provider_id, k.service_type), k)

        voice_row = (
            db.query(ModelVoice).filter(ModelVoice.id == voice_uuid).first()
            if voice_uuid
            else None
        )

        def _slug(pid):
            p = provider_by_id.get(pid)
            return p.slug if p else None

        def _mname(mid):
            m = model_by_id.get(mid)
            return m.name if m else None

        def _key(pid, service_type):
            ak = key_by_provider_service.get((pid, service_type))
            if not ak:
                # Fallback: use key with NULL service_type for this provider
                ak = key_by_provider_service.get((pid, None))
            if not ak:
                return None
            try:
                return decrypt(ak.encrypted_key)
            except Exception as e:
                logger.warning(f"[resolver] decrypt failed for api_key {ak.id}: {e}")
                return None

        llm_slug = _slug(llm_provider_id)
        stt_slug = _slug(stt_provider_id)
        tts_slug = _slug(tts_provider_id)

        llm_model = _mname(llm_model_id)
        stt_model = stt_model_literal or _mname(stt_model_id)
        tts_model = _mname(tts_model_id)

        llm_key = _key(llm_provider_id, "llm") if llm_slug else None
        stt_key = _key(stt_provider_id, "stt") if stt_slug else None
        tts_key = _key(tts_provider_id, "tts") if tts_slug else None

        voice_id = (voice_row.voice_id if voice_row else None) or (
            voice_id_raw if voice_id_raw and not _looks_like_uuid(voice_id_raw) else None
        )

        # Use pipeline builders to construct services — they handle all
        # meta_data_schema params via build_input_params automatically.
        def _build(builders, slug, api_key, model, metadata, **extra):
            if not slug or not api_key:
                return None
            builder = builders.get(slug)
            if not builder:
                logger.warning(f"[resolver] unsupported provider slug: {slug}")
                return None
            ctx = BuildContext(
                provider_name=slug,
                api_key=api_key,
                model=model,
                metadata=dict(metadata),
                model_meta={},
                **extra,
            )
            try:
                return builder.build(ctx)
            except Exception as e:
                logger.exception(f"[resolver] failed to build {slug}: {e}")
                return None

        # Filter settings to only include params the model actually supports.
        # This prevents stale params (e.g. temperature saved for GPT-4o)
        # from being sent to a model that rejects them (e.g. GPT-5).
        _structural = {"provider_id", "model_id", "model", "voice_id",
                        "language", "language_code", "is_s2s",
                        "system_prompt", "system_instruction", "base_url"}

        def _filter_by_model_schema(settings: dict, model_id) -> dict:
            m = model_by_id.get(model_id) if model_id else None
            if not m or not m.meta_data_schema:
                return dict(settings)
            allowed = {f["name"] for f in m.meta_data_schema if "name" in f} | _structural
            return {k: v for k, v in settings.items() if k in allowed}

        # For S2S, inject system_prompt into llm metadata
        llm_metadata = _filter_by_model_schema(llm_settings, llm_model_id)
        if llm_metadata.get("is_s2s") and ac.system_prompt_template:
            llm_metadata["system_prompt"] = ac.system_prompt_template

        # Debug: log the raw settings from AgentConfig so we can verify
        # meta_data_schema values are being passed to the pipeline builders.
        _exclude = {"provider_id", "model_id", "model", "voice_id", "language", "language_code"}
        llm_params = {k: v for k, v in llm_metadata.items() if k not in _exclude and v is not None}
        stt_params = {k: v for k, v in stt_settings.items() if k not in _exclude and v is not None}
        tts_params = {k: v for k, v in voice_settings.items() if k not in _exclude and v is not None}
        logger.info(
            f"[resolver] agent={agent.id} settings from AgentConfig:\n"
            f"  llm_settings  (slug={llm_slug}, model={llm_model}): {llm_params}\n"
            f"  stt_settings  (slug={stt_slug}, model={stt_model}): {stt_params}\n"
            f"  voice_settings(slug={tts_slug}, model={tts_model}, voice={voice_id}): {tts_params}"
        )

        llm = _build(LLM_BUILDERS, llm_slug, llm_key, llm_model, llm_metadata)
        stt = _build(STT_BUILDERS, stt_slug, stt_key, stt_model, stt_settings)

        import aiohttp
        tts_session = aiohttp.ClientSession() if tts_slug in HTTP_TTS_PROVIDERS else None
        tts_language = voice_settings.get("language_code") or voice_settings.get("language")
        # Strip language/language_code from TTS metadata — they contain display
        # names ("English") that fail Pipecat's Language enum. The correct code
        # is passed via BuildContext.language → voice_kwargs in each builder.
        tts_metadata = {k: v for k, v in voice_settings.items() if k not in ("language", "language_code")}
        tts = _build(
            TTS_BUILDERS, tts_slug, tts_key, tts_model, tts_metadata,
            voice_id=voice_id, language=tts_language, session=tts_session,
        )

        if not (llm and stt and tts):
            logger.warning(
                f"[resolver] partial config for agent={agent.id}: "
                f"llm={'ok' if llm else 'MISSING'} (slug={llm_slug}), "
                f"stt={'ok' if stt else 'MISSING'} (slug={stt_slug}), "
                f"tts={'ok' if tts else 'MISSING'} (slug={tts_slug})"
            )
            return None

        logger.info(
            f"[resolver] resolved agent {agent.id} runtime: "
            f"llm={llm_slug}/{llm_model}, stt={stt_slug}/{stt_model}, "
            f"tts={tts_slug}/{tts_model} voice_id={voice_id}"
        )

        return {
            "llm": llm,
            "stt": stt,
            "tts": tts,
            "system_prompt": ac.system_prompt_template or "You are a helpful assistant.",
            "first_message": ac.first_message,
            "end_call_message": ac.end_call_message,
            "agent": agent,
            "agent_config": ac,
        }
