# Feature Doc: Tools (List)

Feature documentation for the Tools list page at `/tools`. Used by
`/generate-tests tools` (or `--docs e2e/ux_flow_docs/tools.md`) to ensure all positive
and negative scenarios are covered.

A **Tool** is a per-organization function the LLM can call mid-conversation.
Tools have a `tool_type`:

- `custom` — call any external HTTP endpoint defined by URL + method +
  parameters + auth (created via `/tools/create/custom`).
- Built-in types (`google_calendar`, `google_sheets`, `send_sms`, etc.) —
  pre-wired integrations whose parameters are defined by a template and whose
  auth is OAuth or service credentials (created via `/tools/create` then
  picking a template tile).

> Template (`is_template=true`) rows live on the backend but are NOT shown in
> the list. The list shows only org-owned tools. Template rows surface only on
> `/tools/create` and are duplicated into a real tool when the user picks one.
>
> The create + edit flows live in separate docs — see `tools-create.md`,
> `tools-edit.md`, and `tools-create-custom.md`. This doc covers `/tools` only.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/tools`
- **Component (wrapper)**: `src/app/(dashboard)/tools/page.tsx`
- **Main component**: `src/components/tools/ToolsListPage.tsx`
- **Sub-components**:
  - `src/components/tools/toolsListConfig.ts` (faceted-list config — list/facets/filter-values endpoints)
  - `ActionMenu` (per-row Edit/Delete dropdown, from `@/components/shared`)
  - Internal `EmptyState` + `SelectionBar` helpers defined inline in `ToolsListPage.tsx`
- **State / data**:
  - `useFacetedList(toolsListConfig)` — paginated table state + search tokens + facets + filters
  - `useDeleteTool` from `@/lib/api/tools` (React Query mutation for single-row delete via the action menu)
  - `toolsApi.delete` (direct call, used by bulk delete to avoid invalidating the React Query cache mid-fan-out)
- **Auth required**: yes (middleware redirects to
  `/auth/login?redirect=%2Ftools` without `tone_access_token` cookie)

---

## User Stories

### US-1: Browse the tools list

**As an** agent owner, **I want to** see all tools my org has defined as a
sortable table, **so that** I can audit what my voice agents can do.

**Acceptance criteria**:

- [ ] Page header shows "Tools" (h1) + subtitle "Define external API tools your voice agents can call during conversations."
- [ ] When `total > 0`, a count `Badge` (secondary, tabular-nums) appears next to the heading
- [ ] Primary CTA "Create New Tool" appears in the header with a Plus icon
- [ ] Toolbar: token-based search bar with placeholder `Search tools… (e.g. name:weather, status:active)` + Filters drawer trigger
- [ ] Table columns: checkbox (select), Name (font-mono name + muted description), Type (color-coded badge), Method (HTTP verb pill), Endpoint URL (mono), Auth, Params, Status, actions (right-aligned)
- [ ] Loading state: `animate-pulse` skeleton rows while `fl.listLoading === true`
- [ ] Empty state (no rows, no filter): Wrench icon + "No tools yet" + subtitle + inline "Create New Tool" button
- [ ] Empty state (no rows, filter active): "No tools match your filters" + "Try clearing the search or filters." + no extra CTA

### US-2: Distinguish built-in vs custom tools

**As an** agent owner, **I want to** see at a glance whether a tool is built-in
(Google Calendar, SMS, etc.) or a custom HTTP endpoint, **so that** I can reason
about its auth + parameters.

**Acceptance criteria**:

- [ ] Custom tools render a sky-colored "Custom" badge in the Type column
- [ ] Built-in tools render a color-coded badge from `TOOL_TYPE_HEADER` (e.g. teal "Google Calendar", amber "SMS", emerald "Google Sheets")
- [ ] Unknown tool types fall through to the default amber badge with the raw `tool_type` value
- [ ] Built-in rows typically have no `url` (Endpoint URL is empty) but always have an HTTP method (defaults to POST when missing)
- [ ] `auth_type === 'none'` (or missing) renders as `-` in the Auth column; other auth types render lowercased with underscores replaced (e.g. `api_key` → `api key` with CSS `capitalize`)

### US-3: Search, filter, sort, paginate

**As an** agent owner, **I want to** filter by name, type, or status and sort the
table, **so that** I can find specific tools fast.

**Acceptance criteria**:

- [ ] Free-text token search sends `search` in the `POST /tool/list` body
- [ ] `name:weather` becomes a typed token routed to the `name` field
- [ ] Filters drawer offers two sections: Type (`tool_type` values from `POST /tool/facets`) and Status (`status` — active / inactive)
- [ ] Sortable columns are Name (`name`) and Status (`is_active`); clicking cycles asc → desc
- [ ] Default sort is `updated_at` desc (from `toolsListConfig.defaultSort`)
- [ ] Default page size is 20; selector exposes 10 / 20 / 50

### US-4: Select rows for bulk delete

**As an** agent owner, **I want to** check several rows and delete them in one
action, **so that** I can prune obsolete tools quickly.

**Acceptance criteria**:

- [ ] Header checkbox is select-all (visible state: unchecked / `indeterminate` when partial / checked when all visible rows selected)
- [ ] Per-row checkbox toggles a `Set<string>` of selected ids (stops row-click propagation)
- [ ] A floating `SelectionBar` appears at the bottom-center with the selection count, "Clear", and "Delete"
- [ ] SelectionBar uses singular "tool selected" when count is 1 and plural "tools selected" otherwise
- [ ] Clicking Delete opens a `CustomModal` titled "Delete tools" with body "Delete N selected tool(s)? This action cannot be undone." (singular vs plural text branches on count)
- [ ] Confirm fans out via `Promise.allSettled(ids.map(id => toolsApi.delete(id)))` — does NOT use the React Query mutation
- [ ] All success → toast `Tool deleted` (n=1) or `N tools deleted`; selection cleared; `fl.refresh()`
- [ ] All failure → error toast title `Bulk delete failed`, description `No tools were deleted.`; selection persists
- [ ] Partial failure → error toast title `Partial delete`, description `M of N deleted. K failed — refresh and try again.`; only the failed ids stay selected

### US-5: Per-row Edit and Delete

**As an** agent owner, **I want to** click Edit or Delete on a specific row,
**so that** I can manage tools individually without selecting checkboxes.

**Acceptance criteria**:

- [ ] Row body click → `router.push('/tools/edit/<id>')`
- [ ] Action menu Edit → same destination
- [ ] Action menu Delete opens a `Delete {toolName}?` confirm modal (from `ActionMenu`)
- [ ] Confirm runs `useDeleteTool().mutateAsync(id)` → `DELETE /tool/delete_tool?tool_id=<id>`; on success: toast `Tool deleted successfully`, the id is removed from `selectedIds` (if present), `fl.refresh()` runs

### US-6: Create new tool

**As an** agent owner, **I want to** start the create flow from the header or
empty-state CTA, **so that** I can author a new tool.

**Acceptance criteria**:

- [ ] Header "Create New Tool" → `router.push('/tools/create')` (chooser page)
- [ ] Empty-state "Create New Tool" (shown only when no filter is active) → same destination

---

## Input Specifications

### Toolbar search

| Field            | Type         | Required | Validation                                                                                       | Notes                                                                       |
| ---------------- | ------------ | -------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Search input     | tokenized    | no       | Free text or typed tokens (`name:<q>`, `status:<active\|inactive>`)                              | Debounced through `useFacetedList`; emits `search` body field               |
| Filters → Type   | multi-select | no       | Values from `POST /tool/facets` → `tool_type` (custom, google_calendar, google_sheets, send_sms, …) | Sent as `filters: [{ field: 'tool_type', operator: 'in', value: [...] }]`   |
| Filters → Status | multi-select | no       | Values from `POST /tool/facets` → `status` (active, inactive)                                    | Sent as `filters: [{ field: 'status', operator: 'in', value: [...] }]`      |

### Confirmation modals

| Field                  | Type   | Required | Validation                       | Exact Text                                                                          |
| ---------------------- | ------ | -------- | -------------------------------- | ----------------------------------------------------------------------------------- |
| Bulk-delete title      | static | n/a      | Always "Delete tools"            | `Delete tools`                                                                       |
| Bulk-delete body (n=1) | static | n/a      | Singular branch                  | `Delete 1 selected tool? This action cannot be undone.`                              |
| Bulk-delete body (n>1) | static | n/a      | Plural branch                    | `Delete N selected tools? This action cannot be undone.`                             |
| Row-delete title       | static | n/a      | `Delete {toolName}?`             | `Delete check_inventory?` (literal interpolation)                                    |
| Row-delete body        | static | n/a      | Renders the name in quotes       | `Are you sure you want to delete "check_inventory"? This action cannot be undone.`   |

---

## Navigation

| Trigger                                       | Destination                                  | Condition                                |
| --------------------------------------------- | -------------------------------------------- | ---------------------------------------- |
| Click "Create New Tool" (header)              | `/tools/create`                              | Always                                   |
| Click "Create New Tool" (empty state)         | `/tools/create`                              | `hasFilter` is false                     |
| Click row body                                | `/tools/edit/<id>`                           | Always                                   |
| Click action menu → Edit                      | `/tools/edit/<id>`                           | Always                                   |
| Click action menu → Delete → confirm          | `DELETE /tool/delete_tool?tool_id=<id>`      | Always                                   |
| Click SelectionBar → Delete → confirm         | Fan-out `DELETE /tool/delete_tool` per id    | `selectedIds.size > 0`                   |
| Change page / page size                       | New `POST /tool/list` request                | Always                                   |
| Click sortable column header                  | New `POST /tool/list` with updated sort      | Always                                   |
| No auth cookie                                | `/auth/login?redirect=%2Ftools`              | `src/middleware.ts` redirect             |

---

## API Contracts

Prefix: `/api/v1`. Verified against the Postman `Tools` folder,
`src/services/toolService.ts`, `src/lib/api/tools.ts`, and the faceted-list
helpers.

| Endpoint                  | Method | Request                                                                              | Success                                                | Error                                          |
| ------------------------- | ------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------ | ---------------------------------------------- |
| `/tool/list`              | POST   | `{ page, page_size, search?, sort_by?, sort_order?, filters?, tool_type?, is_active? }` | `200 { items: Tool[], total, page, page_size }`        | `{ "detail": "..." }`                          |
| `/tool/facets`            | POST   | `{ filters?: Filter[], search? }`                                                    | `200 { tool_type: { custom: n, … }, status: {…} }`     | `{ "detail": "..." }`                          |
| `/tool/filter-values`     | GET    | `?column_name=<field>`                                                               | `200 { column, values: string[] }`                     | `{ "detail": "..." }`                          |
| `/tool/delete_tool`       | DELETE | `?tool_id=<uuid>`                                                                    | `200 { message: "Tool deleted successfully" }`         | `400 / 404`, see below                         |
| `/tool/get_tool`          | GET    | `?tool_id=<uuid>`                                                                    | `200 Tool`                                              | `404 { "detail": "Tool not found" }`           |
| `/tool/get_template_tools`| GET    | —                                                                                    | `200 Tool[]` (only `is_template=true` rows)            | `401 { "detail": "Could not validate credentials" }` |

### Example — `POST /tool/list`

Request body (Postman exemplar):

```json
{ "search": "crm", "sort_by": "-updated_at", "is_active": true, "page": 1, "page_size": 20 }
```

200 OK:

```json
{ "items": [{ "id": "{{tool_id}}", "name": "post_to_crm", "tool_type": "custom" }], "total": 1, "page": 1, "page_size": 20 }
```

200 OK (empty):

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

### Example — `DELETE /tool/delete_tool?tool_id=<uuid>`

200 OK:

```json
{ "message": "Tool deleted successfully" }
```

400 (template tool):

```json
{ "detail": "Template tools cannot be deleted" }
```

400 (MCP-owned tool):

```json
{ "detail": "MCP tools cannot be deleted directly. Delete the MCP server instead." }
```

404 Not Found:

```json
{ "detail": "Tool not found" }
```

### Example — `GET /tool/get_template_tools`

200 OK:

```json
[
  { "id": "550e8400-tmpl-001", "name": "send_sms", "tool_type": "send_sms", "is_template": true },
  { "id": "550e8400-tmpl-002", "name": "google_calendar", "tool_type": "google_calendar", "is_template": true }
]
```

The template endpoint is consumed by `/tools/create` (the chooser page), NOT
by `/tools`. The list page filters templates out at the DB layer.

State is held in:

- `useFacetedList(toolsListConfig)` — list/sort/page/facets/filters
- `useDeleteTool` (React Query mutation) — per-row delete
- `toolsApi.delete` (direct call) — bulk delete fan-out

---

## UI Elements

| Element                       | Type            | Content / Label                                                | Behavior                                                                  |
| ----------------------------- | --------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Page heading                  | h1              | "Tools"                                                        | Static; followed by a count badge when `total > 0`                        |
| Count badge                   | Badge (secondary) | numeric count                                                  | Hidden when `total === 0`                                                  |
| Page subtitle                 | p               | "Define external API tools your voice agents can call during conversations." | Static                                                |
| Create New Tool button (header) | Button (primary) | "Create New Tool" + Plus icon                                  | `router.push('/tools/create')`                                            |
| Search bar                    | TokenSearchBar   | placeholder `Search tools… (e.g. name:weather, status:active)` | Tokenized; debounced                                                       |
| Filters button                | Button + Badge   | "Filters" + drawer filter count badge                          | Opens `FacetFilterDrawer`                                                  |
| Filter drawer                 | Drawer           | Sections "Type" + "Status"                                     | Multi-select facets from `POST /tool/facets`                                |
| Select-all checkbox           | Checkbox        | header cell, aria-label "Select all"                           | indeterminate when partial, checked when all visible rows selected         |
| Per-row checkbox              | Checkbox        | aria-label `Select {tool.name}`                                | Stops row-click propagation                                                |
| Name column                   | th + td         | mono name + muted description                                  | Sortable                                                                   |
| Type badge                    | Badge           | "Custom" / "Google Calendar" / "SMS" / "Google Sheets" / raw   | Color coded                                                                |
| Method pill                   | Badge           | "GET" / "POST" / "PUT" / "DELETE" / "PATCH"                    | Uppercased; defaults to POST when missing                                  |
| Endpoint URL                  | td              | mono URL                                                       | Empty for built-in tools                                                   |
| Auth column                   | td              | lowercased `auth_type.replace('_', ' ')` or `-` for none       | Capitalized via CSS                                                        |
| Params column                 | td              | `N param` / `N params` / `-`                                   | Count of keys in `parameters.properties`                                   |
| Status pill                   | Badge           | "Active" (emerald) / "Inactive" (muted)                        | Driven by `is_active`                                                      |
| Row action menu               | Icon button     | ⋮ (Edit / Delete)                                              | Opens `ActionMenu`; Delete opens confirm modal                              |
| SelectionBar                  | Floating bar    | "N tool(s) selected" + Clear + Delete                          | Visible only when `selectedIds.size > 0`                                   |
| Bulk-delete modal             | CustomModal     | "Delete tools" + plural/singular body                          | Confirm runs the fan-out                                                   |
| Empty state                   | div             | Wrench icon + "No tools yet" + CTA                             | CTA hidden when `hasFilter` is true; subtitle changes for filtered state    |
| Loading skeleton              | divs            | `animate-pulse` placeholder rows                               | Shown while `fl.listLoading`                                                |
| Pagination footer             | div             | "Rows per page" + page nav                                     | Native `<select>` for page size; built into `CustomTable`                   |

---

## Expected Toast Messages

Sonner toasts via `showToast` (`src/utils/toast.tsx`). Errors from the React
Query mutation `useDeleteTool` are NOT funneled through `handleApiError` —
they're caught locally in `ToolsListPage.tsx`'s `ActionMenu.onDelete` callback.
Bulk-delete errors are surfaced as titled error toasts with custom strings
(NOT the backend detail).

| Trigger                                              | Toast title                                                 | Toast description                                                     | Variant  |
| ---------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------- | -------- |
| Per-row delete success                               | `Tool deleted successfully`                                 | —                                                                     | success  |
| Per-row delete backend 400 (template/MCP)            | (backend `detail` string verbatim)                          | —                                                                     | error    |
| Per-row delete backend 404                           | `Tool not found`                                            | —                                                                     | error    |
| Bulk delete — n=1 success                            | `Tool deleted`                                              | —                                                                     | success  |
| Bulk delete — n>1 success                            | `N tools deleted`                                           | —                                                                     | success  |
| Bulk delete — all failed                             | `Bulk delete failed`                                        | `No tools were deleted.`                                              | error    |
| Bulk delete — partial failure                        | `Partial delete`                                            | `M of N deleted. K failed — refresh and try again.`                   | error    |
| List failure                                         | (none — empty state renders)                                | —                                                                     | —        |
| Facets failure                                       | (none — drawer renders empty counts)                        | —                                                                     | —        |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Browse the table renders populated rows

**Preconditions**:
- Authenticated; org has 3 tools (one custom, one Google Calendar, one SMS)

**Action**:
1. Visit `/tools`

**Observation 1 — Heading + default request**:
1. The `h1` heading reads `Tools`
2. The subtitle "Define external API tools your voice agents can call during conversations." is visible
3. Exactly one `POST /tool/list` request is recorded with body `{ page: 1, page_size: 20, sort_by: 'updated_at', sort_order: 'desc' }`

**Observation 2 — Rows render with all column data**:
1. The count Badge reads `3`
2. Each row renders Name (font-mono) and muted description
3. Type badges read `Custom`, `Google Calendar`, `SMS` respectively
4. Method pills read the expected verbs (e.g. `GET`, `POST`)
5. The custom row's Endpoint URL is visible; built-in rows have empty Endpoint URL
6. Auth column reads `api key` for the custom row and `-` for built-in rows with `auth_type === 'none'`
7. Status pills read `Active` / `Inactive` matching `is_active`

**API mock**: `POST /tool/list` → 200 with 3 representative tools.

---

### TC-HAPPY-002: Empty list shows the "No tools yet" state with CTA

**Preconditions**: authenticated; org has zero tools.

**Action**:
1. Visit `/tools`

**Observation 1 — Empty state visuals**:
1. Wrench icon is visible
2. Heading reads `No tools yet`
3. Subtitle reads `Create your first tool to give your agents the ability to call external APIs.`
4. An inline "Create New Tool" button is visible

**Observation 2 — Header CTA also visible**:
1. `page.getByRole('button', { name: /create new tool/i })` returns two results (header CTA + inline CTA)

**API mock**: `POST /tool/list` → 200 `{ items: [], total: 0, page: 1, page_size: 20 }`.

---

### TC-HAPPY-003: Empty list with active filter shows the no-match state

**Action**:
1. Visit `/tools`
2. Type `no_such_tool` into the search bar
3. Wait for the debounce

**Observation 1 — Empty state visuals**:
1. Heading reads `No tools match your filters`
2. Subtitle reads `Try clearing the search or filters.`
3. No inline "Create New Tool" CTA is rendered

**API mock**: `POST /tool/list` → 200 `{ items: [], total: 0, page: 1, page_size: 20 }`.

---

### TC-HAPPY-004: Search by name fires a debounced list call

**Action**:
1. Visit `/tools`
2. Type `inventory` into the search bar
3. Wait for the ~400 ms debounce

**Observation 1 — Network**:
1. Exactly one `POST /tool/list` request is recorded after the initial mount call
2. The new request body contains `search: 'inventory'`

---

### TC-HAPPY-005: Clear search re-fires the list without search

**Preconditions**: a search query is already applied (e.g. after TC-HAPPY-004).

**Action**:
1. Click the X / clear button inside the search bar

**Observation 1 — Network**:
1. A fresh `POST /tool/list` request is recorded
2. The body does NOT include a `search` field (or it is empty)

---

### TC-HAPPY-006: Filter by Type=Custom

**Action**:
1. Visit `/tools`
2. Click the Filters button
3. In the drawer, expand Type and tick `Custom`
4. Click "Apply"

**Observation 1 — Drawer renders facets**:
1. `POST /tool/facets` is recorded
2. The Type section lists at least `custom` with a count

**Observation 2 — List re-fires with filter**:
1. `POST /tool/list` body contains either `filters: [{ field: 'tool_type', operator: 'in', value: ['custom'] }]` OR the legacy `tool_type: 'custom'` shortcut
2. The Filters button badge reads `1`

---

### TC-HAPPY-007: Filter by Status=Active

**Action**:
1. Visit `/tools`
2. Open Filters drawer → expand Status → tick `Active`
3. Click "Apply"

**Observation 1 — List re-fires with filter**:
1. `POST /tool/list` body contains either `is_active: true` OR `filters: [{ field: 'status', operator: 'in', value: ['active'] }]`

---

### TC-HAPPY-008: Sort by Name cycles asc/desc

**Action**:
1. Visit `/tools`
2. Click the Name column header
3. Click it again

**Observation 1 — Two list calls fire**:
1. The first click records `POST /tool/list` with `sort_by` matching `name` (asc)
2. The second click records another with `sort_by` matching `-name` (desc)

---

### TC-HAPPY-009: Sort by Status orders rows by is_active

**Action**:
1. Visit `/tools`
2. Click the Status column header
3. Click it again

**Observation 1 — Network**:
1. `POST /tool/list` body's `sort_by` toggles between `is_active` and `-is_active`

---

### TC-HAPPY-010: Change page size to 50

**Action**:
1. Visit `/tools`
2. Open the rows-per-page native `<select>` in the pagination footer
3. Pick `50`

**Observation 1 — Network**:
1. `POST /tool/list` fires with `page: 1, page_size: 50`

---

### TC-HAPPY-011: Bulk delete — all succeed

**Preconditions**: list has 3 rows (TC-HAPPY-001 state).

**Action**:
1. Visit `/tools`
2. Click the header select-all checkbox
3. Click "Delete" in the SelectionBar
4. Click "Confirm" in the bulk-delete modal

**Observation 1 — SelectionBar reveals**:
1. After step 2, every visible row checkbox is checked
2. SelectionBar displays `3 tools selected` with Clear + Delete buttons

**Observation 2 — Modal copy**:
1. The modal title reads `Delete tools`
2. The modal body reads `Delete 3 selected tools? This action cannot be undone.`

**Observation 3 — Fan-out network calls**:
1. Three `DELETE /tool/delete_tool?tool_id=<id>` requests are recorded

**Observation 4 — Success toast + state cleanup**:
1. Sonner toast title equals `3 tools deleted`
2. SelectionBar is no longer visible
3. A follow-up `POST /tool/list` (refresh) is recorded
4. Modal closes

---

### TC-HAPPY-012: Per-row delete from the action menu

**Action**:
1. Visit `/tools`
2. Open the action menu on a row
3. Click "Delete"
4. Confirm in the modal

**Observation 1 — Network**:
1. Exactly one `DELETE /tool/delete_tool?tool_id=<id>` request is recorded

**Observation 2 — Toast**:
1. Sonner toast title equals `Tool deleted successfully`

**Observation 3 — Row + refresh**:
1. The row leaves the table
2. A follow-up `POST /tool/list` (refresh) is recorded
3. The deleted id is pruned from `selectedIds` (if it was previously selected)

---

### TC-NAV-001: Header Create New Tool navigates to /tools/create

**Action**:
1. Visit `/tools`
2. Click the header "Create New Tool" button

**Observation 1 — Navigation**:
1. URL becomes `/tools/create`

---

### TC-NAV-002: Empty-state Create New Tool navigates to /tools/create

**Preconditions**: empty list (TC-HAPPY-002).

**Action**:
1. Visit `/tools`
2. Click the inline empty-state "Create New Tool" button

**Observation 1 — Navigation**:
1. URL becomes `/tools/create`

---

### TC-NAV-003: Row body click navigates to /tools/edit/<id>

**Action**:
1. Visit `/tools` with at least one row
2. Click the Name cell of the first row

**Observation 1 — Navigation**:
1. URL becomes `/tools/edit/<that row's id>`

