"""Factory to build LLM, STT, and TTS instances from an agent's config and run the bot pipeline."""

from typing import Any, List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.service import Service
from core.models.service_provider import ServiceProvider
from core.services.base import BaseService
from core.utils.encryption import decrypt


class AgentFactoryService(BaseService):
    """Build LLM, STT, TTS instances from agent config and run the voice bot pipeline."""

    def _get_agent_config(self, agent: Any) -> Optional[AgentConfig]:
        """Get the active agent config for the given agent (Agent model or agent_id)."""
        agent_id = agent.id if hasattr(agent, "id") else agent
        print("agent_id in _get_agent_config ===========", agent_id)
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
    ) -> Optional[Tuple[Service, ServiceProvider, str]]:
        """
        Get the default (or first) active Service for the given provider and type,
        plus decrypted API key. Returns (Service, ServiceProvider, decrypted_api_key) or None.
        """
        if not service_provider_id:
            return None
        result = (
            self.db.query(Service, ServiceProvider)
            .join(ServiceProvider, Service.service_provider_id == ServiceProvider.id)
            .filter(
                Service.service_provider_id == service_provider_id,
                Service.service_type == service_type,
                Service.status == "active",
            )
            .order_by(Service.is_default.desc().nulls_last())
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
                    logger.warning("Failed to decrypt API key for service %s: %s", svc.id, e)
        if not api_key_value:
            return None
        return (svc, provider, api_key_value)

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
        model = (svc.config or {}).get("model") or metadata.get("model") or "gpt-4o"
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "openai":
                from pipecatfork.src.pipecat.services.openai.llm import OpenAILLMService
                return OpenAILLMService(api_key=api_key, model=model)
            if provider_name == "anthropic":
                from pipecatfork.src.pipecat.services.anthropic.llm import AnthropicLLMService
                return AnthropicLLMService(api_key=api_key, model=model)
            if provider_name == "groq":
                from pipecatfork.src.pipecat.services.groq.llm import GroqLLMService
                return GroqLLMService(api_key=api_key, model=model)
            if provider_name == "openrouter":
                from pipecatfork.src.pipecat.services.openrouter.llm import OpenRouterLLMService
                return OpenRouterLLMService(api_key=api_key, model=metadata.get("model") or model)
            logger.warning("Unsupported LLM provider: %s", provider.name)
            return None
        except ImportError as e:
            logger.warning("LLM provider %s not available: %s", provider_name, e)
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
            if provider_name == "deepgram":
                from pipecatfork.src.pipecat.services.deepgram.stt import DeepgramSTTService
                return DeepgramSTTService(api_key=api_key)
            if provider_name == "openai":
                from pipecatfork.src.pipecat.services.openai.stt import OpenAISTTService
                return OpenAISTTService(api_key=api_key)
            if provider_name == "groq":
                from pipecatfork.src.pipecat.services.groq.stt import GroqSTTService
                return GroqSTTService(api_key=api_key)
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
        voice_id = (svc.config or {}).get("voice_id") or metadata.get("voice_id") or "71a7ad14-091c-4e8e-a314-022ece01c121"
        provider_name = (provider.name or "").strip().lower()

        try:
            if provider_name == "cartesia":
                from pipecatfork.src.pipecat.services.cartesia.tts import CartesiaTTSService
                return CartesiaTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "openai":
                from pipecatfork.src.pipecat.services.openai.tts import OpenAITTSService
                return OpenAITTSService(api_key=api_key)
            if provider_name == "elevenlabs":
                from pipecatfork.src.pipecat.services.elevenlabs.tts import ElevenLabsTTSService
                return ElevenLabsTTSService(api_key=api_key, voice_id=voice_id)
            if provider_name == "playht":
                from pipecatfork.src.pipecat.services.playht.tts import PlayHTTTSService
                user_id = (svc.config or {}).get("user_id") or metadata.get("user_id") or ""
                voice_url = (svc.config or {}).get("voice_url") or metadata.get("voice_url") or ""
                return PlayHTTTSService(api_key=api_key, user_id=user_id, voice_url=voice_url)
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
        print("agent ===========", agent)
        print("agent.id ===========", agent.id)
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
