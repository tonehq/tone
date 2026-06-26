# Agents — Create Flow (E2E test cases)

Companion to `frontend/e2e/dashboard/agents-create-inbound.spec.ts` and
`agents-create-outbound.spec.ts`. Every test case below maps to a Playwright
`test(...)` name so a failing run can be triaged back to its scenario.

> **Format rule (mandatory):** every test case below is one **Action** (steps
> the user performs) followed by multiple **Observations** (each a set of
> verification steps). See [`_template.md`](_template.md) for the canonical
> shape and ID prefixes.

## User stories

- As a user, I can create a new **inbound** agent from `/agents/create/inbound`
  with name, description, prompt, LLM provider/model, voice provider/model,
  optional tools, MCP servers, KB documents, and phone numbers.
- As a user, I can create a new **outbound** agent with the same options.
- As a user, I can preview the full configuration before saving via a
  read-only modal.
- As a user, I can leave the form mid-flow without losing data thanks to the
  unsaved-changes guard.
- As a user, I can navigate to create a new tool or MCP server from inside
  the form; if the form is dirty, I'm asked to confirm before I lose changes.

> **Routing update (focused editor):** Create is now a focused full-screen
> editor with route-per-section. `/agents/create/{type}` (type ∈
> `inbound | outbound`) redirects to `…/basics` (create mode has no Overview —
> nothing to summarise yet). Sections live at `/agents/create/{type}/{section}`.
> On successful create the app redirects to `/agents/edit/{type}/{id}/overview`.

## Routes

| Route | Renders |
|---|---|
| `/agents/create/{type}` | redirect → `/agents/create/{type}/basics` |
| `/agents/create/{type}/{section}` | the matching step (Basics/Prompt/AI/Voice/Tools/Knowledge) |

The form state + chrome live in `agents/create/[type]/layout.tsx` →
`AgentEditorShell` (shared with the edit editor).

## Key files

- `src/components/agents/AgentEditorShell.tsx`
- `src/components/agents/agent-form/AgentFormNav.tsx`
- `src/components/agents/agent-form/steps/{Basics,Prompt,Ai,Voice,ToolsMcp,KnowledgePhone,Review,KnowledgeBaseUploadModal,AssignPhoneNumberModal}Step.tsx`
- `src/hooks/useUnsavedChangesGuard.ts`
- `src/utils/agentFormUtils.ts` — `defaultFormState`, `formStateToCreatePayload`
- `src/services/agentsService.ts` — `createAgent`
- `src/atoms/AgentsAtom.tsx` — `createAgentAtom`

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| GET | `/provider/catalog` (filtered by kinds) | AI / Voice provider dropdowns |
| GET | `/provider/{id}/models` | LLM/STT/TTS model dropdowns |
| GET | `/tts/languages`, `/tts/providers`, `/tts/voices` | Voice step |
| GET | `/tool/list` | Tools & MCP step |
| GET | `/mcp/servers` | Tools & MCP step |
| POST | `/knowledge-base/list` | KB picker |
| POST | `/knowledge-base/upload` (FormData, `agent_id` optional) | KB upload modal |
| POST | `/channel/list` | Channel picker |
| GET | `/channel/{id}/phone_numbers` | Phone assign modal |
| **POST** | `/agent/create_agent` | Save button |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Renders the new-inbound agent header

**Preconditions**:
- User is authenticated
- User visits the new-inbound create page

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Header copy and badges**:
1. Header shows the default name `My Inbound Assistant`
2. An `Inbound` badge is visible
3. A `New` badge is visible
4. The header tint reflects the inbound `DIRECTION_STYLES` colour

---

### TC-HAPPY-002: Sidebar shows the six steps without Review

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Sidebar nav items**:
1. Exactly 6 sidebar items render in order: `Basics`, `Prompt`, `AI`, `Voice`, `Tools & MCP`, `Knowledge & Phone`
2. There is NO `Review` tab in the sidebar

---

### TC-HAPPY-003: Header has Back / Preview / Create agent buttons

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Header action buttons**:
1. A `Back` button is visible
2. A `Preview` button is visible
3. A `Create agent` button is visible
4. No `Delete` button is in the DOM (create mode has no delete)

---

### TC-HAPPY-004: Basics step is the default body

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Default route lands on Basics**:
1. URL becomes `/agents/create/inbound/basics` (auto-redirect from `/agents/create/inbound`)
2. The Basics step body is visible
3. The `Basics` sidebar item has the active state

---

### TC-HAPPY-006: Description field accepts long text

**Action**:
1. Visit `/agents/create/inbound`
2. Click into the `Description` field
3. Type a description up to 500 characters

