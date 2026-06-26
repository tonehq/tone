# Feature Doc: Agents (List)

Feature documentation for the Agents list page at `/agents`. Used by
`/generate-tests agents` (or `--docs e2e/ux_flow_docs/agents.md`) to ensure all
positive and negative scenarios are covered.

An **Agent** is a per-organization voice/chat assistant backed by configurable
LLM + STT + TTS providers and optional tools, MCP servers, knowledge-base
documents, and phone numbers. The list page is the org's catalogue of agents
with search, faceted filtering, sortable columns, pagination, row-level edit
+ delete, and a typed Create CTA (modal → `/agents/create/{type}`).

> The create + edit flows live in separate docs — see `agents-create.md` and
> `agents-edit.md`. This doc covers `/agents` only.

> **Format rule (mandatory):** every test case below is one **Action** (steps
> the user performs) followed by multiple **Observations** (each a set of
> verification steps). See [`_template.md`](_template.md) for the canonical
> shape and ID prefixes.

---

## Page

- **Route**: `/agents`
- **Component (wrapper)**: `src/app/(dashboard)/agents/page.tsx`
- **Main component**: `src/components/agents/AgentListPage.tsx`
- **Sub-components**:
  - `src/components/agents/AgentActionMenu.tsx` (per-row Edit/Delete dropdown)
  - `src/components/agents/AgentTypeBadge.tsx` (Inbound / Outbound / Chatbot pill)
  - `src/components/agents/CreateAgentModal.tsx` (type chooser modal)
  - `src/components/agents/agentsListConfig.ts` (faceted-list endpoints + facets)
- **Auth required**: yes (middleware redirects to
  `/auth/login?redirect=%2Fagents` without `tone_access_token` cookie)

---

## User Stories

### US-1: Browse the agent list

**As an** agent owner, **I want to** see all agents in my org as a sortable,
filterable table, **so that** I know what's deployed and can drill in.

**Acceptance criteria**:

- [ ] Page header shows "Agents" (h1) + subtitle "Manage your voice agents"
- [ ] When the list is non-empty, a count `Badge` (secondary, tabular-nums) renders next to the heading
- [ ] Primary CTA "Create Agent" appears in the header with a Plus icon
- [ ] Toolbar: token-based search bar with placeholder `Search agents… (e.g. name:hotel)` + Filters button (drawer trigger)
- [ ] Table columns (in order): Agent (name + description), Status, Type, Phone, Last Updated, actions (right-aligned)
- [ ] Status pill is "Active" (emerald) when the agent has at least one phone number, otherwise "Inactive" (amber)
- [ ] Type column renders `<AgentTypeBadge>` (e.g. INBOUND, OUTBOUND, CHATBOT)
- [ ] Phone column shows one `<PhoneNumberDisplay>` per phone number, or an em-dash when none are attached
- [ ] Last Updated column uses `formatDate(updated_at)` from `@/utils/date`
- [ ] Loading state: `CustomTable` shows its built-in skeleton rows while `fl.listLoading === true`
- [ ] Empty state (no rows, no filters): Bot icon + "No agents yet" + subtitle "Create your first voice agent to get started" + inline "Create Agent" button

### US-2: Search and filter agents

**As an** agent owner, **I want to** type a name to find an agent or filter by
type / status, **so that** I can locate a specific agent quickly.

**Acceptance criteria**:

- [ ] Typing into the search bar adds a free-text query that becomes part of the `POST /agent/list` body (`search` field)
- [ ] Typing `name:hotel` is parsed as a `name`-field token and sent as such
- [ ] Clicking the Filters button opens `FacetFilterDrawer` with sections `Type` and `Status`
- [ ] Drawer facet sections are populated by `POST /agent/facets`
- [ ] Selecting facets and applying refreshes the list with `filters: [{field, operator: 'in', value: [...] }]`
- [ ] When `hasActiveFilters` is true, the toolbar exposes a Clear action (`fl.clearAll`)

### US-3: Sort the list

**As an** agent owner, **I want to** click column headers to sort by Agent
name, Type, or Last Updated, **so that** I can reorder the list.

**Acceptance criteria**:

- [ ] Columns flagged `sorter: true` are `name`, `agent_type`, `updated_at`
- [ ] Default sort is `updated_at` desc (`{ field: 'updated_at', order: 'desc' }`, from `agentsListConfig.defaultSort`)
- [ ] Clicking a sortable header cycles asc → desc → reset; `fl.handleSortChange` fires `POST /agent/list` with the new `sort_by` / `sort_order`
- [ ] Backend silently falls back to `updated_at` desc when `sort_by` is unknown (Postman: "200 OK (invalid sort falls back silently)")

### US-4: Paginate

**As an** agent owner, **I want to** change page size and navigate pages,
**so that** I can scan large lists without an infinite scroll.

**Acceptance criteria**:

- [ ] Default page size is 10; selector exposes 10 / 25 / 50 / 100 (from `agentsListConfig.pageSizeOptions`)
- [ ] Changing the page-size selector re-fires `POST /agent/list` with the new `page_size` and resets `page` to 1
- [ ] Clicking pagination next/prev re-fires with the new `page`
- [ ] After deleting the last row on the last page, the page index decrements to the new last page (defensive `lastPage = max(1, ceil((total-1)/page_size))`)

### US-5: Click a row to edit

**As an** agent owner, **I want to** click any row to jump straight into the
agent editor, **so that** I can update prompt, voice, tools, etc.

**Acceptance criteria**:

- [ ] Clicking a row calls `handleEdit(record)` → `router.push("/agents/edit/{type}/{id}")` where `{type}` is the lowercased `agent_type` (`inbound` is the fallback when missing)
- [ ] Clicking Edit from the row action menu has the same effect
- [ ] If the row has no `id`, the click is a no-op (defensive guard)

### US-6: Delete a single agent

**As an** agent owner, **I want to** delete an agent I no longer need from
the row action menu, **so that** I can prune the catalogue.

**Acceptance criteria**:

- [ ] The `AgentActionMenu` exposes Edit + Delete; Delete opens a confirmation modal with title `Delete {name}?` and body `Are you sure you want to delete "{name}"? This action cannot be undone.`
- [ ] Confirm calls `deleteAgentAtom(id)` → `DELETE /agent/delete_agent?agent_id=<id>`
- [ ] On success: toast title `Agent deleted successfully`; if the deleted row was the last on the page, the page index steps back, otherwise `fl.refresh()` re-fires `/agent/list`
- [ ] On error: `handleApiError` surfaces the backend `detail` as a toast title; the row stays in the table

