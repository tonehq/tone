"""Minimal pipecat pipeline harness for readiness probes.

Wraps a single pipecat service (TTS or STT) in a real ``Pipeline`` +
``PipelineTask`` so services that require the pipeline lifecycle
(``TaskManager``, ``StartFrame``, background WebSocket writers, VAD-driven
frame flow) work identically to how they behave in a live call. The only
thing that differs from production is the transport: the probe has no
caller, so we neither open a Twilio/LiveKit input nor emit audio to any
output — we just feed frames in and watch for the target output frame.

The whole probe path stays coherent with production:

* TTS: ``TTSSpeakFrame -> service -> TTSAudioRawFrame`` (matches the
  first-message greeting flow in ``core/services/pipeline/runner/pipecat.py``).
* STT: ``InputAudioRawFrame -> UserStoppedSpeakingFrame -> service ->
  TranscriptionFrame`` (matches the VAD/turn-analyzer signal at
  ``_handle_vad_user_stopped_speaking`` in the same runner).

If a service works in production, it works here — this is the whole point.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Callable, List, Optional, Tuple

from loguru import logger


# pipecat is heavy — keep the module import at usage sites so importing
# the readiness package at API boot doesn't drag it in.


async def probe_in_pipeline(
    service,
    input_frames: List,
    is_target: Callable,
    *,
    params,
    timeout_s: float,
    provider: str,
    warmup_s: float = 0.3,
) -> Tuple[bool, Optional[object], Optional[str]]:
    """Run ``service`` inside a minimal pipecat pipeline, feed ``input_frames``,
    and wait for a downstream frame satisfying ``is_target``.

    Returns ``(ok, target_frame, error_message)``:
      * ``ok=True, frame, None`` — target observed within budget.
      * ``ok=False, None, msg`` — provider ErrorFrame in the stream (msg is
        the error text) OR timeout (msg describes the timeout).

    Cleanup is guaranteed: ``task.cancel()`` runs even on timeout / exception,
    wrapped in ``asyncio.shield`` so a caller-side timeout doesn't strand
    WebSocket / aiohttp resources.
    """
    # Local imports — pipecat is optional at import time.
    from pipecat.frames.frames import ErrorFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    # ---- Frame capture sinks ------------------------------------------------
    #
    # Two capture points, one per direction — pipecat services push data frames
    # DOWNSTREAM (LLMTextFrame, TTSAudioRawFrame, TranscriptionFrame) and error
    # frames UPSTREAM (``FrameProcessor.push_error_frame`` → ``push_frame(
    # error, FrameDirection.UPSTREAM)``). A single downstream sink misses every
    # auth / quota / 4xx signal from OpenAI-compat providers (Grok, DeepSeek,
    # Cerebras, Fireworks, Perplexity, xAI, …) whose bad-key path emits
    # ``ErrorFrame`` upstream followed by a clean ``LLMFullResponseEndFrame``
    # downstream — the old probe accepted EndFrame as PASS and false-passed
    # every wrong Grok key it ever saw. Both queues feed the same
    # ``frames_out`` so the polling loop only has one thing to watch.

    frames_out: asyncio.Queue = asyncio.Queue()

    class _Capture(FrameProcessor):
        """Publishes every DOWNSTREAM frame it sees (the service's output)
        into ``frames_out``, then re-emits it so the pipeline keeps flowing.

        Defined here (not module-scope) so ``frames_out`` is captured by
        closure — one queue per probe run, no cross-talk between concurrent
        probes running under the readiness runner's asyncio.gather.
        """
        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if direction == FrameDirection.DOWNSTREAM:
                await frames_out.put(frame)
            await self.push_frame(frame, direction)

    class _UpstreamErrorObserver(FrameProcessor):
        """Sits at the pipeline source position so ``ErrorFrame``s pushed
        UPSTREAM by the service under test are observed here on their way
        back to the source. Transparent for every other frame — the pipeline
        lifecycle is unchanged, this only *watches*.
        """
        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            if direction == FrameDirection.UPSTREAM and isinstance(frame, ErrorFrame):
                await frames_out.put(frame)
            await self.push_frame(frame, direction)

    error_observer = _UpstreamErrorObserver()
    capture = _Capture()

    # ---- Pipeline + Task construction ---------------------------------------
    #
    # Strip PipelineTask down to just what we need. Defaults would give us:
    #   - enable_turn_tracking=True → turn observer expects turn events
    #     the probe never emits.
    #   - enable_rtvi=True → an RTVI processor injected upstream that we
    #     don't need for a headless probe.
    #   - check_dangling_tasks=True → shouts on cleanup if the service
    #     leaves anything behind, noisy in the probe path.

    # ``error_observer`` first: upstream ErrorFrames from ``service`` pass
    # through it on their way back to the pipeline source, so bad-key /
    # quota / 4xx signals surface here instead of being silently swallowed.
    pipeline = Pipeline([error_observer, service, capture])
    task = PipelineTask(
        pipeline,
        params=params,
        enable_turn_tracking=False,
        enable_rtvi=False,
        check_dangling_tasks=False,
        idle_timeout_secs=None,   # we own the timeout below
    )
    runner = PipelineRunner(handle_sigint=False)

    # ---- Drive the task -----------------------------------------------------
    #
    # PipelineRunner.run(task) blocks until the task ends (EndFrame /
    # CancelFrame propagates through). We run it as a background task so
    # we can concurrently feed input frames and watch the capture queue.

    async def _feed_after_start():
        # Wait for the service to be ready to receive data. WS-based providers
        # (streaming STT: Deepgram, AssemblyAI, Soniox, Sarvam, Gladia;
        # streaming TTS: ElevenLabs, Cartesia) schedule the actual WebSocket
        # handshake in a background task from their ``_connect`` method — so
        # ``StartFrame`` propagates in microseconds but the connection isn't
        # actually usable until the handshake completes 200ms-2s later.
        # Deepgram's ``run_stt`` (line 539) and ``_handle_vad_user_stopped``
        # (line 746) both guard on ``if self._connection:`` and silently drop
        # audio / skip finalize when the connection isn't up — a probe that
        # pushes data too early sees zero transcripts on a HEALTHY provider
        # and times out.
        #
        # Two paths:
        #   1) Service exposes an ``asyncio.Event`` readiness signal
        #      (Deepgram's ``_connection_ready``). Wait for it up to
        #      ``warmup_s`` and proceed as soon as it fires — no wasted
        #      latency on a fast handshake.
        #   2) No explicit signal (most services). Sleep the full ``warmup_s``
        #      as a best-effort budget.
        ready = getattr(service, "_connection_ready", None)
        if isinstance(ready, asyncio.Event):
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(ready.wait(), timeout=warmup_s)
        else:
            await asyncio.sleep(warmup_s)
        for f in input_frames:
            await task.queue_frame(f)

    runner_task = asyncio.create_task(runner.run(task), name=f"probe-runner-{provider}")
    feeder_task = asyncio.create_task(_feed_after_start(), name=f"probe-feed-{provider}")

    target_frame: Optional[object] = None
    error_msg: Optional[str] = None
    runner_exc: Optional[BaseException] = None
    deadline = time.monotonic() + timeout_s

    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            # Short-circuit when the runner died before emitting any frame
            # (e.g. provider raised AuthenticationError inside the LLM
            # service). Without this the caller would wait the full budget
            # and see a misleading "no target frame" timeout instead of the
            # real auth failure.
            if runner_task.done():
                try:
                    runner_exc = runner_task.exception()
                except (asyncio.CancelledError, asyncio.InvalidStateError):
                    runner_exc = None
                if runner_exc is not None:
                    break
            try:
                # Cap the per-tick wait so a dead runner is noticed within
                # ~0.5s instead of hanging on ``frames_out.get()`` for the
                # full timeout budget.
                frame = await asyncio.wait_for(
                    frames_out.get(), timeout=min(remaining, 0.5)
                )
            except asyncio.TimeoutError:
                continue
            # ErrorFrame short-circuit: no point waiting the full budget when
            # the provider already told us it failed (auth, quota, WS reject).
            if isinstance(frame, ErrorFrame):
                error_msg = str(getattr(frame, "error", "") or "provider emitted an error frame")
                break
            if is_target(frame):
                target_frame = frame
                break
    finally:
        # ``_teardown`` returns the runner's stored exception (if any) so we
        # can classify it via ``_summarise_error`` upstream. Assigning the
        # awaited result inside ``finally`` is safe — shield protects it
        # from an outer cancel.
        teardown_exc = await asyncio.shield(
            _teardown(task, runner_task, feeder_task, provider)
        )
        if runner_exc is None:
            runner_exc = teardown_exc

    if target_frame is not None:
        return True, target_frame, None
    if error_msg:
        return False, None, error_msg
    if runner_exc is not None:
        # Surface the provider's real exception. ``_summarise_error`` in
        # probes.py buckets this into auth / quota / rate-limit / etc.
        return False, None, str(runner_exc)
    return False, None, f"no target frame observed within {timeout_s:.0f}s"


async def _teardown(
    task, runner_task: asyncio.Task, feeder_task: asyncio.Task, provider: str
) -> Optional[BaseException]:
    """Cancel the runner, drain the feeder, close the task — best-effort but
    never re-raises. WS providers occasionally hang on close; we bound the
    join with a hard cap so a stuck provider doesn't stall the whole
    readiness report.

    Returns the runner task's stored exception (if any) so the caller can
    surface a real auth / quota / rate-limit message instead of a generic
    "no target frame" timeout. Returns ``None`` when the runner completed
    cleanly or was cancelled.
    """
    # Kill the feeder first — it's the only thing that could still be queuing
    # data into a task we're about to cancel.
    feeder_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await feeder_task

    try:
        await task.cancel()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[readiness] {} pipeline task.cancel raised: {}", provider, exc)

    with contextlib.suppress(asyncio.CancelledError, Exception):
        await asyncio.wait_for(runner_task, timeout=3.0)
    if not runner_task.done():
        runner_task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await runner_task

    # Extract the runner's exception without re-raising. A cancelled task
    # has no exception in the sense we care about; an unfinished task can't
    # be queried yet — return None in both cases.
    if runner_task.done() and not runner_task.cancelled():
        try:
            return runner_task.exception()
        except (asyncio.CancelledError, asyncio.InvalidStateError):
            return None
    return None
