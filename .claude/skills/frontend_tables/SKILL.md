---
name: frontend_tables
description: Generate a complete table listing page with server-side filtering, sorting, and pagination for the Tone frontend. Uses the CustomTable component (TanStack React Table) with ColumnDef-based columns, server-side sorting, sticky columns, infinite scroll or classic pagination. Reads TABLE metadata JSON (from [[backend_tables]]) or inspects the backend API directly to derive column keys, filter options, and sort fields.
---

# frontend_tables — Table page generator (Tone)

Generates a fully wired **table listing page** for the Tone frontend. Consumes TABLE metadata JSON produced by [[backend_tables]], or inspects the backend API and models directly when metadata is unavailable. Produces a Next.js `page.tsx` and any missing React Query hooks needed to power it.

**Primary table component:** `CustomTable` from `@/components/shared/custom-table` — a TanStack React Table wrapper with server-side sorting, sticky columns, infinite scroll, classic pagination, row selection, and loading states.

## Hard constraints

- **Use `CustomTable`** for all new table pages. Do NOT use the legacy `DataTable` component.
- **Follow existing patterns exactly.** Every generated page must structurally match the conventions in the codebase (see Reference Architecture below).
- **DO NOT modify** shared components (`CustomTable`, `PageHeader`, `EmptyState`, `StatusBadge`, `SelectInput`, `ConfirmModal`). Use them as-is.
- **DO NOT invent new component abstractions** — compose from existing shared components only.
- **DO NOT add dependencies** — use only libraries already in `package.json` (`@tanstack/react-table`, `lucide-react`, `sonner`, etc.).
- **DO NOT hardcode data** — all data comes from React Query hooks backed by the backend API.
- **Always verify** the backend endpoint exists and its query params before generating filter/sort/pagination logic.

## Inputs

Before generating, gather these inputs (ask the user if not provided):

1. **Entity name** — e.g. `agents`, `test-runs`, `evaluators`, `audit-logs`.
2. **Route path** — where the page lives under `frontend/app/(dashboard)/`. Usually matches the entity slug.
3. **Metadata source** — one of:
   - Path to `entities.json` with a `table` block from [[backend_tables]].
   - Or: "inspect backend" — skill reads the backend model + controller directly.
4. **Scope** — what features to include: `filters`, `sorting`, `pagination`, `selection`, `bulk-delete`, `row-click`, `empty-state`. Default: all.
5. **Pagination mode** — `classic` (page buttons) or `infinite` (scroll to load more). Default: `classic`.

## Reference Architecture

All table pages in this project follow this exact structure. **Match it precisely.**

### Page file location

```
frontend/app/(dashboard)/<entity-slug>/page.tsx
```

### Imports pattern

```tsx
"use client";
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import { <EntityIcon>, ... } from "lucide-react";
import { toast } from "sonner";
import { use<Entity>, useDelete<Entity> } from "@/lib/api/<module>";
import { CustomTable, SearchBar, EmptyState, PageHeader, StatusBadge, SelectInput, ConfirmModal } from "@/components/shared";
import { Badge } from "@/components/ui/primitives";
import { Checkbox } from "@/components/ui/primitives";
import { formatRelative } from "@/lib/utils";
import type { <EntityType> } from "@/types";
```

### State management pattern

**Search, filtering, sorting, and pagination are ALL server-side.** Every change must update state that flows into the React Query hook params, triggering a new API call. Never filter/sort/search client-side.

```tsx
export default function <Entity>Page() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("-updated_at");

  // Search — SearchBar handles debounce internally, onSearch fires the debounced value
  const [search, setSearch] = useState("");

  // Filters — one state per filter dropdown
  const [statusFilter, setStatusFilter] = useState("");
  // Add more as needed: const [typeFilter, setTypeFilter] = useState("");

  // Named handlers — extract as useCallback, never use inline arrow in JSX
  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleStatusFilter = useCallback((value: string) => {
    setStatusFilter(value === "all" ? "" : value);
    setPage(1);
  }, []);

  // Page size selector
  const [pageSize, setPageSize] = useState(10);

  const handlePageSizeChange = useCallback((size: number) => {
    setPageSize(size);
    setPage(1);
  }, []);

  // ALL params flow into the hook — changes trigger new API request via React Query
  const { data, isLoading } = use<Entity>({
    page,
    page_size: pageSize,
    sort_by: sortBy,
    ...(search && { search }),
    ...(statusFilter && { <filter_key>: statusFilter }),
  });
  const queryClient = useQueryClient();
  const [idsToDelete, setIdsToDelete] = useState<string[]>([]);
  const [selectedRows, setSelectedRows] = useState<EntityType[]>([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Track if filters are active (to distinguish "no data at all" from "no results for filter")
  const hasActiveFilters = search !== "" || statusFilter !== "";
```

