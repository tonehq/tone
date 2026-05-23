---
name: frontend_cards
description: Generate a complete card-grid listing page with infinite scroll, search, status filter, create/edit modal, and framer-motion animations for the Tone frontend. Produces a page.tsx with split components — card, grid, skeleton, and form modal — following the test-profiles page pattern.
---

# frontend_cards — Card grid page generator (Tone)

Generates a fully wired **card-grid listing page** for the Tone frontend. Use this skill when the entity is better represented as cards (key-value previews, profile-like data, config objects) rather than a table. Produces a Next.js `page.tsx` plus split components for the card, grid, skeleton, and form modal.

**Reference implementation:** Test Profiles page (`frontend/app/(dashboard)/test-profiles/page.tsx` + `frontend/components/test-profile/`)

## Hard constraints

- **DO NOT modify** shared components (`PageHeader`, `EmptyState`, `StatusBadge`, `SearchBar`, `SelectInput`, `CustomModal`, `ActionMenu`, `TextInput`, `TextAreaField`, `Button`). Use them as-is from `@/components/shared`.
- **DO NOT invent new component abstractions** — compose from existing shared components only.
- **DO NOT add dependencies** — use only libraries already in `package.json` (`framer-motion`, `@tanstack/react-query`, `lucide-react`, `sonner`, etc.).
- **DO NOT hardcode data** — all data comes from React Query hooks backed by the backend API.
- **Always use `showToast` and `handleApiError`** from `@/lib/toast` — never use raw `toast` from sonner.
- **Always use `useInfiniteQuery`** for the list hook — card grids use infinite scroll, not classic pagination.
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
4. **Frontend types** — `frontend/types/index.ts` → check if interface already exists
5. **Frontend API hooks** — `frontend/lib/api/` → check if hooks already exist
6. **Existing page** — check if `frontend/app/(dashboard)/<route>/page.tsx` already exists

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

### File 2: API hooks

**Path:** `frontend/lib/api/<entity-slug>.ts`

Pattern — uses `useInfiniteQuery` for list, `useMutation` for CUD:

```typescript
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "./client";
import type { Paginated, <Entity> } from "@/types";

const KEY = "<entity-slug>";
const PAGE_SIZE = 12;

export const <entity>Api = {
  list: (p?: Record<string, unknown>) => api.post<Paginated<Entity>>("/<entity-slug>/list", p || {}).then((r) => r.data),
  get: (id: string) => api.get<Entity>(`/<entity-slug>/${id}`).then((r) => r.data),
  create: (d: Record<string, unknown>) => api.post<Entity>("/<entity-slug>", d).then((r) => r.data),
  update: (id: string, d: Record<string, unknown>) => api.patch<Entity>(`/<entity-slug>/${id}`, d).then((r) => r.data),
  delete: (id: string) => api.delete(`/<entity-slug>/${id}`),
};

export const use<Entities> = (filters?: Record<string, unknown>) =>
  useInfiniteQuery({
    queryKey: [KEY, filters],
    queryFn: ({ pageParam = 1 }) =>
      <entity>Api.list({ ...filters, page: pageParam, page_size: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const totalPages = Math.ceil(lastPage.total / lastPage.page_size);
      return lastPage.page < totalPages ? lastPage.page + 1 : undefined;
    },
  });

export const use<Entity> = (id: string) => useQuery({ queryKey: [KEY, id], queryFn: () => <entity>Api.get(id), enabled: !!id });
export const useCreate<Entity> = () => { const qc = useQueryClient(); return useMutation({ mutationFn: <entity>Api.create, onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }) }); };
export const useUpdate<Entity> = () => { const qc = useQueryClient(); return useMutation({ mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => <entity>Api.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }) }); };
export const useDelete<Entity> = () => { const qc = useQueryClient(); return useMutation({ mutationFn: <entity>Api.delete, onSuccess: () => qc.invalidateQueries({ queryKey: [KEY] }) }); };
```

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

Key imports: `ActionMenu`, `StatusBadge` from `@/components/shared`, `Button` from `@/components/ui/button`, `Card`, `Separator` from `@/components/ui/primitives`, `motion` from `framer-motion`, `Hash` from `lucide-react`.

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

- **Always import** `{ handleApiError, showToast }` from `@/lib/toast`
- **Never import** `toast` from `sonner` directly
- `showToast.success("Message")` for success
- `handleApiError(err)` for catch blocks — handles string detail, object `{ errors: { field: "msg" } }`, and fallback

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
