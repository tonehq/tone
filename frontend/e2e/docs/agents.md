# Feature Doc: Agents

Feature documentation for the agents list page and agent creation flow. Used by
`/generate-tests agents` to ensure all user cases are covered alongside the component
source analysis.

---

## Test approach: Real API for CRUD

Agent e2e tests use the **original/real backend API** for every CRUD operation. Do not mock
`/agent/get_all_agents` or `/agent/upsert_agent` for create, read (list), update, or delete flows —
so that data is persisted in the DB and tests validate the full stack.

- **Create (inbound/outbound)**: Save triggers real POST `upsert_agent`; redirect to `/agents` then real GET `get_all_agents`; assert created agent appears in list.
- **Read (list)**: At least one test loads the list from the real API (no mock) and asserts the grid is visible.
- **Update (edit)**: At least one test loads agent from real API, clicks Save (real POST `upsert_agent`), asserts redirect to `/agents`.
- **Delete**: When implemented, use real delete API; do not mock.

**Prerequisites**: Running backend and DB; `NEXT_PUBLIC_BACKEND_URL` set. Tests that need deterministic data (e.g. empty state, loading state, error state) may still mock the API only for those scenarios.

---

## Page

- **Route (list)**: `/agents`
- **Route (create inbound)**: `/agents/create/inbound`
- **Route (create outbound)**: `/agents/create/outbound`
- **Route (edit)**: `/agents/edit/:type/:id` (e.g., `/agents/edit/inbound/42`)
- **Components**:
  - List: `src/components/agents/AgentListPage.tsx`
  - Create modal: `src/components/agents/CreateAgentModal.tsx`
  - Create inbound: `src/app/(dashboard)/agents/create/inbound/page.tsx`
  - Create outbound: `src/app/(dashboard)/agents/create/outbound/page.tsx`
  - Form tabs: `src/components/agents/agent-form/` (GeneralTab, VoiceTab, CallConfigurationTab, promptPage)
  - Form utils: `src/components/agents/agent-form/agentFormUtils.ts`
- **Auth required**: yes (redirects to `/auth/login?redirect=<path>` without `tone_access_token` cookie)

---

## User Stories

### US-1: View agent list

**As a** logged-in user, **I want to** see a list of all my agents in a data grid, **so that** I can manage my voice agents.

**Acceptance criteria**:

- [ ] Shows "Agents" heading (h4)
- [ ] Shows a search input with placeholder "Search..."
- [ ] Shows a "Create Agent" button with a plus icon
- [ ] Displays a DataGrid with 5 columns: Agent Name, Phone Number, Last Edited, Agent Type, Action
- [ ] Column headers are uppercase and styled with grey background
- [ ] Shows loading state while agents are being fetched
- [ ] Shows empty state when no agents exist
- [ ] Agent type column shows a colored Chip: green "Inbound" or purple "Outbound"
- [ ] Last Edited column formats dates as "MMM DD, YYYY, HH:MM AM/PM"
- [ ] Action column shows a three-dot menu with "Edit" and "Delete" options
- [ ] Pagination controls display with page size options: 10, 20, 50

### US-2: Create a new agent (modal selection)

**As a** logged-in user, **I want to** choose between Inbound and Outbound agent types, **so that** I can create the right kind of agent.

**Acceptance criteria**:

- [ ] Clicking "Create Agent" button opens a dialog modal
- [ ] Modal title says "Choose type of agent"
- [ ] Modal shows two cards: "Outbound" and "Inbound"
- [ ] Outbound card shows: CallMade icon, title "Outbound", description "Automate calls within workflows using Zapier, REST API, or HighLevel"
- [ ] Inbound card shows: CallReceived icon, title "Inbound", description "Manage incoming calls via phone, Zapier, REST API, or HighLevel"
- [ ] Cards have hover effect with purple border and shadow
- [ ] Clicking a card closes the modal and navigates to `/agents/create/inbound` or `/agents/create/outbound`
- [ ] Modal has a back arrow button and a close (X) button, both close the modal
- [ ] Widget and Chat types are commented out (not available yet)

### US-3: Create inbound agent

**As a** logged-in user, **I want to** configure and save a new inbound voice agent, **so that** it can receive incoming calls.

**Acceptance criteria**:

- [ ] Page has a left sidebar and main content area
- [ ] Left sidebar shows: "Back to Agents" button, agent avatar, agent name (default "My Inbound Assistant"), "Inbound" chip (green), "Test Agent" button, and menu items (Configure, Prompt, Deployments)
- [ ] Main content shows an info Alert: "Important Your agent doesn't have a phone number and can't receive calls." with an "Assign number" button
- [ ] Shows a section heading (h5) that changes based on selected menu item
- [ ] Shows a "Save Changes" button with save icon (disabled while saving, text changes to "Saving...")
- [ ] Configure menu shows 3 tabs: General, Voice, Call Configuration
- [ ] Prompt menu shows the TipTap rich text editor for system prompt

#### General Tab (9 fields):

- [ ] Agent Name — text input, default "My Inbound Assistant"
- [ ] Description — text input, optional
- [ ] AI Model — dropdown, default "gpt-4.1"
- [ ] First Message — multiline text area
- [ ] End Call Message — multiline text area
- [ ] Custom Vocabulary — chip-based input (type + Enter to add, click X to remove)
- [ ] Filter Words — chip-based input (same behavior)
- [ ] Use Realistic Filler Words — toggle switch, default off
- [ ] Delete Agent — danger button at the bottom

#### Voice Tab (6 fields):

- [ ] Language — dropdown, default "en"
- [ ] Voice Provider (TTS) — dropdown, default "elevenlabs"
- [ ] STT Provider — dropdown, default "deepgram"
- [ ] Voice Speed — slider (0-100), default 50, marks at Slow/Normal/Fast
- [ ] Patience Level — radio buttons (Low ~1s, Medium ~3s, High ~5s), default "low"
- [ ] Speech Recognition — radio buttons (Faster vs High Accuracy), default "fast"

#### Call Configuration Tab (2 fields):

- [ ] Call Recording — toggle switch, default off
- [ ] Call Transcription — toggle switch, default off

### US-4: Create outbound agent

**As a** logged-in user, **I want to** configure and save a new outbound voice agent, **so that** it can make outgoing calls.

**Acceptance criteria**:

- [ ] Same layout as inbound creation page
- [ ] Agent name defaults to "My Outbound Assistant"
- [ ] Chip label says "Outbound" (purple)
- [ ] Info Alert says "...can't make calls" instead of "...can't receive calls"
- [ ] Left sidebar menu items: Configure, Prompt, Actions, Deployment, Calls (different from inbound)
- [ ] Outbound page does NOT have the Prompt menu implemented (no PromptPage rendered)
- [ ] Same 3 form tabs with identical fields (General, Voice, Call Configuration)
- [ ] Save Changes button calls upsert with `agent_type: 'outbound'`

### US-5: Edit an existing agent

**As a** logged-in user, **I want to** click Edit on an agent row to modify its settings, **so that** I can update my agent's configuration.

**Acceptance criteria**:

- [ ] Clicking "Edit" in the action menu navigates to `/agents/edit/:type/:id`
- [ ] Edit page loads existing agent data from the API into the form
- [ ] Form fields are pre-populated with the agent's current values
- [ ] Save Changes sends the existing agent ID in the upsert payload for update
- [ ] "Back to Agents" button returns to the agent list

### US-6: Delete an agent

**As a** logged-in user, **I want to** delete an agent, **so that** I can remove agents I no longer need.

**Acceptance criteria**:

- [ ] Action menu shows a "Delete" option in red
- [ ] Clicking Delete on the list page logs to console (TODO: wire delete API)
- [ ] Clicking Delete Agent button on the create/edit page shows a browser confirm dialog
- [ ] Confirm dialog says: "Deleting an agent will erase personalized data, voice profiles, and integrations. Are you sure?"
- [ ] Confirming the dialog navigates back to `/agents`
- [ ] Canceling the dialog stays on the current page

### US-7: Auth protection

**As the** system, **I want to** redirect unauthenticated users to the login page, **so that** only logged-in users can access agent pages.

**Acceptance criteria**:

- [ ] Redirects to `/auth/login?redirect=<encoded-path>` when no `tone_access_token` cookie
- [ ] All agent routes are protected: `/agents`, `/agents/create/inbound`, `/agents/create/outbound`, `/agents/edit/:type/:id`
- [ ] After login, 4 cookies are set: `tone_access_token`, `org_tenant_id`, `login_data`, `user_id`

---

## UI Elements

### Agent List Page (`/agents`)

