# Call Hangup — Reliable, Provider-Agnostic Call Termination — Requirements

When a voice call should end — the agent asks "Can I end the call now?", the user confirms, and the LLM
calls the `end_call` tool — the phone line does **not** reliably disconnect. It was reproduced on **Telnyx**
(whose serializer *does* implement REST hangup), which proves the defect is in our **shared termination
flow**, not in any single provider's hangup. Today the actual hangup is delegated entirely to each
provider's Pipecat serializer `auto_hang_up` on `EndFrame`, reached through a long chain that fails
silently at several points. This feature makes call termination **authoritative at our own layer and
provider-independent**, so that once an end is decided (by any path), the line always drops — without
changing how the agent *decides* to end (the `end_call` tool + two-step confirmation stay as-is).

## 1. Overview

- **Route(s) / entry points:** No HTTP route. Runtime voice pipeline: `end_call` LLM tool
  (`core/services/pipeline/tools/end_call_tool.py`) → pipeline runner
  (`core/services/pipeline/runner/pipecat.py`) → per-provider hangup (`core/services/call_engines/*`,
  `core/services/transport/*`). Other end triggers: workflow `endCall` node
  (`core/services/pipeline/workflow/engine.py`), caller disconnect, pipeline error.
- **Goal:** Once a call end is decided by ANY path, the phone line reliably disconnects on EVERY provider,
  via one shared provider-agnostic termination path — fixing the Telnyx-reproduced hang.
- **Scope:** Backend / voice-runtime only. **No** frontend, **no** DB schema/migration, **no** change to
  the `end_call` tool schema, the two-step confirmation UX, or agent configuration. Explicitly NOT changing
  how the agent *decides* to end a call.
- **Shared / affected surfaces:** The `end_call` tool handler, the pipeline runner's end/teardown path, the
  telephony transport/serializer layer, and the `CallEngine.end_call` implementations — all reused across
  inbound/outbound and every transport.

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `core/services/pipeline/tools/end_call_tool.py` | LLM `end_call` tool: confirmation guard + queues `EndFrame`. Guard silent-block + "ask once" wedge fixed here; routed through the shared terminator. |
| `core/services/pipeline/runner/pipecat.py` | Pipeline runner: owns `end_reason_holder`, session/disconnect wiring, `task.cancel()`. Central place to invoke the shared terminator. |
| `core/services/call_engines/*.py` (`base.py`, `telnyx_engine.py`, `twilio_engine.py`, `sip_engine.py`, `websocket_engine.py`) | Existing per-provider REST hangup (`end_call(call_id)`); the primitives the shared terminator dispatches to. `websocket_engine.end_call` is a no-op today. |
| `core/services/transport/*.py` (`twilio.py`, `telnyx.py`, `exotel.py`, `plivo.py`, `registry.py`, `base.py`) | Transport/serializer assembly per provider; provider identity + hangup-id source (`call_control_id`, `call_sid`, …). |
| `core/services/pipeline/workflow/engine.py` | Workflow `endCall` node — another end decider that must funnel into the same terminator. |
| `core/services/pipeline/call_end_events.py` | Structured end-reason/event vocabulary — reused for logging the new path. |
| `core/services/subprocess_bot_manager.py` | Subprocess bridge teardown timing (why `EndFrame` can be dropped before the serializer hangs up). |

## 7. Behavior & Functionality

- **Deciding to end (UNCHANGED):** The `end_call` LLM tool + mandatory two-step confirmation remain the
  acceptance mechanism for conversational agents. Workflow `endCall` node, caller-disconnect, and pipeline
  error/timeout remain the other deciders. No decision-side behavior changes except the guard fix below.
- **Confirmation guard fix:** A valid, user-confirmed end must not be silently discarded. The guard must not
  (a) block a genuine confirmation because of a transcript-timing race (context pushed to the LLM before the
  user turn is appended to `transcript_entries`), nor (b) leave the call permanently wedged when it blocks
  (today it returns "ask again" while the system prompt says "ask at most once"). Blocked attempts must be
  observable (already emit `end_call_blocked`).
