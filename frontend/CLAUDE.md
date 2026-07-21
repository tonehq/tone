# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT: Read RULES.md First

**Before reading any source files, always check `docs/RULES.md` for the feature-to-documentation mapping.** The `docs/` folder contains comprehensive documentation (~2,500+ lines) covering the codebase. Reading the relevant doc first reduces token usage by ~90%.

### Quick Reference

| Feature Area | Documentation File |
|-------------|-------------------|
| Auth (login, signup, password reset, tokens) | `docs/AUTH_FLOW_DOCUMENTATION.md` |
| Settings (API keys, members, integrations) | `docs/features/settings-page.md` |
| Shared UI Components (CustomTable, TextInput, etc.) | `docs/shared-components.md` |
| Design System (theme, colors, spacing) | `docs/design.md` |

### Workflow

1. **Every request:** Read `docs/RULES.md` → identify relevant doc → read doc → then read only the source file being edited
2. **After code changes:** If behavior changed, update the relevant doc (see Rule 3 in `docs/RULES.md`)
3. **Cross-feature changes:** Check the cross-feature table in `docs/RULES.md` Rule 6

### Documentation Generation

Use `/generate-feature-docs` skill to create comprehensive feature docs. See `docs/RULES.md` for the complete mapping and coverage gaps. Always update docs after behavioral code changes.

---

## Commands

```bash
yarn dev              # Start dev server with Turbopack at localhost:3000
yarn build            # Production build (Turbopack)
yarn lint             # Run ESLint
yarn lint:fix         # Run ESLint with auto-fix
yarn format           # Run Prettier on all files
yarn test:e2e         # Run Playwright e2e tests (requires dev server)
yarn test:e2e:ui      # Open Playwright UI mode
yarn test:e2e:headed  # Run tests in a visible browser window
yarn test:e2e:debug   # Run tests in debug mode
```

ESLint and Prettier run automatically on staged files via husky pre-commit hooks.

### First-time Playwright setup

After cloning or pulling this branch for the first time:

```bash
yarn install
yarn playwright install chromium
```

---

## Playwright E2E Testing

### `/generate-tests` — create new spec files

Use when a page has **no existing spec file** and you need to write one from scratch.
Reads the component source, generates tests, writes the `.spec.ts` file, and runs it.

Optionally accepts a **feature doc** (`--docs`) for more comprehensive test coverage.
If no `--docs` flag is provided, the skill auto-discovers matching docs in `e2e/ux_flow_docs/`.

```bash
/generate-tests                  # generate tests for the login page (default)
/generate-tests login            # generate tests for the login page
/generate-tests signup           # generate tests for the signup page
/generate-tests home --docs e2e/ux_flow_docs/home.md  # use feature doc for extra coverage
/generate-tests src/app/auth/login/LoginPage.tsx  # use a full path
```

The skill lives at `.claude/skills/generate-tests/SKILL.md`.
Reference docs are at `.claude/skills/generate-tests/references/`.

### `/generate-feature-docs` — create feature documentation

Use when a page has **no existing feature doc** and you need to create one for test generation.
Reads the component source, traces imports (services, atoms, types), and generates a comprehensive
feature doc following the `_template.md` structure.

```bash
/generate-feature-docs settings
/generate-feature-docs agents
/generate-feature-docs login
/generate-feature-docs settings --routes /settings,/settings/members
```

The skill lives at `.claude/skills/generate-feature-docs/SKILL.md`.
Reference docs are at `.claude/skills/generate-feature-docs/references/`.

### Feature docs (`e2e/ux_flow_docs/`)

Feature docs are markdown files that describe a page's user stories, acceptance
criteria, edge cases, and business rules. When provided, `/generate-tests` uses them
alongside the component source to ensure all user cases are covered.

Use `/generate-feature-docs <page-name>` to generate a new feature doc automatically,
or copy `_template.md` and fill in the sections manually.

