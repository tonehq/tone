# Channels — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

A **Channel** is a per-organization integration with a telephony / transport provider (Twilio, Telnyx, Exotel, Plivo, Daily WebRTC, raw WebSocket) that carries credentials and one or more [[phone_numbers]] routable to specific [[agents]]. Channels are how callers REACH agents — the transport layer for the voice pipeline.

Each channel stores an encrypted `encrypted_config` JSONB blob (AES-encrypted via `core/utils/encryption.py`) holding provider API keys, account SIDs, and auth tokens. The voice pipeline ([[voice-pipeline]]) reads this at call boot to instantiate the right Pipecat transport.

- **Target users**: org admins (set up telephony for the org), operators (assign phone numbers to agents).
- **Problem solved**: a single place to store provider credentials per org and a routing layer that maps `phone_number → channel → agent → pipeline`.

Cross-links: [[agents]] (each agent has many phone numbers), [[voice-pipeline]] (reads channel config at call-start), [[call-logs]] (records which channel handled each call).

## 2. User stories & use cases

- As an org admin, I want to connect a Twilio account so my org can receive calls.
- As an org admin, I want to view all channels my org has configured (Twilio + Daily + ...) on the Integrations page.
- As an operator, I want to assign one of the org's phone numbers to an agent (Twilio → agent X).
- As a tester, I want a WebSocket channel for browser-based testing of agent behavior without telephony.
- As an org admin, I want to remove a channel that's no longer needed.

Typical flow: Admin → `/integrations` → "Channels" tab → "Add Twilio" button → modal with API key + auth token + account SID → submit → backend encrypts and stores in `channels.encrypted_config` → admin assigns phone numbers via [[agents]] form.

## 3. Functional requirements

- **`POST /channel/upsert`**: create or update a channel (Twilio/Telnyx/etc.) for the org with encrypted credentials.
- **`POST /channel/list`**: paginated list with sort/search/filter.
- **`GET /channel/all`**: flat array of all channels (dropdown helper).
- **`GET /channel/get?id=...`**: fetch one channel (returns decrypted config? ⚠ verify).
- **`GET /channel/get_by_type?channel_type=...`**: most-recent channel for a type.
- **`GET /channel/list_by_type?channel_type=...`**: all channels of a type in the org.
- **`DELETE /channel/delete?id=...`**: delete a channel.
- **`GET /channel/phone_numbers?channel_id=...`**: list phone numbers attached to a channel.
- **Supported types** (`channel_type` enum-like values): `twilio`, `telnyx`, `exotel`, `plivo`, `daily`, `websocket`.
- **Credential encryption**: every value in `encrypted_config` is AES-encrypted via `core/utils/encryption.encrypt_auth_config`.
- **Unique constraint**: `UNIQUE(organization_id, name)` — channel names must be unique within an org.

### Edge cases & failure modes

