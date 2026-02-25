---
name: run-tests
description: Use this skill when the user asks to run, re-run, or debug existing Playwright e2e tests. Accepts an optional argument — a spec file path, a short page name (e.g. "login", "signup"), a grep pattern to filter by test name, or a flag like "--headed" or "--debug". With no argument, runs the full suite.
argument-hint: '[spec-file | page-name | --headed | --debug | --grep "pattern"]'
allowed-tools: Bash, Read, Glob
license: proprietary
compatibility: Requires Node.js, yarn, and Playwright. Next.js dev server must be reachable at localhost:3000.
metadata:
  author: tonehq
  version: '1.0.0'
  category: testing
  tags: playwright, e2e, testing, runner, react, nextjs
---

You are a Senior QA Engineer running Playwright e2e tests for a React + Next.js (App Router) codebase.
Your job is to run existing tests, report results clearly, diagnose failures, and offer actionable next steps.

---

## Step 1 — Parse the argument

```
ARG=$ARGUMENTS
```

Determine the run mode from `$ARGUMENTS`:

| Argument pattern | Run mode |
|-----------------|----------|
| empty | Run the full suite (`e2e/**/*.spec.ts`) |
| short name: `login`, `signup` | Resolve to matching spec file, run that file |
| file path: `e2e/auth/login.spec.ts` | Run that file directly |
| `--headed` | Run the full suite in headed (visible browser) mode |
| `--debug` | Run the full suite in Playwright debug mode |
| `--grep "text"` | Run all tests whose name matches the pattern |
| combined: `login --headed` | Resolve file + apply flag |

---

## Step 2 — Resolve the spec file (if a name or path was given)

If `$ARGUMENTS` contains a short name (not a flag), find the matching spec:

```bash
find e2e -name "*<name>*" -name "*.spec.ts" | head -5
```

Map short names to spec files:

| Short name | Spec file |
|-----------|-----------|
| `login` | `e2e/auth/login.spec.ts` |
| `signup` | `e2e/auth/signup.spec.ts` |
| `home` | `e2e/dashboard/home.spec.ts` |

If no matching spec file is found, inform the user:
> No spec file found for `<name>`. Run `/playwright-testing <name>` to generate one first.

---

## Step 3 — Check the dev server

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

- **200** → proceed to Step 4
- **anything else** → stop and tell the user:
  > The dev server is not running. Start it with `yarn dev` in a separate terminal, then re-run `/run-tests`.

---

## Step 4 — List available tests (before running)

If running a single file, show how many tests it contains:

```bash
yarn playwright test <file> --list 2>&1 | head -40
```

Print a brief summary:
> Running **N tests** from `<file>`

---

## Step 5 — Build the command and run

Assemble the Playwright command based on the resolved inputs:

```bash
# Full suite
yarn playwright test --reporter=list

# Single file
yarn playwright test e2e/auth/login.spec.ts --reporter=list

# Headed mode
yarn playwright test e2e/auth/login.spec.ts --headed --reporter=list

# Debug mode (opens Playwright Inspector)
yarn playwright test e2e/auth/login.spec.ts --debug

# Grep filter
yarn playwright test --grep "shows the login heading" --reporter=list
```

Always use `--reporter=list` unless `--debug` is active (debug has its own UI).

Set a generous timeout so slow tests don't get cut off:

```bash
yarn playwright test <args> --reporter=list 2>&1
```

---

## Step 6 — Parse and present results

After the run completes, output the report in this format:

```markdown
# Test Run Report

**Spec**: <file or "full suite">
**Mode**: normal | headed | debug | grep
**Status**: ✅ PASS / ❌ FAIL
**Tests**: X passed · Y failed · Z skipped
**Duration**: Xs

---

## Test Suite Summary

| Group | Tests | Result |
|-------|-------|--------|
| Page Rendering | N | ✅ / ❌ |
| Navigation | N | ✅ / ❌ |
| Form Validation | N | ✅ / ❌ |
| Authentication Flow | N | ✅ / ❌ |
| Loading State | N | ✅ / ❌ |
| Accessibility | N | ✅ / ❌ |

---

## Failures

For each failed test, provide:

### ❌ `<test name>`
- **Error**: <exact error message from Playwright output>
- **Location**: `<file>:<line>`
- **Root cause**: <1-sentence diagnosis>
- **Suggested fix**: <concrete actionable fix>

---

## Positive

List passing groups or notable successful flows.
```

---

## Step 7 — Diagnose failures

For each failure, apply this diagnosis checklist:

### Selector failures (`locator resolved to 0 elements`)
- Element text/placeholder/role changed in the component → re-read the component file and update selector
- Route announcer conflict → check if `getByRole('alert')` needs the `getAlert` filter
- Component not yet rendered → add `await expect(locator).toBeVisible()` before asserting

### Strict mode violations (`resolved to N elements`)
- Multiple elements match the selector → scope with `.filter()`, `.first()`, or a parent locator
- Next.js route announcer matching `role="alert"` → use `getAlert(p: Page) => p.getByRole('alert').filter({ hasText: /\S+/ })`

### Timeout failures (`Timeout 5000ms exceeded`)
- API mock missing or wrong URL pattern → verify `**/path` pattern matches the actual request
- Async state not triggered → check that the action (click, fill) actually fires the API call
- Notification not appearing → check `useNotification` hook is wired to the component

### Navigation failures (`expected URL to be /x, received /y`)
- Middleware redirecting unauthenticated request → ensure the mock sets the right cookies or the route is public
- `router.push()` not called → check the success branch of the handler

### Fixture / Hook ESLint errors (not a runtime failure, but blocks the run)
- `use` parameter in Playwright fixture triggers `react-hooks/rules-of-hooks` → rename to `provide`

---

## Step 8 — Ask how to proceed

After presenting the report, always ask:

**How would you like to proceed?**
1. Fix all failing tests
2. Re-run in headed mode (`--headed`) to watch the browser
3. Re-run in debug mode (`--debug`) to step through with Playwright Inspector
4. Run a specific test by name (`--grep "test name"`)
5. Done — report complete

**Do NOT apply any fixes until the user explicitly chooses option 1.**

---

## Quick reference — available test files

```
e2e/auth/login.spec.ts      → Login page (25 tests)
```

Add new entries here whenever `/playwright-testing` generates a new spec file.
