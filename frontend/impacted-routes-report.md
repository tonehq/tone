# Impacted Routes Report

> Generated: 2026-03-09T03:41:41.162068+00:00
> Comparing: `2c294095` → `9908f23c`
> Branch: `claude/UI-improvements`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 0 |
| Transitively impacted routes | 2 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **2** |
| Files changed | 6 |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | `IntegrationAtom.tsx` | IntegrationAtom.tsx → Integrations.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `AgentListPage.tsx` | AgentListPage.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/atoms/IntegrationAtom.tsx` | atom | modified | +2 | -5 |
| `src/components/agents/AgentListPage.tsx` | component | modified | +2 | -2 |
| `src/components/settings/ApiKeysTab.tsx` | component | modified | +2 | -4 |
| `src/components/settings/IntegrationsTable.tsx` | component | modified | +1 | -1 |
| `src/components/settings/PublicKeysTab.tsx` | component | modified | +2 | -1 |
| `src/utils/date.ts` | util | added | +17 | -0 |

---

## Dependency Chains

```
src/atoms/IntegrationAtom.tsx (atom, modified)
  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/agents/AgentListPage.tsx (component, modified)
  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/settings/ApiKeysTab.tsx (component, modified)
  → ApiKeysTab.tsx  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/IntegrationsTable.tsx (component, modified)
  → IntegrationsTable.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/components/settings/PublicKeysTab.tsx (component, modified)
  → PublicKeysTab.tsx  → Apikeys.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/date.ts (util, added)
  → date.ts  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/date.ts (util, added)
  → date.ts  → IntegrationAtom.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```
