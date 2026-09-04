# <repo> — frontend specifics (repo-local, shared)

THIS repo's real FE names, paths, and tokens — **shared by both `plan-mode` (when planning) and
`code-review` (when reviewing)**. Supplements the generic **`frontend-standards`** skill; where it
differs, **this wins**. When planning, follow it (place files / reuse these components); when reviewing,
flag reuse / DRY violations against these names. Fill it in with your repo's reality (delete the
placeholders). **Delete this file if the repo has no frontend.**

**Base path:** `<frontend/ or src/>` — alias `@/*` → `<root>`. Barrels: `<@/components/ui>`, `<@/components/shared>`.

## Folder structure (where things go)

```
<the repo's real FE folders — app/routes, components/{ui,shared,layout,<feature>}, services, stores,
 lib/{constants,schemas}, hooks, types, utils … + naming (PascalCase.tsx components, etc.)>
```

## Shared components — reuse these, never rebuild them

| Need | Use (from `<@/components/shared>` unless noted) |
|---|---|
| Action / icon button | `<Button>` |
| Form wrapper + fields | `<Form>`, `<TextInput / SelectInput / …>` |
| Card / Table / Modal | `<CustomCard>` · `<DataTable>` · `<CustomModal / ConfirmModal / Drawer>` |
| Loading / empty / header | `<PageLoader / EmptyState / PageHeader>` |

## Tokens — single source of truth

- **Colors:** semantic token classes only (`<bg-card / text-foreground / text-primary / border-border …>`),
  defined once in `<globals.css / theme>`. Never a hex or named palette color.
- **Type / spacing scale:** named utilities only (`<text-xs / text-sm / …>`); never `<text-[Npx]>`.

## Repo-specific DON'Ts (on top of the generic frontend-standards)

- <e.g. API only via `<@/services/*>` — never `<@/lib/api/*>` or raw `fetch`.>
- <e.g. Toasts via `<@/utils/toast>` — never raw `toast`.>
- <e.g. No server data in the client store; no exported interfaces from components/services/stores.>

## Enforcement

- Lint/typecheck/build commands: `<npm run lint / typecheck / build>` (CI catches these).
- Rules enforced by **code review**, not lint: `<one-component-per-file, …>`.