| File                    | Purpose                                 |
| ----------------------- | --------------------------------------- |
| `e2e/ux_flow_docs/_template.md` | Template for creating new feature docs  |
| `e2e/ux_flow_docs/home.md`      | Feature doc for the home dashboard page |
| `e2e/ux_flow_docs/agents.md`    | Feature doc for the agents pages (CRUD) |

### Running tests

Run existing spec files using Playwright CLI commands directly:

```bash
# Run the full e2e suite
yarn playwright test --reporter=list

# Run a specific spec file
yarn playwright test e2e/auth/login.spec.ts --reporter=list
yarn playwright test e2e/auth/signup.spec.ts --reporter=list
yarn playwright test e2e/dashboard/home.spec.ts --reporter=list

# Run in headed mode (visible browser)
yarn playwright test e2e/auth/login.spec.ts --headed --reporter=list

# Run in debug mode (Playwright Inspector)
yarn playwright test e2e/auth/login.spec.ts --debug

# Run a single test by name
yarn playwright test --grep "shows the login heading" --reporter=list

# List tests without running them
yarn playwright test e2e/auth/login.spec.ts --list
```

**Prerequisites**: The dev server must be running (`yarn dev`) before executing tests.

### Configuration

- **Config file**: `playwright.config.ts` (project root of `frontend/`)
- **Test directory**: `e2e/`
- **Browser**: Chromium (Desktop Chrome)
- **Base URL**: `http://localhost:3000` (override with `PLAYWRIGHT_BASE_URL` env var)
- **Dev server**: Auto-started by `webServer` config; reuses existing server in dev mode

### Writing tests

Tests live in `e2e/<route-group>/<page-name>.spec.ts`, mirroring the `src/app/` structure:

| Page                                   | Test file                    |
| -------------------------------------- | ---------------------------- |
| `src/app/auth/login/LoginPage.tsx`     | `e2e/auth/login.spec.ts`     |
| `src/app/auth/signup/SignupClient.tsx` | `e2e/auth/signup.spec.ts`    |
| `src/app/(dashboard)/home/...`         | `e2e/dashboard/home.spec.ts` |

**Key conventions:**

- Mock all backend API calls with `page.route('**/path', ...)` — tests must not depend on a live backend
- Use `MOCK_JWT` constant from `test-patterns.md` for auth flows (valid base64 JWT with far-future expiry)
- Prefer `getByRole`, `getByPlaceholder`, `getByText` selectors over CSS classes
- Use `getByPlaceholder` for `TextInput` components (labels use `Typography` without `htmlFor`)
- `CustomButton` with `loading=true` renders text `"Loading..."` and gets `disabled` attribute

### Notification assertions

Notifications use Sonner toast (`showToast` from `@/utils/toast`). Title and description render in separate elements inside the toast:

| Scenario                 | Title              | Description         |
| ------------------------ | ------------------ | ------------------- |
| Login success            | `Login Successful` | `Welcome back!`     |
| Login error (API throws) | `Login Failed`     | `Please try again.` |

Use `page.locator('[data-sonner-toast]')` to find Sonner toast notifications.

### API error handling

All API `catch` blocks must use `handleApiError` from `@/utils/helpers`:

```typescript
import { handleApiError } from '@/utils/helpers';

try {
  await someApiCall();
} catch (error) {
  handleApiError(error);
}
```

`handleApiError(error)` extracts `error.response.data.detail` from Axios errors and shows an error toast with a default title and fallback message. Do NOT duplicate inline error extraction logic.

### Reference docs

| File                                | Covers                                                 |
| ----------------------------------- | ------------------------------------------------------ |
| `references/test-patterns.md`       | Config template, API mocking, mock JWT, test structure |
| `references/selectors-guide.md`     | TextField, Button, Checkbox, Sonner toast selectors    |
| `references/assertion-checklist.md` | Required assertions per test category, anti-patterns   |

---

## Contacts Directories — reusable components/hooks (reuse, don't re-implement)

