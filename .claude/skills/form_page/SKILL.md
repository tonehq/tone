---
name: form_page
description: Create a complete create/edit form — both backend API endpoint and frontend UI — for any entity in the Tone platform. Orchestrates the backend_form and frontend_forms skills. User specifies layout mode (modal, drawer, or page) or it auto-detects from field count. Generates the backend create/update endpoints, Zod schema, API mutation hooks, and the form UI.
---

# form_page — Full-stack form generator

Creates a complete **backend create/update API + frontend form UI** for any entity. This is the parent skill that orchestrates [[frontend_forms]] and the backend endpoint pattern.

**Run this skill** when the user asks to create a form, create/edit UI, or add a "New X" flow for an entity. It handles both backend and frontend.

## Inputs

**Always ask the user these questions before starting.** Do not proceed until answered.

1. **Entity name** — e.g. `personality`, `test-profile`, `webhook`
2. **Layout mode** — Ask: "Which form layout do you want?"
   - `modal` — Small dialog overlay (best for 1–3 fields)
   - `drawer` — Side panel (best for 4–10 fields)
   - `page` — Dedicated full page (best for 11+ fields or multi-section)
   - If the user says "auto" or doesn't specify, inspect the model field count and suggest one, then confirm with the user before proceeding.
3. **Create only, edit only, or both?** — Default: both
4. **Parent page** (for modal/drawer) — Which existing page should host this form? For page layout: what route path?

## Execution order

### Phase 1 — Inspect

Read these files to understand the entity:

1. **Model**: `core/models/<entity>.py`
   - All columns with types, constraints, defaults
   - NOT NULL = required field
   - Enum/CHECK = select options
   - ForeignKey = reference field
   - `to_dict()` for response shape
2. **Existing controller**: `core/api/v1/<entity_plural>.py`
   - Check if create/update endpoints already exist
   - Check required fields in create endpoint
3. **Frontend type**: `frontend/src/types/`
4. **Frontend API hooks**: `frontend/src/lib/api/`

### Phase 2 — Backend

Ensure the backend has create and update endpoints:

**Create endpoint** (if missing):
```python
from core.services.crud import create_record
from core.middleware.auth import require_org_member, JWTClaims
from core.database.session import get_db
from shared.config import settings
from uuid import UUID

@router.post("", status_code=201)
def create_<entity>(
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    record = create_record(
        db, <Model>, organization_id=org_id,
        name=body["name"],
        description=body.get("description"),
        # ... map required and optional fields from body
    )
    return record.to_dict()
```

**Update endpoint** (if missing):
```python
from core.services.crud import update_record, get_or_404

@router.patch("/{record_id}")
def update_<entity>(
    record_id: uuid.UUID,
    body: dict = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    record = get_or_404(db, <Model>, record_id, org_id)
    record = update_record(db, record, body)
    return record.to_dict()
```

**Rules:**
- Use `create_record()` and `update_record()` from `core.services.crud`
- Always filter by `organization_id` (multi-tenancy)
- Required fields: `body["field"]` (raises 422 if missing)
- Optional fields: `body.get("field")` or `body.get("field", default)`

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

### Phase 3 — Frontend (following [[frontend_forms]] pattern)

Generate these files:

#### 3a. Zod schema — `frontend/lib/schemas/<entity>.ts`
- Derive validations from backend model constraints
- Export schema + inferred type
- No JSDoc comments

#### 3b. Constants (if enum fields) — `frontend/lib/constants/filters.ts`
- Add `<ENTITY>_<FIELD>_OPTIONS: SelectOption[]`

#### 3c. API mutations (if missing) — `frontend/lib/api/<entity>.ts`
- `useCreate<Entity>` with query invalidation
- `useUpdate<Entity>` with query invalidation

#### 3d. Form UI — depends on layout mode

**Modal** (1–3 fields):
- Add `CustomModal` + `useState` form inline in parent page
- Simple state management, no react-hook-form needed
- `width="sm:max-w-md"`
- Disable submit when required fields empty

**Drawer** (4–10 fields):
- Add `Drawer` + `react-hook-form` + `zodResolver` inline in parent page
- Single drawer handles both create and edit via `editingItem` state
- `reset()` populates form for edit, clears for create
- All inputs use `control` prop (form-integrated mode)

**Page** (5+ fields):
1. Create **shared form component**: `frontend/components/<entity>/<entity>-form.tsx`
   - Default export accepting `control`, `handleSubmit`, `onSubmit` props
   - Settings-page layout: `grid grid-cols-1 lg:grid-cols-3` — labels left, fields right, `Separator` between sections
   - Contains all form fields, connection selectors, settings panels
2. Create **create page**: `frontend/app/(dashboard)/<entity>/new/page.tsx`
   - `useForm` with empty defaults, imports shared form component
   - Submit calls `useCreate` mutation, redirects to `/<entity>` list
3. Create **edit page**: `frontend/app/(dashboard)/<entity>/[id]/edit/page.tsx`
   - `useForm` + `useEffect` to `reset()` with loaded entity data
   - Submit calls `useUpdate` mutation, redirects to `/<entity>` list
   - Import: `import <Entity>Form from "@/components/<entity>/<entity>-form"`

### Phase 4 — Wire triggers

Connect the form to the parent page:

- **Modal/Drawer**: "New <Entity>" button in header opens the form
- **Page**: "New <Entity>" button navigates to `/<entity>/new` via `router.push()`
- **Edit**: Actions column in table with edit icon → navigates to `/<entity>/<id>/edit`
- Both create and edit redirect to list page (`/<entity>`) on success

### Phase 5 — Verify

1. List all files created/modified
2. Confirm backend endpoints are registered in `main.py` — both `if ee_enabled:` and `else:` blocks, and both `core/api/v1/` and `ee/api/v1/` controller files exist
3. Confirm form trigger is wired in the parent page
4. Confirm query invalidation keys match the list hook

## What NOT to do

- Do not add JSDoc comments on schema/interface props
- Do not use inline arrows in JSX — extract as named handlers
- Do not skip Zod schema for drawer/page forms
- Do not create separate component files for modal forms — inline in parent
- Do not forget to reset form state on close
- Do not forget query invalidation on mutation success
- Do not hardcode option arrays — use constants
- Do not modify shared components (CustomModal, Drawer, Form, etc.)
- Do not worry about breadcrumbs — Header auto-hides on `/new` and `/edit` routes
- Do not put entity-specific form components in `@/components/shared` — use `@/components/<entity>/`
- Do not use named exports for form components — use `export default`
- Do not redirect to detail page after create/edit — redirect to list page (`/<entity>`)

## Example invocation

```
User: "Create a form for personalities as a drawer"
Claude:
  1. Read core/models/personality.py → name, description, traits (JSON), is_active
  2. 4 fields → drawer confirmed
  3. Check backend create/update endpoints exist
  4. Create frontend/lib/schemas/personality.ts
  5. Add useCreatePersonality/useUpdatePersonality hooks
  6. Add Drawer + react-hook-form in personalities page
  7. Wire "New Personality" button + row click edit
  8. List all files
```
