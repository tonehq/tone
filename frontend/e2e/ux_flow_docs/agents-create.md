# Agents — Create Flow (E2E scenarios)

> Companion to `frontend/e2e/dashboard/agents-create-inbound.spec.ts` and
> `agents-create-outbound.spec.ts`. Each scenario ID below maps to a Playwright
> `test(...)` name so a failing run can be triaged directly back to a scenario.

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

## Scenarios — Inbound (AC-001 … AC-030)

### Page identity

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-001 | Visit `/agents/create/inbound` | Header shows "My Inbound Assistant", "Inbound" badge, "New" badge, inbound DIRECTION_STYLES tint | `renders the new-inbound agent header` |
| AC-002 | Sidebar nav items | Exactly 6 items in order: Basics, Prompt, AI, Voice, Tools & MCP, Knowledge & Phone (Review tab removed) | `sidebar shows the six steps without Review` |
| AC-003 | Header action buttons | Back, Preview, **Create agent** (no Delete in create mode) | `header has Back / Preview / Create agent buttons` |
| AC-004 | Default active step | Basics step body visible | `Basics step is the default body` |

### Basics step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-005 | Clear `name` → click Create | Inline error "Required" + tab jumps to Basics | `name is required and jumps to Basics on save` |
| AC-006 | Type long description | Field accepts up to 500 chars | `description accepts long text` |
| AC-007 | First / End call messages | Render as textareas, accept multi-line text | `conversation messages render as textareas` |
| AC-008 | Toggle is_active switch | Switch flips; payload reflects state | `is_active switch toggles` |

### Prompt step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-009 | Type prompt → switch tab → return | Text persists | `system prompt persists across tab switches` |
| AC-010 | Enter non-numeric token limit | Rejected / coerced to number | `token-limit input is numeric only` |

### AI step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-011 | Empty `/provider/catalog` (mocked) | Provider dropdown shows "No data" popover | `LLM provider shows No data when empty` |
| AC-012 | Pick a provider | Model dropdown loads + appears | `selecting LLM provider reveals model dropdown` |
| AC-013 | Adjust temperature / max_tokens | Values captured to `config.llm_settings` | `LLM tuning fields update form state` |

### Voice step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-014 | Language dropdown opens | Lists languages from API | `voice language dropdown loads from API` |
| AC-015 | Pick language | Provider dropdown queries `/tts/providers?language=` | `picking language refreshes TTS providers` |
| AC-016 | Pick language + provider | Voice picker queries `/tts/voices?provider_id=&language=` | `picking provider+language loads voices` |
| AC-017 | Click play on a voice | Audio toggles play/pause | `voice sample play button toggles` |
| AC-018 | Move speed slider | Value clamps 0.5–2.0, default 1.0 | `speed slider is clamped and defaulted` |
| AC-019 | STT provider/model | Provider list + model dropdown wire together | `STT provider+model dropdowns wire together` |

### Tools & MCP step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-020 | Toggle tool checkbox | Tool ID added/removed from `tool_ids` | `tool checkbox toggles tool_ids` |
| AC-021 | Type into tool search | Visible list filters by name/description | `tool search filters the list` |
| AC-022 | Click "New tool" (clean form) | Navigates to `/tools/create` immediately | `New tool navigates when clean` |
| AC-023 | Add + remove MCP server | Chip appears, remove button works | `MCP server picker adds and removes chips` |

### Knowledge & Phone step

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-024 | KB list renders | Items from `/knowledge-base/list` checkboxes | `KB list loads and toggles upload_ids` |
| AC-025 | Open KB Upload modal in create mode | Modal opens, accepts `pdf/txt/csv/json/docx ≤10 MB`, rejects others/oversize | `KB upload modal is enabled in create mode and validates files` |
| AC-026 | Open Phone Assign modal | Service provider + channel dropdowns populate; numbers list fetched | `Assign phone modal lists numbers for the channel` |

