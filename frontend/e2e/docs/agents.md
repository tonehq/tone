# Feature Doc: Agents

Feature documentation for the agents list page and agent creation/edit flow. Used by
`/generate-tests agents` to ensure all user cases are covered alongside the component
source analysis.

---

## Test approach: Real API for CRUD

Agent e2e tests use the **original/real backend API** for every CRUD operation. Do not mock
`/agent/get_all_agents` or `/agent/upsert_agent` for create, read (list), update, or delete flows —
so that data is persisted in the DB and tests validate the full stack.

- **Create (inbound/outbound)**: Save triggers real POST `upsert_agent`; redirect to `/agents` then real GET `get_all_agents`; assert created agent appears in list.
- **Read (list)**: At least one test loads the list from the real API (no mock) and asserts the table is visible.
- **Update (edit)**: At least one test loads agent from real API, clicks Save (real POST `upsert_agent`), asserts redirect to `/agents`.
- **Delete**: Uses real DELETE `/agent/delete_agent?agent_id=N`; after delete, agent list is re-fetched.

**Prerequisites**: Running backend and DB; `NEXT_PUBLIC_BACKEND_URL` set. Tests that need deterministic data (e.g. empty state, loading state, error state) may still mock the API only for those scenarios.

**Important: Mocked save tests** — When mocking `upsert_agent` AND asserting redirect to `/agents`, you MUST also mock `get_all_agents`. After save, `router.push('/agents')` loads the agents list page which fetches from the real API. Without the mock, the navigation hangs waiting for the API response and `toHaveURL` times out. Only the "real API" integration tests should skip the `get_all_agents` mock. Place the `get_all_agents` mock inside individual mocked test bodies, NOT in `beforeEach` (otherwise it breaks real API tests in the same file).

**Important: `unrouteAll` behavior** — Use `page.unrouteAll({ behavior: 'ignoreErrors' })` in cleanup, not `{ behavior: 'wait' }`, to prevent `beforeEach` timeouts when a previous test left pending routes.

---

## Page

- **Route (list)**: `/agents`
- **Route (create inbound)**: `/agents/create/inbound`
- **Route (create outbound)**: `/agents/create/outbound`
- **Route (edit)**: `/agents/edit/:type/:id` (e.g., `/agents/edit/inbound/42`)
- **Components**:
  - List: `src/components/agents/AgentListPage.tsx`
  - Create modal: `src/components/agents/CreateAgentModal.tsx`
  - Agent type badge: `src/components/agents/AgentTypeBadge.tsx`
  - Action menu: `src/components/agents/AgentActionMenu.tsx`
  - Create inbound page: `src/app/(dashboard)/agents/create/inbound/page.tsx`
  - Create outbound page: `src/app/(dashboard)/agents/create/outbound/page.tsx`
  - Edit page: `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx`
  - Form page wrapper: `src/components/agents/AgentFormPage.tsx`
  - Form tabs: `src/components/agents/agent-form/` (GeneralTab, VoiceTab, CallConfigurationTab, promptPage)
  - Voice select: `src/components/agents/agent-form/VoiceSelect.tsx`
  - Dynamic fields: `src/components/agents/agent-form/DynamicProviderFields.tsx`
  - Assign phone number modal: `src/components/agents/AssignPhoneNumberModal.tsx`
  - Form utils: `src/utils/agentFormUtils.ts`
  - Form types: `src/components/agents/agent-form/types.ts`
  - Agent types: `src/types/agent.ts`
  - Agent service: `src/services/agentsService.ts`
  - Voice service: `src/services/voiceService.ts`
  - Agents atom: `src/atoms/AgentsAtom.tsx`
  - Provider atom: `src/atoms/ProviderAtom.tsx`
  - Validators: `src/utils/validators.ts`
- **Auth required**: yes (redirects to `/auth/login?redirect=<path>` without `tone_access_token` cookie)

---

## Architecture

### State flow

```
AgentListPage
  └─ useAtom(agentsAtom)         → reads agent list
  └─ useAtom(fetchAgentList)     → write-only atom, calls getAgents() service
  └─ useAtom(deleteAgentAtom)    → write-only atom, calls deleteAgent() then re-fetches list

AgentFormPage (create/edit)
  └─ useState(formData)         → local AgentFormState (not Jotai)
  └─ useAtom(loadableProvidersAtom) → async providers list (LLM/TTS/STT)
  └─ getAgent() service          → fetches single agent for edit mode
  └─ upsertAgent() service       → creates/updates agent
  └─ deleteAgent() service       → deletes agent
```

