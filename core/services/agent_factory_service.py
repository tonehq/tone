"""Factory to build LLM, STT, and TTS instances from an agent's config and run the bot pipeline."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


from typing import Any, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.models import Model
from core.models.service_provider import ServiceProvider
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
        self, service_provider_id: Optional[int], service_type: str
    ) -> Optional[Tuple[Model, ServiceProvider, str]]:
        """
        Get the first active Model for the given provider and type, plus decrypted API key.
        Returns (Model, ServiceProvider, decrypted_api_key) or None.
        """
        if not service_provider_id:
            return None
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
            return None
        svc, provider = result
        api_key_value = None
        if svc.api_key_id:
            api_key = self.db.query(ApiKey).filter(ApiKey.id == svc.api_key_id).first()
            if api_key and api_key.api_key_encrypted:
                try:
                    api_key_value = decrypt(api_key.api_key_encrypted)
                except Exception as e:
                    logger.warning("Failed to decrypt API key for model %s: %s", svc.id, e)
        if not api_key_value:
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
        filtered = {k: v for k, v in metadata.items() if k in valid_keys and v is not None}
        if not filtered:
            return input_params_class()
        try:
            return input_params_class(**filtered)
        except Exception as e:
            logger.warning("Failed to build InputParams for %s: %s", service_class.__name__, e)
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

    def get_llm_for_agent(self, agent: Any) -> Optional[Any]:
        """
        Build and return the LLM service instance for the given agent.
        Uses agent config's llm_service_id (service_provider) and llm_metadata.
        Returns None if config or credentials are missing or provider is unsupported.
        """
        config = self._get_agent_config(agent)

        if not config or not config.llm_service_id:
            return None
        result = self._get_service_and_credentials(config.llm_service_id, "llm")
        if not result:
            return None

        svc, provider, api_key = result
        metadata = (config.llm_metadata or {}) if hasattr(config, "llm_metadata") else {}
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        # Resolve model name from model_id in llm_metadata; None if not present
        model = self._get_model_name_by_id(metadata.get("model_id"))
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "openai": #done
                from pipecat.services.openai.llm import OpenAILLMService
                return OpenAILLMService(api_key = api_key, model=model or "gpt-4.1", params=self._build_input_params(OpenAILLMService, metadata))
            if provider_name == "anthropic": #done
                from pipecat.services.anthropic.llm import AnthropicLLMService
                return AnthropicLLMService(api_key=api_key, model= model or "claude-sonnet-4-5-20250929", params=self._build_input_params(AnthropicLLMService, metadata))
            if provider_name == "groq": #done
                from pipecat.services.groq.llm import GroqLLMService
                return GroqLLMService(api_key=api_key, model=model or "llama-3.3-70b-versatile", params=self._build_input_params(GroqLLMService, metadata))
            if provider_name == "openrouter": #done
                from pipecat.services.openrouter.llm import OpenRouterLLMService
                return OpenRouterLLMService(api_key=api_key, model= model or "openai/gpt-4o-2024-11-20", params=self._build_input_params(OpenRouterLLMService, metadata))
            if provider_name == "aws_bedrock": #done
                from pipecat.services.aws.llm import AWSBedrockLLMService
                return AWSBedrockLLMService(api_key=api_key, model=model or "amazon.nova-pro-v1:0", params=self._build_input_params(AWSBedrockLLMService, metadata))
            if provider_name == "google": #Done
                from pipecat.services.google.llm import GoogleLLMService
                return GoogleLLMService(api_key=api_key, model=model or "gemini-2.5-flash", params=self._build_input_params(GoogleLLMService, metadata))
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
            return None
        except ImportError as e:
            logger.exception("LLM provider %s not available", provider_name)
            return None


    def get_stt_for_agent(self, agent: Any) -> Optional[Any]:
        """
        Build and return the STT service instance for the given agent.
        Uses agent config's stt_service_id and stt_metadata.
        Returns None if config or credentials are missing or provider is unsupported.
        """
        config = self._get_agent_config(agent)
        if not config or not config.stt_service_id:
            return None
        result = self._get_service_and_credentials(config.stt_service_id, "stt")
        if not result:
            return None
        svc, provider, api_key = result
        metadata = (config.stt_metadata or {}) if hasattr(config, "stt_metadata") else {}
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        # Resolve model name from model_id in stt_metadata; None if not present
        model = self._get_model_name_by_id(metadata.get("model_id"))
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "deepgram":
                from pipecat.services.deepgram.stt import DeepgramSTTService
                return DeepgramSTTService(api_key=api_key)
            if provider_name == "openai":
                from pipecat.services.openai.stt import OpenAISTTService
                return OpenAISTTService(api_key=api_key, model=model or "gpt-4o-transcribe")
            if provider_name == "groq":
                from pipecat.services.groq.stt import GroqSTTService
                return GroqSTTService(api_key=api_key, model=model or "whisper-large-v3-turbo")
            if provider_name == "azure":
                from pipecat.services.azure.stt import AzureSTTService
                region = model_meta.get("region") or metadata.get("region") or "eastus"
                return AzureSTTService(api_key=api_key, region=region)
            if provider_name == "google":
                from pipecat.services.google.stt import GoogleSTTService
                return GoogleSTTService(credentials=api_key, params=self._build_input_params(GoogleSTTService, metadata))
            if provider_name == "nvidia":
                from pipecat.services.nvidia.stt import NvidiaSTTService
                return NvidiaSTTService(api_key=api_key, params=self._build_input_params(NvidiaSTTService, metadata))
            if provider_name == "sarvam":
                from pipecat.services.sarvam.stt import SarvamSTTService
                return SarvamSTTService(api_key=api_key, model=model or "saarika:v2.5", params=self._build_input_params(SarvamSTTService, metadata))
            if provider_name == "speechmatics":
                from pipecat.services.speechmatics.stt import SpeechmaticsSTTService
                return SpeechmaticsSTTService(api_key=api_key, params=self._build_input_params(SpeechmaticsSTTService, metadata))
            if provider_name == "assemblyai":
                from pipecat.services.assemblyai.stt import AssemblyAISTTService
                return AssemblyAISTTService(api_key=api_key)
            if provider_name == "cartesia":
                from pipecat.services.cartesia.stt import CartesiaSTTService
                return CartesiaSTTService(api_key=api_key)
            if provider_name == "elevenlabs":
                from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
                return ElevenLabsRealtimeSTTService(api_key=api_key, model=model or "scribe_v2_realtime", params=self._build_input_params(ElevenLabsRealtimeSTTService, metadata))
            if provider_name == "gladia":
                from pipecat.services.gladia.stt import GladiaSTTService
                return GladiaSTTService(api_key=api_key, model=model or "solaria-1", params=self._build_input_params(GladiaSTTService, metadata))
            if provider_name == "soniox":
                from pipecat.services.soniox.stt import SonioxSTTService
                return SonioxSTTService(api_key=api_key, params=self._build_input_params(SonioxSTTService, metadata))
            if provider_name == "hathora":
                from pipecat.services.hathora.stt import HathoraSTTService
                return HathoraSTTService(api_key=api_key, model=model or "parakeet", params=self._build_input_params(HathoraSTTService, metadata))
            if provider_name == "sambanova":
                from pipecat.services.sambanova.stt import SambaNovaSTTService
                return SambaNovaSTTService(api_key=api_key, model=model or "Whisper-Large-v3")
            logger.warning("Unsupported STT provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("STT provider %s not available: %s", provider_name, e)
            return None

    def get_tts_for_agent(self, agent: Any) -> Optional[Any]:
        print("into get_tts_for_agent")
        """
        Build and return the TTS service instance for the given agent.
        Uses agent config's tts_service_id and tts_metadata.
        Returns None if config or credentials are missing or provider is unsupported.
        """
        config = self._get_agent_config(agent)
        if not config or not config.tts_service_id:
            return None
        result = self._get_service_and_credentials(config.tts_service_id, "tts")
        if not result:
            return None
        svc, provider, api_key = result
        metadata = (config.tts_metadata or {}) if hasattr(config, "tts_metadata") else {}
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        tts_voice_id = metadata.get("voice_id")
        tts_language = metadata.get("language")
        provider_name = (provider.name or "").strip().lower()

        # Resolve model name from model_id in tts_metadata; None if not present
        model = self._get_model_name_by_id(metadata.get("model_id"))

        import aiohttp
        session = aiohttp.ClientSession()
        # session = None

        try:
            if provider_name == "cartesia":
                from pipecat.services.cartesia.tts import CartesiaTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
                
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language or "en"
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return CartesiaTTSService(api_key=api_key, params=self._build_input_params(CartesiaTTSService, metadata), **voice_kwargs)
            if provider_name == "openai":
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
                from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id or "CwhRBWXzGAHq8TQ4Fs17"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language or "en"
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return ElevenLabsTTSService(api_key=api_key, params=self._build_input_params(ElevenLabsTTSService, metadata), **voice_kwargs)
            if provider_name == "playht":
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
            if provider_name == "asyncai_http":
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
            if provider_name == "aws_polly":
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
            if provider_name == "camb":
                from pipecat.services.camb.tts import CambTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return CambTTSService(api_key=api_key, params=self._build_input_params(CambTTSService, metadata), **voice_kwargs)
            if provider_name == "deepgram":
                from pipecat.services.deepgram.tts import DeepgramHttpTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return DeepgramHttpTTSService(api_key=api_key, aiohttp_session = session, **voice_kwargs)
            if provider_name == "google_base":
                # To check this fully
                from pipecat.services.google.tts import GoogleBaseTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return GoogleBaseTTSService(credentials=api_key, params=self._build_input_params(GoogleBaseTTSService, metadata), **voice_kwargs)
            if provider_name == "groq":
                from pipecat.services.groq.tts import GroqTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return GroqTTSService(api_key=api_key, params=self._build_input_params(GroqTTSService, metadata), **voice_kwargs)
            if provider_name == "hathora":
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
                return HathoraTTSService(api_key=api_key, model=model or "sonic-2025-04-16", params=self._build_input_params(HathoraTTSService, metadata), **voice_kwargs)
            if provider_name == "minimax":
                # To check group id in this
                from pipecat.services.minimax.tts import MiniMaxHttpTTSService
                group_id = model_meta.get("group_id") or metadata.get("group_id") or ""
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return MiniMaxHttpTTSService(api_key=api_key, group_id=group_id, aiohttp_session=session, params=self._build_input_params(MiniMaxHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "neuphonic":
                # To check language
                from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id or "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return NeuphonicHttpTTSService(api_key=api_key, aiohttp_session=session, params=self._build_input_params(NeuphonicHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "nvidia":
                from pipecat.services.nvidia.tts import NvidiaTTSService
                server = model_meta.get("server") or metadata.get("server") or "grpc.nvcf.nvidia.com:443"
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return NvidiaTTSService(api_key=api_key, server=server, params=self._build_input_params(NvidiaTTSService, metadata), **voice_kwargs)
            if provider_name == "rime":
                from pipecat.services.rime.tts import RimeHttpTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "albion"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return RimeHttpTTSService(api_key=api_key, aiohttp_session=session, params=self._build_input_params(RimeHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "sarvam":
                from pipecat.services.sarvam.tts import SarvamHttpTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return SarvamHttpTTSService(api_key=api_key, aiohttp_session=session, params=self._build_input_params(SarvamHttpTTSService, metadata), **voice_kwargs)
            if provider_name == "speechmatics":
                from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
                voice_kwargs = {}
                if tts_voice_id is not None:
                    voice_kwargs["voice_id"] = tts_voice_id
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return SpeechmaticsTTSService(api_key=api_key, aiohttp_session=session, params=self._build_input_params(SpeechmaticsTTSService, metadata), **voice_kwargs)
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
                return HumeTTSService(api_key=api_key, params=self._build_input_params(HumeTTSService, metadata), **voice_kwargs)
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
                return InworldTTSService(api_key=api_key, params=self._build_input_params(InworldTTSService, metadata), **voice_kwargs)
            if provider_name == "lmnt":
                from pipecat.services.lmnt.tts import LmntTTSService
                voice_kwargs = {}
                voice_kwargs["voice_id"] = tts_voice_id or "ava"

                if tts_language is not None:
                    voice_kwargs["language"] = tts_language

                return LmntTTSService(api_key=api_key, **voice_kwargs)
            if provider_name == "resemble":
                # Need to check voices
                from pipecat.services.resembleai.tts import ResembleAITTSService
                voice_kwargs = {}

                voice_kwargs["voice_id"] = tts_voice_id
                
                if tts_language is not None:
                    voice_kwargs["language"] = tts_language
                else:
                    voice_kwargs["language"] = None
                print(f"[TTS {provider_name}] voice_kwargs: {voice_kwargs}")
                return ResembleAITTSService(api_key=api_key, **voice_kwargs)

            logger.warning("Unsupported TTS provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("TTS provider %s not available: %s", provider_name, e)
            return None

    def get_agent_bot_data(self, agent: Any) -> Optional[dict]:
        """
        Get all data needed to run the bot for an agent: llm, stt, tts, and messages
        (system_prompt, optional first_message) from agent config.
        Returns None if config or any required service is missing.
        """
        config = self._get_agent_config(agent)
        if not config or not config.system_prompt:
            return None
        llm = self.get_llm_for_agent(agent)
        stt = self.get_stt_for_agent(agent)
        tts = self.get_tts_for_agent(agent)
        if not llm or not stt or not tts:
            return None
        messages: List[dict] = [{"role": "system", "content": config.system_prompt}]
        if getattr(config, "first_message", None) and config.first_message.strip():
            messages.append({"role": "assistant", "content": config.first_message.strip()})
        return {
            "llm": llm,
            "stt": stt,
            "tts": tts,
            "messages": messages,
            "config": config,
        }

    async def run_bot_with_components(
        self,
        transport: Any,
        runner_args: Any,
        llm: Any,
        stt: Any,
        tts: Any,
        messages: List[dict],
    ) -> None:
        """
        Run the voice pipeline with the given transport and services.
        Called by run_bot_for_agent or from bot.py with default components.
        """

        from pipecat.processors.aggregators.llm_context import NOT_GIVEN
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair,
        )
        from pipecat.processors.aggregators.llm_text_processor import (
            LLMTextProcessor,
        )
        from pipecat.processors.frameworks.rtvi import (
            RTVIConfig,
            RTVIObserver,
            RTVIProcessor,
        )
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask


        tools = NOT_GIVEN
        context = LLMContext(messages, tools)
        context_aggregator = LLMContextAggregatorPair(context)
        llm_text_processor = LLMTextProcessor()
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))


        pipeline = Pipeline(
            [
                transport.input(),
                rtvi,
                stt,
                context_aggregator.user(),
                llm,
                llm_text_processor,
                tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )


        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            observers=[RTVIObserver(rtvi)],
        )

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            logger.debug("Client ready event received")
            await rtvi.set_bot_ready()

        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("Client connected.")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, participant):
            logger.info("Client disconnected: {}", participant)
            await task.cancel()

        runner = PipelineRunner(handle_sigint=getattr(runner_args, "handle_sigint", False))
        await runner.run(task)

    async def run_bot_for_agent(
        self, agent: Any, transport: Any, runner_args: Any
    ) -> None:
        """
        Get all agent data (llm, stt, tts, prompt) from config and run the bot pipeline.
        Raises ValueError if agent has no config or missing services.
        """
        data = self.get_agent_bot_data(agent)
        if not data:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        await self.run_bot_with_components(
            transport=transport,
            runner_args=runner_args,
            llm=data["llm"],
            stt=data["stt"],
            tts=data["tts"],
            messages=data["messages"],
        )


      