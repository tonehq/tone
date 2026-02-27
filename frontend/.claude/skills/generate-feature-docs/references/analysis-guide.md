# Analysis Guide

Reference for tracing a page component through its imports to build a complete feature doc.
Used by the `generate-feature-docs` skill during Step 3 (analysis).

---

## Route → File Mapping

### Dashboard routes (auth required)

| Route                             | Page file                                                       | Main component                                   |
| --------------------------------- | --------------------------------------------------------------- | ------------------------------------------------ |
| `/home`                           | `src/app/(dashboard)/home/page.tsx`                             | Inline or `src/components/home/...`              |
| `/agents`                         | `src/app/(dashboard)/agents/page.tsx`                           | `src/components/agents/AgentListPage.tsx`         |
| `/agents/create/inbound`          | `src/app/(dashboard)/agents/create/inbound/page.tsx`            | `src/components/agents/agent-form/...`           |
| `/agents/create/outbound`         | `src/app/(dashboard)/agents/create/outbound/page.tsx`           | `src/components/agents/agent-form/...`           |
| `/agents/edit/:type/:id`          | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx`          | `src/components/agents/agent-form/...`           |
| `/settings`                       | `src/app/(dashboard)/settings/page.tsx`                         | `src/components/settings/...`                    |
| `/phone-numbers`                  | `src/app/(dashboard)/phone-numbers/page.tsx`                    | `src/components/phone-numbers/...`               |

### Auth routes (public)

| Route                  | Page file                                      |
| ---------------------- | ---------------------------------------------- |
| `/auth/login`          | `src/app/auth/login/page.tsx`                  |
| `/auth/signup`         | `src/app/auth/signup/page.tsx`                 |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx`         |
| `/auth/check-email`    | `src/app/auth/check-email/page.tsx`            |
| `/auth/verify_signup`  | `src/app/auth/verify_signup/page.tsx`          |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx`         |

### Discovery commands

When the target doesn't match the table above:

```bash
# Find page files matching a name
find src/app -name "page.tsx" | xargs grep -l "TARGET_NAME" 2>/dev/null
# Or glob for the route group
ls src/app/(dashboard)/TARGET_NAME/ 2>/dev/null
ls src/app/auth/TARGET_NAME/ 2>/dev/null
```

---

## Page Pattern

Pages under `(dashboard)` are **thin wrappers** — they import and render a component from `src/components/`. The actual UI logic lives in the component.

**Tracing steps:**

1. Read the `page.tsx` file
2. Find the default export's `import` statement (e.g., `import AgentListPage from '@/components/agents/AgentListPage'`)
3. Follow that import — the component file is the **primary analysis target**
4. If the page file itself contains significant JSX (like `home/page.tsx`), treat it as the primary target

---

## Import Classification

When reading a component, classify every import to determine what to trace further:

| Import source             | Classification     | Action                                              |
| ------------------------- | ------------------ | --------------------------------------------------- |
| `@/services/*`            | Service            | Read file → extract endpoint, method, request/response |
| `@/atoms/*`               | Atom               | Read file → extract state shape, read/write actions |
| `@/types/*`               | Type               | Read file → extract interface fields                |
| `@/utils/*`               | Utility            | Read file only if it affects UI behavior            |
| `@/components/shared/*`   | Shared component   | Read `docs/shared-components.md` instead of file    |
| `@/components/ui/*`       | shadcn primitive   | Read `docs/shared-components.md` instead of file    |
| `@/components/<domain>/*` | Child component    | Read file → trace recursively (max 3 levels deep)   |
| `@/constants/*`           | Constants          | Read file → extract relevant values                 |
| `next/navigation`         | Navigation         | Note `useRouter`, `useParams`, `useSearchParams`    |
| `next/link`               | Navigation         | Note `<Link>` hrefs                                 |
| `jotai`                   | State management   | Note `useAtom`, `useAtomValue`, `useSetAtom`        |
| `react`                   | React              | Note hooks (`useState`, `useEffect`, `useCallback`) |
| External packages         | Third-party        | Note only if it affects visible UI                  |

### Depth limit

Trace imports up to **3 levels deep**:

```
page.tsx → component.tsx → sub-component.tsx → (stop)
```

Do not trace beyond 3 levels. If a sub-component has further imports, note them but do not read those files.

---

## Service Tracing

For each import from `@/services/*`, read the service file and extract:

1. **Function name** — e.g., `getAgents`, `upsertAgent`
2. **HTTP method** — `get`, `post`, `put`, `delete`
3. **Endpoint path** — e.g., `/agent/get_all_agents`
4. **Request parameters** — query params, body payload, or path params
5. **Response handling** — what the function returns (raw `res.data`, transformed data, etc.)

### Pattern to look for

```typescript
// Standard service pattern
export const getAgents = async () => {
  const res = await axiosInstance.get('/agent/get_all_agents');
  return res.data;
};
```

Extract: function=`getAgents`, method=`GET`, endpoint=`/agent/get_all_agents`, request=none, response=`res.data`.

### Response shape discovery

- Check the atom that calls the service — it often transforms/normalises the response
- Check `@/types/*` for the interface matching the response
- If no type exists, infer the shape from how the component destructures the data

---

## Atom Tracing

For each import from `@/atoms/*`, read the atom file and extract:

1. **Atom name** — e.g., `settingsAtom`, `fetchAgentList`
2. **Atom type** — read-only, write-only, read-write, async, loadable
3. **State shape** — the interface or type of the atom's value
4. **Services called** — which `@/services/*` functions the atom invokes
5. **Error handling** — try/catch, error state updates
6. **Loadable usage** — if wrapped in `loadable()`, note the loading/error/data states

### Common patterns

```typescript
// Write-only async atom (action)
const fetchAgentList = atom(null, async (_get, set) => {
  const data = await getAgents();
  set(agentsAtom, { list: data, loading: false });
});

// Loadable async atom
const asyncMembersAtom = atom(async (get) => {
  get(membersRefreshAtom); // re-fetch trigger
  const data = await getAllUsersForOrganization();
  return data.map(transformMember);
});
const membersLoadableAtom = loadable(asyncMembersAtom);
```

### What to document

- For write-only atoms: the action it performs and what state it updates
- For loadable atoms: the three states (loading, hasData, hasError) and what the component shows for each
- For refresh patterns: what triggers a re-fetch (e.g., incrementing a counter atom)

---

## Type Extraction

For each import from `@/types/*`, read the type file and extract:

1. **Interface/type name** — e.g., `Agent`, `AgentFormState`
2. **Fields** — name, type, optional/required
3. **Nested types** — if fields reference other interfaces
4. **Usage** — which components/atoms use this type

Also check for form state types in utility files:

- `src/components/agents/agent-form/agentFormUtils.ts` — `AgentFormState`, `defaultFormState`
- Similar patterns for other domain forms

---

## Auth Check

Read `src/middleware.ts` and extract:

1. **PUBLIC_PATHS array** — routes that skip auth
2. **Cookie checked** — `tone_access_token`
3. **Redirect pattern** — `/auth/login?redirect=<pathname>`
4. **Is the target route in PUBLIC_PATHS?** — determines "Auth required: yes/no"

### Auth cookies (4 total)

| Cookie              | Purpose                           | Set by           |
| ------------------- | --------------------------------- | ---------------- |
| `tone_access_token` | JWT token for API auth            | Login flow       |
| `org_tenant_id`     | Organization/tenant ID for API    | Login flow       |
| `login_data`        | User profile data (JSON)          | Login flow       |
| `user_id`           | Current user ID                   | Login flow       |

---

## Navigation Extraction

Scan the component and its children for all navigation triggers:

### Sources

| Code pattern                        | Type              |
| ----------------------------------- | ----------------- |
| `router.push('/path')`              | Programmatic nav  |
| `router.replace('/path')`           | Programmatic nav  |
| `<Link href="/path">`               | Declarative link  |
| `<a href="/path">`                  | HTML link         |
| Middleware redirect                  | Server redirect   |
| `window.location` / `window.open`   | Browser nav       |

### What to capture

For each navigation trigger, document:

- **Trigger**: what user action or condition causes the navigation
- **Destination**: the target URL/route
- **Condition**: when this navigation occurs (always, on success, on error, etc.)

---

## Error Handling Extraction

Scan the component for error states and conditional renders:

### Sources

| Pattern                                    | What it means                      |
| ------------------------------------------ | ---------------------------------- |
| `try/catch` in atom write                  | API call error handling            |
| `loadable` state === 'hasError'            | Async data fetch failure           |
| Conditional render on error state          | Error UI shown to user             |
| `useNotification` calls                    | Toast/snackbar messages            |
| `console.error` / `console.log`           | Silent error logging               |
| Empty/null/undefined checks before render  | Guard against missing data         |
| Loading state (`isLoading`, `state === 'loading'`) | Loading indicators          |

### What to capture

- What error states exist and what UI they produce
- What loading states exist and what UI they produce (spinners, skeletons, disabled buttons)
- What success states trigger notifications or navigation
- What empty/null states the component handles (empty list, no data, etc.)

---

## Shared Components

**Do NOT read individual shared component files.** Instead, read `docs/shared-components.md` which documents the full API for all shared components in a single file. This saves tokens and avoids redundant file reads.

Shared components to look for in imports:

- `CustomButton` — buttons with loading state, variants
- `CustomTable` — data tables with search, pagination, actions
- `CustomModal` — dialogs with confirm/cancel
- `TextInput` — form text inputs with labels
- `CheckboxField` — checkboxes with labels
- `RadioGroupField` — radio button groups
- `CustomLink` — styled navigation links
- `Form` — form wrapper with submit handling
