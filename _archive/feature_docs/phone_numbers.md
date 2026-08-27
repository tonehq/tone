# Phone Numbers — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

A **Phone Number** is the routing primitive that maps an inbound (or outbound) E.164 number to a specific [[agents|Agent]] via a [[channels|Channel]]. Each phone number row belongs to exactly one organization, sits on exactly one channel (Twilio / Telnyx / Exotel / Plivo / etc.), and is optionally assigned to one agent. When a call lands on `+1 555 123 4567`, the [[voice-pipeline]] resolves `phone_number → channel → agent` to pick which agent (and which provider credentials) handles the call.

There is no standalone `/phone-numbers` controller in `core/api/v1/`. Phone numbers are managed *through* the [[agents]] and [[channels]] endpoints — `POST /agent/create_agent` and `PUT /agent/update_agent` accept `phone_numbers[]` payloads (declarative replace), and `GET /channel/phone_numbers?channel_id=...` lists numbers attached to a channel.

- **Target users**: operators (assign incoming numbers to agents), agent owners (see which numbers route to my agent).
- **Problem solved**: a separate routing layer between the channel (credentials + provider) and the agent (behavior) — one channel can carry many numbers, and a number can be re-pointed to a different agent without rotating provider credentials.

Cross-links: [[agents]] (the row's `agent_id` FK), [[channels]] (the row's `channel_id` FK), [[voice-pipeline]] (resolves the routing at call-start), [[call-logs]] (records which phone number each call came from).

## 2. User stories & use cases

- As an operator, I want to attach a Twilio phone number to an agent so calls to that number land on that agent.
- As an operator, I want to move a phone number from agent A to agent B without re-buying or re-provisioning the number.
- As an operator, I want to free up a number (detach from agent) without deleting it from the channel.
- As an agent owner, I want to see all numbers routing to my agent in the agent edit form.
- As an admin, I want to see all numbers attached to a Twilio channel before disconnecting it.

Typical flow: Operator opens [[agents]] edit page → "Phone Numbers" section → adds `+15551234567` with `channel_id = <twilio-channel>` → submits → backend `_sync_phone_numbers` upserts the row and reassigns `agent_id`.

## 3. Functional requirements

- **CRUD via [[agents]] payload**:
  - Create: `phone_numbers[]` in `POST /agent/create_agent` body — backend creates rows pointing at this agent.
  - Update: `phone_numbers[]` in `PUT /agent/update_agent` body — backend does a **declarative replace**:
    - Numbers in the incoming list are kept/created on this agent.
    - Numbers currently on this agent but **NOT** in the list are **deleted** (not just unlinked).
  - The replace is implemented by `AgentService._sync_phone_numbers`.
- **List via [[channels]]**: `GET /channel/phone_numbers?channel_id=...` returns the full set of numbers on a channel (with `agent_id` and `label`).
- **Enriched agent listing**: `_phone_numbers_for(db, org_id, agent_ids)` in `core/api/v1/agents.py` batch-fetches a `{agent_id → [{type, no}]}` map joining `phone_numbers` → `channels` in a single SQL round-trip. Used by `POST /agent/list` to render the number badges in the agent table.
- **Unique constraint**: `UNIQUE(organization_id, number)` — the same E.164 number cannot exist twice within an org.
- **Channel FK is `ON DELETE RESTRICT`**: a channel cannot be deleted while it still has phone numbers. ⚠ See edge cases.
- **Agent FK is `ON DELETE SET NULL`**: deleting an agent frees its numbers (they stay on the channel, agent-less).

### Edge cases & failure modes

