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

    def get_llm_for_agent(self, agent: Any) -> Optional[Any]:
        print("get_llm_for_agent", agent)
        """
        Build and return the LLM service instance for the given agent.
        Uses agent config's llm_service_id (service_provider) and llm_metadata.
        Returns None if config or credentials are missing or provider is unsupported.
        """
        config = self._get_agent_config(agent)

        print("config.llm_service_id",config.llm_service_id)
        print("config",config)

        if not config or not config.llm_service_id:
            return None
        result = self._get_service_and_credentials(config.llm_service_id, "llm")
        if not result:
            print("into not result")
            return None

        svc, provider, api_key = result
        metadata = (config.llm_metadata or {}) if hasattr(config, "llm_metadata") else {}
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        model = model_meta.get("model") or metadata.get("model") or "gpt-4o"
        provider_name = (provider.name or "").strip().lower()

        print("provider_name",provider_name)


        try:
            if provider_name == "openai": #done
                print("into openai")
                from pipecatfork.src.pipecat.services.openai.llm import OpenAILLMService
                print("after pipecatfork.src.pipecat.services.openai.llm import OpenAILLMService")
                return OpenAILLMService(api_key=f"{api_key}", model="gpt-4.1")
            if provider_name == "anthropic": #done
                from pipecatfork.src.pipecat.services.anthropic.llm import AnthropicLLMService
                return AnthropicLLMService(api_key=api_key, model=model)
            if provider_name == "groq": #done
                from pipecatfork.src.pipecat.services.groq.llm import GroqLLMService
                return GroqLLMService(api_key=api_key, model=model)
            if provider_name == "openrouter": #done
                from pipecatfork.src.pipecat.services.openrouter.llm import OpenRouterLLMService
                return OpenRouterLLMService(api_key=api_key, model=metadata.get("model") or model)
            if provider_name == "aws_bedrock": #done
                from pipecatfork.src.pipecat.services.aws.llm import AWSBedrockLLMService
                return AWSBedrockLLMService(api_key=api_key, model=model)
            if provider_name == "aws_nova_sonic": #done
                from pipecatfork.src.pipecat.services.aws.llm import AWSNovaSonicLLMService
                return AWSNovaSonicLLMService(api_key=api_key, model=model)
            if provider_name == "google": #Done
                from pipecatfork.src.pipecat.services.google.llm import GoogleLLMService
                return GoogleLLMService(api_key=api_key, model=model)
            if provider_name == "gemini_live": #done
                from pipecatfork.src.pipecat.services.google.llm import GeminiLiveLLMService
                return GeminiLiveLLMService(api_key=api_key, model=model)
            if provider_name == "grok_realtime": #done
                from pipecatfork.src.pipecat.services.grok.llm import GrokRealtimeLLMService
                return GrokRealtimeLLMService(api_key=api_key, model=model)
            if provider_name == "base_openai": #done
                from pipecatfork.src.pipecat.services.openai.llm import BaseOpenAILLMService
                return BaseOpenAILLMService(api_key=api_key, model=model)
            if provider_name == "openai_realtime": #done
                from pipecatfork.src.pipecat.services.openai.llm import OpenAIRealtimeLLMService
                return OpenAIRealtimeLLMService(api_key=api_key, model=model)
            if provider_name == "openai_realtime_beta": #done
                from pipecatfork.src.pipecat.services.openai.llm import OpenAIRealtimeBetaLLMService
                return OpenAIRealtimeBetaLLMService(api_key=api_key, model=model)
            if provider_name == "ultravox_realtime": #done
                from pipecatfork.src.pipecat.services.ultravox.llm import UltravoxRealtimeLLMService
                return UltravoxRealtimeLLMService(api_key=api_key, model=model)
            logger.warning("Unsupported LLM provider: %s", provider.name)
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
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "deepgram": # done
                from pipecatfork.src.pipecat.services.deepgram.stt import DeepgramSTTService
                return DeepgramSTTService(api_key=api_key)
            if provider_name == "openai": # done
                from pipecatfork.src.pipecat.services.openai.stt import OpenAISTTService
                return OpenAISTTService(api_key=api_key)
            if provider_name == "groq": # Done
                from pipecatfork.src.pipecat.services.groq.stt import GroqSTTService
                return GroqSTTService(api_key=api_key)
            if provider_name == "segmented": #done
                from pipecatfork.src.pipecat.services.segmented.stt import SegmentedSTTService
                return SegmentedSTTService(api_key=api_key)
            if provider_name == "azure": #done
                from pipecatfork.src.pipecat.services.azure.stt import AzureSTTService
                return AzureSTTService(api_key=api_key)
            if provider_name == "deepgram_sagemaker": #done
                from pipecatfork.src.pipecat.services.deepgram.stt import DeepgramSageMakerSTTService
                return DeepgramSageMakerSTTService(api_key=api_key)
            if provider_name == "google": # done
                from pipecatfork.src.pipecat.services.google.stt import GoogleSTTService
                return GoogleSTTService(api_key=api_key)
            if provider_name == "nvidia": # done
                from pipecatfork.src.pipecat.services.nvidia.stt import NvidiaSTTService
                return NvidiaSTTService(api_key=api_key)
            if provider_name == "sarvam": #done
                from pipecatfork.src.pipecat.services.sarvam.stt import SarvamSTTService
                return SarvamSTTService(api_key=api_key)
            if provider_name == "speechmatics": #done
                from pipecatfork.src.pipecat.services.speechmatics.stt import SpeechmaticsSTTService
                return SpeechmaticsSTTService(api_key=api_key)
            logger.warning("Unsupported STT provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("STT provider %s not available: %s", provider_name, e)
            return None

    def get_tts_for_agent(self, agent: Any) -> Optional[Any]:
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
        voice_id = model_meta.get("voice_id") or metadata.get("voice_id") or "71a7ad14-091c-4e8e-a314-022ece01c121"
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "cartesia": #done
                from pipecatfork.src.pipecat.services.cartesia.tts import CartesiaTTSService
                return CartesiaTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "openai": #done
                from pipecatfork.src.pipecat.services.openai.tts import OpenAITTSService
                return OpenAITTSService(api_key=api_key)
            if provider_name == "elevenlabs": #done
                from pipecatfork.src.pipecat.services.elevenlabs.tts import ElevenLabsTTSService
                return ElevenLabsTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "playht": #done
                from pipecatfork.src.pipecat.services.playht.tts import PlayHTTTSService
                user_id = model_meta.get("user_id") or metadata.get("user_id") or ""
                voice_url = model_meta.get("voice_url") or metadata.get("voice_url") or ""
                return PlayHTTTSService(api_key=api_key, user_id=user_id, voice_url=voice_url)
            if provider_name == "word": #done
                from pipecatfork.src.pipecat.services.word.tts import WordTTSService
                return WordTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "asyncai_http": #done
                from pipecatfork.src.pipecat.services.asyncai.tts import AsyncAIHttpTTSService
                return AsyncAIHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "aws_polly": #done
                from pipecatfork.src.pipecat.services.aws.tts import AWSPollyTTSService
                return AWSPollyTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "camb": #done
                from pipecatfork.src.pipecat.services.camb.tts import CambTTSService
                return CambTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "cartesia_http": #done
                from pipecatfork.src.pipecat.services.cartesia.tts import CartesiaHttpTTSService
                return CartesiaHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "deepgram": #done
                from pipecatfork.src.pipecat.services.deepgram.tts import DeepgramHttpTTSService
                return DeepgramHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "google_http": #done
                from pipecatfork.src.pipecat.services.google.tts import GoogleHttpTTSService
                return GoogleHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "google_base": #done
                from pipecatfork.src.pipecat.services.google.tts import GoogleBaseTTSService
                return GoogleBaseTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "groq": #done
                from pipecatfork.src.pipecat.services.groq.tts import GroqTTSService
                return GroqTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "hathora": #done
                from pipecatfork.src.pipecat.services.hathora.tts import HathoraTTSService
                return HathoraTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "minimax": #done
                from pipecatfork.src.pipecat.services.minimax.tts import MiniMaxHttpTTSService
                return MiniMaxHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "neuphonic": #done
                from pipecatfork.src.pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
                return NeuphonicHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "nvidia": #done
                from pipecatfork.src.pipecat.services.nvidia.tts import NvidiaTTSService
                return NvidiaTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "piper": #done
                from pipecatfork.src.pipecat.services.piper.tts import PiperTTSService
                return PiperTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "playht": #done
                from pipecatfork.src.pipecat.services.playht.tts import PlayHTHttpTTSService
                user_id = model_meta.get("user_id") or metadata.get("user_id") or ""
                voice_url = model_meta.get("voice_url") or metadata.get("voice_url") or ""
                return PlayHTHttpTTSService(api_key=api_key, user_id=user_id, voice_url=voice_url)
            if provider_name == "rime": #done
                from pipecatfork.src.pipecat.services.rime.tts import RimeHttpTTSService
                return RimeHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "sarvam": #done
                from pipecatfork.src.pipecat.services.sarvam.tts import SarvamHttpTTSService
                return SarvamHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "speechmatics": #done
                from pipecatfork.src.pipecat.services.speechmatics.tts import SpeechmaticsTTSService
                return SpeechmaticsTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "xtts": #done
                from pipecatfork.src.pipecat.services.xtts.tts import XTTSService
                return XTTSService(api_key=api_key, voice_id=voice_id)
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

        print("into run_bot_with_components")
        from pipecatfork.src.pipecat.processors.aggregators.llm_context import NOT_GIVEN
        from pipecatfork.src.pipecat.processors.aggregators.llm_context import LLMContext
        from pipecatfork.src.pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair,
        )
        from pipecatfork.src.pipecat.processors.aggregators.llm_text_processor import (
            LLMTextProcessor,
        )
        from pipecatfork.src.pipecat.processors.frameworks.rtvi import (
            RTVIConfig,
            RTVIObserver,
            RTVIProcessor,
        )
        from pipecatfork.src.pipecat.pipeline.pipeline import Pipeline
        from pipecatfork.src.pipecat.pipeline.runner import PipelineRunner
        from pipecatfork.src.pipecat.pipeline.task import PipelineParams, PipelineTask


        tools = NOT_GIVEN
        context = LLMContext(messages, tools)
        context_aggregator = LLMContextAggregatorPair(context)
        llm_text_processor = LLMTextProcessor()
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        print("into pipeline")

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

        print("into task")

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