- **Authoritative, provider-agnostic termination (primary fix):** Introduce ONE shared terminator that any
  end path calls to actually drop the line. It is provider-**agnostic** to callers; behind it, it resolves
  the call's provider + correct hangup id and dispatches to that provider's hangup primitive. It runs in
  ADDITION to queuing `EndFrame` (so the farewell audio still drains), and does not depend on `EndFrame`
  surviving teardown or on the serializer running.
- **Idempotency:** Termination must be safe to call more than once and from more than one path (LLM tool +
  disconnect handler + error path) without error or double-side-effects. Provider "call already ended"
  responses (e.g. Telnyx 90018) are treated as success.
- **Graceful audio drain preserved:** The one-sentence farewell spoken before `end_call` must still be heard;
  the hard hangup happens after TTS drains (or after a bounded timeout so a stuck TTS can't block teardown).
- **Provider coverage:** The shared path works for every configured provider. Providers with an existing
  hangup (Telnyx, Twilio, SIP) work immediately. Gaps (Exotel, Plivo, the no-op WebSocket engine) are noted;
  filling their hangup primitives is by extension behind the same door (Exotel/Plivo hangup implementation
  may be scheduled as a follow-up task, but the shared path must not special-case them).
- **APIs & data model:** None. No HTTP contract, no DB schema, no migration. Uses existing provider REST
  APIs already used elsewhere. Org-scoped credential lookup uses the existing `get_*_credentials(org_id=)`
  helpers.
- **Error handling:** The terminator never raises out to its callers (best-effort, full-traceback
  `logger.exception` on failure) — a hangup API failure must not crash pipeline teardown. Every `except`
  logs a full traceback per the repo logging rules; `CancelledError` is never swallowed.

## 8. Non-Functional Requirements

- **Standards compliance:** Follows the backend service-layer/reuse doctrine — the shared terminator is ONE
  implementation reused by every end path (no duplicated hangup logic at call sites); logic lives in a
  service, not inline. Ruff clean.
- **No regression to existing functionality (HARD requirement):** All current end paths keep working —
  normal LLM end, caller-hangup teardown, error teardown, workflow `endCall`, recording/call-log completion,
  and end-reason attribution (first-wins `end_reason_holder`). The change is additive/defensive; existing
  behavior on providers that already hang up must be unchanged (the extra call is a harmless no-op there).
- **Observability:** Reuse `call_end_events` vocabulary; log the terminator invocation, provider, resolved
  hangup id, and outcome, correlated by `call_id`/`trace_id`. No secrets/credentials in logs.
- **Security:** Provider credentials stay AES-encrypted, fetched via existing org-scoped helpers; never
  logged.

## 9. Acceptance Criteria

- [ ] R (Telnyx repro): agent asks to end → user confirms → line disconnects reliably on Telnyx.
- [ ] R (guard): a genuine user confirmation is never silently dropped; a blocked attempt cannot permanently
      wedge the call open; the transcript-timing race is closed.
- [ ] R (provider-agnostic): all end paths (LLM tool, workflow `endCall`, caller-disconnect, error) funnel
      through ONE shared terminator; no call site branches on provider.
- [ ] R (idempotent + graceful): terminate is safe to call multiple times / from multiple paths; farewell
      audio still plays before hangup; "already ended" is treated as success.
- [ ] R (no regression): existing end/teardown, call-log completion, recording upload, and end-reason
      attribution all still work; providers that already hang up behave identically.
- [ ] Tests added for the terminator (dispatch, idempotency, error-swallowing) and the guard fix
      (race + no-wedge); regression test for the Telnyx-style "decided but line stays up" path. Ruff passes.

## 10. Out of Scope

- Changing how the agent *decides* to end (the `end_call` tool schema, the two-step confirmation UX, the
  system-prompt wording) — unchanged except the guard's silent-block/wedge fix.
- Implementing Exotel/Plivo hangup primitives and de-no-op-ing the WebSocket engine — the shared path must
  accommodate them, but building each provider's hangup may be a separate follow-up task.
- Any frontend, DB schema/migration, or API-contract change.
- Outbound origination / scheduling / concurrency behavior.