**Observation 1 — Field accepts input**:
1. The field's `value` length equals the typed length (up to 500 chars)
2. No client-side truncation occurs below the 500-char limit

---

### TC-HAPPY-007: Conversation messages render as textareas

**Action**:
1. Visit `/agents/create/inbound`
2. Focus the `First message` field and type multi-line text
3. Focus the `End call message` field and type multi-line text

**Observation 1 — Fields are textareas**:
1. Both `First message` and `End call message` are `<textarea>` elements
2. Both accept newline characters
3. The visible value preserves the newlines

---

### TC-HAPPY-008: is_active switch toggles

**Action**:
1. Visit `/agents/create/inbound`
2. Click the `Active` toggle switch

**Observation 1 — Switch state flips**:
1. The switch's checked state inverts
2. The form state path `is_active` reflects the new boolean (verified via subsequent payload on save)

---

### TC-HAPPY-009: System prompt persists across tab switches

**Action**:
1. Visit `/agents/create/inbound/prompt`
2. Type a system prompt into the prompt textarea
3. Navigate to `/agents/create/inbound/basics`
4. Navigate back to `/agents/create/inbound/prompt`

**Observation 1 — Text persists**:
1. The prompt textarea still contains the previously typed text (state held in `AgentEditorShell`)

---

### TC-HAPPY-012: Selecting LLM provider reveals the model dropdown

**Action**:
1. Visit `/agents/create/inbound/ai`
2. Open the LLM provider dropdown
3. Pick a provider

**Observation 1 — Model dropdown loads**:
1. A `GET /provider/{id}/models` request is recorded
2. The model dropdown becomes visible and is populated

---

### TC-HAPPY-013: LLM tuning fields update form state

**Action**:
1. Visit `/agents/create/inbound/ai`
2. Adjust the `Temperature` slider
3. Type a value into `Max tokens`

**Observation 1 — Values captured to form state**:
1. `config.llm_settings.temperature` reflects the slider value
2. `config.llm_settings.max_tokens` reflects the typed value
3. These values appear in the next `POST /agent/create_agent` payload

---

### TC-HAPPY-014: Voice language dropdown loads from API

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Open the `Language` dropdown

**Observation 1 — Languages load**:
1. A `GET /tts/languages` request is recorded
2. The dropdown lists languages from the API response

---

### TC-HAPPY-015: Picking language refreshes TTS providers

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Pick a language from the dropdown

**Observation 1 — Providers refetch**:
1. A `GET /tts/providers?language=<code>` request is recorded
2. The provider dropdown re-populates with the API response

---

### TC-HAPPY-016: Picking provider + language loads voices

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Pick a language
3. Pick a provider

**Observation 1 — Voices request**:
1. A `GET /tts/voices?provider_id=<id>&language=<code>` request is recorded
2. The voice picker lists the returned voices

---

### TC-HAPPY-017: Voice sample play button toggles

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Pick a language and provider so voices render
3. Click the play button on a voice sample
4. Click it again

**Observation 1 — Audio play state**:
1. First click starts audio playback (button shows pause icon)
2. Second click pauses (button shows play icon)

---

### TC-HAPPY-018: Speed slider is clamped and defaulted

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Focus the `Speed` slider
3. Use keyboard arrows to push the value outside the 0.5–2.0 range

**Observation 1 — Clamp and default**:
1. The slider's value never goes below 0.5 or above 2.0
2. Default value when the page loads is 1.0
3. `config.voice_settings.speed` in the payload reflects the clamped value

---

### TC-HAPPY-019: STT provider+model dropdowns wire together

**Action**:
1. Visit `/agents/create/inbound/voice`
2. Pick an STT provider

**Observation 1 — Model dropdown populates**:
1. A `GET /provider/{id}/models` request is recorded for the STT kind
2. The STT model dropdown becomes selectable

---

### TC-HAPPY-020: Tool checkbox toggles tool_ids

**Action**:
1. Visit `/agents/create/inbound/tools`
2. Click the checkbox on a tool tile
3. Click it again to uncheck

**Observation 1 — tool_ids updates**:
1. After first click, `tool_ids` includes the tool id (verified on subsequent save)
2. After second click, the id is removed from `tool_ids`

---

### TC-HAPPY-021: Tool search filters the list

**Action**:
1. Visit `/agents/create/inbound/tools`
2. Type a term into the tool search input

**Observation 1 — Visible list filters**:
1. Tools whose name or description contains the term remain visible
2. Non-matching tools are hidden

---

### TC-HAPPY-022: New tool navigates when clean

**Preconditions**: form is not dirty (no edits yet).