- **⚠ Frontend hard-codes only Twilio**: `frontend/src/components/integrations/channel-form-modal.tsx` declares `CHANNEL_TYPE_OPTIONS = [{label:'Twilio', value:'twilio'}]` despite the backend accepting 6 types.
- **⚠ Telephony WebSocket router is disabled**: `main.py:123` comments out `/ws` and `/ws/test` routes with "depends on `AgentChannel/CallLog`". The channel is selectable but no transport endpoint serves it.
- **⚠ Architectural duplication**: `core/bot.py` reads telephony credentials from `service_providers` (the [[model-providers]] catalog), not from `channels`. Two sources of truth for the same secret material.
- **⚠ Legacy frontend service**: `frontend/src/services/phoneNumberService.ts` calls `/channel_phone_number/get_twilio_phone_numbers` and `/agent_channel_phone_number/get_assigned_phone_numbers` — both routes are missing from `main.py`. The three legacy Postman collections (`channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony`) document those dead endpoints.
- **⚠ `delete_channel` does not catch `IntegrityError`**: `phone_numbers.channel_id` has `ON DELETE RESTRICT`. Deleting a channel that still has phone numbers raises a 500. Should be caught and surfaced as a 409 with a friendly message.
- **⚠ No audit logging** on the channel write/delete paths.
- **⚠ No backend tests** under `core/tests/test_*channel*.py`.
- **No `is_active` flag**: delete is the only way to disable.
- **Get-decrypted-config flow**: only the service helper (`get_decrypted_config`) is intended for internal callers (pipeline boot). The HTTP `GET /channel/get` ⚠ should NOT return decrypted credentials — verify.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `BaseService.query()` org-filter on `channels`.
- **AuthN**: `require_org_member`.
- **RBAC**: ⚠ none enforced.
- **Secrets at rest**: `encrypted_config` JSONB is AES-encrypted per-value.
- **Audit logging**: ⚠ none.
- **EE parity**: `ee/api/v1/channels.py` mirrors 1:1 and imports `list_phone_numbers_for_channel` from core.
- **Performance**: 1 query per endpoint; no N+1 since `get_all_channels` doesn't enrich with phone numbers.

## 5. Test cases (as-built)

⚠ **No dedicated test file** for `/channel/*`. The block below is the locked-in behavior.

```
TEST: upsert_create_twilio
  GIVEN authenticated owner in org A
  WHEN  POST /channel/upsert
        body {"name":"prod-twilio","channel_type":"twilio","config":{"account_sid":"AC...","auth_token":"..."}}
  THEN  200; new row in channels; encrypted_config values AES-encrypted

TEST: upsert_duplicate_name_409
  GIVEN channel "prod-twilio" already exists in org A
  WHEN  POST /channel/upsert with same name
  THEN  409 "Channel name already exists"

TEST: list_channels_pagination
  GIVEN 5 channels in org A
  WHEN  POST /channel/list {"page": 1, "page_size": 3}
  THEN  200; items.length == 3, total == 5

TEST: get_by_type
  GIVEN 2 twilio channels in org A
  WHEN  GET /channel/get_by_type?channel_type=twilio
  THEN  most-recent one (by updated_at)

TEST: list_by_type
  GIVEN 2 twilio + 1 daily in org A
  WHEN  GET /channel/list_by_type?channel_type=twilio
  THEN  2 items, all twilio

TEST: delete_channel_with_phone_numbers
  GIVEN channel X has 2 phone numbers
  WHEN  DELETE /channel/delete?id=X
  THEN  ⚠ 500 (uncaught IntegrityError) — should be 409 with friendly message

TEST: phone_numbers_for_channel
  GIVEN channel X has phone +15551234567
  WHEN  GET /channel/phone_numbers?channel_id=X
  THEN  200; [{"id":..., "number":"+15551234567", "agent_id":..., "label":...}]

TEST: cross_org_isolation
  GIVEN channel X in org A, caller in org B
  WHEN  GET /channel/get?id=X
  THEN  404
```

## 6. Data model / DB schema

**Table: `channels`** (`core/models/channel.py`)

| Column            | Type        | Null | Default     | Notes                                                |
|-------------------|-------------|------|-------------|------------------------------------------------------|
| id                | UUID        | NO   | `uuid4()`   | PK                                                   |
| organization_id   | UUID        | NO   | —           | Multi-tenancy boundary                               |
| name              | VARCHAR(80) | NO   | —           | Unique within org                                    |
| channel_type      | VARCHAR(30) | NO   | —           | `twilio` / `telnyx` / `exotel` / `plivo` / `daily` / `websocket` |
| encrypted_config  | JSONB       | YES  | —           | AES-encrypted credentials                            |
| created_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |
| updated_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |

**Indexes**: `ix_channels_organization_id`; `UNIQUE(organization_id, name)`.

**Table: `phone_numbers`** (`core/models/phone_number.py`)