| Element             | Type        | Content / Label                 | Behavior                                   |
| ------------------- | ----------- | ------------------------------- | ------------------------------------------ |
| Page heading        | h4          | "Agents"                        | Static text                                |
| Search input        | text field  | placeholder: "Search..."        | Filters agent list (not yet wired)         |
| Search icon         | icon        | SearchIcon                      | Start adornment in search field            |
| Create Agent button | button      | "Create Agent" (with AddIcon)   | Opens CreateAgentModal                     |
| DataGrid            | data grid   | Agent rows                      | 5 columns, pagination, loading overlay     |
| Agent Name column   | grid column | "AGENT NAME"                    | Displays agent name                        |
| Phone Number column | grid column | "PHONE NUMBER"                  | Displays phone or "-"                      |
| Last Edited column  | grid column | "LAST EDITED"                   | Formatted date or "-"                      |
| Agent Type column   | grid column | "AGENT TYPE"                    | Chip: green "Inbound" or purple "Outbound" |
| Action column       | grid column | "ACTION"                        | Three-dot menu (MoreVertIcon)              |
| Edit menu item      | menu item   | "Edit" (with EditIcon)          | Navigates to edit page                     |
| Delete menu item    | menu item   | "Delete" (with DeleteIcon, red) | Triggers delete handler                    |

### Create Agent Modal

| Element       | Type              | Content / Label          | Behavior                               |
| ------------- | ----------------- | ------------------------ | -------------------------------------- |
| Dialog title  | h6                | "Choose type of agent"   | Static text                            |
| Back button   | icon button       | ArrowBackIcon            | Closes modal                           |
| Close button  | icon button       | CloseIcon                | Closes modal                           |
| Outbound card | Paper (clickable) | "Outbound" + description | Navigates to `/agents/create/outbound` |
| Inbound card  | Paper (clickable) | "Inbound" + description  | Navigates to `/agents/create/inbound`  |

### Agent Creation / Edit Page (common to both types)

| Element                | Type         | Content / Label                                                                                      | Behavior                                |
| ---------------------- | ------------ | ---------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Back to Agents button  | button       | "Back to Agents" (with ArrowBackIcon)                                                                | Navigates to `/agents`                  |
| Agent avatar           | Avatar       | Empty avatar                                                                                         | Display only                            |
| Agent name             | subtitle1    | Form name value                                                                                      | Reflects current name field             |
| Type chip              | Chip         | "Inbound" (green) or "Outbound" (purple)                                                             | Display only                            |
| Test Agent button      | button       | "Test Agent" (with PhoneIcon)                                                                        | Not yet implemented                     |
| Menu items             | list items   | Configure, Prompt, Deployments (inbound) or Configure, Prompt, Actions, Deployment, Calls (outbound) | Switches main content section           |
| Info Alert             | Alert (info) | "Important Your agent doesn't have a phone number..."                                                | Contains "Assign number" button         |
| Section heading        | h5           | Dynamic: "Configure" / "Prompt" / etc.                                                               | Changes with menu selection             |
| Save Changes button    | button       | "Save Changes" / "Saving..." (with SaveIcon)                                                         | Calls upsert API, disabled while saving |
| General tab            | Tab          | "General" (with SettingsIcon)                                                                        | Shows GeneralTab form                   |
| Voice tab              | Tab          | "Voice" (with VoiceIcon)                                                                             | Shows VoiceTab form                     |
| Call Configuration tab | Tab          | "Call Configuration" (with PhoneIcon)                                                                | Shows CallConfigurationTab form         |

---

## Navigation

| Trigger                              | Destination                       | Condition                    |
| ------------------------------------ | --------------------------------- | ---------------------------- |
| Click "Create Agent" button          | Opens CreateAgentModal            | Always                       |
| Click Outbound card (modal)          | `/agents/create/outbound`         | Modal closes first           |
| Click Inbound card (modal)           | `/agents/create/inbound`          | Modal closes first           |
| Click back/close button (modal)      | Closes modal (stays on `/agents`) | Always                       |
| Click "Edit" in action menu          | `/agents/edit/:type/:id`          | Agent has valid id           |
| Click "Back to Agents" (create page) | `/agents`                         | Always                       |
| Save Changes (success)               | `/agents`                         | API call succeeds            |
| Delete Agent (confirmed)             | `/agents`                         | User confirms browser dialog |
| No auth cookie                       | `/auth/login?redirect=<path>`     | Middleware redirect          |

---

## API Contracts

