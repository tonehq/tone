"""Pipecat pipeline runner.

Executes a built pipeline and owns all call-lifecycle concerns: call-log creation,
audio recording + R2 upload, transcript/turn capture, metrics persistence, and the
transport event handlers. Performs its own short-lived DB sessions (for call-log writes)
but never holds a session open across the call — matching the old run_bot_with_components
back half.
"""

import asyncio
import io
import time as _time
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from core.services.pipeline.call_end_events import (
    EVENT_CALL_ENDED,
    EVENT_CALL_ENDED_ERROR,
    REASON_CLIENT_DISCONNECT,
    log_call_event,
)
from core.services.pipeline.runner.base import PipelineRunner
from core.services.pipeline.tool_call_timing import merge_and_synthesize

# Different transport families announce connect/disconnect under different event names.
# We map each (connect, disconnect) pair onto the SAME session start/end, so the runner has
# one provider-agnostic lifecycle hookup — only the transport's data-receive layer differs,
# never the runner. The third element says whether the disconnect event's payload is a real
# participant identifier worth logging (telephony/LiveKit) or an opaque object we drop to None
# (the WS bridge fires the websocket, not a participant). Ordered most-common first.
_SESSION_EVENT_PAIRS = (
    ("on_client_connected", "on_client_disconnected", True),              # telephony (FastAPIWebsocket), Daily, SmallWebRTC
    ("on_first_participant_joined", "on_participant_disconnected", True),  # LiveKit
    ("on_connected", "on_disconnected", False),                          # outbound WS bridge (WebsocketClientTransport)
)


def _wire_session_events(transport, on_start, on_end) -> None:
    """Wire a transport's connect/disconnect events to ``on_start``/``on_end``.

    Registers only the ONE event pair the transport actually fires (checked against the
    transport's registered handlers), replacing per-transport ``type(...).__name__`` checks.
    This is what lets the OUTBOUND ws-client agent greet on connect exactly like an inbound
    placed call — ``WebsocketClientTransport`` fires ``on_connected`` (not
    ``on_client_connected``), and this maps it to the same ``_start_session``.
    """
    supported = getattr(transport, "_event_handlers", {}) or {}
    for connect_event, disconnect_event, carries_participant in _SESSION_EVENT_PAIRS:
        if connect_event not in supported:
            continue

        @transport.event_handler(connect_event)
        async def _on_connect(_transport, *_args, _cb=on_start):
            await _cb()

        if disconnect_event in supported:

            @transport.event_handler(disconnect_event)
            async def _on_disconnect(_transport, *args, _cb=on_end, _carries=carries_participant):
                await _cb(args[0] if (_carries and args) else None)
        return

    logger.warning(
        "[runner] no known session connect event on transport {}", type(transport).__name__
    )


