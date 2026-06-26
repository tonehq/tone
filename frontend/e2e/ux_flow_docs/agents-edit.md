# Agents — Edit Flow (E2E test cases)

Companion to `frontend/e2e/dashboard/agents-edit.spec.ts`. Every test case
below maps to a Playwright `test(...)` name so a failing run can be triaged
back to its scenario.

> **Format rule (mandatory):** every test case below is one **Action** (steps
> the user performs) followed by multiple **Observations** (each a set of
> verification steps). See [`_template.md`](_template.md) for the canonical
> shape and ID prefixes.

## User stories

- As a user, I can open `/agents/edit/{type}/{id}` and see the existing
  configuration pre-filled across all six steps.
- I can change any field and save — only the changed fields are sent to the
  backend.
- I can upload KB documents and assign phone numbers from sub-modals.
- I can delete the agent from the header.
- If I try to navigate away with unsaved changes, a custom modal asks me to
  discard or keep editing — covering sidebar nav, browser back, header Back,
  "New tool" / "New MCP server" buttons.
- If the agent ID is not found (404), the page redirects me back to the agent
  list with a toast.

> **Routing update (focused editor):** The editor is now a focused full-screen
> experience (the main app sidebar is hidden) and each section is its own URL
> route. Opening an agent lands on its **Overview** first; the configuration
> steps live at `/agents/edit/{type}/{id}/{section}` where section ∈
> `overview | basics | prompt | ai | voice | tools | knowledge`. The bare
> `/agents/edit/{type}/{id}` redirects to `…/overview`. Section navigation is
> route-based (rail `<Link>`s), so it does **not** trigger the unsaved-changes
> guard; only leaving the editor does.

## Routes

| Route | Renders |
|---|---|
| `/agents/edit/{type}/{id}` | redirect → `/agents/edit/{type}/{id}/overview` |
| `/agents/edit/{type}/{id}/overview` | `AgentOverview` (Vercel-style detail card) |
| `/agents/edit/{type}/{id}/{section}` | the matching step (Basics/Prompt/AI/Voice/Tools/Knowledge) |

The form state + chrome (header save-bar, rail, modals) live in
`agents/edit/[type]/[id]/layout.tsx` → `AgentEditorShell`, which persists across
section navigation so values are never lost.

## Key files

- `src/components/agents/AgentEditorShell.tsx`
- `src/components/agents/agent-form/steps/{KnowledgeBaseUploadModal,AssignPhoneNumberModal}.tsx`
- `src/hooks/useUnsavedChangesGuard.ts`
- `src/utils/agentFormUtils.ts` — `agentDetailToFormState`, `formStateToUpdatePayload`
- `src/services/agentsService.ts` — `getAgent`, `updateAgent`, `deleteAgent`
- `src/atoms/AgentsAtom.tsx` — `fetchAgentAtom`, `updateAgentAtom`, `deleteAgentAtom`

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| GET | `/agent/get_agent?agent_id=` | Page mount |
| PUT | `/agent/update_agent?agent_id=` | Save (diff payload) |
| DELETE | `/agent/delete_agent?agent_id=` | Confirm delete |
| POST | `/knowledge-base/upload` (FormData with `agent_id`) | KB upload modal |
| GET | `/channel/{id}/phone_numbers` | Phone assign modal |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Loads the agent and hydrates the form

**Preconditions**:
- User is authenticated
- An agent exists at id `<id>` of type `inbound`

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Hydration request**:
1. Exactly one `GET /agent/get_agent?agent_id=<id>` request is recorded
2. URL ends up at `/agents/edit/inbound/<id>/overview` (auto-redirect)

**Observation 2 — Form hydrates**:
1. After the response, every form step is populated via `agentDetailToFormState`
2. The header shows the agent's actual name (not the default)

---

### TC-HAPPY-002: Step values persist across tab switches

