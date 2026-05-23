---
name: card_page
description: Create a complete card-grid listing page — both backend API endpoint and frontend UI — for any entity in the Tone platform. Orchestrates the backend_tables and frontend_cards skills in sequence. One command generates the POST /list endpoint with search, filter, sort, pagination, plus the Next.js card-grid page with infinite scroll, search, status filter, create/edit modal, and framer-motion animations.
---

# card_page — Full-stack card grid page generator

Creates a complete **backend API + frontend card-grid listing page** for any entity. This is the parent skill that orchestrates [[backend_tables]] for the backend list endpoint and [[frontend_cards]] for the card-grid UI.

**Run this skill** when the user asks to create a card page, card listing, or grid view for an entity. Use this instead of [[table_page]] when the entity is better represented as cards (key-value previews, profile-like data, config objects) rather than a table.

## When to use card_page vs table_page

- **card_page**: Entities with preview-friendly data (profiles, personalities, knowledge bases, configs with JSONB fields). Uses infinite scroll.
- **table_page**: Entities with many sortable columns (test runs, audit logs, agents). Uses classic pagination.

## Inputs

Ask the user for these (combine into one prompt):

1. **Entity name** — e.g. `test-profiles`, `personalities`, `knowledge-bases`
2. **Route path** (optional) — frontend route slug. Default: kebab-case of entity name under `frontend/app/(dashboard)/`

That's it. Everything else is derived from inspecting the codebase.

## Execution order

### Phase 1 — Inspect

Read these files to understand the entity:

1. **Model**: `core/models/<entity>.py`
   - Column names, types (String, Boolean, DateTime, ForeignKey, Enum, JSONB)
   - `to_dict()` response shape
   - Relationships
   - JSONB fields (these get key-value editors in the form modal)
2. **Existing controller** (if any): `core/api/v1/<entity_plural>.py`
   - Check if a list endpoint already exists
   - Check existing query params / filters
   - Check if create/update/delete endpoints exist
3. **Frontend type** (if any): `frontend/types/index.ts`
   - Check if the entity interface exists
4. **Frontend API hook** (if any): `frontend/lib/api/`
   - Check if list/create/update/delete hooks exist

### Phase 2 — Backend (following [[backend_tables]] pattern)

Create or update the backend list endpoint:

**File**: `core/api/v1/<entity_plural>.py`

```python
@router.post("/list")
def list_<entities>(
    body: dict = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    page = max(body.get("page", 1), 1)
    page_size = min(max(body.get("page_size", 12), 1), 100)
    search = body.get("search")
    sort_by = body.get("sort_by")

    filters = []
    if search:
        filters.append(<Model>.name.ilike(f"%{search}%"))
    # Add filter conditions based on model fields
    # if body.get("is_active") is not None:
    #     filters.append(<Model>.is_active == body["is_active"])

    allowed_sort_fields = {"name", "created_at", "updated_at"}
    order_by = <Model>.updated_at.desc()
    if sort_by:
        desc = sort_by.startswith("-")
        field_name = sort_by.lstrip("-")
        if field_name in allowed_sort_fields:
            col = getattr(<Model>, field_name)
            order_by = col.desc() if desc else col.asc()

    from core.services.crud import list_records
    from shared.config import settings
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)

    items, total = list_records(db, <Model>, org_id, page, page_size, filters, order_by)
    return {"items": [i.to_dict() for i in items], "total": total, "page": page, "page_size": page_size}
```

**Rules:**
- Always `POST /list` with JSON body — never GET with query params
- Default page_size = 12 (card grids show fewer items per page than tables)
- Whitelist sort fields from model columns
- Use `is not None` for boolean filters
- Use `list_records()` from `core.services.crud`

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

Also ensure create, update, and delete endpoints exist (needed for the form modal):

```python
@router.post("", status_code=201)    # Create
@router.get("/{id}")                 # Get single
@router.patch("/{id}")               # Update
@router.delete("/{id}")              # Soft delete
```

### Phase 3 — Frontend (following [[frontend_cards]] pattern)

Generate these files in order:

#### 3a. Type definition (if missing) — `frontend/types/index.ts`
- Add interface matching `to_dict()` output

#### 3b. API hooks — `frontend/lib/api/<entity-slug>.ts`
- `useInfiniteQuery` for list (NOT `useQuery` — card grids use infinite scroll)
- PAGE_SIZE = 12
- `getNextPageParam` calculates from total/page_size
- All mutations invalidate the query key
- Full CRUD: list, get, create, update, delete

#### 3c. Card component — `frontend/components/<entity>/<entity>-card.tsx`
- `motion.div` wrapper with exported `cardVariants`
- Equal height via `h-full flex flex-col`
- Header: name + StatusBadge + ActionMenu (edit/delete)
- Attributes preview: max 2-3 key-value rows + "+N more"
- Clickable card opens edit
- ActionMenu with stopPropagation

#### 3d. Grid component — `frontend/components/<entity>/<entity>-grid.tsx`
- IntersectionObserver for infinite scroll (rootMargin: "200px")
- Staggered animation with AnimatePresence
- Loading spinner for fetchNextPage
- "Showing all N" end state

#### 3e. Grid skeleton — `frontend/components/<entity>/<entity>-grid-skeleton.tsx`
- Mirrors card structure with Skeleton components
- Default count = 6

#### 3f. Form modal — `frontend/components/<entity>/<entity>-form-modal.tsx`
- CustomModal with cancel/submit footer
- Form reset on open via useEffect
- Key-value editor if JSONB field exists (with JSON View toggle)
- Uses showToast / handleApiError

#### 3g. Page component — `frontend/app/(dashboard)/<route>/page.tsx`
- Fixed header (PageHeader + SearchBar + SelectInput filters) — shrink-0
- Scrollable content (skeleton / empty / grid) — flex-1 min-h-0 overflow-y-auto
- Three states: loading, empty (EmptyState), grid
- Grid: `grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3`

### Phase 4 — Verify

After generating all files:

1. List all files created/modified
2. Note any missing pieces (e.g. if model has FKs that need enrichment)
3. Confirm the entity is registered in the API router
4. Confirm imports resolve (check component paths, API hook paths)

## Toast & error handling

- Always import `{ handleApiError, showToast }` from `@/lib/toast`
- Never import `toast` from `sonner` directly
- `showToast.success("Message")` for success
- `handleApiError(err)` for catch blocks

## What NOT to do

- Do not put all frontend code in a single page file — always split into card, grid, skeleton, form modal
- Do not use `useQuery` for the list — use `useInfiniteQuery` with infinite scroll
- Do not use raw `toast` from sonner — use `showToast` / `handleApiError`
- Do not use classic pagination buttons — use IntersectionObserver
- Do not make the entire page scroll — only the card grid area scrolls
- Do not skip framer-motion animations — staggered entrance + exit on cards
- Do not modify shared components (CustomModal, ActionMenu, StatusBadge, etc.)
- Do not add features beyond what the user asked for

## Example invocation

```
User: "Create a card page for personalities"

Claude:
  1. Read core/models/personality.py → columns: name, description, traits (JSONB), is_active, timestamps
  2. Read core/api/v1/personalities.py → check if /list exists
  3. Read frontend/types/index.ts → check if Personality interface exists
  4. Create/update POST /personalities/list endpoint (page_size default 12)
  5. Ensure POST /, PATCH /{id}, DELETE /{id} endpoints exist
  6. Add Personality interface to frontend/types/index.ts
  7. Create frontend/lib/api/personalities.ts → useInfiniteQuery + CUD mutations
  8. Create frontend/components/personality/personality-card.tsx → card with name, traits preview
  9. Create frontend/components/personality/personality-grid.tsx → grid + infinite scroll
  10. Create frontend/components/personality/personality-grid-skeleton.tsx → skeleton
  11. Create frontend/components/personality/personality-form-modal.tsx → name + description + traits KV editor
  12. Create frontend/app/(dashboard)/personalities/page.tsx → page with fixed header + scrollable grid
  13. List all files created/modified
```
