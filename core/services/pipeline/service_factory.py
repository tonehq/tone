"""Pure provider-switch factories that build Pipecat LLM/STT/TTS services from a resolved spec.

These functions contain NO database access. They take an already-resolved service spec
(provider_name, api_key, model_name, metadata, model_meta_data) — the same shape produced
by `service_resolver.load_agent_service_config` / the Redis-cached prefetch dict — and return
the constructed Pipecat service instance (or None on unsupported/failed init).
"""

import json
from typing import Any, Optional

from loguru import logger


def _url_kwargs(metadata: dict, kwarg: str = "base_url") -> dict:
    """Return splat-style URL kwargs for a Pipecat constructor.

    If `metadata["base_url"]` is set (because `Model.base_url` is populated in the DB),
    return `{kwarg: url}` to splat into the constructor. Otherwise return `{}` so the
    Pipecat class falls back to its own hardcoded default — preserving today's behavior
    for any model without a URL.

    `kwarg` picks the constructor parameter name. Pipecat is inconsistent: most providers
    use `base_url`, several use `url`, AssemblyAI uses `api_endpoint_base_url`, NVIDIA STT
    uses `server`. Each call site passes the right name for its provider.
    """
    url = metadata.get("base_url")
    return {kwarg: url} if url else {}


def build_input_params(service_class, metadata: dict):
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


def build_llm(spec: dict) -> Optional[Any]:
    """Build an LLM service instance from a resolved spec dict.

    spec = {provider_name, api_key, model_name, metadata, model_meta_data}
    """
    provider_name = spec["provider_name"]
    api_key = spec["api_key"]
    model = spec["model_name"]
    metadata = spec["metadata"]
    model_meta = spec["model_meta_data"]

    try:
        if provider_name == "openai":  # done
            from pipecat.services.openai.llm import OpenAILLMService
            return OpenAILLMService(api_key=api_key, model=model or "gpt-4.1", params=build_input_params(OpenAILLMService, metadata), **_url_kwargs(metadata))
        if provider_name == "anthropic":  # done
            from pipecat.services.anthropic.llm import AnthropicLLMService
            if "enable_prompt_caching" not in metadata:
                metadata["enable_prompt_caching"] = True
            params = build_input_params(AnthropicLLMService, metadata)
            return AnthropicLLMService(api_key=api_key, model=model or "claude-haiku-4-5-20251001", params=params)
        if provider_name == "groq":  # done
            from pipecat.services.groq.llm import GroqLLMService
            return GroqLLMService(api_key=api_key, model=model or "llama-3.3-70b-versatile", params=build_input_params(GroqLLMService, metadata), **_url_kwargs(metadata))
        if provider_name == "openrouter":  # done
            from pipecat.services.openrouter.llm import OpenRouterLLMService
            return OpenRouterLLMService(api_key=api_key, model=model or "openai/gpt-4o-2024-11-20", params=build_input_params(OpenRouterLLMService, metadata), **_url_kwargs(metadata))
        if provider_name == "aws_bedrock":  # done
            from pipecat.services.aws.llm import AWSBedrockLLMService
            return AWSBedrockLLMService(api_key=api_key, model=model or "amazon.nova-pro-v1:0", params=build_input_params(AWSBedrockLLMService, metadata))
        if provider_name == "google":  # Done
            from pipecat.services.google.llm import GoogleLLMService
            params = build_input_params(GoogleLLMService, metadata)
            return GoogleLLMService(api_key=api_key, model=model or "gemini-2.5-flash", params=params)
        if provider_name == "ollama":  # done
            from pipecat.services.ollama.llm import OLLamaLLMService
            base_url = api_key if api_key else "http://localhost:11434/v1"
            return OLLamaLLMService(model=model or "llama2", base_url=base_url, params=build_input_params(OLLamaLLMService, metadata))
        if provider_name in ["azure", "cerebras", "nvidia_nim", "fireworks", "together", "perplexity", "qwen", "deepseek", "mistral", "sambanova", "grok", "cohere"]:
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
                "cohere": "command-a-03-2025",
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
                "cohere": "https://api.cohere.ai/compatibility/v1",
            }
            if not base_url:
                base_url = default_base_urls.get(provider_name)
            default_model = default_models.get(provider_name, "gpt-4o")
            return BaseOpenAILLMService(api_key=api_key, model=model or default_model, base_url=base_url, params=build_input_params(BaseOpenAILLMService, metadata))
        if provider_name == "openai_realtime":
            from pipecat.services.openai.realtime.events import (
                AudioConfiguration, AudioInput, AudioOutput,
                InputAudioTranscription, SemanticTurnDetection,
                SessionProperties)
            from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
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
            from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
            voice_id = metadata.get("voice_id") or "Puck"
            return GeminiLiveLLMService(
                api_key=api_key,
                model=model or "models/gemini-2.5-flash-native-audio-preview-12-2025",
                voice_id=voice_id,
                system_instruction=metadata.get("system_instruction"),
            )
        logger.warning("No matching LLM provider for '%s'", provider_name)
        return None
    except ImportError:
        logger.exception("LLM provider %s not available (ImportError)", provider_name)
        return None
    except Exception as e:
        logger.exception("LLM provider %s failed to initialize: %s", provider_name, e)
        return None