### Form validation flow

The agent form uses **react-hook-form** with inline `rules` prop (not Zod schemas). Validation is triggered on save via imperative `trigger()` calls through ref handles:

```
AgentFormPage.handleSave()
  └─ generalHandle.current?.trigger()   → validates GeneralTab (agent name required)
  └─ llmHandle.current?.trigger()       → validates LLM DynamicProviderFields
  └─ ttsHandle.current?.trigger()       → validates TTS DynamicProviderFields
  └─ sttHandle.current?.trigger()       → validates STT DynamicProviderFields
  └─ if all valid → formStateToUpsertPayload() → upsertAgent()
```

Each tab exposes a `{ trigger: () => Promise<boolean> }` handle via callback refs:

- `GeneralTab` → `onGeneralValidityChange` (validates `name` field)
- `DynamicProviderFields` → `onLlmValidityChange` / `onTtsValidityChange` / `onSttValidityChange` (validates provider-specific required fields using `buildFieldRules()` from `src/utils/validators.ts`)

**Important**: `FormTextInput` in agent forms auto-renders error messages from `fieldState.error.message`. Do NOT also pass `error` to `FormRow` — this causes duplicate error messages. `FormRow` in `GeneralTab` omits the `error` prop for `FormTextInput` children.

### Provider-driven dynamic fields

`DynamicProviderFields` renders form fields dynamically based on `ServiceProvider.meta_data_schema`:

| `data_type`                 | Rendered as                                                   |
| --------------------------- | ------------------------------------------------------------- |
| `string`                    | `FormTextInput` (text or URL)                                 |
| `float` / `int` / `integer` | `TextInput` (type="number") via `Controller`                  |
| `boolean`                   | `RadioGroupField` (Yes/No) via `Controller`                   |
| `date`                      | `FormTextInput` (type="date")                                 |
| `datetime`                  | `FormTextInput` (type="datetime-local")                       |
| `date range`                | `DateRangeField` (two date inputs) via `Controller`           |
| `list`                      | `MultiSelectField` (checkboxes or tag input) via `Controller` |
| `rangepicker`               | `Slider` via `Controller`                                     |
| Has `values[]` array        | `FormSelectInput` (dropdown)                                  |

Validation rules are built by `buildFieldRules(field)` from `src/utils/validators.ts`, which reads `field.required`, `field.data_type`, `field.format`, and `field.min`/`field.max`.

---

## User Stories

### US-1: View agent list

**As a** logged-in user, **I want to** see a list of all my agents in a table, **so that** I can manage my voice agents.

**Acceptance criteria**:

- [ ] Shows "Agents" heading (h1, text-2xl)
- [ ] Shows a "Create Agent" button with a Plus icon
- [ ] Displays a `CustomTable` with 5 columns: Agent Name, Phone Number, Last Edited, Agent Type, Actions (empty title)
- [ ] Agent Name and Last Edited columns are sortable (`sorter: true`)
- [ ] Table supports search with `searchable` prop and placeholder "Search agents..."
- [ ] Shows loading state while agents are being fetched
- [ ] Shows custom empty state with "No agents yet" text and "Create your first agent" button
- [ ] Agent type column shows `AgentTypeBadge`: emerald "Inbound" or violet "Outbound" with phone icons
- [ ] Last Edited column formats dates using `formatDate()` from `@/utils/date`, or shows "-"
- [ ] Phone Number column shows comma-joined phone numbers from `phone_number` array, or "-"
- [ ] Actions column shows `AgentActionMenu` (3-dot dropdown with Edit and Delete)
- [ ] Clicking a table row navigates to edit page (via `onRowClick`)
- [ ] Pagination is built into `CustomTable`
- [ ] Table takes only its content height — no empty space below rows when data is sparse

### US-2: Create a new agent (modal selection)

**As a** logged-in user, **I want to** choose between Inbound and Outbound agent types, **so that** I can create the right kind of agent.

**Acceptance criteria**:

- [ ] Clicking "Create Agent" button opens a `CustomModal`
- [ ] Modal title says "Choose type of agent"
- [ ] Modal hides footer (`hideFooter`)
- [ ] Modal shows two cards in a 2-column grid: "Outbound" and "Inbound"
- [ ] Outbound card shows: `PhoneOutgoing` icon, title "Outbound", description "Automate calls within workflows using Zapier, REST API, or HighLevel"
- [ ] Inbound card shows: `PhoneIncoming` icon, title "Inbound", description "Manage incoming calls via phone, Zapier, REST API, or HighLevel"
- [ ] Cards are `CustomButton` with hover effect (purple border, shadow, slight lift)
- [ ] Clicking a card closes the modal and navigates to `/agents/create/inbound` or `/agents/create/outbound`
- [ ] Modal has a close (X) button that closes the modal
- [ ] Widget and Chat types are not available (only inbound/outbound handled in `handleSelectAgent`)

### US-3: Create/Edit agent — page layout

**As a** logged-in user, **I want to** see a consistent layout when creating or editing an agent.

**Acceptance criteria**:

- [ ] Page has 4 stacked sections: status banner, breadcrumb bar, agent identity header, tabs + content
- [ ] **Status banner** (top):
  - No phone: amber background, `AlertTriangle` icon, "No phone number — Your agent can't receive/make calls yet."
  - Has phone: emerald background, `CheckCircle2` icon, "Phone assigned: +1234567890"
- [ ] **Breadcrumb bar**: "Agents" link (navigates to `/agents`) > `ChevronRight` > agent name (truncated at 240px)
  - Contains "Test Agent" button (with `Phone` icon, not yet implemented)
  - Contains "Save Changes" button (with `Save` icon, shows `Loader2` spinner + "Saving..." when saving)
- [ ] **Agent identity header**: avatar initial (first char of name, fallback "A"), agent name (h1), `AgentTypeBadge`, phone number badge (if assigned)
- [ ] **Tabs**: 5 tabs via `CustomTab`: General, Voice, Prompt, Call Configuration, Assign Number
  - Tab icons: `Settings`, `Volume2`, `MessageSquare`, `PhoneCall`, `PhoneForwarded`
- [ ] Loading state shows centered `Loader2` spinner when fetching agent data in edit mode

### US-4: General Tab

**As a** logged-in user, **I want to** configure basic agent settings in the General tab.

**Acceptance criteria**:

The General tab has 4 `SectionCard` sections:

#### Agent Identity section (`Bot` icon):

- [ ] Agent Name — `FormTextInput` (RHF controlled), required, validated with `rules={{ required: 'Please enter a name for your agent' }}`
- [ ] Agent Description — `TextAreaField`, optional, 3 rows

#### AI Configuration section (`Brain` icon):

- [ ] AI Model — `SelectInput` dropdown, options from `llmProviders` (loaded from `loadableProvidersAtom`)
- [ ] Model — `SelectInput` dropdown, appears only when selected LLM provider has `models[]` array; options from provider's models
- [ ] Dynamic LLM Fields — `DynamicProviderFields` renders only when selected provider has `meta_data_schema[]`
- [ ] Use Realistic Filler Words — `Switch` toggle, default off

#### Messages section (`MessageSquare` icon):

- [ ] First Message — `TextAreaField`, optional, 3 rows
- [ ] End Call Message — `TextAreaField`, optional, 3 rows

#### Advanced Settings section (`Settings2` icon):

- [ ] Custom Vocabulary — chip-based input (type text + click "Add" or press Enter to add, click X badge button to remove)
- [ ] Filter Words — chip-based input (same behavior as custom vocabulary)

#### Danger Zone section (`Trash2` icon, `variant="danger"`):

- [ ] "Delete Agent" button (type="danger") — calls `onDeleteAgent` which opens a `CustomModal` confirmation dialog
- [ ] Delete description: "Permanently remove this agent and all associated data."

### US-5: Voice Tab

**As a** logged-in user, **I want to** configure voice settings for my agent.

**Acceptance criteria**:

The Voice tab has 3 `SectionCard` sections:

#### Text-to-Speech section (`Volume2` icon):

