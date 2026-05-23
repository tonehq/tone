---
name: frontend_forms
description: Generate create/edit forms for the Tone frontend. Supports three layout modes — modal, drawer, and page — chosen based on form complexity or user preference. Reads FORM metadata JSON (from [[backend_form]]) or inspects the backend model directly. Produces the form component, Zod schema, API mutation hook, and wires it into the parent page.
---

# frontend_forms — Form generator (Tone)

## IMPORTANT: Pre-Generation Checks

Before generating, **always read these files** to detect actual project patterns:

1. **`frontend/src/components/shared/index.tsx`** — Verify which shared components exist.
2. **`frontend/src/atoms/`** — Check if Jotai atoms exist (use Jotai pattern, not React Query).
3. **`frontend/src/utils/toast.ts`** and **`frontend/src/utils/helpers.ts`** — Actual paths for `showToast` and `handleApiError`.
4. **`frontend/src/services/`** — Check existing service pattern (axiosInstance from `@/utils/axios`).
5. **An existing form page** (e.g. MCPFormPage, AgentFormPage) — Match established pattern.

### Current Project Facts (updated 2026-05-23):
- **State management**: Jotai atoms, NOT React Query.
- **Toast/errors**: `showToast` from `@/utils/toast`, `handleApiError` from `@/utils/helpers`. **Never use raw `toast` from sonner.**
- **Service layer**: `src/services/` with `axiosInstance` from `@/utils/axios`.
- **Schemas**: `src/schemas/` (not `src/lib/schemas/`).
- **IDs are UUID strings**: All entity `id` fields are `string`.
- **CustomButton**: Use `CustomButton` from `@/components/shared`, NOT `Button` from `@/components/ui/button` in page code.

Generates a fully wired **create/edit form** for any entity. Supports three container modes:

| Mode | When | Component |
|---|---|---|
| `modal` | 1–3 fields, simple entity | `CustomModal` |
| `drawer` | 4–10 fields, moderate complexity | `Drawer` |
| `page` | 11+ fields, multi-section, stepper | Dedicated `/new` route page with `Card` sections |

## Inputs

Ask the user for these:

1. **Entity name** — e.g. `personality`, `test-profile`, `webhook`
2. **Layout mode** — `modal`, `drawer`, or `page`. If not specified, auto-detect from field count (see Layout decision matrix)
3. **Create only, edit only, or both** — Default: both
4. **Where to render** — For modal/drawer: which parent page hosts the trigger. For page: route path under `(dashboard)/`

## Layout decision matrix (auto-detect)

| Condition | Layout | Size |
|---|---|---|
| 1–3 fields, no references | `modal` | `sm:max-w-md` |
| 4–6 fields, 1 section | `drawer` | default |
| 7–10 fields, 1–2 sections | `drawer` | default |
| 11+ fields or 3+ sections | `page` | full width with Card sections |
| Has stepper requirement | `page` | with `FormStepper` |

## Phase 1 — Inspect the entity

Read these files:

1. **Model**: `core/models/<entity>.py` — columns, types, constraints, `to_dict()`
2. **Controller**: `core/api/v1/<entity_plural>.py` — create/update endpoints, required fields
3. **Frontend type**: `frontend/types/index.ts` — check if interface exists
4. **Frontend API hook**: `frontend/lib/api/` — check if create/update mutations exist

## Phase 2 — Generate files

### 2a. Zod schema — `frontend/lib/schemas/<entity>.ts`

```tsx
import { z } from "zod";

export const create<Entity>Schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  is_active: z.boolean().default(true),
});

export type Create<Entity>FormData = z.infer<typeof create<Entity>Schema>;
```

**Schema rules:**
- No JSDoc comments on fields
- `z.string().min(1, "...")` for required strings
- `z.string().optional()` for nullable strings
- `z.boolean().default(true/false)` for booleans with defaults
- `z.enum([...])` for enum fields
- `z.number().min(0)` for numbers
- Derive validation from backend model constraints (NOT NULL, max_length, CHECK)

### 2b. API mutation hook (if missing) — `frontend/lib/api/<entity>.ts`

```tsx
export function useCreate<Entity>() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: <entity>Api.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["<entity>"] }),
  });
}

export function useUpdate<Entity>() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      <entity>Api.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["<entity>"] }),
  });
}
```

### 2c. Form component — depends on layout mode

---

## Modal layout