### US-7: Create a new agent via the type chooser

**As an** agent owner, **I want to** pick whether the new agent is Inbound or
Outbound before going to the full editor, **so that** the editor opens at the
right preset.

**Acceptance criteria**:

- [ ] Clicking the header "Create Agent" button opens `CreateAgentModal` (a `CustomModal` titled "Choose type of agent")
- [ ] Modal renders two cards: "Outbound" (Initiates calls) and "Inbound" (Receives calls)
- [ ] Picking Outbound routes to `/agents/create/outbound`; picking Inbound routes to `/agents/create/inbound`
- [ ] The modal closes before navigation (`onClose()` runs first)
- [ ] The same modal also opens from the empty-state "Create Agent" button

---

## Input Specifications

### Toolbar search (`FacetFilterBar` + `TokenSearchBar`)

| Field        | Type      | Required | Validation                                                     | Notes                                                         |
| ------------ | --------- | -------- | -------------------------------------------------------------- | ------------------------------------------------------------- |
| Search input | tokenized | no       | Free text or `name:<query>`; no client-side length limit       | Debounced through `useFacetedList`; emits `search` body field |
| Filters drawer (Type)   | multi-select | no | Values from `POST /agent/facets` → `agent_type` (inbound, outbound, chatbot) | Sent as `filters: [{ field: 'agent_type', operator: 'in', value: [...] }]` |
| Filters drawer (Status) | multi-select | no | Values from `POST /agent/facets` → `status` (active, inactive — server-computed from `phone_number` length) | Sent as `filters: [{ field: 'status', operator: 'in', value: [...] }]` |

### Confirmation modal (Delete)

| Field          | Type     | Required | Validation                              | Exact Text                                                       |
| -------------- | -------- | -------- | --------------------------------------- | ---------------------------------------------------------------- |
| Modal title    | static   | n/a      | Renders `Delete {agentName}?`            | `Delete {name}?` (literal interpolation, e.g. `Delete Acme Support Bot?`) |
| Modal body     | static   | n/a      | Renders `Are you sure…this action cannot be undone.` | `Are you sure you want to delete "{name}"? This action cannot be undone.` |
| Confirm button | button   | n/a      | Labelled "Delete", `confirmType=danger` | Triggers `DELETE /agent/delete_agent`                            |
| Cancel button  | button   | n/a      | Closes the modal                         | n/a                                                              |

---

## UI Elements

| Element                      | Type            | Content / Label                                       | Behavior                                                            |
| ---------------------------- | --------------- | ----------------------------------------------------- | ------------------------------------------------------------------- |
| Page heading                 | h1              | "Agents"                                              | Static; followed by a count badge when `total > 0`                  |
| Count badge                  | Badge (secondary) | numeric count                                        | Hidden when `total === 0`                                            |
| Page subtitle                | p               | "Manage your voice agents"                            | Static                                                              |
| Create Agent button          | Button (primary) | "Create Agent" + Plus icon                           | Opens `CreateAgentModal`                                            |
| Search bar                   | TokenSearchBar   | placeholder `Search agents… (e.g. name:hotel)`        | Tokenized; supports `name:<query>` and free text                    |
| Filters button               | Button + Badge   | "Filters" + numeric badge equal to `drawerFilterCount` | Opens `FacetFilterDrawer`                                          |
| Filter drawer                | Drawer           | Sections "Type" + "Status"                            | Multi-select facets with counts from `POST /agent/facets`            |
| Table — Agent column         | th + td          | Name (semibold) + truncated description (muted)       | Sortable (`sorter: true`)                                            |
| Table — Status column        | td               | Pill "Active" (emerald) / "Inactive" (amber)          | Driven by `phone_number?.length > 0`                                 |
| Table — Type column          | th + td          | `<AgentTypeBadge>` (INBOUND / OUTBOUND / CHATBOT)     | Sortable                                                             |
| Table — Phone column         | td               | `<PhoneNumberDisplay>` per number, or em-dash         | Renders flag + formatted number                                      |
| Table — Last Updated         | th + td          | `formatDate(updated_at)`                              | Sortable                                                             |
| Row action menu              | Icon button      | ⋮ (Edit / Delete)                                     | Opens `ActionMenu`; Delete opens confirm modal                      |
| Empty state                  | div              | Bot icon + "No agents yet" + Create Agent button      | Shown when `total === 0` and not loading                            |
| Pagination footer            | div              | "Rows per page" selector + page nav                   | Built into `CustomTable`                                             |
| CreateAgentModal — Outbound  | Card             | "Outbound" + "Initiates calls" + description          | Click → `/agents/create/outbound`                                    |
| CreateAgentModal — Inbound   | Card             | "Inbound" + "Receives calls" + description            | Click → `/agents/create/inbound`                                     |

---

## Navigation

| Trigger                                   | Destination                                  | Condition                                |
| ----------------------------------------- | -------------------------------------------- | ---------------------------------------- |
| Click "Create Agent" (header)             | Opens `CreateAgentModal`                     | Always                                   |
| Click "Create Agent" (empty state)        | Opens `CreateAgentModal`                     | Always                                   |
| Modal — click Inbound card                | `/agents/create/inbound`                     | Always                                   |
| Modal — click Outbound card               | `/agents/create/outbound`                    | Always                                   |
| Click row body (Name cell)                | `/agents/edit/{agent_type}/{id}`             | `record.id` truthy                       |
| Click action menu → Edit                  | `/agents/edit/{agent_type}/{id}`             | Always                                   |
| Click action menu → Delete → confirm      | `DELETE /agent/delete_agent?agent_id=<id>`   | Always                                   |
| Change page / page size                   | New `POST /agent/list` request               | Always                                   |
| Click sortable column header              | New `POST /agent/list` with updated sort     | Always                                   |
| No auth cookie                            | `/auth/login?redirect=%2Fagents`             | `src/middleware.ts` redirect             |

---

## API Contracts

Prefix: `/api/v1`. Verified against the Postman `Agents` folder and
`src/services/agentsService.ts`.