- [ ] Voice Provider — `SelectInput` dropdown, options from `ttsProviders`
- [ ] Language — `SelectInput` dropdown, appears only when voice provider is selected; options are languages filtered from available voices (fetched via `getVoicesByProvider()` service)
- [ ] Voice — `VoiceSelect` (custom searchable select), appears only when both voice provider and language are selected; shows voice name, avatar, gender badge, description; filterable by name/gender/accent/description
- [ ] Dynamic TTS Fields — `DynamicProviderFields`, appears when TTS provider has `meta_data_schema[]` (excludes `language` and `speed` fields)
- [ ] Voice Speed — `Slider` (0-100), default 50, labels: Slow / Normal / Fast

#### Speech-to-Text section (`Mic` icon):

- [ ] STT Provider — `SelectInput` dropdown, options from `sttProviders`
- [ ] Dynamic STT Fields — `DynamicProviderFields`, appears when STT provider has `meta_data_schema[]` (excludes `language` field)
- [ ] Speech Recognition — two `CustomButton` cards with `role="radio"`:
  - "Faster" — "Lower quality, suitable for most use cases" (value: `fast`)
  - "High Accuracy" — "Slower, for high accuracy use cases" (value: `accurate`)
  - Active card: `border-primary bg-primary/10`

#### Response Timing section (`Gauge` icon):

- [ ] Patience Level — three `CustomButton` cards with `role="radio"`:
  - Low (~1 sec), Medium (~3 sec), High (~5 sec)
  - Default: `low`

### US-6: Prompt Tab

**As a** logged-in user, **I want to** write a system prompt for my agent using a rich text editor.

**Acceptance criteria**:

- [ ] Shows description text: "Below is an AI-generated job description. You can edit it or clear it."
- [ ] Rich text editor uses TipTap (`@tiptap/react`) with extensions: StarterKit, Heading (h1-h3), Underline, Link, TextAlign
- [ ] Toolbar contains:
  - Heading dropdown (`SelectInput`): Normal, Heading 1, Heading 2, Heading 3
  - Bold, Italic, Underline buttons (toggle state)
  - Bullet List button
  - Left, Center, Right alignment buttons
  - "Clear all" button (destructive, clears editor content)
- [ ] Editor content syncs to `formData.voicePrompting` via `onUpdate` callback
- [ ] Editor minimum height: 400px

### US-7: Call Configuration Tab

**As a** logged-in user, **I want to** configure call recording and transcription settings.

**Acceptance criteria**:

#### Call Settings section (`Phone` icon):

- [ ] Call Recording — `Switch` toggle, default off. Description: "Enable recording of all calls for review."
- [ ] Call Transcription — `Switch` toggle, default off. Description: "Automatically transcribe all calls to text."

### US-8: Assign Number Tab

**As a** logged-in user, **I want to** assign and manage phone numbers for my agent.

**Acceptance criteria**:

- [ ] Shows section header: "Phone Numbers" with description "Manage phone numbers assigned to this agent."
- [ ] "Assign Number" button appears only in edit mode (`isEditMode`)
- [ ] Empty state (no phones): shows "No phone numbers assigned" with contextual help text
  - Edit mode: 'Click "Assign Number" above to add one.'
  - Create mode: "Save the agent first to assign phone numbers."
- [ ] Assigned phones listed with: phone icon (emerald), phone number, type label, "Unassign" button
- [ ] Clicking "Assign Number" opens `AssignPhoneNumberModal`
- [ ] Clicking "Unassign" opens a `CustomModal` confirmation: "Are you sure you want to unassign {number}?"
- [ ] Assign calls POST `/agent_channel_phone_number/upsert_channel_phone_number` with Twilio channel info
- [ ] Unassign calls POST `/agent_channel_phone_number/detach_channel_phone_number`

### US-9: Save agent

**As a** logged-in user, **I want to** save my agent configuration.

**Acceptance criteria**:

- [ ] "Save Changes" button triggers validation on all tabs (General + dynamic provider fields)
- [ ] If validation fails (any `trigger()` returns false), save is aborted — no API call
- [ ] If validation passes, calls `upsertAgent()` with payload from `formStateToUpsertPayload()`
- [ ] Create mode (no `agentId`): on success, shows toast "Agent created successfully" and redirects to `/agents`
- [ ] Edit mode (has `agentId`): on success, shows toast "Agent saved successfully" and stays on page
- [ ] On API error: calls `handleApiError(error)`, resets saving state, stays on page
- [ ] Button shows "Saving..." text with spinner while saving, is disabled