| Endpoint                           | Method | Request                                                                                                                                                                                                                                          | Success Response                 | Error Response      |
| ---------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- | ------------------- |
| `/agent/get_all_agents`            | GET    | (none)                                                                                                                                                                                                                                           | `Agent[]` or `{ data: Agent[] }` | `{ detail: "..." }` |
| `/agent/get_all_agents?agent_id=N` | GET    | query param `agent_id`                                                                                                                                                                                                                           | `Agent[]` (single item)          | `{ detail: "..." }` |
| `/agent/upsert_agent`              | POST   | `{ name, description, agent_type, first_message, end_call_message, system_prompt, custom_vocabulary, filter_words, realistic_filler_words, language, voice_speed, patience_level, speech_recognition, call_recording, call_transcription, id? }` | `Agent`                          | `{ detail: "..." }` |

### Agent response shape (from API)

```json
{
  "id": 42,
  "uuid": "abc-123",
  "name": "My Inbound Assistant",
  "description": "",
  "agent_type": "inbound",
  "phone_number": null,
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
  "llm_model_id": null,
  "tts_model_id": null,
  "stt_model_id": null,
  "status": "active",
  "created_at": 1708900000,
  "updated_at": 1708900000
}
```

### Upsert payload shape (form → API)

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
  "id": 42
}
```

---

## Edge Cases

- [ ] Empty agent list — DataGrid shows no rows, no error
- [ ] API returns object `{ data: [...] }` instead of array — handled in atom
- [ ] API returns empty array — handled in atom
- [ ] Network error fetching agents — error logged to console, loader stops
- [ ] Agent with no phone number — phone column shows "-"
- [ ] Agent with no `agent_type` — defaults to "inbound" in edit navigation
- [ ] Agent with no `updated_at` — Last Edited shows "-"
- [ ] Upsert API failure — error logged to console, saving state resets, stays on create page
- [ ] Custom vocabulary as string from API (JSON-encoded) — `parseStringArray` handles it
- [ ] Boolean fields as strings from API ("true"/"false") — `parseBoolean` handles it
- [ ] Save with all default values — valid payload, no required fields besides `name`
- [ ] Delete confirm cancelled — stays on page, no navigation
- [ ] Delete on list page — only logs to console (API not wired yet)
- [ ] Double-fetch prevention — `hasFetchedRef` prevents duplicate API calls on mount
- [ ] Agent name reflected in sidebar — changes as user types in the name field
- [ ] Outbound page missing PromptPage — prompt menu item exists in sidebar but no `currentMenu === 'prompt'` rendering

---

## Business Rules

- Agent types are limited to `'inbound'` and `'outbound'` (widget and chat are commented out)
- Default agent names differ by type: "My Inbound Assistant" vs "My Outbound Assistant"
- Default AI model is `gpt-4.1`
- Default voice provider is `elevenlabs`, default STT provider is `deepgram`
- Default language is English (`en`)
- Voice speed range is 0-100, default 50
- Patience level options: low (~1s), medium (~3s), high (~5s)
- Speech recognition options: fast, accurate (high accuracy)
- Call recording and transcription default to off
- `custom_vocabulary` and `filter_words` are stored as JSON strings in the API
- Upsert with an `id` field = update; without = create
- Edit URL pattern: `/agents/edit/:type/:id` — type is lowercased from `agent_type`
- All API calls go through `src/utils/axios.ts` which injects `tenant_id` and `Authorization` headers
- The `fetchAgentList` Jotai atom handles both array and `{ data: [] }` response shapes
- Form state uses camelCase; API uses snake_case — conversion handled by `agentFormUtils.ts`
- Inbound sidebar menu: Configure, Prompt, Deployments
- Outbound sidebar menu: Configure, Prompt, Actions, Deployment, Calls
- Pagination mode is server-side but currently uses client-side data (full list loaded at once)

---

## Accessibility Requirements

- [ ] "Create Agent" button is a proper `<button>` element
- [ ] CreateAgentModal renders as MUI Dialog (focus trapped, aria-modal by default)
- [ ] Modal title uses `<Typography variant="h6">` — should be identifiable as dialog title
- [ ] Agent type cards use `<Paper>` with `onClick` — missing `role="button"` and keyboard handler (accessibility gap)
- [ ] DataGrid has built-in keyboard navigation (MUI DataGrid)
- [ ] Action menu uses MUI Menu with proper aria attributes
- [ ] Tab components use MUI Tabs with `role="tabpanel"` for content panels
- [ ] Form inputs use the project's `TextInput` / `Form` components with labels
- [ ] Toggle switches are MUI Switch components (accessible by default)
- [ ] "Back to Agents" button is a proper `<button>` element
- [ ] "Save Changes" button has `disabled` attribute when saving
- [ ] Info Alert uses MUI Alert with `severity="info"` and `role="alert"`
