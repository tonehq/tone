# Project Rules

Rules that govern how Claude skills operate in this project. Referenced by `CLAUDE.md`.

---

## 1. Skill Error Tracking

Every skill (`generate-tests`, `code-review`, `generate-feature-docs`) **must** log errors to `.claude/error-log.md` when failures occur. This builds a searchable history of issues, recurring patterns, and resolutions.

### When to log

| Trigger               | Example                                                                    |
| --------------------- | -------------------------------------------------------------------------- |
| Test failure          | Playwright test fails with selector/timeout/assertion error                |
| Test generation error | Generated spec has syntax errors, duplicate titles, strict-mode violations |
| Doc generation error  | Feature doc missing sections, unresolvable imports, file not found          |
| Code review finding   | Critical or high-priority issues found during `/code-review`               |
| Skill execution error | Skill cannot run (dev server down, missing deps, config issue)             |
| Fix applied           | A previously logged error was resolved                                     |

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

| Severity     | Meaning                                                   |
| ------------ | --------------------------------------------------------- |
| **critical** | Blocks all tests or skill execution entirely              |
| **high**     | Individual test fails with a bug in the test or component |
| **medium**   | Test is flaky or the error is intermittent                |
| **low**      | Minor issue that doesn't block execution                  |

### Error categories

| Category      | Typical cause                                                      |
| ------------- | ------------------------------------------------------------------ |
| `selector`    | Element not found, wrong role/name, component changed              |
| `timeout`     | API mock missing, async state not triggered, slow render           |
| `assertion`   | Wrong expected value, element state mismatch                       |
| `strict-mode` | Multiple elements matched a locator (e.g., sidebar + main content) |
| `auth`        | Missing auth cookie, middleware redirect, token expired            |
| `api-mock`    | Route pattern mismatch, wrong response shape, missing mock         |
| `config`      | Playwright not installed, dev server down, missing env var         |
| `typescript`  | Type error in generated code, import error                         |
| `runtime`     | Unhandled exception in component, hydration mismatch               |

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

These rules apply to ALL skills in this project (`generate-tests`, `code-review`, `generate-feature-docs`):

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

---

## 6. Shared component usage (mandatory)

All UI must go through `@/components/shared` where a shared component exists. This ensures consistent styling, centralized control, and easier maintenance. Read `docs/shared-components.md` for the full API reference.

### Required shared components

| Need                          | Use                                          | Do NOT use                                                                 |
| ----------------------------- | -------------------------------------------- | -------------------------------------------------------------------------- |
| Button / click action         | `CustomButton` from `@/components/shared`    | Native `<button>`, shadcn `Button` directly, MUI `Button`                  |
| Data table                    | `CustomTable` from `@/components/shared`     | MUI `DataGrid`, Ant Design `Table`, raw `<table>`, shadcn `Table` directly |
| Modal / dialog / confirmation | `CustomModal` from `@/components/shared`     | MUI `Dialog`, shadcn `Dialog` directly, browser `alert()`/`confirm()`      |
| Text input                    | `TextInput` from `@/components/shared`       | MUI `TextField`, shadcn `Input` directly, native `<input>`                 |
| Select / dropdown             | `SelectInput` from `@/components/shared`     | MUI `Select`, shadcn `Select` directly (except toolbar/compact contexts)   |
| Textarea / multiline input    | `TextAreaField` from `@/components/shared`   | MUI `TextField multiline`, shadcn `Textarea` directly                      |
| Tabs                          | `CustomTab` from `@/components/shared`       | MUI `Tabs`, shadcn `Tabs` directly                                         |
| Checkbox                      | `CheckboxField` from `@/components/shared`   | MUI `Checkbox`, shadcn `Checkbox` directly                                 |
| Radio group                   | `RadioGroupField` from `@/components/shared` | MUI `RadioGroup`, shadcn `RadioGroup` directly                             |
| Link navigation               | `CustomLink` from `@/components/shared`      | Styled `<a>` tags (plain `next/link` is fine for non-styled links)         |

### Rules

1. **Always check `@/components/shared` first.** Before reaching for a shadcn primitive or creating an inline solution, verify whether a shared wrapper already exists.
2. **Import from the barrel.** Use `import { CustomButton, CustomTable } from '@/components/shared'` for consistency and tree-shaking.
3. **Shared components wrap shadcn primitives.** The `@/components/ui/` directory contains raw shadcn primitives. Application code should use the shared wrappers, not the primitives directly. Primitives are for building new shared components only.
4. **New shared components must be documented.** When creating or modifying a shared component, update `docs/shared-components.md` and add the export to `@/components/shared/index.tsx`.
5. **No UI logic duplication.** If you find yourself re-implementing loading spinners, confirm/cancel dialogs, or search-enabled tables, you are likely missing a shared component feature. Extend the shared component instead of duplicating.
6. **No raw `<button>` elements.** Every clickable button in application code must use `CustomButton`. Raw `<button>` and direct shadcn `Button` are prohibited outside of `@/components/shared/` and `@/components/ui/`. When touching existing code that has raw buttons, replace them with `CustomButton`.

### Why these rules exist

- **Consistent UI:** All buttons, tables, and modals look and behave the same across the app.
- **Single point of change:** Updating a shared component propagates everywhere. No hunting for 15 different button implementations.
- **Reduced bundle size:** One well-optimized component instead of multiple ad-hoc implementations.
- **Faster development:** Developers reach for proven, documented components instead of building from scratch.
- **Enforced design system:** Prevents drift from the project's visual language.