**Preconditions**: TC-HAPPY-001 setup; form has hydrated.

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Navigate to `/agents/edit/inbound/<id>/prompt`
3. Navigate to `/agents/edit/inbound/<id>/ai`
4. Navigate back to `/agents/edit/inbound/<id>/basics`

**Observation 1 — Values persist across tabs**:
1. All step fields show the originally fetched values throughout the navigation
2. Tab switches do NOT reset any field

---

### TC-HAPPY-005: Header shows Delete and the agent name

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Edit-mode header chrome**:
1. The agent's name is shown in the header
2. An avatar with the initial letter is visible
3. A `Delete` button is visible
4. There is NO `New` badge (edit mode)

---

### TC-HAPPY-006: Save button reads "Save changes" on edit

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Save button label**:
1. The primary save button label reads `Save changes`
2. The label is NOT `Create agent`

---

### TC-HAPPY-007: Name-only change posts diff payload

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Change only the `Name` field
3. Click `Save changes`

**Observation 1 — Diff-only payload**:
1. Exactly one `PUT /agent/update_agent?agent_id=<id>` request is recorded
2. The request body equals `{ "name": "<new-name>" }` (only the changed field)
3. No other fields appear in the body

---

### TC-HAPPY-008: Unchanged save shows "No changes" toast

**Action**:
1. Visit `/agents/edit/inbound/<id>` (form is clean)
2. Click `Save changes` without modifying anything

**Observation 1 — No API call, toast surfaces**:
1. Zero `PUT /agent/update_agent` requests are recorded
2. A toast with the title `No changes` appears

---

### TC-HAPPY-009: Tool toggle posts tool_ids diff only

**Action**:
1. Visit `/agents/edit/inbound/<id>/tools`
2. Toggle one tool checkbox (add or remove)
3. Click `Save changes`

**Observation 1 — Diff-only payload**:
1. `PUT /agent/update_agent` body equals `{ "tool_ids": [...] }`
2. No other fields appear in the body

---

### TC-HAPPY-010: Clearing description posts null

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Clear the `Description` field
3. Click `Save changes`

**Observation 1 — Explicit null in payload**:
1. `PUT /agent/update_agent` body includes `{ "description": null }`
2. This relies on backend `exclude_unset` semantics — if it flips to `exclude_none`, this test fails

---

### TC-HAPPY-011: KB upload modal posts file and selects on close

**Action**:
1. Visit `/agents/edit/inbound/<id>/knowledge`
2. Open the KB upload modal
3. Select a valid file and submit

**Observation 1 — Upload request**:
1. Exactly one `POST /knowledge-base/upload` request is recorded
2. The request body is FormData containing `agent_id=<id>` and the file

**Observation 2 — Modal closes, new upload auto-selected**:
1. The modal is removed from the DOM
2. The new upload appears in the KB picker and is selected (checkbox ticked)

---

### TC-HAPPY-012: Phone assignment round-trips channel_id and label

**Action**:
1. Visit `/agents/edit/inbound/<id>/knowledge`
2. Open the Assign Phone modal
3. Pick a service provider + channel + phone number
4. Click `Save changes` on the editor
5. After save, reload

**Observation 1 — Round-trip persistence**:
1. After reload, the assigned phone shows the correct `channel_id`
2. The assigned phone shows the correct `label`
3. Backend response retains both fields (regression guard)

---

### TC-HAPPY-013: Preview shows live form state

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Type a new value into `Name`
3. Click `Preview` in the header

**Observation 1 — Modal reflects live state via useWatch**:
1. The Preview modal opens
2. The Name card shows the new value (not the persisted value)

---

### TC-HAPPY-014: Delete opens confirmation modal

**Action**:
1. Visit `/agents/edit/inbound/<id>`
2. Click the header `Delete` button

**Observation 1 — Modal opens with destructive copy**:
1. A confirmation modal is visible
2. Copy includes destructive wording (e.g. `This action cannot be undone`)
3. The primary action button is a `Delete` button styled as danger