### Search input pattern

Use the `SearchBar` component from `@/components/shared`. It handles debounce (400ms default), search icon, and clear button internally.

```tsx
import { SearchBar } from "@/components/shared";

<SearchBar
  placeholder="Search <entities>..."
  onSearch={(v) => {
    setSearch(v);   // Updates search param → React Query refetches
    setPage(1);     // ALWAYS reset page on search change
  }}
/>
```

**SearchBar props:**

| Prop | Type | Default | Description |
|---|---|---|---|
| `onSearch` | `(value: string) => void` | required | Fires after debounce with the search value |
| `placeholder` | `string` | `"Search..."` | Input placeholder |
| `debounce` | `number` | `400` | Debounce delay in ms |
| `className` | `string` | — | Additional class for wrapper |

**Search rules:**
- **Always use `SearchBar`** — never build inline search with manual debounce.
- `onSearch` fires the debounced value — set the search state and reset page in the callback.
- Only include `search` in hook params when non-empty: `...(search && { search })`.
- The backend must support a `search` body param that filters with `ilike`.
- **Reset page to 1** when search changes.

### Column definitions (TanStack ColumnDef)

Define columns using `useMemo` and `ColumnDef<EntityType>[]`:

```tsx
const columns = useMemo<ColumnDef<EntityType>[]>(() => [
  // Row selection checkbox column (if selectable)
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllRowsSelected()}
        ref={(el) => {
          if (el) (el as HTMLButtonElement & { indeterminate?: boolean }).indeterminate = table.getIsSomeRowsSelected();
        }}
        onCheckedChange={(v) => table.toggleAllRowsSelected(!!v)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(v) => row.toggleSelected(!!v)}
        onClick={(e) => e.stopPropagation()}
        aria-label="Select row"
      />
    ),
    size: 48,
    enableSorting: false,
  },

  // Name / primary identifier column
  {
    accessorKey: "name",
    header: "Name",
    size: 400,
    enableSorting: true,  // set based on backend support
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 ring-1 ring-primary/20">
            <EntityIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="font-semibold group-hover:text-primary transition-colors">{item.name}</p>
            <p className="text-xs text-muted-foreground line-clamp-1">{item.description || ""}</p>
          </div>
        </div>
      );
    },
  },

  // Enum / type column
  {
    accessorKey: "agent_type",
    header: "Type",
    enableSorting: true,
    cell: ({ row }) => (
      <Badge variant="outline" className="capitalize font-medium">
        {row.original.agent_type}
      </Badge>
    ),
  },

  // Status column
  {
    accessorKey: "status",
    header: "Status",
    enableSorting: true,
    cell: ({ row }) => <StatusBadge status={row.original.status} />,
  },

  // DateTime column
  {
    accessorKey: "updated_at",
    header: "Updated",
    enableSorting: true,
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {formatRelative(row.original.updated_at)}
      </span>
    ),
  },
], []);
```

### Column `meta` options for sticky columns

Use column `meta` for sticky left/right positioning:

```tsx
{
  accessorKey: "name",
  header: "Name",
  meta: { stickyLeft: true },  // Sticky to left edge on horizontal scroll
  // ...
},
{
  id: "actions",
  header: "",
  meta: { stickyRight: true },  // Sticky to right edge
  // ...
},
```

Additional meta options: `className`, `headerClassName`, `cellClassName` — applied to th/td elements.

### Search & filter bar layout

Render the search input and filter dropdowns **above** the table in a single row:

```tsx
// Filter options — define in frontend/lib/constants/filters.ts
export const <ENTITY>_STATUS_OPTIONS: SelectOption[] = [
  { value: "all", label: "All Status" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];
```

