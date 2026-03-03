# Impacted Routes Report

> Generated: 2026-03-03T09:37:42.565230+00:00
> Comparing: `ebcbc81b` → `12feae1e`
> Branch: `claude/shadcn-migration`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 4 |
| Transitively impacted routes | 5 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **9** |
| Files changed | 13 |

---

## Directly Modified Routes

Routes where `page.tsx` itself was changed.

| Route | File | Change |
|-------|------|--------|
| `/home` | `src/app/(dashboard)/home/page.tsx` | modified |
| `/auth/forgotpassword` | `src/app/auth/forgotpassword/page.tsx` | modified |
| `/auth/reset-password` | `src/app/auth/reset-password/page.tsx` | modified |
| `/auth/verify_signup` | `src/app/auth/verify_signup/page.tsx` | modified |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/agents/create/inbound` | `src/app/(dashboard)/agents/create/inbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/create/outbound` | `src/app/(dashboard)/agents/create/outbound/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents/edit/[type]/[id]` | `src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx` | `AgentFormPage.tsx` | AgentFormPage.tsx → page.tsx |
| `/agents` | `src/app/(dashboard)/agents/page.tsx` | `AgentListPage.tsx` | AgentListPage.tsx → page.tsx |
| `/settings` | `src/app/(dashboard)/settings/page.tsx` | `Integrations.tsx` | Integrations.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +2 | -2 |
| `src/app/auth/signup/SignupClient.tsx` | app-config | modified | +2 | -12 |
| `src/components/agents/AgentFormPage.tsx` | component | modified | +10 | -14 |
| `src/components/agents/AgentListPage.tsx` | component | modified | +3 | -2 |
| `src/components/settings/Integrations.tsx` | component | modified | +6 | -7 |
| `src/components/ui/sonner.tsx` | component | modified | +30 | -36 |
| `src/app/(dashboard)/home/page.tsx` | page | modified | +1 | -1 |
| `src/app/auth/forgotpassword/page.tsx` | page | modified | +2 | -12 |
| `src/app/auth/reset-password/page.tsx` | page | modified | +2 | -13 |
| `src/app/auth/verify_signup/page.tsx` | page | modified | +2 | -12 |
| `src/services/auth/helper.tsx` | service | modified | +3 | -2 |
| `src/utils/helpers.ts` | util | modified | +13 | -0 |
| `src/utils/toast.tsx` | util | modified | +8 | -16 |

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
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/components/agents/AgentFormPage.tsx (component, modified)
  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/components/agents/AgentListPage.tsx (component, modified)
  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/components/settings/Integrations.tsx (component, modified)
  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/helpers.ts (util, modified)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/helpers.ts (util, modified)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/helpers.ts (util, modified)
  → helpers.ts  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/helpers.ts (util, modified)
  → helpers.ts  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/helpers.ts (util, modified)
  → helpers.ts  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```

```
src/utils/toast.tsx (util, modified)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/inbound  [src/app/(dashboard)/agents/create/inbound/page.tsx]
```

```
src/utils/toast.tsx (util, modified)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/create/outbound  [src/app/(dashboard)/agents/create/outbound/page.tsx]
```

```
src/utils/toast.tsx (util, modified)
  → toast.tsx  → AgentFormPage.tsx  → page.tsx
  → /agents/edit/[type]/[id]  [src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx]
```

```
src/utils/toast.tsx (util, modified)
  → toast.tsx  → AgentListPage.tsx  → page.tsx
  → /agents  [src/app/(dashboard)/agents/page.tsx]
```

```
src/utils/toast.tsx (util, modified)
  → toast.tsx  → Integrations.tsx  → page.tsx
  → /settings  [src/app/(dashboard)/settings/page.tsx]
```
