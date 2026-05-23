---
name: table_page
description: Create a complete table listing page — both backend API endpoint and frontend UI — for any entity in the Tone platform. Orchestrates the backend_tables and frontend_tables skills in sequence. One command generates the POST /list endpoint with search, filter, sort, pagination, plus the Next.js page with CustomTable, SearchBar, filters, bulk delete, and page size selector.
---

# table_page — Full-stack table page generator

Creates a complete **backend API + frontend listing page** for any entity. This is the parent skill that orchestrates [[frontend_tables]] and the backend endpoint pattern in sequence.

**Run this skill** when the user asks to create a table/list page for an entity. It handles both sides.

## Inputs

Ask the user for these (combine into one prompt):

1. **Entity name** — e.g. `personalities`, `test-profiles`, `webhooks`, `schedules`
2. **Route path** (optional) — frontend route slug. Default: kebab-case of entity name under `frontend/app/(dashboard)/`

That's it. Everything else is derived from inspecting the codebase.

## Execution order

### Phase 1 — Inspect

Read these files to understand the entity:

1. **Model**: `core/models/<entity>.py`
   - Column names, types (String, Boolean, DateTime, ForeignKey, Enum)
   - `to_dict()` response shape
   - Relationships
2. **Existing controller** (if any): `core/api/v1/<entity_plural>.py`
   - Check if a list endpoint already exists
   - Check existing query params / filters
3. **Frontend type** (if any): `frontend/types/index.ts`
   - Check if the entity interface exists
4. **Frontend API hook** (if any): `frontend/lib/api/`
   - Check if list/delete hooks exist

### Phase 2 — Backend (following [[frontend_tables]] backend pattern)

Create or update the backend list endpoint:

**File**: `core/api/v1/<entity_plural>.py`

```python
@router.post("/list")
def list_<entities>(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    from core.services.crud import list_records
    from shared.config import settings
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)

    page = max(body.get("page", 1), 1)
    page_size = min(max(body.get("page_size", 20), 1), 100)
    search = body.get("search")
    sort_by = body.get("sort_by")
    # Extract filter params from body based on model columns
    # e.g. is_active = body.get("is_active")

    filters = []
    if search:
        filters.append(<Model>.name.ilike(f"%{search}%"))
    # Add filter conditions based on model fields
    # if is_active is not None:
    #     filters.append(<Model>.is_active == is_active)

    allowed_sort_fields = {"name", "created_at", "updated_at"}  # derive from model
    order_by = <Model>.updated_at.desc()
    if sort_by:
        desc = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        if field_name in allowed_sort_fields:
            col = getattr(<Model>, field_name)
            order_by = col.desc() if desc else col.asc()

    items, total = list_records(db, <Model>, org_id, page, page_size, filters, order_by)
    return {"items": [i.to_dict() for i in items], "total": total, "page": page, "page_size": page_size}
```

**Rules:**
- Always `POST /list` with JSON body — never GET with query params
- Whitelist sort fields from model columns
- Use `is not None` for boolean filters
- Use `list_records()` from `core.services.crud`
- Enrich with counts if needed (join queries for related entity counts)

### Dual Controller Generation (EE + Core)

Every backend endpoint must exist in **two** controller files:

1. **Core controller**: `core/api/v1/<entity_plural>.py`
   - Import: `from core.middleware.auth import require_org_member, JWTClaims`
   - Import: `from shared.config import settings`
   - org_id: `UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)`

2. **EE controller**: `ee/api/v1/<entity_plural>.py`
   - Import: `from ee.middleware.auth import require_ee_org_member, EEJWTClaims`
   - Auth guard: `claims: EEJWTClaims = Depends(require_ee_org_member)`
   - org_id: `UUID(claims.org_id)`

Everything else is identical — same endpoints, same service calls, same imports from `core.services.*` and `core.database.session`.

### Route Registration in `main.py`

There is NO `main_ee.py`. A single `main.py` has conditional blocks:

1. **Core imports** (top of file): `from core.api.v1 import <entity_plural>`
2. **EE imports** (inside `if ee_enabled:` block): `from ee.api.v1 import <entity_plural> as ee_<entity_plural>`
3. **Register in `if ee_enabled:` block**: `api_v1.include_router(ee_<entity_plural>.router, prefix="/<entity-kebab>", tags=["<entity-kebab>"])`
4. **Register in `else:` block**: `api_v1.include_router(<entity_plural>.router, prefix="/<entity-kebab>", tags=["<entity-kebab>"])`

### Phase 3 — Frontend (following [[frontend_tables]] pattern)

Generate these files:

#### 3a. Type definition (if missing) — `frontend/types/index.ts`
- Add interface matching `to_dict()` output
- No JSDoc comments on props

#### 3b. Filter constants — `frontend/lib/constants/filters.ts`
- Add `<ENTITY>_STATUS_OPTIONS` or similar constants
- Import `SelectOption` type from shared components