---

### TC-HAPPY-015: Delete bypasses unsaved-changes guard and redirects

**Preconditions**: form is dirty (at least one unsaved change).

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Edit the `Name` field
3. Click `Delete` in the header
4. Confirm the deletion

**Observation 1 — Delete fires regardless of dirty state**:
1. Exactly one `DELETE /agent/delete_agent?agent_id=<id>` request is recorded
2. NO discard-changes modal appears (delete bypasses the guard)

**Observation 2 — Redirect to list**:
1. URL becomes `/agents`

---

### TC-NAV-016: Dirty sidebar click opens the discard modal

**Preconditions**: form is dirty.

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Type into a field to make the form dirty
3. Click a sidebar `<Link>` that leaves the editor (e.g. back to `/agents`)

**Observation 1 — Custom modal appears**:
1. A modal titled `Discard unsaved changes?` (or equivalent) is visible
2. Navigation is BLOCKED until the user picks an option

**Observation 2 — Decision branches**:
1. Clicking `Keep editing` dismisses the modal and stays at the current URL
2. Clicking `Discard` continues the navigation

---

### TC-NAV-017: Dirty browser back routes through the discard modal

**Preconditions**: form is dirty; user navigated to this page from somewhere with history.

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Make the form dirty
3. Press the browser Back button

**Observation 1 — Modal intercepts back**:
1. The custom discard modal opens
2. URL has not yet changed

**Observation 2 — Decision branches**:
1. `Keep editing` cancels — URL stays at `/agents/edit/inbound/<id>/basics`
2. `Discard` runs the back navigation

---

### TC-NAV-018: Dirty reload triggers beforeunload

**Preconditions**: form is dirty.

**Action**:
1. Make the form dirty
2. Reload the browser tab (Ctrl+R / Cmd+R)

**Observation 1 — Native beforeunload prompt**:
1. The browser shows its native `beforeunload` dialog
2. The custom modal does NOT replace it (the platform forbids replacement)

---

### TC-NAV-019: Dirty New tool click routes through discard modal

**Preconditions**: form is dirty.

**Action**:
1. Visit `/agents/edit/inbound/<id>/tools`
2. Make the form dirty
3. Click the `New tool` button

**Observation 1 — Custom modal opens**:
1. The discard modal is visible
2. Navigation to `/tools/create` is blocked

**Observation 2 — Discard continues**:
1. Clicking `Discard` navigates to `/tools/create`

---

### TC-NAV-020: Dirty header Back routes through discard modal

**Preconditions**: form is dirty.

**Action**:
1. Make the form dirty
2. Click the header `Back` arrow

**Observation 1 — Custom modal opens**:
1. The discard modal is visible
2. The back navigation is blocked

---

### TC-NAV-021: Clean state never opens the discard modal

**Preconditions**: form is clean (no edits).

**Action**:
1. Visit `/agents/edit/inbound/<id>`
2. Click sidebar Link / header Back / `New tool` button

**Observation 1 — Navigation proceeds without prompt**:
1. NO discard modal is visible at any time
2. Navigation completes immediately

---

### TC-NAV-022: Successful save resets dirty so nav is unblocked

**Action**:
1. Make the form dirty
2. Click `Save changes` (it succeeds)
3. After the success toast, click a sidebar link

**Observation 1 — Form is no longer dirty**:
1. `methods.reset` ran after the successful save
2. Navigation proceeds without a discard modal

---

### TC-ERROR-003: 404 redirects to /agents

**Action**:
1. Visit `/agents/edit/inbound/<bad-id>`

**Observation 1 — Toast and redirect**:
1. A toast titled `Agent not found` appears
2. `router.replace('/agents')` runs — URL becomes `/agents`
3. Pressing browser Back does NOT return to the bad edit URL (replace, not push)

**API mock**: `GET /agent/get_agent?agent_id=<bad-id>` → 404 `{ "detail": "Agent not found" }`.