---

## 7. Code comments policy

Keep code clean and self-documenting. Comments are noise unless they explain _why_, not _what_.

### Do NOT add

- Section divider comments (`// ── Types ──`, `// ── Component ──`, `// ── Defaults ──`)
- JSDoc comments on interface fields when the field name is self-explanatory
- Inline comments that restate the code (`// filter hidden columns`, `// set page to 1`)
- `TODO` or `FIXME` without an associated issue or ticket
- Commented-out code blocks — delete dead code, rely on git history

### Do add

- Comments explaining non-obvious business logic or workarounds
- Comments on regex patterns or complex algorithms
- Links to external docs when using an unusual API or browser quirk
- `// eslint-disable-next-line` with a reason when suppressing a lint rule

---

## 8. File organization conventions

Keep code organized by responsibility. Every new file must land in the correct directory.

### Directory structure

| Directory                | Contents                                        | Examples                                                                                                 |
| ------------------------ | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/types/`             | TypeScript interfaces and type aliases          | `agent.ts`, `provider.ts`, `components.ts`, `integration.ts`, `sidebar.ts`                               |
| `src/constants/`         | Static values, config objects, enums            | `index.ts` (cookie keys, URLs), `sidebar.ts` (nav config, widths), `settings.ts`                         |
| `src/utils/`             | Pure helper functions and utilities             | `helpers.ts` (generateUUID), `agentFormUtils.ts` (form state transforms), `axios.ts`, `notification.tsx` |
| `src/services/`          | API call functions (thin wrappers around axios) | `agentsService.ts`, `channelService.ts`, `providerService.ts`                                            |
| `src/atoms/`             | Jotai atoms (state + write actions)             | `AgentsAtom.tsx`, `AuthAtom.tsx`, `ProviderAtom.tsx`                                                     |
| `src/components/shared/` | Reusable UI components                          | `CustomTable.tsx`, `CustomModal.tsx`, `CustomButton.tsx`                                                 |
| `src/components/ui/`     | Raw shadcn primitives (not imported by pages)   | `button.tsx`, `dialog.tsx`, `table.tsx`                                                                  |

### Rules

1. **Types live in `src/types/`.** Do not define exported interfaces inside atoms, services, or components. Import types from `@/types/<domain>`.
2. **Constants live in `src/constants/`.** Static config, magic numbers, cookie key names, URL patterns, and nav menus go here. Do not scatter constants across component files.
3. **Utility functions live in `src/utils/`.** Pure functions (no side effects, no API calls) that are used by multiple files belong in utils. Single-use helpers may stay in their component file.
4. **Services only do API calls.** Files in `src/services/` must not import Jotai atoms or define types. They accept parameters, call axios, and return data.
5. **Atoms orchestrate state.** Atoms import from `@/services/` and `@/types/`. Components import atoms. Atoms must not import from components.
6. **Re-export for backwards compatibility.** When moving a type, constant, or function to its canonical location, leave a re-export in the old file to avoid breaking existing imports. Remove the re-export in a follow-up cleanup.
7. **One domain per file.** `src/types/agent.ts` holds all agent-related types. `src/constants/sidebar.ts` holds all sidebar constants. Do not split a domain across multiple files in the same directory.

---

## 9. Reusable domain components (mandatory)

Certain UI elements have canonical component implementations. Always use these instead of re-implementing with inline styles or ad-hoc Badge/Chip usage.

### Required domain components

| Need | Use | Do NOT use |
| --- | --- | --- |
| Inbound/Outbound agent type badge | `AgentTypeBadge` from `@/components/agents/AgentTypeBadge` | Inline `Badge` with custom emerald/violet colors, MUI `Chip` |

### Rules

1. **Always use `AgentTypeBadge`** when displaying inbound or outbound agent type labels anywhere in the app. It renders a consistent `Badge variant="outline"` with the correct icon (`PhoneIncoming`/`PhoneOutgoing`) and color scheme (`emerald` for inbound, `violet` for outbound).
2. **Do not duplicate the color logic.** The component owns the `AGENT_TYPE_CONFIG` mapping. If the design changes, update the component once.

---

## 10. Form layout and spacing standards

All form pages (agent form, settings, etc.) follow consistent spacing rules for visual breathing room and alignment.

### Form row pattern

Use a **55% / 40%** left-right split with a gap between label and control:

```
<div className="mb-6 flex items-start justify-between gap-6">
  <div className="flex-[0_0_55%]">
    <h3 className="text-sm font-semibold text-foreground">{label}</h3>
    <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
  </div>
  <div className="flex-[0_0_40%]">{control}</div>
</div>
```

### Spacing tokens

| Element | Class | Value |
| --- | --- | --- |
| Between form rows | `mb-6` | 1.5rem vertical |
| Section container padding | `py-4` | 1rem vertical |
| Tab content area | `px-8 py-6` | 2rem / 1.5rem |
| Sidebar nav item spacing | `space-y-0.5` | 0.125rem between items |
| Description text below labels | `mt-0.5 text-[13px] leading-relaxed` | Tighter to label, readable |
| Alert/banner bar | `px-6 py-2.5` | Compact horizontal bar |

### Typography in forms

| Element | Classes |
| --- | --- |
| Form row label | `text-sm font-semibold text-foreground` |
| Form row description | `text-[13px] leading-relaxed text-muted-foreground` |
| Page heading | `text-lg font-semibold text-foreground` |
| Banner/alert text | `text-[13px]` |
