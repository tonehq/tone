"""end_call: LLM-driven call termination tool.

The single, canonical path for ending a call. Registered automatically for
every agent. The LLM must follow a mandatory two-step confirmation encoded
in ``END_CALL_SYSTEM_PROMPT``: it asks "Can I end the call?" first, waits
for an explicit user confirmation, then speaks a farewell and calls this
tool. The handler queues an EndFrame onto the pipeline worker, which
gracefully tears down the pipeline (TTS finishes any current speech, then
transports disconnect).

A prior keyword-matching fast-path (CallEndDetectorProcessor) was removed
so all end-of-call decisions flow through this same confirmation gate —
eliminating false hangups from STT mistranscriptions and single-word triggers.
"""

import re
import time as _time
from typing import Callable, List, Optional

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import EndFrame
from pipecat.services.llm_service import FunctionCallParams

from core.services.pipeline.call_end_events import (
    EVENT_CALL_ENDED,
    EVENT_END_CALL_BLOCKED,
    REASON_LLM_END_CALL,
    log_call_event,
)


# Regex describing the phrasings the LLM uses to ask "may I end the call?".
# Matches the assistant text that precedes the user's confirmation reply.
# Case-insensitive; anchored on word boundaries.
_CONFIRMATION_ASK_PATTERN = re.compile(
    r"\b("
    r"end (?:the |this |our )?call|"
    r"end (?:the |our )?conversation|"
    r"hang up|"
    r"close (?:the |this )?call|"
    r"finish (?:the |this |up )?call|"
    r"wrap (?:up|things up|this up)|"
    r"can i end|"
    r"shall i end|"
    r"may i end|"
    r"should i end|"
    r"okay (?:to|for me to) end|"
    r"anything else"
    r")\b",
    re.IGNORECASE,
)


def _confirmation_valid(transcript_entries: Optional[list]) -> bool:
    """Return True iff the two-step confirmation was actually completed.

    The confirmation flow is:
      1. Assistant asks "Can I end the call?" (matches ``_CONFIRMATION_ASK_PATTERN``).
      2. User replies (any content).
      3. Assistant fires end_call.

    We validate that (1) and (2) both happened in that order by looking at
    the assistant turn(s) immediately preceding the user's most recent turn.
    If any of those assistant turns contain a confirmation ask, the flow
    is valid. Otherwise the LLM tried to skip step 1 and we refuse.

    ``transcript_entries`` is the runner-owned list populated by the
    aggregator handlers; ``None`` (unwired) falls back to allowing the call
    to end so a mis-wired build cannot deadlock all calls.
    """
    if transcript_entries is None:
        return True  # Backward-compat: unwired transcript → skip the check.
    if not transcript_entries:
        return False

    # Walk backwards for the most recent user turn.
    last_user_idx = None
    for i in range(len(transcript_entries) - 1, -1, -1):
        if transcript_entries[i].get("role") == "user":
            last_user_idx = i
            break
    if last_user_idx is None:
        return False  # No user turn yet — nothing could have been confirmed.

    # Immediately-preceding contiguous assistant turns must include a
    # confirmation ask. (LLM may stream multiple assistant messages in a
    # single turn; scan all of them.)
    for i in range(last_user_idx - 1, -1, -1):
        entry = transcript_entries[i]
        if entry.get("role") != "assistant":
            break
        if _CONFIRMATION_ASK_PATTERN.search(entry.get("text", "") or ""):
            return True
    return False


_BLOCKED_LLM_MESSAGE = (
    "Cannot end the call yet — the required confirmation step was skipped. "
    "First ask the user 'Can I end the call now?' (or a similar clear "
    "confirmation question) and WAIT for their reply. Only after the user "
    "explicitly confirms may you call end_call again."
)


END_CALL_TOOL_NAME = "end_call"


