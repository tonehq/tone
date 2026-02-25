# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
If no `--docs` flag is provided, the skill auto-discovers matching docs in `e2e/docs/`.

```bash
/generate-tests                  # generate tests for the login page (default)
/generate-tests login            # generate tests for the login page
/generate-tests signup           # generate tests for the signup page
/generate-tests home --docs e2e/docs/home.md  # use feature doc for extra coverage
/generate-tests src/app/auth/login/LoginPage.tsx  # use a full path
```

The skill lives at `.claude/skills/generate-tests/SKILL.md`.
Reference docs are at `.claude/skills/generate-tests/references/`.

### Feature docs (`e2e/docs/`)

Feature docs are optional markdown files that describe a page's user stories, acceptance
criteria, edge cases, and business rules. When provided, `/generate-tests` uses them
alongside the component source to ensure all user cases are covered.

| File | Purpose |
|------|---------|
| `e2e/docs/_template.md` | Template for creating new feature docs |
| `e2e/docs/home.md` | Feature doc for the home dashboard page |

To create a feature doc for a new page, copy `_template.md` and fill in the sections.

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

| Page | Test file |
|------|-----------|
| `src/app/auth/login/LoginPage.tsx` | `e2e/auth/login.spec.ts` |
| `src/app/auth/signup/SignupClient.tsx` | `e2e/auth/signup.spec.ts` |
| `src/app/(dashboard)/home/...` | `e2e/dashboard/home.spec.ts` |

**Key conventions:**
- Mock all backend API calls with `page.route('**/path', ...)` — tests must not depend on a live backend
- Use `MOCK_JWT` constant from `test-patterns.md` for auth flows (valid base64 JWT with far-future expiry)
- Prefer `getByRole`, `getByPlaceholder`, `getByText` selectors over CSS classes
- Use `getByPlaceholder` for `TextInput` components (labels use `Typography` without `htmlFor`)
- `CustomButton` with `loading=true` renders text `"Loading..."` and gets `disabled` attribute

### Notification assertions

The `useNotification` hook formats Snackbar messages as `"${title}: ${message}"`:

| Scenario | Expected text |
|----------|--------------|
| Login success | `"Login Successful: Welcome back!"` |
| Login error (API throws) | `"Login Failed: Please try again."` |

Use `page.getByRole('alert')` to find MUI Alert/Snackbar notifications.

### Reference docs

| File | Covers |
|------|--------|
| `references/test-patterns.md` | Config template, API mocking, mock JWT, test structure |
| `references/selectors-guide.md` | MUI TextField, Button, Checkbox, Snackbar selectors |
| `references/assertion-checklist.md` | Required assertions per test category, anti-patterns |

---

## Project Rules

Project-wide rules are defined in `.claude/rules.md`. This includes:

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

All skills (`generate-tests`, `code-review`) automatically log errors to `.claude/error-log.md` when failures occur. The `/error-tracker` skill reads this log and provides:

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
- **This project**: MUI component props that accept callbacks must be stabilised with `useCallback` to avoid re-renders inside MUI's internal `shouldComponentUpdate`

#### 3. Next.js Best Practices
- `'use client'` placed too high — pushes entire subtree into the client bundle
- Raw `<img>` instead of `<Image>` from `next/image`
- Incorrect data fetching pattern for the route type (Server Component vs Client Component)
- Missing API route validation
- **This project**: `ThemeRegistry.tsx` handles MUI + Emotion SSR — do not wrap it in `'use client'` or add a second Emotion cache; all new pages under `(dashboard)/` inherit the sidebar layout automatically

#### 4. SOLID + Architecture
Applies **solid-checklist.md** in full — SRP, OCP, LSP, ISP, DIP, code smells, hook design, component design.

- **This project**: Service functions in `src/services/` must not import Jotai atoms directly (DIP). Atoms call services; services do not know about atoms.
- Components must not call `src/services/` directly — all side effects go through Jotai write atoms.
- `agentFormUtils.ts` owns `AgentFormState` shape, `defaultFormState`, and serialisation — do not duplicate this logic in components.

#### 5. Security
Applies **security-checklist.md** in full — XSS, injection, SSRF, AuthN/AuthZ, secrets, runtime risks, race conditions, data integrity.

- **This project critical paths**:
  - Every new route under `src/app/(dashboard)/` must be covered by the `tone_access_token` check in `src/middleware.ts`. Verify new routes are not excluded accidentally.
  - The Axios instance in `src/utils/axios.ts` injects `tenant_id` and `Authorization` on every request. Do not bypass it by creating a second Axios instance or using `fetch` directly without these headers.
  - Roles and identity must come from the `login_data` cookie (read via `AuthAtom.tsx`) — never from query params or request body fields.
  - Firebase token must never be logged or stored outside of the `tone_access_token` cookie.

#### 6. Performance
Applies **performance-checklist.md** in full across all eight sub-areas:

| Sub-area | Key signals for this project |
|----------|------------------------------|
| React Rendering | Jotai `useAtom` subscriptions — subscribe only to the atom slice needed; avoid subscribing to large atoms just to read one field |
| Next.js & SSR | ThemeRegistry uses Emotion SSR — do not add additional style injection that conflicts; keep Server Components free of `useTheme()` |
| Bundle & Code Splitting | MUI is tree-shaken by default — always import from `@mui/material/Button` not `@mui/material`; use `next/dynamic` for heavy form tabs |
| Network & API | All API calls go through `src/services/` → `src/utils/axios.ts`; verify no N+1 patterns in Jotai write atoms that loop over IDs |
| Core Web Vitals | LCP, INP, CLS — check `next/image` usage, font loading via `next/font`, and that Jotai atom loads do not cause layout shifts |
| Memory Management | Write atoms that start polling or timers must expose a cleanup; `useEffect` in components must clean up axios calls with `AbortController` |
| State Management | Jotai `loadable` is used for async atoms — ensure loading/error/data states are all handled in UI; do not access `.data` without checking `.state` |
| Asset & CSS | MUI `sx` prop with object literals creates new references each render — extract static `sx` objects outside the component or use `styled()` |

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
- Focus not trapped in MUI `Dialog` / `Drawer` (MUI handles this by default — verify it is not disabled)
- **This project**: MUI components are accessible by default — flag any prop that overrides this (e.g., `disablePortal`, `disableEnforceFocus` on dialogs)

#### 9. Dead Code / Removal Candidates
Applies **removal-plan.md** template — safe-to-remove, defer, do-not-remove, unused deps, pre-removal checklist.

- **This project**: Before marking a Jotai atom as dead, verify it is not read via `useAtomValue` in a component that is dynamically imported or conditionally rendered.

---

### Reference checklists

| File | Covers |
|------|--------|
| `references/solid-checklist.md` | SRP, OCP, LSP, ISP, DIP, code smells, hook design, component design signals, refactor heuristics |
| `references/security-checklist.md` | XSS/injection, AuthN/AuthZ, secrets/PII, runtime risks, race conditions, data integrity |
| `references/performance-checklist.md` | React rendering, Next.js SSR, bundle/splitting, network/API, Core Web Vitals, memory, state, assets |
| `references/code-quality-checklist.md` | Error handling, TypeScript quality, boundary conditions, naming, structure, dead code, async, a11y |
| `references/removal-plan.md` | Safe-to-remove, defer, do-not-remove, unused deps, pre-removal checklist, rollback plan |

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
- `src/app/auth/` — public auth pages (login, signup, forgot password, etc.)
- `src/middleware.ts` — enforces auth by checking the `tone_access_token` cookie; unauthenticated requests redirect to `/auth/login?redirect=<path>`

**Page pattern**: Pages under `(dashboard)` are thin wrappers that import and render a component from `src/components/`. All the actual UI logic lives in components.

**State management**: [Jotai](https://jotai.org/). Atoms live in `src/atoms/`:
- `AgentsAtom.tsx` — agent list state with a write-only `fetchAgentList` atom
- `AuthAtom.tsx` — user auth state, logout, and `getCurrentUserAtom` that reads from the `login_data` cookie
- `SettingsAtom.tsx` — organization members and invitations using `jotai/utils` `loadable` for async data with refresh counters

Write-only atoms (e.g., `atom(null, async (_get, set, payload) => {...})`) are the pattern for async actions that update state.

**API layer**: `src/services/` contains service functions that call `src/utils/axios.ts`. The Axios instance:
- Sets base URL from `NEXT_PUBLIC_BACKEND_URL`
- Injects `tenant_id` header (from `org_tenant_id` cookie) and `Authorization: Bearer <token>` (from `tone_access_token` cookie) on every request

**Authentication**: Firebase is used alongside JWT. Auth state is persisted in cookies (`tone_access_token`, `org_tenant_id`, `login_data`). Constants for cookie key names are in `src/constants/index.ts`.

**UI**: Material UI v6 with a custom theme defined in `src/utils/theme.ts`. Primary color is `#8b5cf6` (purple). The theme is provided via `src/components/ThemeRegistry.tsx` which handles MUI + Emotion SSR setup for Next.js. Use `useTheme()` to access theme values in components.

**Agent form**: The create/edit agent flow is a multi-tab form (`GeneralTab`, `VoiceTab`, `CallConfigurationTab`) plus a `PromptPage`. Form state uses `AgentFormState` from `src/components/agents/agent-form/agentFormUtils.ts`, which also exports `defaultFormState` and `formStateToUpsertPayload` for serializing to the API.

---

## Code Style

- **Quotes**: single quotes (`'`)
- **Types**: use `interface` over `type` for object shapes (`@typescript-eslint/consistent-type-definitions: interface`)
- **Trailing commas**: always on multiline arrays/objects/functions
- **Print width**: 100 characters
- **Tab width**: 2 spaces
- Unused variables prefixed with `_` are allowed and suppress warnings