```tsx
// In the page JSX:
<div className="flex items-center gap-4">
  {/* Search — always first */}
  <SearchBar
    placeholder="Search <entities>..."
    onSearch={handleSearch}
  />

  {/* Filter dropdowns — after search, use constants for options */}
  <SelectInput
    options={<ENTITY>_STATUS_OPTIONS}
    value={statusFilter || "all"}
    onValueChange={handleStatusFilter}
    placeholder="All Status"
    className="w-44"
  />
</div>
```

**Search + filter rules:**
- Search is **always present** if the backend supports a `search` body param.
- Search is **always debounced** (400ms) — `SearchBar` handles this internally.
- Filter dropdowns go after the search input in the same row.
- Only generate a filter for a field if the backend actually supports it in the body — never send params the API ignores.
- Common filterable fields: `is_active` (boolean), `status` (enum), `type`/`category` (enum), `agent_id` (reference).
- **Filter options must be constants** — define in `frontend/lib/constants/filters.ts` as `<ENTITY>_<FIELD>_OPTIONS: SelectOption[]`. Never inline option arrays in JSX.
- **Handlers must be named functions** — use `useCallback` for `handleSearch`, `handleStatusFilter`, etc. Never use inline arrows in JSX callbacks.
- For boolean filters (e.g. `is_active`), use `"active"/"inactive"` as select values and convert to `true/false` when passing to the API: `...(statusFilter && { is_active: statusFilter === "active" })`.
- **Always reset page to 1** when any filter or search changes.
- Track `hasActiveFilters` to distinguish "no data" from "no results for filter" in empty states.

### CustomTable usage — Classic pagination

**CRITICAL: `onSortingChange` must always be wired.** Without it, clicking sort headers does nothing — the API is never called with the new sort param.

```tsx
<CustomTable<EntityType>
  loading={isLoading}
  data={data?.items || []}
  columns={columns}
  onRowClick={(row) => router.push(`/<entity-slug>/${row.id}`)}
  enableRowSelection
  onRowSelectionChange={(rows) => setSelectedRows(rows)}
  enableSorting
  onSortingChange={(sort) => {
    setSortBy(sort);   // Updates sort_by param → React Query refetches
    setPage(1);        // ALWAYS reset page on sort change
  }}
  pagination={{
    page,
    pageSize: 20,
    total: data?.total || 0,
    onPageChange: setPage,
  }}
  emptyMessage="No <entities> found"
/>
```

### CustomTable usage — Infinite scroll

```tsx
<CustomTable<EntityType>
  loading={isLoading}
  data={allItems}
  columns={columns}
  onRowClick={(row) => router.push(`/<entity-slug>/${row.id}`)}
  enableSorting
  onSortingChange={setSortBy}
  hasMore={hasMore}
  currentPage={page}
  totalPages={totalPages}
  loadMore={(nextPage) => setPage(nextPage)}
  emptyMessage="No <entities> found"
/>
```

For infinite scroll, accumulate data across pages:
```tsx
const [allItems, setAllItems] = useState<EntityType[]>([]);
const [page, setPage] = useState(1);
const { data, isLoading } = use<Entity>({ ...filters, page, page_size: 20 });
const totalPages = data ? Math.ceil(data.total / 20) : 0;
const hasMore = page < totalPages;

useEffect(() => {
  if (data?.items) {
    setAllItems((prev) => page === 1 ? data.items : [...prev, ...data.items]);
  }
}, [data, page]);
```

### Column rendering rules

Derive columns from the backend model's `to_dict()` output or TABLE metadata. Follow these rules:

| Column type | Render pattern (in `cell` function) |
|---|---|
| **Name/title** (primary identifier) | `size: 400`, render with icon + name + description sub-line |
| **Enum/type** | `<Badge variant="outline" className="capitalize font-medium">{value}</Badge>` |
| **Status** | `<StatusBadge status={row.original.status} />` |
| **Reference** (FK display) | Render the display name, not the UUID. Use a sub-query or joined data from the API response |
| **Model/provider** | Mono-spaced pill: `<div className="inline-flex items-center gap-1.5 rounded-lg bg-muted/80 px-2.5 py-1.5 text-xs font-mono">` |
| **Datetime** | `<span className="text-sm text-muted-foreground">{formatRelative(row.original.<field>)}</span>` |
| **Boolean** | `<StatusBadge status={row.original.<field> ? "active" : "inactive"} />` |
| **Count/number** | Plain text or badge depending on context |
| **IP/string** | `row.original.<field> || "\u2014"` (em-dash fallback) |