---

### TC-ERROR-004: 500 surfaces an error toast

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Toast and stay on page**:
1. `handleApiError` shows a toast with the backend `detail`
2. URL is still `/agents/edit/inbound/<id>` (user is not redirected)

**API mock**: `GET /agent/get_agent` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-026: Update 400 surfaces validation toast and preserves dirty state

**Action**:
1. Make the form dirty with an invalid field value
2. Click `Save changes`

**Observation 1 — Toast with backend detail**:
1. A toast with backend `detail` text appears

**Observation 2 — Form preserved**:
1. Every dirty field still has the typed value
2. URL is unchanged
3. The tab does NOT jump unless the failure is basics-level

**API mock**: `PUT /agent/update_agent` → 400 `{ "detail": "Invalid field X" }`.

---

### TC-ERROR-027: Update 401 surfaces error toast without redirect

**Action**:
1. Make the form dirty
2. Click `Save changes` with an expired token

**Observation 1 — Toast and state**:
1. Toast title equals `Invalid token` (or backend `detail`)
2. The form retains dirty values
3. URL is unchanged — no auto-redirect to login

**API mock**: `PUT /agent/update_agent` → 401 `{ "detail": "Invalid token" }`.

---

### TC-ERROR-028: Update 403 surfaces forbidden toast

**Action**:
1. Make the form dirty as a member-role user
2. Click `Save changes` on an owner-only agent

**Observation 1 — Toast and state**:
1. Toast surfaces backend `detail`
2. Form is intact

**API mock**: `PUT /agent/update_agent` → 403 `{ "detail": "Forbidden" }`.

---

### TC-ERROR-029: Update 404 redirects back to /agents

**Action**:
1. Make the form dirty
2. Click `Save changes` after another user deleted the agent

**Observation 1 — Toast and redirect**:
1. Toast title equals `Agent not found`
2. URL becomes `/agents`

**API mock**: `PUT /agent/update_agent` → 404 `{ "detail": "Agent not found" }`.

---

### TC-ERROR-030: Update 409 surfaces duplicate name toast

**Action**:
1. Change `Name` to a name already used by another agent
2. Click `Save changes`

**Observation 1 — Toast + Save re-enables**:
1. Toast surfaces backend `detail` (e.g. `Agent name already exists`)
2. Form remains on the current step
3. The `Save changes` button re-enables (no longer disabled)

**API mock**: `PUT /agent/update_agent` → 409 `{ "detail": "Agent name already exists" }`.

---

### TC-ERROR-031: Update 500 surfaces generic error toast

**Action**:
1. Make the form dirty and click `Save changes`

**Observation 1 — Toast and re-enable**:
1. Toast shows the backend `detail`
2. Form is intact
3. Save re-enables

**API mock**: `PUT /agent/update_agent` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-032: Delete 403 surfaces forbidden toast on edit page

**Action**:
1. Click `Delete` in the header
2. Confirm

**Observation 1 — Toast and stay on page**:
1. Toast surfaces backend `detail` (e.g. `Forbidden`)
2. URL is still the edit page (no redirect to `/agents`)

**API mock**: `DELETE /agent/delete_agent` → 403 `{ "detail": "Forbidden" }`.

---

### TC-ERROR-033: Delete 500 surfaces generic error toast on edit page

**Action**:
1. Click `Delete` → confirm

**Observation 1 — Toast and stay on page**:
1. Toast shows the backend `detail`
2. URL is still the edit page

**API mock**: `DELETE /agent/delete_agent` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-EDGE-034: Network failure on save preserves the form

**Action**:
1. Make the form dirty
2. Disconnect network
3. Click `Save changes`

**Observation 1 — Toast and preservation**:
1. Toast titled `Something went wrong. Please try again.` appears
2. Every dirty field still has its typed value
3. No partial commit (no `PUT /agent/update_agent` recorded)

---