Import targets (all under `src/`):
- **`usePaginatedList`** (`lib/api/usePaginatedList.ts`) — generic TanStack Query hook for `POST /…/list` (search/sort/paginate). **`queryKeys`** (`lib/api/queryKeys.ts`) — typed query-key factory for all contacts queries/invalidations.
- **`buildContactFormSchema`** (`components/contacts/shared/buildContactFormSchema.ts`) — `schema_fields` → Zod schema at runtime. **`SchemaDrivenContactForm`** (same dir) — renders inputs from `schema_fields` (RHF+Zod). Used by Add + Edit contact.
- **`ContactsTable`** (`components/contacts/shared/ContactsTable.tsx`) — wraps `CustomTable` (search/filter/sort/paginate). Directory General + Agent Contacts + Assign picker.
- **`SchemaFieldsEditor`** (`components/contacts/shared/SchemaFieldsEditor.tsx`) — field CRUD editor.
- **`UploadContactsModal`** (`components/contacts/shared/`) — the single "Upload Contacts" (local CSV / `.xlsx`) modal: mapping-schema + file + optional agent-context directory override → `POST /contact-syncs`; optional `agentId` auto-assigns on completion. Mounted on the directory General view, the Agent Contacts tab, and `AssignContactsModal`'s "Upload a file instead".
- **`ContactFileInput`** + **`SyncProgressPanel`** + **`SampleDownloadMenu`** (`components/contacts/shared/`) — the file picker (client-side extension validation + sample slot), the polled import-progress phase (counts/warnings/errors + Retry/Done, fires `onTerminal` once), and the CSV/Excel sample-download affordance. Reused by `UploadContactsModal` AND the dormant `SyncContactsModal` (no duplication). **Samples are generated SERVER-SIDE** (`schemasApi.downloadSample` → `GET /contact-schemas/{id}/sample?format=`); the browser never builds sample content — do NOT re-add a client-side `buildSample*` / SheetJS generator.
- **`TimezoneSelect`** (`components/shared`) — the single searchable IANA timezone dropdown (options from `getTimeZones()`); reused by `DateTimePicker`, the org scheduling-timezone setting, and date/datetime schema fields. **`getTimeZoneAbbreviation(tz, at?)`** (`@/utils/date`) — `EDT`-style zone abbreviation for the schedule-time label.
- **Agent `schedule` section** (`agent-form/sectionNav.ts` + `AgentSectionBody.tsx` → `ScheduleStep`) — the outbound-gated, edit-only agent Schedule tab renders `ScheduledCallsPage` scoped by `agentId` (list filtered + create modal agent-locked; Agent column hidden). There is NO global `/scheduled-calls` route anymore.
- **`SyncContactsModal`** — DORMANT (no page mounts it); reserved for a future third-party (`rest`) datasource sync. Refactored onto `ContactFileInput` + `SyncProgressPanel`. Use `UploadContactsModal` for local-file uploads.
- **`useSyncStatusPolling`** + **`SyncStatusChip`** (`components/contacts/shared/`) — poll a sync to terminal; status chip.
- **`AssignContactsModal`** + **`DirectoryContactTree`** + **`useDirectoryContactTreeSelection`** (`components/contacts/shared/`) — tri-state directory→contacts multi-select; emits `{directory_ids, contact_ids}`.
- **`ConfirmDeleteModal`** (`components/contacts/shared/ConfirmDeleteModal.tsx`) — impact-summary + confirm wrapper over `CustomModal`.
- API clients: `lib/api/{contactDirectories,contactDatasources,contactSchemas,contactSyncs,agentContacts,contacts}.ts`.

## Project Rules

Project-wide rules are defined in `.claude/rules.md`. This includes:

- **Reuse & the service layer (single source of truth)** — one shared implementation per behavior; all HTTP through `src/services` / `src/lib/api` hooks (never raw `fetch`/`axios` in a component); components stay thin; code review flags duplication (rule §13)
- **Skill error tracking** — How skills log errors, categories, severity levels, and the log format
- **Error resolution workflow** — How to diagnose, fix, and update the error log
- **Skill execution rules** — Pre-execution checks, error handling, output standards
- **Test conventions** — Tab reuse, route cleanup, auth cookies, selector disambiguation