**Column selection (max ~6 plus optional select/actions):**
- Always include: primary name/label column
- Always include: status (if entity has one)
- Always include: `updated_at` or `created_at` as last column
- Skip: `id`, `organization_id`, `deleted_at`, secrets, large JSON blobs
- Prioritize: type/category, key reference fields, important counts

**Column icon in name column:**
- Use a relevant `lucide-react` icon matching the entity type
- Wrap in: `<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 ring-1 ring-primary/20">`

### Sorting — MUST trigger API calls

**Sorting is always server-side.** Every sort column click must update `sortBy` state, which changes the React Query key, which triggers a new API request. This is the required wiring:

1. **Frontend state:** `const [sortBy, setSortBy] = useState("-updated_at");`
2. **Pass to hook:** `use<Entity>({ ..., sort_by: sortBy })`
3. **Wire CustomTable:** `onSortingChange={(sort) => { setSortBy(sort); setPage(1); }}`
4. **Backend must accept `sort_by`** — if it doesn't, add it (see Backend sort_by pattern below)

If any of these 4 pieces is missing, sorting silently does nothing. **All 4 are mandatory.**

### Backend list endpoint pattern (POST)

List endpoints use **POST with a JSON body** — not GET with query params. If the backend doesn't have a `/list` endpoint yet, **add it** using this pattern:

```python
from core.services.crud import list_records
from shared.config import settings

@router.post("/list")
def list_<entities>(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    page = max(body.get("page", 1), 1)
    page_size = min(max(body.get("page_size", 20), 1), 100)
    search = body.get("search")
    sort_by = body.get("sort_by")

    # Extract filter params from body
    is_active = body.get("is_active")           # boolean filter example
    # status = body.get("status")               # enum filter example
    # agent_id = body.get("agent_id")           # reference filter example

    filters = []
    if search:
        filters.append(<Model>.name.ilike(f"%{search}%"))
    if is_active is not None:
        filters.append(<Model>.is_active == is_active)
    # if status:
    #     filters.append(<Model>.status == status)
    # if agent_id:
    #     filters.append(<Model>.agent_id == agent_id)

    # Resolve sort order
    allowed_sort_fields = {"name", "is_active", "created_at", "updated_at"}  # whitelist from model columns
    order_by = <Model>.updated_at.desc()  # default
    if sort_by:
        desc = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        if field_name in allowed_sort_fields:
            col = getattr(<Model>, field_name)
            order_by = col.desc() if desc else col.asc()

    items, total = list_records(db, <Model>, org_id, page, page_size, filters, order_by)
    return {"items": [i.to_dict() for i in items], "total": total, "page": page, "page_size": page_size}
```

**Key rules:**
- **POST `/list`** — body contains `{ page, page_size, search, sort_by, is_active, status, ... }`
- **Search**: `body.get("search")` → `ilike` on name/title fields
- **Boolean filters** (e.g. `is_active`): check `is not None` (not just truthy), since `false` is a valid filter value
- **Enum filters** (e.g. `status`): check truthiness, then `== value`
- **Reference filters** (e.g. `agent_id`): check truthiness, then `== uuid`
- Always whitelist allowed sort fields — never pass user input to `getattr()` without validation
- Default to `-updated_at` (newest first) when no `sort_by` is provided
- Validate `page` and `page_size` with `max()`/`min()` since they come from the body, not FastAPI `Query()` validators

### EE/Core dual controller pattern

When generating backend list endpoints, **always create the controller in BOTH editions**:

1. **Core controller** — `core/api/v1/<entity_plural>.py` — contains the actual endpoint logic.
2. **Enterprise controller** — `ee/api/v1/<entity_plural>.py` — typically imports/re-exports the Core controller or adds EE-specific logic (extra filters, RBAC, audit logging).