### US-10: Delete agent

**As a** logged-in user, **I want to** delete an agent.

**Acceptance criteria**:

#### From agent list:

- [ ] Action menu shows "Delete" option
- [ ] Clicking Delete triggers `AgentActionMenu` which uses `ActionMenu` with built-in `CustomModal` confirmation
- [ ] Delete title: "Delete Agent", description: "Are you sure you want to delete this agent? This action cannot be undone."
- [ ] Confirming calls `deleteAgentAtom` which: calls `deleteAgent(agentId)` API, then re-fetches list
- [ ] On success: shows toast "Agent deleted successfully"
- [ ] On API error: calls `handleApiError(error)`

#### From agent form page:

- [ ] "Delete Agent" button in General tab's Danger Zone section
- [ ] Opens `CustomModal` confirmation: title "Delete Agent", description about erasing data
- [ ] Confirming calls `deleteAgent()` service if in edit mode, then navigates to `/agents`
- [ ] Create mode: just navigates to `/agents` (no API call)
- [ ] Shows loading state on confirm button while deleting

### US-11: Auth protection

**As the** system, **I want to** redirect unauthenticated users to the login page, **so that** only logged-in users can access agent pages.

**Acceptance criteria**:

- [ ] Redirects to `/auth/login?redirect=<encoded-path>` when no `tone_access_token` cookie
- [ ] All agent routes are protected: `/agents`, `/agents/create/inbound`, `/agents/create/outbound`, `/agents/edit/:type/:id`
- [ ] After login, 4 cookies are set: `tone_access_token`, `org_tenant_id`, `login_data`, `user_id`

---

## UI Elements

### Agent List Page (`/agents`)

| Element             | Type                     | Content / Label                                    | Behavior                                        |
| ------------------- | ------------------------ | -------------------------------------------------- | ----------------------------------------------- |
| Page heading        | h1                       | "Agents"                                           | Static text (text-2xl font-semibold)            |
| Create Agent button | `CustomButton` (primary) | "Create Agent" (with `Plus` icon)                  | Opens CreateAgentModal                          |
| CustomTable         | table                    | Agent rows                                         | 5 columns, search, sort, pagination, row click  |
| Agent Name column   | column                   | "Agent Name"                                       | Sortable, displays agent name                   |
| Phone Number column | column                   | "Phone Number"                                     | Comma-joined from `phone_number[]` array or "-" |
| Last Edited column  | column                   | "Last Edited"                                      | Sortable, `formatDate()` or "-"                 |
| Agent Type column   | column                   | "Agent Type"                                       | `AgentTypeBadge` component                      |
| Actions column      | column                   | "" (no title)                                      | `AgentActionMenu` (right-aligned)               |
| Search input        | text field               | placeholder: "Search agents..."                    | Built-in `CustomTable` search                   |
| Empty state         | div                      | "No agents yet" + "Create your first agent" button | Shown when `dataSource` is empty                |

### Agent Type Badge

| Agent Type | Colors                 | Icon            |
| ---------- | ---------------------- | --------------- |
| Inbound    | emerald border/bg/text | `PhoneIncoming` |
| Outbound   | violet border/bg/text  | `PhoneOutgoing` |

### Create Agent Modal

| Element       | Type                     | Content / Label                                 | Behavior                               |
| ------------- | ------------------------ | ----------------------------------------------- | -------------------------------------- |
| Modal         | `CustomModal`            | title: "Choose type of agent", `hideFooter`     | —                                      |
| Outbound card | `CustomButton` (default) | `PhoneOutgoing` icon + "Outbound" + description | Navigates to `/agents/create/outbound` |
| Inbound card  | `CustomButton` (default) | `PhoneIncoming` icon + "Inbound" + description  | Navigates to `/agents/create/inbound`  |

### Agent Form Page (create/edit)