All skills must follow these rules. Read `.claude/rules.md` before modifying any skill.

---

## Error Tracking

### How to invoke

```bash
/error-tracker              # show full summary
/error-tracker summary      # same as above
/error-tracker search timeout   # search for timeout-related errors
/error-tracker recent 5     # show last 5 entries
/error-tracker clear-resolved   # remove resolved entries
```

The skill lives at `.claude/skills/error-tracker/SKILL.md`.
The error log is at `.claude/error-log.md`.

### How it works

All skills (`generate-tests`, `code-review`, `generate-feature-docs`) automatically log errors to `.claude/error-log.md` when failures occur. The `/error-tracker` skill reads this log and provides:

- **Summary** — Error counts by severity, category, and skill
- **Recurring patterns** — Same category + file appearing 2+ times
- **Recommendations** — Preventive actions based on error history

### Error flow

```
Skill runs → Failure detected → Entry appended to .claude/error-log.md
                                              ↓
                             /error-tracker reads log → Summary + Patterns
```

---

## Code Review

### How to invoke

```bash
/code-review          # compare against main (default)
/code-review dev      # compare against dev branch
```

The skill lives at `.claude/skills/code-review/SKILL.md`.
Reference checklists are at `.claude/skills/code-review/references/`.

### What is reviewed (9 sections, in order)

Every `/code-review` run works through all nine sections below. No section is skipped.

---

#### 1. Correctness

- TypeScript type errors, incorrect narrowing, unsafe `as` casts, missing `interface` fields
- Null / undefined access without guard — `user.profile.name`, `items[0].id`
- Async functions without `try/catch`, unhandled promise rejections
- Direct state mutation (`state.items.push(x)` — React does not detect this)
- **This project**: Jotai write atoms must always handle errors and never leave atoms in partial state

#### 2. React Best Practices

- Rules of hooks — conditional hooks, hooks in loops, hooks in callbacks
- Missing or incorrect `useEffect` dependency arrays — stale closures, over-firing
- Missing list `key` props
- `useMemo` / `useCallback` / `React.memo` misuse or missing
- Prop drilling through 3+ levels without context or composition
- **This project**: Component props that accept callbacks should be stabilised with `useCallback` to avoid unnecessary re-renders

#### 3. Next.js Best Practices

- `'use client'` placed too high — pushes entire subtree into the client bundle
- Raw `<img>` instead of `<Image>` from `next/image`
- Incorrect data fetching pattern for the route type (Server Component vs Client Component)
- Missing API route validation
- **This project**: All new pages under `(dashboard)/` inherit the sidebar layout automatically

#### 4. SOLID + Architecture

Applies **solid-checklist.md** in full — SRP, OCP, LSP, ISP, DIP, code smells, hook design, component design.

- **Single source of truth (reuse first):** the same functionality has ONE implementation that every caller uses — a shared component (`src/components/shared`), hook (`src/hooks`), util (`src/lib`/`src/utils`), service (`src/services` / `src/lib/api`), or Jotai atom. Flag any PR that re-implements or copy-pastes behavior a shared piece already provides — call the shared function, don't duplicate it. When new logic will be needed from more than one place, factor it out from the start (extract by responsibility, not shape; rule of three).
- **This project**: Service functions in `src/services/` must not import Jotai atoms directly (DIP). Atoms call services; services do not know about atoms.
- Components must not call `src/services/` directly — all side effects go through Jotai write atoms; all HTTP goes through the service / `src/lib/api` layer (never raw `fetch`/`axios` in a component).
- `agentFormUtils.ts` owns `AgentFormState` shape, `defaultFormState`, and serialisation — do not duplicate this logic in components.

#### 5. Security

Applies **security-checklist.md** in full — XSS, injection, SSRF, AuthN/AuthZ, secrets, runtime risks, race conditions, data integrity.

