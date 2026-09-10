"""end_call: LLM-driven call termination tool.

The single, canonical path for ending a call. Registered automatically for
every agent. The LLM is instructed (via ``END_CALL_SYSTEM_PROMPT``) to ask
"Can I end the call?" and wait for confirmation before calling this tool — but
that two-step is *guidance for the model*. The handler trusts the LLM's decision
and does NOT re-validate it with a rigid word-check: an earlier regex
confirmation gate kept false-blocking valid ends (e.g. when STT mis-heard "end"
as "send", or on transcript-timing races). The only remaining code guard is
single-fire, since an LLM occasionally double-calls the tool in one turn.

The handler queues an EndFrame onto the pipeline worker, which gracefully tears
down the pipeline (TTS finishes any current speech, then transports disconnect);
the runner's provider-agnostic terminator drops the actual phone leg.
"""

import time as _time
from typing import Callable, List, Optional

from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import EndFrame
from pipecat.services.llm_service import FunctionCallParams

from core.services.pipeline.call_end_events import (
    EVENT_CALL_ENDED,
    REASON_LLM_END_CALL,
    log_call_event,
)
from core.services.pipeline.tool_call_timing import (
    ToolCallTimer,
    finalize_and_record,
)

END_CALL_TOOL_NAME = "end_call"


END_CALL_TOOL_SCHEMA = FunctionSchema(
    name=END_CALL_TOOL_NAME,
    description=(
        "End the current voice call. This tool is governed by a MANDATORY "
        "two-step confirmation. NEVER call it in one turn UNLESS the user "
        "directly asks to end (see the Step 1 exception below).\n"
        "Step 1: When the user only HINTS they want to end (says goodbye, "
        "'I'm done', 'that's all') OR when the task feels complete, do NOT "
        "call this tool. Instead, ask 'Can I end the call now?' (or similar) "
        "and wait for the user's reply. EXCEPTION: if the user DIRECTLY asks "
        "to end ('end the call', 'hang up', 'can you end the call'), do not "
        "ask again — say a one-sentence farewell and call this tool right "
        "away.\n"
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
                "Optional short note on why the call is ending — e.g. "
                "\"user said 'hang up'\" or \"user confirmed after the "
                "end-call ask\". Leave it empty if you're unsure; it is only "
                "for logging and never gates the call."
            ),
        },
    },
    required=[],
)


