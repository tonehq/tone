# Schedule a Call — PRD & Implementation Spec

> Authored 2026-08-28. Update via `/generate_feature_prd_and_implementation` whenever the feature changes.
>
> **Source:** ClickUp [86d44t3xg — "Schedule a Call"](https://app.clickup.com/t/86d44t3xg) (status: `to do`) · branch `feature/schedule-a-call`
>
> **Authoring mode:** non-interactive. The source ticket is a *product question*, not a spec. Every
> requirement that the ticket does not answer is written as **`TBD - needs product input`** rather than
> invented. Sections that describe current behaviour are grounded in the code and cite `file:line`.

---

## 1. Overview

Today, one user-facing action ("Schedule Call" → modal "New outbound call") covers two behaviours that
are conceptually different:

1. **Call now** — dial the destination immediately.
2. **Schedule for later** — queue the call to dial at a future instant.

The distinction is currently a checkbox inside the modal (`Schedule for later`,
`frontend/src/components/outbound-calls/NewOutboundCallModal.tsx:597`) and an optional field on the API
(`scheduled_at`, `core/api/v1/outbound_calls.py:30`). The ticket raises that labelling the *entry point*
"Schedule a Call" is wrong for the immediate case, and proposes splitting the concept:

- **Outbound Call** → immediate dialing
- **Schedule a Call** → calls queued for a later time

**Target user:** any org member (`require_org_member`) who places outbound calls from the agent editor's
**Schedule** tab.

**Problem statement:** the naming does not match the behaviour, in three concrete places in the code:

| Where | Current copy / behaviour | Why it misleads |
|---|---|---|
| `ScheduledCallsPage.tsx:268`, `:307` | Primary button reads **"Schedule Call"** | It is the only way to place an *immediate* call too. |
| `NewOutboundCallModal.tsx:416` | Modal title reads **"New outbound call"** | Opened from a button labelled "Schedule Call" — the two names disagree. |
| `ScheduledCallsPage.tsx:257–260` | List titled **"Scheduled Calls"**, described as "queued to dial at a future time" | Multi-number *immediate* batches land in this same list (see below). |

**The behavioural inconsistency behind the naming problem** (this is not just copy): whether a request
dials now or is queued is decided by *two* inputs, not one.

- A **single** number with no `scheduled_at` dials inline and returns `mode: "immediate"`
  (`core/services/outbound_call_service.py:463`, response at `:574`). It surfaces in **Call History**.
- **Multiple** numbers with no `scheduled_at` are routed through `_schedule_via_contacts` and persisted as
  `scheduled_calls` rows with `mode: "bulk"` (`outbound_call_service.py:466–473`, `:544`). They dial ASAP —
  `_resolve_contact_when` falls back to `now` (`:766`) — but they **appear in the "Scheduled Calls" list**.
- A request with `scheduled_at` returns `mode: "scheduled"` (`:544`).
- `provider="websocket"` with no `scheduled_at` fans out immediately as `mode: "parallel_websocket"`
  (`:459–460`, `:698`).

So "Scheduled Calls" today means "rows in the `scheduled_calls` table", which includes immediate bulk
dials. That is the root of the confusion the ticket describes.

---

## 2. User stories & use cases

Derived from the ticket. Acceptance detail for each is deferred to product.

- **US-1** — As an org member, I want a clearly labelled **Outbound Call** action, so that I understand the
  call will be placed immediately when I confirm.
- **US-2** — As an org member, I want a separate **Schedule a Call** action, so that I can queue a call for
  a later time without wondering whether it will dial right now.
- **US-3** — As an org member, I want the **Scheduled Calls** list to contain only calls that are actually
  waiting for a future time, so that the list matches its name.
  - ⚠ Conflicts with current behaviour: immediate `bulk` batches are written to `scheduled_calls`
    (`outbound_call_service.py:469–473`). Resolving this needs a product decision — see FR-4.
- **US-4** — As an org member placing a bulk/CSV batch, I want to know before submitting whether rows will
  dial now or later. *(Partially implemented already: `immediateNotice`, `NewOutboundCallModal.tsx:388–394`;
  submit-button label switches between "Call … now" / "Schedule call", `:400–410`.)*

**Use cases not covered by the ticket:** `TBD - needs product input` — specifically whether the split
applies to the CSV/Excel upload path, the per-row `schedule_column` path, and
`POST /api/v1/contact/schedule-calls` (`core/api/v1/contacts.py:186`), which also dials ASAP when
`scheduled_at` is omitted.

---

## 3. Functional requirements

The ticket asks a question and does not state requirements. The items below are the *decisions that must be
made*, each with the code that would change. **None are approved yet.**

- **FR-1 — Two distinct entry points in the UI.** Replace the single "Schedule Call" button
  (`ScheduledCallsPage.tsx:263–269` and the empty-state button at `:307–309`) with two actions:
  "Outbound Call" (immediate) and "Schedule a Call" (future).
  - Exact labels, button order, primary/secondary emphasis, and icons: `TBD - needs product input`.
  - Whether they open two modals or one modal in two modes: `TBD - needs product input`.
    (Recommended: **one** `NewOutboundCallModal` with a `mode: 'immediate' | 'scheduled'` prop — it already
    holds agent/from-number/provider/concurrency/upload/directory logic that both flows need; forking it
    would duplicate ~650 lines and violate the single-source-of-truth rule in `CLAUDE.md`.)
- **FR-2 — Mode-specific form.** In `immediate` mode the "Schedule for later" checkbox
  (`NewOutboundCallModal.tsx:597`) and the `DateTimePicker` block (`:598–635`) are hidden; in `scheduled`
  mode the scheduled time is **required** rather than opt-in.
- **FR-3 — Copy alignment.** Modal title (`:416`), submit label (`:400–410`), and success toasts
  (`:347–353`) must state which behaviour was chosen. Final strings: `TBD - needs product input`.
- **FR-4 — Where immediate bulk calls are listed.** Decide one of:
  - **(a)** Keep writing immediate bulk batches to `scheduled_calls` and rename the list to something
    behaviour-accurate (e.g. "Outbound queue"), or
  - **(b)** Keep the list name and filter immediate rows out of the default view, or
  - **(c)** Change the backend so immediate bulk no longer persists `scheduled_calls` rows.
  - **Decision: `TBD - needs product input`.** Note (c) is the largest change — it would remove the
    per-batch concurrency mechanism for immediate batches, which is enforced only at dispatch over
    `scheduled_calls` rows (`outbound_call_service.py:866+`, `resolve_batch_concurrency` in
    `core/services/outbound_capacity.py`). **Recommended: (a) or (b).**
- **FR-5 — API surface.** Decide whether the split is UI-only or reaches the API:
  - **(a)** UI-only — `POST /api/v1/outbound-call/create` keeps deciding from `scheduled_at`
    (`core/api/v1/outbound_calls.py:81`). No backend change, no migration, no API-consumer breakage.
  - **(b)** Add explicit sibling routes (e.g. `POST /outbound-call/call-now`, `POST /outbound-call/schedule`)
    as thin wrappers over `OutboundCallService.create_outbound_call`.
  - **Decision: `TBD - needs product input`. Recommended: (a)** — the ticket describes a naming/IA problem,
    and `mode` is already returned in every response (`types/outboundCall.ts:23`), so the client can label
    outcomes correctly without new endpoints.
- **FR-6 — Navigation / IA.** There is no global `/scheduled-calls` route; the list is the agent editor's
  edit-only, outbound-gated **Schedule** tab (`frontend/src/components/agents/agent-form/sectionNav.ts:54`,
  `:65`, `:72` → `steps/ScheduleStep.tsx`). Whether the tab is renamed or split into two tabs:
  `TBD - needs product input`.

### Edge cases & failure modes

Existing behaviour that any redesign must preserve — each already has code:

- **Past / near-now time.** `scheduled_at` in the past is rejected with 400, with a 60s grace window
  (`outbound_call_service.py:447–453`, mirrored client-side at `NewOutboundCallModal.tsx:602–608`).
- **Empty destination list.** 400 "Provide at least one destination number." (`:423–424`); all-invalid
  numbers → 400 (`:444–445`).
- **Partial validity.** Per-number E.164 failures are collected into `invalid` instead of failing the batch
  (`:429–442`); the modal renders them (`NewOutboundCallModal.tsx:569–586`).
- **Duplicates.** De-duplicated both client-side (`parseNumbers`, `:81–96`) and server-side (`seen` set, `:439`).
- **Org isolation.** Every route uses `require_org_member`; the service is constructed with the caller's
  `org_id` (`core/api/v1/outbound_calls.py:71–74`) and all queries are org-scoped
  (e.g. contact load at `outbound_call_service.py:809–813`).
- **Permission boundary.** The `websocket` trigger is restricted — `assert_ws_trigger_allowed`
  (`:1066`) is called on both create routes (`outbound_calls.py:91`, `:138`), and the UI only shows the
  "Trigger via" selector when `ws_trigger_allowed` is true (`NewOutboundCallModal.tsx:456`).
- **Concurrency.** Per-batch limit is stamped on `scheduled_calls.batch_id` / `.max_concurrency`
  (`core/models/scheduled_call.py:41–45`) and enforced at dispatch. **If FR-4(c) is chosen, immediate bulk
  loses this — call out explicitly before implementing.**
- **Cancel race.** Only `scheduled` rows are cancelable; a row already `processing` is rejected
  (`CANCELABLE`, `ScheduledCallsPage.tsx:27`; selection is pruned on poll at `:91–98`).
- **Per-row CSV schedule times.** `schedule_column` cells that are unparseable or in the past are reported
  as invalid rather than dialed now (`outbound_calls.py:165–187`,
  `ContactSchemaService.apply_scheduled_at_from_column`). Empty cells fall back to the request-level time.
- **Telephony failure.** Immediate dial errors surface as 502 (`outbound_call_service.py:565–567`);
  enqueue failures are isolated per row and mark that row `failed` (`:734–738`).
- Pagination limits, rate limits/quotas, and any new empty states for a split view: `TBD - needs product input`.

---

## 4. Non-functional requirements

- **Backward compatibility (blocker-level).** `POST /api/v1/outbound-call/create` and
  `POST /api/v1/contact/schedule-calls` are public API surface. Under FR-5(a) nothing breaks. Under FR-5(b),
  the existing route must remain and keep its current semantics.
- **Multi-tenancy.** Unchanged — `require_org_member` on every route; org-scoped queries throughout.
  No new tenancy seam is introduced by a naming change.
- **Observability.** Existing `[outbound]`-tagged loguru lines (`outbound_call_service.py:552`, `:569`,
  `:853`) already distinguish immediate from scheduled. No new logging required for a UI-only change.
- **Performance.** No new budget. The modal already gates its schema/directory list queries on
  `open && uploadMode` (`NewOutboundCallModal.tsx:143–147`); a mode split must not un-gate them.
- **Security/compliance:** unchanged. **Accessibility:** two adjacent primary actions need distinct
  accessible names — covered by FR-3 copy.

---

## 5. Test cases (requirements-as-tests)

Backend tests live in `test-cases/core/test_outbound_calls.py` and
`test-cases/test_outbound_status_machine.py`; frontend e2e specs live in `frontend/e2e/`.

Regression tests locking today's behaviour (must keep passing whichever option is chosen):

```
TEST: single immediate number dials inline
  GIVEN an outbound agent and one valid E.164 number
  WHEN  POST /api/v1/outbound-call/create with no scheduled_at
  THEN  response mode == "immediate" and no scheduled_calls row is created

TEST: future time queues instead of dialing
  GIVEN an outbound agent and a scheduled_at 1 hour ahead
  WHEN  POST /api/v1/outbound-call/create
  THEN  response mode == "scheduled" and a scheduled_calls row exists with status "scheduled"

TEST: past time is rejected
  GIVEN a scheduled_at 10 minutes in the past
  WHEN  POST /api/v1/outbound-call/create
  THEN  400 "scheduled_at must be in the future."

TEST: near-now time is accepted (60s grace)
  GIVEN a scheduled_at 30 seconds in the past
  WHEN  POST /api/v1/outbound-call/create
  THEN  the request succeeds and the call is queued to dial ASAP

TEST: cross-org scheduled call is not visible
  GIVEN a scheduled call owned by org B
  WHEN  a member of org A calls GET /api/v1/outbound-call/scheduled/{id}
  THEN  404
```

New tests required by this feature:

```
TEST: multi-number immediate batch is labelled correctly
  GIVEN two valid numbers and no scheduled_at
  WHEN  POST /api/v1/outbound-call/create
  THEN  response mode == "bulk"
  AND   the UI reports it as an immediate call, not a scheduled one
  # Expected list placement of these rows: TBD - needs product input (see FR-4)

TEST: Schedule a Call requires a time
  GIVEN the "Schedule a Call" entry point is open
  WHEN  the user submits without picking a date & time
  THEN  the form blocks submission with a validation error
  # Exact message: TBD - needs product input

TEST: Outbound Call hides scheduling controls
  GIVEN the "Outbound Call" entry point is open
  WHEN  the form renders
  THEN  the "Schedule for later" checkbox and the date/time picker are not present
```

Acceptance criteria beyond the above: `TBD - needs product input`.

---

## 6. Data model / DB schema

**No schema change is required for the UI-only option (FR-5a), which is the recommended path.**

Existing table — `scheduled_calls` (`core/models/scheduled_call.py`, extends `OrgScopedModel`):

| Column | Type | Null | Notes |
|---|---|---|---|
| `agent_id` | UUID FK `agents.id` (RESTRICT) | no | |
| `channel_id` | UUID FK `channels.id` (SET NULL) | yes | |
| `contact_id` | UUID FK `contacts.id` (SET NULL) | yes | indexed |
| `from_number` / `to_number` | `String(20)` | no | E.164 |
| `scheduled_at` | `DateTime(timezone=True)` | no | indexed |
| `status` | `String(20)` | no | `scheduled\|processing\|dispatched\|completed\|busy\|no_answer\|failed\|canceled` (`:32–33`) |
| `provider` | `String(20)` | no | default `twilio` |
| `provider_call_sid` | `String(120)` | yes | |
| `call_id` | UUID FK `calls.id` (SET NULL) | yes | set once the call connects |
| `queue_job_id` | `Integer` | yes | Procrastinate job |
| `error` | `String(500)` | yes | |
| `created_by_user_id` | UUID | yes | |
| `batch_id` / `max_concurrency` | UUID / Integer | yes | per-batch concurrency; NULL = unlimited |
| `metadata_` (`metadata`) | JSONB | yes | |

Index: `ix_scheduled_calls_batch_status` on `(batch_id, status)` for the dispatch-time in-flight count
(`:20–22`). Org scoping + soft-delete columns come from `OrgScopedModel` — the convention holds.

**Only if FR-4(c) or an explicit-kind model is chosen** would a change be needed — e.g. a
`kind` / `is_immediate` discriminator column on `scheduled_calls` plus an Alembic migration and a backfill
(`UPDATE ... SET kind = 'immediate' WHERE …`). Whether to add it: `TBD - needs product input`.
Migration head to branch from: the latest of `d4f1b7c8e35a`, `6ab783e9080f`, `b7d4e9c2f1a8` — confirm with
`alembic heads` at implementation time.

---

## 7. API design

All routes are mounted at `/api/v1/outbound-call` (`main.py:176`, `:234`) and guarded by
`require_org_member` (`core/api/v1/outbound_calls.py`). Responses are plain dicts built by
`OutboundCallService._to_response` (`:1341`) — this repo does **not** use a `.to_dict()` ORM convention.

### Existing (unchanged under the recommended option)

| Method + path | Handler | Purpose |
|---|---|---|
| `POST /outbound-call/create` | `create_outbound_call` (`:81`) | Dial now, or queue when `scheduled_at` is set |
| `POST /outbound-call/create-from-file` | `create_outbound_call_from_file` (`:104`) | CSV/Excel batch; optional per-row `schedule_column` |
| `GET  /outbound-call/concurrency-max` | `get_outbound_concurrency_max` (`:205`) | `{max, ws_trigger_allowed}` for the modal |
| `POST /outbound-call/scheduled/list` | `list_scheduled_calls` (`:218`) | Paginated list (`page_no`, `page_size`, `filters`, `sort_by`, `sort_order`, date range) |
| `GET  /outbound-call/scheduled/{id}` | `get_scheduled_call` (`:247`) | Single row |
| `POST /outbound-call/scheduled/{id}/cancel` | `cancel_scheduled_call` (`:256`) | Cancel one |
| `POST /outbound-call/scheduled/bulk-cancel` | `bulk_cancel_scheduled_calls` (`:236`) | Cancel up to 500 |
| `POST /contact/schedule-calls` | `schedule_contact_calls` (`core/api/v1/contacts.py:186`) | Schedule from selected contacts; also dials ASAP when `scheduled_at` is omitted |

`CreateOutboundCallRequest` (`:21–44`): `agent_id` (required), `from_number?`, `to_numbers[]?` /
`to_number?`, `scheduled_at?`, `directory_id?`, `max_concurrency?`,
`provider?: "twilio"|"telnyx"|"websocket"`.

Response `mode` values: `immediate` | `bulk` | `scheduled` | `parallel_websocket`
(`types/outboundCall.ts:23`).

### Proposed additions

`TBD - needs product input` — only if FR-5(b) is chosen. If so, the new routes must be **thin wrappers**
that call the existing `OutboundCallService` methods (no logic in the router), per `CLAUDE.md`:

```
POST /api/v1/outbound-call/call-now   → OutboundCallService.create_outbound_call(scheduled_at=None)
POST /api/v1/outbound-call/schedule   → OutboundCallService.create_outbound_call(scheduled_at=<required>)
```

No WebSocket events are emitted for this feature; the UI polls (`POLL_MS = 5000`,
`ScheduledCallsPage.tsx:22`).

---

## 8. Backend implementation

Under the recommended UI-only option (FR-5a), **no backend change is required.** Files that would change
only if FR-4(c) or FR-5(b) is chosen:

- **Router:** `core/api/v1/outbound_calls.py` — `create_outbound_call`, `create_outbound_call_from_file`,
  `list_scheduled_calls`, `cancel_scheduled_call`, `bulk_cancel_scheduled_calls`, `get_scheduled_call`.
- **Service:** `core/services/outbound_call_service.py` (`OutboundCallService`, extends `BaseService`) —
  `create_outbound_call` (`:407`), `create_outbound_calls_from_rows` (`:475`), `_schedule_via_contacts`
  (`:506`), `_dial_now` (`:549`), `_dial_parallel_ws` (`:588`), `_persist_and_enqueue_rows` (`:711`),
  `_resolve_contact_when` (`:746`), `schedule_calls_for_contacts` (`:768`), `dispatch_scheduled_call`
  (`:866`), `drain_outbound_capacity` (`:1089`), `list_scheduled_calls` (`:1280`), `_to_response` (`:1341`).
- **Shared helpers already in place (reuse, do not re-implement):**
  `select_from_number` (`:253`), `resolve_batch_concurrency` / `get_env_outbound_ceiling`
  (`core/services/outbound_capacity.py`), `get_scheduling_timezone` (`core/services/org_settings.py`),
  the ingestion pipeline in `core/services/contact_ingestion/`.
- **Background work:** Procrastinate — one deferred job per row at that row's own `scheduled_at`
  (`enqueue_outbound_calls_batch`, `core/services/ingestion_queue.py`); periodic `drain_outbound_calls`
  refills freed per-batch slots. Worker manifest: `build/kubernetes/_base/call/outbound-call-worker.yaml`.
  This project uses Procrastinate, **not** Celery.

---

## 9. Frontend implementation

- **Route:** none of its own. The list renders inside the agent editor's **Schedule** section —
  `agent-form/sectionNav.ts:54` (`{ key: 'schedule', label: 'Schedule', icon: CalendarClock }`), gated
  edit-only (`:65`) and outbound-only (`:72`) → `agent-form/steps/ScheduleStep.tsx` →
  `components/scheduled-calls/ScheduledCallsPage.tsx` with `agentId` (list filtered, agent locked in the
  modal, Agent column hidden at `:251`).
- **Components to modify:**
  - `components/scheduled-calls/ScheduledCallsPage.tsx` — header + primary action (`:255–271`),
    empty state (`:298–311`), modal mount (`:314–323`).
  - `components/outbound-calls/NewOutboundCallModal.tsx` — mode prop, title (`:416`), submit label
    (`:400–410`), schedule checkbox + picker (`:597–635`), `immediateNotice` (`:388–394`), toasts (`:347–353`).
  - `components/scheduled-calls/ScheduledCallStatusChip.tsx` — only if statuses change (they should not).
- **New components:** none expected under the recommended one-modal-two-modes approach.
- **Form layout mode:** **modal** (existing `CustomModal` via `@/components/shared`). Keep `CustomButton`
  and the shared `DateTimePicker` — mandated by `CLAUDE.md` / `.cursor/rules/shared-components.mdc`.
- **State:** this repo uses **Jotai**, not Zustand — `atoms/OutboundCallsAtom.tsx`
  (`scheduledCallsAtom`, `fetchScheduledCalls`, `createOutboundCallAtom`,
  `createOutboundCallFromFileAtom`, `cancelScheduledCallAtom`, `cancelScheduledCallsAtom`).
  Components call atoms; atoms call `services/outboundCallService.ts`; HTTP goes through
  `utils/axios.ts`. TanStack Query is used only for the contacts schema/directory lists
  (`lib/api/contactSchemas.ts`, `lib/api/contactDirectories.ts`).
- **Types:** `types/outboundCall.ts` — add the mode prop type here, not inline in the component.
- **Listing component:** `CustomTable` (existing), with client-side polling and bulk-select. Unchanged.
- **Toasts:** `showToast` from `@/utils/toast`; API errors via `handleApiError` from `@/utils/helpers`.

### ⚠ Conventions Check

Flagged for the reader — the PRD skill's generic template assumes a different stack than this repo:

| Skill template assumes | This repo actually uses |
|---|---|
| `backend/app/models`, `backend/app/services` | `core/models/`, `core/services/`, `core/api/v1/` |
| `require_permission(...)` | `require_org_member` / `require_admin_or_owner` (`core/middleware/auth.py`) |
| `.to_dict()` serialization | hand-built response dicts (`OutboundCallService._to_response`) |
| Celery tasks | Procrastinate jobs |
| Zustand + React Query | Jotai (+ TanStack Query for the contacts lists only) |
| `postman/Tone-Test-API.postman_collection.json` | no `postman/` directory exists in this repo |

No convention violation is introduced by this feature as specified. The one design risk to watch is
FR-4(c): removing `scheduled_calls` rows for immediate bulk would also remove per-batch concurrency
enforcement, which lives entirely on those rows.

---

## 10. Postman collection & examples

There is no Postman collection checked into this repo (no `postman/` directory), so there is nothing to
update. Interactive API docs are served by FastAPI at `/docs`. Current request/response shapes for the two
behaviours the ticket distinguishes:

**Immediate call**

```http
POST /api/v1/outbound-call/create
Content-Type: application/json

{ "agent_id": "0b2f…", "to_number": "+14155550123" }
```
```json
{ "mode": "immediate", "status": "dialing", "agent_id": "0b2f…",
  "from_number": "+14155550100", "to_number": "+14155550123", "provider": "twilio" }
```
```bash
curl -X POST "$BASE/api/v1/outbound-call/create" -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"0b2f…","to_number":"+14155550123"}'
```

**Scheduled call**

```http
POST /api/v1/outbound-call/create
Content-Type: application/json

{ "agent_id": "0b2f…", "to_numbers": ["+14155550123", "+14155550124"],
  "scheduled_at": "2026-09-01T17:30:00Z", "max_concurrency": 5 }
```
```json
{ "mode": "scheduled", "count": 2, "invalid": [], "assigned": 2, "data": [ /* scheduled_call rows */ ] }
```
```bash
curl -X POST "$BASE/api/v1/outbound-call/create" -b cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"0b2f…","to_numbers":["+14155550123"],"scheduled_at":"2026-09-01T17:30:00Z"}'
```

Examples for any new endpoints: `TBD - needs product input` (blocked on FR-5).

---

## 11. Next steps (downstream skills)

- [ ] **Resolve the open product decisions first** — FR-1 (labels + one-modal-vs-two), FR-4 (where immediate
      bulk rows are listed), FR-5 (UI-only vs new endpoints), FR-6 (tab naming). Everything below is blocked
      on these; running a generator now would scaffold against `TBD`s.
- [ ] Re-run `/generate_feature_prd_and_implementation schedule-a-call` once decisions land, to replace the
      `TBD - needs product input` markers.
- [ ] Then run `/implement_feature_from_prd schedule-a-call`, or the individual generators:
      - `/form_page` with `layout=modal` — only if FR-1 lands on a new/split modal.
      - `/backend_form` — only if FR-5(b) adds explicit `call-now` / `schedule` endpoints.
      - `/table_page` + `/backend_tables` — **not needed**; `POST /outbound-call/scheduled/list` and
        `ScheduledCallsPage` (CustomTable) already exist. Modify, don't regenerate.
- [ ] Alembic migration — **only** if FR-4(c) / a `kind` discriminator is approved
      (`alembic revision --autogenerate -m "outbound call kind"`).
- [ ] Tests: extend `test-cases/core/test_outbound_calls.py` with the new cases in §5; add/extend a
      Playwright spec under `frontend/e2e/` for the split entry points.
- [ ] Postman: N/A — no collection in this repo.

---

## 12. Change Log

- 2026-08-28 — Initial PRD authored from ClickUp task 86d44t3xg, non-interactively. Current
  immediate-vs-scheduled behaviour documented from code; open product decisions recorded as
  `TBD - needs product input` rather than invented.
