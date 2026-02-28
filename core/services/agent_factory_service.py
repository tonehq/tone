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
                    print("api_key_value in agent_factory_service.py file ===========", api_key_value)
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
                from pipecat.services.openai.llm import OpenAILLMService
                print("after pipecat.services.openai.llm import OpenAILLMService")
                return OpenAILLMService(api_key=f"{api_key}", model="gpt-4.1")
            if provider_name == "anthropic": #done
                from pipecat.services.anthropic.llm import AnthropicLLMService
                return AnthropicLLMService(api_key=api_key, model=model)
            if provider_name == "groq": #done
                from pipecat.services.groq.llm import GroqLLMService
                return GroqLLMService(api_key=api_key, model=model)
            if provider_name == "openrouter": #done
                from pipecat.services.openrouter.llm import OpenRouterLLMService
                return OpenRouterLLMService(api_key=api_key, model=metadata.get("model") or model)
            if provider_name == "aws_bedrock": #done
                from pipecat.services.aws.llm import AWSBedrockLLMService
                return AWSBedrockLLMService(api_key=api_key, model=model)
            if provider_name == "google": #Done
                from pipecat.services.google.llm import GoogleLLMService
                return GoogleLLMService(api_key=api_key, model=model)
            if provider_name == "ollama": #done
                from pipecat.services.ollama.llm import OLLamaLLMService
                return OLLamaLLMService()
            if provider_name in ["azure","cerebras","nvidia_nim","fireworks","together","perplexity","qwen","deepseek", "mistral","sambanova","grok"]:    
                from pipecat.services.openai.llm import BaseOpenAILLMService
                return BaseOpenAILLMService(api_key="sk-e6cc0cf46d814c1baad1cee197474190",model="deepseek-chat")
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
        print("inside get_stt_for_agent ")
        config = self._get_agent_config(agent)
        print("config",config)
        print("config.stt_service_id",config.stt_service_id)
        if not config or not config.stt_service_id:
            return None
        result = self._get_service_and_credentials(config.stt_service_id, "stt")
        print("result in stt",result)
        if not result:
            return None
        svc, provider, api_key = result
        metadata = (config.stt_metadata or {}) if hasattr(config, "stt_metadata") else {}
        model_meta = (svc.meta_data or {}) if isinstance(getattr(svc, "meta_data", None), dict) else {}
        model = model_meta.get("model") or metadata.get("model")
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
                return GoogleSTTService(credentials=api_key)
            if provider_name == "nvidia":
                from pipecat.services.nvidia.stt import NvidiaSTTService
                return NvidiaSTTService(api_key=api_key)
            if provider_name == "sarvam":
                from pipecat.services.sarvam.stt import SarvamSTTService
                return SarvamSTTService(api_key=api_key, model=model or "saarika:v2.5")
            if provider_name == "speechmatics":
                from pipecat.services.speechmatics.stt import SpeechmaticsSTTService
                return SpeechmaticsSTTService(api_key=api_key)
            if provider_name == "assemblyai":
                from pipecat.services.assemblyai.stt import AssemblyAISTTService
                return AssemblyAISTTService(api_key=api_key)
            if provider_name == "cartesia":
                from pipecat.services.cartesia.stt import CartesiaSTTService
                return CartesiaSTTService(api_key=api_key)
            if provider_name == "elevenlabs":
                from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
                return ElevenLabsRealtimeSTTService(api_key=api_key, model=model or "scribe_v2_realtime")
            if provider_name == "gladia":
                from pipecat.services.gladia.stt import GladiaSTTService
                return GladiaSTTService(api_key=api_key, model=model or "solaria-1")
            if provider_name == "soniox":
                from pipecat.services.soniox.stt import SonioxSTTService
                return SonioxSTTService(api_key=api_key)
            if provider_name == "hathora":
                from pipecat.services.hathora.stt import HathoraSTTService
                return HathoraSTTService(api_key=api_key, model=model or "nova-3")
            if provider_name == "sambanova":
                from pipecat.services.sambanova.stt import SambaNovaSTTService
                return SambaNovaSTTService(api_key=api_key, model=model or "Whisper-Large-v3")
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

        model = model_meta.get("model") or metadata.get("model")

        try:
            if provider_name == "cartesia":
                from pipecat.services.cartesia.tts import CartesiaTTSService
                return CartesiaTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "openai":
                from pipecat.services.openai.tts import OpenAITTSService
                voice = model_meta.get("voice") or metadata.get("voice") or "alloy"
                return OpenAITTSService(api_key=api_key, voice=voice, model=model or "tts-1")
            if provider_name == "elevenlabs":
                from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
                return ElevenLabsTTSService(api_key=api_key, voice_id=voice_id, model=model or "eleven_turbo_v2_5")
            if provider_name == "playht":
                from pipecat.services.playht.tts import PlayHTTTSService
                user_id = model_meta.get("user_id") or metadata.get("user_id") or ""
                voice_url = model_meta.get("voice_url") or metadata.get("voice_url") or ""
                return PlayHTTTSService(api_key=api_key, user_id=user_id, voice_url=voice_url)
            if provider_name == "asyncai_http":
                from pipecat.services.asyncai.tts import AsyncAIHttpTTSService
                return AsyncAIHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "aws_polly":
                from pipecat.services.aws.tts import AWSPollyTTSService
                aws_access_key_id = model_meta.get("aws_access_key_id") or metadata.get("aws_access_key_id") or ""
                region = model_meta.get("region") or metadata.get("region") or "us-east-1"
                return AWSPollyTTSService(api_key=api_key, aws_access_key_id=aws_access_key_id, voice_id=voice_id, region=region)
            if provider_name == "camb":
                from pipecat.services.camb.tts import CambTTSService
                return CambTTSService(api_key=api_key, voice_id=voice_id, model=model or "accented-british-english-male")
            if provider_name == "deepgram":
                from pipecat.services.deepgram.tts import DeepgramHttpTTSService
                voice = model_meta.get("voice") or metadata.get("voice") or "aura-asteria-en"
                return DeepgramHttpTTSService(api_key=api_key, voice=voice)
            if provider_name == "google_base":
                from pipecat.services.google.tts import GoogleBaseTTSService
                return GoogleBaseTTSService(credentials=api_key, voice_id=voice_id)
            if provider_name == "groq":
                from pipecat.services.groq.tts import GroqTTSService
                return GroqTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "hathora":
                from pipecat.services.hathora.tts import HathoraTTSService
                return HathoraTTSService(api_key=api_key, voice_id=voice_id, model=model or "sonic-2025-04-16")
            if provider_name == "minimax":
                from pipecat.services.minimax.tts import MiniMaxHttpTTSService
                import aiohttp
                group_id = model_meta.get("group_id") or metadata.get("group_id") or ""
                session = aiohttp.ClientSession()
                return MiniMaxHttpTTSService(api_key=api_key, voice_id=voice_id, group_id=group_id, model=model or "speech-02-turbo", aiohttp_session=session)
            if provider_name == "neuphonic":
                from pipecat.services.neuphonic.tts import NeuphonicHttpTTSService
                return NeuphonicHttpTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "nvidia":
                from pipecat.services.nvidia.tts import NvidiaTTSService
                server = model_meta.get("server") or metadata.get("server") or "grpc.nvcf.nvidia.com:443"
                return NvidiaTTSService(api_key=api_key, voice_id=voice_id, server=server)
            if provider_name == "rime":
                from pipecat.services.rime.tts import RimeHttpTTSService
                return RimeHttpTTSService(api_key=api_key, voice_id=voice_id, model=model or "mist")
            if provider_name == "sarvam":
                from pipecat.services.sarvam.tts import SarvamHttpTTSService
                return SarvamHttpTTSService(api_key=api_key, voice_id=voice_id, model=model or "meera")
            if provider_name == "speechmatics":
                from pipecat.services.speechmatics.tts import SpeechmaticsTTSService
                return SpeechmaticsTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "azure":
                from pipecat.services.azure.tts import AzureTTSService
                region = model_meta.get("region") or metadata.get("region") or "eastus"
                voice = model_meta.get("voice") or metadata.get("voice") or "en-US-SaraNeural"
                return AzureTTSService(api_key=api_key, region=region, voice=voice)
            if provider_name == "fish":
                from pipecat.services.fish.tts import FishAudioTTSService
                return FishAudioTTSService(api_key=api_key, reference_id=voice_id, model_id=model or "s1")
            if provider_name == "hume":
                from pipecat.services.hume.tts import HumeTTSService
                return HumeTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "inworld":
                from pipecat.services.inworld.tts import InworldTTSService
                return InworldTTSService(api_key=api_key, voice_id="Ashley", model=model or "inworld-tts-1.5-max")
            if provider_name == "lmnt":
                from pipecat.services.lmnt.tts import LmntTTSService
                return LmntTTSService(api_key=api_key, voice_id="ava")
            if provider_name == "resemble":
                from pipecat.services.resembleai.tts import ResembleAITTSService
                return ResembleAITTSService(api_key=api_key, voice_id=voice_id)

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
        print("before get_stt_for_agent")
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