class PipecatPipelineRunner(PipelineRunner):
    """Run a Pipecat pipeline built by `PipecatPipelineBuilder`."""

    async def run(self) -> None:
        from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame
        from pipecat.pipeline.runner import PipelineRunner as PipecatRunner
        from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
        from pydub import AudioSegment

        from core.database.session import get_db_context
        from core.services.call_log_service import CallLogService
        from core.utils.telephony import provider_call_id as _provider_call_id

        _t_comp_start = _time.monotonic()
        # Wall-clock anchor for `Call.started_at`. Captured here — at the very
        # start of run() — so it reflects when the call entered the system,
        # not when the background INSERT in `_create_call_log_in_thread`
        # eventually finishes (which can lag by seconds under load).
        call_started_at = datetime.now(timezone.utc)
        agent = self.agent
        runner_args = self.runner_args
        transport = self.transport

        # Extract call metadata from runner_args
        body = getattr(runner_args, "body", None) or {}
        call_data = body.get("call_data", {})
        transport_type = body.get("transport_type", "unknown")
        provider_call_id = _provider_call_id(call_data)
        from_number = call_data.get("from", "")
        to_number = call_data.get("to", "")
        # Outbound calls (see OutboundCallService): the `calls` row was created at
        # request time and is threaded back here via the TwiML <Parameter> tags
        # (promoted onto body in TelephonyTransport.build). When present, the call
        # log is UPDATED in place rather than inserted.
        direction = body.get("direction")
        scheduled_call_id = body.get("scheduled_call_id")
        if direction == "outbound":
            logger.info(
                "[outbound] pipeline run for outbound call agent={} from={} to={} sid={} scheduled_call_id={}",
                getattr(agent, "id", None), from_number, to_number, provider_call_id, scheduled_call_id,
            )

        # Call-lifecycle state (owned by the runner; captured by event handler closures)
        call_log_state = {"id": None, "done": False}
        call_log_ready = asyncio.Event()
        transcript_entries: list[dict] = []
        turn_entries: list[dict] = []
        # Tool-call telemetry: handlers (custom / built-in / document / MCP)
        # append one entry per invocation. Persisted as ``tool_executions`` rows
        # by ``CallLogService.complete_call(tool_calls=...)`` at call end.
        # ``current_turn`` is a dict so handlers see updates via reference
        # (mutated in ``on_turn_started``); ``tool_dedup`` is the per-call
        # idempotency cache shared across handlers.
        tool_call_entries: list[dict] = []
        # Per-call {tool_call_id: llm_requested_at datetime}. Populated by
        # LlmRequestStamper's register_function wrapper at handler dispatch;
        # popped by each handler via ToolCallTimer. Bounded by in-flight
        # tool calls.
        tool_request_ts: dict = {}
        # Per-call {tool_call_id: proposal record}. Populated by
        # ToolCallProposalObserver on FunctionCallsStartedFrame (with
        # proposed_at + arguments) and enriched on FunctionCallCancelFrame.
        # Consumed at call completion so every LLM proposal — including ones
        # that never actually executed — persists as a tool_executions row.
        tool_proposals: dict = {}
        current_turn: dict = {"number": 0}
        tool_dedup: dict = {}
        call_log_updated = {"done": False}
        # First-wins stamp of why the call ended. The end_call tool handler
        # sets it via the shared dict; the transport disconnect handler falls
        # back to "client_disconnect" only if nothing else has set it yet.
        # Persisted onto metadata_ by CallLogService.complete_call.
        end_reason_holder: dict = {"reason": None, "detail": None}
        # The DB row's calls.id, populated once _create_call_log_in_thread
        # returns. Threaded through the builder to the tool handler and the
        # keyword detector so their structured log lines carry the id — makes
        # each Grafana line directly joinable to the DB row.
        call_id_holder: dict = {"id": None}
        audio_buffer = None

        async def _get_call_log_id():
            """Await until call_log_id is available, then return it."""
            await call_log_ready.wait()
            return call_log_state["id"]

        if agent:
            # Capture the call's trace_id from the async context; executor threads
            # don't inherit contextvars, so we re-bind it inside the thread and also
            # persist it on the call record (correlates the record to its logs).
            from core.logging import get_trace_id, set_trace_id
            _call_trace_id = get_trace_id()

            # Snapshot the call's model identity: {provider_name, model_name, model_id}.
            # Stored in the same INSERT that creates the call row (no extra query).
            def _spec_for_snapshot(spec):
                if not spec:
                    return None
                md = spec.get("metadata") or {}
                model_id = md.get("model_id")
                # `provider_name` stays the slug — call filters/grouping key off it
                # via JSONB paths (see CallService.get_filter_values). The friendly
                # name goes in a separate `provider_display_name` field for the UI.
                snap = {
                    "provider_name": spec.get("provider_name"),
                    "provider_display_name": spec.get("provider_display_name"),
                    "model_name": spec.get("model_name"),
                    "model_id": str(model_id) if model_id is not None else None,
                }
                # The TTS spec carries the resolved voice + language on its metadata
                # (see service_resolver._build_service_specs). Store both the raw ids
                # and their human-readable display values so the call-history snapshot
                # is self-sufficient — the UI shows friendly names without reading the
                # mutable live agent config, and never renders a raw voice-id or a
                # bare language code.
                if md.get("voice_id") is not None:
                    snap["voice_id"] = md.get("voice_id")
                if md.get("voice_name") is not None:
                    snap["voice_name"] = md.get("voice_name")
                if md.get("language") is not None:
                    snap["language"] = md.get("language")
                if md.get("language_display") is not None:
                    snap["language_display"] = md.get("language_display")
                return snap

            # `custom_tools` mirrors the resolver's tool cache filtered to non-MCP tools
            # (mcp_server_id IS NULL) to match the original snapshot semantics. MCP servers
            # and knowledge bases come straight from the cached refs — no DB hit here.
            custom_tool_refs = [
                {"id": t.get("id"), "name": t.get("name")}
                for t in (self.params.tools or [])
                if t.get("mcp_server_id") is None and t.get("id") is not None
            ]
            pipeline_snapshot = {
                "llm": _spec_for_snapshot(self.params.llm),
                "stt": _spec_for_snapshot(self.params.stt),
                "tts": _spec_for_snapshot(self.params.tts),
                "is_s2s": bool(self.params.is_s2s),
                "custom_tools": custom_tool_refs,
                "mcp_servers": list(self.params.mcp_servers or []),
                "knowledge_bases": list(self.params.kb_refs or []),
            }

            def _create_call_log_in_thread():
                """Run in a thread so synchronous DB work doesn't block the event loop."""
                try:
                    set_trace_id(_call_trace_id)
                    _t = _time.monotonic()
                    with get_db_context() as db:
                        call_log = CallLogService(db).create_call_log(
                            agent_id=agent.id,
                            agent_config_id=agent.published_config_id,
                            organization_id=agent.organization_id,
                            provider_call_id=provider_call_id,
                            transport_type=transport_type,
                            from_number=from_number,
                            to_number=to_number,
                            trace_id=_call_trace_id if _call_trace_id != "none" else None,
                            pipeline_config=pipeline_snapshot,
                            started_at=call_started_at,
                            direction=direction,
                            scheduled_call_id=scheduled_call_id,
                        )
                        if call_log:
                            call_log_state["id"] = call_log.id
                            call_id_holder["id"] = str(call_log.id)
                            logger.info("[TIMING] create_call_log thread (+{:.3f}s)", _time.monotonic() - _t)
                        else:
                            logger.warning("create_call_log returned None (no channel resolved) — no call record created")
                except Exception as e:
                    logger.exception("Failed to create call log")
                finally:
                    loop.call_soon_threadsafe(call_log_ready.set)

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, _create_call_log_in_thread)

            # Pipecat's built-in AudioBufferProcessor for recording
            audio_buffer = AudioBufferProcessor(sample_rate=16000, num_channels=1)
        else:
            call_log_ready.set()

        # --- Build the pipeline (services + task + observers) ---
        # Per-call variable context ({{caller_number}}, {{agent_name}}, …) resolved from
        # this call's metadata and substituted into the prompt at build time.
        from core.services.pipeline.prompt_variables import build_call_context
        prompt_context = build_call_context(agent, call_data, transport_type)
        build = await self.builder.build(
            transport,
            agent=agent,
            audio_buffer=audio_buffer,
            from_number=from_number,
            prompt_context=prompt_context,
            tool_call_entries=tool_call_entries,
            tool_request_ts=tool_request_ts,
            tool_proposals=tool_proposals,
            current_turn=current_turn,
            tool_dedup=tool_dedup,
            end_reason_holder=end_reason_holder,
            call_id_holder=call_id_holder,
            transcript_entries=transcript_entries,
        )
        task = build.task
        rtvi = build.rtvi
        is_s2s = build.is_s2s
        first_message_text = build.first_message_text
        metrics_collector = build.metrics_collector
        latency_observer = build.latency_observer
        turn_observer = build.turn_observer

        def _assemble_metrics() -> dict:
            """Collected pipeline metrics plus per-call latency samples and turn entries.

            Used by both completion paths (on_audio_data and the post-run fallback) so
            they persist the same metric shape.
            """
            metrics = metrics_collector.get_collected_metrics()
            metrics["user_bot_latency"] = [
                {"latency": round(l, 3)} for l in latency_observer._latencies
            ]
            metrics["turns"] = turn_entries
            return metrics

        # Collect transcripts via Pipecat's built-in aggregator events
        if agent:
            from pipecat.processors.aggregators.llm_response_universal import (
                AssistantTurnStoppedMessage, UserTurnStoppedMessage)

            @build.user_aggregator.event_handler("on_user_turn_stopped")
            async def on_user_turn_stopped(aggregator, strategy, message: UserTurnStoppedMessage):
                if not (message.content or "").strip():
                    return
                transcript_entries.append({
                    "role": "user",
                    "text": message.content,
                    "timestamp": message.timestamp,
                    # Snapshot the live turn number so downstream consolidation can
                    # join transcript rows to tool_executions and turn_metrics on
                    # the same key (see ConsolidatedTranscriptService).
                    "turn_number": current_turn.get("number"),
                })

            @build.assistant_aggregator.event_handler("on_assistant_turn_stopped")
            async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
                if not (message.content or "").strip():
                    return
                transcript_entries.append({
                    "role": "assistant",
                    "text": message.content,
                    "timestamp": message.timestamp,
                    "turn_number": current_turn.get("number"),
                })

        # Turn tracking — the same events drive (a) the simple ``turns``
        # log persisted alongside legacy metrics and (b) the per-turn
        # latency aggregation inside ``MetricsCollectorProcessor``.
        @turn_observer.event_handler("on_turn_started")
        async def on_turn_started(observer, turn_number):
            logger.info("Turn {} started", turn_number)
            # Keep ``current_turn`` in sync so tool handlers stamp the right
            # turn on their entries (they hold the dict by reference).
            current_turn["number"] = turn_number
            metrics_collector.on_turn_started(turn_number)

        @turn_observer.event_handler("on_turn_ended")
        async def on_turn_ended(observer, turn_number, duration, was_interrupted):
            status = "interrupted" if was_interrupted else "completed"
            logger.info("Turn {} {} after {:.2f}s", turn_number, status, duration)
            turn_entries.append({
                "turn": turn_number,
                "duration": round(duration, 3),
                "status": status,
            })
            metrics_collector.on_turn_ended(
                turn_number, duration=duration, was_interrupted=was_interrupted
            )

        # Save audio + update DB inside this event handler.
        # This runs DURING pipeline lifecycle (before cleanup() returns),
        # guaranteeing completion before the subprocess can be terminated.
        if audio_buffer:
            @audio_buffer.event_handler("on_audio_data")
            async def on_audio_data(processor, audio, sample_rate, num_channels):
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
                # Length of the encoded MP3 in seconds — what the audio player
                # actually plays. Stored on the call row so the UI's duration
                # chip lines up with the recording.
                recording_seconds: Optional[int] = None
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
                    recording_seconds_exact = len(audio_segment) / 1000.0
                    recording_seconds = int(recording_seconds_exact)
                    logger.info("Encoded call recording: {} ({:.1f}s, {} bytes)", file_name, recording_seconds_exact, len(audio_bytes))
                except Exception as e:
                    logger.exception("Failed to encode call recording")

                # Upload to Cloudflare R2 and update DB
                if call_log_id:
                    upload_id = None
                    r2_object_key = None
                    if audio_bytes and file_name:
                        try:
                            from core.services.r2_storage_service import (
                                CALL_RECORDING,
                                R2StorageService,
                                build_r2_object_key,
                            )
                            r2 = R2StorageService()
                            r2_object_key = build_r2_object_key(
                                org_id=agent.organization_id,
                                kind=CALL_RECORDING,
                                subpath=f"{agent_uuid_str}/{file_name}",
                            )
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
                            logger.exception("Failed to upload audio to R2")

                    try:
                        transcript_data = transcript_entries if transcript_entries else None

                        collected_metrics = _assemble_metrics()
                        merged_tool_entries = merge_and_synthesize(
                            tool_call_entries, tool_proposals,
                        )
                        with get_db_context() as db:
                            CallLogService(db).complete_call(
                                call_log_id=call_log_id,
                                audio_file_path=r2_object_key,
                                upload_id=upload_id,
                                transcript=transcript_data,
                                metrics=collected_metrics,
                                tool_calls=merged_tool_entries or None,
                                recording_duration_seconds=recording_seconds,
                                ended_reason=end_reason_holder.get("reason"),
                                ended_reason_detail=end_reason_holder.get("detail"),
                            )
                        call_log_updated["done"] = True
                        logger.info(
                            "Call log completed: id={} r2_key={} transcript_entries={} metrics_collected={} ended_reason={}",
                            call_log_id,
                            r2_object_key,
                            len(transcript_data) if transcript_data else 0,
                            {k: len(v) for k, v in collected_metrics.items()},
                            end_reason_holder.get("reason"),
                        )
                    except Exception as e:
                        logger.exception("Failed to complete call log in on_audio_data")
                        log_call_event(
                            EVENT_CALL_ENDED_ERROR,
                            call_id=str(call_log_id) if call_log_id else None,
                            source="on_audio_data_complete_call",
                            reason=end_reason_holder.get("reason"),
                            error_type=type(e).__name__,
                            error=str(e),
                        )

        # Idempotency guard: a single call must start the session ONCE. Some transports fire more
        # than one connect event (the outbound WebSocket client transport raises on_connected from
        # BOTH its input and output halves), which would otherwise greet twice and start recording
        # twice.
        session_started = {"done": False}

        async def _start_session():
            if session_started["done"]:
                logger.debug("Client connected again — session already started, ignoring.")
                return
            session_started["done"] = True
            if audio_buffer:
                logger.info("Client connected — starting audio recording.")
                await audio_buffer.start_recording()
            else:
                logger.info("Client connected.")
            if is_s2s:
                logger.info("Kicking off S2S conversation via LLMRunFrame")
                await task.queue_frames([LLMRunFrame()])
            elif first_message_text:
                logger.info("Speaking first_message via TTS: {}", first_message_text)
                await task.queue_frame(TTSSpeakFrame(text=first_message_text))

        async def _end_session(participant):
            logger.info("Client disconnected: {}", participant)
            # First-wins: only stamp client_disconnect if the LLM tool or the
            # keyword detector hasn't already claimed the reason. Those two
            # queue EndFrame first, which eventually causes the transport to
            # disconnect too — we don't want to relabel their attribution.
            claimed_here = False
            if end_reason_holder.get("reason") is None:
                end_reason_holder["reason"] = REASON_CLIENT_DISCONNECT
                claimed_here = True
            # Only emit the structured "call_ended" line if we're the origin
            # of the end. If the LLM tool or keyword already stamped a reason,
            # that path already emitted its own call_ended event — a second
            # line here would double-count in Grafana.
            if claimed_here:
                log_call_event(
                    EVENT_CALL_ENDED,
                    call_id=call_id_holder.get("id"),
                    reason=REASON_CLIENT_DISCONNECT,
                    source="transport",
                    participant=str(participant) if participant is not None else None,
                )
            try:
                await task.cancel()
            except Exception as e:
                log_call_event(
                    EVENT_CALL_ENDED_ERROR,
                    call_id=call_id_holder.get("id"),
                    source="transport_cancel",
                    error_type=type(e).__name__,
                    error=str(e),
                )
                logger.exception("task.cancel() failed during client disconnect")

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            logger.debug("Client ready event received")
            await rtvi.set_bot_ready()

        # Map whichever connect/disconnect pair this transport fires onto the same session
        # start/end (telephony on_client_*, LiveKit participant events, or the outbound WS
        # bridge's on_connected/on_disconnected) — one provider-agnostic hookup, no
        # transport-class string-typing. See _wire_session_events.
        _wire_session_events(transport, _start_session, _end_session)

        logger.info("[TIMING] runner setup complete, total: {:.3f}s — starting runner.run()", _time.monotonic() - _t_comp_start)
        runner = PipecatRunner(handle_sigint=getattr(runner_args, "handle_sigint", False))
        try:
            await runner.run(task)
        except asyncio.CancelledError:
            # Normal call teardown — the task is cancelled on hangup. Never swallow:
            # pipecat's cancel path depends on it propagating.
            raise
        except Exception:
            # The pipeline itself died (STT/LLM/TTS failure, transport error, …).
            # Log the full traceback and mark the call failed so it isn't left
            # dangling as "in progress", then re-raise for the caller's cleanup.
            logger.exception("[runner] pipeline run failed — marking call failed")
            call_log_id = await _get_call_log_id()
            if call_log_id:
                try:
                    with get_db_context() as db:
                        CallLogService(db).fail_call(call_log_id)
                except Exception:
                    logger.exception("[runner] fail_call failed for call_log_id={}", call_log_id)
            raise

        # Fallback: if on_audio_data didn't update DB (e.g. no audio captured),
        # update the call log here with whatever we have.
        call_log_id = await _get_call_log_id()
        call_duration_secs = _time.monotonic() - _t_comp_start
        if call_log_id and agent and not call_log_updated["done"]:
            # For /ws/test calls only: if the connection was very short with no
            # transcript, it was a failed/retried connection — delete to avoid duplicates.
            # Real telephony calls (Twilio/Telnyx/Plivo via /ws) always keep their log.
            if transport_type == "test" and call_duration_secs < 10 and not transcript_entries:
                logger.info("Short-lived test connection ({:.1f}s, no transcript) — deleting call_log id={}", call_duration_secs, call_log_id)
                try:
                    with get_db_context() as db:
                        CallLogService(db).delete_call(call_log_id)
                except Exception as e:
                    logger.exception("Failed to delete short call_log id={}", call_log_id)
            else:
                logger.info("on_audio_data did not complete DB update, running fallback for call_log_id={}", call_log_id)
                try:
                    transcript_data = transcript_entries if transcript_entries else None

                    collected_metrics = _assemble_metrics()
                    merged_tool_entries = merge_and_synthesize(
                        tool_call_entries, tool_proposals,
                    )
                    with get_db_context() as db:
                        CallLogService(db).complete_call(
                            call_log_id=call_log_id,
                            audio_file_path=None,
                            transcript=transcript_data,
                            metrics=collected_metrics,
                            tool_calls=merged_tool_entries or None,
                            ended_reason=end_reason_holder.get("reason"),
                            ended_reason_detail=end_reason_holder.get("detail"),
                        )
                    logger.info(
                        "Call log completed (fallback): id={} ended_reason={}",
                        call_log_id, end_reason_holder.get("reason"),
                    )
                except Exception as e:
                    logger.exception("Failed to complete call log id={}", call_log_id)
                    log_call_event(
                        EVENT_CALL_ENDED_ERROR,
                        call_id=str(call_log_id) if call_log_id else None,
                        source="fallback_complete_call",
                        reason=end_reason_holder.get("reason"),
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    try:
                        with get_db_context() as db:
                            CallLogService(db).fail_call(call_log_id)
                    except Exception as e_fail:
                        log_call_event(
                            EVENT_CALL_ENDED_ERROR,
                            call_id=str(call_log_id) if call_log_id else None,
                            source="fallback_fail_call",
                            error_type=type(e_fail).__name__,
                            error=str(e_fail),
                        )
