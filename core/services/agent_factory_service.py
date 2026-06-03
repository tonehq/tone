"""Backward-compatible facade over the `core.services.pipeline` package.

The voice pipeline was split into a 3-layer architecture under `core/services/pipeline/`
(params -> builder -> runner, each with a base + Pipecat child). The old monolithic
`run_bot_with_components` lives there now (PipecatPipelineBuilder + PipecatPipelineRunner).

This class is kept as a thin facade so existing callers/tests that import
`AgentFactoryService` keep working. New code should use `core.services.pipeline` directly:

    from core.services.pipeline import PipecatPipelineParams, PipecatPipelineBuilder, PipecatPipelineRunner
    params = PipecatPipelineParams.from_agent(agent, db)
    await PipecatPipelineRunner(params, PipecatPipelineBuilder(params), transport,
                                agent=agent, runner_args=runner_args).run()
"""

from typing import Any, Optional

from core.services.base import BaseService
from core.services.pipeline import (PipecatPipelineBuilder,
                                     PipecatPipelineParams, PipecatPipelineRunner)
from core.services.pipeline import service_resolver as _resolver
from core.services.pipeline import service_factory as _service_factory


class AgentFactoryService(BaseService):
    """Facade: build LLM/STT/TTS instances and run the voice bot pipeline.

    Delegates to `core.services.pipeline.{service_resolver,service_factory,params,builder,runner}`.
    """

    # ------------------------------------------------------------------ #
    # Config helpers (delegate to service_resolver module)
    # ------------------------------------------------------------------ #
    def _get_agent_config(self, agent: Any):
        return _resolver.get_agent_config(self.db, agent)

    # ------------------------------------------------------------------ #
    # Service builders
    # ------------------------------------------------------------------ #
    def get_llm_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        if prefetched:
            return _service_factory.build_llm(prefetched)
        if config is None:
            config = self._get_agent_config(agent)
        if not config:
            return None
        spec = _resolver.resolve_service_spec(self.db, self._org_id, agent, config, "llm")
        return _service_factory.build_llm(spec) if spec else None

    def get_stt_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        if prefetched:
            return _service_factory.build_stt(prefetched)
        if config is None:
            config = self._get_agent_config(agent)
        if not config:
            return None
        spec = _resolver.resolve_service_spec(self.db, self._org_id, agent, config, "stt")
        return _service_factory.build_stt(spec) if spec else None

    def get_tts_for_agent(self, agent: Any, config: Any = None, prefetched: dict = None) -> Optional[Any]:
        if prefetched:
            return _service_factory.build_tts(prefetched)
        if config is None:
            config = self._get_agent_config(agent)
        if not config:
            return None
        spec = _resolver.resolve_service_spec(self.db, self._org_id, agent, config, "tts")
        return _service_factory.build_tts(spec) if spec else None

    # ------------------------------------------------------------------ #
    # Config serialization / prefetch (telephony + subprocess)
    # ------------------------------------------------------------------ #
    def serialize_agent_bot_data(self, agent: Any, transport_type: str = None) -> Optional[dict]:
        return _resolver.resolve_agent_services(
            self.db, agent, transport_type=transport_type, org_id=self._org_id
        )

    def get_agent_bot_data(self, agent: Any, prefetched: dict = None) -> Optional[dict]:
        """Build llm/stt/tts instances + messages for an agent.

        Returns the same dict shape as before: {llm, stt, tts, is_s2s, messages, end_call_message}.
        """
        if prefetched:
            params = PipecatPipelineParams.from_cache_dict(prefetched)
        else:
            params = PipecatPipelineParams.from_agent(agent, self.db, org_id=self._org_id)
        if params is None:
            return None

        llm = _service_factory.build_llm(params.llm.to_dict()) if params.llm else None
        stt = None
        tts = None
        if not params.is_s2s:
            stt = _service_factory.build_stt(params.stt.to_dict()) if params.stt else None
            tts = _service_factory.build_tts(params.tts.to_dict()) if params.tts else None

        if not llm:
            return None
        if not params.is_s2s and (not stt or not tts):
            return None

        return {
            "llm": llm,
            "stt": stt,
            "tts": tts,
            "is_s2s": params.is_s2s,
            "messages": params.messages,
            "end_call_message": params.end_call_message,
        }

    # ------------------------------------------------------------------ #
    # Pipeline run
    # ------------------------------------------------------------------ #
    async def run_bot_for_agent(self, agent: Any, transport: Any, runner_args: Any) -> None:
        """Resolve params and run the voice pipeline for an agent.

        Raises ValueError if the agent has no config or missing services.
        """
        body = getattr(runner_args, "body", None) or {}
        prefetched = body.get("_prefetched_services")
        if prefetched:
            params = PipecatPipelineParams.from_cache_dict(prefetched)
        else:
            params = PipecatPipelineParams.from_agent(agent, self.db, org_id=self._org_id)
        if not params:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        builder = PipecatPipelineBuilder(params)
        runner = PipecatPipelineRunner(params, builder, transport, agent=agent, runner_args=runner_args)
        await runner.run()