| Element             | Type                     | Content / Label                                    | Behavior                                |
| ------------------- | ------------------------ | -------------------------------------------------- | --------------------------------------- |
| Status banner       | div                      | Phone status message                               | Amber (no phone) or emerald (has phone) |
| Breadcrumb: Agents  | `CustomButton` (link)    | "Agents"                                           | Navigates to `/agents`                  |
| Breadcrumb: name    | span                     | Agent name (truncated 240px)                       | Display only                            |
| Test Agent button   | `CustomButton` (default) | "Test Agent" (with `Phone` icon)                   | Not yet implemented                     |
| Save Changes button | `CustomButton` (primary) | "Save Changes" / "Saving..."                       | Validates then upserts                  |
| Agent avatar        | div                      | First char of name                                 | Gradient bg with primary colors         |
| Agent name          | h1                       | `formData.name` or "Untitled Agent"                | Reflects current name field             |
| Type badge          | `AgentTypeBadge`         | "Inbound" or "Outbound"                            | Display only                            |
| Phone badge         | span                     | Phone number + count                               | Only when phones assigned               |
| Tabs                | `CustomTab`              | General, Voice, Prompt, Call Config, Assign Number | Switches tab content                    |
| Delete modal        | `CustomModal`            | "Delete Agent" confirmation                        | `confirmType="danger"`                  |
| Unassign modal      | `CustomModal`            | "Unassign Phone Number" confirmation               | `confirmType="danger"`                  |

---

## Navigation

| Trigger                          | Destination                       | Condition                        |
| -------------------------------- | --------------------------------- | -------------------------------- |
| Click "Create Agent" button      | Opens CreateAgentModal            | Always                           |
| Click Outbound card (modal)      | `/agents/create/outbound`         | Modal closes first               |
| Click Inbound card (modal)       | `/agents/create/inbound`          | Modal closes first               |
| Click close button (modal)       | Closes modal (stays on `/agents`) | Always                           |
| Click agent row in table         | `/agents/edit/:type/:id`          | Agent has valid id               |
| Click "Edit" in action menu      | `/agents/edit/:type/:id`          | Agent has valid id               |
| Click "Agents" breadcrumb        | `/agents`                         | Always                           |
| Save Changes (success, create)   | `/agents`                         | API call succeeds, not edit mode |
| Save Changes (success, edit)     | Stays on page                     | API call succeeds, is edit mode  |
| Delete Agent (confirmed, edit)   | `/agents`                         | Calls delete API then navigates  |
| Delete Agent (confirmed, create) | `/agents`                         | Just navigates (no API call)     |
| No auth cookie                   | `/auth/login?redirect=<path>`     | Middleware redirect              |

---

## API Contracts

| Endpoint                                            | Method | Request                                  | Success Response                 | Error Response      |
| --------------------------------------------------- | ------ | ---------------------------------------- | -------------------------------- | ------------------- |
| `/agent/get_all_agents`                             | GET    | (none)                                   | `Agent[]` or `{ data: Agent[] }` | `{ detail: "..." }` |
| `/agent/get_all_agents?agent_id=N`                  | GET    | query param `agent_id`                   | `Agent[]` (single item)          | `{ detail: "..." }` |
| `/agent/upsert_agent`                               | POST   | See payload shape below                  | `Agent`                          | `{ detail: "..." }` |
| `/agent/delete_agent?agent_id=N`                    | DELETE | query param `agent_id`                   | —                                | `{ detail: "..." }` |
| `/agent_channel_phone_number/upsert_channel_phone_number` | POST   | Phone number assignment payload          | —                                | `{ detail: "..." }` |
| `/agent_channel_phone_number/detach_channel_phone_number` | POST   | `{ channel_id, phone_number, agent_id }` | —                                | `{ detail: "..." }` |
| Voice service: provider-specific                    | GET    | provider id                              | `{ voices: VoiceItem[] }`        | `{ detail: "..." }` |

### Agent response shape (from API)

```json
{
  "id": 42,
  "uuid": "abc-123",
  "name": "My Inbound Assistant",
  "description": "",
  "agent_type": "inbound",
  "phone_number": [{ "type": "twilio", "no": "+1234567890" }],
  "is_public": false,
  "tags": {},
  "total_calls": 0,
  "total_minutes": 0,
  "average_rating": 0,
  "first_message": "",
  "end_call_message": "",
  "system_prompt": "",
  "custom_vocabulary": null,
  "filter_words": null,
  "realistic_filler_words": null,
  "language": "en",
  "voice_speed": "50",
  "patience_level": "low",
  "speech_recognition": "fast",
  "call_recording": null,
  "call_transcription": null,
  "llm_service_id": 1,
  "tts_service_id": 2,
  "stt_service_id": 3,
  "llm_model_id": null,
  "tts_model_id": null,
  "stt_model_id": null,
  "llm_meta_data": {},
  "tts_meta_data": { "voice_id": "abc123" },
  "stt_meta_data": {},
  "channels": [{ "id": 1, "type": "twilio", "meta_data": { "account_sid": "..." } }],
  "status": "active",
  "created_at": 1708900000,
  "updated_at": 1708900000
}
```