- **This project critical paths**:
  - Every new route under `src/app/(dashboard)/` must be covered by the `access_token` httpOnly-cookie presence check in `src/middleware.ts`. Verify new routes are not excluded accidentally by the matcher.
  - The Axios instance in `src/utils/axios.ts` uses `withCredentials: true` so the httpOnly auth cookies are sent automatically, and injects the `tenant_id` hint header. Do not bypass it by creating a second Axios instance or using `fetch` directly without `credentials: 'include'`.
  - Roles and identity must come from the `login_data` payload in localStorage (readable UI state) or the `/auth/me` API — never decoded from the token (it's an httpOnly cookie JS cannot read) and never from query params or request body fields.
  - The access/refresh JWTs live ONLY in httpOnly cookies — never store them in localStorage/sessionStorage or log them.

#### 6. Performance

Applies **performance-checklist.md** in full across all eight sub-areas:

| Sub-area                | Key signals for this project                                                                                                                       |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| React Rendering         | Jotai `useAtom` subscriptions — subscribe only to the atom slice needed; avoid subscribing to large atoms just to read one field                   |
| Next.js & SSR           | Keep Server Components free of client-only hooks; use `'use client'` at the lowest level needed                                                    |
| Bundle & Code Splitting | Prefer shadcn/Tailwind primitives over heavy component libraries; use `next/dynamic` for heavy form tabs                                           |
| Network & API           | All API calls go through `src/services/` → `src/utils/axios.ts`; verify no N+1 patterns in Jotai write atoms that loop over IDs                    |
| Core Web Vitals         | LCP, INP, CLS — check `next/image` usage, font loading via `next/font`, and that Jotai atom loads do not cause layout shifts                       |
| Memory Management       | Write atoms that start polling or timers must expose a cleanup; `useEffect` in components must clean up axios calls with `AbortController`         |
| State Management        | Jotai `loadable` is used for async atoms — ensure loading/error/data states are all handled in UI; do not access `.data` without checking `.state` |
| Asset & CSS             | Prefer Tailwind utility classes over inline style objects; extract shared variants with `cva` or shared component presets                          |

#### 7. Code Quality

Applies **code-quality-checklist.md** in full — error handling, TypeScript quality, boundary conditions, performance patterns, naming, structure, dead code, async/concurrency, accessibility hooks.

- **This project style rules** (enforced by ESLint + Prettier):
  - Single quotes, trailing commas, 100-char print width, 2-space indent
  - `interface` over `type` for object shapes
  - Unused variables prefixed with `_` are allowed

#### 8. Accessibility (mandatory — never skip)

- Interactive `div`/`span` with `onClick` → use `<button>` or add `role` + keyboard handler
- `<img>` without `alt`; form inputs without `<label>` or `aria-label`
- Heading hierarchy skipped; missing `aria-live` on toasts / alerts
- Focus not trapped in dialog/drawer components — Radix primitives (used by shadcn) handle this by default; verify any custom modal traps focus and restores it on close
- **This project**: prefer Radix/shadcn primitives for any new dialog, drawer, popover, or menu — they ship correct ARIA, keyboard, and focus behavior out of the box

#### 9. Dead Code / Removal Candidates

Applies **removal-plan.md** template — safe-to-remove, defer, do-not-remove, unused deps, pre-removal checklist.

- **This project**: Before marking a Jotai atom as dead, verify it is not read via `useAtomValue` in a component that is dynamically imported or conditionally rendered.

---

### Reference checklists

| File                                   | Covers                                                                                              |
| -------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `references/solid-checklist.md`        | SRP, OCP, LSP, ISP, DIP, code smells, hook design, component design signals, refactor heuristics    |
| `references/security-checklist.md`     | XSS/injection, AuthN/AuthZ, secrets/PII, runtime risks, race conditions, data integrity             |
| `references/performance-checklist.md`  | React rendering, Next.js SSR, bundle/splitting, network/API, Core Web Vitals, memory, state, assets |
| `references/code-quality-checklist.md` | Error handling, TypeScript quality, boundary conditions, naming, structure, dead code, async, a11y  |
| `references/removal-plan.md`           | Safe-to-remove, defer, do-not-remove, unused deps, pre-removal checklist, rollback plan             |

---

### Review output structure

Every review produces this report:

```
# Code Review Summary
Base branch · Current branch · Files reviewed · Overall: APPROVE / REQUEST_CHANGES / COMMENT

## Critical Issues       ← security · crash · data loss · 🔴 perf regression
## High Priority Issues  ← SOLID · hook misuse · SSR mistakes · 🟠 perf
## Performance Issues    ← grouped by all 8 sub-areas + Performance Summary
## Medium Priority Issues← maintainability · 🟡 perf · error handling
## Low Priority          ← naming · style · 🔵 optimisations
## Removal / Iteration Plan
## Positive Observations
```

After findings are presented, Claude will ask how to proceed — **no fixes are applied until explicitly chosen**.

---

## Environment

The app requires `NEXT_PUBLIC_BACKEND_URL` to be set (see `src/urls.ts`). This is injected into the Axios base URL for all API calls.

---

## Architecture

**Framework**: Next.js 15 App Router with React 19 and TypeScript. Both dev and build use Turbopack.

**Routing**:

- `src/app/page.tsx` — redirects `/` to `/home`
- `src/app/(dashboard)/` — route group for all authenticated pages (agents, home, settings, phone-numbers); shares a sidebar layout via `(dashboard)/layout.tsx`
- `src/app/auth/` — public auth pages (login, signup, forgot password, reset password). All auth forms use react-hook-form + Zod for validation (see below).
- `src/middleware.ts` — server-side auth guard: checks for the `access_token` httpOnly cookie (readable by middleware, not by browser JS); unauthenticated requests redirect to `/login?next=<path>`

**Page pattern**: Pages under `(dashboard)` are thin wrappers that import and render a component from `src/components/`. All the actual UI logic lives in components.

**State management**: [Jotai](https://jotai.org/). Atoms live in `src/atoms/`:

- `AgentsAtom.tsx` — agent list state with a write-only `fetchAgentList` atom
- `AuthAtom.tsx` — user auth state, logout, and `getCurrentUserAtom` that reads from the `login_data` payload in localStorage
- `SettingsAtom.tsx` — organization members and invitations using `jotai/utils` `loadable` for async data with refresh counters

Write-only atoms (e.g., `atom(null, async (_get, set, payload) => {...})`) are the pattern for async actions that update state.

**API layer**: `src/services/` contains service functions that call `src/utils/axios.ts`. The Axios instance:

- Sets base URL from `NEXT_PUBLIC_BACKEND_URL` (or a relative `/api/v1` when `NEXT_PUBLIC_USE_API_PROXY=true` routes through the Next.js dev proxy — see `next.config.ts` `rewrites`)
- Uses `withCredentials: true` so the browser attaches the httpOnly `access_token` / `refresh_token` cookies automatically; injects only the non-sensitive `tenant_id` hint header (from `active_org_id` in localStorage). On a 401 it silently calls `/auth/refresh` (cookie-based) once and retries.

**Authentication**: JWT access + refresh tokens stored in **httpOnly cookies** (set/cleared by the backend on login / refresh / logout / org-switch), so JS never touches them and XSS can't exfiltrate a session. The readable `login_data` payload + `active_org_id` in localStorage are non-sensitive UI state only. Route protection is server-side in `src/middleware.ts`. Org switching goes through `POST /auth/switch_organization`, which re-mints both cookies with the (membership-verified) new org. Constants for storage keys are in `src/constants/index.ts`. (No Firebase.)

**UI**: shadcn/ui primitives in `src/components/ui/` styled with Tailwind v4 and theme tokens from `src/app/globals.css` (CSS variables for color, radius, etc.). The root font is **Geist Sans** (loaded via `next/font` in `src/app/layout.tsx`, exposed as `--font-geist-sans` and bound to Tailwind's `font-sans`); `font-mono` resolves to Geist Mono. Dark mode is handled by `next-themes`. Use **lucide-react** for icons (or `src/components/icons/` for brand marks). The codebase is MUI-free — do not introduce `@mui/*` or `@emotion/*` packages.

**Shared components**: `src/components/shared/` holds reusable form/UI pieces (TextInput, CustomButton, Form, CheckboxField, RadioGroupField, SelectInput, TextAreaField, CustomLink). Each form component is **unified** — passing a `control` prop activates RHF `Controller` integration automatically (no separate `Form*` wrapper needed). Component prop types are defined in `src/types/components.ts`. To understand or use them without reading each file, read **`docs/shared-components.md`** (single reference, lower token usage). When adding or changing a shared component, update that doc.

**Date/time input (mandatory)**: Use the shared `DateTimePicker` (a single instant → emits a UTC ISO string) or `DateRangePicker` (a range) for ALL date/time selection. Both are timezone-aware and share the `combineToIso`/`splitFromIso`/`getBrowserTimeZone` helpers in `@/utils/date`. Do NOT use native `<input type="date">` / `<input type="datetime-local">` or introduce another calendar library in app/feature code.

**Form validation**: Two patterns are used for form validation:

1. **Auth forms** (login, signup, forgot password, reset password) — use `react-hook-form` with `zodResolver` and Zod schemas from `src/schemas/auth.ts`. Each form uses `useForm<SchemaType>` + `TextInput` (with `control` prop) for inline error display. Dependencies: `zod`, `@hookform/resolvers`.
2. **Agent forms** — use `react-hook-form` with inline `rules` prop validation on `TextInput` / `SelectInput` fields (with `control` prop). No Zod schemas.

**Important**: When using `TextInput` with `control`, do NOT also pass `error` to a parent `FormRow` — the component already renders `fieldState.error.message` as `helperText`, causing duplicate error messages.

**Agent form**: The create/edit agent flow is a multi-tab form (`GeneralTab`, `VoiceTab`, `CallConfigurationTab`) plus a `PromptPage`. Form state uses `AgentFormState` from `src/components/agents/agent-form/agentFormUtils.ts`, which also exports `defaultFormState` and `formStateToUpsertPayload` for serializing to the API. The form is wrapped by `AgentFormPage.tsx` which handles loading agent data for edit mode and provides the `FormProvider` context.

**Key files**:

| File                                                         | Purpose                                                          |
| ------------------------------------------------------------ | ---------------------------------------------------------------- |
| `src/schemas/auth.ts`                                        | Zod schemas + inferred types for all auth forms                  |
| `src/components/agents/agent-form/agentFormUtils.ts`         | `AgentFormState`, `defaultFormState`, `formStateToUpsertPayload` |
| `src/components/agents/AgentFormPage.tsx`                    | Agent create/edit page wrapper with `FormProvider`               |
| `src/components/agents/agent-form/DynamicProviderFields.tsx` | Renders provider-specific config fields dynamically              |

---

## Code Style

- **Quotes**: single quotes (`'`)
- **Types**: use `interface` over `type` for object shapes (`@typescript-eslint/consistent-type-definitions: interface`)
- **Trailing commas**: always on multiline arrays/objects/functions
- **Print width**: 100 characters
- **Tab width**: 2 spaces
- Unused variables prefixed with `_` are allowed and suppress warnings
- **Cursor: pointer for clickables (mandatory)**: every clickable/interactive element shows a pointer cursor; disabled controls show `not-allowed`. A global base rule in `src/app/globals.css` covers `button`, `[role="button"]`, `a[href]`, `label[for]`, `summary`, select triggers, and common ARIA roles — so standard controls need nothing extra. For a non-standard clickable (`div`/`span` with `onClick`), prefer a real `<button>`/`CustomButton`; otherwise add `cursor-pointer` plus a `role` + keyboard handler. Never leave a clickable element on the default arrow.