### TC-LOADING-035: Slow save disables the save button and shows loading text

**Action**:
1. Make the form dirty
2. Click `Save changes` against a deliberately slow `PUT /agent/update_agent` (>3s)
3. Try double-clicking the button

**Observation 1 — Button state during request**:
1. Button text becomes `Loading...`
2. Button has `disabled` attribute
3. Double-clicks record only ONE `PUT /agent/update_agent`

---

### TC-LOADING-036: Slow agent load shows loader until hydration completes

**Action**:
1. Visit `/agents/edit/inbound/<id>` with `GET /agent/get_agent` delayed > 3s

**Observation 1 — Loader visible**:
1. An `<AppLoader>` is visible inside the editor shell
2. No empty-form flash occurs

**Observation 2 — Hydration after response**:
1. After the response, the loader is removed
2. The form renders with hydrated values

---

### TC-LOADING-037: Concurrent edit conflict is surfaced as a toast

**Action**:
1. Make the form dirty in tab A
2. Save the same agent from tab B (or trigger a backend 409/412)
3. Click `Save changes` in tab A

**Observation 1 — Toast surfaces conflict**:
1. Toast shows the backend `detail`
2. Dirty fields in tab A remain — user can manually refresh

**API mock**: `PUT /agent/update_agent` → 409 or 412 with `{ "detail": "Conflict" }`.

---

### TC-NAV-023: Unauthenticated edit visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Middleware redirect**:
1. Status is 307
2. URL becomes `/auth/login?redirect=%2Fagents%2Fedit%2Finbound%2F<id>`

---

### TC-NAV-024: Expired token on edit redirects to login

**Preconditions**: an expired `tone_access_token` cookie is present.

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Redirect + cookie cleared**:
1. URL becomes `/auth/login?redirect=...`
2. The expired cookie is cleared by the login response

---

### TC-NAV-025: Non-member is denied access to the agent editor

**Preconditions**: user signed in but not an org member.

**Action**:
1. Visit `/agents/edit/inbound/<id>`

**Observation 1 — Access denied / redirect**:
1. Either an access-denied state renders OR URL redirects to `/agents`
2. Zero `GET /agent/get_agent` requests fire for the forbidden id

---

### TC-VALIDATE-038: Whitespace-only name update is rejected

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Replace `Name` with `   ` (only spaces)
3. Click `Save changes`

**Observation 1 — Inline error**:
1. Inline `Required` helper text appears under `Name`

**Observation 2 — No API call and tab jumps to Basics**:
1. Zero `PUT /agent/update_agent` requests are recorded
2. URL switches to `/agents/edit/inbound/<id>/basics`

---

### TC-EDGE-039: Name and description are trimmed on update

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Edit `Name` to ` New Name ` (with surrounding spaces)
3. Edit `Description` similarly
4. Click `Save changes`
5. Reload

**Observation 1 — Trimmed values persist**:
1. Reloaded `name` equals `New Name` (no surrounding whitespace)
2. Reloaded `description` is trimmed

---

### TC-EDGE-040: Special chars and unicode round-trip without xss

**Action**:
1. Insert `<script>alert(1)</script>` into `Name`
2. Insert emoji/unicode into `Description` and `Prompt`
3. Click `Save changes`
4. Reload

**Observation 1 — Verbatim round-trip**:
1. The reloaded fields contain the literal text verbatim

**Observation 2 — No XSS execution**:
1. `window.alert` was never invoked
2. The `<script>` substring renders as text, not parsed as HTML

---

### TC-EDGE-041: Very long name update is bounded with feedback

**Action**:
1. Replace `Name` with a > 500-char value
2. Click `Save changes`

**Observation 1 — Bounded behaviour**:
1. Either the input truncates with a helpful inline message OR the backend rejects with 4xx
2. No client crash

---

### TC-EDGE-042: Pasting newlines into name strips them

