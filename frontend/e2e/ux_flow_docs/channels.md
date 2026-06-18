# Feature Doc: Channels (Telephony Integrations)

Feature documentation for the Channels tab on the Integrations page. Used by
`/generate-tests channels` (or `--docs e2e/ux_flow_docs/channels.md`) to ensure all user
cases are covered alongside the component source analysis.

A **Channel** is a per-organization integration with a telephony / transport
provider (Twilio today; Telnyx, Exotel, Plivo, Daily, WebSocket on the backend
roadmap). It stores encrypted provider credentials and carries the phone
numbers routable to agents.

---

## Page

- **Route**: `/settings/integrations` (Channels tab). `/integrations` redirects here.
- **Component**: `src/components/settings/Integrations.tsx`
- **Sub-components**:
  - `src/components/integrations/channel-grid.tsx`
  - `src/components/integrations/channel-card.tsx`
  - `src/components/integrations/channel-form-modal.tsx`
  - `src/components/integrations/channel-grid-skeleton.tsx`
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fsettings%2Fintegrations` without `tone_access_token` cookie)

---

## User Stories

### US-1: View configured channels

**As an** org admin, **I want to** see all telephony channels configured for my
org on the Channels tab, **so that** I know which provider accounts the org can
receive calls on.

**Acceptance criteria**:

- [ ] Channels tab shows the heading "Channels" with a Phone icon
- [ ] Tab label shows a count badge equal to the number of configured channels
- [ ] Each channel renders as a card with name, provider type badge (e.g. "TWILIO"), and "Updated X time ago"
- [ ] Loading state renders `ChannelGridSkeleton` with 2 placeholder cards (animate-pulse)
- [ ] Empty state shows a dashed border box with "No telephony channels yet — add your first one."

### US-2: Add a new channel

**As an** org admin, **I want to** add a Twilio account by entering credentials
in a modal, **so that** my org can start receiving calls on Twilio numbers.

**Acceptance criteria**:

- [ ] Click "Add channel" (dashed card with Plus icon) → `ChannelFormModal` opens
- [ ] Modal has 4 fields: Name, Type (default "twilio"), Auth Token (password), Account SID
- [ ] All fields are required and validated client-side with a Zod schema
- [ ] "Save" button shows "Saving…" + `disabled` while the request is in flight
- [ ] On success: modal closes, list refetches, success toast "Integration created successfully"
- [ ] On error: toast shown via `handleApiError`, modal remains open

### US-3: Edit an existing channel

**As an** org admin, **I want to** rotate Twilio credentials on an existing
channel, **so that** I can update tokens without recreating the channel.

**Acceptance criteria**:

- [ ] Click a channel card or "Edit" in the action menu (3-dot icon) → modal opens with fields pre-filled from `GET /channel/get`
- [ ] An `AppLoader` spinner shows while the modal hydrates
- [ ] The Type field is locked (read-only) in edit mode
- [ ] Submitting calls `POST /channel/upsert` with the existing channel id
- [ ] Phone numbers attached to the channel are unaffected by credential updates

### US-4: Delete a channel

**As an** org admin, **I want to** remove a channel I no longer use, **so that**
no agents accidentally route calls through a stale provider account.

**Acceptance criteria**:

- [ ] Action menu (3-dot icon) on each card shows a "Delete" item
- [ ] Confirming delete calls `DELETE /channel/delete` with the channel id
- [ ] Card is removed from the grid on success
- [ ] Channels with phone numbers still attached: backend response surfaces an error, frontend shows it via `handleApiError`

### US-5: Pre-select provider from the catalog

**As an** org admin, **I want to** click "Connect" on a Twilio tile in the
Available Providers catalog, **so that** the channel form opens with Twilio
pre-selected.

**Acceptance criteria**:

- [ ] Catalog tile "Connect" triggers `openAdd()` on the `ChannelGrid` ref
- [ ] Modal opens with the Type field locked to the chosen provider
- [ ] The rest of the create flow (US-2) applies

---

## User Workflow Steps

**WF-1: View the channels list** (positive)

1. User has a `tone_access_token` cookie → expected: middleware allows the request, page renders
2. User navigates to `/settings/integrations` → expected: header "Integrations" + subtitle render; Catalog section shows above the tabs
3. User clicks the "Channels" tab → expected: `TabsContent value="channels"` becomes active; `ChannelGrid` polls `POST /channel/list`
4. While the request is in flight → expected: `ChannelGridSkeleton` renders 2 animate-pulse cards
5. Response arrives with items → expected: each channel card shows Name, "TWILIO" provider pill, and "Updated X ago"; count badge on the tab equals `items.length`
6. Response is empty `[]` → expected: dashed empty-state box reads "No telephony channels yet — add your first one." and the "Add channel" CTA is visible

**WF-2: Add a new channel via the dashed CTA** (positive)

1. User clicks the dashed "Add channel" CTA → expected: `ChannelFormModal` opens with title "Add channel"
2. User sees fields: Name (text), Type (select, default "twilio"), Auth Token (password), Account SID (text)
3. User types `Twilio Production` → `auth_token: abc123` → `account_sid: AC1234567890abcdef` → expected: Save button enables (`formState.isValid` true)
4. User clicks Save → expected: button text becomes "Saving..." and `disabled=true`; `POST /channel/upsert` fires
5. On 201 success → expected: modal closes, `fetchChannelsAtom` re-runs, success toast "Integration created successfully" appears, new card animates in via framer-motion
6. On any error → expected: modal stays open, button reverts to "Save", error toast surfaced by `handleApiError`

**WF-3: Edit an existing channel** (positive)

1. User clicks an existing channel card → expected: `ChannelFormModal` opens with title "Edit channel"
2. `getChannel(id, include_config=true)` fires → expected: `AppLoader` (min-h-[260px]) renders while hydrating
3. On 200 response → expected: Name, Auth Token, Account SID pre-populate; Type field is disabled with helper text "Type cannot be changed after the channel is created."
4. User changes Auth Token and clicks Save → expected: `POST /channel/upsert` with `id` payload field
5. On 200 success → expected: modal closes, list refetches, toast "Integration updated successfully"

**WF-4: Delete a channel** (positive)

1. User opens the 3-dot action menu on a card → expected: menu shows "Edit" and "Delete"
2. User clicks "Delete" → expected: confirmation step (component default); on confirm, `DELETE /channel/delete?channel_id=<id>` fires
3. On 200 success → expected: card animates out (framer-motion exit), `fetchChannelsAtom` runs, toast "Integration deleted successfully"
4. On error → expected: card remains, toast surfaces backend `detail`

**WF-5: Catalog "Add API key" pre-selects provider** (positive)

1. User scrolls to the "API key" section in Available Providers → expected: Twilio tile renders with "Add API key" CTA
2. User clicks "Add API key" on Twilio → expected: `setActiveTab('channels')` flips the tab, `channelGridRef.current.openAdd('twilio')` opens the modal
3. Modal renders with Type field disabled and helper text "Pre-selected from the provider tile."
4. User completes Name/Auth Token/Account SID and saves → same as WF-2 step 5

**WF-6: Auth gating** (negative)

1. User has no `tone_access_token` cookie and visits `/settings/integrations` → expected: middleware 307 redirect to `/auth/login?redirect=%2Fsettings%2Fintegrations`
2. User logs in → expected: post-login redirect lands back on `/settings/integrations`

**WF-7: Refresh both lists from the header button** (positive)

1. User clicks the "Refresh" header button (RefreshCw icon) → expected: `fetchOAuthAtom` and `fetchChannelsAtom` both re-run
2. While in flight → expected: button shows `loading` state ("Loading..."), `ChannelGridSkeleton` renders briefly

---

## Input Specifications

### ChannelFormModal — create + edit

Source: `src/components/integrations/channel-form-modal.tsx` (Zod `channelFormSchema`, lines 17-21).

| Field          | Type            | Required | Validation Rules                            | Exact Error Message     |
| -------------- | --------------- | -------- | ------------------------------------------- | ----------------------- |
| Name           | text            | yes      | `z.string().min(1)`; trimmed before submit  | "Name is required"      |
| Type           | select          | yes      | Locked to "twilio" today; disabled in edit / pre-selected modes | n/a (locked) |
| Auth Token     | password        | yes      | `z.string().min(1)`; trimmed before submit  | "Auth token is required"|
| Account SID    | text            | yes      | `z.string().min(1)`; trimmed before submit  | "Account SID is required" |

**Button state rules:**

- Save is **disabled** while any of: `!formState.isValid`, `hydrating === true`, or `saving === true`.
- Save text flips to "Saving..." while `saving === true`.

---

## Success Scenarios

**PS-1: List loads with one Twilio channel**

- **Preconditions**: authenticated; user has 1 channel.
- **Steps**: navigate to `/settings/integrations` → click "Channels" tab.
- **Expected outcome**: tab badge shows `1`; one `ChannelCard` renders with name "prod-twilio" and provider pill "TWILIO".
- **Mock API** (`POST /channel/list`, 200):
  ```json
  [
    {
      "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
      "name": "prod-twilio",
      "channel_type": "twilio",
      "created_at": "2026-06-17T10:00:00",
      "updated_at": "2026-06-17T10:00:00"
    }
  ]
  ```

**PS-2: Empty list renders empty state**

- **Preconditions**: authenticated; no channels.
- **Steps**: navigate to `/settings/integrations?tab=channels`.
- **Expected outcome**: dashed box reads "No telephony channels yet — add your first one." and the dashed "Add channel" CTA is visible.
- **Mock API** (`POST /channel/list`, 200): `[]`

**PS-3: Create channel succeeds**

- **Preconditions**: empty list (PS-2).
- **Steps**: click "Add channel" → fill Name `Twilio Production`, Auth Token `secret-token-abc`, Account SID `AC1234567890abcdef` → click Save.
- **Expected outcome**: modal closes; `fetchChannelsAtom` re-fires; new card visible; success toast "Integration created successfully" appears with default 3000 ms duration.
- **Mock API** (`POST /channel/upsert`, 201):
  ```json
  {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "Twilio Production",
    "channel_type": "twilio",
    "created_at": "2026-06-17T10:00:00",
    "updated_at": "2026-06-17T10:00:00"
  }
  ```

**PS-4: Edit channel succeeds**

- **Preconditions**: PS-1.
- **Steps**: click card → wait for hydration → change Auth Token → Save.
- **Expected outcome**: modal closes; toast "Integration updated successfully"; the Type field stays locked throughout.
- **Mock API** (`POST /channel/upsert`, 200):
  ```json
  {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "Twilio Production (renamed)",
    "channel_type": "twilio",
    "created_at": "2026-06-17T10:00:00",
    "updated_at": "2026-06-17T11:00:00"
  }
  ```

**PS-5: Edit modal hydrates with decrypted config**

- **Preconditions**: PS-1.
- **Steps**: click card.
- **Expected outcome**: `AppLoader` renders; once `GET /channel/get?include_config=true` resolves, Auth Token + Account SID fields are pre-filled.
- **Mock API** (`GET /channel/get`, 200):
  ```json
  {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "Twilio Production",
    "channel_type": "twilio",
    "config": {
      "account_sid": "AC1234567890abcdef",
      "auth_token": "twilio-auth-token-here"
    }
  }
  ```

**PS-6: Delete channel succeeds**

- **Preconditions**: PS-1.
- **Steps**: open action menu → click "Delete" → confirm.
- **Expected outcome**: card animates out; toast "Integration deleted successfully".
- **Mock API** (`DELETE /channel/delete`, 200): `{"message": "Channel deleted successfully"}`

**PS-7: Catalog "Add API key" pre-selects Twilio**

- **Preconditions**: empty list.
- **Steps**: click "Add API key" on the Twilio tile in Available Providers.
- **Expected outcome**: active tab flips to Channels; modal opens with Type field disabled showing helper text "Pre-selected from the provider tile."

---

## Failure Scenarios

**FS-1: Empty required Name**

- **Preconditions**: Create modal open.
- **Steps**: leave Name blank, fill Auth Token + Account SID, attempt Save.
- **Mock API**: not called — Zod blocks submit.
- **Expected UI behavior**: Save button stays disabled; helperText under Name reads "Name is required" (rendered by `TextInput` via RHF `fieldState.error.message`).

**FS-2: Empty Auth Token**

- Same as FS-1, with Auth Token blank.
- **Expected**: helperText reads "Auth token is required".

**FS-3: Empty Account SID**

- Same as FS-1, with Account SID blank.
- **Expected**: helperText reads "Account SID is required".

**FS-4: Backend validation 400 (missing channel_type)**

- **Preconditions**: form filled, Type somehow null.
- **Mock API** (`POST /channel/upsert`, 400): `{"detail": "channel_type is required"}`
- **Expected UI**: modal stays open; error toast title = `channel_type is required` (passed verbatim from `handleApiError`).

**FS-5: Duplicate channel name (409 conflict)**

- **Preconditions**: a channel named "Twilio Production" already exists.
- **Steps**: Create a second channel with the same name.
- **Mock API** (`POST /channel/upsert`, 409): `{"detail": "A channel with this name already exists in this organization"}`
- **Expected UI**: modal stays open; toast title = "A channel with this name already exists in this organization"; Save button re-enables.

**FS-6: Unauthorized 401 on list**

- **Preconditions**: token rejected mid-session.
- **Mock API** (`POST /channel/list`, 401): `{"detail": "Could not validate credentials"}`
- **Expected UI**: list state flips to `status: "error"`; `handleApiError` raises a toast titled "Could not validate credentials".

**FS-7: Forbidden 403 on delete (non-admin)**

- **Preconditions**: user is a member, not admin/owner.
- **Mock API** (`DELETE /channel/delete`, 403): `{"detail": "Admin or Owner role required"}`
- **Expected UI**: card stays in list; toast title = "Admin or Owner role required".

**FS-8: Channel not found 404 on delete**

- **Mock API** (`DELETE /channel/delete`, 404): `{"detail": "Channel not found"}`
- **Expected UI**: toast title = "Channel not found"; subsequent refetch removes the stale row.

**FS-9: Network failure (500) on upsert**

- **Mock API** (`POST /channel/upsert`, 500): `{"detail": "Internal Server Error"}`
- **Expected UI**: modal stays open; toast title = "Internal Server Error"; Save re-enables.

**FS-10: 422 validation error (malformed body)**

- **Mock API** (`POST /channel/upsert`, 422):
  ```json
  {
    "detail": [
      {
        "type": "model_attributes_type",
        "loc": ["body"],
        "msg": "Input should be a valid dictionary or object to extract fields from",
        "input": "not-a-json-object"
      }
    ]
  }
  ```
- **Expected UI**: `handleApiError` only stringifies `detail` when it is a string; for array `detail` it falls back to "Something went wrong. Please try again." ⚠ unverified — confirm fallback text appears in toast.

**FS-11: Delete a channel that still has phone numbers (500 IntegrityError)**

- **Mock API** (`DELETE /channel/delete`, 500): `{"detail": "Internal Server Error"}`
- **Expected UI**: card remains; toast title = "Internal Server Error". (Per Postman: backend doesn't yet catch `IntegrityError` — should be 409.)

**FS-12: Edit hydration fails**

- **Preconditions**: click an existing card.
- **Mock API** (`GET /channel/get`, 404): `{"detail": "Channel not found"}`
- **Expected UI**: `handleApiError` shows toast "Channel not found"; form falls back to defaults (`{ name: editChannel.name, auth_token: '', account_sid: '' }`); modal stays open.

**FS-13: Auth gating redirect**

- **Preconditions**: no `tone_access_token` cookie.
- **Steps**: visit `/settings/integrations`.
- **Expected UI**: 307 redirect to `/auth/login?redirect=%2Fsettings%2Fintegrations`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` (`src/utils/toast.tsx`). Sonner renders title and (optional) description as separate elements inside `[data-sonner-toast]`. `handleApiError` (in `src/utils/helpers.ts`) passes the backend `response.data.detail` string as the toast **title** (no description); when `detail` is not a string, it uses the title "Something went wrong. Please try again."