**Action**:
1. Visit `/agents/create/inbound/tools`
2. Click the `New tool` button

**Observation 1 — Direct navigation**:
1. URL changes to `/tools/create` immediately
2. No discard-changes modal appears

---

### TC-HAPPY-023: MCP server picker adds and removes chips

**Action**:
1. Visit `/agents/create/inbound/tools`
2. Add an MCP server from the picker
3. Click the remove (`x`) button on the chip

**Observation 1 — Add**:
1. A chip for the selected MCP server is visible
2. `mcp_server_ids` payload (on save) includes the id

**Observation 2 — Remove**:
1. The chip is removed from the DOM
2. The id is removed from `mcp_server_ids`

---

### TC-HAPPY-024: KB list loads and toggles upload_ids

**Action**:
1. Visit `/agents/create/inbound/knowledge`

**Observation 1 — KB list renders**:
1. A `POST /knowledge-base/list` request is recorded
2. Each KB document renders as a checkbox-controlled row

**Observation 2 — Toggling updates upload_ids**:
1. Clicking a checkbox toggles `upload_ids` (verified on payload at save time)

---

### TC-HAPPY-025: KB upload modal is enabled in create mode and validates files

**Action**:
1. Visit `/agents/create/inbound/knowledge`
2. Open the KB Upload modal
3. Attempt to upload (a) a valid `.pdf` ≤ 10 MB, (b) an invalid `.exe`, (c) an oversized `.pdf` > 10 MB

**Observation 1 — Valid file accepted**:
1. The `.pdf` is staged and a `POST /knowledge-base/upload` (FormData) request will fire on submit

**Observation 2 — Invalid type rejected**:
1. The `.exe` triggers a validation error
2. No upload request fires
3. The modal shows the validation message

**Observation 3 — Oversized file rejected**:
1. The > 10 MB `.pdf` triggers an oversize error
2. No upload request fires

---

### TC-HAPPY-026: Assign phone modal lists numbers for the channel

**Action**:
1. Visit `/agents/create/inbound/knowledge`
2. Open the Assign Phone modal
3. Pick a service provider
4. Pick a channel

**Observation 1 — Dropdowns populate**:
1. `POST /channel/list` populates the channel dropdown
2. After picking the channel, `GET /channel/{id}/phone_numbers` is recorded and the numbers list renders

---

### TC-HAPPY-027: Preview modal opens with scrollable Review content

**Action**:
1. Visit `/agents/create/inbound`
2. Click the `Preview` button in the header

**Observation 1 — Modal opens**:
1. A modal is visible containing the read-only `ReviewStep` content
2. The modal body has `max-height: 85vh` and is scrollable

---

### TC-HAPPY-028: Edit link in preview jumps to the step

**Action**:
1. Click `Preview`
2. In the modal, click an `Edit` link on one of the review cards

**Observation 1 — Modal closes and tab switches**:
1. The Preview modal is removed from the DOM
2. URL changes to the matching `/agents/create/inbound/{section}`
3. The matching step body is visible

---

### TC-HAPPY-029: Create posts the payload and redirects to edit

**Preconditions**: required fields are filled (`name` non-empty).

**Action**:
1. Visit `/agents/create/inbound`
2. Fill required fields (Name + any other required)
3. Click `Create agent`

**Observation 1 — API call**:
1. Exactly one `POST /agent/create_agent` request is recorded
2. The body matches the form state via `formStateToCreatePayload`

**Observation 2 — Success toast and redirect**:
1. A success toast appears
2. URL becomes `/agents/edit/inbound/<id>` (overview)
3. No unsaved-changes modal is shown along the way

---

### TC-VALIDATE-005: Name is required and jumps to Basics on save

**Action**:
1. Visit `/agents/create/inbound`
2. Navigate to a non-Basics step (e.g. `/agents/create/inbound/prompt`)
3. Click into the `Agent name` field, clear it
4. Click `Create agent`

**Observation 1 — Inline error**:
1. Inline helper text `Required` appears under the `Name` field
2. The field receives the error style

**Observation 2 — Tab jumps to Basics**:
1. URL switches to `/agents/create/inbound/basics`
2. The `Basics` sidebar item becomes active
3. Focus moves to the `Name` field

**Observation 3 — No API call**:
1. Zero `POST /agent/create_agent` requests are recorded

---

### TC-VALIDATE-010: Token-limit input is numeric only

**Action**:
1. Visit `/agents/create/inbound/ai`
2. Focus the `Conversation history token limit` field
3. Type a non-numeric string (`abc123`)