### Preview + Save

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-027 | Click Preview | Modal opens with read-only ReviewStep, scrolls within 85vh | `Preview modal opens with scrollable Review content` |
| AC-028 | Click "Edit" on a review card | Modal closes + tab switches to matching step | `Edit link in preview jumps to the step` |
| AC-029 | Fill required + click Create | `POST /agent/create_agent` fires; success toast; URL becomes `/agents/edit/inbound/{id}` (no unsaved-changes modal) | `Create posts the payload and redirects to edit` |
| AC-030 | Create API returns 400 | Error toast; stay on form; no redirect | `Create surfaces backend validation errors` |

### Comprehensive flow (every field, every step)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-FULL | Fill **every** writable control on every step, save, reload, and verify the persisted values round-trip | All filled values rehydrate after reload; agent is deleted in the same test for cleanup | `fills every step, saves, reloads and verifies persistence` |

AC-FULL exercises the following fields end-to-end. Each row maps a step section to the form field, the path on `AgentFormState`, the helper used in `frontend/e2e/helpers/agentFixtures.ts`, and whether persistence is asserted after reload.

| Step | Field | Path | Helper | Asserted on reload |
|---|---|---|---|---|
| Basics | Agent name | `name` | inline `fill` | yes |
| Basics | Description | `description` | `fillBasicsStep({ description })` | yes |
| Basics | First message | `config.first_message` | `fillBasicsStep({ firstMessage })` | yes |
| Basics | End call message | `config.end_call_message` | `fillBasicsStep({ endCallMessage })` | yes |
| Basics | Active toggle | `is_active` | `fillBasicsStep({ toggleActive: true })` | — (visual, not re-asserted) |
| Prompt | System prompt | `config.system_prompt_template` | `fillPromptStep({ systemPrompt })` | yes |
| AI | LLM provider | `config.llm_settings.provider_id` | `fillAiStep()` | — (catalog-dependent) |
| AI | LLM model | `config.llm_settings.model_id` | `fillAiStep()` | — (catalog-dependent) |
| AI | Temperature (slider) | `config.llm_settings.temperature` | `fillAiStep({ temperatureSteps })` via `setSliderByKeyboard` | — (slider position) |
| AI | Max tokens | `config.llm_settings.max_tokens` | `fillAiStep({ maxTokens })` | yes |
| AI | Conversation history token limit | `config.conversation_history_token_limit` | `fillAiStep({ tokenLimit })` | yes |
| Voice (TTS) | Language | `config.voice_settings.language` | `fillVoiceStep()` | — |
| Voice (TTS) | Provider | `config.voice_settings.provider_id` | `fillVoiceStep()` | — |
| Voice (TTS) | Model | `config.voice_settings.model_id` | `fillVoiceStep()` | — |
| Voice (TTS) | Voice | `config.voice_settings.voice_id` | `fillVoiceStep()` (SearchableSelect) | — |
| Voice (TTS) | Speed (slider) | `config.voice_settings.speed` | `fillVoiceStep()` via `setSliderByKeyboard` | — |
| Voice (STT) | Provider | `config.stt_settings.provider_id` | `fillVoiceStep()` | — |
| Voice (STT) | Model | `config.stt_settings.model` | `fillVoiceStep()` | — |
| Tools & MCP | Tool tiles (every visible) | `tool_ids` | `pickAllTools()` | — |
| Tools & MCP | MCP server | `mcp_server_ids` | `attachFirstMcpServer()` | — |
| Knowledge & Phone | KB document | `upload_ids` | `pickFirstKbDoc()` | — |
| Knowledge & Phone | Phone number | `phone_numbers` | `assignFirstPhoneNumber()` | — |

Notes:

- Helpers are **best-effort**: if the catalog is empty (e.g. no providers seeded, no tools in org), the helper returns `null` / `false` and the test logs the gap instead of failing — see the `console.log('AC-FULL fill report', …)` block.
- Slider values are driven by Radix keyboard semantics (`Home` then `N × ArrowRight`) so the same number of presses yields the same value across environments.
- Sliders, the active toggle, and dependent dropdowns (provider → model) are not re-asserted on reload because the catalog ordering can vary by environment; the spec verifies that the controls saved without error and the agent round-tripped on the server.

