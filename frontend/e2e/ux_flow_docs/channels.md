# Feature Doc: Channels (Telephony Integrations)

Feature documentation for the Channels tab on the Integrations page. Used by
`/generate-tests channels` (or `--docs e2e/ux_flow_docs/channels.md`) to ensure all user
cases are covered alongside the component source analysis.

A **Channel** is a per-organization integration with a telephony / transport
provider (Twilio today; Telnyx, Exotel, Plivo, Daily, WebSocket on the backend
roadmap). It stores encrypted provider credentials and carries the phone
numbers routable to agents.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

**As an** org admin, **I want to** see all telephony channels configured for my org on the Channels tab, **so that** I know which provider accounts the org can receive calls on.

**Acceptance criteria**:

- [ ] Channels tab shows the heading "Channels" with a Phone icon
- [ ] Tab label shows a count badge equal to the number of configured channels
- [ ] Each channel renders as a card with name, provider type badge (e.g. "TWILIO"), and "Updated X time ago"
- [ ] Loading state renders `ChannelGridSkeleton` with 2 placeholder cards (animate-pulse)
- [ ] Empty state shows a dashed border box with "No telephony channels yet — add your first one."

### US-2: Add a new channel

**As an** org admin, **I want to** add a Twilio account by entering credentials in a modal, **so that** my org can start receiving calls on Twilio numbers.

**Acceptance criteria**:

- [ ] Click "Add channel" (dashed card with Plus icon) → `ChannelFormModal` opens
- [ ] Modal has 4 fields: Name, Type (default "twilio"), Auth Token (password), Account SID
- [ ] All fields are required and validated client-side with a Zod schema
- [ ] "Save" button shows "Saving…" + `disabled` while the request is in flight
- [ ] On success: modal closes, list refetches, success toast "Integration created successfully"
- [ ] On error: toast shown via `handleApiError`, modal remains open

### US-3: Edit an existing channel

**As an** org admin, **I want to** rotate Twilio credentials on an existing channel, **so that** I can update tokens without recreating the channel.

**Acceptance criteria**:

- [ ] Click a channel card or "Edit" in the action menu (3-dot icon) → modal opens with fields pre-filled from `GET /channel/get`
- [ ] An `AppLoader` spinner shows while the modal hydrates
- [ ] The Type field is locked (read-only) in edit mode
- [ ] Submitting calls `POST /channel/upsert` with the existing channel id
- [ ] Phone numbers attached to the channel are unaffected by credential updates

### US-4: Delete a channel

**As an** org admin, **I want to** remove a channel I no longer use, **so that** no agents accidentally route calls through a stale provider account.

**Acceptance criteria**:

- [ ] Action menu (3-dot icon) on each card shows a "Delete" item
- [ ] Confirming delete calls `DELETE /channel/delete` with the channel id
- [ ] Card is removed from the grid on success
- [ ] Channels with phone numbers still attached: backend response surfaces an error, frontend shows it via `handleApiError`

### US-5: Pre-select provider from the catalog

**As an** org admin, **I want to** click "Connect" on a Twilio tile in the Available Providers catalog, **so that** the channel form opens with Twilio pre-selected.

**Acceptance criteria**:

- [ ] Catalog tile "Connect" triggers `openAdd()` on the `ChannelGrid` ref
- [ ] Modal opens with the Type field locked to the chosen provider
- [ ] The rest of the create flow (US-2) applies

---

## Input Specifications

### ChannelFormModal — create + edit

Source: `src/components/integrations/channel-form-modal.tsx` (Zod `channelFormSchema`, lines 17-21).

| Field          | Type            | Required | Validation Rules                                            | Exact Error Message     |
| -------------- | --------------- | -------- | ----------------------------------------------------------- | ----------------------- |
| Name           | text            | yes      | `z.string().min(1)`; trimmed before submit                  | "Name is required"      |
| Type           | select          | yes      | Locked to "twilio" today; disabled in edit / pre-selected   | n/a (locked)            |
| Auth Token     | password        | yes      | `z.string().min(1)`; trimmed before submit                  | "Auth token is required"|
| Account SID    | text            | yes      | `z.string().min(1)`; trimmed before submit                  | "Account SID is required" |

**Button state rules:**

- Save is **disabled** while any of: `!formState.isValid`, `hydrating === true`, or `saving === true`.
- Save text flips to "Saving..." while `saving === true`.

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

Real payloads sourced from `/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json` (folder: `Channels`). The frontend actually returns a bare `Channel[]` array from `/channel/list` (see `src/services/channelService.ts:listChannels`) — not a `{ items, total }` envelope.

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

State is held in `src/atoms/IntegrationAtom.tsx`:

- `channelsAtom` (read), `fetchChannelsAtom`, `upsertChannelAtom`, `deleteChannelAtom`, `resetChannelsAtom`

