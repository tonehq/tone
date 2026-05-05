"""Factory to build LLM, STT, and TTS instances from an agent's config and run the bot pipeline."""

import json
import os
import sys
import time as _time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


from typing import Any, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.models import Model
from core.models.service import Service
from core.models.service_provider import ServiceProvider
from core.models.voice import Voice
from core.services.base import BaseService
from core.utils.encryption import decrypt


class AgentFactoryService(BaseService):
    """Build LLM, STT, TTS instances from agent config and run the voice bot pipeline."""

    def _get_agent_config(self, agent: Any) -> Optional[AgentConfig]:
        """Get the active agent config for the given agent (Agent model or agent_id)."""
        agent_id = agent.id if hasattr(agent, "id") else agent
        return (
            self.db.query(AgentConfig)
            .filter(
                AgentConfig.agent_id == agent_id,
                AgentConfig.status == "active",
            )
            .first()
        )

    def _get_service_and_credentials(
        self, service_id: Optional[int], service_type: str
    ) -> Optional[Tuple[Model, ServiceProvider, str]]:
        """
        Get the first active Model for the given service and type, plus decrypted API key.
        service_id now refers to services.id (not service_providers.id).
        Returns (Model, ServiceProvider, decrypted_api_key) or None.
        """
        if not service_id:
            return None

        # Look up the Service record to get service_provider_id and api_key_id
        service = self.db.query(Service).filter(Service.id == service_id).first()
        if not service:
            print(f"DEBUG _get_service_and_credentials: no Service found for service_id={service_id}")
            return None

        service_provider_id = service.service_provider_id

        result = (
            self.db.query(Model, ServiceProvider)
            .join(ServiceProvider, Model.service_provider_id == ServiceProvider.id)
            .filter(
                Model.service_provider_id == service_provider_id,
                Model.service_type == service_type,
                Model.status == "active",
            )
            .first()
        )
        if not result:
            print(f"DEBUG _get_service_and_credentials: no active Model found for provider_id={service_provider_id} type={service_type}")
            return None
        svc, provider = result

        # Prefer API key from Service record, then fallback to provider-level
        api_key_id = service.api_key_id
        if not api_key_id:
            q = self.db.query(ApiKey.id).filter(ApiKey.service_provider_id == service_provider_id)
            if self.org_id:
                q = q.filter(ApiKey.organization_id == self.org_id)
            api_key_id = q.order_by(ApiKey.id.desc()).limit(1).scalar()

        api_key_value = None
        if api_key_id:
            api_key = self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
            if api_key and api_key.api_key_encrypted:
                try:
                    api_key_value = decrypt(api_key.api_key_encrypted)
                except Exception as e:
                    logger.warning("Failed to decrypt API key for model %s: %s", svc.id, e)
            else:
                print(f"DEBUG _get_service_and_credentials: api_key record missing or not encrypted for api_key_id={api_key_id}")
        else:
            print(f"DEBUG _get_service_and_credentials: no api_key found for service_id={service_id} provider_id={service_provider_id}")
        if not api_key_value:
            print(f"DEBUG _get_service_and_credentials: no api_key_value resolved for service_id={service_id} type={service_type}")
            return None
        return (svc, provider, api_key_value)

    def _build_input_params(self, service_class, metadata: dict):
        """Convert metadata dict to proper InputParams for a Pipecat service class.

        Filters metadata to only include keys that the service's InputParams accepts,
        then constructs and returns the InputParams instance.
        Returns None if the service has no InputParams class.
        """
        input_params_class = getattr(service_class, "InputParams", None)
        if not input_params_class:
            return None
        valid_keys = set(input_params_class.model_fields.keys())
        filtered = {k: v for k, v in metadata.items() if k in valid_keys and v is not None and v != "None"}
        # Deserialize JSON-encoded strings for fields that expect list/dict types
        for k, v in filtered.items():
            if isinstance(v, str):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, (list, dict)):
                        filtered[k] = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        if not filtered:
            return input_params_class()
        try:
            return input_params_class(**filtered)
        except Exception as e:
            logger.warning(f"Failed to build InputParams for {service_class.__name__}: {e}")
            return input_params_class()

    def _get_model_name_by_id(self, model_id: Any) -> Optional[str]:
        """Look up a Model record by ID and return its name, or None if not found."""
        if model_id is None:
            return None
        try:
            model_record = self.db.query(Model).filter(Model.id == int(model_id)).first()
            return model_record.name if model_record else None
        except (TypeError, ValueError):
            return None

    def _get_model_name_from_voice(self, provider_id: int, voice_id: str) -> Optional[str]:
        """Look up a Voice record by provider and voice_id, then resolve its model name.

        Used by providers like Rime and Sarvam where the model is determined by the voice.
        """
        if not voice_id:
            return None
        voice = (
            self.db.query(Voice)
            .filter(Voice.service_provider_id == provider_id, Voice.voice_id == voice_id)
            .first()
        )
        if not voice or not voice.model_id:
            return None
        return self._get_model_name_by_id(voice.model_id)

    def _extract_service_data(self, service_provider_id: Optional[int], service_type: str, metadata: dict) -> Optional[dict]:
        """Extract raw service data (provider, key, model) into a JSON-serializable dict.

        Used by serialize_agent_bot_data to pre-fetch data for the subprocess.
        """
        if not service_provider_id:
            return None
        result = self._get_service_and_credentials(service_provider_id, service_type)
        if not result:
            return None
        svc, provider, api_key = result
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        provider_name = (provider.name or "").strip().lower()
        model_name = self._get_model_name_by_id(metadata.get("model_id"))
        # For Rime and Sarvam, the model is determined by the voice
        if provider_name in ("rime", "sarvam") and metadata.get("voice_id"):
            voice_model = self._get_model_name_from_voice(provider.id, metadata["voice_id"])
            if voice_model:
                model_name = voice_model
        return {
            "provider_name": (provider.name or "").strip().lower(),
            "api_key": api_key,
            "model_name": model_name,
            "metadata": metadata,
            "model_meta_data": model_meta,
        }

    def _get_telephony_creds_bulk(self, provider_name: str) -> dict:
        """Fetch telephony provider credentials in a single query using the existing DB session.

        Avoids the separate ServiceProvider + ApiKey queries that _get_twilio_credentials does.
        """
        provider = self.db.query(ServiceProvider).filter(ServiceProvider.name == provider_name).first()
        if not provider:
            logger.warning("%s service provider not found in DB", provider_name)
            return {}

        q = self.db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id)
        if self.org_id:
            q = q.filter(ApiKey.organization_id == self.org_id)
        api_keys = q.all()

        creds = {}
        for ak in api_keys:
            additional = ak.additional_credentials or {}
            key_type = additional.get("key_type")
            if key_type and ak.api_key_encrypted:
                try:
                    creds[key_type] = decrypt(ak.api_key_encrypted)
                except Exception as e:
                    logger.warning("Failed to decrypt %s key %s: %s", provider_name, ak.id, e)
        return creds

    def serialize_agent_bot_data(self, agent: Any, transport_type: str = None) -> Optional[dict]:
        """Pre-fetch all data needed to build LLM/STT/TTS services into a JSON-serializable dict.

        Called in the main process so the subprocess can build services without DB queries.
        Uses bulk queries to minimize DB round-trips.
        If transport_type is provided, also fetches telephony credentials in the same DB session.
        Returns None if config or any required service is missing.

        Results are cached in Redis keyed by agent_id + transport_type.
        """
        from sqlalchemy import and_, or_

        from core.services.redis_service import cache_get, cache_set

        _t_ser = _time.monotonic()

        # Check Redis cache first
        agent_id = agent.id if hasattr(agent, "id") else agent
        cache_key = f"agent_bot_data:{agent_id}:{transport_type or 'none'}"
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("[TIMING] serialize: CACHE HIT for agent_id=%s (+%.3fs)", agent_id, _time.monotonic() - _t_ser)
            return cached

        # Query 1: Get agent config
        config = self._get_agent_config(agent)
        logger.info("[TIMING] serialize: Q1 _get_agent_config (+%.3fs)", _time.monotonic() - _t_ser)
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

        # Collect all service IDs (these now point to services.id, not service_providers.id)
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
        _t = _time.monotonic()
        svc_records = self.db.query(Service).filter(Service.id.in_(all_svc_ids)).all()
        svc_lookup = {s.id: s for s in svc_records}
        # Map: service_type -> service_provider_id
        sp_id_map = {}
        svc_api_key_map = {}  # service_id -> api_key_id from Service record
        for stype, svc_id in service_id_map.items():
            if svc_id and svc_id in svc_lookup:
                sp_id_map[stype] = svc_lookup[svc_id].service_provider_id
                if svc_lookup[svc_id].api_key_id:
                    svc_api_key_map[svc_id] = svc_lookup[svc_id].api_key_id
        all_sp_ids = list(set(sp_id_map.values()))
        logger.info("[TIMING] serialize: Q1.5 resolve Service->provider (+%.3fs)", _time.monotonic() - _t)

        # Collect model_ids for name resolution (needed before Q2)
        metadata_map = {"llm": llm_metadata, "stt": stt_metadata, "tts": tts_metadata}
        model_name_ids = set()
        for stype, meta in metadata_map.items():
            mid = meta.get("model_id")
            if mid is not None:
                model_name_ids.add(int(mid))

        # Query 2: Bulk fetch Models + ServiceProviders + model names (merged Q2+Q4)
        _t = _time.monotonic()
        q2_conditions = [and_(Model.service_provider_id.in_(all_sp_ids), Model.status == "active")]
        if model_name_ids:
            q2_conditions.append(Model.id.in_(model_name_ids))
        rows = (
            self.db.query(Model, ServiceProvider)
            .join(ServiceProvider, Model.service_provider_id == ServiceProvider.id)
            .filter(or_(*q2_conditions))
            .all()
        )
        logger.info("[TIMING] serialize: Q2 bulk Models+Providers+names (+%.3fs)", _time.monotonic() - _t)

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
                    # Fallback: find API key by service_provider_id
                    fallback_q = self.db.query(ApiKey.id).filter(
                        ApiKey.service_provider_id == svc.service_provider_id,
                        ApiKey.status == "active",
                    )
                    if self.org_id:
                        fallback_q = fallback_q.filter(ApiKey.organization_id == self.org_id)
                    fallback_key_id = fallback_q.order_by(ApiKey.id.desc()).limit(1).scalar()
                    if fallback_key_id:
                        api_key_ids.add(fallback_key_id)
                        svc_api_key_map[matched_svc_id] = fallback_key_id

        # Query 3: Bulk fetch ApiKeys + telephony keys (merged Q3 + telephony creds)
        _t = _time.monotonic()
        api_key_map = {}
        telephony_creds = {}

        q3_filters = []
        if api_key_ids:
            q3_filters.append(ApiKey.id.in_(api_key_ids))
        if transport_type:
            # Use subquery to include telephony provider's keys without a separate query
            telephony_sp_subq = (
                self.db.query(ServiceProvider.id)
                .filter(ServiceProvider.name == transport_type)
                .scalar_subquery()
            )
            telephony_filter = ApiKey.service_provider_id == telephony_sp_subq
            if self.org_id:
                telephony_filter = and_(telephony_filter, ApiKey.organization_id == self.org_id)
            q3_filters.append(telephony_filter)

        # Try channels table first for telephony creds (org-scoped)
        if transport_type == "twilio" and hasattr(agent, "organization_id") and agent.organization_id:
            from core.models.channel import Channel
            from core.models.enums import ChannelType

            channel = (
                self.db.query(Channel)
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
            all_api_keys = self.db.query(ApiKey).filter(or_(*q3_filters)).all()
            _t_decrypt = _time.monotonic()
            logger.info("[TIMING] serialize: Q3 ApiKey+telephony query (+%.3fs)", _t_decrypt - _t)
            for ak in all_api_keys:
                if not ak.api_key_encrypted:
                    continue
                try:
                    decrypted = decrypt(ak.api_key_encrypted)
                    # LLM/STT/TTS service key
                    if ak.id in api_key_ids:
                        api_key_map[ak.id] = decrypted
                    elif not telephony_creds:
                        # Telephony key — only use api_keys if channels didn't provide creds
                        additional = ak.additional_credentials or {}
                        key_type = additional.get("key_type")
                        if key_type:
                            telephony_creds[key_type] = decrypted
                except Exception as e:
                    logger.warning("Failed to decrypt API key %s: %s", ak.id, e)
            logger.info("[TIMING] serialize: Q3 decrypt %d keys (+%.3fs)", len(api_key_map) + len(telephony_creds), _time.monotonic() - _t_decrypt)

        logger.info("[TIMING] serialize: TOTAL (+%.3fs)", _time.monotonic() - _t_ser)

        # Build service data dicts
        def _build_service_data(stype, metadata):
            sp_id = sp_id_map.get(stype)
            if not sp_id:
                print(f"DEBUG _build_service_data({stype}): no sp_id in sp_id_map. sp_id_map={sp_id_map}")
                return None
            entry = model_map.get((sp_id, stype))
            if not entry:
                print(f"DEBUG _build_service_data({stype}): no entry in model_map for key=({sp_id}, {stype}). model_map_keys={list(model_map.keys())}")
                return None
            svc, provider = entry
            # Look up API key from Service record (via svc_api_key_map), not Model
            svc_id = service_id_map.get(stype)
            svc_ak_id = svc_api_key_map.get(svc_id) if svc_id else None
            api_key = api_key_map.get(svc_ak_id) if svc_ak_id else None
            print(f"DEBUG _build_service_data({stype}): svc_id={svc_id} svc_ak_id={svc_ak_id} api_key={'present' if api_key else 'MISSING'} api_key_map_keys={list(api_key_map.keys())} svc_api_key_map={svc_api_key_map}")
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
        print(f"DEBUG serialize: llm_data={'present' if llm_data else 'NONE'} stt_data={'present' if stt_data else 'NONE'} tts_data={'present' if tts_data else 'NONE'} is_s2s={is_s2s}")

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
        cache_set(cache_key, result, ttl_seconds=1800)
        logger.info("[TIMING] serialize: CACHE MISS — stored in Redis for agent_id=%s (+%.3fs)", agent_id, _time.monotonic() - _t_ser)

        return result

    def get_llm_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        """
        Build and return the LLM service instance for the given agent.
        Uses agent config's llm_service_id (service_provider) and llm_metadata.
        If prefetched is provided, skips all DB queries.
        Returns None if config or credentials are missing or provider is unsupported.
        """
        if prefetched:
            provider_name = prefetched["provider_name"]
            api_key = prefetched["api_key"]
            model = prefetched["model_name"]
            metadata = prefetched["metadata"]
            model_meta = prefetched["model_meta_data"]
        else:
            if config is None:
                config = self._get_agent_config(agent)
            if not config or not config.llm_service_id:
                return None
            result = self._get_service_and_credentials(config.llm_service_id, "llm")
            if not result:
                return None
            svc, provider, api_key = result
            metadata = (config.llm_metadata or {}) if hasattr(config, "llm_metadata") else {}
            model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
            model = self._get_model_name_by_id(metadata.get("model_id"))
            provider_name = (provider.name or "").strip().lower()
            # For S2S, inject system_prompt so the LLM builder can use it
            if metadata.get("is_s2s") and config.system_prompt:
                metadata = dict(metadata)
                metadata["system_prompt"] = config.system_prompt

        print(f"DEBUG get_llm_for_agent: provider_name='{provider_name}' model='{model}' api_key={'present' if api_key else 'MISSING'}")
        try:
            if provider_name == "openai": #done
                from pipecat.services.openai.llm import OpenAILLMService
                return OpenAILLMService(api_key = api_key, model=model or "gpt-4.1", params=self._build_input_params(OpenAILLMService, metadata))
            if provider_name == "anthropic": #done
                from pipecat.services.anthropic.llm import AnthropicLLMService
                if "enable_prompt_caching" not in metadata:
                    metadata["enable_prompt_caching"] = True
                params=self._build_input_params(AnthropicLLMService, metadata)
                return AnthropicLLMService(api_key=api_key, model= model or "claude-haiku-4-5-20251001", params=params)
            if provider_name == "groq": #done
                from pipecat.services.groq.llm import GroqLLMService
                return GroqLLMService(api_key=api_key, model=model or "llama-3.3-70b-versatile", params=self._build_input_params(GroqLLMService, metadata))
            if provider_name == "openrouter": #done
                from pipecat.services.openrouter.llm import \
                    OpenRouterLLMService
                return OpenRouterLLMService(api_key=api_key, model= model or "openai/gpt-4o-2024-11-20", params=self._build_input_params(OpenRouterLLMService, metadata))
            if provider_name == "aws_bedrock": #done
                from pipecat.services.aws.llm import AWSBedrockLLMService
                return AWSBedrockLLMService(api_key=api_key, model=model or "amazon.nova-pro-v1:0", params=self._build_input_params(AWSBedrockLLMService, metadata))
            if provider_name == "google": #Done
                from pipecat.services.google.llm import GoogleLLMService
                params=self._build_input_params(GoogleLLMService, metadata)
                return GoogleLLMService(api_key=api_key, model=model or "gemini-2.5-flash", params=params)
            if provider_name == "ollama": #done
                from pipecat.services.ollama.llm import OLLamaLLMService
                base_url = api_key if api_key else "http://localhost:11434/v1"
                return OLLamaLLMService(model= model or "llama2", base_url=base_url, params=self._build_input_params(OLLamaLLMService, metadata))
            if provider_name in ["azure", "cerebras", "nvidia_nim", "fireworks", "together", "perplexity", "qwen", "deepseek", "mistral", "sambanova", "grok"]:
                from pipecat.services.openai.llm import BaseOpenAILLMService
                base_url = model_meta.get("base_url") or metadata.get("base_url")
                default_models = {
                    "azure": "gpt-4o",
                    "cerebras": "llama-4-scout-17b-16e-instruct",
                    "nvidia_nim": "meta/llama-3.1-8b-instruct",
                    "fireworks": "accounts/fireworks/models/deepseek-v3p1",
                    "together": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                    "perplexity": "sonar",
                    "qwen": "qwen-turbo",
                    "deepseek": "deepseek-chat",
                    "mistral": "mistral-small-latest",
                    "sambanova": "Meta-Llama-3.1-8B-Instruct",
                    "grok": "grok-3",
                }
                default_base_urls = {
                    "cerebras": "https://api.cerebras.ai/v1",
                    "nvidia_nim": "https://integrate.api.nvidia.com/v1",
                    "fireworks": "https://api.fireworks.ai/inference/v1",
                    "together": "https://api.together.xyz/v1",
                    "perplexity": "https://api.perplexity.ai",
                    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                    "deepseek": "https://api.deepseek.com/v1",
                    "mistral": "https://api.mistral.ai/v1",
                    "sambanova": "https://api.sambanova.ai/v1",
                    "grok": "https://api.x.ai/v1",
                }
                if not base_url:
                    base_url = default_base_urls.get(provider_name)
                default_model = default_models.get(provider_name, "gpt-4o")
                return BaseOpenAILLMService(api_key=api_key, model=model or default_model, base_url=base_url, params=self._build_input_params(BaseOpenAILLMService, metadata))
            if provider_name == "openai_realtime":
                from pipecat.services.openai.realtime.events import (
                    AudioConfiguration, AudioInput, AudioOutput,
                    InputAudioTranscription, SemanticTurnDetection,
                    SessionProperties)
                from pipecat.services.openai.realtime.llm import \
                    OpenAIRealtimeLLMService
                voice_id = metadata.get("voice_id")
                system_prompt = metadata.get("system_prompt")
                session_props = SessionProperties(
                    audio=AudioConfiguration(
                        input=AudioInput(
                            transcription=InputAudioTranscription(),
                            turn_detection=SemanticTurnDetection(),
                        ),
                        output=AudioOutput(voice=voice_id) if voice_id else None,
                    ),
                    instructions=system_prompt,
                )
                return OpenAIRealtimeLLMService(
                    api_key=api_key,
                    model=model or "gpt-4o-realtime-preview",
                    session_properties=session_props,
                )
            if provider_name == "gemini_live":
                from pipecat.services.google.gemini_live.llm import \
                    GeminiLiveLLMService
                voice_id = metadata.get("voice_id") or "Puck"
                return GeminiLiveLLMService(
                    api_key=api_key,
                    model=model or "models/gemini-2.5-flash-native-audio-preview-12-2025",
                    voice_id=voice_id,
                    system_instruction=metadata.get("system_instruction"),
                )
            print(f"DEBUG get_llm_for_agent: no matching provider for '{provider_name}'")
            return None
        except ImportError as e:
            logger.exception("LLM provider %s not available (ImportError)", provider_name)
            return None
        except Exception as e:
            logger.exception("LLM provider %s failed to initialize: %s", provider_name, e)
            return None


    def get_stt_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        """
        Build and return the STT service instance for the given agent.
        If prefetched is provided, skips all DB queries.
        """
        if prefetched:
            provider_name = prefetched["provider_name"]
            api_key = prefetched["api_key"]
            model = prefetched["model_name"]
            metadata = prefetched["metadata"]
            model_meta = prefetched["model_meta_data"]
        else:
            if config is None:
                config = self._get_agent_config(agent)
            if not config or not config.stt_service_id:
                return None
            result = self._get_service_and_credentials(config.stt_service_id, "stt")
            if not result:
                return None
            svc, provider, api_key = result
            metadata = (config.stt_metadata or {}) if hasattr(config, "stt_metadata") else {}
            model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
            model = self._get_model_name_by_id(metadata.get("model_id"))
            provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "deepgram":
                from deepgram import LiveOptions
                from pipecat.services.deepgram.stt import DeepgramSTTService
                dg_kwargs = {}
                if metadata.get("sample_rate") is not None:
                    dg_kwargs["sample_rate"] = metadata["sample_rate"]
                live_options = None
                if metadata.get("language"):
                    live_options = LiveOptions(language=metadata["language"])
                return DeepgramSTTService(api_key=api_key, live_options=live_options, **dg_kwargs)
            if provider_name == "openai":
                from pipecat.services.openai.stt import OpenAISTTService
                return OpenAISTTService(
                    api_key=api_key,
                    model=model or "gpt-4o-transcribe",
                    language=metadata.get("language"),
                    prompt=metadata.get("prompt"),
                    temperature=metadata.get("temperature"),
                )
            if provider_name == "groq":
                from pipecat.services.groq.stt import GroqSTTService
                return GroqSTTService(
                    api_key=api_key,
                    model=model or "whisper-large-v3-turbo",
                    language=metadata.get("language"),
                    prompt=metadata.get("prompt"),
                    temperature=metadata.get("temperature"),
                )
            if provider_name == "azure":
                from pipecat.services.azure.stt import AzureSTTService
                region = model_meta.get("region") or metadata.get("region") or "eastus"
                azure_kwargs = {}
                if metadata.get("language") is not None:
                    azure_kwargs["language"] = metadata["language"]
                if metadata.get("sample_rate") is not None:
                    azure_kwargs["sample_rate"] = metadata["sample_rate"]
                if metadata.get("endpoint_id") is not None:
                    azure_kwargs["endpoint_id"] = metadata["endpoint_id"]
                return AzureSTTService(api_key=api_key, region=region, **azure_kwargs)
            if provider_name == "google":
                from pipecat.services.google.stt import GoogleSTTService
                return GoogleSTTService(credentials=api_key, params=self._build_input_params(GoogleSTTService, metadata))
            if provider_name == "nvidia":
                from pipecat.services.nvidia.stt import NvidiaSTTService
                return NvidiaSTTService(api_key=api_key, params=self._build_input_params(NvidiaSTTService, metadata))
            if provider_name == "sarvam":
                from pipecat.services.sarvam.stt import SarvamSTTService
                return SarvamSTTService(
                    api_key=api_key,
                    model=model or "saarika:v2.5",
                    sample_rate=metadata.get("sample_rate"),
                    params=self._build_input_params(SarvamSTTService, metadata),
                )
            if provider_name == "speechmatics":
                from core.services.speechmatics_stt import \
                    ToneSpeechmaticsSTTService

                # Use adaptive mode for fast basic VAD; LocalSmartTurnAnalyzerV3
                # handles the actual turn-end decision in the pipeline.
                if "turn_detection_mode" not in metadata:
                    metadata["turn_detection_mode"] = "adaptive"
                if "operating_point" not in metadata:
                    metadata["operating_point"] = "enhanced"
                if "max_delay" not in metadata:
                    metadata["max_delay"] = 0.7
                return ToneSpeechmaticsSTTService(
                    api_key=api_key,
                    base_url="wss://us2.rt.speechmatics.com/v2",
                    sample_rate=metadata.get("sample_rate"),
                    params=self._build_input_params(ToneSpeechmaticsSTTService, metadata),
                )
            if provider_name == "assemblyai":
                from pipecat.services.assemblyai.models import \
                    AssemblyAIConnectionParams
                from pipecat.services.assemblyai.stt import \
                    AssemblyAISTTService
                conn_kwargs = {}
                if metadata.get("sample_rate") is not None:
                    conn_kwargs["sample_rate"] = metadata["sample_rate"]
                if metadata.get("word_finalization_max_wait_time") is not None:
                    conn_kwargs["word_finalization_max_wait_time"] = metadata["word_finalization_max_wait_time"]
                if metadata.get("end_of_turn_confidence_threshold") is not None:
                    conn_kwargs["end_of_turn_confidence_threshold"] = metadata["end_of_turn_confidence_threshold"]
                if metadata.get("speech_model") is not None:
                    conn_kwargs["speech_model"] = metadata["speech_model"]
                asm_kwargs = {}
                if metadata.get("language") is not None:
                    asm_kwargs["language"] = metadata["language"]
                if conn_kwargs:
                    asm_kwargs["connection_params"] = AssemblyAIConnectionParams(**conn_kwargs)
                return AssemblyAISTTService(api_key=api_key, **asm_kwargs)
            if provider_name == "cartesia":
                from pipecat.services.cartesia.stt import (CartesiaLiveOptions,
                                                           CartesiaSTTService)
                live_options = CartesiaLiveOptions(
                    language=metadata.get("language") or "en",
                    sample_rate=metadata.get("sample_rate") or 16000,
                )
                return CartesiaSTTService(
                    api_key=api_key,
                    sample_rate=metadata.get("sample_rate") or 16000,
                    live_options=live_options,
                )
            if provider_name == "elevenlabs":
                from pipecat.services.elevenlabs.stt import \
                    ElevenLabsRealtimeSTTService
                return ElevenLabsRealtimeSTTService(api_key=api_key, model=model or "scribe_v2_realtime", params=self._build_input_params(ElevenLabsRealtimeSTTService, metadata))
            if provider_name == "gladia":
                from pipecat.services.gladia.stt import GladiaSTTService
                return GladiaSTTService(
                    api_key=api_key,
                    model=model or "solaria-1",
                    region=metadata.get("region"),
                    sample_rate=metadata.get("sample_rate"),
                    params=self._build_input_params(GladiaSTTService, metadata),
                )
            if provider_name == "soniox":
                from pipecat.services.soniox.stt import SonioxSTTService
                return SonioxSTTService(api_key=api_key, params=self._build_input_params(SonioxSTTService, metadata))
            if provider_name == "hathora":
                from pipecat.services.hathora.stt import HathoraSTTService
                return HathoraSTTService(api_key=api_key, model=model or "parakeet", params=self._build_input_params(HathoraSTTService, metadata))
            if provider_name == "sambanova":
                from pipecat.services.sambanova.stt import SambaNovaSTTService
                sn_kwargs = {}
                if metadata.get("language") is not None:
                    sn_kwargs["language"] = metadata["language"]
                if metadata.get("prompt") is not None:
                    sn_kwargs["prompt"] = metadata["prompt"]
                if metadata.get("temperature") is not None:
                    sn_kwargs["temperature"] = metadata["temperature"]
                return SambaNovaSTTService(api_key=api_key, model=model or "Whisper-Large-v3", **sn_kwargs)
            logger.warning("Unsupported STT provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("STT provider %s not available: %s", provider_name, e)
            return None

    def get_tts_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        """
        Build and return the TTS service instance for the given agent.
        If prefetched is provided, skips all DB queries.
        """
        if prefetched:
            provider_name = prefetched["provider_name"]
            api_key = prefetched["api_key"]
            model = prefetched["model_name"]
            metadata = prefetched["metadata"]
            model_meta = prefetched["model_meta_data"]
        else:
            if config is None:
                config = self._get_agent_config(agent)
            if not config or not config.tts_service_id:
                return None
            result = self._get_service_and_credentials(config.tts_service_id, "tts")
            if not result:
                return None
            svc, provider, api_key = result
            metadata = (config.tts_metadata or {}) if hasattr(config, "tts_metadata") else {}
            model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
            model = self._get_model_name_by_id(metadata.get("model_id"))
            provider_name = (provider.name or "").strip().lower()
            # For Rime and Sarvam, the model is determined by the voice
            if provider_name in ("rime", "sarvam") and metadata.get("voice_id"):
                voice_model = self._get_model_name_from_voice(provider.id, metadata["voice_id"])
                if voice_model:
                    model = voice_model

        tts_voice_id = metadata.get("voice_id")
        tts_language = metadata.get("language")

        # Providers that need an aiohttp session
        _http_providers = {"asyncai_http", "deepgram", "minimax", "neuphonic", "rime", "sarvam", "speechmatics"}

        import aiohttp
        session = aiohttp.ClientSession() if provider_name in _http_providers else None

        try:
            if provider_name == "cartesia": # In code but class is different
                from pipecat.services.cartesia.tts import CartesiaTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
                
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language or "en"
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return CartesiaTTSService(api_key=api_key, model=model or "sonic-3", params=self._build_input_params(CartesiaTTSService, metadata), **voice_kwargs)
            if provider_name == "openai": # In code
                
                from pipecat.services.openai.tts import OpenAITTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return OpenAITTSService(api_key=api_key, model=model or "gpt-4o-mini-tts", params=self._build_input_params(OpenAITTSService, metadata), **voice_kwargs)
            if provider_name == "elevenlabs":
                from pipecat.services.elevenlabs.tts import \
                    ElevenLabsTTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id or "CwhRBWXzGAHq8TQ4Fs17"

                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return ElevenLabsTTSService(api_key=api_key, model=model or "eleven_v3", params=self._build_input_params(ElevenLabsTTSService, metadata), **voice_kwargs)
            if provider_name == "playht": # In code but class is different
                # To check this fully
                from pipecat.services.playht.tts import PlayHTTTSService
                user_id = model_meta.get("user_id") or metadata.get("user_id") or ""
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_url"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return PlayHTTTSService(api_key=api_key, user_id=user_id, params=self._build_input_params(PlayHTTTSService, metadata), **voice_kwargs)
            if provider_name == "asyncai_http":  # in code
                # To check languages in this
                from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "13616e5f-6fda-4247-b548-8821cb71fb54"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return AsyncAIHttpTTSService(api_key=api_key, aiohttp_session=session, params=self._build_input_params(AsyncAIHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "aws_polly":  # In code
                from pipecat.services.aws.tts import AWSPollyTTSService
                aws_access_key_id = model_meta.get("aws_access_key_id") or metadata.get("aws_access_key_id") or ""
                region = model_meta.get("region") or metadata.get("region") or "us-east-1"
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return AWSPollyTTSService(api_key=api_key, aws_access_key_id=aws_access_key_id, region=region, params=self._build_input_params(AWSPollyTTSService, metadata), **voice_kwargs)
            if provider_name == "camb":  # In code
                from pipecat.services.camb.tts import CambTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                # Camb uses numeric language IDs (e.g. "1", "35") passed via voice_kwargs,
                # but InputParams expects locale codes (e.g. "en"). Exclude language from params.
                camb_metadata = {k: v for k, v in metadata.items() if k != "language"}
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return CambTTSService(api_key=api_key, params=self._build_input_params(CambTTSService, camb_metadata), **voice_kwargs)
            if provider_name == "deepgram":  # In code
                from pipecat.services.deepgram.tts import \
                    DeepgramHttpTTSService
                dg_voice = tts_voice_id or "aura-2-helena-en"
                dg_model = model or "aura-2"
                dg_kwargs = {}
                if metadata.get("sample_rate") is not None:
                    dg_kwargs["sample_rate"] = metadata["sample_rate"]
                print(f"[TTS {provider_name}] model: {dg_model}, voice: {dg_voice}")
                return DeepgramHttpTTSService(api_key=api_key, model=dg_model, voice=dg_voice, aiohttp_session=session, **dg_kwargs)
            if provider_name == "google": # Done
                from pipecat.services.google.tts import GoogleTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}, location: global")
                return GoogleTTSService(credentials=api_key, params=self._build_input_params(GoogleTTSService, metadata), **voice_kwargs)
            if provider_name == "groq": # In code
                from pipecat.services.groq.tts import GroqTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                # Pick model based on language: Arabic voices use Arabic model, everything else uses English model
                if not model:
                    model = "canopylabs/orpheus-arabic-saudi" if tts_language == "ar" else "canopylabs/orpheus-v1-english"
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return GroqTTSService(api_key=api_key, model_name=model, params=self._build_input_params(GroqTTSService, metadata), **voice_kwargs)
            if provider_name == "hathora": # In code
                # Need to check this fully
                from pipecat.services.hathora.tts import HathoraTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return HathoraTTSService(api_key=api_key, model=model or "hexgrad-kokoro-82m", params=self._build_input_params(HathoraTTSService, metadata), **voice_kwargs)
            if provider_name == "minimax": # In code
                # To check group id in this
                from pipecat.services.minimax.tts import MiniMaxHttpTTSService
                group_id = model_meta.get("group_id") or metadata.get("group_id") or ""
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return MiniMaxHttpTTSService(api_key=api_key, group_id=group_id, model=model or "speech-2.8-turbo", aiohttp_session=session, params=self._build_input_params(MiniMaxHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "neuphonic": # In code
                # To check language
                from pipecat.services.neuphonic.tts import \
                    NeuphonicHttpTTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id or "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return NeuphonicHttpTTSService(api_key=api_key, model=model or "neu_hq", aiohttp_session=session, params=self._build_input_params(NeuphonicHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "nvidia": # In code
                from pipecat.services.nvidia.tts import NvidiaTTSService
                server = model_meta.get("server") or metadata.get("server") or "grpc.nvcf.nvidia.com:443"
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return NvidiaTTSService(api_key=api_key, server=server, params=self._build_input_params(NvidiaTTSService, metadata), **voice_kwargs)
            if provider_name == "rime": # In code
                from pipecat.services.rime.tts import RimeHttpTTSService
                from pipecat.transcriptions.language import Language
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "albion"

                # Map human-readable language name to Language enum for Rime's InputParams.
                # Rime uses InputParams.language to set the 'lang' field in the API payload.
                _RIME_LANG_MAP = {
                    "english": Language.EN,
                    "german": Language.DE,
                    "french": Language.FR,
                    "spanish": Language.ES,
                    "hindi": Language.HI,
                }
                rime_language = None
                if tts_language:
                    rime_language = _RIME_LANG_MAP.get(tts_language.strip().lower())

                # Build InputParams, overriding language if we resolved one
                params = self._build_input_params(RimeHttpTTSService, metadata)
                if rime_language and params:
                    params.language = rime_language

                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return RimeHttpTTSService(api_key=api_key, model=model or "mistv2", aiohttp_session=session, params=params, **voice_kwargs)
            if provider_name == "sarvam": # In code
                from pipecat.services.sarvam.tts import SarvamHttpTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    # Sarvam API expects just the speaker name (e.g. "shubh"),
                    # but DB stores composite voice_ids like "sarvam-shubh-hi-IN".
                    # Strip the prefix and language suffix if present.
                    sarvam_voice = tts_voice_id
                    if sarvam_voice.startswith("sarvam-"):
                        parts = sarvam_voice.split("-")
                        # Format: sarvam-{name}-{lang}-{region} → extract name
                        if len(parts) >= 3:
                            sarvam_voice = parts[1]
                    voice_kwargs["voice_id"] = sarvam_voice
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return SarvamHttpTTSService(api_key=api_key, model=model or "bulbul:v3", aiohttp_session=session, params=self._build_input_params(SarvamHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "speechmatics": # In code
                from pipecat.services.speechmatics.tts import \
                    SpeechmaticsTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return SpeechmaticsTTSService(api_key=api_key, aiohttp_session=session, sample_rate=metadata.get("sample_rate") or SpeechmaticsTTSService.SPEECHMATICS_SAMPLE_RATE, params=self._build_input_params(SpeechmaticsTTSService, metadata), **voice_kwargs)
            if provider_name == "azure":
                from pipecat.services.azure.tts import AzureTTSService
                region = model_meta.get("region") or metadata.get("region") or "eastus"
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return AzureTTSService(api_key=api_key, region=region, params=self._build_input_params(AzureTTSService, metadata), **voice_kwargs)
            if provider_name == "fish":
                # To check this fully
                from pipecat.services.fish.tts import FishAudioTTSService
                voice_kwargs = {}
                voice_kwargs["reference_id"] = tts_voice_id or "0eb2bd3576714dbcad7cd4c6b2b6e12f"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return FishAudioTTSService(api_key=api_key, model_id=model or "s1", params=self._build_input_params(FishAudioTTSService, metadata), **voice_kwargs)
            if provider_name == "hume":
                from pipecat.services.hume.tts import HumeTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return HumeTTSService(api_key=api_key, version=model or "2", params=self._build_input_params(HumeTTSService, metadata), **voice_kwargs)
            if provider_name == "inworld":
                from pipecat.services.inworld.tts import InworldTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return InworldTTSService(api_key=api_key, model=model or "inworld-tts-1.5-max", params=self._build_input_params(InworldTTSService, metadata), **voice_kwargs)
            if provider_name == "lmnt":
                from pipecat.services.lmnt.tts import LmntTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "ava"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language

                return LmntTTSService(api_key=api_key, **voice_kwargs)
            if provider_name == "resemble":
                # Need to check voices
                from pipecat.services.resembleai.tts import \
                    ResembleAITTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                if metadata.get("sample_rate") is not None:
                    voice_kwargs["sample_rate"] = metadata["sample_rate"]
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return ResembleAITTSService(api_key=api_key, **voice_kwargs)

            logger.warning("Unsupported TTS provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("TTS provider %s not available: %s", provider_name, e)
            return None

    def get_agent_bot_data(self, agent: Any, prefetched: dict = None) -> Optional[dict]:
        """
        Get all data needed to run the bot for an agent: llm, stt, tts, and messages.
        If prefetched is provided (from serialize_agent_bot_data), skips all DB queries.
        Returns None if config or any required service is missing.
        """
        _t0 = _time.monotonic()

        # If no prefetched data provided, try Redis cache before hitting DB
        if not prefetched:
            from core.services.redis_service import cache_get
            agent_id = agent.id if hasattr(agent, "id") else agent
            # Try transport-specific cache keys first, then fall back to 'none'
            for transport_suffix in ("twilio", "telnyx", "plivo", "exotel", "none"):
                cache_key = f"agent_bot_data:{agent_id}:{transport_suffix}"
                cached = cache_get(cache_key)
                if cached is not None:
                    logger.info("[TIMING] using Redis-cached service data from key=%s (no DB queries)", cache_key)
                    prefetched = cached
                    break

        if prefetched:
            logger.info("[TIMING] using prefetched service data (no DB queries)")
            is_s2s = bool(prefetched.get("is_s2s"))
            print(f"DEBUG get_agent_bot_data: is_s2s={is_s2s} llm_prefetched={prefetched.get('llm')}")

            _t = _time.monotonic()
            llm = self.get_llm_for_agent(agent, prefetched=prefetched["llm"])
            print(f"DEBUG get_agent_bot_data: llm={'present' if llm else 'NONE'}")
            logger.info("[TIMING] get_llm_for_agent prefetched (+%.3fs)", _time.monotonic() - _t)

            stt = None
            tts = None
            if not is_s2s:
                _t = _time.monotonic()
                stt = self.get_stt_for_agent(agent, prefetched=prefetched["stt"])
                logger.info("[TIMING] get_stt_for_agent prefetched (+%.3fs)", _time.monotonic() - _t)

                _t = _time.monotonic()
                tts = self.get_tts_for_agent(agent, prefetched=prefetched["tts"])
                logger.info("[TIMING] get_tts_for_agent prefetched (+%.3fs)", _time.monotonic() - _t)

            messages = prefetched["messages"]
            end_call_message = prefetched.get("end_call_message")
        else:
            config = self._get_agent_config(agent)
            logger.info("[TIMING] _get_agent_config (+%.3fs)", _time.monotonic() - _t0)
            if not config or not config.system_prompt:
                return None

            llm_metadata = (config.llm_metadata or {}) if hasattr(config, "llm_metadata") else {}
            is_s2s = bool(llm_metadata.get("is_s2s"))

            _t = _time.monotonic()
            llm = self.get_llm_for_agent(agent, config=config)
            print(f"DEBUG llm_service_id={config.llm_service_id} llm={llm}")
            logger.info("[TIMING] get_llm_for_agent (+%.3fs)", _time.monotonic() - _t)

            stt = None
            tts = None
            if not is_s2s:
                _t = _time.monotonic()
                stt = self.get_stt_for_agent(agent, config=config)
                print(f"DEBUG stt_service_id={config.stt_service_id} stt={stt}")
                logger.info("[TIMING] get_stt_for_agent (+%.3fs)", _time.monotonic() - _t)

                _t = _time.monotonic()
                tts = self.get_tts_for_agent(agent, config=config)
                print(f"DEBUG tts_service_id={config.tts_service_id} tts={tts}")
                logger.info("[TIMING] get_tts_for_agent (+%.3fs)", _time.monotonic() - _t)

            if not llm:
                print("DEBUG RETURNING None: llm is None/falsy")
                return None
            if not is_s2s and (not stt or not tts):
                print(f"DEBUG RETURNING None: is_s2s={is_s2s} stt={stt} tts={tts}")
                return None
            messages = [{"role": "system", "content": config.system_prompt}]
            if getattr(config, "first_message", None) and config.first_message.strip():
                messages.append({"role": "assistant", "content": config.first_message.strip()})
            end_call_message = getattr(config, "end_call_message", None)

        if not llm:
            return None
        if not is_s2s and (not stt or not tts):
            return None
        logger.info("[TIMING] get_agent_bot_data total (+%.3fs)", _time.monotonic() - _t0)
        return {
            "llm": llm,
            "stt": stt,
            "tts": tts,
            "is_s2s": is_s2s,
            "messages": messages,
            "end_call_message": end_call_message,
        }

    async def run_bot_with_components(
        self,
        transport: Any,
        runner_args: Any,
        llm: Any,
        stt: Any,
        tts: Any,
        messages: List[dict],
        agent: Any = None,
        end_call_message: str = None,
        is_s2s: bool = False,
    ) -> None:
        """
        Run the voice pipeline with the given transport and services.
        Called by run_bot_for_agent or from bot.py with default components.
        """
        _t_comp_start = _time.monotonic()
        import io

        _t = _time.monotonic()
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.llm_context import (NOT_GIVEN,
                                                                LLMContext)
        from pipecat.processors.aggregators.llm_response_universal import (
            AssistantTurnStoppedMessage, LLMContextAggregatorPair,
            LLMUserAggregatorParams, UserTurnStoppedMessage)
        from pipecat.turns.user_turn_strategies import UserTurnStrategies
        from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
        from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
        from pipecat.processors.aggregators.llm_text_processor import \
            LLMTextProcessor
        from pipecat.processors.audio.audio_buffer_processor import \
            AudioBufferProcessor
        from pipecat.processors.frameworks.rtvi import (RTVIConfig,
                                                        RTVIObserver,
                                                        RTVIProcessor)
        from pydub import AudioSegment

        from core.database.session import get_db_context
        from core.processors.call_end_detector import CallEndDetectorProcessor
        from core.processors.metrics_collector import MetricsCollectorProcessor
        from core.services.call_log_service import CallLogService
        logger.info("[TIMING] run_bot_with_components imports (+%.3fs)", _time.monotonic() - _t)

        # Extract call metadata from runner_args
        body = getattr(runner_args, "body", None) or {}
        call_data = body.get("call_data", {})
        transport_type = body.get("transport_type", "unknown")
        provider_call_id = (
            call_data.get("call_id")
            or call_data.get("call_control_id")
            or call_data.get("stream_id", "")
        )
        from_number = call_data.get("from", "")
        to_number = call_data.get("to", "")

        # Create call log entry in DB (non-blocking — runs in background)
        import asyncio
        call_log_state = {"id": None, "done": False}
        call_log_ready = asyncio.Event()
        audio_buffer = None
        transcript_entries: list[dict] = []
        call_log_updated = {"done": False}

        async def _get_call_log_id() -> int | None:
            """Await until call_log_id is available, then return it."""
            await call_log_ready.wait()
            return call_log_state["id"]

        if agent:
            def _create_call_log_in_thread():
                """Run in a thread so synchronous DB work doesn't block the event loop."""
                try:
                    _t = _time.monotonic()
                    with get_db_context() as db:
                        call_log = CallLogService(db).create_call_log(
                            agent_id=agent.id,
                            organization_id=agent.organization_id,
                            provider_call_id=provider_call_id,
                            transport_type=transport_type,
                            from_number=from_number,
                            to_number=to_number,
                        )
                        call_log_state["id"] = call_log.id
                        logger.info("[TIMING] create_call_log thread (+%.3fs)", _time.monotonic() - _t)
                except Exception as e:
                    logger.error("Failed to create call log: {}", e)
                finally:
                    loop.call_soon_threadsafe(call_log_ready.set)

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _create_call_log_in_thread)

            # Pipecat's built-in AudioBufferProcessor for recording
            audio_buffer = AudioBufferProcessor(sample_rate=16000, num_channels=1)

            # Save audio + update DB inside this event handler.
            # This runs DURING pipeline lifecycle (before cleanup() returns),
            # guaranteeing completion before the subprocess can be terminated.
            @audio_buffer.event_handler("on_audio_data")
            async def on_audio_data(processor, audio, sample_rate, num_channels):
                import asyncio

                # Yield to let pending transcript event handlers complete first
                await asyncio.sleep(0)

                # Wait for background call log creation to finish
                call_log_id = await _get_call_log_id()

                if not audio or len(audio) == 0:
                    logger.warning("on_audio_data called with empty audio for call_log_id={}", call_log_id)
                    return

                logger.info("on_audio_data: {} bytes, {}Hz, {}ch", len(audio), sample_rate, num_channels)

                # Convert raw audio to MP3
                audio_bytes = None
                file_name = None
                try:
                    audio_segment = AudioSegment(
                        data=audio,
                        sample_width=2,
                        frame_rate=sample_rate,
                        channels=num_channels,
                    )
                    agent_uuid_str = str(agent.uuid) if hasattr(agent, 'uuid') else str(agent.id)
                    call_id_str = provider_call_id or str(int(_time.time()))
                    file_name = f"{call_id_str}.mp3"

                    mp3_buffer = io.BytesIO()
                    audio_segment.export(mp3_buffer, format="mp3")
                    audio_bytes = mp3_buffer.getvalue()
                    logger.info("Encoded call recording: {} ({:.1f}s, {} bytes)", file_name, len(audio_segment) / 1000, len(audio_bytes))
                except Exception as e:
                    logger.error("Failed to encode call recording: {}", e)

                # Upload to Cloudflare R2 and update DB
                if call_log_id:
                    upload_id = None
                    r2_object_key = None
                    if audio_bytes and file_name:
                        try:
                            from core.services.r2_storage_service import \
                                R2StorageService
                            r2 = R2StorageService()
                            r2_object_key = f"{agent_uuid_str}/{file_name}"
                            r2.upload_file(audio_bytes, r2_object_key, content_type="audio/mpeg")

                            with get_db_context() as db:
                                upload = CallLogService(db).create_upload(
                                    r2_object_key=r2_object_key,
                                    agent_id=agent.id,
                                    organization_id=agent.organization_id,
                                    call_log_id=call_log_id,
                                    file_name=file_name,
                                    content_type="audio/mpeg",
                                    file_size_bytes=len(audio_bytes),
                                )
                                upload_id = upload.id
                            logger.info("Audio uploaded to R2: key={} upload_id={}", r2_object_key, upload_id)
                        except Exception as e:
                            logger.error("Failed to upload audio to R2: {}", e)

                    try:
                        transcript_data = transcript_entries if transcript_entries else None

                        collected_metrics = metrics_collector.get_collected_metrics()
                        collected_metrics["user_bot_latency"] = [
                            {"latency": round(l, 3)} for l in latency_observer._latencies
                        ]
                        collected_metrics["turns"] = turn_entries
                        with get_db_context() as db:
                            CallLogService(db).complete_call(
                                call_log_id=call_log_id,
                                audio_file_path=r2_object_key,
                                upload_id=upload_id,
                                transcript=transcript_data,
                                metrics=collected_metrics,
                            )
                        call_log_updated["done"] = True
                        logger.info(
                            "Call log completed: id={} r2_key={} transcript_entries={} metrics_collected={}",
                            call_log_id,
                            r2_object_key,
                            len(transcript_data) if transcript_data else 0,
                            {k: len(v) for k, v in collected_metrics.items()},
                        )
                    except Exception as e:
                        logger.error("Failed to complete call log in on_audio_data: {}", e)
        else:
            call_log_ready.set()

        _t = _time.monotonic()
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        # Register document tool if agent has uploaded documents
        doc_tools = None
        if agent:
            from core.services.document_tool_service import \
                register_document_tool
            doc_tools = register_document_tool(llm, agent.id, agent.organization_id)

        # Fetch custom tools for this agent
        custom_tools_schema = None
        if agent:
            from core.services.custom_tool_service import (
                get_custom_tools_for_agent,
                build_custom_tool_schemas,
                create_custom_tool_handler,
            )
            custom_tools = get_custom_tools_for_agent(agent.id)
            if custom_tools:
                logger.info("Fetched {} custom tools for agent {}", len(custom_tools), agent.id)
                custom_tools_schema = build_custom_tool_schemas(custom_tools)
                for tool in custom_tools:
                    handler = create_custom_tool_handler(tool)
                    llm.register_function(tool.name, handler)
                    logger.info("Registered custom tool handler: {}", tool.name)

        # Combine doc tools and custom tools into one ToolsSchema
        all_tool_schemas = []
        if doc_tools:
            all_tool_schemas.extend(doc_tools.standard_tools)
        if custom_tools_schema:
            all_tool_schemas.extend(custom_tools_schema.standard_tools)

        if all_tool_schemas:
            from pipecat.adapters.schemas.tools_schema import ToolsSchema
            combined_tools = ToolsSchema(standard_tools=all_tool_schemas)
        else:
            combined_tools = NOT_GIVEN

        if is_s2s:
            # S2S pipeline: audio goes through the LLM directly (no separate STT/TTS)
            # But still needs context aggregators for conversation tracking
            logger.info("Building S2S pipeline (speech-to-speech)")
            from pipecat.frames.frames import LLMRunFrame

            tools = combined_tools
            # For S2S, the first message in context triggers the initial response
            # System prompt is already set via session_properties.instructions (OpenAI)
            # or system_instruction (Gemini) during LLM creation
            context = LLMContext(messages, tools)
            context_aggregator = LLMContextAggregatorPair(context)
            s2s_user_aggregator = context_aggregator.user()
            s2s_assistant_aggregator = context_aggregator.assistant()

            # Build pipeline: input → user_agg → llm → output → assistant_agg
            pipeline_processors = [
                transport.input(),
                rtvi,
                s2s_user_aggregator,
                llm,
                transport.output(),
                s2s_assistant_aggregator,
            ]

            # Collect transcripts via aggregator events (same as standard pipeline)
            if agent:
                @s2s_user_aggregator.event_handler("on_user_turn_stopped")
                async def on_s2s_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
                    transcript_entries.append({
                        "role": "user",
                        "text": message.content,
                        "timestamp": message.timestamp,
                    })

                @s2s_assistant_aggregator.event_handler("on_assistant_turn_stopped")
                async def on_s2s_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
                    transcript_entries.append({
                        "role": "assistant",
                        "text": message.content,
                        "timestamp": message.timestamp,
                    })

            logger.info("[TIMING] S2S pipeline processors created (+%.3fs)", _time.monotonic() - _t)
        else:
            # Standard pipeline: STT → LLM → TTS
            tools = combined_tools
            context = LLMContext(messages, tools)
            smart_turn_analyzer = LocalSmartTurnAnalyzerV3(
                confidence_threshold=0.9,
                params=SmartTurnParams(stop_secs=0.4),
            )
            context_aggregator = LLMContextAggregatorPair(
                context,
                user_params=LLMUserAggregatorParams(
                    user_turn_strategies=UserTurnStrategies(
                        stop=[TurnAnalyzerUserTurnStopStrategy(turn_analyzer=smart_turn_analyzer)]
                    ),
                ),
            )
            user_aggregator = context_aggregator.user()
            assistant_aggregator = context_aggregator.assistant()
            llm_text_processor = LLMTextProcessor()
            # Use passed end_call_message; only query DB if not provided, agent exists, and DB is available
            if end_call_message is None and agent and self.db is not None:
                agent_config = self._get_agent_config(agent)
                if agent_config:
                    end_call_message = agent_config.end_call_message
            call_end_detector = CallEndDetectorProcessor(end_call_message=end_call_message)
            logger.info("[TIMING] context + aggregators + processors created (+%.3fs)", _time.monotonic() - _t)

            # Collect transcripts via Pipecat's built-in aggregator events
            if agent:
                @user_aggregator.event_handler("on_user_turn_stopped")
                async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
                    transcript_entries.append({
                        "role": "user",
                        "text": message.content,
                        "timestamp": message.timestamp,
                    })

                @assistant_aggregator.event_handler("on_assistant_turn_stopped")
                async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
                    transcript_entries.append({
                        "role": "assistant",
                        "text": message.content,
                        "timestamp": message.timestamp,
                    })

            # Build pipeline
            pipeline_processors = [transport.input()]

            pipeline_processors.extend([
                rtvi,
                stt,
                call_end_detector,
                user_aggregator,
                llm,
                llm_text_processor,
                tts,
                transport.output(),
                assistant_aggregator,
            ])

        # MetricsCollectorProcessor collects metrics for DB storage
        metrics_collector = MetricsCollectorProcessor()
        pipeline_processors.append(metrics_collector)

        # AudioBufferProcessor sees both InputAudioRawFrame and OutputAudioRawFrame
        # when placed at the end of the pipeline
        if audio_buffer:
            pipeline_processors.append(audio_buffer)

        _t = _time.monotonic()
        pipeline = Pipeline(pipeline_processors)

        # Observers for metrics, latency, and turn tracking
        from pipecat.observers.loggers.metrics_log_observer import \
            MetricsLogObserver
        from pipecat.observers.turn_tracking_observer import \
            TurnTrackingObserver

        from core.observers.user_bot_latency_observer import \
            UserBotLatencyObserver

        metrics_observer = MetricsLogObserver()
        latency_observer = UserBotLatencyObserver()
        turn_observer = TurnTrackingObserver()
        turn_entries: list[dict] = []

        @turn_observer.event_handler("on_turn_started")
        async def on_turn_started(observer, turn_number):
            logger.info("Turn {} started", turn_number)

        @turn_observer.event_handler("on_turn_ended")
        async def on_turn_ended(observer, turn_number, duration, was_interrupted):
            status = "interrupted" if was_interrupted else "completed"
            logger.info("Turn {} {} after {:.2f}s", turn_number, status, duration)
            turn_entries.append({
                "turn": turn_number,
                "duration": round(duration, 3),
                "status": status,
            })

        # Use the TTS service's native sample rate so the output transport
        # tags audio frames correctly for the serializer (e.g. Hume @ 48 kHz).
        # S2S models output 24kHz audio by default.
        tts_sample_rate = 24000
        if not is_s2s and tts:
            tts_sample_rate = getattr(tts, "_init_sample_rate", None) or 24000

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
                audio_out_sample_rate=tts_sample_rate,
            ),
            observers=[
                RTVIObserver(rtvi),
                metrics_observer,
                latency_observer,
                turn_observer,
            ],
        )
        logger.info("[TIMING] Pipeline + PipelineTask created (+%.3fs)", _time.monotonic() - _t)

        # Extract first_message from messages to speak via TTS on connect
        first_message_text = None
        if len(messages) > 1 and messages[-1].get("role") == "assistant":
            first_message_text = messages[-1].get("content", "").strip()

        # Start recording and speak first_message when client connects
        if audio_buffer:
            @transport.event_handler("on_client_connected")
            async def on_client_connected(transport, client):
                logger.info("Client connected — starting audio recording.")
                await audio_buffer.start_recording()
                if is_s2s:
                    # S2S: kick off the conversation — context already has the messages
                    from pipecat.frames.frames import LLMRunFrame
                    logger.info("Kicking off S2S conversation via LLMRunFrame")
                    await task.queue_frames([LLMRunFrame()])
                elif first_message_text:
                    from pipecat.frames.frames import TTSSpeakFrame
                    logger.info("Speaking first_message via TTS: {}", first_message_text)
                    await task.queue_frame(TTSSpeakFrame(text=first_message_text))
        else:
            @transport.event_handler("on_client_connected")
            async def on_client_connected(transport, client):
                logger.info("Client connected.")
                if is_s2s:
                    from pipecat.frames.frames import LLMRunFrame
                    logger.info("Kicking off S2S conversation via LLMRunFrame")
                    await task.queue_frames([LLMRunFrame()])
                elif first_message_text:
                    from pipecat.frames.frames import TTSSpeakFrame
                    logger.info("Speaking first_message via TTS: {}", first_message_text)
                    await task.queue_frame(TTSSpeakFrame(text=first_message_text))

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            logger.debug("Client ready event received")
            await rtvi.set_bot_ready()

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, participant):
            logger.info("Client disconnected: {}", participant)
            await task.cancel()

        logger.info("[TIMING] run_bot_with_components setup complete, total: %.3fs — starting runner.run()", _time.monotonic() - _t_comp_start)
        runner = PipelineRunner(handle_sigint=getattr(runner_args, "handle_sigint", False))
        await runner.run(task)

        # Fallback: if on_audio_data didn't update DB (e.g. no audio captured),
        # update the call log here with whatever we have.
        call_log_id = await _get_call_log_id()
        if call_log_id and agent and not call_log_updated["done"]:
            logger.info("on_audio_data did not complete DB update, running fallback for call_log_id={}", call_log_id)
            try:
                transcript_data = transcript_entries if transcript_entries else None

                collected_metrics = metrics_collector.get_collected_metrics()
                with get_db_context() as db:
                    CallLogService(db).complete_call(
                        call_log_id=call_log_id,
                        audio_file_path=None,
                        transcript=transcript_data,
                        metrics=collected_metrics,
                    )
                logger.info("Call log completed (fallback): id={}", call_log_id)
            except Exception as e:
                logger.error("Failed to complete call log id={}: {}", call_log_id, e)
                try:
                    with get_db_context() as db:
                        CallLogService(db).fail_call(call_log_id)
                except Exception:
                    pass

    async def run_bot_for_agent(
        self, agent: Any, transport: Any, runner_args: Any
    ) -> None:
        """
        Get all agent data (llm, stt, tts, prompt) from config and run the bot pipeline.
        Raises ValueError if agent has no config or missing services.
        """
        _t0 = _time.monotonic()
        # Use pre-fetched service data from main process if available (subprocess path)
        body = getattr(runner_args, "body", None) or {}
        prefetched = body.get("_prefetched_services")
        data = self.get_agent_bot_data(agent, prefetched=prefetched)
        logger.info("[TIMING] run_bot_for_agent: get_agent_bot_data (+%.3fs)", _time.monotonic() - _t0)
        if not data:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        _t = _time.monotonic()
        await self.run_bot_with_components(
            transport=transport,
            runner_args=runner_args,
            llm=data["llm"],
            stt=data["stt"],
            tts=data["tts"],
            messages=data["messages"],
            agent=agent,
            end_call_message=data.get("end_call_message"),
            is_s2s=data.get("is_s2s", False),
        )
        logger.info("[TIMING] run_bot_for_agent: run_bot_with_components (+%.3fs), total: %.3fs", _time.monotonic() - _t, _time.monotonic() - _t0)


      