Both controllers must be **registered in `main.py`** inside the appropriate conditional blocks:
- Core routes are included unconditionally (or under `if not settings.IS_ENTERPRISE`).
- EE routes are included under `if settings.IS_ENTERPRISE` (in `main_ee.py`).

Check existing routers in `main.py` and `main_ee.py` to match the registration pattern already in use.

### `enableSorting` per column

- Set `enableSorting: true` for: name/title, status, type/enum, datetime, numeric columns
- Set `enableSorting: false` for: select checkbox, actions, JSON blobs, long text, references
- Only set `enableSorting: true` on columns whose `accessorKey` is in the backend's `allowed_sort_fields` whitelist

### Empty state pattern

```tsx
{!isLoading && data?.items.length === 0 ? (
  <EmptyState
    icon={<EntityIcon>}
    title="No <entities> yet"
    description="<Contextual description of what to do>"
    action={() => router.push("/<entity-slug>/new")}
    actionLabel="Create <Entity>"
  />
) : (
  <CustomTable ... />
)}
```

### Bulk delete pattern (using row selection)

**CRITICAL: Bulk delete must call the raw API directly and invalidate queries ONCE after all deletes complete.** Never use `mutateAsync` in a loop — each mutation's `onSuccess` would trigger a separate list refetch.

```tsx
const handleBulkDelete = async () => {
  if (idsToDelete.length === 0) return;
  setBulkDeleting(true);
  try {
    await Promise.all(idsToDelete.map((id) => <entity>Api.delete(id)));
    await queryClient.invalidateQueries({ queryKey: ["<entity>"] });
    toast.success(`${idsToDelete.length} <entity>${idsToDelete.length > 1 ? "s" : ""} deleted`);
    setIdsToDelete([]);
    setSelectedRows([]);
  } catch {
    toast.error("Failed to delete <entities>");
  } finally {
    setBulkDeleting(false);
  }
};

// Bulk action in toolbar (inline with search/filters):
{selectedRows.length > 0 && (
  <div className="flex items-center gap-2">
    <span className="text-xs text-muted-foreground tabular-nums">
      {selectedRows.length} selected
    </span>
    <Button variant="destructive" size="sm" className="h-8 text-xs"
      onClick={() => setIdsToDelete(selectedRows.map((r) => r.id))}>
      <Trash2 className="h-3.5 w-3.5 mr-1" />
      Delete
    </Button>
  </div>
)}

// At the bottom of the JSX:
<ConfirmModal
  open={idsToDelete.length > 0}
  onClose={() => setIdsToDelete([])}
  title={`Delete ${idsToDelete.length > 1 ? "<Entities>" : "<Entity>"}`}
  description={`Are you sure you want to delete ${idsToDelete.length} <entity>${idsToDelete.length > 1 ? "s" : ""}? This action cannot be undone.`}
  confirmText={`Delete ${idsToDelete.length} <Entity>${idsToDelete.length > 1 ? "s" : ""}`}
  confirmVariant="destructive"
  confirmLoading={bulkDeleting}
  onConfirm={handleBulkDelete}
/>
```

### Pagination behavior

- Default `page_size`: 10. Options: `PAGE_SIZE_OPTIONS`.
- CustomTable's pagination footer is **always visible** when `total > 0` — shows "1–10 of 50" + page size selector + page controls.
- **Page size selector**: native `<select>` with `pageSizeOptions` array. Resets to page 1 on change.
- **Page number buttons**: For 7 or fewer pages, all shown. For 8+, ellipsis pagination (first, around current, last).
- Current page has primary fill, others are ghost buttons.
- Prev/Next with chevron icons, disabled at boundaries.
- Pagination footer is **inside** the table card border, pinned at bottom with `border-t bg-muted/20`.
- **Always reset page to 1** when any filter, search, sort, or page size changes.
- Pass pagination params to the API hook: `{ page, page_size: pageSize }`.

```tsx
pagination={{
  page,
  pageSize,
  total: data?.total || 0,
  onPageChange: setPage,
  pageSizeOptions: PAGE_SIZE_OPTIONS,
  onPageSizeChange: handlePageSizeChange,
}}
```

## CustomTable Component API Reference