---

### TC-NAV-004: Action menu → Edit navigates to /tools/edit/<id>

**Action**:
1. Visit `/tools` with at least one row
2. Open the action menu on a row
3. Click "Edit"

**Observation 1 — Navigation**:
1. URL becomes `/tools/edit/<that row's id>`

---

### TC-NAV-005: Unauthenticated visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools` is recorded

---

### TC-NAV-006: Expired token redirects to login and clears cookie

**Preconditions**: expired `tone_access_token` cookie.

**Action**:
1. Visit `/tools`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools` is recorded
2. The expired cookie is cleared in the response Set-Cookie

---

### TC-NAV-007: Non-member is denied access to the tools list

**Preconditions**: signed-in user is NOT a member of the org.

**Action**:
1. Visit `/tools`

**Observation 1 — Access denial**:
1. Either an access-denied state renders OR the URL redirects to `/home`
2. Zero `POST /tool/list` requests are recorded

---

### TC-ERROR-001: List 500 renders empty state without toast

**Action**:
1. Visit `/tools`

**Observation 1 — Loading clears**:
1. The skeleton rows disappear after the response

**Observation 2 — Empty state appears, no toast**:
1. The "No tools yet" empty state is rendered
2. No Sonner toast appears

**API mock**: `POST /tool/list` → 500 `{ "detail": "Internal server error" }`.

---

### TC-ERROR-002: List 400 renders empty state without toast

**Action**:
1. Visit `/tools`

**Observation 1 — Same as 500 path**:
1. The empty state appears
2. No Sonner toast appears

**API mock**: `POST /tool/list` → 400.

---

### TC-ERROR-003: List 401 renders empty state without redirect

**Action**:
1. Visit `/tools`

**Observation 1 — No auto-redirect**:
1. URL remains `/tools`
2. The empty state appears
3. No Sonner toast appears

**API mock**: `POST /tool/list` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-004: Facets 500 still opens the drawer with empty counts

**Action**:
1. Visit `/tools`
2. Click the Filters button

**Observation 1 — Drawer opens**:
1. The Filters drawer is rendered

**Observation 2 — Sections render with no counts**:
1. The Type and Status sections render with empty counts (0 or no facet items)
2. The user can still tick boxes (counts read 0)

**API mock**: `POST /tool/facets` → 500.

---

### TC-ERROR-005: Facets 401 renders empty counts in drawer

**Action**:
1. Visit `/tools`
2. Click the Filters button

**Observation 1 — Drawer opens with empty counts**:
1. The drawer is rendered
2. Type / Status sections show empty counts
3. No Sonner toast appears

**API mock**: `POST /tool/facets` → 401.

---

### TC-ERROR-006: Per-row delete — template tool 400

**Action**:
1. Visit `/tools`
2. Open the action menu on a template-derived row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals `Template tools cannot be deleted`

**Observation 2 — Row + selection**:
1. The row remains in the table
2. `selectedIds` is NOT modified

**API mock**: `DELETE /tool/delete_tool**` → 400 `{ "detail": "Template tools cannot be deleted" }`.

---

### TC-ERROR-007: Per-row delete — MCP-owned tool 400

**Action**:
1. Visit `/tools`
2. Open the action menu on an MCP-owned row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals `MCP tools cannot be deleted directly. Delete the MCP server instead.`

**Observation 2 — Row remains**:
1. The row is still in the table

**API mock**: `DELETE /tool/delete_tool**` → 400 with that `detail`.

---

### TC-ERROR-008: Per-row delete — 404 (already gone)

**Action**:
1. Visit `/tools`
2. Open the action menu on a row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals `Tool not found`

**Observation 2 — Row reconciles on refresh**:
1. The next `fl.refresh()` removes the row from the table

**API mock**: `DELETE /tool/delete_tool**` → 404 `{ "detail": "Tool not found" }`.

---

### TC-ERROR-009: Per-row delete — 500 keeps the row

**Action**:
1. Visit `/tools`
2. Open the action menu on a row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals `Internal server error`

**Observation 2 — Row remains**:
1. The row is still in the table

**API mock**: `DELETE /tool/delete_tool**` → 500.

---

### TC-ERROR-010: Per-row delete 401 surfaces error toast without redirect

**Action**:
1. Visit `/tools`
2. Open the action menu on a row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (e.g. `Invalid token`)

**Observation 2 — No redirect**:
1. URL remains `/tools`
2. The row is still in the table

**API mock**: `DELETE /tool/delete_tool**` → 401.

---

### TC-ERROR-011: Per-row delete 403 surfaces forbidden toast

**Action**:
1. As a member, visit `/tools`
2. Open the action menu on an owner-only row
3. Click "Delete" → confirm

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (forbidden message)

**Observation 2 — Row remains**:
1. The row is still in the table

**API mock**: `DELETE /tool/delete_tool**` → 403.

---

### TC-ERROR-012: Bulk delete — all rows fail (5xx)

**Action**:
1. Visit `/tools` (with at least 2 rows)
2. Header select-all → SelectionBar Delete → Confirm

**Observation 1 — Toast**:
1. Toast title equals `Bulk delete failed`
2. Toast description equals `No tools were deleted.`

**Observation 2 — Selection persists**:
1. SelectionBar still shows the full count (the failed-set replaces the prior set; when ALL fail it is the same set)

**Observation 3 — Modal closes**:
1. The bulk-delete CustomModal is no longer in the DOM

**API mock**: `DELETE /tool/delete_tool**` → 500 for every id.

---

### TC-ERROR-013: Bulk delete — partial failure keeps failed ids selected

**Action**:
1. Visit `/tools` (with N rows)
2. Select all → Delete → Confirm

**Observation 1 — Toast**:
1. Toast title equals `Partial delete`
2. Toast description matches `/\d+ of \d+ deleted\. \d+ failed — refresh and try again\./`

**Observation 2 — Selection narrowed**:
1. `selectedIds` is replaced with just the failed subset

**Observation 3 — Refresh**:
1. A `POST /tool/list` (refresh) is recorded

**API mock**: `DELETE /tool/delete_tool**` → first id 500, the rest 200.

---

### TC-ERROR-014: Bulk delete — mixed 403 + 200 keeps failed ids selected

**Action**:
1. Visit `/tools` (with N rows)
2. Select all → Delete → Confirm

**Observation 1 — Partial-delete toast**:
1. Toast title equals `Partial delete`

**Observation 2 — Selection narrowed**:
1. Only the failed ids remain in `selectedIds`

**Observation 3 — Refresh**:
1. A `POST /tool/list` (refresh) is recorded

**API mock**: half the DELETE calls → 403, half → 200.

---

### TC-LOADING-001: Slow list keeps skeleton visible without blocking the page

**Action**:
1. Visit `/tools` against a slow `POST /tool/list` (>3 seconds)

**Observation 1 — Skeleton persists**:
1. `animate-pulse` skeleton rows are visible the whole time

**Observation 2 — Toolbar remains interactive**:
1. The header "Create New Tool" button is interactable (not disabled)
2. The Filters button is interactable

---

### TC-LOADING-002: Slow delete disables confirm button and shows spinner

**Action**:
1. Visit `/tools`
2. Open a row's action menu and click Delete
3. Click "Confirm" against a slow backend (>3 seconds)

**Observation 1 — Confirm button state**:
1. The confirm button is disabled
2. A spinner or `Loading...` text is shown on the confirm button

**Observation 2 — Modal blocks dismiss until response**:
1. The modal does NOT dismiss until the response returns

---

### TC-LOADING-003: Double-confirm bulk delete records exactly one fan-out

**Action**:
1. Visit `/tools` (with at least 2 rows)
2. Select all → Delete → Confirm
3. Click "Confirm" again rapidly (≤100 ms)

**Observation 1 — Only one fan-out**:
1. The total number of `DELETE /tool/delete_tool` requests equals the number of selected rows (no doubling)

---

### TC-EDGE-001: List network failure renders empty state

**Action**:
1. Visit `/tools` with the network forced offline

**Observation 1 — Empty state appears**:
1. Skeleton clears
2. The empty-state body renders
3. No Sonner toast appears

**API mock**: route aborted with `failed` status.

---

### TC-EDGE-002: Bulk delete handles timeout per-id

**Action**:
1. Visit `/tools` (with N rows)
2. Select all → Delete → Confirm with half the DELETE calls timing out / network-failing

**Observation 1 — Partial-delete toast**:
1. Toast title equals `Partial delete`

**Observation 2 — Selection narrowed + refresh**:
1. `selectedIds` retains only the failed subset
2. A `POST /tool/list` (refresh) is recorded

---

### TC-EDGE-003: Concurrent delete 404 reconciles via refresh

**Action**:
1. Visit `/tools`
2. Another tab deletes the same row first
3. Open the action menu in this tab and click Delete → Confirm

**Observation 1 — Toast**:
1. Toast title equals `Tool not found`

**Observation 2 — UI converges on next refresh**:
1. The row disappears after `fl.refresh()` runs

**API mock**: `DELETE /tool/delete_tool**` → 404 once.

---

### TC-EDGE-004: Whitespace-only search is treated as empty

**Action**:
1. Visit `/tools`
2. Type only spaces into the search bar
3. Wait for the debounce

**Observation 1 — Either no call or empty search**:
1. The next `POST /tool/list` either does NOT include `search` OR includes `search: ''` / `search: '   '` with default rows still returned

---

### TC-EDGE-005: Search trims surrounding whitespace

**Action**:
1. Visit `/tools`
2. Type ` inventory ` (leading + trailing space) into the search bar
3. Wait for the debounce

**Observation 1 — Trimmed body**:
1. `POST /tool/list` body `search` equals `inventory` (NOT ` inventory `)

> ⚠ unverified whether trimming happens client-side or server-side.

---

### TC-EDGE-006: Search accepts unicode and html-ish input without xss

**Action**:
1. Visit `/tools`
2. Type `<script>alert(1)</script>` + emoji + unicode into the search bar
3. Wait for the debounce

**Observation 1 — Payload carries verbatim**:
1. `POST /tool/list` body `search` equals the literal typed string

**Observation 2 — No XSS execution**:
1. The page does NOT render the script (literal text only)
2. `window.alert` was NOT invoked

---

### TC-EDGE-007: Very long search query does not crash the page

**Action**:
1. Visit `/tools`
2. Paste a 600-character string into the search bar
3. Wait for the debounce

**Observation 1 — Either accepted or truncated**:
1. The search input value length is at most 600 chars
2. The page does NOT crash

---

### TC-EDGE-008: Pasting newlines into search strips them

**Action**:
1. Visit `/tools`
2. Paste multiline content into the search bar

**Observation 1 — Resulting query is single-line**:
1. The next `POST /tool/list` body `search` value does NOT contain `\n`

---

### TC-EDGE-009: Pagination disables prev on the first page

**Action**:
1. Visit `/tools` with enough rows to span multiple pages

**Observation 1 — Prev disabled**:
1. The pagination footer's Previous button has the `disabled` attribute

**Observation 2 — Next enabled**:
1. The Next button is interactable

---

### TC-EDGE-010: Pagination disables next on the last page

**Action**:
1. Visit `/tools` with enough rows to span multiple pages
2. Navigate to the last page

**Observation 1 — Next disabled**:
1. The pagination footer's Next button has the `disabled` attribute

**Observation 2 — Prev enabled**:
1. The Previous button is interactable

---

### TC-EDGE-011: Sort by Name cycles asc → desc → reset

**Action**:
1. Visit `/tools`
2. Click the Name column header three times

**Observation 1 — Three list calls**:
1. Three `POST /tool/list` requests are recorded (after the initial mount)
2. They carry `sort_by: 'name'`, then `sort_by: '-name'`, then default sort (`updated_at` desc) — or the third click resets to default

---

### TC-EDGE-012: Bulk delete cancel preserves selection

**Action**:
1. Visit `/tools` (with at least 2 rows)
2. Select-all → SelectionBar Delete
3. Click "Cancel" in the bulk-delete modal

**Observation 1 — Modal closes, no calls**:
1. The modal is no longer in the DOM
2. Zero `DELETE /tool/delete_tool` requests are recorded

**Observation 2 — Selection retained**:
1. SelectionBar still shows the original count

---

### TC-EDGE-013: Row delete cancel preserves the row

**Action**:
1. Visit `/tools`
2. Open a row's action menu and click Delete
3. Click "Cancel" in the confirm modal

**Observation 1 — Modal closes, no calls**:
1. The confirm modal is no longer in the DOM
2. Zero `DELETE /tool/delete_tool` requests are recorded

**Observation 2 — Row remains**:
1. The row is still in the table

---

### TC-EDGE-014: Select-all on an empty page is a no-op

**Preconditions**: empty list (TC-HAPPY-002).

**Action**:
1. Visit `/tools`
2. Attempt to click the header select-all checkbox

**Observation 1 — Nothing happens**:
1. SelectionBar is NOT rendered
2. `selectedIds` remains empty

---

### TC-EDGE-015: Filter chip count badge updates after Apply

**Action**:
1. Visit `/tools`
2. Open Filters → tick Type=Custom + Status=Active → Apply
3. Reopen Filters → untick Status=Active → Apply

**Observation 1 — Badge counts**:
1. After step 2, the Filters button badge reads `2`
2. After step 3, the Filters button badge reads `1`
3. After clearing all, no badge is visible

---

### TC-EDGE-016: Race — bulk-delete fan-out while a sort change is in flight

**Action**:
1. Visit `/tools` (with at least 2 rows)
2. Click a sortable column header
3. Immediately confirm a bulk delete

**Observation 1 — All DELETE calls resolve**:
1. `Promise.allSettled` resolves every fan-out call
2. A follow-up `POST /tool/list` (refresh) is recorded with the latest sort + page

**Observation 2 — No stale rows**:
1. After the refresh, the table reflects the actual server state (no stale rows reappear)

---

### TC-EDGE-017: Search debounce — final query wins

**Action**:
1. Visit `/tools`
2. Type `abc` into the search bar
3. Within 100 ms, backspace twice and type `def`

**Observation 1 — Only the final query reaches the server**:
1. The last `POST /tool/list` `search` body equals the final typed value (e.g. `adef` or `def`)
2. Any in-flight earlier `search: 'abc'` response is dropped by the in-flight token

---

### TC-A11Y-001: Tab order through the toolbar reaches every control

**Action**:
1. Visit `/tools`
2. Focus the search input
3. Press `Tab` repeatedly

**Observation 1 — Order**:
1. Focus moves Search → Filters button → Create New Tool → select-all checkbox → first sortable column header
2. No focusable element is skipped or reached twice

---

### TC-A11Y-002: Enter on sortable header triggers sort

**Action**:
1. Visit `/tools`
2. Focus the Name column header
3. Press `Enter`

**Observation 1 — Network**:
1. A `POST /tool/list` request fires with updated sort (same as clicking the header)

---

### TC-A11Y-003: Bulk delete modal traps focus and restores on close

**Action**:
1. Visit `/tools` (with at least 2 rows)
2. Select-all → SelectionBar Delete (modal opens)
3. Tab cycles inside the modal
4. Press `Escape`

**Observation 1 — Focus trapped**:
1. While the modal is open, Tab cycles only between modal-internal focusable elements

**Observation 2 — Focus restored on close**:
1. After Escape, focus returns to the SelectionBar's Delete button

---

### TC-A11Y-004: Per-row delete modal traps focus and restores on close

**Action**:
1. Visit `/tools`
2. Open a row's action menu and click Delete (modal opens)
3. Press `Escape`

**Observation 1 — Focus trapped**:
1. While the modal is open, Tab cycles only between modal-internal focusable elements

**Observation 2 — Focus restored on close**:
1. After Escape, focus returns to the row's action menu trigger

---

### TC-A11Y-005: Error toast is announced via aria-live

**Action**:
1. Visit `/tools`
2. Trigger an error toast (e.g. via TC-ERROR-006 — template-tool delete)

**Observation 1 — Toast has alert role**:
1. The Sonner toast container in `[data-sonner-toast]` has `role="alert"` or `aria-live="polite"`
2. Screen readers announce the toast title without manual focus

---

### TC-FULL-001: Lifecycle — create then edit then delete a tool end to end

**Preconditions**: authenticated against a real backend; no existing tool named `__e2e__lifecycle_tool`.

**Action**:
1. Visit `/tools`
2. Click the header "Create New Tool"
3. On `/tools/create`, click the Custom Tool tile
4. On `/tools/create/custom`, fill name `__e2e__lifecycle_tool`, description, URL, and required fields
5. Click "Create"
6. After landing on `/tools`, click the new row's Name cell to enter `/tools/edit/<id>`
7. Mutate the description + URL and click "Save"
8. Navigate back to `/tools` and confirm the row reflects the changes
9. Open the row's action menu, click Delete, and confirm

**Observation 1 — Create succeeds**:
1. `POST /tool/upsert_tool` is recorded for step 5
2. Toast `Tool created successfully` appears
3. URL becomes `/tools`

**Observation 2 — Edit succeeds**:
1. `GET /tool/get_tool?tool_id=<id>` fires on mount of `/tools/edit/<id>`
2. `POST /tool/upsert_tool` (with `id`) is recorded for step 7
3. Toast `Tool updated successfully` appears

**Observation 3 — Row reflects changes**:
1. Back on `/tools`, the row's Name column reads `__e2e__lifecycle_tool`
2. The row's Endpoint URL reflects the new URL

**Observation 4 — Delete succeeds**:
1. `DELETE /tool/delete_tool?tool_id=<id>` is recorded
2. Toast `Tool deleted successfully` appears
3. The row is no longer present in the table

**Cleanup** (in `finally`):
1. If the per-row delete failed, call the backend directly to remove the throw-away tool by id

---

### TC-FULL-002: Walks the entire tools list page end to end

**Preconditions**: authenticated against a real backend; a small seeded `__e2e__` set of tools exists (at least 3 rows).

**Action**:
1. Authenticate and visit `/tools`
2. Assert default heading + sort + page-size selector defaults
3. Exercise search: type free-text, then `name:`, then clear
4. Open Filters → tick Type=Custom + Status=Active → Apply
5. Clear filters (reopen and untick all → Apply)
6. Sort by Name (twice), then sort by Status (twice)
7. Change page size to 50 via the rows-per-page selector
8. Click the header select-all checkbox on the visible page
9. Click SelectionBar Delete → Cancel
10. Re-click SelectionBar Delete → Confirm (deletes the seeded `__e2e__` set)
11. After list refresh, open the action menu on another `__e2e__` tool
12. Click Delete → Cancel
13. Reopen Delete → Confirm

**Observation 1 — Every toolbar/table affordance fires expected list calls**:
1. After each search / filter / sort / page-size change, a corresponding `POST /tool/list` request is recorded with the matching body fields

**Observation 2 — Bulk delete toast and selection clearing**:
1. After step 10, toast `N tools deleted` appears (plural)
2. SelectionBar is no longer visible
3. A follow-up `POST /tool/list` is recorded

**Observation 3 — Per-row delete cancel + confirm**:
1. After step 12, no DELETE is recorded
2. After step 13, exactly one `DELETE /tool/delete_tool?tool_id=<id>` is recorded
3. Toast `Tool deleted successfully` appears
4. The row leaves the table

**Cleanup** (in `finally`):
1. Any remaining `__e2e__` tools are deleted via direct backend calls

---

## Edge Cases (each appears as a `TC-EDGE-*` / `TC-LOADING-*` test case above)

- [x] Unauthenticated access → see TC-NAV-005
- [x] Slow `POST /tool/list` → see TC-LOADING-001
- [x] Empty org (`No tools yet` + inline CTA) → see TC-HAPPY-002
- [x] Filtered to zero (`No tools match your filters`) → see TC-HAPPY-003
- [x] All-failure bulk delete REPLACES `selectedIds` → see TC-ERROR-012
- [x] Partial-failure bulk delete REPLACES `selectedIds` with failed subset → see TC-ERROR-013
- [x] Sort cycling — see TC-EDGE-011
- [x] Search debounce — see TC-EDGE-017
- [x] Race — bulk delete during sort change — see TC-EDGE-016
- [x] Select-all on empty page is no-op — see TC-EDGE-014
- [x] Filter chip count updates — see TC-EDGE-015
- [x] Bulk-delete cancel preserves selection — see TC-EDGE-012
- [x] Row-delete cancel preserves the row — see TC-EDGE-013

Other documented but not separately scenario-ised edge cases:

- Tool with `method` missing → defaults to "POST" in the Method column
- Tool with `auth_type === 'none'` or missing → renders `-` in Auth column
- Tool with `parameters.properties` empty/missing → Params column reads `-`
- Tool with 1 param vs many → singular "1 param" vs plural "N params"
- Unknown `tool_type` → amber default badge with the raw value
- Row click on a tool with no `id` is a no-op (defensive)
- React Query cache invalidation: `useDeleteTool.onSuccess` invalidates `TOOLS_QUERY_KEY`; bulk delete uses `toolsApi.delete` directly and does NOT invalidate
- Search + filter combine: typing `name:foo` AND ticking Type=Custom sends both in the same `POST /tool/list` body
- `selectedIds` is a `Set<string>` — switching pages preserves selection across pages (the SelectionBar count includes off-page ids)
- Header select-all only flips visible rows; off-page selected ids are NOT touched
- Page-size selector is a native `<select>` — keyboard users get OS-native option lists

---

## Business Rules

- Template tools (`is_template=true`) are read-only on the backend and excluded from the list endpoint; they only appear on `/tools/create` as picker tiles.
- MCP-owned tools cannot be deleted from the Tools page — the user must delete the parent MCP server (`/mcp/edit/<id>` → Delete) to remove them.
- The Status pill mirrors the backend `is_active` boolean directly (unlike the Agents list, where Status is a UI derivation from phone-number presence).
- Custom tools are the only type whose URL is shown on the list page; built-in tool URLs are managed by the backend per `tool_type` template.
- Per-row delete uses the React Query mutation so the on-success cache invalidation cleans up other read sites (e.g. agent editor's tool picker). Bulk delete intentionally bypasses React Query to avoid invalidating the cache N times during the fan-out — the visible list refresh is handled by `fl.refresh()`.
- Default page size is 20 (vs the Agents list's 10) — tools are typically more numerous than agents per org.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Page heading is a real `<h1>` (asserted in TC-HAPPY-001)
- [x] Tab order through the toolbar reaches every control — see TC-A11Y-001
- [x] Sortable column headers respond to Enter — see TC-A11Y-002
- [x] Bulk-delete modal traps focus and restores it — see TC-A11Y-003
- [x] Per-row delete modal traps focus and restores it — see TC-A11Y-004
- [x] Error toast is announced via `role="alert"` / `aria-live` — see TC-A11Y-005

Other documented but not separately scenario-ised a11y bullets:

- "Create New Tool" buttons are keyboard-reachable; Enter activates
- Token search input has an associated label / placeholder
- Filters button announces "Filters, N" when the badge is visible
- Per-row action menu trigger has an accessible name
- Header select-all checkbox has `aria-label="Select all"`
- Per-row checkboxes have `aria-label={`Select ${name}`}`
- SelectionBar buttons (Clear, Delete) are keyboard reachable; closing the bar via Clear restores focus to a sensible row
- Status pill includes text ("Active" / "Inactive"), not only color
- Method pill includes the verb text, not only color
- Type badge includes the type label text, not only color

---

## Scenario ID Mapping

| Old scenario ID | New TC ID         | Spec test name                                                  |
| --------------- | ----------------- | --------------------------------------------------------------- |
| PS-1            | TC-HAPPY-001      | list renders the populated table                                |
| PS-2            | TC-HAPPY-002      | empty list renders the no-tools empty state                     |
| PS-3            | TC-HAPPY-003      | search with no matches renders no-results state                 |
| PS-4            | TC-HAPPY-004      | search debounce captures the final query                        |
| PS-5            | TC-HAPPY-006      | filter by Type=Custom                                           |
| PS-6            | TC-HAPPY-007      | filter by Status=Active                                         |
| PS-7            | TC-HAPPY-008      | sort by Name cycles asc desc                                    |
| PS-8            | TC-HAPPY-010      | page-size change resets to page 1                               |
| PS-9            | TC-HAPPY-011      | bulk delete — all succeed                                       |
| PS-10           | TC-HAPPY-012      | per-row delete from the action menu                             |
| FS-1            | TC-ERROR-001      | list 500 renders empty state without toast                      |
| FS-2            | TC-ERROR-003      | list 401 renders empty state without redirect                   |
| FS-3            | TC-ERROR-004      | facets 500 renders empty counts in drawer                       |
| FS-4            | TC-ERROR-006      | per-row delete — template tool 400                              |
| FS-5            | TC-ERROR-007      | per-row delete — MCP-owned tool 400                             |
| FS-6            | TC-ERROR-008      | per-row delete — 404 (already gone)                             |
| FS-7            | TC-ERROR-009      | per-row delete — 500                                            |
| FS-8            | TC-ERROR-012      | bulk delete — all rows fail (5xx)                               |
| FS-9            | TC-ERROR-013      | bulk delete — partial failure                                   |
| FS-10           | TC-EDGE-012       | bulk-delete confirm + Cancel                                    |
| FS-11           | TC-EDGE-013       | per-row delete confirm + Cancel                                 |
| FS-12           | TC-EDGE-014       | select-all on an empty page                                     |
| FS-13           | TC-EDGE-016       | race — bulk-delete fan-out while a sort change is in flight     |
| FS-14           | TC-EDGE-017       | search debounce — final query wins                              |
| FS-15           | TC-EDGE-015       | filter chip count badge updates after Apply                     |
| FS-16           | TC-NAV-005        | auth gating redirect                                            |
| TL-001          | TC-NAV-005        | unauthenticated visit redirects to login                        |
| TL-002          | TC-NAV-006        | expired token redirects to login and clears cookie              |
| TL-003          | TC-NAV-007        | non-member is denied access to the tools list                   |
| TL-004          | TC-ERROR-002      | list 400 renders empty state without toast                      |
| TL-005          | TC-ERROR-003      | list 401 renders empty state without redirect                   |
| TL-006          | TC-ERROR-010      | delete 401 surfaces error toast without redirect                |
| TL-007          | TC-ERROR-011      | delete 403 surfaces forbidden toast                             |
| TL-008          | TC-ERROR-014      | bulk delete partial 403 keeps failed ids selected               |
| TL-009          | TC-ERROR-005      | facets 401 renders empty counts in drawer                       |
| TL-010          | TC-EDGE-001       | list network failure renders empty state                        |
| TL-011          | TC-LOADING-001    | slow list keeps skeleton visible without blocking the page      |
| TL-012          | TC-LOADING-002    | slow delete disables confirm button and shows spinner           |
| TL-013          | TC-EDGE-002       | bulk delete handles timeout per-id                              |
| TL-014          | TC-EDGE-003       | concurrent delete 404 reconciles via refresh                    |
| TL-015          | TC-EDGE-004       | whitespace-only search is treated as empty                      |
| TL-016          | TC-EDGE-005       | search trims surrounding whitespace                             |
| TL-017          | TC-EDGE-006       | search accepts unicode and html-ish input without xss           |
| TL-018          | TC-EDGE-007       | very long search query does not crash the page                  |
| TL-019          | TC-EDGE-008       | pasting newlines into search strips them                        |
| TL-020          | TC-HAPPY-002      | empty list renders the no-tools empty state                     |
| TL-021          | TC-HAPPY-003      | search with no matches renders no-results state                 |
| TL-022          | TC-EDGE-009       | pagination disables prev on the first page                      |
| TL-023          | TC-EDGE-010       | pagination disables next on the last page                       |
| TL-024          | TC-EDGE-011       | sort by Name cycles asc desc and reset                          |
| TL-025          | TC-HAPPY-009      | sort by Status orders rows by is_active                         |
| TL-026          | TC-EDGE-012       | bulk delete cancel preserves selection                          |
| TL-027          | TC-EDGE-013       | row delete cancel preserves the row                             |
| TL-028          | TC-A11Y-001       | tab order through toolbar reaches every control                 |
| TL-029          | TC-A11Y-002       | Enter on sortable header triggers sort                          |
| TL-030          | TC-A11Y-003       | bulk delete modal traps focus and restores on close             |
| TL-031          | TC-A11Y-004       | per-row delete modal traps focus and restores on close          |
| TL-032          | TC-A11Y-005       | error toast is announced via aria-live                          |
| TL-LIFECYCLE    | TC-FULL-001       | lifecycle: create then edit then delete a tool end to end       |
| TL-FULL         | TC-FULL-002       | walks the entire tools list page end to end                     |