**Action**:
1. Paste `line1\nline2` into the single-line `Name` input
2. Click `Save changes`

**Observation 1 — Single-line value**:
1. The Name input `value` contains no `\n`
2. The persisted `name` is single-line

---

### TC-EDGE-043: Very large token-limit value is bounded by the backend

**Action**:
1. Visit `/agents/edit/inbound/<id>/ai`
2. Set token limit to `999999`
3. Click `Save changes`

**Observation 1 — Bounded behaviour**:
1. Either the value is accepted (200) OR the backend caps with a 4xx
2. No client crash either way

---

### TC-EDGE-044: Temperature slider clamps to range via keyboard on edit

**Action**:
1. Visit `/agents/edit/inbound/<id>/ai`
2. Focus the `Temperature` slider
3. Press `Home`, then `End`
4. Click `Save changes`

**Observation 1 — Clamped values**:
1. `Home` sets the value to the slider minimum
2. `End` sets the value to the slider maximum
3. The `PUT /agent/update_agent` payload reflects the clamped value

---

### TC-A11Y-045: Tab order through Basics reaches every control on edit

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Press `Tab` repeatedly from the page body

**Observation 1 — Sequence**:
1. Focus passes through `Name` → `Description` → `First message` → `End call message` → `Active` toggle
2. No focusable form control is skipped

---

### TC-A11Y-046: Enter on Name input triggers save

**Action**:
1. Visit `/agents/edit/inbound/<id>/basics`
2. Make a small change to `Name`
3. Focus `Name` and press `Enter`

**Observation 1 — Save fires**:
1. Exactly one `PUT /agent/update_agent` request is recorded (same as clicking `Save changes`)

---

### TC-A11Y-047: Validation error is announced via aria-live on edit

**Action**:
1. Clear `Name` and click `Save changes`

**Observation 1 — Announceable error**:
1. The `Required` helper text is inside an element with `role="alert"` or `aria-live="polite"`
2. The text equals `Required` exactly

---

### TC-A11Y-048: Delete confirmation modal traps focus and restores on close

**Action**:
1. Click `Delete`
2. Tab cycle inside the modal
3. Press `Escape`

**Observation 1 — Focus trap**:
1. Tab cycles only within the modal

**Observation 2 — Focus restoration**:
1. Escape closes the modal
2. Focus returns to the `Delete` button

---

### TC-A11Y-049: Discard changes modal traps focus and restores on close

**Action**:
1. Make the form dirty
2. Click a sidebar Link to trigger the discard modal
3. Tab cycle inside the modal
4. Press `Escape` (or click `Keep editing`)

**Observation 1 — Focus trap**:
1. Tab cycles only within the discard modal

**Observation 2 — Focus restoration**:
1. Closing the modal restores focus to the link/button that triggered the navigation attempt

---

### TC-A11Y-050: Sub-modals trap focus and restore on close

**Action**:
1. Open the KB Upload modal — tab cycle — close with Escape
2. Open the Assign Phone modal — tab cycle — close with Escape

**Observation 1 — KB modal trap + restore**:
1. Tab cycles only within the modal
2. Escape closes and restores focus to the trigger

**Observation 2 — Phone assign modal trap + restore**:
1. Same behaviour: focus trapped, restored on close

---

### TC-FULL-001: Modifies every step, saves, reloads and verifies

**Preconditions**:
- User authenticated against a real backend (no mocks)
- A freshly created `__e2e__`-prefixed inbound agent exists
- Helpers from `frontend/e2e/helpers/agentFixtures.ts` available

**Action**:
1. Visit `/agents/edit/inbound/<freshAgentId>`
2. **Basics**: change `description`, `first message`, `end call message`, toggle `is_active`
3. **Prompt**: change `system prompt`
4. **AI**: pick LLM provider + model; set temperature via `setSliderByKeyboard`; set `max_tokens`; set `conversation_history_token_limit`
5. **Voice (TTS)**: pick `language`, `provider`, `model`, `voice`, set `speed` via keyboard
6. **Voice (STT)**: pick STT provider + model
7. Click `Save changes`
8. Reload `/agents/edit/inbound/<id>`
9. Read back every field