| Trigger                                              | Toast title                                                   | Toast description | Variant  |
| ---------------------------------------------------- | ------------------------------------------------------------- | ----------------- | -------- |
| Channel create succeeds                              | `Integration created successfully`                            | —                 | success  |
| Channel update succeeds                              | `Integration updated successfully`                            | —                 | success  |
| Channel delete succeeds                              | `Integration deleted successfully`                            | —                 | success  |
| Upsert backend 409 duplicate                         | `A channel with this name already exists in this organization`| —                 | error    |
| Upsert backend 400 (missing field)                   | `channel_type is required` / `name is required`               | —                 | error    |
| Delete backend 404                                   | `Channel not found`                                           | —                 | error    |
| Delete backend 403                                   | `Admin or Owner role required`                                | —                 | error    |
| Any 5xx with `detail` string                         | `Internal Server Error` (verbatim)                            | —                 | error    |
| Any error where `detail` is not a string             | `Something went wrong. Please try again.`                     | —                 | error    |

---

## UI Elements

| Element              | Type            | Content / Label                                  | Behavior                                                  |
| -------------------- | --------------- | ------------------------------------------------ | --------------------------------------------------------- |
| Channels tab         | Tab             | "Channels" + Phone icon + count badge            | Switches the right pane to `ChannelGrid`                  |
| Add channel card     | Card (dashed)   | "Add channel" + Plus icon                        | Opens `ChannelFormModal` in create mode                   |
| Channel card         | Card            | Name (semibold) + provider type pill + timestamp | Click opens edit modal; action menu for Edit/Delete       |
| Provider type pill   | Badge           | "TWILIO" uppercase                               | Static                                                    |
| Action menu          | Icon button     | ⋮                                                | Opens menu with Edit + Delete items                       |
| Channel grid skeleton| Skeleton        | 2 placeholder cards                              | Renders while `fetchChannelsAtom` is loading              |
| Empty state          | Dashed box      | "No telephony channels yet — add your first one."| Shown when `channels.items.length === 0` and not loading  |
| Name input           | TextInput       | placeholder: "e.g. Twilio Production"            | Required, Zod-validated                                   |
| Type input           | SelectInput     | default "twilio"                                 | Locked on edit / when pre-selected from catalog           |
| Auth Token input     | TextInput (pwd) | placeholder: "Enter auth token"                  | Required                                                  |
| Account SID input    | TextInput       | placeholder: "Enter account SID"                 | Required                                                  |
| Save button          | Button          | "Save" → "Saving…"                               | Disabled while submitting                                 |
| Cancel button        | Button          | "Cancel"                                         | Closes modal without saving                               |

