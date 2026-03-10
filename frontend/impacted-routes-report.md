# Impacted Routes Report

> Generated: 2026-03-10T05:07:49.429704+00:00
> Comparing: `ea342ffe` → `feef30ef`
> Branch: `claude/UI-improvements`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 0 |
| Transitively impacted routes | 3 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **3** |
| Files changed | 1 |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/components/agents/AgentFormPage.tsx` | component | modified | +14 | -28 |

---

## Dependency Chains

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```