#### 3c. API hook — `frontend/lib/api/<module>.ts`

```tsx
const KEY = "<entity>";
export const <entity>Api = {
  list: (params?: Record<string, unknown>) =>
    api.post<Paginated<EntityType>>("/<entity>/list", params || {}).then((r) => r.data),
  get: (id: string) => api.get<EntityType>(`/<entity>/${id}`).then((r) => r.data),
  create: (d: Record<string, unknown>) => api.post<EntityType>("/<entity>", d).then((r) => r.data),
  update: (id: string, d: Record<string, unknown>) => api.patch<EntityType>(`/<entity>/${id}`, d).then((r) => r.data),
  delete: (id: string) => api.delete(`/<entity>/${id}`),
};
export function use<Entity>(params?: Record<string, unknown>) {
  return useQuery({ queryKey: [KEY, params], queryFn: () => <entity>Api.list(params) });
}
export function useDelete<Entity>() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: <entity>Api.delete, onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }) });
}
```

#### 3d. Page component — `frontend/app/(dashboard)/<slug>/page.tsx`

Follow the full [[frontend_tables]] reference architecture:

- `"use client"` directive
- `useMemo<ColumnDef<T>[]>` for columns — no JSDoc comments
- State: `page`, `pageSize`, `sortBy`, `search`, filter states
- Named `useCallback` handlers: `handleSearch`, `handleStatusFilter`, `handlePageSizeChange`
- Bulk delete via raw API + single `queryClient.invalidateQueries`
- `CustomTable` with: `enableRowSelection`, `enableSorting`, `onSortingChange`, `pagination` with `pageSizeOptions`
- `SearchBar` + `SelectInput` filters in toolbar row
- `ConfirmModal` for bulk delete
- Inline header (no `PageHeader` component) with live stats
- Flex layout: `flex flex-col gap-5 flex-1 min-h-0`
- Table container: `flex flex-col flex-1 min-h-0`

### Phase 4 — Verify

After generating all files:

1. List all files created/modified
2. Note any missing pieces (e.g. if model has FKs that need enrichment)
3. Confirm the entity is registered in `main.py` — both `if ee_enabled:` and `else:` blocks, and both `core/api/v1/` and `ee/api/v1/` controller files exist

## Reference — Agents page (canonical example)

The agents page at `frontend/app/(dashboard)/agents/page.tsx` is the canonical implementation of this pattern. When in doubt, match its structure:

- Backend: `POST /agents/list` with body `{ page, page_size, search, sort_by, is_active }`
- Frontend: `CustomTable<Agent>` with checkbox, name+desc, count columns, status pill, relative time
- Bulk delete: `agentsApi.delete()` in `Promise.all` + single `queryClient.invalidateQueries`
- Page size: `PAGE_SIZE_OPTIONS` with default `10`
- Sorting: `onSortingChange` wired → `setSortBy` + `setPage(1)`

## Column rendering reference

| Data type | Rendering |
|---|---|
| Name + description | Icon (9x9 rounded-lg) + name (`text-sm font-medium`) + desc (`text-xs text-muted-foreground`) |
| Count (> 0) | Tinted pill: `bg-primary/10 dark:bg-primary/15 text-primary` with icon |
| Count (= 0) | Plain `text-sm text-muted-foreground` "0" |
| Boolean status | Pill with dot: `bg-emerald-100 dark:bg-emerald-500/15` for true, `bg-muted` for false |
| Enum | `Badge variant="outline" className="capitalize"` |
| DateTime | `text-sm text-muted-foreground` with `formatRelative()` |
| Reference | Display name (joined), not UUID |

All colors must work in both light and dark themes. Use `dark:` variants for any hardcoded colors.

## What NOT to do

- Do not add JSDoc comments (`/** ... */`) on interface props
- Do not use `PageHeader` component — build inline header with stats
- Do not use `mutateAsync` in bulk delete loops — use raw API + invalidate once
- Do not use GET for list endpoints — always POST `/list` with body
- Do not hardcode opacity values for dark mode — use `dark:` variant or theme tokens
- Do not add features beyond what the user asked for
- Do not modify `CustomTable`, `SearchBar`, or any shared components

## Example invocation

```
User: "Create a table page for personalities"
Claude:
  1. Read core/models/personality.py → columns: name, description, traits (JSON), is_active, timestamps
  2. Read core/api/v1/personalities.py → check if /list exists
  3. Read frontend/types/index.ts → check if Personality interface exists
  4. Create/update POST /personalities/list endpoint with search, sort_by, is_active filters
  5. Add PERSONALITY_STATUS_OPTIONS to frontend/lib/constants/filters.ts
  6. Create/update frontend/lib/api/personalities.ts with list (POST), hooks
  7. Create frontend/app/(dashboard)/personalities/page.tsx with CustomTable
  8. List all files created/modified
```