---

## Test Cases

> Every test case is **one Action + multiple Observations**. ID prefix legend:
> `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation), `TC-ERROR-` (server
> errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled), `TC-EDGE-`
> (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: View the channels list

**Preconditions**:
- Authenticated session (`tone_access_token` cookie set).

**Action**:
1. Visit `/settings/integrations`
2. Click the "Channels" tab

**Observation 1 — Page chrome**:
1. Header "Integrations" + subtitle render
2. Catalog section appears above the tabs

**Observation 2 — Channels tab activates**:
1. `TabsContent value="channels"` becomes active
2. `ChannelGrid` polls `POST /channel/list`

**Observation 3 — Loading skeleton**:
1. While in flight, `ChannelGridSkeleton` renders 2 animate-pulse cards

**Observation 4 — Cards render**:
1. Each channel card shows Name, "TWILIO" provider pill, and "Updated X ago"
2. The Channels tab badge equals `items.length`

---

### TC-HAPPY-002: List loads with one Twilio channel (PS-1)

**Preconditions**:
- Authenticated; user has 1 channel.

**Action**:
1. Navigate to `/settings/integrations`
2. Click the "Channels" tab

**Observation 1 — Badge count**:
1. The Channels tab badge shows `1`

**Observation 2 — Card render**:
1. One `ChannelCard` renders with name "prod-twilio" and provider pill "TWILIO"

**API mock**: `POST /channel/list` → 200 with `[{ id: "f4d22a...", name: "prod-twilio", channel_type: "twilio", ... }]`.

---

### TC-HAPPY-003: Empty list renders dashed empty state (PS-2)

**Preconditions**:
- Authenticated; no channels.

**Action**:
1. Navigate to `/settings/integrations?tab=channels`

**Observation 1 — Empty state**:
1. A dashed box reads "No telephony channels yet — add your first one."

**Observation 2 — Add channel CTA**:
1. The dashed "Add channel" CTA is visible

**API mock**: `POST /channel/list` → 200 `[]`.

---

### TC-HAPPY-004: Add a new channel via the dashed CTA

**Preconditions**:
- Authenticated session.

**Action**:
1. Click the dashed "Add channel" CTA
2. Fill Name `Twilio Production`, Auth Token `secret-token-abc`, Account SID `AC1234567890abcdef`
3. Click Save

**Observation 1 — Modal opens**:
1. `ChannelFormModal` opens with title "Add channel"
2. Fields render: Name, Type (default "twilio"), Auth Token (password), Account SID

**Observation 2 — Save fires**:
1. The Save button shows "Saving..." and `disabled=true`
2. Exactly one `POST /channel/upsert` is recorded

**Observation 3 — Success closure**:
1. Modal closes
2. `fetchChannelsAtom` re-runs (`POST /channel/list` is re-recorded)
3. Success toast title equals `Integration created successfully`
4. New card animates in via framer-motion

**API mock**: `POST /channel/upsert` → 201.

---

### TC-HAPPY-005: Edit modal hydrates with decrypted config (PS-5)

**Preconditions**:
- One channel exists (PS-1).

**Action**:
1. Click the channel card

**Observation 1 — Hydration spinner**:
1. `AppLoader` (`min-h-[260px]`) renders while `GET /channel/get?include_config=true` is in flight

**Observation 2 — Fields populate**:
1. After 200, Auth Token and Account SID are pre-filled
2. Type field is disabled with helper text "Type cannot be changed after the channel is created."

**API mock**: `GET /channel/get` → 200 with `config.account_sid` + `config.auth_token`.

---

### TC-HAPPY-006: Edit a channel succeeds (PS-4)

**Preconditions**:
- One channel exists.

**Action**:
1. Click the channel card
2. Wait for hydration
3. Change Auth Token to a new value
4. Click Save

**Observation 1 — Upsert with id**:
1. Exactly one `POST /channel/upsert` is recorded with the existing channel `id` in the body

**Observation 2 — Success toast**:
1. Toast title equals `Integration updated successfully`

**Observation 3 — Type stays locked**:
1. Type field remains disabled throughout the entire edit flow

**API mock**: `POST /channel/upsert` → 200.

---

### TC-HAPPY-007: Delete a channel succeeds (PS-6)

**Preconditions**:
- One channel exists.

**Action**:
1. Open the 3-dot action menu on the card
2. Click "Delete"
3. Confirm

**Observation 1 — Delete fires**:
1. Exactly one `DELETE /channel/delete?channel_id=<id>` is recorded

**Observation 2 — Card removed + toast**:
1. The card animates out (framer-motion exit)
2. `fetchChannelsAtom` re-runs
3. Toast title equals `Integration deleted successfully`

**API mock**: `DELETE /channel/delete` → 200.

---

### TC-HAPPY-008: Catalog "Add API key" pre-selects Twilio (PS-7)

**Preconditions**:
- Empty list; Twilio tile present in Available Providers.

**Action**:
1. Scroll to the "API key" section in Available Providers
2. Click "Add API key" on the Twilio tile

**Observation 1 — Tab flips**:
1. `setActiveTab('channels')` activates the Channels tab

**Observation 2 — Modal pre-select**:
1. `ChannelFormModal` opens
2. The Type field is disabled with helper text "Pre-selected from the provider tile."

---

### TC-HAPPY-009: Refresh both lists from the header button

**Action**:
1. Click the "Refresh" header button (RefreshCw icon)

**Observation 1 — Both atoms run**:
1. `fetchOAuthAtom` re-runs
2. `fetchChannelsAtom` re-runs

**Observation 2 — Loading affordance**:
1. Button shows the loading label ("Loading...") while in flight
2. `ChannelGridSkeleton` renders briefly in the grid

---

### TC-VALIDATE-001: Empty required Name blocks submit (FS-1)

**Preconditions**:
- Create modal open.

**Action**:
1. Leave Name blank, fill Auth Token + Account SID
2. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Name reads exactly `Name is required`
2. Save button stays disabled

---

### TC-VALIDATE-002: Empty Auth Token (FS-2)

**Action**:
1. Open Create modal
2. Fill Name + Account SID, leave Auth Token blank
3. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Auth Token reads `Auth token is required`

---

### TC-VALIDATE-003: Empty Account SID (FS-3)

**Action**:
1. Open Create modal
2. Fill Name + Auth Token, leave Account SID blank
3. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Account SID reads `Account SID is required`

---

### TC-VALIDATE-004: Whitespace-only Name is rejected (CN-016)

**Action**:
1. Open Create modal
2. Type `   ` into Name
3. Fill Auth Token + Account SID
4. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Name reads `Name is required`

---

### TC-VALIDATE-005: Whitespace-only Auth Token is rejected (CN-017)

**Action**:
1. Open Create modal
2. Fill Name + Account SID
3. Type `   ` into Auth Token
4. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Auth Token reads `Auth token is required`

---

### TC-VALIDATE-006: Whitespace-only Account SID is rejected (CN-018)

**Action**:
1. Open Create modal
2. Fill Name + Auth Token
3. Type `   ` into Account SID
4. Click Save

**Observation 1 — No network call**:
1. Zero `POST /channel/upsert` requests are recorded

**Observation 2 — Inline error**:
1. helperText under Account SID reads `Account SID is required`

---

### TC-ERROR-001: Backend validation 400 (missing channel_type) (FS-4)

**Preconditions**:
- Form filled; backend rejects with `channel_type is required`.

**Action**:
1. Open Create modal, fill all fields
2. Click Save

**Observation 1 — Modal persists**:
1. Modal remains open
2. Save button re-enables

**Observation 2 — Error toast**:
1. Toast title equals `channel_type is required`

**API mock**: `POST /channel/upsert` → 400 `{ detail: "channel_type is required" }`.

---

### TC-ERROR-002: Duplicate channel name (409) (FS-5 / CN-009)

**Preconditions**:
- A channel named "Twilio Production" already exists.

**Action**:
1. Open Create modal
2. Enter the same name and valid credentials
3. Click Save

**Observation 1 — Modal persists**:
1. Modal remains open
2. Save button re-enables

**Observation 2 — Error toast**:
1. Toast title equals `A channel with this name already exists in this organization`

**API mock**: `POST /channel/upsert` → 409.

---

### TC-ERROR-003: Unauthorized 401 on list (FS-6)

**Preconditions**:
- Token rejected mid-session.

**Action**:
1. Navigate to `/settings/integrations?tab=channels`

**Observation 1 — List state**:
1. The channels-list state flips to `status: "error"`

**Observation 2 — Toast**:
1. `handleApiError` raises a toast titled `Could not validate credentials`

**API mock**: `POST /channel/list` → 401.

---

### TC-ERROR-004: Forbidden 403 on delete (non-admin) (FS-7 / CN-007)

**Preconditions**:
- Authenticated as a member (non-admin/owner).

**Action**:
1. Open action menu, click Delete, confirm

**Observation 1 — Card persists**:
1. The card stays in the list

**Observation 2 — Toast**:
1. Toast title equals `Admin or Owner role required`

**API mock**: `DELETE /channel/delete` → 403.

---

### TC-ERROR-005: Channel not found 404 on delete (FS-8 / CN-008)

**Action**:
1. Open action menu, click Delete, confirm

**Observation 1 — Toast**:
1. Toast title equals `Channel not found`

**Observation 2 — Refetch clears stale row**:
1. Subsequent `POST /channel/list` removes the stale row

**API mock**: `DELETE /channel/delete` → 404.

---

### TC-ERROR-006: Server 500 on upsert (FS-9 / CN-010)

**Action**:
1. Open Create modal, fill valid fields
2. Click Save

**Observation 1 — Modal persists**:
1. Modal remains open
2. Save button re-enables

**Observation 2 — Toast**:
1. Toast title equals `Internal Server Error`

**API mock**: `POST /channel/upsert` → 500.

---

### TC-ERROR-007: 422 validation error falls back to generic toast (FS-10)

**Action**:
1. Open Create modal, fill valid fields
2. Click Save

**Observation 1 — Fallback toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is not a string)

> ⚠ unverified — confirm fallback text appears in toast.

**API mock**: `POST /channel/upsert` → 422 with array `detail`.

---

### TC-ERROR-008: Delete a channel that still has phone numbers (500 IntegrityError) (FS-11 / CN-034)

**Action**:
1. Open action menu, click Delete, confirm

**Observation 1 — Toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Card + bindings**:
1. The card remains in the grid
2. Phone-number bindings are untouched

**API mock**: `DELETE /channel/delete` → 500 (IntegrityError).

---

### TC-ERROR-009: Edit hydration fails — 404 on get (FS-12)

**Preconditions**:
- A channel card visible.

**Action**:
1. Click the channel card

**Observation 1 — Toast**:
1. Toast title equals `Channel not found`

**Observation 2 — Modal fallback**:
1. Form fields fall back to defaults (`{ name: editChannel.name, auth_token: '', account_sid: '' }`)
2. The modal stays open

**API mock**: `GET /channel/get` → 404.

---

### TC-ERROR-010: Upsert 401 mid-flow surfaces toast without redirect (CN-006)

**Preconditions**:
- Token expires between modal open and Save.

**Action**:
1. Open Create modal, fill valid fields
2. Click Save

**Observation 1 — Toast**:
1. Toast title surfaces `Invalid token` / `Could not validate credentials`

**Observation 2 — Modal persists**:
1. Modal stays open
2. Form values are intact

**API mock**: `POST /channel/upsert` → 401.

---

### TC-ERROR-011: List 400 surfaces detail toast and renders empty grid (CN-005)

**Action**:
1. Navigate to `/settings/integrations?tab=channels`

**Observation 1 — Empty grid state**:
1. The grid is empty (no crash)

**Observation 2 — Toast surfaces detail**:
1. Toast surfaces the backend `detail` for the malformed `channel_type`

**API mock**: `POST /channel/list` → 400.

---

### TC-LOADING-001: Slow save disables button and shows saving label (CN-012)

**Action**:
1. Open Create modal, fill valid fields
2. Click Save against a ≥3s slow backend

**Observation 1 — Loading state**:
1. Save button text becomes `Saving…`
2. Save button has `disabled` throughout

**Observation 2 — Cancel still works**:
1. Cancel discards the form and closes the modal

**API mock**: `POST /channel/upsert` → 200 delayed 3500 ms.

---

### TC-LOADING-002: Slow edit hydration keeps loader and disabled save (CN-013)

**Action**:
1. Click a channel card with a ≥3s slow `GET /channel/get`

**Observation 1 — Loader visible**:
1. `AppLoader` is visible throughout hydration

**Observation 2 — Type locked + Save disabled**:
1. Type field is locked
2. Save button is disabled until hydration completes

**API mock**: `GET /channel/get` → 200 delayed 3500 ms.

---

### TC-LOADING-003: Double-click on save does not double-submit (CN-015)

**Action**:
1. Open Create modal, fill valid fields
2. Click Save twice in rapid succession

**Observation 1 — Single request**:
1. Exactly one `POST /channel/upsert` is recorded
2. The second click is ignored while `saving === true`

---

### TC-EDGE-001: Name trims surrounding whitespace before submit (CN-019)

**Action**:
1. Open Create modal
2. Type ` Twilio Production ` into Name
3. Fill remaining fields
4. Click Save

**Observation 1 — Trimmed payload**:
1. `POST /channel/upsert` body name equals `Twilio Production` (trimmed)

---

### TC-EDGE-002: Account SID trims surrounding whitespace (CN-023)

**Action**:
1. Open Create modal
2. Type ` AC1234567890abcdef ` into Account SID
3. Fill remaining fields
4. Click Save

**Observation 1 — Trimmed payload**:
1. `POST /channel/upsert` body `config.account_sid` equals `AC1234567890abcdef`

---

### TC-EDGE-003: Name accepts unicode and html-ish characters without XSS (CN-020)

**Action**:
1. Open Create modal
2. Enter `Twilio 🚀 <script>` into Name and valid credentials
3. Click Save

**Observation 1 — Round-trip**:
1. The new card displays the unicode + html-ish text as visible text

**Observation 2 — No XSS**:
1. `window.alert` is not invoked
2. No script tag is parsed into the DOM

---

### TC-EDGE-004: Very long name handled with backend validation (CN-021)

**Action**:
1. Open Create modal
2. Enter a >500-char name
3. Fill remaining fields
4. Click Save

**Observation 1 — Backend handling**:
1. Either the request succeeds OR backend returns 400/422 with toast detail
2. Modal stays open in error branch

---

### TC-EDGE-005: Auth Token input is masked (CN-022)

**Action**:
1. Open Create modal
2. Type a value into Auth Token

**Observation 1 — Masking**:
1. Input type is `password`
2. The plaintext value is not visible as text in the DOM
3. No toggle-reveal control is present (single-mask design)

---

### TC-EDGE-006: Edit submit preserves immutable channel_type (CN-035)

**Action**:
1. Click an existing card to edit
2. Modify Auth Token, click Save

**Observation 1 — Type unchanged**:
1. `POST /channel/upsert` body contains `channel_type: 'twilio'` (unchanged)

---

### TC-EDGE-007: Type select exposes only twilio today (CN-036)

**Action**:
1. Open Create modal
2. Open the Type select

**Observation 1 — Options**:
1. Only `twilio` is selectable
2. No other provider option appears

---

### TC-EDGE-008: Closing modal after catalog pre-select resets type lock (CN-033)

**Action**:
1. Click "Add API key" on Twilio in the catalog (pre-selects + locks)
2. Close the modal
3. Click the dashed "Add channel" CTA

**Observation 1 — Type editable again**:
1. The Type field is editable / enabled (no stuck locked state)

---

### TC-EDGE-009: Type field is locked in edit mode (CN-032)

**Action**:
1. Click an existing card to edit

**Observation 1 — Locked**:
1. Type select is disabled
2. Helper text "Type cannot be changed after the channel is created." is visible

---

### TC-EDGE-010: Save network failure preserves form data (CN-011)

**Action**:
1. Open Create modal, fill valid fields
2. Click Save with the network aborted (`route.abort('failed')`)

**Observation 1 — Toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Modal persists**:
1. Modal stays open with form values preserved
2. Save button re-enables

---

### TC-EDGE-011: Concurrent edit handled by last-write or 409 (CN-014)

**Preconditions**:
- A second user is editing the same channel.

**Action**:
1. User A and User B both edit the same channel; B saves first, then A saves

**Observation 1 — Outcome**:
1. A's save either succeeds (last-write-wins) OR backend returns 409
2. Toast reflects the backend response

---

### TC-EDGE-012: Loading state renders the skeleton grid (CN-025)

**Action**:
1. Visit `/settings/integrations?tab=channels` with a slow `POST /channel/list`

**Observation 1 — Skeleton**:
1. `ChannelGridSkeleton` renders 2 animate-pulse cards while in flight

---

### TC-EDGE-013: Tab badge reflects channel count (CN-026)

**Preconditions**:
- N channels exist.

**Action**:
1. Navigate to `/settings/integrations?tab=channels`

**Observation 1 — Badge count**:
1. The Channels tab badge equals `items.length`

---

### TC-EDGE-014: Refresh button re-fetches both lists (CN-027)

**Action**:
1. Click the "Refresh" header button

**Observation 1 — Both fetches fire**:
1. `fetchOAuthAtom` runs
2. `fetchChannelsAtom` runs

**Observation 2 — Loading affordance**:
1. The refresh button shows `Loading…` while in flight

---

### TC-EDGE-015: Action menu Edit opens form in edit mode (CN-028)

**Action**:
1. Click the 3-dot action menu on a card
2. Click "Edit"

**Observation 1 — Modal opens in edit mode**:
1. `ChannelFormModal` opens with title "Edit channel"
2. Type field is locked

---

### TC-EDGE-016: Delete confirmation cancel preserves the card (CN-029)

**Action**:
1. Open action menu, click Delete
2. Cancel the confirmation dialog

**Observation 1 — Card persists**:
1. The card remains in the grid
2. No `DELETE /channel/delete` is recorded

---

### TC-EDGE-017: Channel grid does not currently expose sort or filter (CN-030)

**Action**:
1. Inspect the channels grid header

**Observation 1 — No sort/filter controls**:
1. No sort headers or filter controls are visible

---

### TC-NAV-001: Unauthenticated visit redirects to login (CN-001 / FS-13)

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/settings/integrations`