Located at: `frontend/components/shared/custom-table.tsx`

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `data` | `D[]` | `[]` | Array of row data |
| `columns` | `ColumnDef<D>[]` | required | TanStack column definitions |
| `loading` | `boolean` | `false` | Shows skeleton/overlay loading state |
| `pagination` | `{ page, pageSize, total, onPageChange, pageSizeOptions?, onPageSizeChange? }` | — | Classic pagination with optional page size selector |
| `hasMore` | `boolean` | `false` | Infinite scroll: more data available |
| `currentPage` | `number` | — | Infinite scroll: current page |
| `totalPages` | `number` | — | Infinite scroll: total pages |
| `loadMore` | `(page: number) => void` | — | Infinite scroll: load next page callback |
| `onRowClick` | `(row: D) => void` | — | Row click handler |
| `enableRowSelection` | `boolean` | `false` | Enable checkbox row selection |
| `onRowSelectionChange` | `(rows: D[]) => void` | — | Selection change callback |
| `enableSorting` | `boolean` | `false` | Enable column sort indicators |
| `onSortingChange` | `(sort: string) => void` | — | Sort change callback. Format: `"field"` (asc) or `"-field"` (desc) |
| `emptyMessage` | `string` | `"No data found"` | Empty state text |
| `emptyContent` | `ReactNode` | — | Custom empty state content |
| `containerClassName` | `string` | — | Additional class for outer container |
| `tableClassName` | `string` | — | Additional class for table element |
| `headerClassName` | `string` | — | Additional class for thead tr |
| `rowClassName` | `string \| ((row) => string)` | — | Row class (static or dynamic) |
| `cellClassName` | `string` | — | Additional class for all td elements |
| `resetScrollOnDataChange` | `boolean` | `true` | Reset scroll position on data change |

### Column `meta` options

```tsx
meta: {
  stickyLeft?: boolean;    // Stick column to left edge
  stickyRight?: boolean;   // Stick column to right edge
  className?: string;      // Applied to both th and td
  headerClassName?: string; // Applied to th only
  cellClassName?: string;   // Applied to td only
}
```

### Sorting callback format

The `onSortingChange` callback receives a string:
- `"name"` — sort by name ascending
- `"-name"` — sort by name descending
- `"-updated_at"` — sort by updated_at descending

Pass this directly to the backend API as `sort_by` or `ordering` param.

## React Query Hook Pattern

If a hook doesn't exist for the entity, generate it in the appropriate file under `frontend/lib/api/`.

### List hook structure

**List endpoints use POST** to send filter/sort/pagination params in the request body (not query params).

```tsx
const <ENTITY>_KEY = "<entity>";

export const <entity>Api = {
  list: (params?: Record<string, unknown>) =>
    api.post<Paginated<EntityType>>("<endpoint>/list", params || {}).then((r) => r.data),
  get: (id: string) =>
    api.get<EntityType>(`<endpoint>/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    api.post<EntityType>("<endpoint>", data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch<EntityType>(`<endpoint>/${id}`, data).then((r) => r.data),
  delete: (id: string) =>
    api.delete(`<endpoint>/${id}`),
};

export function use<Entity>(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [<ENTITY>_KEY, params],
    queryFn: () => <entity>Api.list(params),
  });
}

