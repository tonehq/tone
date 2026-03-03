# Impacted Routes Report

> Generated: 2026-03-03T12:35:29.204607+00:00
> Comparing: `9f3e8418` → `8d7b56b2`
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
| `src/app/auth/login/LoginPage.tsx` | app-config | modified | +1 | -3 |

---

## Dependency Chains

```
src/app/auth/login/LoginPage.tsx (app-config, modified)
  → LoginPage.tsx  → page.tsx
  → /auth/login  [src/app/auth/login/page.tsx]
```