| Column            | Type        | Null | Default     | Notes                                                |
|-------------------|-------------|------|-------------|------------------------------------------------------|
| id                | UUID        | NO   | `uuid4()`   | PK                                                   |
| organization_id   | UUID        | NO   | —           |                                                      |
| channel_id        | UUID        | NO   | —           | FK → `channels.id` (`ON DELETE RESTRICT` ⚠)         |
| agent_id          | UUID        | YES  | —           | FK → `agents.id` (`ON DELETE SET NULL`)              |
| number            | VARCHAR(20) | NO   | —           | E.164 format                                         |
| label             | VARCHAR(80) | YES  | —           | Display label                                        |
| created_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |
| updated_at        | TIMESTAMPTZ | NO   | `now()`     |                                                      |

**Migration**: `alembic/versions/a0b1c2d3e4f5_tone_v2_full_schema_revamp.py` creates both tables.

## 7. API design

All endpoints under prefix `/api/v1/channel`. Auth: JWT bearer. RBAC: ⚠ none.

| Method | Path                                     | Purpose                                       |
|--------|------------------------------------------|-----------------------------------------------|
| POST   | `/channel/upsert`                        | Create or update a channel                    |
| POST   | `/channel/list`                          | Paginated list with search/sort/filter        |
| GET    | `/channel/all`                           | Flat array of all channels in org             |
| GET    | `/channel/get?id=...`                    | Fetch one channel                             |
| GET    | `/channel/get_by_type?channel_type=...`  | Most-recent channel of a type                 |
| GET    | `/channel/list_by_type?channel_type=...` | All channels of a type                        |
| DELETE | `/channel/delete?id=...`                 | Delete a channel ⚠ uncaught FK error          |
| GET    | `/channel/phone_numbers?channel_id=...`  | List phone numbers attached to a channel      |

### Request: POST /channel/upsert

```json
{
  "name": "prod-twilio",
  "channel_type": "twilio",
  "config": {
    "account_sid": "AC...",
    "auth_token": "...",
    "from_number": "+15551234567"
  }
}
```

### Response

```json
{
  "id": "uuid", "organization_id": "uuid", "name": "prod-twilio",
  "channel_type": "twilio", "config_keys": ["account_sid","auth_token","from_number"],
  "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}
```

⚠ `config_keys` lists which keys are set without exposing the values. Verify exact response shape.

### Referenced but not present

- ⚠ Legacy: `/channel_phone_number/get_twilio_phone_numbers` (called by FE, missing from `main.py`).
- ⚠ Legacy: `/agent_channel_phone_number/get_assigned_phone_numbers` (called by FE, missing).
- ⚠ Disabled: `/ws` and `/ws/test` (commented out in `main.py:123`).
- ⚠ No `POST /channel/test_connection` health check.

## 8. Backend implementation

- **Controller**: `core/api/v1/channels.py` — 8 routes; helper `list_phone_numbers_for_channel(db, org_id, channel_id)`.
- **EE Controller**: `ee/api/v1/channels.py` — mirrors; imports `list_phone_numbers_for_channel` from core.
- **Service**: `core/services/channel_service.py` — `ChannelService(BaseService)`.
  - `upsert_channel`, `list_channels`, `get_all_channels`, `get_channel`, `get_channel_by_type`, `get_channels_by_type`, `delete_channel`.
  - `get_or_create_channel_by_type` (used by EE seeding flows).
  - `get_decrypted_config(channel_id)` — used internally by pipeline boot; never exposed via HTTP.
- **Encryption**: `core/utils/encryption.encrypt_auth_config(config_dict)` AES-encrypts every value; `decrypt_auth_config` reverses.
- **Models**: `core/models/channel.py`, `core/models/phone_number.py`.
- **No audit logging**, no Celery tasks.

## 9. Frontend implementation

