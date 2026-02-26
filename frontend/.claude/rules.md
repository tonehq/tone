# Project Rules

Rules that govern how Claude skills operate in this project. Referenced by `CLAUDE.md`.

---

## 1. Skill Error Tracking

Every skill (`generate-tests`, `code-review`) **must** log errors to `.claude/error-log.md` when failures occur. This builds a searchable history of issues, recurring patterns, and resolutions.

### When to log

| Trigger | Example |
|---------|---------|
| Test failure | Playwright test fails with selector/timeout/assertion error |
| Test generation error | Generated spec has syntax errors, duplicate titles, strict-mode violations |
| Code review finding | Critical or high-priority issues found during `/code-review` |
| Skill execution error | Skill cannot run (dev server down, missing deps, config issue) |
| Fix applied | A previously logged error was resolved |

### What NOT to log

- Passing tests (only log failures)
- Low-priority code review suggestions (style, naming)
- Transient issues the user resolved immediately (e.g., started the dev server)

### Error log format

Each entry in `.claude/error-log.md` follows this format:

```markdown
### [YYYY-MM-DD] SKILL_NAME — SHORT_TITLE

- **Severity**: critical | high | medium | low
- **Category**: selector | timeout | assertion | strict-mode | auth | api-mock | config | typescript | runtime
- **Spec/File**: `path/to/file.ts:line`
- **Error**: Exact error message (first 2 lines)
- **Root cause**: 1-sentence explanation
- **Resolution**: What fixed it (or "unresolved")
- **Pattern**: Is this a recurring issue? Link to previous entries if yes
```

### Severity definitions

| Severity | Meaning |
|----------|---------|
| **critical** | Blocks all tests or skill execution entirely |
| **high** | Individual test fails with a bug in the test or component |
| **medium** | Test is flaky or the error is intermittent |
| **low** | Minor issue that doesn't block execution |

### Error categories

| Category | Typical cause |
|----------|--------------|
| `selector` | Element not found, wrong role/name, component changed |
| `timeout` | API mock missing, async state not triggered, slow render |
| `assertion` | Wrong expected value, element state mismatch |
| `strict-mode` | Multiple elements matched a locator (e.g., sidebar + main content) |
| `auth` | Missing auth cookie, middleware redirect, token expired |
| `api-mock` | Route pattern mismatch, wrong response shape, missing mock |
| `config` | Playwright not installed, dev server down, missing env var |
| `typescript` | Type error in generated code, import error |
| `runtime` | Unhandled exception in component, hydration mismatch |

---

## 2. Error Resolution Workflow

When a skill encounters an error:

1. **Log it** — Append to `.claude/error-log.md` using the format above
2. **Diagnose** — Check error-log for similar past entries to find known fixes
3. **Fix** — Apply the resolution (only after user approval per skill rules)
4. **Update log** — Change "unresolved" to the actual fix applied

When the user runs `/error-tracker`:

1. **Read** the full error log
2. **Summarize** — Count by severity, category, and skill
3. **Identify patterns** — Flag recurring issues (same category + same file)
4. **Recommend** — Suggest preventive actions for top patterns

---

## 3. Skill Execution Rules

These rules apply to ALL skills in this project:

### Pre-execution checks

- Always verify the dev server is running before test skills (`curl localhost:3000`)
- Always read reference checklists before generating content
- Never apply fixes without explicit user approval

### Error handling

- Never silently swallow errors — always surface them in the report
- If a skill fails mid-execution, log what completed and what failed
- If the same error occurs 3+ times in the log, flag it as a **recurring pattern**

### Output standards

- Every skill must produce a structured report (not free-form text)
- Reports must include a "Next steps" section with numbered options
- The user chooses the action — skills do not auto-fix

---

## 4. Test Conventions

Rules specific to Playwright e2e tests (enforced by `generate-tests`):

- **Tab reuse**: One browser context per worker, one tab reused across tests. State isolation via `beforeEach` hooks (`page.unrouteAll()`, soft navigation). Only create a fresh tab per test if browser-level state conflicts exist.
- **Route cleanup**: `test.beforeEach` must call `page.unrouteAll({ behavior: 'wait' })` for specs that mock API routes, to prevent mock bleed between tests.
- **Login once per worker**: Call `loginViaUI(page)` from `e2e/helpers/auth.ts` inside the **worker-scoped fixture**, NOT in `beforeEach`. This logs in once through the actual login page UI against the real backend. Auth cookies persist across all tests in the worker. Do NOT manually inject cookies with `addCookies()`.
- **Soft navigation (dashboard pages)**: Use an `ensureOnPage(page, '/route')` helper in `beforeEach` instead of `page.goto()`. This skips navigation when already on the target page, uses sidebar links for client-side routing from other dashboard pages, and only falls back to a hard reload when outside the dashboard layout (e.g., after Auth Redirect tests land on `/auth/login`).
- **Soft navigation (auth pages)**: Use an `ensureOnPage(page)` helper that skips navigation when already on the target auth page, and falls back to `page.goto()` when on a different URL. Auth pages have no sidebar, so soft nav is simply skip-or-goto. Test groups that need a clean form (Form Validation, Auth Flow) add their own nested `beforeEach` with `page.goto()`.
- **Cookie save/restore**: Tests that clear cookies (e.g., Auth Redirect) must save cookies in a nested `beforeEach` and restore them in `afterEach` so subsequent tests stay authenticated.
- **Cookie cleanup (auth pages)**: Auth flow tests that mock the login API with a 200 success response trigger `setToken()` which sets real cookies. These test groups must clear cookies in `afterEach` to prevent interference with subsequent tests.
- **Loading state mocks**: Delayed API mocks for testing loading state should use `route.abort()` instead of `route.fulfill()` to prevent the component's success handler from triggering navigation after the test ends.
- **Selector disambiguation**: When sidebar and main content share element names (e.g., "Agents"), use the full accessible name or scope to a parent locator.
- **Alert helper**: Always use `const getAlert = (p: Page) => p.getByRole('alert').filter({ hasText: /\S+/ })` to avoid Next.js route announcer collisions.
- **Unique test titles**: When generating tests in a loop, include enough context in the title to avoid duplicates (e.g., include card name, not just href).

---

## 5. UI stack: shadcn + Tailwind (MUI removal planned)

- **Prefer shadcn and Tailwind CSS** for new UI: use `@/components/ui/` (shadcn) and Tailwind classes. Use **lucide-react** for generic icons.
- **Do not add new MUI dependencies.** For new features (icons, components, layouts), use shadcn components, Tailwind, or plain SVG/icons in `@/components/icons/` (e.g. brand icons like Google).
- **MUI removal is planned.** Existing MUI usage remains for now, but when touching code that uses `@mui/icons-material` or `@mui/material`, prefer replacing with shadcn + Tailwind or `@/components/icons/` + lucide-react where practical.