| Endpoint                        | Method | Request                                                                                                | Success                                              | Error                              |
| ------------------------------- | ------ | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- | ---------------------------------- |
| `/agent/list`                   | POST   | `{ page, page_size, search?, sort_by?, sort_order?, filters? }`                                        | `200 { items: Agent[], total, page, page_size }`     | `{ "detail": "..." }`              |
| `/agent/facets`                 | POST   | `{ filters?: Filter[], search? }`                                                                      | `200 { agent_type: { inbound: n, … }, status: {…} }` | `{ "detail": "..." }`              |
| `/agent/filter-values`          | GET    | `?column_name=<field>`                                                                                 | `200 { column, values: string[] }`                   | `{ "detail": "..." }`              |
| `/agent/delete_agent`           | DELETE | `?agent_id=<uuid>`                                                                                     | `200 { message: "Agent deleted successfully" }`      | `{ "detail": "..." }`              |
| `/agent/get_agent`              | GET    | `?agent_id=<uuid>&config_id?=<uuid>`                                                                   | `200 Agent`                                          | `404 { "detail": "Agent not found" }` |

### Example — `POST /agent/list`

Request body (matches the Postman exemplar):

```json
{
  "page": 1,
  "page_size": 20,
  "search": "acme",
  "sort_by": "-updated_at",
  "is_active": true,
  "agent_type": "inbound"
}
```

> The frontend's `useFacetedList` translates its drawer selections into the
> `filters: [{ field, operator: 'in', value }]` shape rather than the
> top-level `agent_type` / `is_active` shortcuts shown above. Both are accepted
> by the backend; tests should mock matching whichever path the UI uses.

200 OK:

```json
{
  "items": [
    {
      "id": "a1c5e8b2-9d3f-4e7a-8b1c-2f4d6e8a1b3c",
      "uuid": "a1c5e8b2-9d3f-4e7a-8b1c-2f4d6e8a1b3c",
      "name": "Acme Support Bot",
      "description": "Tier-1 support assistant",
      "agent_type": "inbound",
      "is_active": true,
      "phone_number": [{ "type": "twilio", "no": "+15551234567" }],
      "created_at": 1716800000.0,
      "updated_at": 1716800500.0
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

200 OK (empty):

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

200 OK (outbound filter):

```json
{
  "items": [
    {
      "id": "e7f8a9b0-1c2d-4e5f-9a8b-7c6d5e4f3a2b",
      "uuid": "e7f8a9b0-1c2d-4e5f-9a8b-7c6d5e4f3a2b",
      "name": "Lead Qualifier",
      "description": "Outbound qualification agent",
      "agent_type": "outbound",
      "is_active": true,
      "phone_number": [{ "type": "twilio", "no": "+14155557788" }],
      "created_at": 1750155612.118911,
      "updated_at": 1750155612.118911
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

401 Unauthorized:

```json
{ "detail": "Could not validate credentials" }
```

### Example — `DELETE /agent/delete_agent?agent_id=<uuid>`

200 OK: `{ "message": "Agent deleted successfully" }`

401 Unauthorized: `{ "detail": "Invalid token" }`

404 Not Found: `{ "detail": "Agent not found" }`

422 Validation: `{ "detail": [{ "type": "missing", "loc": ["query", "agent_id"], "msg": "Field required", "input": null }] }`

State is held in `src/atoms/AgentsAtom.tsx` — the list page primarily uses
`useFacetedList` (which manages its own state). The `deleteAgentAtom` is the
write-only atom used by the row delete action.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: List renders the populated table

**Preconditions**:
- User is authenticated (`tone_access_token` cookie present)
- Org has 1 agent in the backend (or `POST /agent/list` is mocked to return one row)

**Action**:
1. Visit `/agents`

**Observation 1 — Network request fires with defaults**:
1. Exactly one `POST /agent/list` request is recorded
2. Request body includes `{ page: 1, page_size: 10, sort_by: 'updated_at', sort_order: 'desc' }`

**Observation 2 — Page header renders**:
1. An `<h1>` with text `Agents` is visible
2. Subtitle `Manage your voice agents` is visible
3. A count `Badge` next to the heading shows `1`

**Observation 3 — Row content renders correctly**:
1. The row name reads `Acme Support Bot`
2. Status pill reads `Active` (emerald) because `phone_number.length > 0`
3. Type column shows the `INBOUND` `AgentTypeBadge`
4. Phone column renders `+15551234567`

**API mock**: `POST /agent/list` → 200 with the PS-1 fixture body shown in API Contracts.

---

### TC-HAPPY-002: Empty list shows the no-agents empty state

**Preconditions**:
- User is authenticated
- Org has zero agents (`POST /agent/list` returns `total: 0`)

**Action**:
1. Visit `/agents`

**Observation 1 — Empty state visible**:
1. The Bot icon is in the DOM inside the table body
2. Text `No agents yet` is visible
3. Subtitle `Create your first voice agent to get started` is visible
4. An inline `Create Agent` button is visible

**Observation 2 — Count badge is hidden**:
1. The numeric count badge next to the `Agents` heading is NOT in the DOM

**API mock**: `POST /agent/list` → 200 `{ "items": [], "total": 0, "page": 1, "page_size": 10 }`.

---

### TC-HAPPY-003: Search by free-text query refires the list

**Preconditions**:
- TC-HAPPY-001 setup; list is populated

**Action**:
1. Visit `/agents`
2. Type `acme` into the search bar
3. Wait for the search debounce

**Observation 1 — Network request body**:
1. A subsequent `POST /agent/list` request body contains `"search": "acme"`

**Observation 2 — Table updates**:
1. Matching rows are rendered
2. The toolbar exposes a Clear action when `hasActiveFilters` is true

---

### TC-HAPPY-004: Filter by Type=outbound via the drawer

**Preconditions**:
- Both inbound and outbound agents exist (or mocked accordingly)

**Action**:
1. Visit `/agents`
2. Click the `Filters` button
3. In the drawer, tick `Outbound` under the `Type` section
4. Click `Apply`

**Observation 1 — Drawer facets load**:
1. `POST /agent/facets` was recorded when the drawer opened
2. Drawer sections `Type` and `Status` are rendered with counts

**Observation 2 — List re-fires with filters**:
1. A `POST /agent/list` is recorded with body containing `"filters": [{ "field": "agent_type", "operator": "in", "value": ["outbound"] }]`
2. Filters button badge reads `1`

**Observation 3 — Table shows only outbound rows**:
1. Each visible row's Type badge reads `OUTBOUND`

---

### TC-HAPPY-005: Sort by Name asc

**Preconditions**: list has at least 2 agents.

**Action**:
1. Visit `/agents`
2. Click the `Agent` column header once

**Observation 1 — Sort request**:
1. A `POST /agent/list` request is recorded with `"sort_by": "name", "sort_order": "asc"`

**Observation 2 — Subsequent click flips direction**:
1. Click the `Agent` header again
2. Next request has `"sort_by": "name", "sort_order": "desc"`

---

### TC-HAPPY-006: Page-size change resets to page 1

**Preconditions**: total > 25 (or mock returns that condition).

**Action**:
1. Visit `/agents`
2. Open the rows-per-page selector
3. Pick `25`

**Observation 1 — Request body**:
1. A `POST /agent/list` is recorded with body `{ ..., "page": 1, "page_size": 25 }`

**Observation 2 — Selector reflects new value**:
1. The page-size selector displays `25`

---

### TC-HAPPY-007: Row click navigates to the editor

**Preconditions**: TC-HAPPY-001 setup.

**Action**:
1. Visit `/agents`
2. Click the Name cell of the inbound row

**Observation 1 — Navigation**:
1. URL changes to `/agents/edit/inbound/a1c5e8b2-9d3f-4e7a-8b1c-2f4d6e8a1b3c`
2. No new full-page reload occurs (client-side navigation)

---

### TC-HAPPY-008: Delete from row menu succeeds

**Preconditions**: TC-HAPPY-001 setup (one agent in the table).

**Action**:
1. Visit `/agents`
2. Click the per-row ⋮ action menu
3. Click `Delete`
4. In the confirmation modal, click the `Delete` button

**Observation 1 — Confirmation modal content**:
1. Modal title equals `Delete Acme Support Bot?`
2. Modal body contains `Are you sure you want to delete "Acme Support Bot"? This action cannot be undone.`
3. Primary button is labeled `Delete` (danger style)

**Observation 2 — Delete API fires**:
1. Exactly one `DELETE /agent/delete_agent?agent_id=a1c5e8b2-9d3f-4e7a-8b1c-2f4d6e8a1b3c` request is recorded

**Observation 3 — Success toast and refresh**:
1. A Sonner toast title `Agent deleted successfully` appears
2. A subsequent `POST /agent/list` request is recorded (refresh)
3. The deleted row is no longer in the DOM

**API mock**:
- `DELETE /agent/delete_agent` → 200 `{ "message": "Agent deleted successfully" }`

---

### TC-HAPPY-009: Create modal opens and routes to Inbound

**Preconditions**: any.

**Action**:
1. Visit `/agents`
2. Click the header `Create Agent` button
3. Click the `Inbound` card in the modal

**Observation 1 — Modal opens**:
1. `CreateAgentModal` is visible with title `Choose type of agent`
2. Two cards labelled `Outbound` (`Initiates calls`) and `Inbound` (`Receives calls`) render

**Observation 2 — Modal closes then navigates**:
1. The modal is removed from the DOM
2. URL changes to `/agents/create/inbound`

---

### TC-HAPPY-010: Create modal routes to Outbound

**Action**:
1. Visit `/agents`
2. Click the header `Create Agent` button
3. Click the `Outbound` card

**Observation 1 — Outbound navigation**:
1. The modal closes
2. URL changes to `/agents/create/outbound`

---

### TC-HAPPY-011: Empty-state Create button opens the same modal

**Preconditions**: zero-agent org (`POST /agent/list` returns `total: 0`).

**Action**:
1. Visit `/agents`
2. Click the inline `Create Agent` button in the empty state

**Observation 1 — Same modal opens**:
1. `CreateAgentModal` is visible with title `Choose type of agent`
2. Both `Outbound` and `Inbound` cards are present

---

### TC-ERROR-001: List 401 (token rejected) — empty state, no toast

**Preconditions**: authenticated user but token rejected mid-session.

**Action**:
1. Visit `/agents`

**Observation 1 — Empty fallback**:
1. `fl.listLoading` clears (no spinner)
2. The empty state ("No agents yet") renders because `fl.rows` is empty
3. No error toast is shown

**Observation 2 — No auto-redirect**:
1. URL is still `/agents` — axios does NOT redirect to login on 401 today (⚠ unverified)

**API mock**: `POST /agent/list` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-002: List 500 falls back to empty state (no destructive crash)

**Action**:
1. Visit `/agents`

**Observation 1 — UI does not crash**:
1. The empty state ("No agents yet") renders
2. Skeleton/spinner clears
3. No client-side error is thrown

**API mock**: `POST /agent/list` → 500 `{ "detail": "Internal server error" }`.

---

### TC-ERROR-003: Facets 500 — drawer renders empty counts

**Action**:
1. Visit `/agents`
2. Click the `Filters` button

**Observation 1 — Drawer still opens**:
1. The drawer is visible
2. Sections `Type` and `Status` render with empty counts (0)
3. User can still tick selections

**API mock**: `POST /agent/facets` → 500 `{ "detail": "Internal server error" }`.

---

### TC-ERROR-004: Delete 404 — row stays, toast surfaces

**Preconditions**: TC-HAPPY-001 setup; user opens the row delete confirm.

**Action**:
1. Visit `/agents`
2. Open row action menu → click `Delete`
3. Confirm the modal

**Observation 1 — Toast surfaces backend `detail`**:
1. A toast with title `Agent not found` appears

**Observation 2 — Row remains in the table**:
1. The row is still present in the DOM
2. No new `POST /agent/list` refresh fires

**API mock**: `DELETE /agent/delete_agent` → 404 `{ "detail": "Agent not found" }`.

---

### TC-ERROR-005: Delete 401 — invalid token toast

**Action**:
1. Open row action menu → Delete → confirm

**Observation 1 — Error toast**:
1. Toast title equals `Invalid token` (or backend `detail` verbatim)

**Observation 2 — Row remains**:
1. Row is still in the table

**API mock**: `DELETE /agent/delete_agent` → 401 `{ "detail": "Invalid token" }`.

---

### TC-ERROR-006: Delete 422 (array detail) falls back to generic toast

**Action**:
1. Trigger delete confirm

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.` (⚠ unverified — confirm fallback text)

**API mock**: `DELETE /agent/delete_agent` → 422 `{ "detail": [{ "type": "missing", "loc": ["query","agent_id"], "msg": "Field required", "input": null }] }`.

---

### TC-ERROR-007: Delete 500 — backend detail string surfaces

**Action**:
1. Trigger delete confirm

**Observation 1 — Toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Row stays**:
1. The row remains in the DOM

**API mock**: `DELETE /agent/delete_agent` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-008: Delete 403 (member tries owner-only agent)

**Action**:
1. Trigger delete confirm as a member-role user

**Observation 1 — Toast**:
1. Toast title equals `Forbidden` (or backend `detail` verbatim)

**Observation 2 — Row remains**:
1. Row is still in the table

**API mock**: `DELETE /agent/delete_agent` → 403 `{ "detail": "Forbidden" }`.

---

### TC-ERROR-009: Delete 401 mid-session — surfaces toast without auto-redirect

**Action**:
1. Trigger delete confirm

**Observation 1 — Toast and URL**:
1. Toast title equals `Invalid token` (or `Could not validate credentials`)
2. URL is still `/agents` — user is NOT auto-redirected to login

**API mock**: `DELETE /agent/delete_agent` → 401 `{ "detail": "Invalid token" }`.

---

### TC-ERROR-010: List 400 (malformed filter) — empty state, no toast

**Action**:
1. Visit `/agents` with a deliberately malformed search/filter combo

**Observation 1 — Empty state**:
1. Table renders the empty state
2. No error toast is shown (list errors are swallowed)

**API mock**: `POST /agent/list` → 400 `{ "detail": "Invalid filter" }`.

---

### TC-ERROR-011: List 500 mid-search — empty state, recovers on retry

**Action**:
1. Visit `/agents`
2. Type `acme` to trigger a search

**Observation 1 — First request 500**:
1. Skeleton clears; empty-state body renders; no client crash

**Observation 2 — Retry succeeds**:
1. On a follow-up request returning 200, the table re-populates

**API mock**:
- First `POST /agent/list` → 500
- Subsequent `POST /agent/list` → 200 (PS-1 fixture)

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**: no `tone_access_token` cookie set.

**Action**:
1. Visit `/agents`

**Observation 1 — Middleware redirect**:
1. Response status is 307
2. Final URL is `/auth/login?redirect=%2Fagents`

**Observation 2 — Login form is visible**:
1. The login page renders (no agents UI loaded)

---

### TC-NAV-002: Expired token redirects to login and clears cookie

**Preconditions**: an expired `tone_access_token` cookie is set.

**Action**:
1. Visit `/agents`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fagents` (307)

**Observation 2 — Cookie state**:
1. The expired `tone_access_token` cookie is cleared by the login response

---

### TC-NAV-003: Non-member is denied access

**Preconditions**: user is signed in but is not a member of the active org.

**Action**:
1. Visit `/agents`

**Observation 1 — Access denied or /home redirect**:
1. Either an access-denied state is rendered OR URL redirects to `/home`

**Observation 2 — No list fetch fires**:
1. Zero `POST /agent/list` requests are recorded

---

### TC-NAV-004: Pagination — Prev disabled on first page

**Preconditions**: list has > 1 page.

**Action**:
1. Visit `/agents` (lands on page 1)

**Observation 1 — Button state**:
1. The `Prev` pagination button has `disabled` attribute
2. The `Next` pagination button is enabled

---

### TC-NAV-005: Pagination — Next disabled on last page

**Preconditions**: list has > 1 page; user navigates to the last page.

**Action**:
1. Visit `/agents`
2. Click `Next` until on the last page

**Observation 1 — Button state**:
1. The `Next` pagination button has `disabled` attribute
2. The `Prev` button is enabled

---

### TC-NAV-006: Sort by Name cycles asc → desc → reset

**Preconditions**: list has ≥ 2 rows.

**Action**:
1. Visit `/agents`
2. Click the `Agent` column header three times in a row

**Observation 1 — Three requests in order**:
1. First click: `POST /agent/list` body has `sort_by: 'name', sort_order: 'asc'`
2. Second click: body has `sort_by: 'name', sort_order: 'desc'`
3. Third click: body resets to default `sort_by: 'updated_at', sort_order: 'desc'`

---

### TC-NAV-007: Sort by Type orders rows by agent_type

**Action**:
1. Visit `/agents`
2. Click the `Type` column header

**Observation 1 — Request body**:
1. `POST /agent/list` body contains `"sort_by": "agent_type"`

---

### TC-NAV-008: Sort by Last Updated cycles direction

**Action**:
1. Visit `/agents`
2. Click the `Last Updated` column header twice

**Observation 1 — Two requests**:
1. First click body: `sort_by: 'updated_at', sort_order: 'asc'`
2. Second click body: `sort_by: 'updated_at', sort_order: 'desc'`

---

### TC-NAV-009: Delete confirmation cancel preserves the row

**Action**:
1. Visit `/agents`
2. Open the row action menu
3. Click `Delete`
4. Click `Cancel` (or close the modal)

**Observation 1 — Modal dismissed**:
1. The delete confirmation modal is no longer in the DOM

**Observation 2 — Row unaffected**:
1. Zero `DELETE /agent/delete_agent` requests are recorded
2. The row is still in the table

---

### TC-NAV-010: CreateAgentModal Escape key cancels without navigation

**Action**:
1. Visit `/agents`
2. Click `Create Agent` in the header
3. Press the `Escape` key

**Observation 1 — Modal closes, no navigation**:
1. `CreateAgentModal` is no longer in the DOM
2. URL is still `/agents`
3. No `router.push` is invoked

---

### TC-LOADING-001: Slow list keeps skeleton visible

**Action**:
1. Visit `/agents` against a deliberately slow backend (`POST /agent/list` delayed > 3s)

**Observation 1 — Skeleton stays**:
1. `CustomTable` skeleton rows are visible until the response resolves
2. The Create Agent CTA remains enabled (not blocked)

**Observation 2 — Final render**:
1. After resolution, real rows replace the skeleton

---

### TC-LOADING-002: Slow delete disables confirm and shows spinner

**Action**:
1. Open the delete confirmation modal
2. Click `Delete` against a deliberately slow `DELETE /agent/delete_agent` (>3s)

**Observation 1 — Button state during request**:
1. The confirm button has `disabled` set
2. A spinner is visible inside the confirm button
3. The modal cannot be dismissed (no Escape-close while in-flight)

**Observation 2 — Resolution**:
1. After the response, the modal closes and the row disappears (on 200)

---

### TC-LOADING-003: Concurrent delete 404 reconciles via refresh

**Preconditions**: another user just deleted the same agent.

**Action**:
1. Open the row delete confirmation
2. Click `Delete`

**Observation 1 — 404 toast**:
1. Toast title equals `Agent not found`

**Observation 2 — UI converges on refresh**:
1. A subsequent `fl.refresh()` (or page reload) removes the row

**API mock**: `DELETE /agent/delete_agent` → 404 `{ "detail": "Agent not found" }`.

---

### TC-EDGE-001: Whitespace-only search is treated as empty

**Action**:
1. Visit `/agents`
2. Type `   ` (only spaces) into the search bar
3. Wait for debounce

**Observation 1 — Request shape**:
1. The next `POST /agent/list` either omits `search` or sends an empty string — NOT the whitespace literal
2. Table reverts to default (unfiltered) list

---

### TC-EDGE-002: Search trims surrounding whitespace

**Action**:
1. Visit `/agents`
2. Type ` acme ` (with leading/trailing spaces) into the search bar
3. Wait for debounce

**Observation 1 — Trimmed body**:
1. `POST /agent/list` body contains `"search": "acme"` (no surrounding whitespace)

---

### TC-EDGE-003: Search accepts unicode/html-ish input without XSS

**Action**:
1. Visit `/agents`
2. Type `<script>alert(1)</script>` (or an emoji 🚀) into the search bar

**Observation 1 — Verbatim transmission**:
1. The `POST /agent/list` body contains the literal `<script>alert(1)</script>` (or emoji) in `search`

**Observation 2 — No XSS execution**:
1. `window.alert` is not invoked
2. The DOM does not contain an evaluated `<script>` tag
3. The literal text appears in the search input as `value` (rendered as text)

---

### TC-EDGE-004: Very long search query (> 500 chars) does not crash

**Action**:
1. Visit `/agents`
2. Paste a 600-character string into the search bar

**Observation 1 — Behaviour**:
1. Either the input accepts the value and a single `POST /agent/list` fires with the long search, OR a truncation message appears
2. No client crash; the page stays interactable

---

### TC-EDGE-005: Pasting newlines into search strips them

**Action**:
1. Visit `/agents`
2. Paste a multiline value (`line1\nline2`) into the search bar

**Observation 1 — Single-line value**:
1. The search input's `value` contains no `\n`
2. The `POST /agent/list` `search` field is single-line

---

### TC-EDGE-006: Drawer Apply with no changes is a no-op

**Action**:
1. Visit `/agents`
2. Click `Filters`
3. Without changing anything, click `Apply`

**Observation 1 — No new list fetch**:
1. Zero new `POST /agent/list` requests are recorded after Apply
2. The drawer closes

---

### TC-EDGE-007: Delete last row on last page steps page index back

**Preconditions**: 11 total rows; page_size 10; user navigates to page 2 (1 row).

**Action**:
1. Visit `/agents`
2. Click `Next` to go to page 2
3. Open the row's action menu → Delete → confirm

**Observation 1 — Defensive page step-back**:
1. `handleDelete` computes `lastPage = max(1, ceil(10/10)) = 1`
2. A `POST /agent/list` fires with `"page": 1`

---

### TC-EDGE-008: Row click on a row missing `id` is a no-op

**Preconditions**: malformed response missing `id` on a row.

**Action**:
1. Visit `/agents`
2. Click the malformed row

**Observation 1 — No navigation**:
1. URL is still `/agents`
2. No client error is thrown

---

### TC-EDGE-009: Row click with missing `agent_type` falls back to inbound

**Preconditions**: row returned without `agent_type`.

**Action**:
1. Visit `/agents`
2. Click the row

**Observation 1 — Fallback path**:
1. URL becomes `/agents/edit/inbound/<id>`

---

### TC-EDGE-010: Search debounce — rapid typing fires at most one request

**Action**:
1. Visit `/agents`
2. Type `abcdef` quickly (within the debounce window)

**Observation 1 — Single request after debounce**:
1. After the debounce, at most one `POST /agent/list` is recorded for the final value `abcdef` (⚠ unverified for `useFacetedList` specifically; the legacy atom path drops in-flight)

---

### TC-EDGE-011: Search with no matches renders no-results state

**Action**:
1. Visit `/agents`
2. Type a query that yields zero rows (mocked or known empty)

**Observation 1 — Empty results state**:
1. The empty-state body renders inside the table
2. A `Clear filters` shortcut is available

---

### TC-EDGE-012: Offline / network failure on list recovers on retry

**Action**:
1. Visit `/agents` while network is offline
2. Restore network
3. Retry (or wait for next fetch)

**Observation 1 — First attempt empty**:
1. Skeleton clears; table shows the empty state

**Observation 2 — Retry succeeds**:
1. A subsequent successful `POST /agent/list` refills the table

---

### TC-A11Y-001: Tab order through the toolbar reaches every control

**Action**:
1. Visit `/agents`
2. Press `Tab` repeatedly starting from the URL bar / page body

**Observation 1 — Tab sequence**:
1. Focus moves through Search → Filters button → Create Agent → first sortable column header
2. No focusable toolbar element is skipped

---

### TC-A11Y-002: Enter on a sortable column header triggers sort

**Action**:
1. Visit `/agents`
2. Focus the `Agent` column header via Tab
3. Press the `Enter` key

**Observation 1 — Sort request fires**:
1. A `POST /agent/list` request is recorded with updated `sort_by` / `sort_order` (same behaviour as click)

---

### TC-A11Y-003: Delete modal traps focus and restores on close

**Action**:
1. Visit `/agents`
2. Open the row delete confirmation modal
3. Press `Tab` repeatedly to verify focus cycles inside the modal
4. Press `Escape`

**Observation 1 — Focus trap**:
1. Tabbing cycles between focusable elements inside the modal only
2. Focus never leaves the modal during cycling

**Observation 2 — Restoration on close**:
1. Escape closes the modal
2. Focus returns to the row action menu trigger that opened it

---

### TC-A11Y-004: Error toast is announced via aria-live

**Action**:
1. Trigger a delete error (e.g. 404)

**Observation 1 — Toast accessibility**:
1. The toast element has `role="alert"` or `aria-live="polite"`
2. Screen readers announce the toast title without manual focus

---

### TC-A11Y-005: CreateAgentModal cards are keyboard-activatable

**Action**:
1. Visit `/agents`
2. Click `Create Agent`
3. Tab into the modal

**Observation 1 — Tab order**:
1. Focus moves to the `Outbound` card first, then the `Inbound` card (DOM order)
2. Both cards have a visible focus ring

**Observation 2 — Enter activates focused card**:
1. Pressing `Enter` on the focused card closes the modal and navigates to the corresponding `/agents/create/{type}` route

---

### TC-FULL-001: Lifecycle — create → edit → delete an agent end-to-end

**Preconditions**:
- User authenticated against a real backend (no mocks)
- Test agent name prefixed `__e2e__` for cleanup

**Action**:
1. Visit `/agents`
2. Click `Create Agent` and pick `Inbound`
3. On `/agents/create/inbound/basics`, fill the create form for an `__e2e__` agent and save
4. Land on `/agents/edit/inbound/<id>/overview`, mutate name + description, save
5. Navigate back to `/agents` and confirm the row appears with the new name
6. Open the row action menu, click Delete, confirm

**Observation 1 — Create succeeds and routes to edit**:
1. A success toast appears after Create
2. URL becomes `/agents/edit/inbound/<id>/overview`

**Observation 2 — Edit save succeeds**:
1. A success toast appears after edit Save
2. The row on `/agents` shows the new name and description after navigation

**Observation 3 — Delete succeeds and row disappears**:
1. Toast title equals `Agent deleted successfully`
2. The row is no longer in the table

**Cleanup** (in `try/finally`):
1. Delete the `__e2e__` agent via `DELETE /agent/delete_agent` if it still exists
2. Clear cookies

---

### TC-FULL-002: Walk the entire agents list page end-to-end

**Preconditions**:
- Authenticated; one seeded `__e2e__` agent exists

**Action**:
1. Visit `/agents`
2. Assert headings + default sort + page-size selector defaults
3. Type into the search bar (free text), then `name:hotel` token, then clear
4. Open `Filters` → tick `Type=Inbound` + `Status=Active` → Apply
5. Clear all filters
6. Sort by Name, then Type, then Last Updated
7. Change page-size to `25`
8. Open the per-row action menu → Cancel delete
9. Re-open and confirm delete on the seeded `__e2e__` agent
10. Click `Create Agent` → press `Escape`
11. Click `Create Agent` again → pick `Inbound`

**Observation 1 — Toolbar wiring fires correct list calls**:
1. Each affordance (search, filter, sort, paginate) records the expected `POST /agent/list` body

**Observation 2 — Delete confirm-cancel preserves row**:
1. Cancel does not fire `DELETE /agent/delete_agent`
2. Confirm fires it; toast `Agent deleted successfully` appears
3. Row is removed

**Observation 3 — Create modal handles Escape**:
1. Pressing Escape closes the modal without navigation
2. Re-opening and picking Inbound routes to `/agents/create/inbound`

**Cleanup** (in `try/finally`):
1. Sweep any `__e2e__` agents from `/agent/list` and delete them

---

## Expected Toast Messages

Sonner toasts via `showToast` (`src/utils/toast.tsx`); errors run through
`handleApiError` (`src/utils/helpers.ts`) which passes backend `detail` (when
it's a string) as the toast **title** with no description, or falls back to
`Something went wrong. Please try again.` when `detail` is an array or absent.

| Trigger                                        | Toast title                                  | Toast description | Variant  |
| ---------------------------------------------- | -------------------------------------------- | ----------------- | -------- |
| Delete success                                 | `Agent deleted successfully`                 | —                 | success  |
| Delete backend 404                             | `Agent not found`                            | —                 | error    |
| Delete backend 401                             | `Invalid token` (or `Could not validate credentials`) | —        | error    |
| Delete backend 5xx with string `detail`        | `Internal Server Error` (verbatim from backend) | —              | error    |
| Delete backend 422 (array `detail`)            | `Something went wrong. Please try again.`    | —                 | error    |
| Any error where `detail` is not a string       | `Something went wrong. Please try again.`    | —                 | error    |
| List failure                                   | (none — empty state renders, no toast)       | —                 | —        |
| Facets failure                                 | (none — drawer renders empty counts)         | —                 | —        |

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-NAV-*` test case above)

- [x] Unauthenticated access → middleware redirect — see TC-NAV-001
- [x] Slow `POST /agent/list` — see TC-LOADING-001
- [x] Empty org — see TC-HAPPY-002
- [x] Agent with no phone numbers → Status pill `Inactive` — covered in UI Elements + TC-HAPPY-001 fixture variants
- [x] Agent with multiple phone numbers → stacked `PhoneNumberDisplay` rows — covered implicitly in TC-HAPPY-001
- [x] Description longer than 280px-truncate column — covered in UI Elements
- [x] `updated_at` missing → em-dash placeholder — covered in UI Elements
- [x] `agent_type` missing → row click falls back to inbound — see TC-EDGE-009
- [x] `record.id` missing → row click is a no-op — see TC-EDGE-008
- [x] Search debounce — see TC-EDGE-010
- [x] Drawer Apply with no changes — see TC-EDGE-006
- [x] Delete last row on last page — see TC-EDGE-007
- [x] CreateAgentModal Escape key — see TC-NAV-010

---

## Business Rules

- The "Active" pill is a UI derivation from `phone_number?.length > 0` — it is NOT the backend `is_active` flag. An agent can be `is_active=true` and still render "Inactive" if no phone is attached.
- Backend deletes are cascading: deleting an agent also deletes its config rows and phone bindings (see Postman: "200 OK (hard delete + cascade)").
- Type chooser is the only way the list page reaches the create editor — there is no direct "Create Inbound" button. The two-step flow is intentional so the editor can preset DIRECTION_STYLES and section nav.
- Default sort is `updated_at` desc so recently-touched agents bubble to the top; this is configured in `agentsListConfig.defaultSort` and cannot be overridden by the user via URL today.
- Page-size selector options are `[10, 25, 50, 100]`; default is 10.
- Search uses the token-search syntax (`field:value` or bare text); only `name` is exposed as a typed field via `searchField` in `agentsListConfig`.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Page heading is rendered as a real `<h1>` — covered in TC-HAPPY-001
- [x] "Create Agent" button is reachable via Tab — see TC-A11Y-001
- [x] Token search input has an associated label / `aria-label` — see TC-A11Y-001
- [x] Filters button has visible text + count badge — see TC-A11Y-001
- [x] Sortable column headers are real `<th role="columnheader">` and respond to Enter — see TC-A11Y-002
- [x] Per-row action menu trigger has an accessible name — see TC-A11Y-003
- [x] Delete confirmation modal traps focus and restores on close — see TC-A11Y-003
- [x] Status pill includes text, not only colour — covered in UI Elements
- [x] `<PhoneNumberDisplay>` flag is decorative — covered in UI Elements
- [x] CreateAgentModal cards are keyboard-activatable — see TC-A11Y-005
- [x] Error toast announced via aria-live — see TC-A11Y-004

---

## Scenario → TC ID cross-reference

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| PS-1            | TC-HAPPY-001      | list renders the populated table                                     |
| PS-2            | TC-HAPPY-002      | empty list renders the no-agents empty state                         |
| PS-3            | TC-HAPPY-003      | search by free-text query refires the list                           |
| PS-4            | TC-HAPPY-004      | filter by Type=outbound via the drawer                               |
| PS-5            | TC-HAPPY-005      | sort by Name asc                                                     |
| PS-6            | TC-HAPPY-006      | page-size change resets to page 1                                    |
| PS-7            | TC-HAPPY-007      | row click navigates to the editor                                    |
| PS-8            | TC-HAPPY-008      | delete from row menu succeeds                                        |
| PS-9            | TC-HAPPY-009      | create modal opens and routes to inbound                             |
| FS-1            | TC-ERROR-001      | list 401 — empty state, no toast                                     |
| FS-2            | TC-ERROR-002      | list 500 falls back to empty state                                   |
| FS-3            | TC-ERROR-003      | facets 500 — drawer renders empty counts                             |
| FS-4            | TC-ERROR-004      | delete 404 — row stays, toast surfaces                               |
| FS-5            | TC-ERROR-005      | delete 401 — invalid token toast                                     |
| FS-6            | TC-ERROR-006      | delete 422 falls back to generic toast                               |
| FS-7            | TC-ERROR-007      | delete 500 — backend detail string surfaces                          |
| FS-8            | TC-EDGE-007       | delete last row on last page steps page index back                   |
| FS-9            | TC-EDGE-010       | search debounce — rapid typing fires at most one request             |
| FS-10           | (covered in PS-5 assertions) | sort by unknown field — backend silent fallback           |
| FS-11           | TC-EDGE-008       | row click on a row missing id is a no-op                             |
| FS-12           | TC-EDGE-009       | row click with missing agent_type falls back to inbound              |
| FS-13           | (informational — list never POSTs create) | duplicate-name 409 surfaces only on create page  |
| FS-14           | TC-EDGE-006       | drawer Apply with no changes is a no-op                              |
| FS-15           | TC-NAV-001        | unauthenticated visit redirects to login                             |
| FS-16           | TC-NAV-010        | createAgentModal Escape key cancels without navigation               |
| AL-001          | TC-NAV-001        | unauthenticated visit redirects to login                             |
| AL-002          | TC-NAV-002        | expired token redirects to login and clears cookie                   |
| AL-003          | TC-NAV-003        | non-member is denied access to the agents list                       |
| AL-004          | TC-ERROR-010      | list 400 renders empty state without toast                           |
| AL-005          | TC-ERROR-009      | delete 401 surfaces error toast without redirect                     |
| AL-006          | TC-ERROR-008      | delete 403 surfaces forbidden toast                                  |
| AL-007          | TC-ERROR-004      | delete 404 surfaces not-found toast                                  |
| AL-008          | TC-ERROR-011      | list 500 falls back to empty state                                   |
| AL-009          | TC-EDGE-012       | list network failure renders empty then recovers on retry            |
| AL-010          | TC-LOADING-001    | slow list keeps skeleton visible                                     |
| AL-011          | TC-LOADING-002    | slow delete disables confirm button and shows spinner                |
| AL-012          | TC-LOADING-003    | concurrent delete 404 reconciles via refresh                         |
| AL-013          | TC-EDGE-001       | whitespace-only search is treated as empty                           |
| AL-014          | TC-EDGE-002       | search trims surrounding whitespace                                  |
| AL-015          | TC-EDGE-003       | search accepts unicode and html-ish input without xss                |
| AL-016          | TC-EDGE-004       | very long search query does not crash                                |
| AL-017          | TC-EDGE-005       | pasting newlines into search strips them                             |
| AL-018          | TC-HAPPY-002      | empty list renders the no-agents empty state                         |
| AL-019          | TC-EDGE-011       | search with no matches renders no-results state                      |
| AL-020          | TC-NAV-004        | pagination disables prev on the first page                           |
| AL-021          | TC-NAV-005        | pagination disables next on the last page                            |
| AL-022          | TC-NAV-006        | sort by Name cycles asc desc and reset                               |
| AL-023          | TC-NAV-007        | sort by Type orders rows by agent_type                               |
| AL-024          | TC-NAV-008        | sort by Last Updated cycles direction                                |
| AL-025          | TC-NAV-009        | delete confirmation cancel preserves the row                         |
| AL-026          | TC-A11Y-001       | tab order through toolbar reaches every control                      |
| AL-027          | TC-A11Y-002       | Enter on sortable header triggers sort                               |
| AL-028          | TC-A11Y-003       | delete modal traps focus and restores on close                       |
| AL-029          | TC-A11Y-004       | error toast is announced via aria-live                               |
| AL-030          | TC-A11Y-005       | create modal cards are keyboard activatable                          |
| AL-LIFECYCLE    | TC-FULL-001       | lifecycle: create then edit then delete an agent end to end          |
| AL-FULL         | TC-FULL-002       | walks the entire agents list page end to end                         |