def build_stt(spec: dict) -> Optional[Any]:
    """Build an STT service instance from a resolved spec dict."""
    provider_name = spec["provider_name"]
    api_key = spec["api_key"]
    model = spec["model_name"]
    metadata = spec["metadata"]
    model_meta = spec["model_meta_data"]

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
            return DeepgramSTTService(api_key=api_key, live_options=live_options, **dg_kwargs, **_url_kwargs(metadata))
        if provider_name == "openai":
            from pipecat.services.openai.stt import OpenAISTTService
            return OpenAISTTService(
                api_key=api_key,
                model=model or "gpt-4o-transcribe",
                language=metadata.get("language"),
                prompt=metadata.get("prompt"),
                temperature=metadata.get("temperature"),
            )
        if provider_name == "voxtral":
            # Self-hosted Voxtral via the custom transformers server, which speaks
            # the same /ws/asr protocol as nemotron — so we reuse NvidiaWebSocketService.
            from pipecat.services.nvidia.websocket_stt import NvidiaWebSocketService
            from core.logging import get_trace_id
            ws_url = "ws://staging-stt-voxtral-service.staging.svc.cluster.local/ws/asr"
            ws_kwargs = {}
            if metadata.get("sample_rate") is not None:
                ws_kwargs["sample_rate"] = metadata["sample_rate"]
            return NvidiaWebSocketService(url=ws_url, trace_id=get_trace_id(), **ws_kwargs)
        if provider_name == "gemma":
            # Self-hosted Gemma 4 E2B ASR via the custom transformers server, which speaks
            # the same /ws/asr protocol as nemotron — so we reuse NvidiaWebSocketService.
            from pipecat.services.nvidia.websocket_stt import NvidiaWebSocketService
            from core.logging import get_trace_id
            ws_url = "ws://staging-stt-gemma-service.staging.svc.cluster.local/ws/asr"
            ws_kwargs = {}
            if metadata.get("sample_rate") is not None:
                ws_kwargs["sample_rate"] = metadata["sample_rate"]
            return NvidiaWebSocketService(url=ws_url, trace_id=get_trace_id(), **ws_kwargs)
        if provider_name == "groq":
            from pipecat.services.groq.stt import GroqSTTService
            return GroqSTTService(
                api_key=api_key,
                model=model or "whisper-large-v3-turbo",
                language=metadata.get("language"),
                prompt=metadata.get("prompt"),
                temperature=metadata.get("temperature"),
                **_url_kwargs(metadata),
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
            return GoogleSTTService(credentials=api_key, params=build_input_params(GoogleSTTService, metadata))
        if provider_name == "nvidia":
            from pipecat.services.nvidia.stt import NvidiaSTTService
            return NvidiaSTTService(api_key=api_key, params=build_input_params(NvidiaSTTService, metadata))
        if provider_name == "nvidia_sage":
            from pipecat.services.stt_service import WebsocketSTTService
            return NvidiaSageMakerSTTService(api_key=api_key, params=build_input_params(NvidiaSageMakerSTTService, metadata))
        if provider_name == "nvidia_websocket":
            from pipecat.services.nvidia.websocket_stt import NvidiaWebSocketService
            from core.logging import get_trace_id
            ws_url = "ws://staging-stt-nemotron-service.staging.svc.cluster.local/ws/asr"
            ws_kwargs = {}
            if metadata.get("sample_rate") is not None:
                ws_kwargs["sample_rate"] = metadata["sample_rate"]
            return NvidiaWebSocketService(url=ws_url, trace_id=get_trace_id(), **ws_kwargs)
        if provider_name == "sarvam":
            from pipecat.services.sarvam.stt import SarvamSTTService
            return SarvamSTTService(
                api_key=api_key,
                model=model or "saarika:v2.5",
                sample_rate=metadata.get("sample_rate"),
                params=build_input_params(SarvamSTTService, metadata),
            )
        if provider_name == "speechmatics":
            from core.services.speechmatics_stt import ToneSpeechmaticsSTTService
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
                base_url=metadata.get("base_url") or "wss://us2.rt.speechmatics.com/v2",
                sample_rate=metadata.get("sample_rate"),
                params=build_input_params(ToneSpeechmaticsSTTService, metadata),
            )
        if provider_name == "assemblyai":
            from pipecat.services.assemblyai.models import AssemblyAIConnectionParams
            from pipecat.services.assemblyai.stt import AssemblyAISTTService
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
            return AssemblyAISTTService(api_key=api_key, **asm_kwargs, **_url_kwargs(metadata, "api_endpoint_base_url"))
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
                **_url_kwargs(metadata),
            )
        if provider_name == "elevenlabs":
            from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
            return ElevenLabsRealtimeSTTService(api_key=api_key, model=model or "scribe_v2_realtime", params=build_input_params(ElevenLabsRealtimeSTTService, metadata), **_url_kwargs(metadata))
        if provider_name == "gladia":
            from pipecat.services.gladia.stt import GladiaSTTService
            return GladiaSTTService(
                api_key=api_key,
                model=model or "solaria-1",
                region=metadata.get("region"),
                sample_rate=metadata.get("sample_rate"),
                params=build_input_params(GladiaSTTService, metadata),
                **_url_kwargs(metadata, "url"),
            )
        if provider_name == "soniox":
            from pipecat.services.soniox.stt import SonioxSTTService
            return SonioxSTTService(api_key=api_key, params=build_input_params(SonioxSTTService, metadata), **_url_kwargs(metadata, "url"))
        if provider_name == "hathora":
            from pipecat.services.hathora.stt import HathoraSTTService
            return HathoraSTTService(api_key=api_key, model=model or "parakeet", params=build_input_params(HathoraSTTService, metadata))
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
        logger.warning("Unsupported STT provider: %s", provider_name)
        return None
    except ImportError as e:
        logger.warning("STT provider %s not available: %s", provider_name, e)
        return None
    except Exception as e:
        logger.exception("STT provider %s failed to initialize: %s", provider_name, e)
        return None