For simple forms (1–3 fields). Form lives in the **parent page** as a `CustomModal`.

### Pattern

```tsx
// State in parent page
const [createOpen, setCreateOpen] = useState(false);
const [createForm, setCreateForm] = useState({ name: "", description: "" });
const create<Entity> = useCreate<Entity>();
const [isCreating, setIsCreating] = useState(false);

const handleCreate = async () => {
  if (!createForm.name.trim()) return;
  setIsCreating(true);
  try {
    await create<Entity>.mutateAsync(createForm);
    showToast.success("<Entity> created");
    setCreateOpen(false);
    setCreateForm({ name: "", description: "" });
  } catch (err: any) {
    handleApiError(err?.response?.data?.detail || "Failed to create");
  }
  setIsCreating(false);
};

// In JSX (alongside the table)
<CustomModal
  open={createOpen}
  onClose={() => setCreateOpen(false)}
  title="Create <Entity>"
  width="sm:max-w-md"
  footer={
    <>
      <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
      <Button onClick={handleCreate} disabled={!createForm.name.trim()} loading={isCreating}>
        Create
      </Button>
    </>
  }
>
  <div className="space-y-4">
    <TextInput name="name" label="Name" isRequired value={createForm.name}
      onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))} />
    <TextAreaField name="description" label="Description" value={createForm.description}
      onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))} />
  </div>
</CustomModal>
```

**Modal rules:**
- Form state with `useState` (no react-hook-form for simple forms)
- Disable submit when required fields empty
- Reset form on close
- `width="sm:max-w-md"` for small forms, `"sm:max-w-lg"` for medium
- Footer always has Cancel + Submit buttons

---

## Drawer layout

For moderate forms (4–10 fields). Form lives as a `Drawer` in the **parent page**.

### Pattern

```tsx
// State in parent page
const [drawerOpen, setDrawerOpen] = useState(false);
const [editingItem, setEditingItem] = useState<EntityType | null>(null);

const { control, handleSubmit, reset } = useForm<Create<Entity>FormData>({
  resolver: zodResolver(create<Entity>Schema),
  defaultValues: { name: "", description: "", is_active: true },
});

useEffect(() => {
  if (editingItem) {
    reset({
      name: editingItem.name,
      description: editingItem.description || "",
      is_active: editingItem.is_active,
    });
  } else {
    reset({ name: "", description: "", is_active: true });
  }
}, [editingItem, reset]);

const onSubmit = async (values: Create<Entity>FormData) => {
  try {
    if (editingItem) {
      await update<Entity>.mutateAsync({ id: editingItem.id, data: values });
      showToast.success("<Entity> updated");
    } else {
      await create<Entity>.mutateAsync(values);
      showToast.success("<Entity> created");
    }
    setDrawerOpen(false);
    setEditingItem(null);
  } catch (err: any) {
    handleApiError(err?.response?.data?.detail || "Failed to save");
  }
};

// Trigger
<Button onClick={() => { setEditingItem(null); setDrawerOpen(true); }}>New <Entity></Button>

// Row edit action
onRowClick={(item) => { setEditingItem(item); setDrawerOpen(true); }}

// In JSX
<Drawer
  open={drawerOpen}
  onClose={() => { setDrawerOpen(false); setEditingItem(null); }}
  title={editingItem ? `Edit ${editingItem.name}` : "Create <Entity>"}
  footer={
    <>
      <Button variant="outline" onClick={() => { setDrawerOpen(false); setEditingItem(null); }}>Cancel</Button>
      <Button onClick={handleSubmit(onSubmit)} loading={create<Entity>.isPending || update<Entity>.isPending}>
        {editingItem ? "Save Changes" : "Create"}
      </Button>
    </>
  }
>
  <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
    <TextInput name="name" control={control} label="Name" isRequired />
    <TextAreaField name="description" control={control} label="Description" />
    <CheckboxField name="is_active" control={control} label="Active" />
    <SelectInput name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
  </Form>
</Drawer>
```

**Drawer rules:**
- Use `react-hook-form` + `zodResolver` for validation
- Single Drawer handles both create and edit (via `editingItem` state)
- `reset()` populates form when editing, clears when creating
- All inputs use `control` prop (form-integrated mode)
- Footer changes label: "Create" vs "Save Changes"
- Close resets `editingItem` to null

---

## Page layout

For complex forms (11+ fields, multi-section). Dedicated route at `/<entity>/new`.

### Pattern — Single form

