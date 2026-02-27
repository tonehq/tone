---
name: generate-tests
description: Generates a new Playwright e2e spec file by reading a page component's source code, then runs it. Use when a page has NO existing spec file and you need to create one from scratch.
argument-hint: '[target] [--docs path/to/feature-doc.md]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
license: proprietary
compatibility: Requires Node.js, yarn, and Playwright. Next.js dev server must be reachable at localhost:3000.
metadata:
  author: tonehq
  version: '1.1.0'
  category: testing
  tags: playwright, e2e, testing, react, nextjs, mui
---

You are a Senior QA Engineer and Frontend Automation Specialist for a React + Next.js (App Router) codebase.
Your job is to produce high-quality, maintainable Playwright e2e tests that cover real user interactions.

---

## Step 1 — Resolve the target and feature docs

```
FULL_ARGS=$ARGUMENTS
```

### 1a. Parse `--docs` flag (optional)

If `$ARGUMENTS` contains `--docs <path>`:

- Extract the docs path and set `FEATURE_DOCS=<path>`
- Remove `--docs <path>` from arguments, leaving the target

Examples:

```
/generate-tests home --docs e2e/docs/home.md
  → TARGET=home, FEATURE_DOCS=e2e/docs/home.md

/generate-tests home
  → TARGET=home, FEATURE_DOCS=<auto-discover>
```

### 1b. Resolve the target component

- If target is empty, default to `src/app/auth/login/LoginPage.tsx`
- If target is a route like `/auth/login`, find the matching page file under `src/app/`
- If target is a short name like `login` or `signup`, search for the component:
  ```bash
  find src/app -iname "*$TARGET*" | head -20
  ```
- If target is already a file path, use it directly

### 1c. Auto-discover feature docs (when `--docs` is not provided)

If no explicit `--docs` was given, search for a matching feature doc:

```bash
# Convention: e2e/docs/<page-name>.md
find e2e/docs -iname "*<target-name>*.md" 2>/dev/null | head -3
```

- If a matching doc is found, set `FEATURE_DOCS=<path>` and inform the user:
  > Found feature doc: `<path>` — using it for test generation
- If no doc is found, proceed without feature docs (component source only)

---

## Step 2 — Read reference checklists

Read ALL three reference files before generating any tests. Do not skip any.

- `.claude/skills/generate-tests/references/test-patterns.md`
- `.claude/skills/generate-tests/references/selectors-guide.md`
- `.claude/skills/generate-tests/references/assertion-checklist.md`

### 2a. Read feature docs (if available)

If `FEATURE_DOCS` is set, read the feature doc file in full. Extract:

1. **User stories / acceptance criteria** — what the user expects to do on this page
2. **Edge cases** — scenarios the component code alone might not reveal
3. **Business rules** — validation logic, permissions, conditional UI
4. **Integration points** — API contracts, data dependencies

These requirements are used **in addition to** the component analysis in Step 3.
Tests must cover both what the code does AND what the feature doc says it should do.
If the feature doc mentions a scenario not visible in the code, still generate a test
for it — the test will fail, surfacing a gap between the spec and the implementation.

---

## Step 3 — Analyse the component (+ feature docs)

Read the resolved component file(s) in full. Also read any closely related files:

- Shared sub-components it imports (form, inputs, buttons, notifications)
- The auth/API service it calls
- Related utility files (notification hooks, form helpers)

From your analysis, capture:

1. **Route** — what URL does this page live at?
2. **Elements** — every interactive or visible element (inputs, buttons, links, checkboxes, text)
3. **User flows** — what can a user DO on this page (submit form, click link, toggle visibility)?
4. **API calls** — what backend endpoints does it hit, and what does it do with the response?
5. **State changes** — loading states, error states, success states
6. **Navigation** — where does the page redirect on success/failure?
7. **Accessibility hooks** — aria-labels, roles, placeholder text

### Cross-reference with feature docs (if available)

If a feature doc was loaded in Step 2a, cross-reference its requirements against the
component analysis above. Build a **coverage matrix**:

| Requirement (from feature doc)    | Found in code? | Test plan                                  |
| --------------------------------- | -------------- | ------------------------------------------ |
| User story / acceptance criterion | Yes / No       | Test name or "GAP — generate failing test" |

