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


def _spec_summary(spec: Any) -> str:
    """Render a `{provider_name, model_name, ...}` spec as "provider/model" for logs."""
    if not spec:
        return "none"
    return f"{spec.get('provider_name') or '?'}/{spec.get('model_name') or '?'}"


def _build_service(kind: str, factory, spec: Any) -> Any:
    """Build one pipeline service, logging which provider/model failed on error.

    Without this, a bad provider name or missing API key surfaces as a bare
    traceback from deep inside service_factory with no indication of which of the
    three services (or which provider) actually blew up.
    """
    if not spec:
        logger.bind(service_kind=kind).debug(
            "[pipeline-builder] service kind={} not configured — skipping", kind
        )
        return None
    provider = (spec or {}).get("provider_name")
    model = (spec or {}).get("model_name")
    started = _time.monotonic()
    try:
        service = factory(spec)
    except Exception:
        logger.bind(service_kind=kind, provider=provider, model=model).exception(
            "[pipeline-builder] service build failed kind={} provider={} model={}",
            kind, provider, model,
        )
        raise
    logger.bind(
        service_kind=kind,
        provider=provider,
        model=model,
        elapsed_ms=int((_time.monotonic() - started) * 1000),
    ).info(
        "[pipeline-builder] service ready kind={} provider={} model={}",
        kind, provider, model,
    )
    return service


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
        # Runner-owned {tool_call_id: llm_requested_at datetime}. Populated by
        # LlmRequestStamper's register_function wrapper at handler dispatch;
        # consumed by every tool handler via ToolCallTimer so each
        # tool_executions row captures the LLM-request → invoked → completed
        # lifecycle.
        tool_request_ts: Any = None,
        # Runner-owned {tool_call_id: proposal record}. Populated by
        # ToolCallProposalObserver on FunctionCallsStartedFrame (and enriched
        # on FunctionCallCancelFrame). Consumed at call completion to attribute
        # ``proposed_at`` to executed rows AND synthesise rows for LLM
        # proposals that never actually executed (unregistered tool name,
        # user-interrupted before dispatch).
        tool_proposals: Any = None,
        current_turn: Any = None,
        tool_dedup: Any = None,
        # Runner-owned dict for attributing why the call ended
        # (llm_end_call / client_disconnect). Handed to the end_call tool
        # handler; first-wins so a later transport disconnect can't overwrite it.
        end_reason_holder: Any = None,
        # Runner-owned dict carrying the DB row's calls.id once available.
        # Piped into the same downstream sinks so their structured log lines
        # include call_id=<uuid> for direct Grafana → DB joins.
        call_id_holder: Any = None,
        # Runner-owned list of {role, text, timestamp} turn entries. Passed to
        # the end_call handler so its confirmation guard can inspect the
        # conversation and refuse a tool call that skipped the ask/reply step.
        transcript_entries: Any = None,
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
        from pipecat.audio.vad.vad_analyzer import VADParams
        from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
        from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
        from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
        from pipecat.processors.aggregators.llm_text_processor import LLMTextProcessor
        from pipecat.processors.frameworks.rtvi import (RTVIObserver, RTVIProcessor)

        from core.processors.llm_response_logger import LLMResponseLogger
        from core.processors.metrics_collector import MetricsCollectorProcessor
        from core.processors.stt_audio_usage_tap import STTAudioUsageTap
        from core.processors.stt_latency_tap import STTLatencyTap
        # Telephony resilience (ported from the call_engines work): keep barge-in
        # robust when Silero VAD gets stuck "speaking" on phone-line noise.
        from core.processors.vad_speaking_timeout import VADSpeakingTimeoutProcessor
        from core.processors.duplicate_transcription_filter import DuplicateTranscriptionFilter
        from core.processors.transcription_timeout_turn_stop import TranscriptionTimeoutUserTurnStopStrategy

        _t_build_start = _time.monotonic()
        _agent_id = getattr(agent, "id", None)
        logger.bind(
            agent_id=_agent_id,
            is_s2s=is_s2s,
            llm_provider=(params.llm or {}).get("provider_name"),
            llm_model=(params.llm or {}).get("model_name"),
            stt_provider=(params.stt or {}).get("provider_name"),
            stt_model=(params.stt or {}).get("model_name"),
            tts_provider=(params.tts or {}).get("provider_name"),
            tts_model=(params.tts or {}).get("model_name"),
        ).info(
            "[pipeline-builder] build START agent={} s2s={} llm={} stt={} tts={}",
            _agent_id, is_s2s,
            _spec_summary(params.llm), _spec_summary(params.stt), _spec_summary(params.tts),
        )

        # --- Build services from the resolved specs (plain dicts, no DB) ---
        llm = _build_service("llm", build_llm, params.llm)
        stt = _build_service("stt", build_stt, None if is_s2s else params.stt)
        tts = _build_service("tts", build_tts, None if is_s2s else params.tts)

        # Install the LLM-request timing stamper BEFORE any register_function
        # call. Every subsequently registered handler (document, custom,
        # built-in, MCP, end_call) is wrapped to stamp ``tool_request_ts``
        # synchronously on dispatch — see LlmRequestStamper for why an
        # observer can't do this race-free.
        if llm and tool_request_ts is not None:
            from core.services.pipeline.tool_call_timing import LlmRequestStamper
            LlmRequestStamper(tool_request_ts).install(llm)

        _t = _time.monotonic()
        rtvi = RTVIProcessor()

        # Register document tool from the cached KB data (no DB query; pgvector still
        # searched live at call time inside the handler).
        doc_tools = None
        if agent:
            from core.services.document_tool_service import build_document_tool
            try:
                doc_tools = build_document_tool(
                    llm, agent.id, agent.organization_id, params.kb,
                    tool_call_entries=tool_call_entries,
                    tool_request_ts=tool_request_ts,
                    current_turn=current_turn,
                )
                _doc_count = len(doc_tools.standard_tools) if doc_tools else 0
                logger.bind(
                    agent_id=agent.id,
                    doc_tool_count=_doc_count,
                    kb_configured=bool(params.kb),
                ).info(
                    "[pipeline-builder] document tool ready agent={} tools={} kb_configured={}",
                    agent.id, _doc_count, bool(params.kb),
                )
            except Exception:
                logger.bind(agent_id=agent.id).exception(
                    "[pipeline-builder] document tool build failed agent={}", agent.id
                )
                raise

        # Custom + built-in tools, rebuilt from the cached tool dicts (no DB query).
        custom_tools_schema = None
        if agent and params.tools:
            from core.services.custom_tool_service import (
                build_custom_tool_schemas, create_built_in_tool_handler,
                create_custom_tool_handler, sanitize_tool_name, tool_from_cache)
            custom_tools = [tool_from_cache(t) for t in params.tools]
            if custom_tools:
                logger.bind(agent_id=agent.id, tool_count=len(custom_tools)).info(
                    "[pipeline-builder] building custom tools agent={} count={}",
                    agent.id, len(custom_tools),
                )
                custom_tools_schema = build_custom_tool_schemas(custom_tools)
                for tool in custom_tools:
                    try:
                        # Only "custom" tools are customer webhooks; everything else
                        # (google_calendar, send_sms, …) is a built-in whose tool_type IS
                        # the specific type. google_calendar needs org_id for its OAuth
                        # lookup. (The old code routed identically: tool_type != "custom".)
                        if tool.tool_type != "custom":
                            handler = create_built_in_tool_handler(
                                tool, from_number, org_id=agent.organization_id,
                                tool_call_entries=tool_call_entries,
                                tool_request_ts=tool_request_ts,
                                current_turn=current_turn,
                                tool_dedup=tool_dedup,
                            )
                        else:
                            handler = create_custom_tool_handler(
                                tool,
                                tool_call_entries=tool_call_entries,
                                tool_request_ts=tool_request_ts,
                                current_turn=current_turn,
                            )
                        # Register under the SAME sanitized name used in the schema so the
                        # model's tool call (e.g. "calender_tool") maps back to this handler.
                        fn_name = sanitize_tool_name(tool.name)
                        llm.register_function(fn_name, handler)
                        logger.bind(
                            agent_id=agent.id,
                            tool_name=tool.name,
                            tool_type=tool.tool_type,
                            fn_name=fn_name,
                        ).info(
                            "[pipeline-builder] registered tool handler type={} name={} fn={}",
                            tool.tool_type, tool.name, fn_name,
                        )
                    except Exception:
                        logger.bind(
                            agent_id=agent.id,
                            tool_name=getattr(tool, "name", None),
                            tool_type=getattr(tool, "tool_type", None),
                        ).exception(
                            "[pipeline-builder] tool handler registration failed name={} type={} agent={}",
                            getattr(tool, "name", "?"), getattr(tool, "tool_type", "?"), agent.id,
                        )
                        raise

        # MCP tools: connect to the agent's linked MCP servers and register their tools.
        # register_mcp_tools is async (network I/O), which is why build() is async.
        mcp_tools_schema = None
        if agent:
            _t_mcp = _time.monotonic()
            try:
                from core.services.mcp_tool_service import register_mcp_tools
                mcp_tools_schema = await register_mcp_tools(
                    llm, agent.id,
                    tool_call_entries=tool_call_entries,
                    tool_request_ts=tool_request_ts,
                    current_turn=current_turn,
                    tool_dedup=tool_dedup,
                )
                _mcp_count = len(mcp_tools_schema.standard_tools) if mcp_tools_schema else 0
                logger.bind(
                    agent_id=agent.id,
                    mcp_tool_count=_mcp_count,
                    elapsed_ms=int((_time.monotonic() - _t_mcp) * 1000),
                ).info(
                    "[pipeline-builder] MCP tools ready agent={} tools={}",
                    agent.id, _mcp_count,
                )
            except Exception:
                # Recoverable — the pipeline builds and the call still proceeds
                # without MCP. But logged at ERROR (via .exception) with the full
                # traceback so regressions in MCP integrations are visible in
                # Loki without a separate lookup for the stack.
                logger.bind(
                    agent_id=agent.id,
                    elapsed_ms=int((_time.monotonic() - _t_mcp) * 1000),
                ).exception(
                    "[pipeline-builder] MCP tools unavailable — continuing without them agent={}",
                    agent.id,
                )

        # Built-in end_call tool — always-on for every agent. The single,
        # canonical path for ending a call (mandatory two-step confirmation
        # is encoded in END_CALL_SYSTEM_PROMPT).
        end_call_registered = False
        if llm and agent:
            from core.services.pipeline.tools.end_call_tool import (
                END_CALL_TOOL_NAME, END_CALL_TOOL_SCHEMA, create_end_call_handler,
            )
            llm.register_function(
                END_CALL_TOOL_NAME,
                create_end_call_handler(
                    tool_call_entries=tool_call_entries,
                    tool_request_ts=tool_request_ts,
                    current_turn=current_turn,
                    end_reason_holder=end_reason_holder,
                    call_id_holder=call_id_holder,
                    transcript_entries=transcript_entries,
                ),
            )
            end_call_registered = True
            logger.bind(agent_id=agent.id).info(
                "[pipeline-builder] registered built-in end_call tool agent={}", agent.id
            )

        # Combine doc tools, custom tools, MCP tools, and built-in tools into one ToolsSchema
        all_tool_schemas = []
        if doc_tools:
            all_tool_schemas.extend(doc_tools.standard_tools)
        if custom_tools_schema:
            all_tool_schemas.extend(custom_tools_schema.standard_tools)
        if mcp_tools_schema:
            all_tool_schemas.extend(mcp_tools_schema.standard_tools)
        if end_call_registered:
            all_tool_schemas.append(END_CALL_TOOL_SCHEMA)

        doc_count = len(doc_tools.standard_tools) if doc_tools else 0
        custom_count = len(custom_tools_schema.standard_tools) if custom_tools_schema else 0
        mcp_count = len(mcp_tools_schema.standard_tools) if mcp_tools_schema else 0
        built_in_count = 1 if end_call_registered else 0
        if agent:
            logger.bind(
                agent_id=getattr(agent, "id", None),
                total_tools=len(all_tool_schemas),
                doc_tools=doc_count,
                custom_tools=custom_count,
                mcp_tools=mcp_count,
                built_in_tools=built_in_count,
            ).info(
                "[pipeline-builder] tool inventory agent={} total={} doc={} custom={} mcp={} built_in={}",
                getattr(agent, "id", None), len(all_tool_schemas), doc_count, custom_count, mcp_count, built_in_count,
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
        if end_call_registered:
            from core.services.pipeline.tools.end_call_tool import inject_end_call_instructions
            messages = inject_end_call_instructions(messages)

        if is_s2s:
            # S2S pipeline: audio goes through the LLM directly (no separate STT/TTS).
            # System prompt is already set via session_properties.instructions (OpenAI)
            # or system_instruction (Gemini) during LLM creation.
            logger.bind(agent_id=_agent_id).info(
                "[pipeline-builder] building S2S pipeline (speech-to-speech)"
            )
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
            logger.bind(
                agent_id=_agent_id,
                phase="s2s_processors",
                elapsed_ms=int((_time.monotonic() - _t) * 1000),
            ).info("[pipeline-builder] phase complete phase=s2s_processors")
        else:
            # Standard pipeline: STT -> LLM -> TTS
            context = LLMContext(messages, combined_tools)
            # Smart Turn keeps stop_secs=0.8 to tolerate mid-sentence pauses
            # (~0.5s, e.g. "Hi, what <pause> can you help me with") without
            # splitting one utterance into two; VAD stop_secs=0.2 gives faster
            # end-of-speech detection at the audio level.
            smart_turn_analyzer = LocalSmartTurnAnalyzerV3(
                confidence_threshold=0.7,
                params=SmartTurnParams(stop_secs=0.8),
            )
            context_aggregator = LLMContextAggregatorPair(
                context,
                user_params=LLMUserAggregatorParams(
                    vad_analyzer=SileroVADAnalyzer(
                        params=VADParams(stop_secs=0.2),
                    ),
                    user_turn_strategies=UserTurnStrategies(
                        stop=[
                            # Primary: Smart Turn (the new design's turn detector).
                            TurnAnalyzerUserTurnStopStrategy(turn_analyzer=smart_turn_analyzer),
                            # Telephony fallback: fire end-of-turn when transcription
                            # goes quiet even if Silero VAD never reports "stopped"
                            # (phone-line noise can keep VAD stuck in speaking state).
                            TranscriptionTimeoutUserTurnStopStrategy(timeout=0.6),
                        ]
                    ),
                ),
            )
            user_aggregator = context_aggregator.user()
            assistant_aggregator = context_aggregator.assistant()
            llm_text_processor = LLMTextProcessor()
            # Log one INFO line per assistant response (model + turn + chars
            # + duration + truncated text). Sits AFTER llm_text_processor so
            # it observes the assembled text, BEFORE tts so it fires at the
            # moment the LLM finishes — not after audio synthesis. Pairs
            # with [pgvector.query] via the per-call trace_id for full
            # user-query → chunks → answer correlation.
            llm_response_logger = LLMResponseLogger(
                llm_model=(getattr(llm, "model_name", None) or None)
                or ((params.llm or {}).get("model_name")),
                current_turn=current_turn,
            )
            # Keyword-based CallEndDetectorProcessor intentionally removed.
            # All end-of-call decisions now flow through the LLM's end_call
            # tool with a mandatory two-step confirmation (see END_CALL_SYSTEM_PROMPT).
            # The agent_config.end_call_message column is preserved for
            # backwards compatibility but no longer takes effect.
            logger.bind(
                agent_id=_agent_id,
                phase="context_aggregators_processors",
                elapsed_ms=int((_time.monotonic() - _t) * 1000),
            ).info("[pipeline-builder] phase complete phase=context_aggregators_processors")

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
            # Resolve the STT model name once for both taps. Prefer the
            # runtime instance's `model_name` (set by services that call
            # `set_model_name` in their constructor — Deepgram, OpenAI,
            # Groq, Parakeet, Granite, ...) and fall back to the configured
            # spec name for services that leave the AIService default of
            # `""` in place (NvidiaWebSocketService → voxtral / gemma). The
            # `or None` step normalizes pipecat's empty-string default into
            # a clean fallthrough.
            stt_model_name = (
                (getattr(stt, "model_name", None) or None)
                or (params.stt.get("model_name") if params.stt else None)
            )

            stt_latency_tap = STTLatencyTap(
                stt_processor_name=stt.name,
                stt_model_name=stt_model_name,
            )

            # STTAudioUsageTap derives billable STT audio duration (ms) from
            # the AudioRawFrames flowing into the STT service. Must sit
            # immediately BEFORE stt so it counts what the provider is about
            # to receive (and skips audio the STT service mutes out).
            stt_audio_usage_tap = STTAudioUsageTap(stt=stt, stt_model_name=stt_model_name)

            pipeline_processors = [
                transport.input(),
                rtvi,
                vad_timeout,
                stt_audio_usage_tap,
                stt,
                duplicate_filter,
                stt_latency_tap,
                user_aggregator,
                llm,
                llm_text_processor,
                llm_response_logger,
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

        logger.bind(
            agent_id=_agent_id,
            processor_count=len(pipeline_processors),
        ).info(
            "[pipeline-builder] processor chain ({}): {}",
            len(pipeline_processors),
            " -> ".join(getattr(p, "name", None) or type(p).__name__ for p in pipeline_processors),
        )

        _t = _time.monotonic()
        pipeline = Pipeline(pipeline_processors)

        # Observers for metrics, latency, and turn tracking
        from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
        from pipecat.observers.turn_tracking_observer import TurnTrackingObserver

        from core.observers.tool_call_proposal_observer import ToolCallProposalObserver
        from core.observers.user_bot_latency_observer import UserBotLatencyObserver

        metrics_observer = MetricsLogObserver()
        latency_observer = UserBotLatencyObserver()
        turn_observer = TurnTrackingObserver()
        # Only attach when the runner wired the map (older callers may not).
        # ``llm_requested_at`` is captured by LlmRequestStamper (installed on
        # the LLM above) — no observer needed for that timestamp any more.
        tool_call_proposal_observer = (
            ToolCallProposalObserver(tool_proposals, current_turn)
            if tool_proposals is not None
            else None
        )

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
                obs for obs in (
                    RTVIObserver(rtvi),
                    metrics_observer,
                    latency_observer,
                    turn_observer,
                    tool_call_proposal_observer,
                ) if obs is not None
            ],
        )
        logger.bind(
            agent_id=_agent_id,
            phase="pipeline_task",
            elapsed_ms=int((_time.monotonic() - _t) * 1000),
        ).info("[pipeline-builder] phase complete phase=pipeline_task")
        _build_elapsed_ms = int((_time.monotonic() - _t_build_start) * 1000)
        logger.bind(
            agent_id=_agent_id,
            is_s2s=is_s2s,
            processor_count=len(pipeline_processors),
            tts_sample_rate=tts_sample_rate,
            elapsed_ms=_build_elapsed_ms,
        ).info(
            "[pipeline-builder] build COMPLETE agent={} s2s={} processors={} tts_sample_rate={} elapsed_ms={}",
            _agent_id, is_s2s, len(pipeline_processors), tts_sample_rate, _build_elapsed_ms,
        )

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
