"""Observer that captures every LLM-proposed tool call for a call.

Pipecat's ``LLMService.run_function_calls`` emits two frames per tool_call_id
that we care about here:

* ``FunctionCallsStartedFrame`` — the LLM decided to invoke a batch of tools
  (one or more ``FunctionCallFromLLM`` entries). This is the earliest, most
  reliable signal that "the LLM asked for this tool" — captured even when the
  pipeline never dispatches a handler (unregistered tool name) or when the
  user interrupts mid-batch.
* ``FunctionCallCancelFrame`` — a specific tool_call_id has been cancelled
  before it could complete (usually a barge-in during handler execution).

The observer stamps each proposal into the runner-owned proposals map keyed
by ``tool_call_id`` so the call-completion merge step
(``merge_and_synthesize``) can (a) attribute ``proposed_at`` to executed rows
and (b) synthesise rows for proposals that never executed. Kept
single-purpose so it can coexist with the other observers without
side-effects.
"""

from typing import Any, Optional

from pipecat.frames.frames import (
    FunctionCallCancelFrame,
    FunctionCallsStartedFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed

from core.services.pipeline.tool_call_timing import (
    ToolProposalMap,
    record_cancel,
    record_proposal,
)


# Human-readable label persisted alongside cancelled proposals — makes the
# per-row error_message self-explanatory in the UI without having to infer
# "why is this cancelled" from surrounding metrics.
_CANCEL_REASON = "cancelled during call (barge-in or pipeline stop)"


class ToolCallProposalObserver(BaseObserver):
    """Records LLM-proposed tool calls into the shared proposals map.

    ``current_turn`` is the runner-owned ``{"number": int}`` dict shared with
    other handlers so proposals snapshot the turn that was live when the LLM
    emitted them — which is what the consolidated per-turn view groups on.
    """

    def __init__(
        self,
        proposals: ToolProposalMap,
        current_turn: Optional[Any] = None,
    ) -> None:
        super().__init__()
        self._proposals = proposals
        self._current_turn = current_turn

    def _turn_number(self) -> Optional[int]:
        if self._current_turn is None:
            return None
        return self._current_turn.get("number")

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame
        if isinstance(frame, FunctionCallsStartedFrame):
            turn_number = self._turn_number()
            for call in frame.function_calls or ():
                record_proposal(
                    self._proposals,
                    tool_call_id=getattr(call, "tool_call_id", None),
                    tool_name=getattr(call, "function_name", None),
                    arguments=getattr(call, "arguments", None),
                    turn_number=turn_number,
                )
            return

        if isinstance(frame, FunctionCallCancelFrame):
            record_cancel(
                self._proposals,
                tool_call_id=getattr(frame, "tool_call_id", None),
                reason=_CANCEL_REASON,
            )