---

## Navigation

| Trigger                          | Destination                                            | Condition                              |
| -------------------------------- | ------------------------------------------------------ | -------------------------------------- |
| Visit `/integrations`            | `/settings/integrations`                               | Redirect                               |
| Click Channels tab               | `/settings/integrations?tab=channels`                  | Always                                 |
| Click "Add channel"              | `ChannelFormModal` opens                               | Always                                 |
| Click channel card               | `ChannelFormModal` opens in edit mode                  | Card click is allowed                  |
| Click Edit in action menu        | `ChannelFormModal` opens in edit mode                  | Always                                 |
| Click Delete in action menu      | Confirm dialog → `DELETE /channel/delete`              | Always                                 |
| Catalog "Connect" on Twilio tile | `ChannelFormModal` opens with Type pre-selected/locked | Provider is configured in the catalog  |
| No auth cookie                   | `/auth/login?redirect=%2Fsettings%2Fintegrations`      | `src/middleware.ts` redirect           |

---

## API Contracts

Real payloads sourced from `/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json` (folder: `Channels`). Note the **frontend actually returns a bare `Channel[]` array** from `/channel/list` (see `src/services/channelService.ts:listChannels`) — not a `{ items, total }` envelope.

| Endpoint                                              | Method | Request                                                                          | Success Response                                  | Error Response                        |
| ----------------------------------------------------- | ------ | -------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------- |
| `/channel/list`                                       | POST   | `{ "channel_type": "twilio"\|null }`                                             | `Channel[]`                                       | `{ "detail": "..." }`                 |
| `/channel/get?channel_id=<id>&include_config=<bool>`  | GET    | —                                                                                | `Channel` (with `config` when `include_config=true`) | `{ "detail": "Channel not found" }` (404) |
| `/channel/upsert`                                     | POST   | `{ id?, name, channel_type, config: { auth_token, account_sid } }`               | `Channel` (201 create, 200 update)                | `{ "detail": "..." }`                 |
| `/channel/delete?channel_id=<id>`                     | DELETE | —                                                                                | `{ "message": "Channel deleted successfully" }`   | `{ "detail": "..." }`                 |
| `/channel/phone_numbers?channel_id=<id>`              | GET    | —                                                                                | `ChannelPhoneNumber[]`                            | `{ "detail": "..." }`                 |

