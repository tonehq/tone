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

from core.services.pipeline.runner.base import PipelineRunner


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
        current_turn: dict = {"number": 0}
        tool_dedup: dict = {}
        call_log_updated = {"done": False}
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
                return {
                    "provider_name": spec.get("provider_name"),
                    "model_name": spec.get("model_name"),
                    "model_id": str(model_id) if model_id is not None else None,
                }

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
                            organization_id=agent.organization_id,
                            provider_call_id=provider_call_id,
                            transport_type=transport_type,
                            from_number=from_number,
                            to_number=to_number,
                            trace_id=_call_trace_id if _call_trace_id != "none" else None,
                            pipeline_config=pipeline_snapshot,
                            started_at=call_started_at,
                        )
                        if call_log:
                            call_log_state["id"] = call_log.id
                            logger.info("[TIMING] create_call_log thread (+%.3fs)", _time.monotonic() - _t)
                        else:
                            logger.warning("create_call_log returned None (no channel resolved) — no call record created")
                except Exception as e:
                    logger.error("Failed to create call log: {}", e)
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
            current_turn=current_turn,
            tool_dedup=tool_dedup,
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
                transcript_entries.append({
                    "role": "user",
                    "text": message.content,
                    "timestamp": message.timestamp,
                })

            @build.assistant_aggregator.event_handler("on_assistant_turn_stopped")
            async def on_assistant_turn_stopped(aggregator, message: AssistantTurnStoppedMessage):
                transcript_entries.append({
                    "role": "assistant",
                    "text": message.content,
                    "timestamp": message.timestamp,
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
                    logger.error("Failed to encode call recording: {}", e)

                # Upload to Cloudflare R2 and update DB
                if call_log_id:
                    upload_id = None
                    r2_object_key = None
                    if audio_bytes and file_name:
                        try:
                            from core.services.r2_storage_service import R2StorageService
                            r2 = R2StorageService()
                            r2_object_key = f"{agent_uuid_str}/{file_name}"
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
                            logger.error("Failed to upload audio to R2: {}", e)

                    try:
                        transcript_data = transcript_entries if transcript_entries else None

                        collected_metrics = _assemble_metrics()
                        with get_db_context() as db:
                            CallLogService(db).complete_call(
                                call_log_id=call_log_id,
                                audio_file_path=r2_object_key,
                                upload_id=upload_id,
                                transcript=transcript_data,
                                metrics=collected_metrics,
                                tool_calls=tool_call_entries or None,
                                recording_duration_seconds=recording_seconds,
                            )
                        call_log_updated["done"] = True
                        logger.info(
                            "Call log completed: id={} r2_key={} transcript_entries={} metrics_collected={}",
                            call_log_id,
                            r2_object_key,
                            len(transcript_data) if transcript_data else 0,
                            {k: len(v) for k, v in collected_metrics.items()},
                        )
                    except Exception as e:
                        logger.error("Failed to complete call log in on_audio_data: {}", e)

        # Start recording and speak first_message when client connects
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            if audio_buffer:
                logger.info("Client connected — starting audio recording.")
                await audio_buffer.start_recording()
            else:
                logger.info("Client connected.")
            if is_s2s:
                # S2S: kick off the conversation — context already has the messages
                logger.info("Kicking off S2S conversation via LLMRunFrame")
                await task.queue_frames([LLMRunFrame()])
            elif first_message_text:
                logger.info("Speaking first_message via TTS: {}", first_message_text)
                await task.queue_frame(TTSSpeakFrame(text=first_message_text))

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            logger.debug("Client ready event received")
            await rtvi.set_bot_ready()

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, participant):
            logger.info("Client disconnected: {}", participant)
            await task.cancel()

        logger.info("[TIMING] runner setup complete, total: %.3fs — starting runner.run()", _time.monotonic() - _t_comp_start)
        runner = PipecatRunner(handle_sigint=getattr(runner_args, "handle_sigint", False))
        await runner.run(task)

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
                    logger.error("Failed to delete short call_log id={}: {}", call_log_id, e)
            else:
                logger.info("on_audio_data did not complete DB update, running fallback for call_log_id={}", call_log_id)
                try:
                    transcript_data = transcript_entries if transcript_entries else None

                    collected_metrics = _assemble_metrics()
                    with get_db_context() as db:
                        CallLogService(db).complete_call(
                            call_log_id=call_log_id,
                            audio_file_path=None,
                            transcript=transcript_data,
                            metrics=collected_metrics,
                            tool_calls=tool_call_entries or None,
                        )
                    logger.info("Call log completed (fallback): id={}", call_log_id)
                except Exception as e:
                    logger.error("Failed to complete call log id={}: {}", call_log_id, e)
                    try:
                        with get_db_context() as db:
                            CallLogService(db).fail_call(call_log_id)
                    except Exception:
                        pass
