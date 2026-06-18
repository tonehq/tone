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

**As an** agent owner, **I want to** see at a glance whether a tool is
built-in (Google Calendar, SMS, etc.) or a custom HTTP endpoint, **so that**
I can reason about its auth + parameters.

**Acceptance criteria**:

- [ ] Custom tools render a sky-colored "Custom" badge in the Type column
- [ ] Built-in tools render a color-coded badge from `TOOL_TYPE_HEADER` (e.g. teal "Google Calendar", amber "SMS", emerald "Google Sheets")
- [ ] Unknown tool types fall through to the default amber badge with the raw `tool_type` value
- [ ] Built-in rows typically have no `url` (Endpoint URL is empty) but always have an HTTP method (defaults to POST when missing)
- [ ] `auth_type === 'none'` (or missing) renders as `-` in the Auth column; other auth types render lowercased with underscores replaced (e.g. `api_key` → `api key` with CSS `capitalize`)

### US-3: Search, filter, sort, paginate

**As an** agent owner, **I want to** filter by name, type, or status and sort
the table, **so that** I can find specific tools fast.

**Acceptance criteria**:

- [ ] Free-text token search sends `search` in the `POST /tool/list` body
- [ ] `name:weather` becomes a typed token routed to the `name` field
- [ ] Filters drawer offers two sections: Type (`tool_type` values from `POST /tool/facets`) and Status (`status` — active / inactive)
- [ ] Sortable columns are Name (`name`) and Status (`is_active`); clicking cycles asc → desc
- [ ] Default sort is `updated_at` desc (from `toolsListConfig.defaultSort`)
- [ ] Default page size is 20; selector exposes 10 / 20 / 50

### US-4: Select rows for bulk delete

**As an** agent owner, **I want to** check several rows and delete them in
one action, **so that** I can prune obsolete tools quickly.

**Acceptance criteria**:

- [ ] Header checkbox is select-all (visible state: unchecked / `indeterminate` when partial / checked when all visible rows selected)
- [ ] Per-row checkbox toggles a `Set<string>` of selected ids (stops row-click propagation)
- [ ] A floating `SelectionBar` appears at the bottom-center with the selection count, "Clear", and "Delete"
- [ ] SelectionBar uses singular "tool selected" when count is 1 and plural "tools selected" otherwise
- [ ] Clicking Delete opens a `CustomModal` titled "Delete tools" with body "Delete N selected tool(s)? This action cannot be undone." (singular vs plural text branches on count)
- [ ] Confirm fans out via `Promise.allSettled(ids.map(id => toolsApi.delete(id)))` — does NOT use the React Query mutation (so a single failure doesn't invalidate the whole cache twice)
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

## User Workflow Steps

Step-by-step actions per major flow. Used to derive `test(...)` blocks in
`e2e/dashboard/tools.spec.ts`. Toast assertions use
`page.locator('[data-sonner-toast]')`.

**WF-1: Browse the table** (positive — US-1, US-2)

1. User authenticates and navigates to `/tools` → expected: heading "Tools" + subtitle visible; `POST /tool/list` fires with default `{ page: 1, page_size: 20, sort_by: 'updated_at', sort_order: 'desc' }`.
2. Response with three rows → expected: count `Badge` = 3; rows render with Name (font-mono), description, Type badge ("Custom" / "Google Calendar" / "SMS"), Method ("GET" / "POST"), Endpoint URL for custom tools (`https://api.example.com/inventory/{product_id}`), Auth ("api key" / "-"), Params ("2 params" / "1 param" / "-"), Status ("Active" / "Inactive").

**WF-2: Search by name with debounce** (positive — US-3)

1. User types `inventory` into the search bar → expected: after the ~400 ms debounce, `POST /tool/list` re-fires with `search: 'inventory'`.
2. User clears the search via the X button in the search bar → expected: input clears and `POST /tool/list` re-fires without `search`.

**WF-3: Filter by Type via the drawer** (positive — US-3)

1. User clicks the Filters button → expected: `FacetFilterDrawer` opens with two sections, populated from `POST /tool/facets`.
2. User ticks `Custom` under Type → Apply → expected: `POST /tool/list` re-fires with `filters: [{ field: 'tool_type', operator: 'in', value: ['custom'] }]`; drawer filter count badge reads `1`.

> Note: the existing `tools.spec.ts` exercises a legacy `tool_type: 'custom'`
> top-level body field. Both shapes are valid against the backend; tests should
> mock matching whichever the current UI build sends.

**WF-4: Sort by Name then Status** (positive — US-3)

1. User clicks the "Name" column header → expected: `POST /tool/list` re-fires with `sort_by` matching `name` or `-name` (asc then desc).
2. User clicks "Status" → expected: `sort_by` toggles between `is_active` and `-is_active`.

**WF-5: Change page size** (positive — US-3)

1. User opens the rows-per-page native `<select>` → picks `50` → expected: `POST /tool/list` fires with `page_size: 50`.

**WF-6: Bulk delete — happy path** (positive — US-4)

1. User clicks the header select-all checkbox → expected: every visible row checkbox flips on; SelectionBar reveals with "3 tools selected" (when 3 rows are visible).
2. User clicks Delete in the SelectionBar → expected: `CustomModal` opens with title "Delete tools" and body "Delete 3 selected tools? This action cannot be undone.".
3. User confirms → expected: three `DELETE /tool/delete_tool?tool_id=<id>` calls fan out; on all-success, toast `3 tools deleted`, SelectionBar collapses, list refetches.

**WF-7: Bulk delete — partial failure** (negative — US-4)

1. Setup: first `DELETE` returns 500, the rest return 200.
2. User selects all → Delete → confirm → expected: toast title `Partial delete`, description matching `/\d+ of \d+ deleted\. \d+ failed — refresh and try again\./`; only the failed ids stay in `selectedIds`.

**WF-8: Per-row delete from the action menu** (positive — US-5)

1. User clicks the Delete button inside a row's action menu → expected: `ActionMenu` opens its own `Delete {name}?` confirm modal.
2. User confirms → expected: `DELETE /tool/delete_tool?tool_id=<id>` returns 200; toast `Tool deleted successfully`; row removed; `fl.refresh()`.

**WF-9: Per-row delete failure (template tool)** (negative — US-5)

1. Setup: `DELETE /tool/delete_tool?tool_id=<id>` returns 400 `{"detail": "Template tools cannot be deleted"}`.
2. User confirms delete → expected: toast title `Template tools cannot be deleted`; row remains; `useDeleteTool`'s React Query cache is NOT invalidated (the mutation rejected).

**WF-10: Navigate to create chooser** (positive — US-6)

1. User clicks the header "Create New Tool" → expected: `router.push('/tools/create')`.
2. (Empty list) User clicks the empty-state "Create New Tool" → same destination.

**WF-11: Row click navigates to edit** (positive — US-5)

1. User clicks the Name cell of any row → expected: `router.push('/tools/edit/<id>')`. (Editor behavior is covered in `tools-edit.md`.)

**WF-12: Auth gating** (negative)

1. Unauthenticated user visits `/tools` → expected: 307 → `/auth/login?redirect=%2Ftools`.

---

## Input Specifications

### Toolbar search

| Field        | Type      | Required | Validation                                                              | Notes                                                              |
| ------------ | --------- | -------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Search input | tokenized | no       | Free text or typed tokens (`name:<q>`, `status:<active\|inactive>`)     | Debounced through `useFacetedList`; emits `search` body field      |
| Filters → Type   | multi-select | no | Values from `POST /tool/facets` → `tool_type` (custom, google_calendar, google_sheets, send_sms, …) | Sent as `filters: [{ field: 'tool_type', operator: 'in', value: [...] }]` |
| Filters → Status | multi-select | no | Values from `POST /tool/facets` → `status` (active, inactive)            | Sent as `filters: [{ field: 'status', operator: 'in', value: [...] }]` |

### Confirmation modals

| Field                  | Type   | Required | Validation                                  | Exact Text                                                                          |
| ---------------------- | ------ | -------- | ------------------------------------------- | ----------------------------------------------------------------------------------- |
| Bulk-delete title      | static | n/a      | Always "Delete tools"                       | `Delete tools`                                                                       |
| Bulk-delete body (n=1) | static | n/a      | Singular branch                              | `Delete 1 selected tool? This action cannot be undone.`                              |
| Bulk-delete body (n>1) | static | n/a      | Plural branch                                | `Delete N selected tools? This action cannot be undone.`                             |
| Row-delete title       | static | n/a      | `Delete {toolName}?`                         | `Delete check_inventory?` (literal interpolation)                                    |
| Row-delete body        | static | n/a      | Renders the name in quotes                   | `Are you sure you want to delete "check_inventory"? This action cannot be undone.`   |

---

## Success Scenarios

**PS-1: List renders the populated table** (US-1, US-2)

- **Preconditions**: authenticated; org has 3 tools (one custom, one Google Calendar, one SMS).
- **Steps**: navigate to `/tools`.
- **Expected outcome**: count `Badge` shows `3`; rows render with the expected Type badges, Method pills, URLs, Auth, Params, Status; default sort indicator on "Last updated" is desc.
- **Mock API** (`POST /tool/list`, 200):
  ```json
  {
    "items": [
      {
        "id": "11111111-1111-1111-1111-111111111111",
        "uuid": "11111111-1111-1111-1111-111111111111",
        "name": "check_inventory",
        "description": "Checks product inventory and returns availability.",
        "tool_type": "custom",
        "url": "https://api.example.com/inventory/{product_id}",
        "method": "GET",
        "auth_type": "api_key",
        "auth_config": { "header_name": "X-API-Key", "api_key": "sk-xxxx" },
        "meta_data": null,
        "parameters": { "type": "object", "properties": { "product_id": { "type": "string" }, "location": { "type": "string" } }, "required": ["product_id"] },
        "is_active": true,
        "is_template": false,
        "oauth_connection_id": null,
        "mcp_server_id": null,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-05-01T00:00:00Z"
      },
      {
        "id": "22222222-2222-2222-2222-222222222222",
        "uuid": "22222222-2222-2222-2222-222222222222",
        "name": "create_calendar_event",
        "description": "Create a Google Calendar event for a customer.",
        "tool_type": "google_calendar",
        "url": null,
        "method": "POST",
        "auth_type": "none",
        "auth_config": null,
        "meta_data": { "calendar_id": "primary", "timezone": "UTC" },
        "parameters": { "type": "object", "properties": { "title": { "type": "string" } } },
        "is_active": false,
        "is_template": false,
        "oauth_connection_id": "oauth-1",
        "mcp_server_id": null,
        "created_at": "2026-02-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z"
      },
      {
        "id": "33333333-3333-3333-3333-333333333333",
        "uuid": "33333333-3333-3333-3333-333333333333",
        "name": "send_appointment_sms",
        "description": "Send an SMS appointment reminder via Twilio.",
        "tool_type": "send_sms",
        "url": null,
        "method": "POST",
        "auth_type": "none",
        "auth_config": { "account_sid": "AC***", "auth_token": "***" },
        "meta_data": { "from_number": "+15551234567" },
        "parameters": {},
        "is_active": true,
        "is_template": false,
        "oauth_connection_id": null,
        "mcp_server_id": null,
        "created_at": "2026-03-01T00:00:00Z",
        "updated_at": "2026-03-15T00:00:00Z"
      }
    ],
    "total": 3,
    "page": 1,
    "page_size": 20
  }
  ```

**PS-2: Empty list (no filter) shows the empty state with CTA**

- **Mock API** (`POST /tool/list`, 200): `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`
- **Expected outcome**: Wrench icon + "No tools yet" + "Create your first tool to give your agents the ability to call external APIs." + inline "Create New Tool" button. Header also still renders its own "Create New Tool" button → two `getByRole('button', { name: /create new tool/i })` results.

**PS-3: Empty list with active filter shows the no-match state**

- **Steps**: user types `no_such_tool` into the search bar.
- **Expected outcome**: "No tools match your filters" + "Try clearing the search or filters." — the inline CTA is NOT rendered.
- **Mock API** (`POST /tool/list`, 200): `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`

**PS-4: Search debounce — captures the final query** (US-3)

- **Steps**: type `inventory`.
- **Expected outcome**: after ~400 ms, exactly one `POST /tool/list` fires with `search: 'inventory'`.

**PS-5: Filter by Type=custom**

- **Steps**: open Filters → Type → tick `Custom` → Apply.
- **Expected outcome**: `POST /tool/list` body contains `filters: [{ field: 'tool_type', operator: 'in', value: ['custom'] }]` (or the legacy `tool_type: 'custom'` shortcut).

**PS-6: Filter by Status=Active**

- Same as PS-5 with the Status section → `is_active: true` (or filters-array equivalent).

**PS-7: Sort by Name ascending**

- **Steps**: click the "Name" column header once.
- **Expected outcome**: next `POST /tool/list` carries `sort_by: 'name'` (or `-name` when toggled to desc).

**PS-8: Page-size change resets to page 1**

- **Steps**: pick `50` from the rows-per-page selector.
- **Expected outcome**: `POST /tool/list` fires with `page: 1, page_size: 50`.

**PS-9: Bulk delete — all succeed**

- **Preconditions**: PS-1 (3 rows).
- **Steps**: select-all → Delete → confirm.
- **Mock API** (`DELETE /tool/delete_tool**`, 200): `{ "message": "Tool deleted successfully" }` for each id.
- **Expected outcome**: 3 `DELETE` calls fire concurrently; toast `3 tools deleted`; selection cleared; bulk-delete modal closes; `fl.refresh()` runs.

**PS-10: Per-row delete from the action menu**

- **Steps**: open the row's action menu → Delete → confirm.
- **Mock API** (`DELETE /tool/delete_tool**`, 200): `{ "message": "Tool deleted successfully" }`
- **Expected outcome**: toast `Tool deleted successfully`; row leaves the table; selection set is pruned of the deleted id; `fl.refresh()` runs.

---

## Failure Scenarios

**FS-1: List returns 500 → empty state**

- **Mock API** (`POST /tool/list`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: `fl.listLoading` clears; table body shows "No tools yet" (no inline error banner; `useFacetedList` swallows the error and resets to empty rows).

**FS-2: List returns 401 (token rejected mid-session)**

- **Mock API** (`POST /tool/list`, 401): `{ "detail": "Could not validate credentials" }`
- **Expected UI**: same as FS-1 — empty state appears; no auto-redirect to login.

**FS-3: Facets endpoint returns 500**

- **Mock API** (`POST /tool/facets`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: drawer still opens; sections render with empty counts; user can still apply selections (counts read 0).

**FS-4: Per-row delete — template tool 400**

- **Mock API** (`DELETE /tool/delete_tool**`, 400): `{ "detail": "Template tools cannot be deleted" }`
- **Expected UI**: toast title `Template tools cannot be deleted`; row remains in the table; `selectedIds` not modified.

**FS-5: Per-row delete — MCP-owned tool 400**

- **Mock API** (`DELETE /tool/delete_tool**`, 400): `{ "detail": "MCP tools cannot be deleted directly. Delete the MCP server instead." }`
- **Expected UI**: toast title is that exact `detail` string; row remains.

**FS-6: Per-row delete — 404 (already gone)**

- **Mock API** (`DELETE /tool/delete_tool**`, 404): `{ "detail": "Tool not found" }`
- **Expected UI**: toast title `Tool not found`; the next `fl.refresh()` removes the row.

**FS-7: Per-row delete — 500**

- **Mock API** (`DELETE /tool/delete_tool**`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: toast title `Internal server error`; row remains.

**FS-8: Bulk delete — all rows fail (5xx)**

- **Mock API** (`DELETE /tool/delete_tool**`, 500): `{ "detail": "Internal error" }` for every id.
- **Expected UI**: bulk-delete modal closes; toast title `Bulk delete failed`, description `No tools were deleted.`; `selectedIds` is reset (per the implementation, the failed-set replaces the prior set — when ALL fail, every id stays selected).

**FS-9: Bulk delete — partial failure**

- **Mock API** (`DELETE /tool/delete_tool**`): first id → 500, rest → 200.
- **Expected UI**: toast title `Partial delete`, description matching `/\d+ of \d+ deleted\. \d+ failed — refresh and try again\./`; `selectedIds` is replaced with the set of failed ids.

**FS-10: Bulk-delete confirm + Cancel**

- **Steps**: open the bulk-delete modal → click Cancel.
- **Expected UI**: modal closes; no `DELETE` calls fired; selection unchanged.

**FS-11: Per-row delete confirm + Cancel**

- **Steps**: open the row action menu → Delete → click Cancel.
- **Expected UI**: confirm modal closes; no `DELETE` call fired; row remains; `useDeleteTool` mutation never runs.

**FS-12: Select-all on an empty page**

- **Preconditions**: PS-2 (empty list).
- **Steps**: click the header select-all checkbox.
- **Expected UI**: nothing happens — `tools.length === 0` so the `allRowsSelected` branch never triggers; SelectionBar stays hidden.

**FS-13: Race — bulk-delete fan-out while a sort change is in flight**

- **Steps**: click a sortable header, then immediately confirm a bulk delete.
- **Expected UI**: `Promise.allSettled` resolves all DELETE calls; `fl.refresh()` re-fetches the latest sort + page; no stale rows reappear.

**FS-14: Search debounce — final query wins**

- **Steps**: type `abc`, then within 100 ms backspace twice and type `def`.
- **Expected UI**: only the last `search: 'abdef'` (or whatever the final value is) reaches the server — the in-flight token drops the earlier `search: 'abc'` response.

**FS-15: Filter chip count badge updates after Apply**

- **Steps**: select Type=Custom + Status=Active in the drawer → Apply → reopen → uncheck one → Apply.
- **Expected UI**: Filters button badge reads `2` then `1`; clearing all flips back to no badge.

**FS-16: Auth gating redirect**

- **Preconditions**: no `tone_access_token` cookie.
- **Steps**: visit `/tools`.
- **Expected UI**: 307 redirect to `/auth/login?redirect=%2Ftools`.

---

## Expected Toast Messages

Sonner toasts via `showToast` (`src/utils/toast.tsx`). Errors from the React
Query mutation `useDeleteTool` are NOT funneled through `handleApiError` —
they're caught locally in `ToolsListPage.tsx`'s `ActionMenu.onDelete`
callback. Bulk-delete errors are surfaced as titled error toasts with custom
strings (NOT the backend detail). For per-row delete, the backend `detail`
string is surfaced verbatim via `showToast.error(detail)` ⚠ unverified — the
current code shows `showToast.success('Tool deleted successfully')` only on
success; failure paths bubble up via `ActionMenu`'s parent error handling
(which today uses `handleApiError`). Confirm by reading
`src/components/shared/ActionMenu.tsx`.

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
| Type badge                    | Badge           | "Custom" / "Google Calendar" / "SMS" / "Google Sheets" / raw  | Color coded                                                                |
| Method pill                   | Badge           | "GET" / "POST" / "PUT" / "DELETE" / "PATCH"                    | Uppercased; defaults to POST when missing                                   |
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

## Edge Cases

- [ ] Unauthenticated access → middleware redirect to `/auth/login?redirect=%2Ftools`
- [ ] Slow `POST /tool/list` → `animate-pulse` skeleton rows render until the response
- [ ] Empty org → "No tools yet" empty state + inline CTA; header CTA still visible (so two "Create New Tool" buttons coexist)
- [ ] Filtered to zero → "No tools match your filters" empty state; inline CTA hidden
- [ ] Tool with `method` missing → defaults to "POST" in the Method column
- [ ] Tool with `auth_type === 'none'` or missing → renders `-` in Auth column
- [ ] Tool with `parameters.properties` empty/missing → Params column reads `-`
- [ ] Tool with 1 param vs many → singular "1 param" vs plural "N params"
- [ ] `tool_type === 'custom'` → sky badge "Custom"
- [ ] Unknown `tool_type` → amber default badge with the raw value
- [ ] Row click on a tool with no `id` is a no-op (defensive — should not happen)
- [ ] Selecting all then deleting clears `selectedIds` only on full success
- [ ] All-failure bulk delete REPLACES `selectedIds` with the failed set (which is the same set) — selection persists
- [ ] Partial-failure bulk delete REPLACES `selectedIds` with just the failed subset
- [ ] React Query cache invalidation: `useDeleteTool.onSuccess` invalidates the `TOOLS_QUERY_KEY` cache; bulk delete uses `toolsApi.delete` directly and does NOT invalidate the cache to avoid races during the fan-out — `fl.refresh()` (which uses the faceted-list endpoint, not React Query) covers the visible refresh
- [ ] Search + filter combine: typing `name:foo` AND ticking Type=Custom sends both in the same `POST /tool/list` body
- [ ] `selectedIds` is a `Set<string>` — switching pages preserves selection across pages (the SelectionBar count includes off-page ids)
- [ ] Header select-all only flips visible rows; off-page selected ids are NOT touched
- [ ] Confirm modal can be dismissed via Cancel (no calls) or by clicking outside (Radix close)
- [ ] Page-size selector is a native `<select>` — keyboard users get OS-native option lists

---

## Business Rules

- Template tools (`is_template=true`) are read-only on the backend and excluded from the list endpoint; they only appear on `/tools/create` as picker tiles.
- MCP-owned tools cannot be deleted from the Tools page — the user must delete the parent MCP server (`/mcp/edit/<id>` → Delete) to remove them.
- The Status pill mirrors the backend `is_active` boolean directly (unlike the Agents list, where Status is a UI derivation from phone-number presence).
- Custom tools are the only type whose URL is shown on the list page; built-in tool URLs are managed by the backend per `tool_type` template.
- Per-row delete uses the React Query mutation so the on-success cache invalidation cleans up other read sites (e.g. agent editor's tool picker). Bulk delete intentionally bypasses React Query to avoid invalidating the cache N times during the fan-out — the visible list refresh is handled by `fl.refresh()`.
- Default page size is 20 (vs the Agents list's 10) — tools are typically more numerous than agents per org.

---

## Accessibility Requirements

- [ ] Page heading is a real `<h1>` (`role: heading, level: 1`)
- [ ] "Create New Tool" buttons are keyboard-reachable; Enter activates
- [ ] Token search input has an associated label / placeholder
- [ ] Filters button announces "Filters, N" when the badge is visible
- [ ] Sortable column headers are real `<th role="columnheader">` and respond to Enter
- [ ] Per-row action menu trigger has an accessible name
- [ ] Header select-all checkbox has `aria-label="Select all"`
- [ ] Per-row checkboxes have `aria-label={`Select ${name}`}`
- [ ] SelectionBar buttons (Clear, Delete) are keyboard reachable; closing the bar via Clear restores focus to a sensible row
- [ ] Confirm modals trap focus and restore it on close (Radix/shadcn default via `CustomModal`)
- [ ] Status pill includes text ("Active" / "Inactive"), not only color
- [ ] Method pill includes the verb text, not only color
- [ ] Type badge includes the type label text, not only color

---

## Appended Scenarios (gap-fill, ID prefix `TL-`)

These rows extend the original PS/FS coverage with auth, error-state, network, input-edge-case, list-specific, accessibility and lifecycle scenarios so `/generate-tests` can produce a comprehensive `tools.spec.ts`. Real-backend conventions apply (`__e2e__` prefix, try/finally cleanup in the same test body); no `page.route` mocks unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-001 | Visit `/tools` without `tone_access_token` cookie | Middleware 307 → `/auth/login?redirect=%2Ftools` | `unauthenticated visit redirects to login` |
| TL-002 | Visit `/tools` with an expired token cookie | Middleware 307 → `/auth/login?redirect=%2Ftools`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| TL-003 | Logged-in non-member opens `/tools` (org switched away) | Access-denied state OR redirect to `/home`; no `POST /tool/list` fires | `non-member is denied access to the tools list` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-004 | `POST /tool/list` returns 400 (malformed filter) | Empty table state; no destructive crash; no toast | `list 400 renders empty state without toast` |
| TL-005 | `POST /tool/list` returns 401 mid-session | Empty table state; no auto-redirect to login | `list 401 renders empty state without redirect` |
| TL-006 | Token expires between page load and a per-row Delete confirm → 401 | Toast with backend `detail` (e.g. `Invalid token`); row remains | `delete 401 surfaces error toast without redirect` |
| TL-007 | Member role attempts delete on owner-only tool → 403 | Toast with backend `detail`; row remains | `delete 403 surfaces forbidden toast` |
| TL-008 | Bulk delete with mixed 403 + 200 responses | Partial-delete toast surfaces; only failed ids remain selected; refresh runs | `bulk delete partial 403 keeps failed ids selected` |
| TL-009 | `POST /tool/facets` returns 401 | Drawer still opens; sections render with empty counts; no toast | `facets 401 renders empty counts in drawer` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-010 | Offline / network failure on `POST /tool/list` | Skeleton clears; empty-state body renders; user can retry by reloading | `list network failure renders empty state` |
| TL-011 | Slow `POST /tool/list` (>3s) | `animate-pulse` skeleton stays visible; Create CTA + Filters remain interactive | `slow list keeps skeleton visible without blocking the page` |
| TL-012 | Slow `DELETE /tool/delete_tool` (>3s) | Confirm button disabled + spinner; modal blocks dismiss until response | `slow delete disables confirm button and shows spinner` |
| TL-013 | Bulk delete fan-out — half the calls time out / network-fail | Partial-delete toast surfaces; selection retained for the failed subset; `fl.refresh()` runs | `bulk delete handles timeout per-id` |
| TL-014 | Concurrent delete — tool already deleted by another tab returns 404 mid-confirm | Toast `Tool not found`; UI converges on next `fl.refresh()` | `concurrent delete 404 reconciles via refresh` |

### Input edge cases (search bar)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-015 | Type only whitespace into the search bar | `search` body field not sent (or sent empty); table reverts to default rows | `whitespace-only search is treated as empty` |
| TL-016 | Search query with leading/trailing spaces (` inventory `) | Trimmed; `search` body contains `inventory` | `search trims surrounding whitespace` |
| TL-017 | Search query with special characters / emoji / unicode | Query sent verbatim; results render without breaking the UI; no XSS execution | `search accepts unicode and html-ish input without xss` |
| TL-018 | Search query >500 characters | Either accepted or truncated; no client crash | `very long search query does not crash the page` |
| TL-019 | Paste multiline value into the single-line search input | Newlines stripped; resulting `search` is single-line | `pasting newlines into search strips them` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-020 | Org has zero tools | Wrench icon + "No tools yet" + inline "Create New Tool" CTA; header CTA also visible | `empty list renders the no-tools empty state` |
| TL-021 | Search with no matches | "No tools match your filters" + clearing helper text; inline CTA hidden | `search with no matches renders no-results state` |
| TL-022 | Pagination — first page | Prev button disabled, Next enabled when more pages exist | `pagination disables prev on the first page` |
| TL-023 | Pagination — last page | Next button disabled, Prev enabled when prior pages exist | `pagination disables next on the last page` |
| TL-024 | Sort by Name (asc → desc → reset) | Three header clicks fire three `POST /tool/list` calls cycling `name` asc/desc/reset | `sort by Name cycles asc desc and reset` |
| TL-025 | Sort by Status | `POST /tool/list` fires with `sort_by: 'is_active'` (asc/desc) | `sort by Status orders rows by is_active` |
| TL-026 | Bulk select + delete cancel | Cancel closes the modal; no `DELETE` fired; selection retained | `bulk delete cancel preserves selection` |
| TL-027 | Row-level delete cancel | Confirm modal closes; no `DELETE` fired; row remains | `row delete cancel preserves the row` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-028 | Tab order through the toolbar | Search → Filters button → Create New Tool → select-all checkbox → first sortable column header | `tab order through toolbar reaches every control` |
| TL-029 | Press Enter on a sortable column header | Re-fires `POST /tool/list` with updated sort (same as click) | `Enter on sortable header triggers sort` |
| TL-030 | Bulk-delete confirmation modal traps focus and restores it | Focus enters modal; Tab cycles; Escape closes and restores focus to SelectionBar's Delete button | `bulk delete modal traps focus and restores on close` |
| TL-031 | Per-row delete confirmation modal traps focus and restores it | Focus enters modal; Escape restores focus to the row action menu trigger | `per-row delete modal traps focus and restores on close` |
| TL-032 | Toast error has `role="alert"` / aria-live | Screen readers announce the toast title without manual focus | `error toast is announced via aria-live` |

### Cross-flow lifecycle

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-LIFECYCLE | Walk **create → edit → delete** end-to-end in one Playwright test against the real backend: open `/tools` → click Create New Tool → pick Custom on `/tools/create` → fill a `__e2e__` Custom tool on `/tools/create/custom` → save → land on `/tools` → click the new row to enter `/tools/edit/<id>` → mutate description + URL → save → return to `/tools` → confirm the row reflects the changes → per-row Delete + confirm → row gone | All three pages cooperate; toasts fire on each save/delete; cleanup runs in the same test body via `try/finally` even if assertions fail mid-way | `lifecycle: create then edit then delete a tool end to end` |

### Full lifecycle (`TL-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TL-FULL | Authenticate → visit `/tools` → assert heading + default sort + page-size selector defaults → exercise search (free-text + `name:` + clear) → open Filters → tick Type=Custom + Status=Active + Apply → clear filters → sort by Name and Status → change page size to 50 → select-all on the visible page → cancel bulk delete → re-open and confirm bulk delete on a seeded `__e2e__` set → assert plural toast and selection cleared → open the row action menu for another `__e2e__` tool → cancel delete → re-open and confirm → assert toast and row removal | Every toolbar/table affordance fires the expected `POST /tool/list` request; all seeded tools are deleted in the same test body via `try/finally` | `walks the entire tools list page end to end` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| TL-001..003 | FS-16 (auth gating) | Adds expired-token + non-member cases |
| TL-004..009 | FS-1..FS-8 | Adds 400/403/401 paths for list/facets + delete |
| TL-010..014 | (new) | Network resilience for list, delete, bulk delete fan-out |
| TL-015..019 | (new) | Input edge cases for the search bar |
| TL-020..027 | PS-2, PS-3, PS-7 + FS-10..FS-11 | Promotes pagination/sort/cancel scenarios into list-specific cluster |
| TL-028..032 | Accessibility checklist | Promotes a11y bullets into runnable scenarios |
| TL-LIFECYCLE | (new) | Cross-flow create→edit→delete lifecycle |
| TL-FULL | (new) | Single-test sweep of the list page |
