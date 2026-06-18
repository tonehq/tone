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

## User Workflow Steps

Step-by-step actions per major flow. Used to derive `test(...)` blocks in
`e2e/dashboard/agents.spec.ts`. Toast assertions use
`page.locator('[data-sonner-toast]')`.

**WF-1: Browse and search the list** (positive — US-1, US-2)

1. User authenticates and navigates to `/agents` → expected: heading "Agents" + subtitle "Manage your voice agents" visible; `POST /agent/list` fires with default `{ page: 1, page_size: 10, sort_by: 'updated_at', sort_order: 'desc' }`.
2. With 1+ rows in the response → expected: count `Badge` next to the heading shows `total`; rows render with name + truncated description, status pill, type badge, phone list, and timestamp.
3. User types `acme` into the search bar → expected: after the token-search debounce, `POST /agent/list` fires with `search: 'acme'` (free-text token).
4. User clicks the Filters button → expected: `FacetFilterDrawer` opens, sections "Type" and "Status" load from `POST /agent/facets` with counts.
5. User selects `Type: Inbound` and applies → expected: list re-fires with `filters: [{ field: 'agent_type', operator: 'in', value: ['inbound'] }]`; drawer filter count badge reads `1`.
6. User clicks the toolbar's clear button → expected: search tokens + drawer selections both reset, list re-fetches with the default body.

**WF-2: Sort and paginate** (positive — US-3, US-4)

1. User clicks the "Agent" column header → expected: `sort_by: 'name', sort_order: 'asc'` in the next `POST /agent/list`; clicking again flips to `desc`.
2. User clicks the "Type" header → expected: `sort_by: 'agent_type'`.
3. User opens the page-size selector and picks `25` → expected: `POST /agent/list` fires with `page_size: 25, page: 1`.
4. User clicks the next-page chevron → expected: `page: 2` in the next request.

**WF-3: Open an existing agent in the editor** (positive — US-5)

1. User clicks any non-action cell of a row → expected: `router.push('/agents/edit/inbound/<id>')` (or `outbound` per the row's `agent_type`).
2. URL changes; the editor shell hydrates from `GET /agent/get_agent?agent_id=<id>`. (Editor behavior is documented in `agents-edit.md`.)

**WF-4: Delete an agent from the row menu** (positive — US-6)

1. User clicks the per-row 3-dot action menu → expected: dropdown shows "Edit" and "Delete".
2. User clicks "Delete" → expected: confirmation modal opens with the agent's name in the title; primary button labeled "Delete" (danger).
3. User confirms → expected: `DELETE /agent/delete_agent?agent_id=<id>` fires; on 200, toast title `Agent deleted successfully`, the row disappears, `fl.refresh()` re-fires `/agent/list`.

**WF-5: Create flow — type chooser** (positive — US-7)

1. User clicks "Create Agent" in the header → expected: `CreateAgentModal` opens with title "Choose type of agent" and two type cards.
2. User clicks "Inbound" → expected: modal closes, `router.push('/agents/create/inbound')`.
3. (Restart) User triggers the modal again, picks Outbound → expected: `router.push('/agents/create/outbound')`.

**WF-6: Empty state** (positive — US-1)

1. Org has zero agents → expected: `POST /agent/list` returns `{ items: [], total: 0 }`; table body renders the Bot icon, "No agents yet", and an inline "Create Agent" button that opens the same `CreateAgentModal`.

**WF-7: Auth gating** (negative)

1. User without a `tone_access_token` cookie visits `/agents` → expected: `src/middleware.ts` returns 307 → `/auth/login?redirect=%2Fagents`.
2. After login → expected: post-login redirect lands back on `/agents`.

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

## Success Scenarios

**PS-1: List renders the populated table** (US-1)

- **Preconditions**: authenticated; org has 1 agent.
- **Steps**: navigate to `/agents`.
- **Expected outcome**: heading + subtitle render; count `Badge` shows `1`; one row with name `Acme Support Bot`, status pill "Active" (phone present), type badge "INBOUND", phone display `+15551234567`.
- **Mock API** (`POST /agent/list`, 200):
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
    "page_size": 10
  }
  ```

**PS-2: Empty list shows the no-agents empty state** (US-1)

- **Preconditions**: authenticated; org has no agents.
- **Steps**: navigate to `/agents`.
- **Expected outcome**: table body shows the Bot icon, "No agents yet", subtitle, and an inline "Create Agent" button (count `Badge` is hidden because `fl.total === 0`).
- **Mock API** (`POST /agent/list`, 200): `{ "items": [], "total": 0, "page": 1, "page_size": 10 }`

**PS-3: Search by free-text query** (US-2)

- **Preconditions**: at least one matching agent.
- **Steps**: type `acme` into the search bar; wait for debounce.
- **Expected outcome**: `POST /agent/list` body contains `"search": "acme"`; table re-renders with matches.
- **Mock API** (`POST /agent/list`, 200): same shape as PS-1 with `total: 1`.

**PS-4: Filter by Type=outbound via the drawer** (US-2)

- **Preconditions**: PS-1 state, with both inbound and outbound agents.
- **Steps**: click Filters → tick `Outbound` under Type → Apply.
- **Expected outcome**: `POST /agent/list` body contains `"filters": [{ "field": "agent_type", "operator": "in", "value": ["outbound"] }]`; table shows only outbound agents.
- **Mock API** (`POST /agent/list`, 200):
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
    "page_size": 10
  }
  ```