**Observation 1 — Save round-trip succeeds**:
1. Exactly one `PUT /agent/update_agent` is recorded
2. A success toast appears

**Observation 2 — Scalar fields rehydrate on reload (asserted)**:
1. `description` matches what was typed
2. `config.first_message` matches
3. `config.end_call_message` matches
4. `config.system_prompt_template` matches
5. `config.llm_settings.max_tokens` matches
6. `config.conversation_history_token_limit` matches

**Observation 3 — Sliders + dependent dropdowns saved but not re-asserted**:
1. Temperature slider, speed slider, `is_active` toggle, and provider/model cascades are filled
2. Reload does not re-assert these because catalog ordering varies by environment

**Observation 4 — Tools/MCP/KB/phone NOT exercised here**:
1. Those flows are exercised in `agents-create.md` TC-FULL-001 and individually by TC-HAPPY-009 (tools), TC-HAPPY-011 (KB), TC-HAPPY-012 (phone)

**Cleanup** (in `try/finally`):
1. `DELETE /agent/delete_agent?agent_id=<freshAgentId>`
2. Clear cookies

---

## Edge cases

- Backend dropping `selected_tools` from `agent_mcp_server` (legacy column) →
  payload silently omits it; covered indirectly by TC-HAPPY-009.
- `agent_response` returning `phone_numbers` without `channel_id` is a
  regression that TC-HAPPY-012 explicitly guards against.
- `update_agent` honouring explicit `null` via `exclude_unset=True` is covered
  by TC-HAPPY-010 — if this flips to `exclude_none`, TC-HAPPY-010 fails.

## Coverage map (which scenarios `TC-FULL-001` transitively exercises)

| Original scenario | Transitively covered by TC-FULL-001? | Notes |
|---|---|---|
| AE-002 Step values persist across tabs | yes | every step is visited and its values are re-asserted after reload |
| AE-007 Diff-aware name update | partially | save round-trip is exercised, but the test changes many fields, not just `name` |
| AE-010 Clearing description posts null | no | TC-FULL-001 only sets non-empty values |

Scenarios still tracked only by their individual test cases (TC-ERROR-004 500-error toast, TC-HAPPY-009 tool diff, TC-HAPPY-010 description null, TC-HAPPY-011 KB upload, TC-HAPPY-012 phone round-trip, TC-HAPPY-013 Preview live form, TC-NAV-017 dirty back, TC-NAV-018 dirty reload, TC-NAV-022 save resets dirty) are *not* exercised by TC-FULL-001.

## Out of scope (covered elsewhere)

- Initial creation flow → `agents-create.md`.
- Listing / search / sort → `agents.md`.
- Backend integrity tests → pytest under `test-cases/`.

## Cleanup

Tests create a "fixture" agent in `beforeAll` and `DELETE` it in `afterAll`
via `/agent/delete_agent`. If the spec aborts before cleanup, the next run
sweeps any agent name starting with `__e2e__` from `/agent/list`.

---