- **Found in code**: Generate tests that verify the implementation matches the spec
- **NOT found in code**: Still generate the test — it will fail, surfacing the gap between
  the feature doc and the implementation. Mark with a comment: `// GAP: feature doc requires X but component does not implement it`

This ensures tests cover both what the code does AND what the feature doc says it should do.

---

## Step 4 — Check Playwright setup

```bash
# Check if @playwright/test is already installed
cat package.json | grep playwright
```

If `@playwright/test` is **not** in devDependencies:

1. Add it to `package.json` devDependencies: `"@playwright/test": "^1.50.0"`
2. Add test scripts to `package.json` scripts:
   ```json
   "test:e2e": "playwright test",
   "test:e2e:ui": "playwright test --ui",
   "test:e2e:headed": "playwright test --headed",
   "test:e2e:debug": "playwright test --debug"
   ```
3. Tell the user to run: `yarn install && yarn playwright install chromium`

If `playwright.config.ts` does **not** exist, create it using the template in `test-patterns.md`.

---

## Step 5 — Determine the output file path

Map the target page to its test file location:

| Page file                              | Test file                          |
| -------------------------------------- | ---------------------------------- |
| `src/app/auth/login/LoginPage.tsx`     | `e2e/auth/login.spec.ts`           |
| `src/app/auth/signup/SignupClient.tsx` | `e2e/auth/signup.spec.ts`          |
| `src/app/(dashboard)/home/...`         | `e2e/dashboard/home.spec.ts`       |
| `src/app/auth/forgotpassword/...`      | `e2e/auth/forgot-password.spec.ts` |

General rule: strip `src/app/` prefix, replace inner path with kebab-case, append `.spec.ts`.

If the test file already exists, **update** it (add missing test cases, do not duplicate existing ones).

---

## Step 6 — Generate the test file

Apply **all three reference checklists** to produce tests that cover:

### Mandatory test groups (never skip):

1. **Page Rendering** — every visible element is present on load
2. **Navigation** — all links navigate to the correct route
3. **Form Validation** — browser HTML5 constraints, client-side rules, required fields
4. **User Flows** — the main happy path (success scenario) and key failure paths
5. **CRUD: use real API** — for create, read, update, delete flows do **not** mock the corresponding API; use the real backend so data is persisted and the full stack is validated. See `test-patterns.md` (CRUD operations). Use `page.route()` only for error paths, loading states, or edge cases (empty list, 4xx/5xx).
6. **Loading / Async State** — loading indicators, disabled buttons during async ops
7. **Error States** — network errors, API errors (4xx, 5xx), empty/invalid responses (mock these with `page.route()`)
8. **Accessibility** — keyboard navigation, aria roles, focus management

### Code standards:

- Use the worker-context + single-tab fixture from `test-patterns.md` — one browser window per worker, one tab reused across all tests. State isolation is handled by `beforeEach` hooks (soft navigation, `page.unrouteAll()`). This eliminates tab churn in `--headed` mode. Only create a fresh tab per test if tests have conflicting browser-level state that cannot be reset in `beforeEach`
- **Dashboard pages (login once per worker)**: Call `loginViaUI` from `e2e/helpers/auth.ts` inside the **worker-scoped fixture**, NOT in `beforeEach`. This logs in once through the actual login page UI against the real backend. Auth cookies persist across all tests in the worker. Do NOT manually inject cookies with `addCookies()`. See `test-patterns.md` for full usage.
- **Soft navigation (dashboard pages)**: Use an `ensureOnPage(page, '/route')` helper in `beforeEach` instead of `page.goto()`. It skips navigation when already on the target page, uses sidebar links (`a[href="/route"]`) for client-side routing from other dashboard pages, and only falls back to hard `page.goto()` when outside the dashboard layout.
- **Soft navigation (auth pages)**: Use an `ensureOnPage(page)` helper that skips when already on the target URL, falls back to `page.goto()` otherwise. No form clearing in the helper — `fill('')` causes React re-renders and element detachment. Test groups that need clean form state (Form Validation, Auth Flow) add a nested `beforeEach` with `page.goto()`. See `test-patterns.md` for the full pattern.
- **Cookie save/restore**: Tests that clear cookies (e.g., Auth Redirect) must save cookies in a nested `beforeEach` and restore them in `afterEach` so subsequent tests stay authenticated.
- **Cookie cleanup (auth pages)**: Auth flow tests that mock the login API with 200 trigger `setToken()` which sets real cookies. Add `afterEach` with `clearCookies()` in these groups.
- **Loading state mocks**: Use `route.abort()` not `route.fulfill()` for delayed mocks that test loading state. This prevents the success handler from triggering navigation after the test ends.
- **Auth pages**: Do NOT use `loginViaUI` — auth pages (login, signup, etc.) are public and test the login flow itself
- Group tests with `test.describe()` blocks matching the groups above
- Prefer semantic selectors: `getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`
- Tests authenticate against the real backend — the dev server and backend must be running
- Import `loginViaUI` and `TEST_EMAIL` from `e2e/helpers/auth.ts`
- Add page-specific `MOCK_*` constants at the top of the file for non-auth test data
- Use TypeScript throughout; no `any` unless unavoidable
- Each test name must start with an action verb: "shows", "navigates", "submits", "displays", "allows", "prevents", "redirects"
- Apply the **selectors-guide.md** for MUI component selectors
- Apply the **assertion-checklist.md** to ensure each test has the right assertion type