- **Cross-agent reassignment is rejected**: in `_sync_phone_numbers`, if a number `+15550001111` is already assigned to a **different** agent in the same org, the agent update returns **HTTP 409** `"Phone number +15550001111 is already assigned to another agent"`. To move a number, first remove it from the source agent.
- **Cross-org reassignment is blocked structurally**: the unique constraint `(organization_id, number)` plus the org-scoped query means org B literally cannot see / claim a number registered in org A.
- **Declarative replace is destructive**: omitting a number from `phone_numbers[]` on update **deletes** that row from the DB (not just unlinks). Re-creating it later requires reissuing from the channel provider. ⚠ This is surprising — verify the frontend always sends the full desired set.
- **No agent-less detach**: there is no `null`-agent path through the [[agents]] payload. To leave a number on the channel without an agent, you'd have to delete it via the agent update (no number in the list) and then re-add it later through the channel — there's no `PATCH /phone-number` endpoint.
- **⚠ Channel delete fails on FK**: `DELETE /channel/delete?id=X` with attached numbers raises a 500 (uncaught `IntegrityError`) because of `ON DELETE RESTRICT`. The fix lives in [[channels]] §11.
- **⚠ No `POST /phone-number` / `DELETE /phone-number` endpoints**: phone numbers cannot be managed independently of an agent payload. If you want to provision a number without binding it to an agent immediately, there is no API for that today.
- **⚠ Legacy frontend service** (`frontend/src/services/phoneNumberService.ts`) calls dead routes (`/channel_phone_number/get_twilio_phone_numbers`, `/agent_channel_phone_number/get_assigned_phone_numbers`) — neither exists in `main.py`. The Postman collections `channel_phone_numbers`, `agent_channel_phone_numbers`, and `telephony` document the same dead endpoints. See [[channels]] §3.
- **⚠ No Twilio "buy a number" API integration**: numbers must already exist on the Twilio account. Tone does not call `POST https://api.twilio.com/.../IncomingPhoneNumbers` to provision new numbers on the customer's behalf.
- **No `is_active` flag**: delete is the only way to disable a routing entry.
- **No format validation on `number`**: stored as a free `VARCHAR(20)`. ⚠ A malformed number (`"+5551"`) will be accepted on insert and only fail at call-time when Twilio rejects it. The frontend should validate E.164 client-side.
- **`label` is optional and free-form** — has no impact on routing.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `organization_id` (inherited from `OrgScopedModel`) plus the `UNIQUE(organization_id, number)` constraint. Cross-org reads are structurally prevented.
- **AuthN**: same as the parent surface — [[agents]] mutations require `require_org_member`; `GET /channel/phone_numbers` also requires it.
- **RBAC**: ⚠ none enforced. Any org member can reassign any number.
- **Performance**: agent-list enrichment is one batched SQL (`_phone_numbers_for`); no N+1. The phone-numbers table is small (one row per provisioned number per org — typically <1000).
- **Audit logging**: ⚠ none. Reassigning a number from one agent to another is a routing change with no trail.
- **Observability**: no metrics on phone-number churn or routing changes.
- **EE parity**: handled via the same shared `AgentService._sync_phone_numbers` invoked from both Core and EE agent controllers.

## 5. Test cases (as-built)

⚠ **No dedicated pytest suite** for phone-number handling. The cases below are the locked-in behaviors implied by `AgentService._sync_phone_numbers` and `core/api/v1/channels.py:list_phone_numbers_for_channel`.

```
TEST: create_agent_with_phone_numbers
  GIVEN authenticated user in org A; channel C exists
  WHEN  POST /agent/create_agent body={
          "name":"X","agent_type":"inbound",
          "phone_numbers":[{"number":"+15551234567","channel_id":C,"label":"Main"}]
        }
  THEN  201; phone_numbers row created with agent_id=X.id, channel_id=C

TEST: list_phone_numbers_for_channel
  GIVEN channel C has 2 phone numbers
  WHEN  GET /channel/phone_numbers?channel_id=C
  THEN  200; [{"id":..,"number":..,"agent_id":..,"label":..}, ...]

TEST: update_agent_replace_keeps_existing
  GIVEN agent X has phone_numbers=[+15551111111, +15552222222]
  WHEN  PUT /agent/update_agent?agent_id=X phone_numbers=[{number:+15551111111,channel_id:C}, {number:+15552222222,channel_id:C}]
  THEN  200; both rows untouched

TEST: update_agent_replace_drops_omitted
  GIVEN agent X has phone_numbers=[+15551111111, +15552222222]
  WHEN  PUT /agent/update_agent?agent_id=X phone_numbers=[{number:+15551111111,channel_id:C}]
  THEN  200; +15552222222 row DELETED ⚠ (declarative replace)

TEST: cross_agent_reassign_blocked
  GIVEN +15550001111 already assigned to agent Y in org A
  WHEN  PUT /agent/update_agent?agent_id=X phone_numbers=[{number:+15550001111,channel_id:C}]
  THEN  409 "Phone number +15550001111 is already assigned to another agent"

TEST: same_agent_reassign_noop
  GIVEN +15550001111 already on agent X with label "Main"
  WHEN  PUT /agent/update_agent?agent_id=X phone_numbers=[{number:+15550001111,channel_id:C,label:"New Label"}]
  THEN  200; row updated in place (label changes; channel_id can change)

TEST: cross_org_isolation
  GIVEN phone_number +15551234567 in org A on channel CA
  WHEN  PUT /agent/update_agent as user in org B with same number+channel
  THEN  channel CA not visible in org B → 404 (or 400 on channel lookup)

TEST: delete_agent_frees_phone_numbers
  GIVEN agent X has 2 phone numbers
  WHEN  DELETE /agent/delete_agent?agent_id=X
  THEN  200; phone_numbers rows DELETED in cascade
        (the agent CRUD cascades; not the FK's ON DELETE SET NULL,
         which would have left them with agent_id=NULL)
        ⚠ Verify exact cascade behavior in AgentService.delete_agent

TEST: channel_delete_with_numbers_fails
  GIVEN channel C has 1 phone number
  WHEN  DELETE /channel/delete?id=C
  THEN  ⚠ 500 (uncaught IntegrityError, ON DELETE RESTRICT)
```