### Example: `POST /channel/upsert` (create)

Request body:

```json
{
  "name": "Twilio Production",
  "channel_type": "twilio",
  "config": {
    "account_sid": "AC1234567890abcdef",
    "auth_token": "secret-token-abc"
  }
}
```

201 Created response body:

```json
{
  "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
  "name": "Twilio Production",
  "channel_type": "twilio",
  "created_at": "2026-06-17T10:00:00",
  "updated_at": "2026-06-17T10:00:00"
}
```

409 Conflict response body:

```json
{ "detail": "A channel with this name already exists in this organization" }
```

422 Validation Error response body:

```json
{
  "detail": [
    {
      "type": "model_attributes_type",
      "loc": ["body"],
      "msg": "Input should be a valid dictionary or object to extract fields from",
      "input": "not-a-json-object"
    }
  ]
}
```

### Example: `POST /channel/list`

Request body:

```json
{ "channel_type": null }
```

200 OK response body:

```json
[
  {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "prod-twilio",
    "channel_type": "twilio",
    "created_at": "2026-06-17T10:00:00"
  }
]
```

200 OK (empty):

```json
[]
```

### Example: `GET /channel/get?channel_id=...&include_config=true`

200 OK:

```json
{
  "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
  "name": "Twilio Production",
  "channel_type": "twilio",
  "config": {
    "account_sid": "AC1234567890abcdef",
    "auth_token": "twilio-auth-token-here"
  }
}
```