- **Route**: `/integrations` — `frontend/src/app/(dashboard)/integrations/page.tsx`.
- **Main component**: `frontend/src/components/settings/Integrations.tsx` — tabs split into Services (OAuth) and **Channels**.
- **Channel components** (`frontend/src/components/integrations/`):
  - `channel-grid.tsx` — grid of channel cards.
  - `channel-card.tsx` — per-channel card.
  - `channel-form-modal.tsx` — create/edit modal. ⚠ Hard-codes `CHANNEL_TYPE_OPTIONS = [{label:'Twilio', value:'twilio'}]`.
- **API service**: `frontend/src/services/channelService.ts` — `listChannels`, `getChannel`, `upsertChannel`, `deleteChannel`.
- **Legacy phone-number service**: `frontend/src/services/phoneNumberService.ts` — ⚠ calls dead `/channel_phone_number/*` and `/agent_channel_phone_number/*` routes.
- **State**: Jotai atoms in `frontend/src/atoms/IntegrationAtom.tsx`.
- **Layout mode**: modal (create/edit). Only a handful of fields.

## 10. Postman collection & examples

`postman_collection/channels.postman_collection.json` is the current source. The three legacy collections (`channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony`) reference dead endpoints. ⚠

### POST /api/v1/channel/upsert

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "name": "prod-twilio",
    "channel_type": "twilio",
    "config": {"account_sid": "AC...", "auth_token": "secret"}
  }' \
  "$BASE_URL/api/v1/channel/upsert"
```

### POST /api/v1/channel/list

```json
{"page": 1, "page_size": 10, "search": "twilio"}
```

### GET /api/v1/channel/phone_numbers?channel_id=...

```json
[
  {"id": "uuid", "number": "+15551234567", "channel_id": "uuid", "agent_id": "uuid", "label": "Main line"}
]
```

## 11. Next steps

- [ ] ⚠ **Re-enable telephony WebSocket router**: `/ws` and `/ws/test` are commented out in `main.py:123`. Resolve the `AgentChannel/CallLog` dependency and turn it back on.
- [ ] ⚠ **Reconcile `service_providers` vs `channels`**: `core/bot.py` reads telephony credentials from the [[model-providers]] catalog rather than from `channels`. Pick one source of truth.
- [ ] ⚠ **Frontend: unlock all 6 channel types** in `CHANNEL_TYPE_OPTIONS`.
- [ ] ⚠ **Delete or fix legacy FE service**: `phoneNumberService.ts` calls dead endpoints.
- [ ] ⚠ **Drop or refresh legacy Postman collections** (`channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony`).
- [ ] ⚠ **Catch `IntegrityError` on `delete_channel`** and return 409 with "channel has N phone numbers, detach first".
- [ ] ⚠ **Add audit logging** on upsert/delete (channel credentials are sensitive).
- [ ] ⚠ **Add RBAC**: channel mgmt should require admin/owner.
- [ ] **Add `POST /channel/test_connection`** to validate credentials before saving (Twilio's API-keys endpoint, Daily's domain check, etc.).
- [ ] **Add tests** under `tests/test_channels.py`.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) Frontend hard-codes only Twilio despite backend accepting 6 types; (2) `/ws` and `/ws/test` telephony WebSocket routes disabled in `main.py:123`; (3) Architectural duplication: `core/bot.py` reads credentials from `service_providers`, not from `channels`; (4) Frontend `phoneNumberService.ts` calls dead `/channel_phone_number/*` and `/agent_channel_phone_number/*` routes; (5) Three legacy Postman collections (`channel_phone_numbers`, `agent_channel_phone_numbers`, `telephony`) document dead endpoints; (6) `delete_channel` does not catch `IntegrityError` from `phone_numbers.channel_id ON DELETE RESTRICT` — raises 500 instead of 409; (7) No audit logging; (8) No backend tests; (9) No `is_active` flag on channels (delete is only way to disable); (10) No `POST /channel/test_connection` health check.
