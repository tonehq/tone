---
name: frontend_cards
description: Generate a complete card-grid listing page with infinite scroll, search, status filter, create/edit modal, and framer-motion animations for the Tone frontend. Produces a page.tsx with split components — card, grid, skeleton, and form modal — following the test-profiles page pattern.
---

# frontend_cards — Card grid page generator (Tone)

Generates a fully wired **card-grid listing page** for the Tone frontend. Use this skill when the entity is better represented as cards (key-value previews, profile-like data, config objects) rather than a table. Produces a Next.js `page.tsx` plus split components for the card, grid, skeleton, and form modal.

**Reference implementation:** Organizations page (`frontend/src/components/organizations/OrganizationListPage.tsx` + `OrganizationCard.tsx`)

## IMPORTANT: Pre-Generation Checks

Before generating, **always read these files** to detect the actual frontend patterns:

1. **`frontend/src/components/shared/index.tsx`** — List of available shared components. Verify which exist before using them (e.g. `PageHeader`, `EmptyState`, `StatusBadge` may NOT exist).
2. **`frontend/src/atoms/`** — Check if the project uses Jotai atoms (not React Query). If Jotai atoms exist, use that pattern.
3. **`frontend/src/services/listHelpers.ts`** — Check if `listRequest`/`pagedListRequest` exist for the `POST /list` pattern.
4. **`frontend/src/types/list.ts`** — Check `ListRequest`/`ListResponse` types.
5. **`frontend/src/utils/toast.ts`** and **`frontend/src/utils/helpers.ts`** — Check actual import paths for `showToast` and `handleApiError`.
6. **An existing card-grid page** (e.g. OrganizationListPage) — Match the established pattern.

### Current Project Facts (updated 2026-05-23):
- **State management**: Jotai atoms in `src/atoms/`, **NOT** React Query. Use `useAtom` pattern.
- **Service layer**: `src/services/` with `listRequest` from `src/services/listHelpers.ts` for `POST /list`.
- **Toast/errors**: `showToast` from `@/utils/toast`, `handleApiError` from `@/utils/helpers`.
- **Types**: Entity-specific type files in `src/types/` (e.g. `src/types/mcp.ts`), not a single `index.ts`.
- **IDs are UUID strings**: All entity `id` fields are `string`, not `number`.
- **Non-existent components**: `PageHeader`, `EmptyState`, `StatusBadge` do NOT exist in shared. Build empty states inline or as entity-specific components.
- **Available shared components**: `ActionMenu`, `CustomButton`, `CustomModal`, `CustomTable`, `SearchBar`, `SelectInput`, `TextInput`, `TextAreaField`, `CustomCard`, `SliderField`, `CheckboxField`, `RadioGroupField`, `MultiSelectField`, `CustomTooltip`, `Divider`, `Form`, `Logo`, `ThemeToggle`.

## Hard constraints

- **DO NOT modify** shared components. Use them as-is from `@/components/shared`.
- **DO NOT reference non-existent shared components** — always verify against `@/components/shared/index.tsx` first.
- **DO NOT invent new component abstractions** — compose from existing shared components only.
- **DO NOT add dependencies** — use only libraries already in `package.json` (`framer-motion`, `lucide-react`, etc.).
- **DO NOT hardcode data** — all data comes from Jotai atoms backed by the service layer.
- **Always use `showToast` and `handleApiError`** from `@/utils/toast` and `@/utils/helpers` — never use raw `toast` from sonner.
- **Detect the state management pattern** — use Jotai if atoms exist, React Query only if `useQuery`/`useMutation` are the established pattern.
- **Always verify** the backend endpoint exists before generating.
- **Always split into components** — never put everything in a single page file.

## Inputs

Before generating, gather these inputs (ask the user if not provided):

1. **Entity name** — e.g. `test-profiles`, `personalities`, `knowledge-bases`.
2. **Route path** — where the page lives under `frontend/app/(dashboard)/`. Usually matches the entity slug.
3. **Backend model path** — path to the SQLAlchemy model to derive fields.
4. **Backend API prefix** — e.g. `/api/v1/test-profiles`. Must have `POST /list`, `POST /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`.
5. **Card preview fields** — which fields to show on the card (max 2-3 preview, rest as "+N more"). If not specified, derive from the model.
6. **Form fields** — which fields the create/edit modal should contain. If the entity has a JSONB field, include key-value editor support.
7. **Filter fields** — which fields to expose as filters (typically `is_active` for status). Search is always on the `name` field.

## Phase 1 — Inspect the entity

Read these files to understand the entity shape:

1. **Backend model** — e.g. `core/models/<entity>.py` → column names, types, JSONB fields
2. **Backend controller** — e.g. `core/api/v1/<entity_plural>.py` → endpoint structure, allowed sort/filter fields
3. **Backend service** — e.g. `core/services/<entity>_service.py` → business logic, validation
4. **Frontend types** — check `frontend/src/types/<entity>.ts` or `frontend/src/types/index.ts` for existing interface
5. **Frontend state** — check `frontend/src/atoms/` for existing Jotai atoms, or `frontend/src/services/` for service functions
6. **Existing page** — check if `frontend/src/app/(dashboard)/<route>/page.tsx` or `frontend/src/components/<entity>/` already exists

## Phase 2 — Generate files

Generate these files in order:

### File 1: Type definition (if missing)

**Path:** `frontend/types/index.ts` (append)

```typescript
export interface <Entity> {
  id: string;
  organization_id: string;
  name: string;
  // ... fields from backend model's to_dict()
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
```

### File 2: Service + Atoms (Jotai pattern — current project default)

**Service file:** `frontend/src/services/<entitySlug>Service.ts`

```typescript
import { listRequest } from '@/services/listHelpers';
import type { ListRequest } from '@/types/list';
import type { <Entity>, <Entity>UpsertPayload } from '@/types/<entity-slug>';
import axiosInstance from '@/utils/axios';

export const list<Entities> = (request: ListRequest = {}): Promise<<Entity>[]> =>
  listRequest<<Entity>>('/<entity-prefix>/list', request);

export const get<Entity> = async (id: string): Promise<<Entity>> => {
  const { data } = await axiosInstance.get<<Entity>>('/<entity-prefix>/get', { params: { <entity>_id: id } });
  return data;
};

export const upsert<Entity> = async (payload: <Entity>UpsertPayload): Promise<<Entity>> => {
  const { data } = await axiosInstance.post<<Entity>>('/<entity-prefix>/upsert', payload);
  return data;
};

export const delete<Entity> = async (id: string): Promise<void> => {
  await axiosInstance.delete('/<entity-prefix>/delete', { params: { <entity>_id: id } });
};
```

**Atoms file:** `frontend/src/atoms/<Entity>Atom.tsx`

```typescript
import { list<Entities>, upsert<Entity>, delete<Entity> } from '@/services/<entitySlug>Service';
import type { <Entity>, <Entity>UpsertPayload, <Entities>State } from '@/types/<entity-slug>';
import { atom } from 'jotai';

const <entities>Atom = atom<<Entities>State>({ items: [], loading: false });

const fetch<Entities>Atom = atom(null, async (_get, set) => {
  set(<entities>Atom, (prev) => ({ ...prev, loading: true }));
  try {
    const items = await list<Entities>();
    set(<entities>Atom, { items: items ?? [], loading: false });
  } catch (error) {
    set(<entities>Atom, (prev) => ({ ...prev, loading: false }));
    throw error;
  }
});

const upsert<Entity>Atom = atom(null, async (_get, _set, payload: <Entity>UpsertPayload): Promise<<Entity>> =>
  await upsert<Entity>(payload));

const delete<Entity>Atom = atom(null, async (_get, _set, id: string) => {
  await delete<Entity>(id);
});

export { <entities>Atom, fetch<Entities>Atom, upsert<Entity>Atom, delete<Entity>Atom };
```

**Note:** If the project uses React Query instead of Jotai (check `src/atoms/` vs `src/lib/api/`), generate `useInfiniteQuery` hooks instead. Always match the existing pattern.

### File 3: Card component

**Path:** `frontend/components/<entity>/<entity>-card.tsx`

Structure:
- Wrapped in `motion.div` with stagger animation variants
- `Card` with `h-full flex flex-col` for equal heights
- **Header**: entity name (truncated) + `StatusBadge` + `ActionMenu` (edit/delete)
- **Separator** divider
- **Attributes preview**: icon-prefixed key-value rows (max 2-3), with `+N more` Button link
- **Footer**: "+N more attributes" link (left) + timestamp (right)
- Entire card is clickable (`onClick={onEdit}`)
- Empty state: dashed border Button "Click to add attributes"

Animation variants (exported for grid use):
```typescript
export const cardVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  visible: {
    opacity: 1, y: 0, scale: 1,
    transition: { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const },
  },
  exit: { opacity: 0, scale: 0.95, transition: { duration: 0.2 } },
};
```