END_CALL_SYSTEM_PROMPT = (
    "\n\n## Ending the call\n"
    "You have a tool called `end_call`. It is governed by a MANDATORY "
    "two-step confirmation. You MUST never end the call in a single turn.\n"
    "\n"
    "**Task completion — announce, then ask for follow-ups (do this FIRST).**\n"
    "Whenever you finish what the user asked for — a booking made, an order "
    "placed, an appointment scheduled, a question answered, information "
    "provided, a form filled, a request logged, or any other requested "
    "action — do BOTH of the following before anything else:\n"
    "1. Clearly announce the completion in one short natural sentence "
    "appropriate to your domain (e.g. \"Your booking is confirmed\", \"The "
    "order has been placed\", \"I've scheduled the appointment for you\", "
    "\"Here is the information you asked for\").\n"
    "2. Ask a natural follow-up question inviting more, e.g. \"Is there "
    "anything else I can help you with?\" — then WAIT for the user's reply.\n"
    "Do NOT skip either half. Do NOT jump straight from task completion to "
    "\"Can I end the call?\" — the user must first know their task is done "
    "AND be given the chance to ask for more.\n"
    "Only if the user's reply indicates they have nothing more (\"no that's "
    "all\", \"nothing else\", \"I'm good\", \"that's it\") should you move "
    "on to Step 1 below.\n"
    "\n"
    "**Express end path — when the user directly asks to end (this takes "
    "PRECEDENCE over Step 1).**\n"
    "If the user's own message clearly and directly asks you to end the "
    "call — whether phrased as a command (\"hang up\", \"end the call\", "
    "\"end it now\", \"disconnect\", \"cut the call\", \"just hang up\") or "
    "as a direct request or question (\"can you end the call\", \"please end "
    "the call\", \"please hang up\", \"could you hang up\") — in a short "
    "direct message, SKIP the two-step confirmation below. A direct end "
    "request is NEVER a reason to ask \"Can I end the call?\": the user has "
    "already told you to end, so asking would be tone-deaf and just repeat "
    "them. Instead:\n"
    "1. Say a brief thank-you farewell in ONE sentence (e.g. \"Thank you "
    "for calling — have a great day!\", \"Thanks, take care!\", \"Alright, "
    "thanks for reaching out — goodbye!\").\n"
    "2. Immediately call `end_call`.\n"
    "Use the `reason` argument to quote the user's exact end request "
    "(e.g. \"user said 'hang up'\", \"user said 'end the call'\"). This "
    "express path applies only when the user's own message contains an "
    "explicit direct end request — never for indirect signals like "
    "\"thanks\" or \"that's all\".\n"
    "\n"
    "**Step 1 — Ask for confirmation.**\n"
    "When ANY of the following happen, do NOT call `end_call`. Instead, ask "
    "the user for permission to end and WAIT for their reply:\n"
    "- The user says a soft farewell or hint (\"bye\", \"goodbye\", \"have a "
    "good day\", \"talk to you later\", \"I'll let you go\", \"that's all\", "
    "\"I'm done\"). NOTE: a DIRECT end command like \"end the call\" or "
    "\"hang up\" is NOT a Step 1 hint — it uses the Express end path above "
    "(end right away, do not ask).\n"
    "- The user has confirmed (in the completion step above) that they need "
    "nothing else.\n"
    "\n"
    "Reply with a short closing line plus a confirmation question, for example:\n"
    "- \"Alright, thank you for calling. Can I end the call now?\"\n"
    "- \"Glad I could help! Would you like me to end the call, or is there "
    "anything else?\"\n"
    "- \"Sounds good — shall I go ahead and end the call?\"\n"
    "\n"
    "**Step 2 — End only after explicit confirmation.**\n"
    "Look ONLY at the user's reply to your Step 1 question:\n"
    "- If the reply is ANY affirmative (\"yes\", \"yeah\", \"yep\", \"sure\", "
    "\"okay\", \"ok\", \"please\", \"please do\", \"go ahead\", \"you can\", "
    "\"that's fine\", \"goodbye\", a nod word): this IS a valid call-end "
    "confirmation because it directly answers your \"Can I end the call?\" "
    "question. You MUST speak a one-sentence farewell (e.g. \"Alright, have a "
    "great day!\") and THEN call `end_call`. Do NOT re-classify a bare "
    "\"yes\"/\"sure\"/\"okay\" here as a mere task confirmation, and do NOT "
    "ask again — just end. Do not generate any further text after the tool "
    "call.\n"
    "- If the reply is anything else — a new question, \"no\", \"wait\", "
    "changing their mind, adding information, uncertainty, silence — do NOT "
    "call `end_call`. Continue the conversation normally.\n"
    "\n"
    "**Hard rules — never break these:**\n"
    "- Never call `end_call` on the same turn a user first hints at "
    "goodbye. Always ask for confirmation first.\n"
    "- Never skip Step 1, even if ending feels obvious.\n"
    "- Never call `end_call` before speaking a brief farewell sentence.\n"
    "- Once the user has agreed to end (or directly asked to), calling "
    "`end_call` is MANDATORY. A farewell sentence WITHOUT the tool call does "
    "NOT end the call and leaves the caller stuck on a dead line — always emit "
    "the `end_call` tool call in that same turn. A brief `reason` is optional; "
    "never withhold the tool call just because you can't phrase one.\n"
    "- **Ask AT MOST ONCE per conversation.** If you have already asked "
    "\"Can I end the call?\" (or any variant) earlier in this conversation "
    "and the user did not clearly confirm, DO NOT ask again. Continue the "
    "conversation naturally and let the user hang up on their own. Asking "
    "the same closing question repeatedly is worse than not ending at all.\n"
    "- **Ask \"Is there anything else?\" at most TWICE per conversation.** "
    "The first time is fine after your first task completes. The second "
    "time is fine if the user brought up another task and you finished "
    "that too. After that, do NOT keep asking. Continue naturally and let "
    "the user tell you if they need more. Asking \"anything else?\" over "
    "and over turns the call into an awkward loop.\n"
    "- **Distinguish task confirmations from call-end confirmations by WHAT "
    "you last asked.** The user will often say \"confirm\", \"go ahead\", "
    "\"proceed\", \"that's correct\", \"yes\", \"okay\" to move a TASK forward "
    "(booking, ordering, scheduling, etc.) — when your last question was about "
    "the task, those move the task forward and are NOT permission to end. "
    "BUT when your last question was \"Can I end the call?\" (Step 1), that "
    "SAME \"yes\"/\"yeah\"/\"sure\"/\"okay\" IS the call-end confirmation — "
    "end the call per Step 2. The words are identical; the meaning comes from "
    "the question you just asked. If you just asked to end the call, treat a "
    "short affirmative as YES, end it.\n"
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
    tool_request_ts: Optional[dict] = None,
    current_turn: Optional[dict] = None,
    end_reason_holder: Optional[dict] = None,
    call_id_holder: Optional[dict] = None,
) -> Callable:
    """Factory: build a handler that pushes EndFrame to gracefully end the call.

    Mirrors the shape of the built-in handlers in ``custom_tool_service``:
    appends one entry to ``tool_call_entries`` for the per-call log and invokes
    ``params.result_callback`` so the LLM sees a tool result. EndFrame goes onto
    the pipeline worker — pipecat drains downstream queues (TTS) before
    actually terminating, so any farewell already in flight will be heard.

    The two-step confirmation is left to the LLM (per ``END_CALL_SYSTEM_PROMPT``);
    the only code guard is single-fire, since an LLM occasionally double-calls the
    tool in one turn. (A prior regex confirmation gate was removed — it kept
    false-blocking valid ends, e.g. when STT mis-heard "end" as "send".)

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
        timer = ToolCallTimer.start(params, tool_request_ts)

        entry = {
            "tool": END_CALL_TOOL_NAME,
            "tool_type": "built_in",
            "arguments": {"reason": reason},
            "timestamp": int(_time.time()),
            "turn": current_turn["number"] if current_turn else None,
            **timer.initial_fields(),
        }

        if state["fired"]:
            logger.bind(
                tool_name=END_CALL_TOOL_NAME,
                tool_type="built_in",
                call_id=call_id_holder.get("id") if call_id_holder else None,
                reason=reason,
            ).info(
                "[end-call-tool] end_call invoked again — ignoring (already ending) reason={!r}",
                reason,
            )
            entry["result"] = "ignored: already ending"
            entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
            finalize_and_record(entry, timer, tool_call_entries)
            await params.result_callback("Call is already ending.")
            return

        # Trust the LLM's decision to end (the two-step is guidance in
        # END_CALL_SYSTEM_PROMPT). No code-level confirmation re-check — it kept
        # false-blocking valid ends on STT mis-hears / phrasing / timing.
        state["fired"] = True
        logger.bind(
            tool_name=END_CALL_TOOL_NAME,
            tool_type="built_in",
            call_id=call_id_holder.get("id") if call_id_holder else None,
            reason=reason,
            turn=current_turn["number"] if current_turn else None,
        ).info("[end-call-tool] LLM end_call invoked — ending pipeline reason={!r}", reason)
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

        # Resolve the LLM function call BEFORE queueing the end frame: pipecat's
        # graceful EndFrame drains the queue on the way down, and a callback left
        # until after can be dropped — leaving the tool call unresolved (per the
        # Pipecat pipeline-termination guide).
        await params.result_callback("Call ending now.")

        try:
            await params.pipeline_worker.queue_frame(EndFrame())
            entry["result"] = "ending"
        except Exception as e:
            logger.bind(
                tool_name=END_CALL_TOOL_NAME,
                tool_type="built_in",
                call_id=call_id_holder.get("id") if call_id_holder else None,
                reason=reason,
            ).exception("[end-call-tool] failed to queue EndFrame from end_call handler")
            entry["result"] = f"error: {e}"

        entry["duration_ms"] = round((_time.monotonic() - _t_start) * 1000)
        finalize_and_record(entry, timer, tool_call_entries)

    return handle_end_call