## 6. Data model / DB schema

**Table: `phone_numbers`** (`core/models/phone_number.py`)

| Column          | Type        | Null | Default     | Notes                                                  |
|-----------------|-------------|------|-------------|--------------------------------------------------------|
| id              | UUID        | NO   | `uuid4()`   | PK (inherited from `OrgScopedModel`)                   |
| organization_id | UUID        | NO   | —           | Multi-tenancy boundary (inherited from `OrgScopedModel`)|
| number          | VARCHAR(20) | NO   | —           | E.164 format (`+15551234567`)                          |
| channel_id      | UUID        | NO   | —           | FK → `channels.id` `ON DELETE RESTRICT` ⚠              |
| agent_id        | UUID        | YES  | —           | FK → `agents.id` `ON DELETE SET NULL`                  |
| label           | VARCHAR(200)| YES  | —           | Human-readable display ("Main line", "Sales queue")    |
| created_at      | TIMESTAMPTZ | NO   | `now()`     | (inherited)                                            |
| updated_at      | TIMESTAMPTZ | NO   | `now()`     | (inherited)                                            |

**Indexes / constraints**:
- `UNIQUE(organization_id, number)` — `uq_phone_numbers_org_number`. Same number cannot exist twice in an org.
- Implicit index on `organization_id` (from `OrgScopedModel`).

**Foreign-key behaviors**:
- `channel_id ON DELETE RESTRICT` — channels with attached numbers cannot be deleted. ⚠ See [[channels]] §3.
- `agent_id ON DELETE SET NULL` — deleting an agent frees its numbers. **BUT** `AgentService.delete_agent` cascades through `phone_numbers` directly (hard delete), so this `SET NULL` path is dead today — see [[agents]] §3.

**Migration**: created by `alembic/versions/a0b1c2d3e4f5_tone_v2_full_schema_revamp.py` alongside `channels`.

## 7. API design

⚠ **No dedicated `/phone-number` prefix exists in `core/api/v1/`.** Phone-number CRUD happens through two parent surfaces:

### Via [[agents]] — `/api/v1/agent`

| Method | Path                                | Phone-number behavior                                            |
|--------|-------------------------------------|------------------------------------------------------------------|
| POST   | `/agent/create_agent`               | Body `phone_numbers[]` creates rows pointing at the new agent    |
| PUT    | `/agent/update_agent?agent_id=...`  | Body `phone_numbers[]` does declarative replace (see §3)         |
| DELETE | `/agent/delete_agent?agent_id=...`  | Cascades through `phone_numbers` (hard delete)                   |
| POST   | `/agent/list`                       | Each row's `phone_number[]` is batch-enriched via `_phone_numbers_for` |
| GET    | `/agent/get_agent?agent_id=...`     | Response embeds `phone_numbers[]` array                          |

### Via [[channels]] — `/api/v1/channel`

| Method | Path                                          | Phone-number behavior                          |
|--------|-----------------------------------------------|------------------------------------------------|
| GET    | `/channel/phone_numbers?channel_id=...`       | Lists numbers attached to a channel            |

### Request shape — `phone_numbers[]` element

```json
{
  "number": "+15551234567",
  "channel_id": "uuid-channel",
  "label": "Main line"
}
```

### Response shape — embedded in agent detail

```json
{
  "phone_numbers": [
    {
      "id": "uuid",
      "number": "+15551234567",
      "channel_id": "uuid",
      "agent_id": "uuid",
      "label": "Main line"
    }
  ]
}
```

