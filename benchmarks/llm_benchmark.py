from __future__ import annotations

from typing import Any, Dict, List

from benchmarks.base import BaseBenchmark
from core.services.pipeline import service_factory
from pipecat.frames.frames import (
    EndFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMTextFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext

DEFAULT_PROMPT = "Reply with one short sentence about scheduling a dental appointment."


class LLMBenchmark(BaseBenchmark):
    service_type = "llm"
    timeout_s = 30.0
    warmup_s = 0.0

    def __init__(self, spec: Dict[str, Any], *, prompt: str = DEFAULT_PROMPT, **kwargs):
        super().__init__(spec, **kwargs)
        self.prompt = prompt

    def build_service(self) -> Any:
        return service_factory.build_llm(self.spec)

    def input_frames(self, _service: Any) -> List[Any]:
        context = LLMContext(messages=[{"role": "user", "content": self.prompt}])
        return [LLMContextFrame(context=context), EndFrame()]

    def is_target(self, frame: Any) -> bool:
        if isinstance(frame, LLMTextFrame):
            return bool((getattr(frame, "text", "") or "").strip())
        return isinstance(frame, LLMFullResponseEndFrame)

    def is_complete(self, frame: Any) -> bool:
        return isinstance(frame, LLMFullResponseEndFrame)

    def sample_detail(self, frame: Any) -> Dict[str, Any]:
        text = (getattr(frame, "text", "") or "").strip()
        return {"first_token": text[:60]} if text else {}
