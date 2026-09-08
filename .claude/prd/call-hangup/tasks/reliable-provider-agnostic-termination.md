# reliable-provider-agnostic-termination

> feature: call-hangup · task: reliable-provider-agnostic-termination
> clickup: https://app.clickup.com/t/90161705086/86d49x4gg (MCP unauthorized — populated from session conversation, pending user approval)

## Requirements

WHAT: Make call termination reliable and provider-independent. Once an end is decided by ANY path
(the `end_call` LLM tool, the workflow `endCall` node, caller-disconnect, or a pipeline error), the phone
line must actually disconnect on EVERY provider — fixing the hang reproduced on **Telnyx**.

WHY: Today the real hangup is delegated entirely to each provider's Pipecat serializer `auto_hang_up` on
`EndFrame`, through a chain that fails silently: (1) the confirmation guard can silently block a valid end
and the "ask once" rule then wedges the call open; a transcript-timing race can also mis-block; (2) even
when accepted, the `EndFrame` may never reach `serializer.serialize()` (early-return when the WS is already
closing / subprocess-bridge teardown), so no hangup fires; (3) coverage is per-provider (Exotel has none).
We already own provider REST hangups (`CallEngine.end_call`) that this path never uses.

Scope / non-goals:
- KEEP the `end_call` tool + two-step confirmation as the decision mechanism (only fix the guard's
  silent-block/wedge + race).
- Backend/voice-runtime only. No frontend, no DB, no migration, no API-contract change.
- Do NOT special-case providers; Exotel/Plivo hangup *implementations* are a possible follow-up — this task
  builds the shared door and wires all deciders through it.
- HARD: no regression to any existing end/teardown path, call-log completion, recording, or end-reason
  attribution.

## Implementation Details

Affected surfaces (final design to be produced in plan mode):
- **Shared terminator** — one provider-agnostic entry point that resolves provider + correct hangup id
  (`call_control_id` for Telnyx, `call_sid` for Twilio, …) and dispatches to the existing
  `CallEngine.end_call` / provider hangup primitive; idempotent; best-effort (never raises); treats
  "already ended" as success. Single source of truth — no hangup logic duplicated at call sites.
- **Runner wiring** (`runner/pipecat.py`) — invoke the terminator from the end/teardown path in ADDITION to
  the existing `EndFrame` queue + `task.cancel()`, coordinated with `end_reason_holder` (first-wins) so
  attribution and single-fire are preserved.
- **`end_call` tool** (`tools/end_call_tool.py`) — keep queuing `EndFrame` for graceful audio drain; ensure
  the decided end reaches the terminator; fix the guard so a valid confirmation isn't silently dropped and a
  block can't permanently wedge the call; close the transcript-timing race.
- **Other deciders** — workflow `endCall` node and caller-disconnect/error paths funnel through the same
  terminator.
- **Verify hangup id + endpoint per provider** — reconcile the Telnyx serializer hangup
  (`/v2/calls/{call_control_id}/actions/hangup`) vs `TelnyxCallEngine.end_call` (`Status=completed`) so the
  authoritative path uses the correct id/endpoint.
- Logging via `call_end_events`; org-scoped credential helpers; full-traceback excepts; no secrets logged.

Edge cases: multiple end paths firing for one call (idempotency); TTS still draining (bounded wait before
hard hangup); provider already ended; missing/invalid hangup id; test transport (no real provider).

## Acceptance Criteria

- [ ] Telnyx: decided end → line disconnects reliably.
- [ ] Guard: no silent drop of a genuine confirmation; no permanent wedge; race closed.
- [ ] All deciders (tool, workflow node, caller-disconnect, error) go through ONE terminator; no call site
      branches on provider.
- [ ] Terminator is idempotent, best-effort (never raises), treats "already ended" as success; farewell
      audio still plays before hangup.
- [ ] No regression: existing teardown, call-log completion, recording upload, end-reason attribution
      unchanged; already-hanging-up providers behave identically.
- [ ] Tests: terminator (dispatch/idempotency/error-swallow) + guard (race/no-wedge) + Telnyx-style
      regression. Ruff passes.