export function useDelete<Entity>() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: <entity>Api.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: [<ENTITY>_KEY] }),
  });
}
```

**Key difference from GET pattern:** `api.post("<endpoint>/list", params || {})` sends params as JSON body, not query string. React Query still uses `params` as the query key for caching/deduplication.

### Endpoint derivation

- Read the backend router prefix from `core/api/v1/<entity_plural>.py`.
- The frontend API client already prepends `/api/v1` via the base URL in `frontend/lib/api/client.ts`.
- List endpoint: `"/<entity>/list"` (POST) — e.g. `"/agents/list"`, `"/test-runs/list"`.
- Other endpoints: `"/<entity>"` (GET by id), `"/<entity>"` (POST create), `"/<entity>/<id>"` (PATCH/DELETE).

## Backend Inspection Checklist

When metadata JSON is unavailable, inspect these backend files to derive table configuration:

1. **Model** (`core/models/<entity>.py`):
   - Column names and types (String, Enum, Boolean, DateTime, ForeignKey, etc.)
   - Enum/CHECK constraints for filter options
   - `to_dict()` method to see the exact response shape
   - Relationships for reference columns

2. **Controller** (`core/api/v1/<entity_plural>.py`):
   - List endpoint query params: `page`, `page_size`, `search`, `status`, `agent_id`, etc.
   - Which params actually get used as filters in `list_records()`
   - Sort order (the `order_by` param passed to `list_records()`)
   - Response format: `{"items": [...], "total": N, "page": N, "page_size": N}`

3. **CRUD helper** (`core/services/crud.py`):
   - `list_records()` handles: org_id filter, soft_delete exclusion, pagination, custom filters, order_by
   - Default sort: `created_at.desc()` (unless overridden)

4. **Frontend types** (`frontend/types/index.ts`):
   - Check if the entity type already exists
   - If not, create it based on `to_dict()` output

## Output Checklist

When generating a table page, produce these files:

1. **Page component** — `frontend/app/(dashboard)/<slug>/page.tsx`
   - [ ] `"use client"` directive
   - [ ] `useMemo` for `ColumnDef[]` column definitions
   - [ ] State for page, filters, sortBy, selectedRows, idsToDelete
   - [ ] API hook with filters + pagination + sort params
   - [ ] Delete mutation hook
   - [ ] Filter `SelectInput`s (only for backend-supported params)
   - [ ] Inline header with title, live stats, optional create action (no `PageHeader`)
   - [ ] `EmptyState` for zero results
   - [ ] `CustomTable` with columns, pagination, sorting, selection, row click
   - [ ] Bulk action bar when rows selected
   - [ ] `ConfirmModal` for bulk delete
   - [ ] Proper loading states (CustomTable handles skeleton internally)

2. **API hook** (if missing) — `frontend/lib/api/<module>.ts`
   - [ ] CRUD api object with list/get/create/update/delete
   - [ ] useList hook with params
   - [ ] useDelete mutation with query invalidation
   - [ ] Correct endpoint matching backend router prefix

3. **Type definition** (if missing) — `frontend/types/index.ts`
   - [ ] Interface matching backend `to_dict()` output
   - [ ] Only add if not already present

## What NOT to do

- Do not use the legacy `DataTable` component — always use `CustomTable`.
- Do not create new shared components — use existing ones from `@/components/shared`.
- Do not add client-side filtering when the backend handles it.
- Do not generate filters for query params the backend doesn't support.
- Do not modify the `CustomTable` component to add features — work within its current API.
- Do not use `useEffect` for data fetching — React Query handles it.
- Do not add `"use server"` — all table pages are client components.
- Do not add separate loading spinners — `CustomTable` renders its own skeleton/overlay.
- Do not skip the `ConfirmModal` for bulk delete — always include it.
- Do not use `any` types — use proper TypeScript interfaces.
- Do not define columns inline in JSX — always use `useMemo<ColumnDef<T>[]>`.
- Do not add JSDoc comments (`/** ... */`) on interface props — keep interfaces clean.
- Do not use `mutateAsync` in bulk operations — call raw API + invalidate once (see Bulk delete pattern).
- Do not use `PageHeader` component — build the header inline with live stats (count + active).
- Always include an **actions column** as the last column with edit (pencil) and delete (trash) icon buttons.
- Actions column: `id: "actions"`, `enableSorting: false`, `meta: { className: "text-right" }`, `stopPropagation` on click.
- Edit navigates to `/<entity>/<id>/edit`, delete opens `ConfirmModal` for single item.

## Example invocation

```
User: "Create a table page for test profiles"
Claude:
  1. Check if TABLE metadata exists in entities.json for test_profile
  2. If not, inspect core/models/test_profile.py and core/api/v1/test_profiles.py
  3. Derive columns (ColumnDef[]) from to_dict(), filters from controller query params
  4. Check if useTestProfiles hook exists in frontend/lib/api/
  5. Check if TestProfile type exists in frontend/types/index.ts
  6. Generate page.tsx with CustomTable + ColumnDef columns following Reference Architecture
  7. Generate missing hook/type if needed
  8. List all files created/modified
```