def _close_unused_session(session) -> None:
    """Close an aiohttp session that was created but never handed off to a service.

    `build_tts` is sync but always runs inside the builder's event loop, so schedule
    the async close rather than awaiting. Best-effort: skip if there's no running loop.
    """
    if session is None:
        return
    import asyncio
    try:
        asyncio.get_running_loop().create_task(session.close())
    except RuntimeError:
        pass


def build_tts(spec: dict) -> Optional[Any]:
    """Build a TTS service instance from a resolved spec dict."""
    provider_name = spec["provider_name"]
    api_key = spec["api_key"]
    model = spec["model_name"]
    metadata = spec["metadata"]
    model_meta = spec["model_meta_data"]

    tts_voice_id = metadata.get("voice_id")
    tts_language = metadata.get("language")

    # HTTP-based providers create their aiohttp session lazily, in their own branch
    # right before construction (so a failed import never leaks a session). `session`
    # stays None until then; the failure handlers below close it if it was created
    # but never handed off to a constructed service.
    import aiohttp
    session = None

    try:
        if provider_name == "cartesia":  # In code but class is different
            from pipecat.services.cartesia.tts import CartesiaTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language or "en"
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return CartesiaTTSService(api_key=api_key, model=model or "sonic-3", params=build_input_params(CartesiaTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata, "url"))
        if provider_name == "openai":  # In code
            from pipecat.services.openai.tts import OpenAITTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return OpenAITTSService(api_key=api_key, model=model or "gpt-4o-mini-tts", params=build_input_params(OpenAITTSService, metadata), **voice_kwargs, **_url_kwargs(metadata))
        if provider_name == "elevenlabs":
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "CwhRBWXzGAHq8TQ4Fs17"
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return ElevenLabsTTSService(api_key=api_key, model=model or "eleven_v3", params=build_input_params(ElevenLabsTTSService, metadata), **voice_kwargs)
        if provider_name == "playht":  # In code but class is different
            from pipecat.services.playht.tts import PlayHTTTSService
            user_id = model_meta.get("user_id") or metadata.get("user_id") or ""
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_url"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return PlayHTTTSService(api_key=api_key, user_id=user_id, params=build_input_params(PlayHTTTSService, metadata), **voice_kwargs)
        if provider_name == "asyncai_http":  # in code
            from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "13616e5f-6fda-4247-b548-8821cb71fb54"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return AsyncAIHttpTTSService(api_key=api_key, aiohttp_session=session, params=build_input_params(AsyncAIHttpTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata, "url"))
        if provider_name == "aws_polly":  # In code
            from pipecat.services.aws.tts import AWSPollyTTSService
            aws_access_key_id = model_meta.get("aws_access_key_id") or metadata.get("aws_access_key_id") or ""
            region = model_meta.get("region") or metadata.get("region") or "us-east-1"
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return AWSPollyTTSService(api_key=api_key, aws_access_key_id=aws_access_key_id, region=region, params=build_input_params(AWSPollyTTSService, metadata), **voice_kwargs)
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
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return CambTTSService(api_key=api_key, params=build_input_params(CambTTSService, camb_metadata), **voice_kwargs)
        if provider_name == "deepgram":  # In code
            from pipecat.services.deepgram.tts import DeepgramHttpTTSService
            dg_voice = tts_voice_id or "aura-2-helena-en"
            dg_model = model or "aura-2"
            dg_kwargs = {}
            if metadata.get("sample_rate") is not None:
                dg_kwargs["sample_rate"] = metadata["sample_rate"]
            logger.debug("[TTS {}] model: {}, voice: {}", provider_name, dg_model, dg_voice)
            session = aiohttp.ClientSession()
            return DeepgramHttpTTSService(api_key=api_key, model=dg_model, voice=dg_voice, aiohttp_session=session, **dg_kwargs, **_url_kwargs(metadata))
        if provider_name == "google":  # Done
            from pipecat.services.google.tts import GoogleTTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            logger.debug("[TTS {}] voice_kwargs: {}, location: global", provider_name, voice_kwargs)
            return GoogleTTSService(credentials=api_key, params=build_input_params(GoogleTTSService, metadata), **voice_kwargs)
        if provider_name == "groq":  # In code
            from pipecat.services.groq.tts import GroqTTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            # Pick model based on language: Arabic voices use Arabic model, everything else uses English model
            if not model:
                model = "canopylabs/orpheus-arabic-saudi" if tts_language == "ar" else "canopylabs/orpheus-v1-english"
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return GroqTTSService(api_key=api_key, model_name=model, params=build_input_params(GroqTTSService, metadata), **voice_kwargs)
        if provider_name == "hathora":  # In code
            from pipecat.services.hathora.tts import HathoraTTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return HathoraTTSService(api_key=api_key, model=model or "hexgrad-kokoro-82m", params=build_input_params(HathoraTTSService, metadata), **voice_kwargs)
        if provider_name == "minimax":  # In code
            from pipecat.services.minimax.tts import MiniMaxHttpTTSService
            group_id = model_meta.get("group_id") or metadata.get("group_id") or ""
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return MiniMaxHttpTTSService(api_key=api_key, group_id=group_id, model=model or "speech-2.8-turbo", aiohttp_session=session, params=build_input_params(MiniMaxHttpTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata))
        if provider_name == "neuphonic":  # In code
            from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "6654e5a9-143e-46f4-a44a-4fcb9e1fe2a6"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return NeuphonicHttpTTSService(api_key=api_key, model=model or "neu_hq", aiohttp_session=session, params=build_input_params(NeuphonicHttpTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata, "url"))
        if provider_name == "nvidia":  # In code
            from pipecat.services.nvidia.tts import NvidiaTTSService
            server = model_meta.get("server") or metadata.get("server") or "grpc.nvcf.nvidia.com:443"
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return NvidiaTTSService(api_key=api_key, server=server, params=build_input_params(NvidiaTTSService, metadata), **voice_kwargs)
        if provider_name == "rime":  # In code
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
            params = build_input_params(RimeHttpTTSService, metadata)
            if rime_language and params:
                params.language = rime_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return RimeHttpTTSService(api_key=api_key, model=model or "mistv2", aiohttp_session=session, params=params, **voice_kwargs)
        if provider_name == "sarvam":  # In code
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
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return SarvamHttpTTSService(api_key=api_key, model=model or "bulbul:v3", aiohttp_session=session, params=build_input_params(SarvamHttpTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata))
        if provider_name == "speechmatics":  # In code
            from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            session = aiohttp.ClientSession()
            return SpeechmaticsTTSService(api_key=api_key, aiohttp_session=session, sample_rate=metadata.get("sample_rate") or SpeechmaticsTTSService.SPEECHMATICS_SAMPLE_RATE, params=build_input_params(SpeechmaticsTTSService, metadata), **voice_kwargs)
        if provider_name == "azure":
            from pipecat.services.azure.tts import AzureTTSService
            region = model_meta.get("region") or metadata.get("region") or "eastus"
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return AzureTTSService(api_key=api_key, region=region, params=build_input_params(AzureTTSService, metadata), **voice_kwargs)
        if provider_name == "fish":
            from pipecat.services.fish.tts import FishAudioTTSService
            voice_kwargs = {}
            voice_kwargs["reference_id"] = tts_voice_id or "0eb2bd3576714dbcad7cd4c6b2b6e12f"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return FishAudioTTSService(api_key=api_key, model_id=model or "s1", params=build_input_params(FishAudioTTSService, metadata), **voice_kwargs)
        if provider_name == "hume":
            from pipecat.services.hume.tts import HumeTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "d8ab67c6-953d-4bd8-9370-8fa53a0f1453"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return HumeTTSService(api_key=api_key, version=model or "2", params=build_input_params(HumeTTSService, metadata), **voice_kwargs)
        if provider_name == "inworld":
            from pipecat.services.inworld.tts import InworldTTSService
            voice_kwargs = {}
            if tts_voice_id is not None:
                voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return InworldTTSService(api_key=api_key, model=model or "inworld-tts-1.5-max", params=build_input_params(InworldTTSService, metadata), **voice_kwargs, **_url_kwargs(metadata, "url"))
        if provider_name == "lmnt":
            from pipecat.services.lmnt.tts import LmntTTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id or "ava"
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            return LmntTTSService(api_key=api_key, **voice_kwargs)
        if provider_name == "resemble":
            from pipecat.services.resembleai.tts import ResembleAITTSService
            voice_kwargs = {}
            voice_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                voice_kwargs["language"] = tts_language
            else:
                voice_kwargs["language"] = None
            if metadata.get("sample_rate") is not None:
                voice_kwargs["sample_rate"] = metadata["sample_rate"]
            logger.debug("[TTS {}] voice_kwargs: {}", provider_name, voice_kwargs)
            return ResembleAITTSService(api_key=api_key, **voice_kwargs, **_url_kwargs(metadata, "url"))

        if provider_name == "chatterbox":
            # Self-hosted Resemble AI Chatterbox — same /ws/tts protocol + 24kHz as Qwen,
            # so we reuse QwenWebSocketTTSService pointed at the chatterbox service.
            from core.services.pipeline.qwen_tts_service import QwenWebSocketTTSService
            from core.logging import get_trace_id
            ws_url = "ws://staging-tts-chatterbox-service.staging.svc.cluster.local/ws/tts"
            cb_kwargs = {}
            if tts_voice_id is not None:
                cb_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                cb_kwargs["language"] = tts_language
            if metadata.get("sample_rate") is not None:
                cb_kwargs["sample_rate"] = metadata["sample_rate"]
            return QwenWebSocketTTSService(url=ws_url, trace_id=get_trace_id(), **cb_kwargs)

        if provider_name == "qwen_websocket":
            from core.services.pipeline.qwen_tts_service import QwenWebSocketTTSService
            from core.logging import get_trace_id
            ws_url = "ws://staging-tts-qwen-service.staging.svc.cluster.local/ws/tts"
            qwen_kwargs = {}
            if tts_voice_id is not None:
                qwen_kwargs["voice_id"] = tts_voice_id
            if tts_language is not None:
                qwen_kwargs["language"] = tts_language
            if metadata.get("sample_rate") is not None:
                qwen_kwargs["sample_rate"] = metadata["sample_rate"]
            logger.debug("[TTS {}] qwen_kwargs: {}", provider_name, qwen_kwargs)
            return QwenWebSocketTTSService(url=ws_url, trace_id=get_trace_id(), **qwen_kwargs)

        logger.warning("Unsupported TTS provider: %s", provider_name)
        return None
    except ImportError as e:
        logger.warning("TTS provider %s not available: %s", provider_name, e)
        _close_unused_session(session)
        return None
    except Exception as e:
        logger.exception("TTS provider %s failed to initialize: %s", provider_name, e)
        _close_unused_session(session)
        return None