**Observation 1 — Redirect**:
1. Middleware 307 redirects to `/auth/login?redirect=%2Fsettings%2Fintegrations`

---

### TC-NAV-002: Expired token redirects to login and clears cookie (CN-002)

**Preconditions**:
- Expired `tone_access_token` cookie present.

**Action**:
1. Visit `/settings/integrations`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fintegrations`

**Observation 2 — Cookie cleared**:
1. The expired cookie is removed by middleware

---

### TC-NAV-003: Member role sees channels list but cannot mutate (CN-003)

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Visit `/settings/integrations?tab=channels`

**Observation 1 — Read-only view**:
1. Tab renders with cards visible read-only
2. Add channel / Edit / Delete actions are disabled OR backend returns 403 on save

---

### TC-NAV-004: Legacy /integrations path redirects (CN-004)

**Action**:
1. Visit `/integrations`

**Observation 1 — Server-side redirect**:
1. URL becomes `/settings/integrations`

---

### TC-NAV-005: Catalog Add API key pre-selects twilio and locks type (CN-031 / PS-7)

**Action**:
1. Click "Add API key" on the Twilio catalog tile

**Observation 1 — Tab flips + modal**:
1. `setActiveTab('channels')` flips
2. Modal opens with Type locked + helper text `Pre-selected from the provider tile.`

---

### TC-NAV-006: Clicking channels tab flips active state (CN-043)

**Action**:
1. From a sibling tab, click the Channels tab

**Observation 1 — Active state + URL**:
1. Active tab flips
2. URL stays at `/settings/integrations` (or includes `?tab=channels`)
3. `ChannelGrid` mounts

---

### TC-NAV-007: Browser back closes the modal without leaving the page (CN-044)

**Action**:
1. Click a card to open the edit modal
2. Press browser Back

**Observation 1 — Modal closes**:
1. Modal is no longer in the DOM
2. URL is unchanged
3. List state is preserved

---

### TC-NAV-008: Reload preserves the active tab via query param (CN-045)

**Action**:
1. Visit `/settings/integrations?tab=channels`
2. Reload the page

**Observation 1 — Tab persists**:
1. After reload, the Channels tab is active

---

### TC-A11Y-001: Tab order through channel form reaches every field (CN-037)

**Action**:
1. Open the Add channel modal
2. Tab through the form

**Observation 1 — Tab order**:
1. Focus moves Name → Type → Auth Token → Account SID → Cancel → Save

---

### TC-A11Y-002: Enter on Account SID submits the form (CN-038)

**Action**:
1. Open Add channel, fill valid fields
2. Focus Account SID, press Enter

**Observation 1 — Submit**:
1. Exactly one `POST /channel/upsert` request fires

---

### TC-A11Y-003: Channel modal traps focus and restores on close (CN-039)

**Action**:
1. Open Add channel modal
2. Tab repeatedly
3. Press Escape

**Observation 1 — Focus trap**:
1. Focus stays inside the modal

**Observation 2 — Restore on close**:
1. Escape closes the modal
2. Focus returns to the Add channel / Edit trigger

---

### TC-A11Y-004: Action menu trigger exposes accessible name (CN-040)

**Action**:
1. Inspect a card's action menu trigger

**Observation 1 — ARIA**:
1. The trigger has `aria-label="Channel actions"` (or equivalent accessible name)

---

### TC-A11Y-005: Inline errors are announced via aria-live (CN-041)

**Action**:
1. Trigger a required-field error (blur empty field, click Save)

**Observation 1 — ARIA**:
1. The inline error element has `role="alert"` or `aria-live`

---

### TC-A11Y-006: Save button announces saving state (CN-042)

**Action**:
1. Open Add channel, fill valid fields
2. Click Save

**Observation 1 — Accessible name change**:
1. Button accessible name changes from `Save` to `Saving…`
2. `aria-disabled="true"` (or `disabled`) is set while in flight

---

### TC-FULL-001: Walk create configure edit delete of a Twilio channel end to end (CN-FULL)

**Preconditions**:
- Authenticated via `loginViaUI`.

**Action**:
1. Visit `/settings/integrations?tab=channels`
2. Assert empty state OR existing list
3. Click "Add channel"
4. Fill Name `__e2e__ Twilio Production`, Auth Token `__e2e__ token`, Account SID `__e2e__ AC123`
5. Click Save
6. Click the new card to open the edit modal
7. Change Auth Token
8. Click Save
9. Open action menu → Delete → confirm
10. Cleanup any residual data via API in `try/finally`

**Observation 1 — Initial state**:
1. Page renders empty state OR existing channel list

**Observation 2 — Create success**:
1. `POST /channel/upsert` body matches the typed Name + credentials
2. Toast title `Integration created successfully`
3. The new card is visible

**Observation 3 — Edit hydration + lock**:
1. `GET /channel/get?include_config=true` fires
2. Auth Token + Account SID + Type are populated; Type is locked

**Observation 4 — Edit success**:
1. `POST /channel/upsert` body contains the existing `id` and updated Auth Token
2. Toast title `Integration updated successfully`

**Observation 5 — Delete success**:
1. `DELETE /channel/delete?channel_id=<id>` fires
2. Toast title `Integration deleted successfully`
3. The card is removed from the grid

**Observation 6 — Cleanup**:
1. The cleanup block runs even if assertions fail
2. No `__e2e__` residue remains after the test

---

## Expected Toast Messages

Toasts use Sonner via `showToast` (`src/utils/toast.tsx`). `handleApiError` (in `src/utils/helpers.ts`) passes the backend `response.data.detail` string as the toast **title**; when `detail` is not a string, it uses the title "Something went wrong. Please try again."

| Trigger                                              | Toast title                                                   | Variant  |
| ---------------------------------------------------- | ------------------------------------------------------------- | -------- |
| Channel create succeeds                              | `Integration created successfully`                            | success  |
| Channel update succeeds                              | `Integration updated successfully`                            | success  |
| Channel delete succeeds                              | `Integration deleted successfully`                            | success  |
| Upsert backend 409 duplicate                         | `A channel with this name already exists in this organization`| error    |
| Upsert backend 400 (missing field)                   | `channel_type is required` / `name is required`               | error    |
| Delete backend 404                                   | `Channel not found`                                           | error    |
| Delete backend 403                                   | `Admin or Owner role required`                                | error    |
| Any 5xx with `detail` string                         | `Internal Server Error` (verbatim)                            | error    |
| Any error where `detail` is not a string             | `Something went wrong. Please try again.`                     | error    |

---

## Edge Cases (each appears as a `TC-EDGE-*` or related test case above)

- [x] Unauthenticated access → middleware redirect — TC-NAV-001
- [x] Slow `/channel/list` → skeleton renders until response — TC-EDGE-012
- [x] Empty org → dashed empty state + visible "Add channel" affordance — TC-HAPPY-003
- [x] Edit modal opens before `GET /channel/get` returns → TC-LOADING-002
- [x] Submit while a previous submit is in flight → TC-LOADING-003
- [x] Zod validation empty fields → TC-VALIDATE-001..003
- [x] Network/API error on upsert → TC-EDGE-010
- [x] Delete a channel that still has phone numbers — TC-ERROR-008
- [ ] Reset atom on page unmount (`resetChannelsAtom`) — not yet covered ⚠
- [x] Catalog pre-select closing modal — TC-EDGE-008
- [x] Token expires mid-action → 401 — TC-ERROR-010 ⚠ unverified interceptor behaviour
- [x] Double submission — TC-LOADING-003
- [ ] Delete confirm + immediate refresh concurrent — not yet covered ⚠
- [ ] Hydration race (modal closed before GET resolves) — not yet covered ⚠
- [ ] Catalog tile `configured: false` — not yet covered ⚠

---

## Business Rules

- Today only one provider type is exposed in the UI: `twilio`. The select is functional but single-option.
- `encrypted_config` is AES-encrypted server-side (`core/utils/encryption.py`); the frontend only ever sees the plaintext values it submits.
- Channel ownership is per-organization; the `tenant_id` header (from the `org_tenant_id` cookie, injected by `src/utils/axios.ts`) scopes every request.
- A channel can carry many phone numbers; phone-number routing is owned by the agent CRUD flow, not the Channels tab.
- Provider type is immutable after creation (Type field locked in edit mode).

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab navigation reaches every actionable element — TC-A11Y-001
- [x] Action menu trigger has an accessible name — TC-A11Y-004
- [x] Modal traps focus and restores it on close — TC-A11Y-003
- [x] Inputs use shared `TextInput`/`SelectInput` with associated labels — covered indirectly via TC-VALIDATE-* errors
- [x] Error messages render as `helperText` and announced — TC-A11Y-005
- [x] Buttons in the loading state announce a meaningful label — TC-A11Y-006

---

## Mapping: old scenario IDs → new TC IDs

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| WF-1            | TC-HAPPY-001      | view the channels list                                               |
| PS-1            | TC-HAPPY-002      | list loads with one Twilio channel                                   |
| PS-2            | TC-HAPPY-003      | empty list renders dashed empty state                                |
| WF-2 / PS-3     | TC-HAPPY-004      | add a new channel via the dashed CTA                                 |
| PS-5            | TC-HAPPY-005      | edit modal hydrates with decrypted config                            |
| WF-3 / PS-4     | TC-HAPPY-006      | edit a channel succeeds                                              |
| WF-4 / PS-6     | TC-HAPPY-007      | delete a channel succeeds                                            |
| WF-5 / PS-7     | TC-HAPPY-008      | catalog Add API key pre-selects Twilio                               |
| WF-7            | TC-HAPPY-009      | refresh both lists from header button                                |
| FS-1            | TC-VALIDATE-001   | empty required Name blocks submit                                    |
| FS-2            | TC-VALIDATE-002   | empty Auth Token                                                     |
| FS-3            | TC-VALIDATE-003   | empty Account SID                                                    |
| CN-016          | TC-VALIDATE-004   | whitespace-only name is rejected by validation                       |
| CN-017          | TC-VALIDATE-005   | whitespace-only auth token is rejected by validation                 |
| CN-018          | TC-VALIDATE-006   | whitespace-only account sid is rejected by validation                |
| FS-4            | TC-ERROR-001      | backend 400 missing channel_type                                     |
| FS-5 / CN-009   | TC-ERROR-002      | duplicate channel name (409)                                         |
| FS-6            | TC-ERROR-003      | unauthorized 401 on list                                             |
| FS-7 / CN-007   | TC-ERROR-004      | forbidden 403 on delete                                              |
| FS-8 / CN-008   | TC-ERROR-005      | channel not found 404 on delete                                      |
| FS-9 / CN-010   | TC-ERROR-006      | server 500 on upsert                                                 |
| FS-10           | TC-ERROR-007      | 422 validation error falls back to generic toast                     |
| FS-11 / CN-034  | TC-ERROR-008      | delete a channel that still has phone numbers (500 IntegrityError)   |
| FS-12           | TC-ERROR-009      | edit hydration fails (404 on get)                                    |
| CN-006          | TC-ERROR-010      | upsert 401 mid-flow surfaces toast without redirect                  |
| CN-005          | TC-ERROR-011      | list 400 surfaces detail toast and renders empty grid                |
| CN-012          | TC-LOADING-001    | slow save disables button and shows saving label                     |
| CN-013          | TC-LOADING-002    | slow edit hydration keeps loader and disabled save                   |
| CN-015          | TC-LOADING-003    | double-click on save does not double-submit                          |
| CN-019          | TC-EDGE-001       | name trims surrounding whitespace before submit                      |
| CN-023          | TC-EDGE-002       | account sid trims surrounding whitespace before submit               |
| CN-020          | TC-EDGE-003       | name accepts unicode and html-ish characters without xss             |
| CN-021          | TC-EDGE-004       | very long name handled with backend validation                       |
| CN-022          | TC-EDGE-005       | auth token input is masked                                           |
| CN-035          | TC-EDGE-006       | edit submit preserves immutable channel_type                         |
| CN-036          | TC-EDGE-007       | type select exposes only twilio today                                |
| CN-033          | TC-EDGE-008       | closing modal after catalog pre-select resets type lock              |
| CN-032          | TC-EDGE-009       | type field is locked in edit mode                                    |
| CN-011          | TC-EDGE-010       | save network failure preserves form data                             |
| CN-014          | TC-EDGE-011       | concurrent edit handled by last-write or 409                         |
| CN-025          | TC-EDGE-012       | loading state renders the skeleton grid                              |
| CN-026          | TC-EDGE-013       | tab badge reflects channel count                                     |
| CN-027          | TC-EDGE-014       | refresh button re-fetches both lists                                 |
| CN-028          | TC-EDGE-015       | action menu edit opens form in edit mode                             |
| CN-029          | TC-EDGE-016       | delete confirmation cancel preserves the card                        |
| CN-030          | TC-EDGE-017       | channel grid does not currently expose sort or filter                |
| FS-13 / CN-001  | TC-NAV-001        | unauthenticated visit redirects to login                             |
| CN-002          | TC-NAV-002        | expired token redirects to login and clears cookie                   |
| CN-003          | TC-NAV-003        | member role sees channels list but cannot mutate                     |
| CN-004          | TC-NAV-004        | legacy integrations path redirects to settings integrations          |
| CN-031          | TC-NAV-005        | catalog Add API key pre-selects twilio and locks type                |
| CN-043          | TC-NAV-006        | clicking channels tab flips active state                             |
| CN-044          | TC-NAV-007        | browser back closes the modal without leaving the page               |
| CN-045          | TC-NAV-008        | reload preserves the active tab via query param                      |
| CN-037          | TC-A11Y-001       | tab order through channel form reaches every field                   |
| CN-038          | TC-A11Y-002       | Enter on Account SID submits the form                                |
| CN-039          | TC-A11Y-003       | channel modal traps focus and restores on close                      |
| CN-040          | TC-A11Y-004       | action menu trigger exposes accessible name                          |
| CN-041          | TC-A11Y-005       | inline errors are announced via aria-live                            |
| CN-042          | TC-A11Y-006       | save button announces saving state                                   |
| CN-FULL         | TC-FULL-001       | walks create configure edit delete of a twilio channel end to end    |