**PS-5: Sort by Name asc** (US-3)

- **Preconditions**: at least 2 agents.
- **Steps**: click the "Agent" column header once.
- **Expected outcome**: `POST /agent/list` re-fires with `"sort_by": "name", "sort_order": "asc"`; table reorders.

**PS-6: Page-size change resets to page 1** (US-4)

- **Preconditions**: total > 25.
- **Steps**: pick `25` from the rows-per-page selector.
- **Expected outcome**: `POST /agent/list` fires with `page: 1, page_size: 25`.

**PS-7: Row click navigates to the editor** (US-5)

- **Preconditions**: PS-1 (one inbound agent).
- **Steps**: click the row's Name cell.
- **Expected outcome**: URL changes to `/agents/edit/inbound/a1c5e8b2-9d3f-4e7a-8b1c-2f4d6e8a1b3c`. (Editor hydration is covered in `agents-edit.md`.)

**PS-8: Delete from row menu** (US-6)

- **Preconditions**: PS-1.
- **Steps**: open the row action menu → Delete → confirm.
- **Expected outcome**: `DELETE /agent/delete_agent?agent_id=...` returns 200; toast title `Agent deleted successfully`; row disappears; `fl.refresh()` re-fires `/agent/list`.
- **Mock API** (`DELETE /agent/delete_agent`, 200): `{ "message": "Agent deleted successfully" }`

**PS-9: Create modal opens and routes to inbound** (US-7)

- **Preconditions**: any.
- **Steps**: click the header "Create Agent" button → click the "Inbound" card.
- **Expected outcome**: modal closes; `router.push('/agents/create/inbound')`; the URL changes accordingly.

---

## Failure Scenarios

**FS-1: List returns 401 (token rejected)**

- **Preconditions**: authenticated user with an expired token mid-session.
- **Mock API** (`POST /agent/list`, 401): `{ "detail": "Could not validate credentials" }`
- **Expected UI**: `fl.listLoading` flips to false; the table shows the empty state ("No agents yet") because `fl.rows` stays empty — there is no inline list-level error banner. Axios does NOT auto-redirect to login on 401 today. ⚠ unverified — confirm no toast bubbles up.

**FS-2: List returns 500 (backend down)**

