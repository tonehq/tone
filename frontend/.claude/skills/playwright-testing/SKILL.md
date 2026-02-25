---
name: playwright-testing
description: Use this skill when the user asks to write, run, or fix Playwright e2e tests for any page or component. Accepts an optional target argument — a file path, page name, or route (e.g. "login", "signup", "src/app/auth/login/LoginPage.tsx"). Defaults to the login page when no argument is given.
argument-hint: '[target-page-or-component]'
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
license: proprietary
compatibility: Requires Node.js, yarn, and Playwright. Next.js dev server must be reachable at localhost:3000.
metadata:
  author: tonehq
  version: '1.0.1'
  category: testing
  tags: playwright, e2e, testing, react, nextjs, mui
---

You are a Senior QA Engineer and Frontend Automation Specialist for a React + Next.js (App Router) codebase.
Your job is to produce high-quality, maintainable Playwright e2e tests that cover real user interactions.

---

## Step 1 — Resolve the target

```
TARGET=$ARGUMENTS
```

- If `$ARGUMENTS` is empty, default to `src/app/auth/login/LoginPage.tsx`
- If `$ARGUMENTS` is a route like `/auth/login`, find the matching page file under `src/app/`
- If `$ARGUMENTS` is a short name like `login` or `signup`, search for the component:
  ```bash
  find src/app -iname "*$ARGUMENTS*" | head -20
  ```
- If `$ARGUMENTS` is already a file path, use it directly

---

## Step 2 — Read reference checklists

Read ALL three reference files before generating any tests. Do not skip any.

- `.claude/skills/playwright-testing/references/test-patterns.md`
- `.claude/skills/playwright-testing/references/selectors-guide.md`
- `.claude/skills/playwright-testing/references/assertion-checklist.md`

---

## Step 3 — Analyse the component

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

| Page file | Test file |
|-----------|-----------|
| `src/app/auth/login/LoginPage.tsx` | `e2e/auth/login.spec.ts` |
| `src/app/auth/signup/SignupClient.tsx` | `e2e/auth/signup.spec.ts` |
| `src/app/(dashboard)/home/...` | `e2e/dashboard/home.spec.ts` |
| `src/app/auth/forgotpassword/...` | `e2e/auth/forgot-password.spec.ts` |

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
5. **API Mocking** — intercept backend calls with `page.route()`, never depend on a live backend
6. **Loading / Async State** — loading indicators, disabled buttons during async ops
7. **Error States** — network errors, API errors (4xx, 5xx), empty/invalid responses
8. **Accessibility** — keyboard navigation, aria roles, focus management

### Code standards:
- Use the worker-context + per-tab fixture from `test-patterns.md` — one browser window per worker, a fresh tab opened before each test and closed after
- Group tests with `test.describe()` blocks matching the groups above
- Use `test.beforeEach(async ({ page }) => { await page.goto('/route') })` to navigate inside the fresh tab
- Prefer semantic selectors: `getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`
- Mock all backend API calls — tests must pass without a live backend
- Add a `MOCK_*` constant section at the top of the file for test data
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
- Inform the user: "Start the dev server with `yarn dev` in a separate terminal, then re-run `/playwright-testing`"
- Still write the test file so it is ready to run

---

## Step 9 — Output

```markdown
# Playwright Test Report

**Target**: <component/page>
**Test file**: <e2e/path/to/file.spec.ts>
**Status**: PASS / FAIL / SKIPPED (dev server not running)
**Tests**: X passed · Y failed · Z skipped

---

## Test Suite Summary

| Group | Tests | Result |
|-------|-------|--------|
| Page Rendering | N | ✅ / ❌ |
| Navigation | N | ✅ / ❌ |
| Form Validation | N | ✅ / ❌ |
| User Flows | N | ✅ / ❌ |
| Loading State | N | ✅ / ❌ |
| Error States | N | ✅ / ❌ |
| Accessibility | N | ✅ / ❌ |

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

## Step 10 — Confirm before fixing failures

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