Key imports: `ActionMenu` from `@/components/shared`, `Card`, `CardContent` from `@/components/ui/card`, `motion` from `framer-motion`, icons from `lucide-react`. **Do NOT import `StatusBadge` — it does not exist. Build status indicators inline.**

### File 4: Grid component with infinite scroll

**Path:** `frontend/components/<entity>/<entity>-grid.tsx`

Structure:
- Props: `items`, `total`, `hasNextPage`, `isFetchingNextPage`, `fetchNextPage`, `onEdit`, `onDelete`
- `motion.div` grid with `staggerChildren: 0.04`
- `AnimatePresence mode="popLayout"` wrapping card map
- Sentinel `div` with `IntersectionObserver` (rootMargin: "200px")
- Loading spinner: `Loader2` icon + "Loading more..." text
- End state: "Showing all N items" text

```typescript
const sentinelRef = useRef<HTMLDivElement>(null);

const handleIntersect = useCallback(
  (entries: IntersectionObserverEntry[]) => {
    if (entries[0]?.isIntersecting && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  },
  [hasNextPage, isFetchingNextPage, fetchNextPage],
);

useEffect(() => {
  const el = sentinelRef.current;
  if (!el) return;
  const observer = new IntersectionObserver(handleIntersect, { rootMargin: "200px" });
  observer.observe(el);
  return () => observer.disconnect();
}, [handleIntersect]);
```

### File 5: Grid skeleton

**Path:** `frontend/components/<entity>/<entity>-grid-skeleton.tsx`

- Accepts `count` prop (default 6)
- Grid of `Card` components with `Skeleton` matching the card layout structure
- Must mirror the card component structure (header row, separator, attribute rows, footer)

### File 6: Form modal

**Path:** `frontend/components/<entity>/<entity>-form-modal.tsx`

Structure:
- `CustomModal` with title "Create/Edit <Entity>"
- Footer: Cancel (outline) + Submit (primary) buttons, both `flex-1`
- Form resets via `useEffect` when `open` or `editing` changes
- If entity has a JSONB field, include:
  - Key-value editor (grid of Key/Value TextInputs + trash Button per row + "+ Add" Button)
  - JSON View toggle Button (switches to `TextAreaField` with `font-mono`)
  - Bidirectional sync between KV pairs and JSON text
  - JSON parse error display

Props pattern:
```typescript
interface <Entity>FormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { /* entity fields */ }) => void;
  isPending: boolean;
  editing: <Entity> | null;
}
```

### File 7: Page component

**Path:** `frontend/app/(dashboard)/<route>/page.tsx`

Structure — split layout with fixed header and scrollable content:

```typescript
return (
  <div className="flex flex-col flex-1 min-h-0">
    {/* Fixed header */}
    <div className="shrink-0 space-y-5 pb-4">
      <PageHeader title="..." description="..." action={openCreate} actionLabel="New ..." />

      {showFilters && (
        <div className="flex items-center gap-3">
          <SearchBar onSearch={setSearch} placeholder="Search ..." />
          <SelectInput name="status" value={statusFilter} onValueChange={setStatusFilter} options={STATUS_OPTIONS} className="w-[150px]" />
        </div>
      )}
    </div>

    {/* Scrollable content */}
    <div className="flex-1 min-h-0 overflow-y-auto">
      {isLoading ? (
        <GridSkeleton />
      ) : items.length === 0 ? (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <EmptyState icon={...} title="..." description="..." action={openCreate} actionLabel="New ..." />
        </motion.div>
      ) : (
        <Grid items={items} total={total} hasNextPage={!!hasNextPage} isFetchingNextPage={isFetchingNextPage} fetchNextPage={fetchNextPage} onEdit={openEdit} onDelete={handleDelete} />
      )}
    </div>

    <FormModal open={modalOpen} onClose={closeModal} onSubmit={handleSubmit} isPending={...} editing={editing} />
  </div>
);
```

Key state:
- `search` (string) — debounced via SearchBar
- `statusFilter` ("all" | "active" | "inactive") — SelectInput
- `modalOpen` (boolean) + `editing` (Entity | null) — modal state
- Data from `useInfiniteQuery`: `data.pages.flatMap(p => p.items)`, `data.pages[0]?.total`

Error handling:
```typescript
try {
  await mutation.mutateAsync(payload);
  showToast.success("Entity created/updated/deleted");
} catch (err) {
  handleApiError(err);
}
```

## Page layout rules

- **Fixed header area**: `shrink-0` — contains `PageHeader` + filters. Never scrolls.
- **Scrollable content**: `flex-1 min-h-0 overflow-y-auto` — contains skeleton/empty/grid. This is the only scrollable area.
- **Grid**: `grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3`
- This layout works with the dashboard layout's `overflow-hidden` + `flex flex-col` on `<main>`.

