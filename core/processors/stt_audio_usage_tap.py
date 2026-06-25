"""STT audio-usage derivation tap.

Sits just upstream of the STT service to measure how much audio (in
milliseconds) is being sent into the STT provider. Pipecat does not
emit any STT usage metric natively — it only reports STT TTFB. STT
providers (Deepgram, AssemblyAI, Speechmatics, Whisper, ...) all bill on
audio duration sent to them, so this gap must be filled in Tone if STT
cost is to be billed accurately.

Why a tap (and not a service subclass)
--------------------------------------
Subclassing each STT service to add a usage counter would duplicate the
logic across every provider integration. A single pipeline tap placed
before the STT processor sees the same ``AudioRawFrame``s the STT
service is about to consume, so it naturally measures what each provider
will be billed on without per-provider code.

Pipeline placement
------------------
Insert immediately before the STT service::

    transport.input → rtvi → vad_timeout → stt_audio_usage_tap → stt → ...

Frame contract
--------------
Every frame is passed through unchanged. Side effects:

* On ``AudioRawFrame`` going downstream — if the wrapped STT service is
  not muted, add the chunk's duration (ms) to the per-utterance and
  per-call accumulators. Muted audio is skipped because pipecat's STT
  base class drops muted frames before forwarding them to the provider,
  so we should not bill for them.

* On ``UserStoppedSpeakingFrame`` — flush the per-utterance accumulator
  as one ``MetricsFrame`` carrying ``STTUsageMetricsData``. This bucket
  lands inside the active turn buffer in ``MetricsCollectorProcessor``,
  giving per-turn STT-usage granularity.

* On ``EndFrame`` / ``CancelFrame`` — flush any remaining accumulated
  audio (e.g. straggler frames after the last user-stop) so a full-call
  total never silently loses bytes.

Duration formula
----------------
The standard PCM bytes-to-seconds formula::

    seconds = len(audio_bytes) / (sample_rate × num_channels × bytes_per_sample)

Pipecat hard-codes 16-bit PCM throughout (see ``AudioRawFrame.num_frames``
in ``pipecat/frames/frames.py:220`` which divides by ``num_channels * 2``),
so ``bytes_per_sample`` is always 2. The sample rate and channel count are
read directly off each frame so a Twilio 8k transport and a Daily 16k/24k
transport both produce correct durations.
"""

from typing import Optional

from pipecat.frames.frames import (
    AudioRawFrame,
    CancelFrame,
    EndFrame,
    Frame,
    MetricsFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import MetricsData
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class STTUsageMetricsData(MetricsData):
    """Audio duration (ms) consumed by an STT service.

    Mirrors pipecat's ``TTSUsageMetricsData`` shape — ``processor`` + ``model``
    identify the service, ``value`` carries the billable unit (milliseconds
    of audio sent to the provider).
    """

    value: int


class STTAudioUsageTap(FrameProcessor):
    """Counts audio sent into an STT service and emits per-utterance usage frames.

    Args:
        stt: The STT service instance whose audio input we're metering. The
            tap reads ``stt.is_muted`` to decide whether a given frame counts,
            and uses ``stt.name`` to label the emitted ``STTUsageMetricsData``
            (so the metrics collector can attribute the usage by the same
            processor name it already uses for STT TTFB).
        stt_model_name: Configured STT model name (from the resolved spec).
            Used as a fallback when the underlying STT instance doesn't set
            ``model_name`` in its constructor — some services (e.g. the
            shared ``NvidiaWebSocketService`` used by voxtral/gemma) leave
            it as the empty-string default, which would otherwise surface as
            ``null`` in the UI's model column.
    """

    def __init__(self, *, stt, stt_model_name: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._stt = stt
        self._fallback_model = stt_model_name
        # Per-utterance accumulator, flushed on UserStoppedSpeakingFrame.
        self._utterance_ms: float = 0.0
        # Trailing accumulator for audio that arrives after the last
        # UserStoppedSpeakingFrame (e.g. during bot speech, or right before
        # the pipeline ends). Flushed on EndFrame / CancelFrame.
        self._trailing_ms: float = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, AudioRawFrame) and direction == FrameDirection.DOWNSTREAM:
            self._maybe_count(frame)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            await self._flush_utterance()
        elif isinstance(frame, (EndFrame, CancelFrame)):
            # Drain anything still pending. Order matters: utterance first
            # (in case the call ended mid-utterance), then any trailing
            # audio caught after the last stop.
            await self._flush_utterance()
            await self._flush_trailing()

        await self.push_frame(frame, direction)

    def _maybe_count(self, frame: AudioRawFrame) -> None:
        """Add this frame's duration to the active accumulator.

        Skips when the STT service is muted — pipecat's STT base class
        drops muted audio in ``process_audio_frame`` before forwarding to
        the provider, so the provider does not bill for it.
        """
        if getattr(self._stt, "is_muted", False):
            return
        sample_rate = getattr(frame, "sample_rate", 0) or 0
        channels = getattr(frame, "num_channels", 1) or 1
        if sample_rate <= 0:
            return
        # 16-bit PCM throughout pipecat → 2 bytes per sample.
        seconds = len(frame.audio) / (sample_rate * channels * 2)
        self._utterance_ms += seconds * 1000.0
        self._trailing_ms += seconds * 1000.0

    async def _flush_utterance(self) -> None:
        """Emit per-utterance usage. Resets the utterance accumulator.

        The trailing accumulator is also reset because every byte the
        utterance flush includes was already counted in the trailing
        running total — we don't want EndFrame to double-emit them.
        """
        if self._utterance_ms <= 0:
            return
        await self._emit(round(self._utterance_ms))
        self._utterance_ms = 0.0
        self._trailing_ms = 0.0

    async def _flush_trailing(self) -> None:
        """Emit any remaining audio caught after the last user-stop."""
        if self._trailing_ms <= 0:
            return
        await self._emit(round(self._trailing_ms))
        self._trailing_ms = 0.0

    async def _emit(self, audio_ms: int) -> None:
        # Prefer the runtime instance's model_name (what's actually serving the
        # call — covers Deepgram's `nova-3-general` default and any provider
        # that called `set_model_name` in its constructor). Fall back to the
        # configured spec model so STTs that don't populate `model_name`
        # (NvidiaWebSocketService → voxtral/gemma) still surface a usable label.
        runtime_model = getattr(self._stt, "model_name", None) or None
        model = runtime_model or self._fallback_model
        data = STTUsageMetricsData(
            processor=getattr(self._stt, "name", "stt"),
            model=model,
            value=audio_ms,
        )
        await self.push_frame(MetricsFrame(data=[data]), FrameDirection.DOWNSTREAM)
