# Impacted Routes Report

> Generated: 2026-03-17T10:42:15.762593+00:00
> Comparing: `3aff2713` → `ab3afb0e`
> Branch: `new-schema-changes`

## Summary

| Category                         | Count |
| -------------------------------- | ----- |
| Direct route changes             | 0     |
| Transitively impacted routes     | 4     |
| Layout-impacted routes           | 0     |
| Middleware modified              | ❌ No |
| **Total unique routes affected** | **4** |
| Files changed                    | 2     |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route                      | File                                                   | Via                   | Impact Chain                                      |
| -------------------------- | ------------------------------------------------------ | --------------------- | ------------------------------------------------- |
| `/settings`                | `src/app/(dashboard)/settings/page.tsx`                | `AddChannelModal.tsx` | AddChannelModal.tsx → Integrations.tsx → page.tsx |
| `/agents/create/inbound`   | `src/app/(dashboard)/agents/create/inbound/page.tsx`   | `agentFormUtils.ts`   | agentFormUtils.ts → AgentFormPage.tsx → page.tsx  |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `agentFormUtils.ts`   | agentFormUtils.ts → AgentFormPage.tsx → page.tsx  |
| `/agents/create/outbound`  | `src/app/(dashboard)/agents/create/outbound/page.tsx`  | `agentFormUtils.ts`   | agentFormUtils.ts → AgentFormPage.tsx → page.tsx  |

---

## Changed Files by Category

| File                                          | Category  | Status   | +Lines | -Lines |
| --------------------------------------------- | --------- | -------- | ------ | ------ |
| `src/components/settings/AddChannelModal.tsx` | component | modified | +4     | -4     |
| `src/utils/agentFormUtils.ts`                 | util      | modified | +1     | -1     |

---

## Dependency Chains

```
src/components/settings/AddChannelModal.tsx (component, modified)
  → AddChannelModal.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/agentFormUtils.ts (util, modified)
  → agentFormUtils.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```
