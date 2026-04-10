"""Processor to collect pipeline metrics (TTFB, processing time, token usage, TTS usage)."""

from typing import List

from loguru import logger
from pipecat.frames.frames import Frame, MetricsFrame
from pipecat.metrics.metrics import (
    LLMUsageMetricsData,
    ProcessingMetricsData,
    TTFBMetricsData,
    TTSUsageMetricsData,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class MetricsCollectorProcessor(FrameProcessor):
    """Collects metrics from MetricsFrame objects flowing through the pipeline.

    Stores TTFB, processing time, LLM token usage, and TTS character usage
    in lists that can be retrieved after the call ends.

    Pipeline placement: at the end of the pipeline (after transport.output()).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ttfb_metrics: List[dict] = []
        self.processing_metrics: List[dict] = []
        self.llm_usage_metrics: List[dict] = []
        self.tts_usage_metrics: List[dict] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, MetricsFrame):
            for data in frame.data:
                if isinstance(data, TTFBMetricsData):
                    self.ttfb_metrics.append({
                        "processor": data.processor,
                        "model": data.model,
                        "value": data.value,
                    })
                elif isinstance(data, ProcessingMetricsData):
                    self.processing_metrics.append({
                        "processor": data.processor,
                        "model": data.model,
                        "value": data.value,
                    })
                elif isinstance(data, LLMUsageMetricsData):
                    usage = data.value
                    self.llm_usage_metrics.append({
                        "processor": data.processor,
                        "model": data.model,
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens,
                    })
                elif isinstance(data, TTSUsageMetricsData):
                    self.tts_usage_metrics.append({
                        "processor": data.processor,
                        "model": data.model,
                        "characters": data.value,
                    })

        await self.push_frame(frame, direction)

    def get_collected_metrics(self) -> dict:
        """Return all collected metrics as a dictionary."""
        return {
            "ttfb": self.ttfb_metrics,
            "processing": self.processing_metrics,
            "llm_usage": self.llm_usage_metrics,
            "tts_usage": self.tts_usage_metrics,
        }