## Scenarios — Outbound (ACO-001 … ACO-003)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| ACO-001 | Visit `/agents/create/outbound` | Default name "My Outbound Assistant", outbound badge + tint | `renders the new-outbound agent header` |
| ACO-002 | Create with defaults | Payload sent to `/agent/create_agent` includes `agent_type: 'outbound'` | `outbound create payload carries agent_type=outbound` |
| ACO-003 | Tab parity with inbound | All 6 sidebar items visible + behave identically | `outbound exposes the same six steps` |

## Edge cases

- Empty provider catalogs → SelectInput "No data" popover (covered by AC-011).
- Validation error on save → tab jumps to Basics (covered by AC-005).
- "New tool" while dirty → guarded by unsaved-changes modal (covered in
  `agents-edit.md` AE-019; same code path).

## Coverage map (which scenarios `AC-FULL` transitively exercises)

| Scenario | Transitively covered by AC-FULL? | Notes |
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

Scenarios still tracked only by their individual `test.fixme` placeholders (e.g. AC-011 "No data" popover with an empty catalog, AC-017 voice sample play, AC-021 tool search, AC-025 KB upload modal, AC-028 Edit-from-Preview, AC-030 backend 400 error) are *not* exercised by AC-FULL.

## Out of scope (covered elsewhere)

- Listing / search / pagination → `agents.md` (list spec).
- Edit flow, sub-modals on edit, delete, guard regression → `agents-edit.md`.
- Backend service validation rules → pytest under `test-cases/`.

## Cleanup

Real-backend writes are namespaced with `__e2e__` in agent names so an
`afterAll` hook can search `/agent/list` for those rows and `DELETE` them.

---

## Appended Scenarios (gap-fill, ID prefix continues `AC-`)

These rows extend the original AC coverage with auth, error-state, network, input-edge-case and accessibility scenarios so `/generate-tests` can produce a comprehensive `agents-create-*.spec.ts`. Real-backend conventions apply (`__e2e__` prefix, try/finally cleanup in the same test body); no `page.route` mocks unless the scenario explicitly requires fault injection.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-031 | Visit `/agents/create/inbound` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Fagents%2Fcreate%2Finbound` | `unauthenticated visit redirects to login` |
| AC-032 | Visit `/agents/create/outbound` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Fagents%2Fcreate%2Foutbound` | `unauthenticated outbound visit redirects to login` |
| AC-033 | Visit `/agents/create/inbound` with an expired token | Middleware 307 → `/auth/login?redirect=…`; expired cookie cleared | `expired token redirects to login` |
| AC-034 | Non-member role attempts to load the create page | Access-denied / `/home` redirect; no provider catalog requests fire | `non-member is denied access to create` |