**Observation 1 — Non-digits rejected or coerced**:
1. Non-digit characters are filtered out OR coerced to a numeric value
2. The form state path `config.conversation_history_token_limit` is a `number`
3. On save, the payload field is a JSON `number` (not a string)

---

### TC-VALIDATE-046: Whitespace-only name fails validation

**Action**:
1. Visit `/agents/create/inbound`
2. Type `   ` (only spaces) into `Name`
3. Click `Create agent`

**Observation 1 — Inline error**:
1. Inline `Required` helper text appears under `Name`

**Observation 2 — No API call and tab jumps to Basics**:
1. Zero `POST /agent/create_agent` requests are recorded
2. URL switches to `/agents/create/inbound/basics`

---

### TC-VALIDATE-052: Token-limit field rejects non-numeric input

**Action**:
1. Visit `/agents/create/inbound/ai`
2. Type letters/symbols into the token-limit input

**Observation 1 — Numeric-only enforced**:
1. The accepted value is numeric only
2. `conversation_history_token_limit` in the create payload is a JSON number

---

### TC-VALIDATE-053: Temperature slider clamps to range via keyboard

**Action**:
1. Visit `/agents/create/inbound/ai`
2. Focus the `Temperature` slider
3. Press `Home`, then `End`

**Observation 1 — Clamped values**:
1. After `Home`, the slider value equals the slider's minimum
2. After `End`, the slider value equals the slider's maximum
3. The payload's `config.llm_settings.temperature` reflects the clamped value

---

### TC-ERROR-011: LLM provider shows "No data" when catalog is empty

**Action**:
1. Visit `/agents/create/inbound/ai` with `GET /provider/catalog` mocked empty
2. Open the LLM provider dropdown

**Observation 1 — Empty popover**:
1. The dropdown shows a `No data` popover (no options listed)

**API mock**: `GET /provider/catalog` → 200 `[]`.

---

### TC-ERROR-030: Create 400 — surfaces backend validation toast, form intact

**Action**:
1. Visit `/agents/create/inbound`
2. Fill required fields and click `Create agent`

**Observation 1 — Toast surfaces backend detail**:
1. A toast with the backend `detail` text appears

**Observation 2 — Form remains intact**:
1. URL stays at `/agents/create/inbound/{section}`
2. Every typed field still has its value
3. No redirect to `/agents/edit/...` occurs

**API mock**: `POST /agent/create_agent` → 400 `{ "detail": "Invalid field X" }`.

---

### TC-ERROR-036: Create 401 surfaces error toast

**Action**:
1. Fill required fields and click `Create agent` with an expired token

**Observation 1 — Toast and form**:
1. Toast title equals `Invalid token` (or `Could not validate credentials`)
2. The form retains all typed values
3. No auto-redirect to login

**API mock**: `POST /agent/create_agent` → 401 `{ "detail": "Invalid token" }`.

---

### TC-ERROR-037: Create 403 surfaces forbidden toast

**Action**:
1. Fill required fields and click `Create agent` as a member-role user

**Observation 1 — Toast and form**:
1. A toast with backend `detail` (e.g. `Forbidden`) appears
2. Form is intact
3. No redirect

**API mock**: `POST /agent/create_agent` → 403 `{ "detail": "Forbidden" }`.

---

### TC-ERROR-038: Create 409 surfaces duplicate name toast

**Action**:
1. Fill required fields (with a name that already exists) and click `Create agent`

**Observation 1 — Toast and re-enable**:
1. A toast with backend `detail` (e.g. `Agent name already exists`) appears
2. The form stays on the current step
3. The `Create agent` button re-enables (no longer disabled / loading)

**API mock**: `POST /agent/create_agent` → 409 `{ "detail": "Agent name already exists" }`.

---

### TC-ERROR-039: Create 500 surfaces generic error toast

**Action**:
1. Fill required fields and click `Create agent`

**Observation 1 — Toast and re-enable**:
1. A toast with the backend `detail` appears
2. The form is intact
3. The Create button re-enables

**API mock**: `POST /agent/create_agent` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-040: Provider catalog 500 falls back gracefully

**Action**:
1. Visit `/agents/create/inbound/ai` with `GET /provider/catalog` returning 500

**Observation 1 — Empty dropdowns, form still saveable**:
1. The LLM provider dropdown renders empty
2. Other tabs still allow editing
3. Saving (with defaults retained on AI step) does not crash

**API mock**: `GET /provider/catalog` → 500.

---

### TC-ERROR-041: KB upload 413 surfaces oversize message

**Action**:
1. Open the KB Upload modal
2. Attempt to upload a file the backend rejects with 413