404 Not Found: `{ "detail": "Channel not found" }`

### Example: `DELETE /channel/delete?channel_id=...`

200 OK: `{ "message": "Channel deleted successfully" }`

403 Forbidden: `{ "detail": "Admin or Owner role required" }`

500 (IntegrityError — attached phone numbers): `{ "detail": "Internal Server Error" }`

State is held in `src/atoms/IntegrationAtom.tsx`:

- `channelsAtom` (read), `fetchChannelsAtom`, `upsertChannelAtom`, `deleteChannelAtom`, `resetChannelsAtom`

---

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] Slow `/channel/list` → skeleton renders until response
- [ ] Empty org → dashed empty state + visible "Add channel" affordance
- [ ] Edit modal opens before `GET /channel/get` returns → spinner; fields hydrate when ready
- [ ] Submit while a previous submit is in flight → button disabled, double-submit prevented
- [ ] Zod validation: empty name / token / SID block submit and surface inline errors
- [ ] Network/API error on upsert → modal stays open, error toast shown
- [ ] Delete a channel that still has phone numbers attached → backend error toast
- [ ] Reset atom on page unmount (`resetChannelsAtom`) — switching to a sibling tab and back should refetch cleanly
- [ ] Catalog pre-select: closing the modal should not leave the locked-Type state stuck for the next plain "Add channel" click
- [ ] Token expires mid-action (Save click): backend returns 401 with `{"detail":"Invalid token"}` → toast title = "Invalid token"; user is not auto-redirected (axios interceptor does not log out on 401 today) ⚠ unverified, confirm interceptor behavior
- [ ] Double submission: user double-clicks Save → `saving` flag flips true on first click and `disabled` blocks the second; only one `POST /channel/upsert` fires
- [ ] Delete confirm + immediate refresh button click: `fetchChannelsAtom` early-returns when `status === 'loading'`, so concurrent refreshes don't race
- [ ] Hydration race: closing the edit modal before `GET /channel/get` resolves → response is discarded (modal already unmounted), no stale state written
- [ ] Catalog tile with `configured: false`: the "Add API key" button still renders for API-key (channel) providers (they don't gate on `configured`); only OAuth tiles disable when not configured

---

## Business Rules

- Today only one provider type is exposed in the UI: `twilio`. The select is functional but single-option.
- `encrypted_config` is AES-encrypted server-side (`core/utils/encryption.py`); the frontend only ever sees the plaintext values it submits.
- Channel ownership is per-organization; the `tenant_id` header (from the `org_tenant_id` cookie, injected by `src/utils/axios.ts`) scopes every request.
- A channel can carry many phone numbers; phone-number routing is owned by the agent CRUD flow, not the Channels tab.
- Provider type is immutable after creation (Type field locked in edit mode).

---

## Accessibility Requirements

- [ ] Tab navigation reaches every actionable element (Add card, channel cards, action menu, modal inputs, Save, Cancel)
- [ ] Action menu trigger has an accessible name (e.g. `aria-label="Channel actions"`)
- [ ] Modal traps focus and restores it on close (Radix/shadcn default)
- [ ] Inputs use shared `TextInput`/`SelectInput` with associated labels
- [ ] Error messages render as `helperText` under inputs and are not duplicated by parent rows
- [ ] Buttons in the loading state announce a meaningful label ("Saving…") instead of only visual spinners

---

## Appended Scenarios (gap-fill, ID prefix `CN-`)

These rows extend the PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `channels.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-001 | Visit `/settings/integrations` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fsettings%2Fintegrations` | `unauthenticated visit redirects to login` |
| CN-002 | Visit `/settings/integrations` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Fsettings%2Fintegrations`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| CN-003 | Member role attempts to open the Channels tab | Tab renders read-only; Add channel / Edit / Delete actions disabled OR backend 403 on save | `member role sees channels list but cannot mutate` |
| CN-004 | Visit `/integrations` (legacy) when authenticated | Server-side redirect to `/settings/integrations` | `legacy integrations path redirects to settings integrations` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-005 | `POST /channel/list` returns 400 (malformed `channel_type`) | Empty grid state; toast surfaces backend `detail`; no crash | `list 400 surfaces detail toast and renders empty grid` |
| CN-006 | Token expires between modal open and Save → 401 on upsert | Toast `Invalid token` / `Could not validate credentials`; modal stays open; form intact | `upsert 401 surfaces error toast without redirect` |
| CN-007 | Member role attempts delete → 403 | Toast `Admin or Owner role required`; card remains | `delete 403 surfaces forbidden toast` |
| CN-008 | Delete a channel that was already removed → 404 | Toast `Channel not found`; subsequent refetch removes the stale card | `delete 404 surfaces not-found toast` |
| CN-009 | Upsert duplicate name → 409 | Toast `A channel with this name already exists in this organization`; modal stays open; Save re-enables | `upsert 409 surfaces duplicate-name toast` |
| CN-010 | Upsert 500 server error | Toast `Internal Server Error`; modal stays open; Save re-enables | `upsert 500 surfaces server error toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-011 | Offline / network failure during Save | Modal stays open with form values preserved; toast `Something went wrong. Please try again.`; Save re-enables | `save network failure preserves form data` |
| CN-012 | Slow `POST /channel/upsert` (>3s) | Save button shows "Saving…" + `disabled` the whole time; Cancel still works to discard | `slow save disables button and shows saving label` |
| CN-013 | Slow `GET /channel/get` on edit modal hydrate (>3s) | `AppLoader` visible; Type field locked; Save button disabled until hydration completes | `slow edit hydration keeps loader and disabled save` |
| CN-014 | Concurrent edit — second user updates the same channel mid-form | Save succeeds last-write-wins OR backend returns 409; toast reflects backend response | `concurrent edit handled by last-write or 409` |
| CN-015 | Double-click Save during a pending request | Only one `POST /channel/upsert` fires; second click ignored while `saving === true` | `double-click on save does not double-submit` |

### Input edge cases (ChannelFormModal)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-016 | Whitespace-only Name | Zod blocks submit; helperText `Name is required`; no network call | `whitespace-only name is rejected by validation` |
| CN-017 | Whitespace-only Auth Token | Zod blocks submit; helperText `Auth token is required` | `whitespace-only auth token is rejected by validation` |
| CN-018 | Whitespace-only Account SID | Zod blocks submit; helperText `Account SID is required` | `whitespace-only account sid is rejected by validation` |
| CN-019 | Name with leading/trailing whitespace (` Twilio Production `) | Trimmed before submit; payload contains `Twilio Production` | `name trims surrounding whitespace before submit` |
| CN-020 | Name with special chars + emoji + unicode (`Twilio 🚀 <script>`) | Accepted; round-trips through API; no XSS execution in the card/badge | `name accepts unicode and html-ish characters without xss` |
| CN-021 | Name > 500 characters | Either accepted or backend 400/422; modal stays open; toast surfaces detail | `very long name handled with backend validation` |
| CN-022 | Auth Token visually masked (input type=password) | Input value not visible in DOM as plain text; toggle-reveal absent (single-mask design) | `auth token input is masked` |
| CN-023 | Account SID with leading/trailing whitespace | Trimmed before submit | `account sid trims surrounding whitespace before submit` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-024 | Empty list — no channels | Dashed empty-state box + "Add channel" CTA visible | `empty list renders the dashed empty state` |
| CN-025 | Loading state | `ChannelGridSkeleton` shows 2 animate-pulse cards while in-flight | `loading state renders the skeleton grid` |
| CN-026 | Channel grid count badge | Tab badge equals `items.length` | `tab badge reflects channel count` |
| CN-027 | Refresh header button | Triggers both `fetchOAuthAtom` + `fetchChannelsAtom`; button shows `Loading…` while in flight | `refresh button re-fetches both lists` |
| CN-028 | Action menu — Edit | Opens the form modal in edit mode with Type field locked | `action menu edit opens form in edit mode` |
| CN-029 | Action menu — Delete confirmation | Confirm dialog renders; cancel keeps the card | `delete confirmation cancel preserves the card` |
| CN-030 | Sort or filter — N/A | Channels grid does not currently expose sort/filter; assertion: no sort headers visible | `channel grid does not currently expose sort or filter` |

### Channel-specific

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-031 | Pre-select Twilio from the catalog tile | `setActiveTab('channels')` flips; modal opens with Type locked + helper text `Pre-selected from the provider tile.` | `catalog Add API key pre-selects twilio and locks type` |
| CN-032 | Type field is read-only in edit mode | Type select disabled with helper text "Type cannot be changed after the channel is created." | `type field is locked in edit mode` |
| CN-033 | Closing modal after catalog pre-select | Re-opening plain "Add channel" shows Type as editable again (no stuck locked state) | `closing modal after catalog pre-select resets type lock` |
| CN-034 | Delete a channel that still has phone numbers attached | Backend 500 (IntegrityError); toast `Internal Server Error`; card remains; phone-number bindings untouched | `delete with attached phone numbers surfaces backend error` |
| CN-035 | Edit channel updates only credentials, not channel_type | Submitting an edit sends `channel_type: 'twilio'` (unchanged); backend does not allow type switch | `edit submit preserves immutable channel_type` |
| CN-036 | Add channel — supported provider list | Type select currently exposes only `twilio`; no other providers selectable | `type select exposes only twilio today` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-037 | Tab order through the form | Name → Type → Auth Token → Account SID → Cancel → Save | `tab order through channel form reaches every field` |
| CN-038 | Submit via Enter key in the last field | Triggers Save (same as button click) | `Enter on Account SID submits the form` |
| CN-039 | Modal traps focus and restores it on close | Focus moves inside modal; Esc closes; focus returns to Add channel / Edit trigger | `channel modal traps focus and restores on close` |
| CN-040 | Action menu trigger has accessible name (`aria-label="Channel actions"`) | Screen readers can announce the menu trigger | `action menu trigger exposes accessible name` |
| CN-041 | Error helperText announced by screen readers | Inline errors render with `role="alert"` or aria-live | `inline errors are announced via aria-live` |
| CN-042 | Saving button announces label change | "Save" → "Saving…" + `aria-disabled="true"` while in-flight | `save button announces saving state` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-043 | Click Channels tab from sibling tab | Active tab flips; URL stays at `/settings/integrations`; ChannelGrid mounts | `clicking channels tab flips active state` |
| CN-044 | Browser back after opening edit modal | Modal closes; URL unchanged; list state preserved | `browser back closes the modal without leaving the page` |
| CN-045 | Reload `/settings/integrations` | Page reloads with the Channels tab active when URL has `?tab=channels` | `reload preserves the active tab via query param` |

### Full lifecycle (`CN-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| CN-FULL | Authenticate via `loginViaUI` → visit `/settings/integrations?tab=channels` → assert empty state OR list → click "Add channel" → fill Name `__e2e__ Twilio Production`, Auth Token `__e2e__ token`, Account SID `__e2e__ AC123` → click Save → assert toast `Integration created successfully` and card visible → click card → assert edit modal hydrates with Auth Token + Account SID + Type locked → change Auth Token → Save → assert toast `Integration updated successfully` → open action menu → Delete → confirm → assert toast `Integration deleted successfully` and card removed → cleanup any residual data via API in the same `try/finally` block | All CRUD endpoints fire with the expected payloads; type field locked throughout edit; cleanup runs in the same test body even if assertions fail | `walks create configure edit delete of a twilio channel end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| CN-001..004 | FS-13 (auth gating) | Adds expired-token + member + legacy-redirect cases |
| CN-005..010 | FS-4..FS-11 | Standardises 400/401/403/404/409/500 paths |
| CN-011..015 | (new) | Network resilience + concurrent + double-submit |
| CN-016..023 | FS-1..FS-3 | Adds whitespace + special-char + length input edge cases |
| CN-024..030 | PS-2, US-1 | Promotes empty/loading/badge/menu/no-sort scenarios |
| CN-031..036 | PS-7, US-3 | Promotes channel-specific catalog/edit/type lock to scenarios |
| CN-037..042 | Accessibility section | Promotes a11y bullets to scenarios |
| CN-043..045 | Navigation table | Adds reload + browser back + tab switching |
| CN-FULL | (new) | Single-test sweep of create → edit → delete |
