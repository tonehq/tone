"""end_call: LLM-driven call termination tool.

Registered automatically for every agent. The LLM calls this when it judges
the user wants to end the conversation (says goodbye, signals completion,
thanks with no follow-up, asks to hang up, etc.). The handler queues an
EndFrame onto the pipeline worker, which gracefully tears down the pipeline
(TTS finishes any current speech, then transports disconnect).

Companion to the keyword-based ``CallEndDetectorProcessor``: that processor
remains the fast-path for explicit "bye"/"goodbye" utterances configured in
``agent_config.end_call_message``. This tool covers the long tail of natural
endings keyword matching can never anticipate ("alright I'll let you go",
"appreciate it, take care", etc.).
"""

import time as _time
from typing import Callable, List, Optional

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import EndFrame
from pipecat.services.llm_service import FunctionCallParams


END_CALL_TOOL_NAME = "end_call"


END_CALL_TOOL_SCHEMA = FunctionSchema(
    name=END_CALL_TOOL_NAME,
    description=(
        "End the current voice call. Call this ONLY when the user clearly "
        "signals they want to end the conversation. Signals include: saying "
        "goodbye, thanking you with no follow-up question, indicating they are "
        "done, or explicitly asking to hang up. DO NOT call this if the user "
        "has a pending question, is mid-sentence, or is just thanking you in "
        "the middle of the conversation."
    ),
    properties={
        "reason": {
            "type": "string",
            "description": (
                "Short reason for ending the call, e.g. 'user said goodbye', "
                "'user completed booking and had no more questions'."
            ),
        },
    },
    required=["reason"],
)


END_CALL_SYSTEM_PROMPT = (
    "\n\n## Ending the call\n"
    "You have a tool called `end_call`. Use it ONLY when the user has explicitly "
    "signaled they want to end the conversation. Examples of valid signals:\n"
    "- Explicit goodbye: \"bye\", \"goodbye\", \"have a good day\", \"talk to you later\"\n"
    "- Polite closure: \"thanks, that's all\", \"appreciate the help\", \"I'll let you go\"\n"
    "- Direct: \"hang up\", \"end the call\"\n"
    "DO NOT call `end_call` when:\n"
    "- The user has a pending question or is mid-sentence\n"
    "- The user just thanked you mid-conversation and is still engaged\n"
    "- It is unclear whether the user wants to continue\n"
    "- The task appears complete (booking taken, question answered, details "
    "collected) but the user has NOT said goodbye — ask if there is anything "
    "else instead\n"
    "If you are unsure whether the user wants to end, DO NOT call `end_call`. "
    "Ask \"Is there anything else I can help you with?\" and wait for their reply.\n"
    "Optionally speak a brief one-sentence farewell BEFORE calling the tool. "
    "After calling it, the call ends automatically — do not generate further text.\n"
)


def inject_end_call_instructions(messages: List[dict]) -> List[dict]:
    """Append the end_call usage block to the first system message.

    Returns a new list; never mutates the input. No-op (returns list unchanged)
    if there is no system message — keeping the contract identical to
    ``messages_with_date_anchor``.
    """
    out: List[dict] = []
    injected = False
    for m in messages:
        if not injected and m.get("role") == "system":
            out.append({**m, "content": (m.get("content") or "") + END_CALL_SYSTEM_PROMPT})
            injected = True
        else:
            out.append(m)
    return out


def create_end_call_handler(
    *,
    tool_call_entries: Optional[list] = None,
    current_turn: Optional[dict] = None,
) -> Callable:
    """Factory: build a handler that pushes EndFrame to gracefully end the call.

    Mirrors the shape of the built-in handlers in ``custom_tool_service``:
    appends one entry to ``tool_call_entries`` for the per-call log and invokes
    ``params.result_callback`` so the LLM sees a tool result. EndFrame goes onto
    the pipeline worker — pipecat drains downstream queues (TTS) before
    actually terminating, so any farewell already in flight will be heard.
    """

    # Closure-mutable single-fire guard. The LLM occasionally double-calls a
    # tool on the same turn; we want a strict at-most-once EndFrame.
    state = {"fired": False}

    async def handle_end_call(params: FunctionCallParams) -> None:
        reason = (params.arguments or {}).get("reason", "unspecified")
        _t_start = _time.monotonic()

        entry = {
            "tool": END_CALL_TOOL_NAME,
            "tool_type": "built_in",
            "arguments": {"reason": reason},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
        }

        if state["fired"]:
            logger.info(
                "end_call invoked again — ignoring (already ending). reason={!r}", reason
            )
            entry["result"] = "ignored: already ending"
            entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(entry)
            await params.result_callback("Call is already ending.")
            return

        state["fired"] = True
        logger.info("LLM end_call invoked — ending pipeline. reason={!r}", reason)

        try:
            await params.pipeline_worker.queue_frame(EndFrame())
            entry["result"] = "ending"
        except Exception as e:
            logger.error("Failed to queue EndFrame from end_call handler: {}", e)
            entry["result"] = f"error: {e}"

        entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
        if tool_call_entries is not None:
            tool_call_entries.append(entry)

        await params.result_callback("Call ending now.")

    return handle_end_call