**Observation 1 — Modal feedback**:
1. The modal shows an oversize validation message
2. The KB list is unchanged
3. No new upload is added

**API mock**: `POST /knowledge-base/upload` → 413 `{ "detail": "File too large" }`.

---

### TC-NAV-031: Unauthenticated visit redirects to login (inbound)

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Middleware redirect**:
1. Status is 307
2. URL becomes `/auth/login?redirect=%2Fagents%2Fcreate%2Finbound`

---

### TC-NAV-032: Unauthenticated visit redirects to login (outbound)

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/agents/create/outbound`

**Observation 1 — Middleware redirect**:
1. Status is 307
2. URL becomes `/auth/login?redirect=%2Fagents%2Fcreate%2Foutbound`

---

### TC-NAV-033: Expired token redirects to login

**Preconditions**: an expired `tone_access_token` cookie is present.

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Redirect + cookie cleared**:
1. URL becomes `/auth/login?redirect=...`
2. The expired cookie is cleared by the login response

---

### TC-NAV-034: Non-member is denied access to create

**Preconditions**: user signed in but not a member of the active org.

**Action**:
1. Visit `/agents/create/inbound`

**Observation 1 — Access denied / redirect**:
1. Either an access-denied state renders OR URL redirects to `/home`
2. No `GET /provider/catalog` requests are recorded

---

### TC-LOADING-043: Slow save disables the create button and shows loading text

**Action**:
1. Fill required fields
2. Click `Create agent` against a deliberately slow `POST /agent/create_agent` (>3s)

**Observation 1 — Button state during request**:
1. Button text changes to `Loading...`
2. Button has `disabled` attribute
3. Clicking the button additional times records zero extra `POST /agent/create_agent` requests

---

### TC-LOADING-044: Slow provider catalog keeps other tabs responsive

**Action**:
1. Visit `/agents/create/inbound/ai` with `GET /provider/catalog` delayed > 3s
2. While loading, click the `Basics` sidebar item

**Observation 1 — Loading visible on AI**:
1. A loading spinner is visible inside the provider dropdown

**Observation 2 — Other tabs unblocked**:
1. The `Basics` step body renders without waiting for the catalog
2. All Basics inputs are interactive

---

### TC-LOADING-045: Prompt text survives a transient network drop

**Action**:
1. Visit `/agents/create/inbound/prompt`
2. Type a long prompt
3. Simulate a network drop
4. Restore the network and click `Create agent`

**Observation 1 — Local state preserved**:
1. The prompt textarea still contains the typed text after the network drop

**Observation 2 — Retry succeeds with full text**:
1. The retried `POST /agent/create_agent` payload contains the full prompt text

---

### TC-EDGE-042: Network failure on save preserves the form

**Action**:
1. Fill required fields
2. Disconnect network
3. Click `Create agent`

**Observation 1 — Generic error toast**:
1. A toast titled `Something went wrong. Please try again.` appears

**Observation 2 — Form preserved**:
1. Every typed value remains
2. URL stays on the create page
3. Re-clicking after restoring the network successfully POSTs

---

### TC-EDGE-047: Name and description are trimmed on save

**Action**:
1. Type ` My Agent ` (with surrounding spaces) into `Name`
2. Type ` description ` into `Description`
3. Click `Create agent`
4. After redirect, reload the edit page

**Observation 1 — Trimmed values persist**:
1. The reloaded agent's `name` equals `My Agent` (no surrounding whitespace)
2. The reloaded agent's `description` equals `description`

> ⚠ Trim location (frontend vs backend) is unverified — assert observable round-trip only.

---

### TC-EDGE-048: Special chars and unicode round-trip without XSS

**Action**:
1. Type `<script>alert(1)</script>` into `Name` and `Description`
2. Type `pass🔥word` and `मेरा एजेंट` into `Prompt`
3. Click `Create agent`
4. Reload the edit page

**Observation 1 — Verbatim round-trip**:
1. All special chars / emoji / unicode appear verbatim in the reloaded fields' `value`s

**Observation 2 — No XSS**:
1. `window.alert` was never invoked
2. The `<script>` text is rendered as text, not parsed as HTML

---

### TC-EDGE-049: Very long name is bounded with feedback

**Action**:
1. Paste a 600-character name into the `Name` field
2. Click `Create agent`

**Observation 1 — Bounded behaviour**:
1. Either the input truncates with a helpful inline message OR the backend rejects with 4xx
2. No client crash
3. The form remains interactive

---

### TC-EDGE-050: Very long prompt persists end to end

**Action**:
1. Paste a 10,000-character prompt
2. Click `Create agent`
3. Reload the edit page

**Observation 1 — Prompt accepts long text**:
1. The textarea contains the full 10k chars before save

**Observation 2 — Round-trips on reload**:
1. After reload, the prompt textarea contains the same 10k chars

---

### TC-EDGE-051: Pasting newlines into name strips them

**Action**:
1. Paste `line1\nline2` into the single-line `Name` input
2. Click `Create agent`

**Observation 1 — Single-line value**:
1. The Name input's `value` contains no `\n`
2. The saved `name` is single-line

---

### TC-A11Y-054: Tab order through Basics reaches every control

**Action**:
1. Visit `/agents/create/inbound/basics`
2. Press `Tab` repeatedly starting from the page body

**Observation 1 — Sequence**:
1. Focus passes through: `Name` → `Description` → `First message` → `End call message` → `Active` toggle
2. No focusable form control is skipped

---

### TC-A11Y-055: Enter on Name input triggers create

**Action**:
1. Visit `/agents/create/inbound`
2. Fill required fields
3. Focus the `Name` input
4. Press `Enter`

**Observation 1 — Create fires**:
1. Exactly one `POST /agent/create_agent` request is recorded (same as clicking `Create agent`)

---

### TC-A11Y-056: Validation error is announced via aria-live

**Action**:
1. Click `Create agent` with `Name` empty

**Observation 1 — Announceable error**:
1. The `Required` helper text is rendered inside an element with `role="alert"` or `aria-live="polite"`
2. The text equals `Required` exactly

---

### TC-A11Y-057: KB upload modal traps focus and restores on close

**Action**:
1. Open the KB Upload modal
2. Press `Tab` repeatedly
3. Press `Escape`

**Observation 1 — Focus trap**:
1. Tabbing cycles only within focusable elements inside the modal

**Observation 2 — Focus restoration**:
1. Escape closes the modal
2. Focus returns to the modal's trigger button

---

### TC-A11Y-058: Phone assign modal traps focus and restores on close

**Action**:
1. Open the Assign Phone modal
2. Tab cycle
3. Press `Escape`

**Observation 1 — Same focus trap behaviour**:
1. Focus stays inside the modal
2. Escape closes the modal and restores focus to the trigger

---

### TC-A11Y-059: Preview modal traps focus and restores on close

**Action**:
1. Click `Preview`
2. Tab cycle inside the modal
3. Press `Escape`

**Observation 1 — Focus trap and restore**:
1. Focus stays inside the Preview modal during cycling
2. Escape closes the modal
3. Focus returns to the `Preview` button

---

### TC-HAPPY-O001: Renders the new-outbound agent header

**Action**:
1. Visit `/agents/create/outbound`

**Observation 1 — Outbound chrome**:
1. Header default name reads `My Outbound Assistant`
2. An `Outbound` badge is visible
3. Header tint reflects the outbound `DIRECTION_STYLES` colour

---

### TC-HAPPY-O002: Outbound create payload carries agent_type=outbound

**Action**:
1. Visit `/agents/create/outbound`
2. Fill required fields with defaults
3. Click `Create agent`

**Observation 1 — Payload field**:
1. `POST /agent/create_agent` body contains `"agent_type": "outbound"`

---

### TC-HAPPY-O003: Outbound exposes the same six steps

**Action**:
1. Visit `/agents/create/outbound`

**Observation 1 — Sidebar parity**:
1. Exactly 6 sidebar items render in the same order as inbound: `Basics`, `Prompt`, `AI`, `Voice`, `Tools & MCP`, `Knowledge & Phone`
2. Each step behaves identically to the inbound flow

---

### TC-FULL-001: Fills every step, saves, reloads and verifies persistence

**Preconditions**:
- User authenticated against a real backend (no mocks)
- Test agent name prefixed `__e2e__` for cleanup
- Helpers from `frontend/e2e/helpers/agentFixtures.ts` available

**Action**:
1. Visit `/agents/create/inbound`
2. **Basics**: fill `name`, `description`, `first message`, `end call message`, toggle `is_active`
3. **Prompt**: fill `system prompt`
4. **AI**: pick LLM provider, model; set temperature via `setSliderByKeyboard`; set `max_tokens`; set `conversation_history_token_limit`
5. **Voice (TTS)**: pick `language`, `provider`, `model`, `voice`, set `speed` via keyboard
6. **Voice (STT)**: pick STT provider, STT model
7. **Tools & MCP**: tick every visible tool; attach the first available MCP server
8. **Knowledge & Phone**: pick the first KB doc; assign the first available phone number
9. Click `Create agent`
10. Wait for redirect to `/agents/edit/inbound/<id>/overview`
11. Reload the edit page
12. Read back every field

**Observation 1 — Create succeeds**:
1. Exactly one `POST /agent/create_agent` request is recorded
2. Success toast appears
3. URL becomes `/agents/edit/inbound/<id>/overview`

**Observation 2 — Persisted scalar fields rehydrate on reload (asserted)**:
1. `name` matches what was typed
2. `description` matches
3. `config.first_message` matches
4. `config.end_call_message` matches
5. `config.system_prompt_template` matches
6. `config.llm_settings.max_tokens` matches
7. `config.conversation_history_token_limit` matches

**Observation 3 — Helpers report gaps without failing**:
1. If the catalog is empty (no providers / tools / MCP / KB / phone numbers seeded), the helper returns `null` / `false`
2. The test logs a `AC-FULL fill report` block and continues

**Observation 4 — Sliders + dependent dropdowns are saved (not re-asserted on reload)**:
1. Temperature slider, speed slider, `is_active` toggle, and provider→model cascades were filled
2. These are NOT re-asserted on reload (catalog ordering varies by environment)
3. Their persistence is implied by the successful round-trip

**Cleanup** (in `try/finally`):
1. `DELETE /agent/delete_agent?agent_id=<id>` for the created `__e2e__` agent
2. Clear cookies

---

## Edge cases

- Empty provider catalogs → SelectInput "No data" popover — see TC-ERROR-011
- Validation error on save → tab jumps to Basics — see TC-VALIDATE-005
- "New tool" while dirty → guarded by unsaved-changes modal (covered in
  `agents-edit.md` TC-NAV-019; same code path)

## Coverage map (which scenarios `TC-FULL-001` transitively exercises)

| Original scenario | Transitively covered by TC-FULL-001? | Notes |
|---|---|---|
| AC-007 First / End call messages render as textareas | yes | filled + reloaded with assertions |
| AC-008 is_active switch toggles | yes (filled, not reloaded) | passed through `toggleActive` |
| AC-009 System prompt persists across tab switches | partially | system prompt is filled and asserted on reload |
| AC-010 Token-limit is numeric | partially | numeric `tokenLimit` saved + re-asserted |
| AC-012 Selecting provider reveals model dropdown | yes | second dropdown is required to fill |
| AC-013 LLM tuning fields update form state | yes | temperature + max_tokens + history limit filled |
| AC-014–AC-016 Voice cascade | yes | language → provider → model → voice |
| AC-018 Speed slider | yes (filled) | driven via keyboard |
| AC-019 STT provider+model | yes | both filled |
| AC-020 Tool checkbox | yes | every visible tile toggled |
| AC-023 MCP server add | yes | first server attached |
| AC-024 KB list toggles upload_ids | yes | first KB doc selected |
| AC-026 Phone Assign modal flow | yes | first available number assigned |

Scenarios still tracked only by their individual test cases (e.g. TC-ERROR-011 "No data" popover, TC-HAPPY-017 voice sample play, TC-HAPPY-021 tool search, TC-HAPPY-025 KB upload modal, TC-HAPPY-028 Edit-from-Preview, TC-ERROR-030 backend 400 error) are *not* exercised by TC-FULL-001.

## Out of scope (covered elsewhere)

- Listing / search / pagination → `agents.md` (list spec).
- Edit flow, sub-modals on edit, delete, guard regression → `agents-edit.md`.
- Backend service validation rules → pytest under `test-cases/`.

## Cleanup

Real-backend writes are namespaced with `__e2e__` in agent names so an
`afterAll` hook can search `/agent/list` for those rows and `DELETE` them.

---

## Scenario → TC ID cross-reference

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| AC-001          | TC-HAPPY-001      | renders the new-inbound agent header                                 |
| AC-002          | TC-HAPPY-002      | sidebar shows the six steps without Review                           |
| AC-003          | TC-HAPPY-003      | header has Back / Preview / Create agent buttons                     |
| AC-004          | TC-HAPPY-004      | Basics step is the default body                                      |
| AC-005          | TC-VALIDATE-005   | name is required and jumps to Basics on save                         |
| AC-006          | TC-HAPPY-006      | description accepts long text                                        |
| AC-007          | TC-HAPPY-007      | conversation messages render as textareas                            |
| AC-008          | TC-HAPPY-008      | is_active switch toggles                                             |
| AC-009          | TC-HAPPY-009      | system prompt persists across tab switches                           |
| AC-010          | TC-VALIDATE-010   | token-limit input is numeric only                                    |
| AC-011          | TC-ERROR-011      | LLM provider shows No data when empty                                |
| AC-012          | TC-HAPPY-012      | selecting LLM provider reveals model dropdown                        |
| AC-013          | TC-HAPPY-013      | LLM tuning fields update form state                                  |
| AC-014          | TC-HAPPY-014      | voice language dropdown loads from API                               |
| AC-015          | TC-HAPPY-015      | picking language refreshes TTS providers                             |
| AC-016          | TC-HAPPY-016      | picking provider+language loads voices                               |
| AC-017          | TC-HAPPY-017      | voice sample play button toggles                                     |
| AC-018          | TC-HAPPY-018      | speed slider is clamped and defaulted                                |
| AC-019          | TC-HAPPY-019      | STT provider+model dropdowns wire together                           |
| AC-020          | TC-HAPPY-020      | tool checkbox toggles tool_ids                                       |
| AC-021          | TC-HAPPY-021      | tool search filters the list                                         |
| AC-022          | TC-HAPPY-022      | New tool navigates when clean                                        |
| AC-023          | TC-HAPPY-023      | MCP server picker adds and removes chips                             |
| AC-024          | TC-HAPPY-024      | KB list loads and toggles upload_ids                                 |
| AC-025          | TC-HAPPY-025      | KB upload modal is enabled in create mode and validates files        |
| AC-026          | TC-HAPPY-026      | Assign phone modal lists numbers for the channel                     |
| AC-027          | TC-HAPPY-027      | Preview modal opens with scrollable Review content                   |
| AC-028          | TC-HAPPY-028      | Edit link in preview jumps to the step                               |
| AC-029          | TC-HAPPY-029      | Create posts the payload and redirects to edit                       |
| AC-030          | TC-ERROR-030      | Create surfaces backend validation errors                            |
| AC-031          | TC-NAV-031        | unauthenticated visit redirects to login                             |
| AC-032          | TC-NAV-032        | unauthenticated outbound visit redirects to login                    |
| AC-033          | TC-NAV-033        | expired token redirects to login                                     |
| AC-034          | TC-NAV-034        | non-member is denied access to create                                |
| AC-035          | TC-ERROR-030      | create 400 keeps the form intact with toast                          |
| AC-036          | TC-ERROR-036      | create 401 surfaces error toast                                      |
| AC-037          | TC-ERROR-037      | create 403 surfaces forbidden toast                                  |
| AC-038          | TC-ERROR-038      | create 409 surfaces duplicate name toast                             |
| AC-039          | TC-ERROR-039      | create 500 surfaces generic error toast                              |
| AC-040          | TC-ERROR-040      | provider catalog 500 falls back gracefully                           |
| AC-041          | TC-ERROR-041      | kb upload 413 surfaces oversize message                              |
| AC-042          | TC-EDGE-042       | network failure on save preserves the form                           |
| AC-043          | TC-LOADING-043    | slow save disables the create button and shows loading text         |
| AC-044          | TC-LOADING-044    | slow provider catalog keeps other tabs responsive                    |
| AC-045          | TC-LOADING-045    | prompt text survives a transient network drop                        |
| AC-046          | TC-VALIDATE-046   | whitespace-only name fails validation                                |
| AC-047          | TC-EDGE-047       | name and description are trimmed on save                             |
| AC-048          | TC-EDGE-048       | special chars and unicode round-trip without xss                     |
| AC-049          | TC-EDGE-049       | very long name is bounded with feedback                              |
| AC-050          | TC-EDGE-050       | very long prompt persists end to end                                 |
| AC-051          | TC-EDGE-051       | pasting newlines into name strips them                               |
| AC-052          | TC-VALIDATE-052   | token-limit field rejects non-numeric input                          |
| AC-053          | TC-VALIDATE-053   | temperature slider clamps to range via keyboard                      |
| AC-054          | TC-A11Y-054       | tab order through Basics reaches every control                       |
| AC-055          | TC-A11Y-055       | enter on name input triggers create                                  |
| AC-056          | TC-A11Y-056       | validation error is announced via aria-live                          |
| AC-057          | TC-A11Y-057       | kb upload modal traps focus and restores on close                    |
| AC-058          | TC-A11Y-058       | phone assign modal traps focus and restores on close                 |
| AC-059          | TC-A11Y-059       | preview modal traps focus and restores on close                      |
| AC-FULL         | TC-FULL-001       | fills every step, saves, reloads and verifies persistence            |
| ACO-001         | TC-HAPPY-O001     | renders the new-outbound agent header                                |
| ACO-002         | TC-HAPPY-O002     | outbound create payload carries agent_type=outbound                  |
| ACO-003         | TC-HAPPY-O003     | outbound exposes the same six steps                                  |
