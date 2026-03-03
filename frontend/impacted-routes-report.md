# Impacted Routes Report

> Generated: 2026-03-03T12:27:16.479627+00:00
> Comparing: `de22d2b3` → `3c461694`
> Branch: `claude/shadcn-migration`

## Summary

| Category | Count |
|----------|-------|
| Direct route changes | 0 |
| Transitively impacted routes | 1 |
| Layout-impacted routes | 0 |
| Middleware modified | ❌ No |
| **Total unique routes affected** | **1** |
| Files changed | 1 |

---

## Transitively Impacted Routes

Routes affected via shared components, atoms, or services.

| Route | File | Via | Impact Chain |
|-------|------|-----|--------------|
| `/auth/login` | `src/app/auth/login/page.tsx` | `LoginPage.tsx` | LoginPage.tsx → page.tsx |

---

## Changed Files by Category

| File | Category | Status | +Lines | -Lines |
|------|----------|--------|--------|--------|
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +3 | -1 |

---

## Dependency Chains

```
src/app/auth/login/LoginPage.tsx (app-config, modified)
  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```