## Scenario → TC ID cross-reference

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| AE-001          | TC-HAPPY-001      | loads the agent and hydrates the form                                |
| AE-002          | TC-HAPPY-002      | step values persist across tab switches                              |
| AE-003          | TC-ERROR-003      | 404 redirects to /agents                                             |
| AE-004          | TC-ERROR-004      | 500 surfaces an error toast                                          |
| AE-005          | TC-HAPPY-005      | header shows Delete and the agent name                               |
| AE-006          | TC-HAPPY-006      | Save button reads Save changes on edit                               |
| AE-007          | TC-HAPPY-007      | name-only change posts diff payload                                  |
| AE-008          | TC-HAPPY-008      | unchanged save shows No changes toast                                |
| AE-009          | TC-HAPPY-009      | tool toggle posts tool_ids diff only                                 |
| AE-010          | TC-HAPPY-010      | clearing description posts null                                      |
| AE-011          | TC-HAPPY-011      | KB upload modal posts file and selects on close                      |
| AE-012          | TC-HAPPY-012      | phone assignment round-trips channel_id and label                    |
| AE-013          | TC-HAPPY-013      | Preview shows live form state                                        |
| AE-014          | TC-HAPPY-014      | Delete opens confirmation modal                                      |
| AE-015          | TC-HAPPY-015      | Delete bypasses unsaved-changes guard and redirects                  |
| AE-016          | TC-NAV-016        | dirty sidebar click opens the discard modal                          |
| AE-017          | TC-NAV-017        | dirty browser back routes through the discard modal                  |
| AE-018          | TC-NAV-018        | dirty reload triggers beforeunload                                   |
| AE-019          | TC-NAV-019        | dirty New tool click routes through discard modal                    |
| AE-020          | TC-NAV-020        | dirty header Back routes through discard modal                       |
| AE-021          | TC-NAV-021        | clean state never opens the discard modal                            |
| AE-022          | TC-NAV-022        | successful save resets dirty so nav is unblocked                     |
| AE-023          | TC-NAV-023        | unauthenticated edit visit redirects to login                        |
| AE-024          | TC-NAV-024        | expired token on edit redirects to login                             |
| AE-025          | TC-NAV-025        | non-member is denied access to the agent editor                      |
| AE-026          | TC-ERROR-026      | update 400 surfaces validation toast and preserves dirty state       |
| AE-027          | TC-ERROR-027      | update 401 surfaces error toast without redirect                     |
| AE-028          | TC-ERROR-028      | update 403 surfaces forbidden toast                                  |
| AE-029          | TC-ERROR-029      | update 404 redirects back to /agents                                 |
| AE-030          | TC-ERROR-030      | update 409 surfaces duplicate name toast                             |
| AE-031          | TC-ERROR-031      | update 500 surfaces generic error toast                              |
| AE-032          | TC-ERROR-032      | delete 403 surfaces forbidden toast on edit page                     |
| AE-033          | TC-ERROR-033      | delete 500 surfaces generic error toast on edit page                 |
| AE-034          | TC-EDGE-034       | network failure on save preserves the form                           |
| AE-035          | TC-LOADING-035    | slow save disables the save button and shows loading text            |
| AE-036          | TC-LOADING-036    | slow agent load shows loader until hydration completes               |
| AE-037          | TC-LOADING-037    | concurrent edit conflict is surfaced as a toast                      |
| AE-038          | TC-VALIDATE-038   | whitespace-only name update is rejected                              |
| AE-039          | TC-EDGE-039       | name and description are trimmed on update                           |
| AE-040          | TC-EDGE-040       | special chars and unicode round-trip without xss                     |
| AE-041          | TC-EDGE-041       | very long name update is bounded with feedback                       |
| AE-042          | TC-EDGE-042       | pasting newlines into name strips them                               |
| AE-043          | TC-EDGE-043       | very large token-limit value is bounded by the backend               |
| AE-044          | TC-EDGE-044       | temperature slider clamps to range via keyboard on edit              |
| AE-045          | TC-A11Y-045       | tab order through Basics reaches every control on edit               |
| AE-046          | TC-A11Y-046       | enter on name input triggers save                                    |
| AE-047          | TC-A11Y-047       | validation error is announced via aria-live on edit                  |
| AE-048          | TC-A11Y-048       | delete confirmation modal traps focus and restores on close          |
| AE-049          | TC-A11Y-049       | discard changes modal traps focus and restores on close              |
| AE-050          | TC-A11Y-050       | sub-modals trap focus and restore on close                           |
| AE-FULL         | TC-FULL-001       | modifies every step, saves, reloads and verifies                     |
