"""Observer that stamps ``llm_requested_at`` for every tool call.

Pipecat pushes a ``FunctionCallInProgressFrame`` the moment the LLM asks for a
tool call, before the registered handler runs. We stamp that moment into the
per-call ``tool_request_ts`` map, keyed by ``tool_call_id``. Handlers then pop
the stamp inside :class:`~core.services.pipeline.tool_call_timing.ToolCallTimer`.

Kept single-purpose so it can coexist with the other observers (latency,
turn tracking, metrics) without side-effects.
"""

from pipecat.frames.frames import FunctionCallInProgressFrame
from pipecat.observers.base_observer import BaseObserver, FramePushed

from core.services.pipeline.tool_call_timing import (
    ToolRequestTsMap,
    record_llm_request,
)


class ToolCallRequestObserver(BaseObserver):
    """Records the LLM-request moment for each tool call into a shared dict."""

    def __init__(self, tool_request_ts: ToolRequestTsMap) -> None:
        super().__init__()
        self._tool_request_ts = tool_request_ts

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame
        if isinstance(frame, FunctionCallInProgressFrame):
            record_llm_request(self._tool_request_ts, getattr(frame, "tool_call_id", None))