### Response shape — agent list enrichment (`_phone_numbers_for`)

```json
{
  "items": [
    {
      "id": "agent-uuid",
      "name": "Acme Bot",
      "phone_number": [
        {"type": "twilio", "no": "+15551234567"}
      ]
    }
  ]
}
```

Note: the list-enrichment shape uses `phone_number` (singular) with `{type, no}` keys — different from the detail shape's `phone_numbers` (plural) with `{id, number, channel_id, agent_id, label}`. ⚠ Inconsistent — see [[agents]] §3.

### ⚠ Referenced but NOT implemented

- ⚠ `GET /channel_phone_number/get_twilio_phone_numbers` — called by `frontend/src/services/phoneNumberService.ts` (legacy). Does not exist in `main.py`.
- ⚠ `GET /agent_channel_phone_number/get_assigned_phone_numbers` — same: called by FE, dead in BE.
- ⚠ No `POST /phone-number` standalone create.
- ⚠ No `PATCH /phone-number/{id}` standalone update.
- ⚠ No `DELETE /phone-number/{id}` standalone delete.
- ⚠ No Twilio "buy a number" passthrough — Tone cannot provision new numbers on the customer's Twilio account.

## 8. Backend implementation

- **Model**: `core/models/phone_number.py` (19 lines) — `PhoneNumber(OrgScopedModel)`.
- **Service logic**: `core/services/agent_service.py:AgentService._sync_phone_numbers` — the declarative-replace implementation. Handles:
  - Pre-check: any number in the incoming list that's already assigned to a **different** agent in the same org → raise 409.
  - For each number in the incoming list: `INSERT … ON CONFLICT (organization_id, number) DO UPDATE SET agent_id, channel_id, label`.
  - For each number currently on this agent but NOT in the incoming list: `DELETE` the row.
- **Controller helpers**:
  - `core/api/v1/agents.py:_phone_numbers_for(db, org_id, agent_ids)` — batched enrichment for list view. Joins `phone_numbers` → `channels` and returns `{agent_id: [{type, no}]}`.
  - `core/api/v1/channels.py:list_phone_numbers_for_channel(db, org_id, channel_id)` — the helper behind `GET /channel/phone_numbers`. Shared with EE via direct import.
- **No service layer of its own** — there is no `PhoneNumberService`. Logic lives inside `AgentService` and the two controllers' helpers.
- **No audit logging**, no Celery tasks, no Pydantic schema for `PhoneNumber` (it's defined inline in `core/api/v1/agents.py` as `PhoneNumberAttachment`).

## 9. Frontend implementation

- **No dedicated route**: phone-number management is embedded in the [[agents]] form.
- **Agent form** (`frontend/src/components/agents/agent-form/`):
  - The "Phone Numbers" sub-section of the agent form renders a list of `{number, channel_id, label}` rows with add/remove controls.
  - On submit, the array is serialized as `phone_numbers[]` in the create/update payload (via `agentFormUtils.formStateToUpsertPayload`).
- **Agent list page** (`frontend/src/components/agents/AgentListPage.tsx`):
  - Renders `PhoneNumberDisplay` per row using the `phone_number[]` array from the list response (the `{type, no}` enriched shape).
- **API service**: `frontend/src/services/agentsService.ts` — phone numbers travel through the agent endpoints; there is no dedicated `phoneNumberService` API caller used today.
- **⚠ Orphaned service file**: `frontend/src/services/phoneNumberService.ts` exists and exports functions, but its endpoints are dead (`/channel_phone_number/get_twilio_phone_numbers`, `/agent_channel_phone_number/get_assigned_phone_numbers`). No component imports it.
- **State**: phone numbers are part of the form-level RHF state inside the agent edit form. No standalone Jotai atom.
- **Validation**: ⚠ frontend should validate E.164 format client-side. Verify with `react-hook-form` resolver / Zod schema.

## 10. Postman collection & examples

⚠ The three legacy collections — `channel_phone_numbers.postman_collection.json`, `agent_channel_phone_numbers.postman_collection.json`, `telephony.postman_collection.json` — document **dead endpoints** that have been removed from `main.py`. Drop them, or refresh to point at the [[agents]] / [[channels]] payload shape.

Live examples (under [[agents]] and [[channels]]):

### POST /api/v1/agent/create_agent (with numbers)

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Bot",
    "agent_type": "inbound",
    "phone_numbers": [
      {"number": "+15551234567", "channel_id": "uuid-twilio-channel", "label": "Main"},
      {"number": "+15559876543", "channel_id": "uuid-twilio-channel", "label": "Backup"}
    ]
  }' \
  "$BASE_URL/api/v1/agent/create_agent"