### Backend error states (save flow)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-035 | `POST /agent/create_agent` returns 400 (validation) | Error toast with backend `detail`; form intact; tab does NOT jump unless basics-level | `create 400 keeps the form intact with toast` |
| AC-036 | `POST /agent/create_agent` returns 401 (token expired mid-submit) | Toast `Invalid token` (or `Could not validate credentials`); form intact; no auto-redirect | `create 401 surfaces error toast` |
| AC-037 | `POST /agent/create_agent` returns 403 (member tries owner-only action) | Toast with backend `detail`; form intact; no redirect | `create 403 surfaces forbidden toast` |
| AC-038 | `POST /agent/create_agent` returns 409 (duplicate name) | Toast with backend `detail`; form stays on the current step; Create button re-enabled | `create 409 surfaces duplicate name toast` |
| AC-039 | `POST /agent/create_agent` returns 500 | Generic backend `detail` toast; form intact; Create re-enabled | `create 500 surfaces generic error toast` |
| AC-040 | `GET /provider/catalog` returns 500 | AI step renders empty provider dropdowns; form still saveable when other steps complete (defaults retained) | `provider catalog 500 falls back gracefully` |
| AC-041 | `POST /knowledge-base/upload` returns 413 (file too large) | Modal shows oversize validation message; no upload added; KB list unchanged | `kb upload 413 surfaces oversize message` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-042 | Offline / network failure on Create click | Error toast `Something went wrong. Please try again.`; form preserved with every typed value | `network failure on save preserves the form` |
| AC-043 | Slow `POST /agent/create_agent` (>3s) | Create button shows `Loading...` text + `disabled` attr the whole time; user can't double-submit | `slow save disables the create button and shows loading text` |
| AC-044 | Slow `/provider/catalog` (>3s) | AI step shows a loading spinner inside the provider dropdown without blocking other tabs | `slow provider catalog keeps other tabs responsive` |
| AC-045 | Network drop mid-typing in Prompt step | Local state preserved; subsequent save retries with all typed text intact | `prompt text survives a transient network drop` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-046 | Submit with whitespace-only `name` | Inline "Required" / validation error; no `POST /agent/create_agent` fires; tab jumps to Basics | `whitespace-only name fails validation` |
| AC-047 | Leading/trailing whitespace in `name` and `description` | Trimmed by frontend or backend before persist; reloaded agent shows trimmed values | `name and description are trimmed on save` |
| AC-048 | Special chars (`<script>alert(1)</script>`, emoji, unicode) in name + description + prompt | Accepted; round-trip on reload renders text verbatim; no XSS execution | `special chars and unicode round-trip without xss` |
| AC-049 | Very long name (>500 chars) | Either truncated at the max-length with helpful message or backend rejects with a 4xx; no client crash | `very long name is bounded with feedback` |
| AC-050 | Very long prompt (>10k chars) | Prompt textarea accepts the value; save succeeds; reload reproduces the full text | `very long prompt persists end to end` |
| AC-051 | Paste multiline content into the single-line `name` input | Newlines stripped before save; saved name is single-line | `pasting newlines into name strips them` |
| AC-052 | Numeric token limit accepts only digits | Non-digit input rejected/coerced; payload's `conversation_history_token_limit` is a number | `token-limit field rejects non-numeric input` |
| AC-053 | Temperature slider keyboard edge — Home then End | Value clamps to min/max of the slider; payload reflects the clamped value | `temperature slider clamps to range via keyboard` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AC-054 | Tab order through Basics step | Name → Description → First message → End call message → Active toggle | `tab order through Basics reaches every control` |
| AC-055 | Press Enter on the Name input while focused | Triggers Create (saves the form) — matches the primary action of the editor | `enter on name input triggers create` |
| AC-056 | Validation error message has `role="alert"` or aria-live | Screen readers announce "Required" without manual focus | `validation error is announced via aria-live` |
| AC-057 | KB Upload modal traps focus and restores it | Focus moves into the modal; Tab cycles; close restores focus to the trigger button | `kb upload modal traps focus and restores on close` |
| AC-058 | Phone Assign modal traps focus and restores it | Same behaviour for the phone assign drawer/modal | `phone assign modal traps focus and restores on close` |
| AC-059 | Preview modal traps focus and restores it | Focus moves into the modal; Escape closes; focus returns to Preview button | `preview modal traps focus and restores on close` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| AC-031..034 | (new) | Auth gating + role gating were not previously enumerated |
| AC-035..041 | AC-030 (create 400) | Adds 401/403/409/500 and provider-catalog / KB-upload error paths |
| AC-042..045 | (new) | Network resilience for save + catalog + KB upload |
| AC-046..053 | AC-005, AC-006, AC-010 | Promotes basic validation into edge-case sweep (whitespace, trim, XSS, long input, slider clamp) |
| AC-054..059 | Accessibility checklist | Promotes existing a11y bullets into runnable scenarios |
