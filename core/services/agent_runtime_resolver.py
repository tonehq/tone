from typing import Any, Dict, Optional
from uuid import UUID

import aiohttp
from deepgram import LiveOptions
from loguru import logger
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.assemblyai.stt import AssemblyAISTTService
from pipecat.services.cartesia.stt import CartesiaSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramHttpTTSService
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.gladia.stt import GladiaSTTService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.stt import GroqSTTService
from pipecat.services.nvidia.stt import NvidiaSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.rime.tts import RimeHttpTTSService
from pipecat.services.soniox.stt import SonioxSTTService
from pipecat.services.speechmatics.stt import SpeechmaticsSTTService
from sqlalchemy.orm import Session

from core.database.session import get_db_context
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.models.phone_number import PhoneNumber
from core.utils.encryption import decrypt


def _model_name(db: Session, model_id: Any) -> Optional[str]:
    if not model_id:
        return None
    m = db.query(Model).filter(Model.id == model_id).first()
    return m.name if m else None


def _provider_slug(db: Session, provider_id: Any) -> Optional[str]:
    if not provider_id:
        return None
    p = db.query(ModelProvider).filter(ModelProvider.id == provider_id).first()
    return p.slug if p else None


def _voice_name(db: Session, voice_id: Any) -> Optional[str]:
    if not voice_id:
        return None
    v = db.query(ModelVoice).filter(ModelVoice.id == voice_id).first()
    if v:
        return v.name
    return None


def _looks_like_uuid(value: Any) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def _api_key(db: Session, provider_id: Any, service_type: str, org_id: Any) -> Optional[str]:
    if not provider_id:
        return None
    ak = (
        db.query(ApiKey)
        .filter(
            ApiKey.provider_id == provider_id,
            ApiKey.service_type == service_type,
            ApiKey.organization_id == org_id,
            ApiKey.is_active.is_(True),
        )
        .order_by(ApiKey.is_default.desc())
        .first()
    )
    if not ak:
        return None
    try:
        return decrypt(ak.encrypted_key)
    except Exception as e:
        logger.warning(f"[resolver] decrypt failed for api_key {ak.id}: {e}")
        return None


def _build_llm(slug: str, api_key: str, model: Optional[str], settings: Dict[str, Any]):
    params: Dict[str, Any] = {}
    if settings.get("temperature") is not None:
        params["temperature"] = settings["temperature"]
    if settings.get("max_tokens") is not None:
        params["max_tokens"] = settings["max_tokens"]

    if slug == "openai":
        kwargs = {"api_key": api_key, "model": model or "gpt-4o-mini"}
        if params:
            kwargs["params"] = OpenAILLMService.InputParams(**params)
        return OpenAILLMService(**kwargs)
    if slug == "anthropic":
        kwargs = {"api_key": api_key, "model": model or "claude-3-5-sonnet-latest"}
        if params:
            kwargs["params"] = AnthropicLLMService.InputParams(**params)
        return AnthropicLLMService(**kwargs)
    if slug == "groq":
        kwargs = {"api_key": api_key, "model": model or "llama-3.1-70b-versatile"}
        if params:
            kwargs["params"] = GroqLLMService.InputParams(**params)
        return GroqLLMService(**kwargs)
    if slug == "google":
        kwargs = {"api_key": api_key, "model": model or "gemini-2.0-flash-exp"}
        if params:
            kwargs["params"] = GoogleLLMService.InputParams(**params)
        return GoogleLLMService(**kwargs)
    logger.warning(f"[resolver] unsupported LLM provider slug: {slug}")
    return None


def _build_stt(slug: str, api_key: str, model: Optional[str], settings: Dict[str, Any]):
    if slug == "deepgram":
        if model:
            return DeepgramSTTService(api_key=api_key, live_options=LiveOptions(model=model))
        return DeepgramSTTService(api_key=api_key)
    if slug == "openai":
        return OpenAISTTService(api_key=api_key, model=model or "whisper-1")
    if slug == "groq":
        return GroqSTTService(api_key=api_key, model=model or "whisper-large-v3")
    if slug == "google":
        return GoogleSTTService(api_key=api_key)
    if slug == "nvidia":
        return NvidiaSTTService(api_key=api_key)
    if slug == "cartesia":
        kwargs = {"api_key": api_key}
        if model:
            kwargs["model"] = model
        return CartesiaSTTService(**kwargs)
    if slug == "elevenlabs":
        kwargs = {"api_key": api_key}
        if model:
            kwargs["model"] = model
        return ElevenLabsRealtimeSTTService(**kwargs)
    if slug == "gladia":
        return GladiaSTTService(api_key=api_key)
    if slug == "assemblyai":
        return AssemblyAISTTService(api_key=api_key)
    if slug == "speechmatics":
        return SpeechmaticsSTTService(api_key=api_key)
    if slug == "soniox":
        return SonioxSTTService(api_key=api_key)
    logger.warning(f"[resolver] unsupported STT provider slug: {slug}")
    return None


def _build_tts(slug: str, api_key: str, model: Optional[str], voice_id: Optional[str], settings: Dict[str, Any]):
    if slug == "cartesia":
        kwargs = {"api_key": api_key}
        if voice_id:
            kwargs["voice_id"] = voice_id
        if model:
            kwargs["model"] = model
        return CartesiaTTSService(**kwargs)
    if slug == "openai":
        return OpenAITTSService(api_key=api_key, voice=voice_id or "alloy", model=model or "tts-1")
    if slug == "elevenlabs":
        return ElevenLabsTTSService(api_key=api_key, voice_id=voice_id or "21m00Tcm4TlvDq8ikWAM")
    if slug == "deepgram":
        return DeepgramHttpTTSService(api_key=api_key, voice=voice_id or "aura-2-helena-en", model=model or "aura-2")
    if slug == "google":
        return GoogleTTSService(credentials=api_key, voice_id=voice_id or "en-US-Wavenet-A")
    if slug == "rime":
        rime_params: Dict[str, Any] = {}
        speed = settings.get("speed")
        if speed is not None:
            rime_params["speed_alpha"] = float(speed)
        kwargs = {
            "api_key": api_key,
            "voice_id": voice_id or "kai",
            "aiohttp_session": aiohttp.ClientSession(),
            "model": model or "mistv2",
        }
        if rime_params:
            kwargs["params"] = RimeHttpTTSService.InputParams(**rime_params)
        return RimeHttpTTSService(**kwargs)
    logger.warning(f"[resolver] unsupported TTS provider slug: {slug}")
    return None


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

        llm = _build_llm(llm_slug, llm_key, llm_model, llm_settings) if llm_slug and llm_key else None
        stt = _build_stt(stt_slug, stt_key, stt_model, stt_settings) if stt_slug and stt_key else None

        voice_id = (voice_row.name if voice_row else None) or (
            voice_id_raw if voice_id_raw and not _looks_like_uuid(voice_id_raw) else None
        )
        tts = _build_tts(tts_slug, tts_key, tts_model, voice_id, voice_settings) if tts_slug and tts_key else None

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
