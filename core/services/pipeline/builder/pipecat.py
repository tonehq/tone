"""Pipecat pipeline builder.

Builds the LLM/STT/TTS services from the params' specs and assembles a Pipecat
`Pipeline` + `PipelineTask` (standard STT->LLM->TTS or S2S). Performs NO database access:
everything it needs is on `self.params` (resolved earlier by PipelineParams.from_agent).

This is the front half of the old AgentFactoryService.run_bot_with_components
(service construction + pipeline assembly). Event handlers that persist data are wired
by the runner, which owns the transcript/turn entry lists.
"""

import time as _time
from typing import Any

from loguru import logger

from core.services.pipeline.builder.base import BuildResult, PipelineBuilder
from core.services.pipeline.service_factory import build_llm, build_stt, build_tts


class PipecatPipelineBuilder(PipelineBuilder):
    """Assemble a Pipecat pipeline from `PipelineParams`."""

    def build(self, transport: Any, agent: Any = None, audio_buffer: Any = None, from_number: str = "") -> BuildResult:
        params = self.params
        is_s2s = params.is_s2s

        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineParams as PipecatTaskParams
        from pipecat.pipeline.task import PipelineTask
        from pipecat.processors.aggregators.llm_context import NOT_GIVEN, LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair, LLMUserAggregatorParams)
        from pipecat.turns.user_turn_strategies import UserTurnStrategies
        from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
        from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
        from pipecat.processors.aggregators.llm_text_processor import LLMTextProcessor
        from pipecat.processors.frameworks.rtvi import (RTVIConfig, RTVIObserver, RTVIProcessor)

        from core.processors.call_end_detector import CallEndDetectorProcessor
        from core.processors.metrics_collector import MetricsCollectorProcessor

        # --- Build services from the resolved specs (no DB) ---
        llm = build_llm(params.llm.to_dict()) if params.llm else None
        stt = build_stt(params.stt.to_dict()) if (not is_s2s and params.stt) else None
        tts = build_tts(params.tts.to_dict()) if (not is_s2s and params.tts) else None

        _t = _time.monotonic()
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

        # Register document tool if agent has uploaded documents
        doc_tools = None
        if agent:
            from core.services.document_tool_service import register_document_tool
            doc_tools = register_document_tool(llm, agent.id, agent.organization_id)

        # Fetch custom tools for this agent
        custom_tools_schema = None
        if agent:
            from core.services.custom_tool_service import (
                build_custom_tool_schemas, create_built_in_tool_handler,
                create_custom_tool_handler, get_custom_tools_for_agent)
            custom_tools = get_custom_tools_for_agent(agent.id)
            if custom_tools:
                logger.info("Fetched {} custom tools for agent {}", len(custom_tools), agent.id)
                custom_tools_schema = build_custom_tool_schemas(custom_tools)
                for tool in custom_tools:
                    if tool.tool_type == "built_in":
                        handler = create_built_in_tool_handler(tool, from_number)
                    else:
                        handler = create_custom_tool_handler(tool)
                    llm.register_function(tool.name, handler)
                    logger.info("Registered {} tool handler: {}", tool.tool_type, tool.name)

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

        messages = params.messages

        if is_s2s:
            # S2S pipeline: audio goes through the LLM directly (no separate STT/TTS).
            # System prompt is already set via session_properties.instructions (OpenAI)
            # or system_instruction (Gemini) during LLM creation.
            logger.info("Building S2S pipeline (speech-to-speech)")
            context = LLMContext(messages, combined_tools)
            context_aggregator = LLMContextAggregatorPair(context)
            user_aggregator = context_aggregator.user()
            assistant_aggregator = context_aggregator.assistant()

            pipeline_processors = [
                transport.input(),
                rtvi,
                user_aggregator,
                llm,
                transport.output(),
                assistant_aggregator,
            ]
            logger.info("[TIMING] S2S pipeline processors created (+%.3fs)", _time.monotonic() - _t)
        else:
            # Standard pipeline: STT -> LLM -> TTS
            context = LLMContext(messages, combined_tools)
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
            call_end_detector = CallEndDetectorProcessor(end_call_message=params.end_call_message)
            logger.info("[TIMING] context + aggregators + processors created (+%.3fs)", _time.monotonic() - _t)

            pipeline_processors = [
                transport.input(),
                rtvi,
                stt,
                call_end_detector,
                user_aggregator,
                llm,
                llm_text_processor,
                tts,
                transport.output(),
                assistant_aggregator,
            ]

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
        from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
        from pipecat.observers.turn_tracking_observer import TurnTrackingObserver

        from core.observers.user_bot_latency_observer import UserBotLatencyObserver

        metrics_observer = MetricsLogObserver()
        latency_observer = UserBotLatencyObserver()
        turn_observer = TurnTrackingObserver()

        # Use the TTS service's native sample rate so the output transport tags audio
        # frames correctly for the serializer (e.g. Hume @ 48 kHz). S2S models output
        # 24kHz audio by default.
        tts_sample_rate = 24000
        if not is_s2s and tts:
            tts_sample_rate = getattr(tts, "_init_sample_rate", None) or 24000

        task = PipelineTask(
            pipeline,
            params=PipecatTaskParams(
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

        return BuildResult(
            pipeline=pipeline,
            task=task,
            context=context,
            user_aggregator=user_aggregator,
            assistant_aggregator=assistant_aggregator,
            rtvi=rtvi,
            audio_buffer=audio_buffer,
            metrics_collector=metrics_collector,
            metrics_observer=metrics_observer,
            latency_observer=latency_observer,
            turn_observer=turn_observer,
            llm=llm,
            stt=stt,
            tts=tts,
            is_s2s=is_s2s,
            first_message_text=params.first_message_text,
        )