### Upsert payload shape (form → API via `formStateToUpsertPayload`)

```json
{
  "name": "My Inbound Assistant",
  "description": null,
  "agent_type": "inbound",
  "first_message": null,
  "end_call_message": null,
  "system_prompt": null,
  "custom_vocabulary": null,
  "filter_words": "[\"word1\",\"word2\"]",
  "realistic_filler_words": false,
  "language": "en",
  "voice_speed": 50,
  "patience_level": "low",
  "speech_recognition": "fast",
  "call_recording": false,
  "call_transcription": false,
  "llm_service_id": 1,
  "tts_service_id": 2,
  "stt_service_id": 3,
  "voice_id": null,
  "channel": { "type": "TWILIO" },
  "llm_meta_data": null,
  "tts_meta_data": { "voice_id": "abc123" },
  "stt_meta_data": null,
  "id": 42
}
```

**Key differences from `AgentFormState`**:

- `aiModel` → `llm_service_id`, `voiceProvider` → `tts_service_id`, `sttProvider` → `stt_service_id`
- `voicePrompting` → `system_prompt`
- `customVocabulary` array → `custom_vocabulary` JSON string
- `filterWords` array → `filter_words` JSON string
- `id` included only for updates

### Phone number assignment payload

```json
{
  "phone_number": [{ "type": "twilio", "no": "+1234567890" }],
  "phone_number_sid": "ACXXXXXXX",
  "phone_number_auth_token": "token",
  "provider": "twilio",
  "channel_id": 1,
  "agent_id": 42,
  "country_code": "+1",
  "number_type": "international",
  "capabilities": { "voice": true, "sms": false, "mms": true },
  "status": "active"
}
```

---

## Edge Cases

### List page

- [ ] Empty agent list — CustomTable shows empty state with "No agents yet" and "Create your first agent" button
- [ ] API returns object `{ data: [...] }` instead of array — handled in `fetchAgentList` atom
- [ ] API returns empty array — handled in atom, sets empty list
- [ ] Network error fetching agents — error logged to console, loader stops
- [ ] Agent with no phone number — phone column shows "-"
- [ ] Agent with no `agent_type` — defaults to "inbound" in edit navigation (`(row.agent_type ?? 'inbound')`)
- [ ] Agent with no `updated_at` — Last Edited shows "-"
- [ ] Agent with no `id` — edit click does nothing (`if (!row.id) return`)
- [ ] Double-fetch prevention — `hasFetchedRef` prevents duplicate API calls on mount

### Form page

- [ ] Upsert API failure — calls `handleApiError(error)`, saving state resets, stays on page
- [ ] Custom vocabulary as string from API (JSON-encoded) — `parseStringArray` handles it
- [ ] Boolean fields as strings from API ("true"/"false") — `parseBoolean` handles it
- [ ] Save with all default values — valid payload, `name` is only validated required field
- [ ] Agent name reflected in breadcrumb and header — changes as user types (via `onValueChange`)
- [ ] Empty agent name — breadcrumb/header shows "Untitled Agent"
- [ ] Provider not loaded yet — `loadableProvidersAtom` shows empty array while loading
- [ ] Provider has no models — model dropdown not rendered
- [ ] Provider has no meta_data_schema — dynamic fields not rendered
- [ ] Voice provider change — resets `ttsMetaData` and `language` to empty
- [ ] STT provider change — resets `sttMetaData` to empty
- [ ] LLM provider change — resets `llmMetaData` to empty
- [ ] Voice fetch failure — `setVoices([])`, calls `handleApiError(error)`, has abort cleanup
- [ ] Language change — resets `voice_id` in `ttsMetaData`
- [ ] No voices for selected language — voice list empty
- [ ] Edit mode agent not found — shows error toast "Agent not found"
- [ ] Delete in create mode — no API call, just navigates to `/agents`

### Delete