```tsx
// File: frontend/app/(dashboard)/<entity>/new/page.tsx
"use client";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { showToast } from "@/utils/toast";
import { handleApiError } from "@/utils/helpers";
import { create<Entity>Schema, type Create<Entity>FormData } from "@/lib/schemas/<entity>";
import { useCreate<Entity> } from "@/lib/api/<entity>";
import { Form, TextInput, TextAreaField, SelectInput, CheckboxField } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/primitives";
import { Button } from "@/components/ui/button";

export default function New<Entity>Page() {
  const router = useRouter();
  const create = useCreate<Entity>();

  const { control, handleSubmit } = useForm<Create<Entity>FormData>({
    resolver: zodResolver(create<Entity>Schema),
    defaultValues: { name: "", description: "", is_active: true },
  });

  const onSubmit = async (values: Create<Entity>FormData) => {
    try {
      const result = await create.mutateAsync(values);
      showToast.success("<Entity> created");
      router.push(`/<entity>/${result.id}`);
    } catch (err: any) {
      handleApiError(err?.response?.data?.detail || "Failed to create");
    }
  };

  return (
    <div className="flex flex-col gap-5 flex-1 min-h-0">
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Create <Entity></h1>
          <p className="text-[13px] text-muted-foreground mt-0.5">Fill in the details below</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => router.back()}>Cancel</Button>
          <Button onClick={handleSubmit(onSubmit)} loading={create.isPending}>Create</Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto space-y-4">
        <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
          <Card>
            <CardHeader><CardTitle className="text-base">Basic Info</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <TextInput name="name" control={control} label="Name" isRequired />
              <TextAreaField name="description" control={control} label="Description" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">Configuration</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <SelectInput name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
                <SelectInput name="priority" control={control} label="Priority" options={PRIORITY_OPTIONS} />
              </div>
              <CheckboxField name="is_active" control={control} label="Active" />
            </CardContent>
          </Card>
        </Form>
      </div>
    </div>
  );
}
```

### Pattern — Stepper form

For very complex forms with 3+ sections, use `FormStepper`:

```tsx
const STEPS = [
  { id: "basics", title: "Basic Info", description: "Name and description" },
  { id: "config", title: "Configuration", description: "Settings and options" },
  { id: "review", title: "Review", description: "Confirm and create" },
];

const [currentStep, setCurrentStep] = useState(0);

// In JSX
<FormStepper steps={STEPS} currentStep={currentStep} onStepClick={setCurrentStep} />

{currentStep === 0 && (
  <Card>...</Card>
)}
{currentStep === 1 && (
  <Card>...</Card>
)}
{currentStep === 2 && (
  <Card>... review summary ...</Card>
)}

<div className="flex justify-between">
  <Button variant="outline" onClick={() => setCurrentStep((s) => s - 1)} disabled={currentStep === 0}>
    Previous
  </Button>
  {currentStep < STEPS.length - 1 ? (
    <Button onClick={() => setCurrentStep((s) => s + 1)}>Next</Button>
  ) : (
    <Button onClick={handleSubmit(onSubmit)} loading={create.isPending}>Create</Button>
  )}
</div>
```

**Page rules:**
- `react-hook-form` + `zodResolver` always
- **Create a shared form component** at `frontend/components/<entity>/<entity>-form.tsx` with `export default`
- Form component accepts `control`, `handleSubmit`, `onSubmit` props — contains all form fields
- Both create (`/new`) and edit (`/[id]/edit`) pages import and use the same form component
- Create page: `useForm` with empty defaults, submit calls `useCreate` mutation
- Edit page: `useForm` with empty defaults + `useEffect` to `reset()` with loaded entity data
- Use settings-page layout: `grid grid-cols-1 lg:grid-cols-3` — labels left (1/3), fields right (2/3), separated by `Separator`
- Inline header (no PageHeader) with title + Cancel/Submit
- Flex layout: `flex flex-col gap-5 flex-1 min-h-0`
- Redirect to list page on success: `router.push("/<entity>")`
- Import form component as default: `import AgentForm from "@/components/agents/agent-form"`

---

## Field type → Component mapping

