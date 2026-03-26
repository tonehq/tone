"""Processor to record call audio (both caller and bot) and save as MP3."""

import os

from loguru import logger
from pydub import AudioSegment
from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

# Default directory for storing recordings
RECORDINGS_DIR = os.path.join(os.getcwd(), "recordings")


class AudioRecorderProcessor(FrameProcessor):
    """Records raw audio frames from both input (caller) and output (bot) and
    saves the combined audio as an MP3 file when the call ends.

    Each call subprocess has its own instance, so there is no cross-call mixing.
    """

    def __init__(self, call_id: str, agent_uuid: str, sample_rate: int = 8000, num_channels: int = 1, **kwargs):
        super().__init__(**kwargs)
        self._call_id = call_id
        self._agent_uuid = agent_uuid
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        self._audio_chunks: list[bytes] = []
        self._saved_path: str | None = None

    @property
    def saved_path(self) -> str | None:
        return self._saved_path

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Capture audio from both directions
        if isinstance(frame, (InputAudioRawFrame, OutputAudioRawFrame)):
            self._audio_chunks.append(frame.audio)

        await self.push_frame(frame, direction)

    def save(self):
        """Save captured audio to disk. Call this after the pipeline finishes."""
        try:
            self._save_audio()
        except Exception as e:
            logger.error("Failed to save call recording for call_id={}: {}", self._call_id, e)

    def _save_audio(self):
        if not self._audio_chunks:
            logger.warning("No audio data captured for call_id={}", self._call_id)
            return

        raw_audio = b"".join(self._audio_chunks)

        # Convert raw PCM to AudioSegment
        audio_segment = AudioSegment(
            data=raw_audio,
            sample_width=2,  # 16-bit PCM
            frame_rate=self._sample_rate,
            channels=self._num_channels,
        )

        # Ensure output directory exists
        output_dir = os.path.join(RECORDINGS_DIR, self._agent_uuid)
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"{self._call_id}.mp3")
        audio_segment.export(file_path, format="mp3")

        self._saved_path = file_path
        self._audio_chunks.clear()
        logger.info("Saved call recording: {} ({:.1f}s)", file_path, len(audio_segment) / 1000)