END_CALL_TOOL_SCHEMA = FunctionSchema(
    name=END_CALL_TOOL_NAME,
    description=(
        "End the current voice call. This tool is governed by a MANDATORY "
        "two-step confirmation. NEVER call it in one turn.\n"
        "Step 1: When the user hints they want to end (says goodbye, 'I'm "
        "done', 'that's all', asks to hang up) OR when the task feels "
        "complete, do NOT call this tool. Instead, ask 'Can I end the call "
        "now?' (or similar) and wait for the user's reply.\n"
        "Step 2: Only if the user's next message clearly confirms (e.g. "
        "'yes', 'sure', 'go ahead', 'please do', 'goodbye', 'yep'), speak "
        "a one-sentence farewell and THEN call this tool. If the user says "
        "anything else — a new question, 'no', 'wait', changes their mind, "
        "or adds new information — do NOT call this tool and continue the "
        "conversation."
    ),
    properties={
        "reason": {
            "type": "string",
            "description": (
                "Quote the user's exact confirmation, given as a DIRECT reply "
                "to your \"Can I end the call?\" question — not to any other "
                "question. Examples: \"user confirmed with 'yes'\" (after you "
                "asked to end), \"user said 'goodbye' after your end-call "
                "ask\", \"user said 'please go ahead' to end-call ask\". "
                "DO NOT reuse task-level confirmations (e.g. \"user said "
                "'confirm the booking'\", \"user said 'go ahead' about the "
                "order\", \"user said 'that's correct' about the details\") "
                "as reasons — those confirm the TASK, not ending the call. "
                "If you cannot quote a direct call-end confirmation, do NOT "
                "call this tool."
            ),
        },
    },
    required=["reason"],
)