```

### PUT /api/v1/agent/update_agent (declarative replace — drops omitted numbers)

```bash
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"phone_numbers": [{"number": "+15551234567", "channel_id": "uuid"}]}' \
  "$BASE_URL/api/v1/agent/update_agent?agent_id=550e8400-..."
```

⚠ Note: the "+15559876543" row from the create example is now **deleted** because it was omitted from the update payload.

### GET /api/v1/channel/phone_numbers?channel_id=...

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/channel/phone_numbers?channel_id=uuid-twilio-channel"
```

```json
[
  {"id": "uuid", "number": "+15551234567", "agent_id": "uuid-agent-A", "label": "Main"},
  {"id": "uuid", "number": "+15559876543", "agent_id": null, "label": "Unassigned"}
]
```

## 11. Next steps

This feature is **functional through the [[agents]] and [[channels]] surfaces** but has rough edges that should be addressed.

- [ ] ⚠ **Add standalone `/phone-number/*` endpoints**: `POST /phone-number` (provision without binding to an agent), `PATCH /phone-number/{id}` (rename / move between agents), `DELETE /phone-number/{id}` (remove without an agent payload). Useful for ops workflows where the number is bought first and assigned later.
- [ ] ⚠ **Unify the list-vs-detail response shape**: list returns `phone_number[]` of `{type, no}`; detail returns `phone_numbers[]` of `{id, number, channel_id, agent_id, label}`. Pick one and update the frontend.
- [ ] ⚠ **Catch `IntegrityError` on channel delete** so deleting a channel with phone numbers returns 409 (with message "detach N phone numbers first") instead of 500. See [[channels]] §11.
- [ ] ⚠ **Delete or fix `frontend/src/services/phoneNumberService.ts`** — it calls dead endpoints (`/channel_phone_number/*`, `/agent_channel_phone_number/*`).
- [ ] ⚠ **Drop the three legacy Postman collections**: `channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony` — all reference removed endpoints.
- [ ] ⚠ **Reconcile the agent-delete cascade**: today `AgentService.delete_agent` hard-deletes `phone_numbers` rows even though the FK is `ON DELETE SET NULL`. Pick one: either let the FK fire (numbers stay on the channel agent-less) or keep the explicit cascade and drop the `SET NULL` clause.
- [ ] ⚠ **Add E.164 validation** server-side (Pydantic validator on `PhoneNumberAttachment.number`). Today malformed numbers are accepted and only fail at call-time.
- [ ] ⚠ **Add audit logging**: routing changes (reassigning a number from one agent to another) are a security/ops event. Today there's no trail.
- [ ] ⚠ **Add tests** under `tests/test_phone_numbers.py` covering the §5 scenarios (declarative-replace, cross-agent-block, cross-org-isolation).
- [ ] **Frontend**: add a confirmation modal when an update would drop a phone number (declarative replace is destructive — users may not realize omitting an entry deletes the row).
- [ ] **Twilio number-buy passthrough**: optional — `POST /phone-number/provision?channel_id=...&area_code=...` could call Twilio's `IncomingPhoneNumbers` API to provision a new number on the customer's account and create the row in one shot.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) No dedicated `/phone-number/*` controller — CRUD is embedded in [[agents]] and [[channels]] surfaces; (2) Declarative-replace semantics on `PUT /agent/update_agent` silently **delete** omitted numbers — destructive and likely surprising; (3) Inconsistent response shapes between agent list (`phone_number[]` of `{type, no}`) and agent detail (`phone_numbers[]` of full row); (4) Channel delete with attached numbers raises uncaught `IntegrityError` (500 instead of 409); (5) Legacy frontend `phoneNumberService.ts` calls dead `/channel_phone_number/*` and `/agent_channel_phone_number/*` routes; (6) Three legacy Postman collections (`channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony`) document removed endpoints; (7) `phone_numbers.agent_id ON DELETE SET NULL` FK is shadowed by the explicit cascade in `AgentService.delete_agent`; (8) No E.164 validation on the backend — malformed numbers fail at call-time, not save-time; (9) No audit logging on routing changes; (10) No tests; (11) No Twilio "buy a number" passthrough — numbers must already exist on the customer's Twilio account.
