"""Framework-agnostic pipeline builder interface + build result."""

from dataclasses import dataclass
from typing import Any, Optional

from core.services.pipeline.params.base import PipelineParams


@dataclass
class BuildResult:
    """Everything a runner needs to execute and observe a built pipeline."""

    pipeline: Any
    task: Any
    context: Any
    user_aggregator: Any
    assistant_aggregator: Any
    rtvi: Any
    audio_buffer: Optional[Any]
    metrics_collector: Any
    metrics_observer: Any
    latency_observer: Any
    turn_observer: Any
    llm: Any
    stt: Optional[Any]
    tts: Optional[Any]
    is_s2s: bool
    first_message_text: Optional[str]


class PipelineBuilder:
    """Builds a voice pipeline from a `PipelineParams`. Subclass per framework."""

    def __init__(self, params: PipelineParams):
        self.params = params

    async def build(self, transport: Any, agent: Any = None, audio_buffer: Any = None, from_number: str = "") -> BuildResult:
        raise NotImplementedError