| Field type | Component | Props |
|---|---|---|
| `string` | `TextInput` | `name`, `control`, `label`, `isRequired`, `placeholder` |
| `textarea` | `TextAreaField` | `name`, `control`, `label`, `rows` (default 3) |
| `integer` | `TextInput` | `type="number"`, `min`, `max` |
| `float` | `TextInput` | `type="number"`, `step="0.01"` |
| `boolean` | `CheckboxField` | `name`, `control`, `label` |
| `enum` | `SelectInput` | `name`, `control`, `label`, `options` from constants |
| `reference` | `SelectInput` or `SearchableSelect` | options from API hook |
| `multi_reference` | `MultiSelectField` | `name`, `control`, `options` |
| `password` | `TextInput` | `type="password"` |
| `json` | `TextAreaField` | `rows={6}`, `className="font-mono text-sm"` |
| `date` | `TextInput` | `type="date"` |
| `datetime` | `TextInput` | `type="datetime-local"` |
| `file` | Custom file input | Hidden input + Button trigger |

## Enum options — always constants

Define in `frontend/lib/constants/filters.ts`:

```tsx
export const <ENTITY>_<FIELD>_OPTIONS: SelectOption[] = [
  { value: "option1", label: "Option 1" },
  { value: "option2", label: "Option 2" },
];
```

## Edit form — loading initial values

For drawer/page edit modes, load the entity and populate:

```tsx
// Drawer: use reset() in useEffect when editingItem changes
// Page: use a separate /edit route with useForm defaultValues from API
const { data: entity } = use<Entity>(id);

useEffect(() => {
  if (entity) {
    reset({
      name: entity.name,
      description: entity.description || "",
      // ... map all fields
    });
  }
}, [entity, reset]);
```

## Output checklist

1. **Zod schema** — `frontend/lib/schemas/<entity>.ts`
   - [ ] Schema with proper validations
   - [ ] Exported type alias

2. **API mutations** (if missing) — `frontend/lib/api/<entity>.ts`
   - [ ] `useCreate<Entity>` with query invalidation
   - [ ] `useUpdate<Entity>` with query invalidation

3. **Constants** (if enum fields) — `frontend/lib/constants/filters.ts`
   - [ ] `<ENTITY>_<FIELD>_OPTIONS` arrays

4. **Shared form component** (for page layout) — `frontend/components/<entity>/<entity>-form.tsx`
   - [ ] Default export, accepts `control`, `handleSubmit`, `onSubmit` props
   - [ ] Contains all form sections (Basic Info, Connections, etc.)
   - [ ] Settings-page layout: `grid grid-cols-1 lg:grid-cols-3` with `Separator`

5. **Form pages** (for page layout):
   - [ ] Create: `frontend/app/(dashboard)/<entity>/new/page.tsx` — imports shared form
   - [ ] Edit: `frontend/app/(dashboard)/<entity>/[id]/edit/page.tsx` — imports shared form, loads entity with `useEffect` + `reset()`
   - [ ] Both redirect to list page on success

6. **Form UI** — depends on layout:
   - [ ] Modal: inline in parent page with `CustomModal`
   - [ ] Drawer: inline in parent page with `Drawer` + `react-hook-form`
   - [ ] Page: shared form component + create/edit page wrappers

7. **Trigger wired** — Button/action that opens the form
   - [ ] "New <Entity>" button in page header or toolbar
   - [ ] Edit action column in table (pencil icon) → navigates to `/<entity>/<id>/edit`

## What NOT to do

- Do not add JSDoc comments on interface/schema props
- Do not use inline arrow functions in JSX — extract as named handlers or `useCallback`
- Do not use `any` types — use proper interfaces
- Do not skip the Zod schema for drawer/page forms — always validate
- Do not create a separate component file for modal forms — inline in parent page
- Do not forget to reset form state on close (modal/drawer)
- Do not forget query invalidation on mutation success
- Do not hardcode option arrays in JSX — use constants from `lib/constants/`
- Do not use `PageHeader` component — build inline header
- Do not worry about breadcrumbs — the Header component auto-hides on `/new` and `/edit` routes
- Do not import from `@/components/shared` for entity-specific form components — use `@/components/<entity>/<entity>-form`

## Example invocation

```
User: "Create a form for personalities with drawer layout"
Claude:
  1. Read core/models/personality.py → name (string), description (text), traits (JSON), is_active (bool)
  2. Count: 4 fields → drawer confirmed
  3. Create frontend/lib/schemas/personality.ts with Zod schema
  4. Check/create useCreatePersonality + useUpdatePersonality hooks
  5. Add Drawer with react-hook-form in personalities page
  6. Wire "New Personality" button + row click for edit
  7. List all files modified
```