### Selector priority order (most preferred first):

1. `getByRole` with accessible name
2. `getByLabel`
3. `getByPlaceholder`
4. `getByText`
5. `locator('[data-testid="..."]')` — only if no semantic option exists

---

## Step 7 — Write the test file

Write the complete test file to disk. Ensure:

- Valid TypeScript syntax
- No import errors (correct `@playwright/test` import)
- Correct file path (matches Step 5)
- All `page.route()` mocks use `**/path` to be backend-URL-agnostic

---

## Step 8 — Run the tests

```bash
# Ensure the dev server is reachable first
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/auth/login
```

If the server responds with 200:

```bash
yarn playwright test <test-file-path> --reporter=list
```

If the server is NOT running:

- Do NOT start it automatically (it takes too long to be useful here)
- Inform the user: "Start the dev server with `yarn dev` in a separate terminal, then re-run `/generate-tests`"
- Still write the test file so it is ready to run

---

## Step 9 — Log errors to the error tracker

If any tests failed after running, append each failure to `.claude/error-log.md` using the format defined in `.claude/rules.md` Section 1.

Before logging, read the existing error log to:

- Check if the same error was logged before (link as recurring pattern)
- Avoid duplicate entries for the same error in the same run

For each failure, append an entry:

```markdown
### [YYYY-MM-DD] generate-tests — <short description of failure>

- **Severity**: high | medium
- **Category**: selector | timeout | assertion | strict-mode | auth | api-mock | typescript
- **Spec/File**: `<spec-file>:<line>`
- **Error**: <first 2 lines of the Playwright error>
- **Root cause**: <1-sentence diagnosis>
- **Resolution**: unresolved
- **Pattern**: <link to previous entry if recurring, otherwise "first occurrence">
```

Also log if the generated spec file had issues (syntax errors, duplicate test titles, etc.) as `category: typescript`.

---

## Step 10 — Output

```markdown
# Playwright Test Report

**Target**: <component/page>
**Test file**: <e2e/path/to/file.spec.ts>
**Status**: PASS / FAIL / SKIPPED (dev server not running)
**Tests**: X passed · Y failed · Z skipped

---

## Test Suite Summary

| Group           | Tests | Result  |
| --------------- | ----- | ------- |
| Page Rendering  | N     | ✅ / ❌ |
| Navigation      | N     | ✅ / ❌ |
| Form Validation | N     | ✅ / ❌ |
| User Flows      | N     | ✅ / ❌ |
| Loading State   | N     | ✅ / ❌ |
| Error States    | N     | ✅ / ❌ |
| Accessibility   | N     | ✅ / ❌ |

---

## Failures (if any)

For each failure: **test name** — Error message — Root cause — Fix applied/suggested

---

## What was tested

Brief description of each test group and what it covers.

---

## Next steps
```

---

## Step 11 — Confirm before fixing failures

After presenting findings, ask:

**How would you like to proceed?**

1. Fix all failing tests
2. Re-run after starting the dev server
3. Add more test cases (specify which scenario)
4. Done — report complete

**Do NOT implement any changes until the user explicitly chooses an option.**

---

If Playwright is not installed, tell the user the exact commands to run and stop there.
Be precise — use exact element text, placeholders, and aria-labels from the component source.
Do NOT guess element selectors; always derive them from the component code you read.