END_CALL_SYSTEM_PROMPT = (
    "\n\n## Ending the call\n"
    "You have a tool called `end_call`. It is governed by a MANDATORY "
    "two-step confirmation. You MUST never end the call in a single turn.\n"
    "\n"
    "**Step 1 — Ask for confirmation.**\n"
    "When ANY of the following happen, do NOT call `end_call`. Instead, ask "
    "the user for permission to end and WAIT for their reply:\n"
    "- The user says a farewell word (\"bye\", \"goodbye\", \"have a good "
    "day\", \"talk to you later\", \"I'll let you go\", \"that's all\", "
    "\"hang up\", \"end the call\").\n"
    "- The user says the task is done or they have no more questions.\n"
    "- The task appears complete (booking taken, question answered, details "
    "collected).\n"
    "\n"
    "Reply with a short closing line plus a confirmation question, for example:\n"
    "- \"Alright, thank you for calling. Can I end the call now?\"\n"
    "- \"Glad I could help! Would you like me to end the call, or is there "
    "anything else?\"\n"
    "- \"Sounds good — shall I go ahead and end the call?\"\n"
    "\n"
    "**Step 2 — End only after explicit confirmation.**\n"
    "Look ONLY at the user's reply to your Step 1 question:\n"
    "- If the reply clearly confirms (\"yes\", \"sure\", \"please\", \"go "
    "ahead\", \"goodbye\", \"okay\", \"yep\", \"that's fine\"): speak a "
    "one-sentence farewell (e.g. \"Alright, have a great day!\") and THEN "
    "call `end_call`. Do not generate any further text after the tool call.\n"
    "- If the reply is anything else — a new question, \"no\", \"wait\", "
    "changing their mind, adding information, uncertainty, silence — do NOT "
    "call `end_call`. Continue the conversation normally.\n"
    "\n"
    "**Hard rules — never break these:**\n"
    "- Never call `end_call` on the same turn a user first hints at "
    "goodbye. Always ask for confirmation first.\n"
    "- Never skip Step 1, even if ending feels obvious.\n"
    "- Never call `end_call` before speaking a brief farewell sentence.\n"
    "- The `reason` argument must quote the user's exact confirmation words. "
    "Vague reasons like \"conversation complete\" are invalid and mean you "
    "should not be calling the tool.\n"
    "- **Ask AT MOST ONCE per conversation.** If you have already asked "
    "\"Can I end the call?\" (or any variant) earlier in this conversation "
    "and the user did not clearly confirm, DO NOT ask again. Continue the "
    "conversation naturally and let the user hang up on their own. Asking "
    "the same closing question repeatedly is worse than not ending at all.\n"
    "- **Task confirmations are NOT call-end confirmations.** Whatever your "
    "domain (booking, ordering, scheduling, support, sales, information "
    "lookup, form filling, etc.), the user will often say things like "
    "\"confirm\", \"go ahead\", \"proceed\", \"that's correct\", \"looks "
    "good\", \"sounds right\", \"yes\", \"okay\" to move the task forward. "
    "These words refer to the TASK, not the CALL. Never treat them as "
    "permission to end the call. Only accept them as call-end confirmation "
    "if they are a DIRECT reply to your \"Can I end the call?\" question "
    "and there is no other pending topic between the two.\n"
    "\n"
    "If you are ever unsure whether the user really wants to end, DO NOT "
    "call `end_call`. Keep the conversation going — but do NOT re-ask the "
    "confirmation question if you already asked it once.\n"
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
    end_reason_holder: Optional[dict] = None,
    call_id_holder: Optional[dict] = None,
    transcript_entries: Optional[list] = None,
) -> Callable:
    """Factory: build a handler that pushes EndFrame to gracefully end the call.

    Mirrors the shape of the built-in handlers in ``custom_tool_service``:
    appends one entry to ``tool_call_entries`` for the per-call log and invokes
    ``params.result_callback`` so the LLM sees a tool result. EndFrame goes onto
    the pipeline worker — pipecat drains downstream queues (TTS) before
    actually terminating, so any farewell already in flight will be heard.

    Two guards run BEFORE the EndFrame is queued:
      1. Single-fire — LLMs occasionally double-call the tool in one turn.
      2. Confirmation — the assistant must have asked "Can I end the call?"
         and the user must have replied. Enforces the two-step flow encoded
         in ``END_CALL_SYSTEM_PROMPT`` at the code level so an LLM that
         ignores the prompt still cannot terminate the call.

    If ``end_reason_holder`` is provided (a dict owned by the runner), the
    first successful invocation stamps ``reason='llm_end_call'`` and the LLM's
    free-text reason as ``detail``. First-wins so the later transport
    ``on_client_disconnected`` cannot overwrite the true cause.
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

        # Confirmation guard — enforce the two-step flow. If the LLM skipped
        # the ask/reply step, refuse and instruct it to try again. Do NOT
        # mark ``state["fired"]`` so a later, valid attempt can still succeed.
        if not _confirmation_valid(transcript_entries):
            logger.warning(
                "end_call blocked — confirmation flow not completed. reason={!r}", reason
            )
            log_call_event(
                EVENT_END_CALL_BLOCKED,
                call_id=call_id_holder.get("id") if call_id_holder else None,
                source="llm_tool",
                turn=current_turn["number"] if current_turn else None,
                attempted_reason=reason,
            )
            entry["result"] = "blocked: missing confirmation"
            entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            if tool_call_entries is not None:
                tool_call_entries.append(entry)
            await params.result_callback(_BLOCKED_LLM_MESSAGE)
            return

        state["fired"] = True
        logger.info("LLM end_call invoked — ending pipeline. reason={!r}", reason)
        log_call_event(
            EVENT_CALL_ENDED,
            call_id=call_id_holder.get("id") if call_id_holder else None,
            reason=REASON_LLM_END_CALL,
            source="llm_tool",
            turn=current_turn["number"] if current_turn else None,
            detail=reason,
        )

        # Stamp end-reason before queueing EndFrame so downstream disconnect
        # handlers (which fire when the transport tears down) see it already
        # set and skip overwriting.
        if end_reason_holder is not None and end_reason_holder.get("reason") is None:
            end_reason_holder["reason"] = REASON_LLM_END_CALL
            end_reason_holder["detail"] = reason

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
