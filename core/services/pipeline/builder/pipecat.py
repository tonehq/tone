"""Pipecat pipeline builder.

Builds the LLM/STT/TTS services from the params' specs and assembles a Pipecat
`Pipeline` + `PipelineTask` (standard STT->LLM->TTS or S2S). Performs NO database access:
everything it needs is on `self.params` (resolved earlier by PipelineParams.from_agent).

It handles service construction + pipeline assembly; event handlers that persist data are
wired by the runner, which owns the transcript/turn entry lists.
"""

import time as _time
from typing import Any

from loguru import logger

from core.services.pipeline.builder.base import BuildResult, PipelineBuilder
from core.services.pipeline.service_factory import build_llm, build_stt, build_tts

def _llm_safe_schema(node):
    """Coerce a JSON-schema node so every current LLM provider accepts it.

    Gemini (the strictest provider) rejects two patterns that MCP tools (e.g. ClickUp)
    commonly emit and that OpenAI/Anthropic tolerate. We normalise to the strict form
    once, so a single tool definition works across all LLMs:
      * "type" as a list, e.g. ["string", "null"] -> first non-null type
      * enum whose values aren't all strings       -> drop the enum (KEEP the declared
        type, so the model still passes the real int/number value to the tool; Gemini
        only permits string enums, so an int enum can't be kept either way)
    """
    if isinstance(node, list):
        return [_llm_safe_schema(x) for x in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key == "type" and isinstance(value, list):
            non_null = [t for t in value if t != "null"]
            out[key] = non_null[0] if non_null else "string"
        elif key == "enum" and isinstance(value, list):
            if all(isinstance(v, str) for v in value):
                out[key] = value  # string enums are valid everywhere
            # else: drop the non-string enum, preserving the param's declared type
        else:
            out[key] = _llm_safe_schema(value)
    return out


def _sanitize_tool_schemas(tool_schemas):
    """Return copies of the FunctionSchemas with provider-agnostic, LLM-safe properties."""
    from pipecat.adapters.schemas.function_schema import FunctionSchema

    cleaned = []
    for fs in tool_schemas:
        cleaned.append(
            FunctionSchema(
                name=fs.name,
                description=fs.description,
                properties={k: _llm_safe_schema(v) for k, v in (fs.properties or {}).items()},
                required=fs.required,
            )
        )
    return cleaned


def _build_service_categories(*, stt: Any, llm: Any, tts: Any) -> dict:
    """Map each built service instance's ``.name`` to its role category.

    Consumed by ``MetricsCollectorProcessor`` to classify TTFB metrics
    without inspecting class names. Skips ``None`` services (e.g. STT/TTS
    are unset on the S2S path).
    """
    from core.processors.metrics_collector import (CATEGORY_LLM, CATEGORY_STT,
                                                   CATEGORY_TTS)

    role_map = {CATEGORY_STT: stt, CATEGORY_LLM: llm, CATEGORY_TTS: tts}
    return {svc.name: role for role, svc in role_map.items() if svc is not None}


class PipecatPipelineBuilder(PipelineBuilder):
    """Assemble a Pipecat pipeline from `PipelineParams`."""

    async def build(
        self,
        transport: Any,
        agent: Any = None,
        audio_buffer: Any = None,
        from_number: str = "",
        prompt_context: Any = None,
        # Mutable holders owned by the runner so tool handlers (custom / built-in /
        # document / MCP) can append one entry per invocation. The runner threads
        # the same list into ``CallLogService.complete_call(tool_calls=...)`` at
        # call end, which persists each entry as a row in ``tool_executions``.
        # ``current_turn`` is a dict so handlers see the latest turn number live
        # (bumped by the runner's ``on_turn_started``); ``tool_dedup`` is the
        # per-call idempotency cache shared across MCP and built-in handlers.
        tool_call_entries: Any = None,
        current_turn: Any = None,
        tool_dedup: Any = None,
    ) -> BuildResult:
        params = self.params
        is_s2s = params.is_s2s

        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineParams as PipecatTaskParams
        from pipecat.pipeline.task import PipelineTask
        from pipecat.processors.aggregators.llm_context import NOT_GIVEN, LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMContextAggregatorPair, LLMUserAggregatorParams)
        from pipecat.turns.user_turn_strategies import UserTurnStrategies
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
        from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
        from pipecat.processors.aggregators.llm_text_processor import LLMTextProcessor
        from pipecat.processors.frameworks.rtvi import (RTVIObserver, RTVIProcessor)

        from core.processors.call_end_detector import CallEndDetectorProcessor
        from core.processors.metrics_collector import MetricsCollectorProcessor
        from core.processors.stt_latency_tap import STTLatencyTap
        # Telephony resilience (ported from the call_engines work): keep barge-in
        # robust when Silero VAD gets stuck "speaking" on phone-line noise.
        from core.processors.vad_speaking_timeout import VADSpeakingTimeoutProcessor
        from core.processors.duplicate_transcription_filter import DuplicateTranscriptionFilter
        from core.processors.transcription_timeout_turn_stop import TranscriptionTimeoutUserTurnStopStrategy

        # --- Build services from the resolved specs (plain dicts, no DB) ---
        llm = build_llm(params.llm) if params.llm else None
        stt = build_stt(params.stt) if (not is_s2s and params.stt) else None
        tts = build_tts(params.tts) if (not is_s2s and params.tts) else None

        _t = _time.monotonic()
        rtvi = RTVIProcessor()

        # Register document tool from the cached KB data (no DB query; pgvector still
        # searched live at call time inside the handler).
        doc_tools = None
        if agent:
            from core.services.document_tool_service import build_document_tool
            doc_tools = build_document_tool(
                llm, agent.id, agent.organization_id, params.kb,
                tool_call_entries=tool_call_entries, current_turn=current_turn,
            )

        # Custom + built-in tools, rebuilt from the cached tool dicts (no DB query).
        custom_tools_schema = None
        if agent and params.tools:
            from core.services.custom_tool_service import (
                build_custom_tool_schemas, create_built_in_tool_handler,
                create_custom_tool_handler, sanitize_tool_name, tool_from_cache)
            custom_tools = [tool_from_cache(t) for t in params.tools]
            if custom_tools:
                logger.info("Building {} cached tools for agent {}", len(custom_tools), agent.id)
                custom_tools_schema = build_custom_tool_schemas(custom_tools)
                for tool in custom_tools:
                    # Only "custom" tools are customer webhooks; everything else
                    # (google_calendar, send_sms, …) is a built-in whose tool_type IS
                    # the specific type. google_calendar needs org_id for its OAuth
                    # lookup. (The old code routed identically: tool_type != "custom".)
                    if tool.tool_type != "custom":
                        handler = create_built_in_tool_handler(
                            tool, from_number, org_id=agent.organization_id,
                            tool_call_entries=tool_call_entries,
                            current_turn=current_turn,
                            tool_dedup=tool_dedup,
                        )
                    else:
                        handler = create_custom_tool_handler(
                            tool,
                            tool_call_entries=tool_call_entries,
                            current_turn=current_turn,
                        )
                    # Register under the SAME sanitized name used in the schema so the
                    # model's tool call (e.g. "calender_tool") maps back to this handler.
                    fn_name = sanitize_tool_name(tool.name)
                    llm.register_function(fn_name, handler)
                    logger.info("Registered {} tool handler: {} (fn name: {})", tool.tool_type, tool.name, fn_name)

        # MCP tools: connect to the agent's linked MCP servers and register their tools.
        # register_mcp_tools is async (network I/O), which is why build() is async.
        mcp_tools_schema = None
        if agent:
            try:
                from core.services.mcp_tool_service import register_mcp_tools
                mcp_tools_schema = await register_mcp_tools(
                    llm, agent.id,
                    tool_call_entries=tool_call_entries,
                    current_turn=current_turn,
                    tool_dedup=tool_dedup,
                )
            except Exception as e:
                logger.warning("MCP tools unavailable, disabled: {}", e)

        # Combine doc tools, custom tools, and MCP tools into one ToolsSchema
        all_tool_schemas = []
        if doc_tools:
            all_tool_schemas.extend(doc_tools.standard_tools)
        if custom_tools_schema:
            all_tool_schemas.extend(custom_tools_schema.standard_tools)
        if mcp_tools_schema:
            all_tool_schemas.extend(mcp_tools_schema.standard_tools)

        doc_count = len(doc_tools.standard_tools) if doc_tools else 0
        custom_count = len(custom_tools_schema.standard_tools) if custom_tools_schema else 0
        mcp_count = len(mcp_tools_schema.standard_tools) if mcp_tools_schema else 0
        if agent:
            logger.info(
                "Agent {} tool inventory: {} total (doc={}, custom={}, mcp={})",
                getattr(agent, "id", None), len(all_tool_schemas), doc_count, custom_count, mcp_count,
            )

        if all_tool_schemas:
            # Normalise every tool's parameter schema to the strict form that all
            # current LLM providers accept (Gemini rejects int enums / union types
            # that OpenAI tolerates). One definition, every provider.
            all_tool_schemas = _sanitize_tool_schemas(all_tool_schemas)
            from pipecat.adapters.schemas.tools_schema import ToolsSchema
            combined_tools = ToolsSchema(standard_tools=all_tool_schemas)
        else:
            combined_tools = NOT_GIVEN

        # Anchor the conversation to the real current date AND substitute per-call
        # {{variables}} (caller number, agent name, …) — both fresh per call, not the
        # resolver's cached messages, so values never go stale or leak across calls.
        # No-op for the date anchor when there's no system message; substitution is
        # skipped when prompt_context is empty.
        messages = params.messages_with_runtime_context(prompt_context)

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
                    vad_analyzer=SileroVADAnalyzer(),
                    user_turn_strategies=UserTurnStrategies(
                        stop=[
                            # Primary: Smart Turn (the new design's turn detector).
                            TurnAnalyzerUserTurnStopStrategy(turn_analyzer=smart_turn_analyzer),
                            # Telephony fallback: fire end-of-turn when transcription
                            # goes quiet even if Silero VAD never reports "stopped"
                            # (phone-line noise can keep VAD stuck in speaking state).
                            TranscriptionTimeoutUserTurnStopStrategy(timeout=1.5),
                        ]
                    ),
                ),
            )
            user_aggregator = context_aggregator.user()
            assistant_aggregator = context_aggregator.assistant()
            llm_text_processor = LLMTextProcessor()
            call_end_detector = CallEndDetectorProcessor(end_call_message=params.end_call_message)
            logger.info("[TIMING] context + aggregators + processors created (+%.3fs)", _time.monotonic() - _t)

            # VADSpeakingTimeout caps a stuck VAD "speaking" segment (8s) so
            # segmented STTs flush and turn-stop strategies can fire; the
            # DuplicateTranscriptionFilter drops repeated final transcripts that
            # would otherwise trigger a duplicate LLM response (the turn-stop race).
            vad_timeout = VADSpeakingTimeoutProcessor(max_duration_secs=8.0)
            duplicate_filter = DuplicateTranscriptionFilter()

            # STTLatencyTap derives STT TTFB from the wall-clock gap between
            # UserStoppedSpeaking and the first TranscriptionFrame. It MUST sit
            # before user_aggregator — the aggregator absorbs TranscriptionFrame
            # without pushing it downstream, so anything past it never sees the
            # transcript. The tap emits a synthetic MetricsFrame that flows on
            # to MetricsCollectorProcessor through the normal MetricsFrame path.
            stt_latency_tap = STTLatencyTap(
                stt_processor_name=stt.name,
                stt_model_name=getattr(stt, "model_name", None),
            )

            pipeline_processors = [
                transport.input(),
                rtvi,
                vad_timeout,
                stt,
                duplicate_filter,
                stt_latency_tap,
                call_end_detector,
                user_aggregator,
                llm,
                llm_text_processor,
                tts,
                transport.output(),
                assistant_aggregator,
            ]

        # MetricsCollectorProcessor collects metrics for DB storage.
        # The {service_name -> role} map lets the collector classify TTFB
        # samples by STT / LLM / TTS without string-matching class names.
        # Built from the actual instances so it covers the auto-assigned
        # "#N" suffix pipecat uses for processor identity.
        service_categories = _build_service_categories(stt=stt, llm=llm, tts=tts)
        metrics_collector = MetricsCollectorProcessor(service_categories=service_categories)
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
            first_message_text=params.first_message_with_context(prompt_context),
        )