## Status filter pattern

```typescript
const STATUS_OPTIONS = [
  { value: "all", label: "All Status" },
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
];

// In the hook call:
useEntities({
  ...(search && { search }),
  ...(statusFilter !== "all" && { is_active: statusFilter === "active" }),
});
```

Show filters when: `profiles.length > 0 || search || statusFilter !== "all"`.

## Toast & error handling

- **Always import** `showToast` from `@/utils/toast` and `handleApiError` from `@/utils/helpers`
- **Never import** `toast` from `sonner` directly
- `showToast.success("Message")` for success
- `handleApiError(err)` for catch blocks — extracts `error.response.data.detail` and shows error toast

## Output checklist

When generating, produce these files:

1. **Type definition** — `frontend/types/index.ts`
   - [ ] Interface matching backend `to_dict()` output
   - [ ] Added after existing types (find appropriate section)

2. **API hooks** — `frontend/lib/api/<entity-slug>.ts`
   - [ ] `useInfiniteQuery` for list (not `useQuery`)
   - [ ] PAGE_SIZE = 12
   - [ ] `getNextPageParam` calculates from total/page_size
   - [ ] All mutations invalidate the query key

3. **Card component** — `frontend/components/<entity>/<entity>-card.tsx`
   - [ ] `motion.div` wrapper with exported `cardVariants`
   - [ ] Equal height via `h-full flex flex-col`
   - [ ] Clickable card opens edit
   - [ ] `ActionMenu` with stopPropagation
   - [ ] Max 2 preview attributes + "+N more"
   - [ ] Empty state with dashed border

4. **Grid component** — `frontend/components/<entity>/<entity>-grid.tsx`
   - [ ] IntersectionObserver for infinite scroll
   - [ ] Staggered animation with `AnimatePresence`
   - [ ] Loading spinner for fetchNextPage
   - [ ] "Showing all N" end state

5. **Grid skeleton** — `frontend/components/<entity>/<entity>-grid-skeleton.tsx`
   - [ ] Mirrors card structure with Skeleton components

6. **Form modal** — `frontend/components/<entity>/<entity>-form-modal.tsx`
   - [ ] `CustomModal` with cancel/submit footer
   - [ ] Form reset on open via `useEffect`
   - [ ] Key-value editor if JSONB field exists
   - [ ] JSON View toggle if JSONB field exists

7. **Page** — `frontend/app/(dashboard)/<route>/page.tsx`
   - [ ] Fixed header + scrollable content split
   - [ ] SearchBar + SelectInput filters
   - [ ] Three states: loading skeleton, empty, grid
   - [ ] `showToast` / `handleApiError` for all operations
   - [ ] Imports from `@/components/<entity>/`

## What NOT to do

- Do not put all code in a single page file — always split into card, grid, skeleton, form modal
- Do not use `useQuery` for the list — use `useInfiniteQuery`
- Do not use raw `toast` from sonner — use `showToast` / `handleApiError`
- Do not use classic pagination buttons — use infinite scroll with IntersectionObserver
- Do not make the entire page scroll — only the card grid area scrolls
- Do not skip framer-motion animations — staggered entrance + exit on cards
- Do not hardcode filter values — derive from backend allowed fields
- Do not forget `"use client"` directive on all components
- Do not use `PageLoader` — use the grid skeleton component instead

## Example invocation

```
User: "Create a card page for knowledge bases"

Claude:
  1. Read core/models/knowledge_base.py → id, name, description, documents (JSONB), is_active, created_at
  2. Read core/api/v1/knowledge_bases.py → POST /list, POST /, PATCH /{id}, DELETE /{id}
  3. Check frontend/types/index.ts → KnowledgeBase interface missing → add it
  4. Create frontend/lib/api/knowledge-bases.ts → useInfiniteQuery list hook + CUD mutations
  5. Create frontend/components/knowledge-base/knowledge-base-card.tsx → card with name, description preview, doc count
  6. Create frontend/components/knowledge-base/knowledge-base-grid.tsx → grid + infinite scroll
  7. Create frontend/components/knowledge-base/knowledge-base-grid-skeleton.tsx → skeleton loader
  8. Create frontend/components/knowledge-base/knowledge-base-form-modal.tsx → name + description fields in CustomModal
  9. Create frontend/app/(dashboard)/knowledge-bases/page.tsx → page shell with fixed header + scrollable grid
  10. Verify build passes
```