- [ ] Delete from list — calls `deleteAgentAtom` which deletes then re-fetches
- [ ] Delete from form (edit mode) — calls `deleteAgent()` then navigates
- [ ] Delete from form (create mode) — just navigates, no API call
- [ ] Delete confirmation cancelled — stays on page, no action

### Phone numbers

- [ ] Assign in create mode — "Assign Number" button hidden (only shown in edit mode)
- [ ] Empty phones list — shows contextual message based on edit/create mode
- [ ] Assign failure — calls `handleApiError(error)`, re-throws error
- [ ] Unassign failure — calls `handleApiError(error)`
- [ ] Multiple phones — listed individually with unassign button each

---

## Business Rules

- Agent types are limited to `'inbound'` and `'outbound'` (widget and chat exist in `AgentType` but are not selectable)
- Default agent names differ by type: "My Inbound Assistant" vs "My Outbound Assistant"
- Agent form state defaults: `src/utils/agentFormUtils.ts` → `defaultFormState(agentType)`
- AI Model, Voice Provider, STT Provider are nullable (`number | null`) — refer to provider service IDs, not model names
- Voice speed range is 0-100, default 50
- Patience level options: low (~1s), medium (~3s), high (~5s)
- Speech recognition options: fast, accurate
- Call recording and transcription default to false
- `custom_vocabulary` and `filter_words` are stored as JSON strings in the API, arrays in form state
- Upsert with an `id` field = update; without = create
- Edit URL pattern: `/agents/edit/:type/:id` — type is lowercased from `agent_type`
- All API calls go through `src/utils/axios.ts` which injects `tenant_id` and `Authorization` headers
- The `fetchAgentList` Jotai atom handles both array and `{ data: [] }` response shapes
- Form state uses camelCase; API uses snake_case — conversion handled by `agentFormUtils.ts`
- Provider data (LLM/TTS/STT) is loaded from `loadableProvidersAtom` (Jotai async atom)
- Voice list is fetched per-provider via `getVoicesByProvider()` — not cached across provider switches
- Tab layout: General, Voice, Prompt, Call Configuration, Assign Number (same for inbound and outbound)
- Create mode success redirects to `/agents`; edit mode success stays on page
- Delete from list re-fetches agent list after deletion; delete from form navigates away
- Phone number assignment uses Twilio channel info from `formData.channels`
- `channel` field in upsert payload is always `{ type: "TWILIO" }`

---

## Accessibility Requirements

- [ ] "Create Agent" button is a proper `CustomButton` element (renders as `<button>`)
- [ ] CreateAgentModal uses `CustomModal` (renders shadcn `Dialog` with focus trapping, aria-modal)
- [ ] Agent type cards in modal use `CustomButton` — proper button semantics
- [ ] `AgentActionMenu` uses `ActionMenu` shared component (dropdown menu with keyboard navigation)
- [ ] CustomTable has built-in keyboard navigation
- [ ] Tab components use `CustomTab` (renders Radix-based tabs with `role="tablist"` / `role="tabpanel"`)
- [ ] Form inputs use `FormTextInput` (RHF Controller wrapper) in agent form — error messages auto-derived from `fieldState.error.message` as `helperText`
- [ ] `FormRow` in GeneralTab does NOT pass `error` prop when child is `FormTextInput` (to avoid duplicate error messages)
- [ ] Speech Recognition and Patience Level cards use `role="radio"` + `aria-checked` within `role="radiogroup"` containers
- [ ] Toggle switches use shadcn `Switch` component (accessible by default)
- [ ] "Agents" breadcrumb is a `CustomButton` (type="link") — proper button semantics
- [ ] "Save Changes" button has `loading` prop which renders `disabled` attribute and spinner
- [ ] Agent Name heading in FormRow renders as `<h3>` with text "Agent Name\*" (asterisk in child `<span>`, no space char) — use `getByRole('heading', { name: /^Agent Name/, level: 3 })` in tests, not `getByText('Agent Name', { exact: true })`
- [ ] Delete confirmation uses `CustomModal` with `confirmType="danger"` — proper dialog semantics
- [ ] VoiceSelect uses `SearchableSelect` — keyboard navigable popover with search input
- [ ] Editor click area has `cursor-text` class but uses `div` with `onClick` — editor itself (`EditorContent`) is keyboard accessible
- [ ] Slider uses shadcn `Slider` component (Radix-based, keyboard accessible)