- **Mock API** (`POST /agent/list`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: `useFacetedList`'s loader catches; table shows empty state; no destructive client crash; loading spinner clears.

**FS-3: Facets endpoint returns 500**

- **Mock API** (`POST /agent/facets`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: drawer still opens; sections render with `facetsLoading` skeletons that resolve to empty counts; user can still apply selections (though counts read 0).

**FS-4: Delete returns 404 (agent already gone)**

- **Mock API** (`DELETE /agent/delete_agent`, 404): `{ "detail": "Agent not found" }`
- **Expected UI**: `handleApiError` surfaces the `detail` as a toast title `Agent not found`; the row stays in the table; subsequent `fl.refresh()` would remove it on the next list fetch.

**FS-5: Delete returns 401 (invalid token)**

- **Mock API** (`DELETE /agent/delete_agent`, 401): `{ "detail": "Invalid token" }`
- **Expected UI**: toast title `Invalid token`; row stays.

**FS-6: Delete returns 422 (missing agent_id query param)**

- **Mock API** (`DELETE /agent/delete_agent`, 422):
  ```json
  { "detail": [{ "type": "missing", "loc": ["query", "agent_id"], "msg": "Field required", "input": null }] }
  ```
- **Expected UI**: `handleApiError` sees a non-string `detail` and falls back to `Something went wrong. Please try again.` ⚠ unverified — confirm fallback text appears.

**FS-7: Delete returns 500**

- **Mock API** (`DELETE /agent/delete_agent`, 500): `{ "detail": "Internal Server Error" }`
- **Expected UI**: toast title `Internal Server Error`; row stays.

**FS-8: Delete of the last row on the last page**

- **Preconditions**: page 2 of 2, page-size 10, with exactly 11 total rows; user deletes the single row on page 2.
- **Mock API** (`DELETE /agent/delete_agent`, 200): `{ "message": "Agent deleted successfully" }`
- **Expected UI**: `handleDelete` computes `lastPage = max(1, ceil(10/10)) = 1`; calls `fl.handlePaginationChange(1, 10)`; `/agent/list` re-fires with `page: 1`.

**FS-9: Search debounce — rapid typing fires only the final request**

- **Steps**: type `abcdef` quickly into the search bar.
- **Expected UI**: at most one `POST /agent/list` is sent after the debounce window — earlier in-flight requests are dropped by `useFacetedList`'s in-flight token (mirrors the `paginatedAgentsAtom` pattern). ⚠ unverified for `useFacetedList` specifically; covered for the legacy atom path.

**FS-10: Sort by an unknown field (defensive fallback)**

- **Preconditions**: malformed client mutation sends `sort_by: "bogus"`.
- **Mock API** (`POST /agent/list`, 200): same shape as PS-1; backend silently sorts by `updated_at` desc per Postman "200 OK (invalid sort falls back silently)".
- **Expected UI**: list renders; no error toast.

**FS-11: Row click on a row missing `id`**

- **Preconditions**: malformed response (defensive — should not happen in prod).
- **Steps**: click such a row.
- **Expected UI**: `handleEdit` early-returns; no navigation; no error.

**FS-12: `agent_type` missing on a row**

- **Preconditions**: row returned without `agent_type`.
- **Steps**: click the row.
- **Expected UI**: `handleEdit` falls back to `inbound`; router pushes `/agents/edit/inbound/<id>`.

**FS-13: Backend duplicate-name response is not surfaced here**

- Create endpoint 409s are surfaced by the *create* flow, NOT by the list page. The list page only triggers `DELETE` and `POST /agent/list`; it never calls `POST /agent/create_agent`. (Documenting this explicitly so spec tests don't accidentally assert a toast that won't appear on `/agents`.)

**FS-14: Drawer Apply with no selections is a no-op**

- **Steps**: open the drawer, change nothing, click Apply.
- **Expected UI**: the drawer closes; no new `POST /agent/list` fires (the underlying `facetSelections` are unchanged).

**FS-15: Auth-gating redirect**

- **Preconditions**: no `tone_access_token` cookie.
- **Steps**: visit `/agents`.
- **Expected UI**: 307 redirect to `/auth/login?redirect=%2Fagents`.

**FS-16: Create modal — Escape key cancels without navigation**

- **Steps**: click "Create Agent" → press Escape.
- **Expected UI**: modal closes; no `router.push` call; URL stays `/agents`.

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

## Edge Cases

- [ ] Unauthenticated access → middleware redirect to `/auth/login?redirect=%2Fagents`
- [ ] Slow `POST /agent/list` → `CustomTable` skeleton renders until response
- [ ] Empty org → empty-state Bot icon + "No agents yet" + Create button; count badge hidden
- [ ] Agent with no phone numbers → Status pill reads "Inactive" (amber), even if `is_active=true` on the backend (badge is purely UI-derived from `phone_number?.length`)
- [ ] Agent with multiple phone numbers → Phone column renders one `<PhoneNumberDisplay>` per entry, vertically stacked
- [ ] Description longer than the 280px-truncate column width → ellipsis (CSS `truncate max-w-[280px]`)
- [ ] `updated_at` missing → em-dash placeholder
- [ ] `agent_type` missing → row click falls back to `/agents/edit/inbound/<id>`
- [ ] `record.id` missing → row click is a no-op (defensive)
- [ ] Search debounce — rapid typing fires at most one `POST /agent/list` (in-flight token drops stale responses)
- [ ] Drawer Apply with no changes → no extra `POST /agent/list`
- [ ] Delete last row on last page → page index steps back to the new last page via `lastPage = max(1, ceil((total-1)/page_size))`
- [ ] Concurrent delete + refresh — `fl.refresh()` after delete only re-fires once
- [ ] CreateAgentModal Escape key → closes without navigation
- [ ] CreateAgentModal — both cards have `cursor-pointer` + focus-visible ring; Tab order is Outbound → Inbound (DOM order)
- [ ] Filter chip count badge — drawer button hides the badge when `drawerFilterCount === 0`

---

## Business Rules

- The "Active" pill is a UI derivation from `phone_number?.length > 0` — it is NOT the backend `is_active` flag. An agent can be `is_active=true` and still render "Inactive" if no phone is attached.
- Backend deletes are cascading: deleting an agent also deletes its config rows and phone bindings (see Postman: "200 OK (hard delete + cascade)").
- Type chooser is the only way the list page reaches the create editor — there is no direct "Create Inbound" button. The two-step flow is intentional so the editor can preset DIRECTION_STYLES and section nav.
- Default sort is `updated_at` desc so recently-touched agents bubble to the top; this is configured in `agentsListConfig.defaultSort` and cannot be overridden by the user via URL today.
- Page-size selector options are `[10, 25, 50, 100]`; default is 10.
- Search uses the token-search syntax (`field:value` or bare text); only `name` is exposed as a typed field via `searchField` in `agentsListConfig`.

---

## Accessibility Requirements

- [ ] Page heading is rendered as a real `<h1>` (`role: heading, level: 1`)
- [ ] "Create Agent" button is reachable via Tab and activates on Enter/Space
- [ ] Token search input has an associated label / `aria-label`
- [ ] Filters button has visible text + count badge; screen readers announce "Filters, 2"
- [ ] Sortable column headers are real `<th role="columnheader">` and respond to Enter
- [ ] Per-row action menu trigger has an accessible name (e.g. `aria-label="Agent actions"`)
- [ ] Delete confirmation modal traps focus and restores it on close (Radix/shadcn default via `CustomModal`)
- [ ] Status pill includes text ("Active" / "Inactive"), not only color
- [ ] `<PhoneNumberDisplay>` flag is decorative (alt-text or aria-hidden); the formatted number is read by screen readers
- [ ] `CreateAgentModal` cards are keyboard-activatable (`CustomButton` with `type="text"` renders as a real `<button>`)

---

## Appended Scenarios (gap-fill, ID prefix `AL-`)

These rows extend the original PS/FS coverage with auth/error-state/network/a11y/list-specific/lifecycle scenarios so `/generate-tests` can produce a comprehensive `agents.spec.ts`. They use real-backend conventions (`__e2e__` prefix, try/finally cleanup) — not `page.route` mocks — unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-001 | Visit `/agents` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Fagents` | `unauthenticated visit redirects to login` |
| AL-002 | Visit `/agents` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Fagents`; expired cookie cleared on the login response | `expired token redirects to login and clears cookie` |
| AL-003 | Logged-in non-member opens `/agents` (org switched away) | Access-denied state OR redirect to `/home`; no `POST /agent/list` fires | `non-member is denied access to the agents list` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-004 | `POST /agent/list` returns 400 (malformed filter) | Empty table state; no destructive crash; no toast (list errors are swallowed) | `list 400 renders empty state without toast` |
| AL-005 | Token expires between page load and a delete confirm (401 on DELETE) | Toast `Invalid token` (or `Could not validate credentials`); row remains; user is NOT auto-redirected to login | `delete 401 surfaces error toast without redirect` |
| AL-006 | Member role attempts delete on an owner-only agent → 403 | Toast `Forbidden` (or backend `detail` verbatim); row remains | `delete 403 surfaces forbidden toast` |
| AL-007 | Delete an agent that was already removed by another user → 404 | Toast `Agent not found`; row stays until `fl.refresh()`, then disappears | `delete 404 surfaces not-found toast` |
| AL-008 | `POST /agent/list` returns 500 mid-search | Skeleton clears; empty-state body renders; no client crash | `list 500 falls back to empty state` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-009 | Offline / network failure during `POST /agent/list` | Skeleton clears; table shows empty state; subsequent successful retry refills the table | `list network failure renders empty then recovers on retry` |
| AL-010 | Slow `POST /agent/list` (>3s) | Skeleton rows visible the whole time; Create Agent CTA remains enabled | `slow list keeps skeleton visible without blocking the page` |
| AL-011 | Slow `DELETE /agent/delete_agent` (>3s) | Confirm button disabled + spinner while in-flight; modal blocks dismiss until response | `slow delete disables confirm button and shows spinner` |
| AL-012 | Concurrent delete — same agent deleted by another tab returns 404 mid-confirm | Toast `Agent not found`; UI converges on next `fl.refresh()` | `concurrent delete 404 reconciles via refresh` |

### Input edge cases (search bar)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-013 | Type only whitespace into the search bar | No `POST /agent/list` body field `search` is sent (or sent as empty) — table reverts to default | `whitespace-only search is treated as empty` |
| AL-014 | Search query with leading/trailing spaces (` acme `) | Backend or frontend trims; `search` body contains `acme` | `search trims surrounding whitespace` |
| AL-015 | Search query with special characters (`<script>alert(1)</script>`, emoji, unicode) | Query sent verbatim; results render without breaking the UI; no XSS execution | `search accepts unicode and html-ish input without xss` |
| AL-016 | Search query >500 characters | Either accepted in one request or truncated with helpful message; no client crash | `very long search query does not crash the page` |
| AL-017 | Paste a multiline value into the single-line search input | Newlines stripped; resulting `search` value is single-line | `pasting newlines into search strips them` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-018 | Org has zero agents | Empty-state Bot icon + "No agents yet" + inline "Create Agent" CTA; count badge hidden | `empty list renders the no-agents empty state` |
| AL-019 | Search with no matches | "no results" empty state for the filtered case; clear-filters shortcut available | `search with no matches renders no-results state` |
| AL-020 | Pagination — first page | Prev button disabled, Next enabled when more pages exist | `pagination disables prev on the first page` |
| AL-021 | Pagination — last page | Next button disabled, Prev enabled when prior pages exist | `pagination disables next on the last page` |
| AL-022 | Sort by Name (asc → desc → reset) | Three consecutive header clicks fire three `POST /agent/list` calls with `sort_by: 'name'` asc, desc, then default `updated_at` desc | `sort by Name cycles asc desc and reset` |
| AL-023 | Sort by Type | `POST /agent/list` fires with `sort_by: 'agent_type'` | `sort by Type orders rows by agent_type` |
| AL-024 | Sort by Last Updated | `POST /agent/list` fires with `sort_by: 'updated_at'` (toggling asc/desc) | `sort by Last Updated cycles direction` |
| AL-025 | Row-level delete confirmation cancel | Modal closes; no `DELETE` fired; row remains | `delete confirmation cancel preserves the row` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-026 | Tab order through the toolbar | Search → Filters button → Create Agent → first sortable column header — reachable in order | `tab order through toolbar reaches every control` |
| AL-027 | Press Enter on a sortable column header | Re-fires `POST /agent/list` with updated sort (same as click) | `Enter on sortable header triggers sort` |
| AL-028 | Delete-confirmation modal opens — focus is trapped | Focus moves inside the modal; Tab cycles within; Escape closes and restores focus to the row action menu trigger | `delete modal traps focus and restores on close` |
| AL-029 | Toast error has `role="alert"` / aria-live | Screen readers announce the toast title without manual focus | `error toast is announced via aria-live` |
| AL-030 | CreateAgentModal cards reachable via Tab + Enter | Tab order is Outbound → Inbound; Enter activates the focused card | `create modal cards are keyboard activatable` |

### Cross-flow lifecycle

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-LIFECYCLE | Walk **create → edit → delete** end-to-end in one Playwright test using the real backend: open `/agents` → click Create Agent → pick Inbound → fill the create form for a `__e2e__` agent → save → land on `/agents/edit/inbound/<id>/overview` → mutate name + description → save → navigate back to `/agents` → confirm the row appears with the new name → row delete + confirm → row gone | All three pages cooperate; toasts fire on each save/delete; cleanup runs in the same test body via `try/finally` even if assertions fail mid-way | `lifecycle: create then edit then delete an agent end to end` |

### Full lifecycle (`AL-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AL-FULL | Authenticate → visit `/agents` → assert headings + default sort + page-size selector defaults → exercise search (free-text + `name:` token + clear) → open Filters → tick Type=Inbound + Status=Active + Apply → clear all filters → sort by Name, Type, Last Updated → change page-size to 25 → open the per-row action menu → cancel delete → re-open and confirm delete on a seeded `__e2e__` agent → assert toast `Agent deleted successfully` and row removal → open Create Agent modal → press Escape to close → re-open and route to `/agents/create/inbound` | Every toolbar/table affordance fires the expected `POST /agent/list` request; the seeded agent is deleted in the same test body via `try/finally`; URL ends at `/agents/create/inbound` | `walks the entire agents list page end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| AL-001..003 | FS-15 (auth gating) | Adds expired-token + non-member cases on top of the bare unauth redirect |
| AL-004..008 | FS-1, FS-4..FS-7 | Adds 400/403 paths and standardises the 401/404/500 assertions |
| AL-009..012 | (new) | Network resilience was not previously covered |
| AL-013..017 | (new) | Input edge cases for the search bar were not previously covered |
| AL-018..025 | PS-2, PS-5, PS-6 + edge-cases | Pagination/sort/empty-state assertions are now first-class scenarios |
| AL-026..030 | Accessibility checklist | Promotes bullet items to runnable scenarios |
| AL-LIFECYCLE | (new) | Cross-flow create→edit→delete lifecycle |
| AL-FULL | (new) | Single-test sweep of the list page |
