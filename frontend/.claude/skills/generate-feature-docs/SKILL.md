---
name: generate-feature-docs
description: >
  Generates feature documentation for a Next.js page by analyzing component source,
  service imports, Jotai atoms, and navigation paths. Output placed in e2e/docs/<page-name>.md
  and consumed by /generate-tests for comprehensive test coverage.
argument-hint: '<page-name> [--routes /path1,/path2]'
allowed-tools: Bash, Read, Write, Glob, Grep
license: proprietary
compatibility: Requires a Next.js (App Router) project with src/app/ structure.
metadata:
  author: tonehq
  version: '1.0.0'
  category: documentation
  tags: feature-docs, e2e, testing, analysis, react, nextjs, jotai
---

You are a Senior Frontend Analyst and Documentation Specialist for a React + Next.js (App Router) codebase.
Your job is to produce accurate, structured feature documentation that the `/generate-tests` skill consumes to create comprehensive Playwright e2e tests.

**Core principle**: Every value in the doc must come from the source code. Use exact text from JSX, exact endpoints from service files, exact field names from types. Never guess or assume.

---

## Step 1 — Resolve the target and routes

```
FULL_ARGS=$ARGUMENTS
```

### 1a. Parse `--routes` flag (optional)

If `$ARGUMENTS` contains `--routes /path1,/path2`:

- Extract the comma-separated routes and set `ROUTES=[/path1, /path2]`
- Remove `--routes ...` from arguments, leaving the page name

Examples:

```
/generate-feature-docs settings --routes /settings,/settings/members
  → TARGET=settings, ROUTES=[/settings, /settings/members]

/generate-feature-docs agents
  → TARGET=agents, ROUTES=<auto-discover>
```

### 1b. Resolve the target component

- If target is empty, inform the user: "Please specify a page name (e.g., `/generate-feature-docs settings`)" and stop
- If target is a short name like `settings` or `agents`, search for the matching page:
  ```bash
  find src/app -name "page.tsx" -path "*$TARGET*" | head -10
  ```
- If target is already a file path, use it directly
- If target is a route like `/settings`, find the matching page file under `src/app/`

### 1c. Auto-discover routes (when `--routes` is not provided)

If no explicit `--routes` was given, discover all routes for this page:

```bash
# Find all page.tsx files in the target directory
find src/app -name "page.tsx" -path "*$TARGET*"
```

Map each `page.tsx` to its route:
- `src/app/(dashboard)/settings/page.tsx` → `/settings`
- `src/app/auth/login/page.tsx` → `/auth/login`
- Strip `src/app/`, remove `(dashboard)/` and other route groups, remove `/page.tsx`

### 1d. Check for existing feature doc

```bash
ls e2e/docs/ 2>/dev/null | grep -i "$TARGET"
```

- If a feature doc already exists, inform the user:
  > Found existing feature doc: `e2e/docs/<name>.md` — overwrite? (proceed only with confirmation)
- If no doc exists, continue

---

## Step 2 — Read references

Read ALL of these before generating any documentation. Do not skip any.

- `.claude/skills/generate-feature-docs/references/analysis-guide.md` — how to trace imports
- `e2e/docs/_template.md` — the 8-section template structure
- `docs/shared-components.md` — shared component API reference (read this instead of individual component files)

### 2a. Read existing feature docs for quality calibration

Read **one** existing feature doc to calibrate output quality:

- If `e2e/docs/agents.md` exists, prefer it (complex multi-route example)
- Otherwise read `e2e/docs/home.md` (simple single-page example)

Use the existing doc as a quality benchmark: match its level of detail, formatting style, and completeness.

---

## Step 3 — Analyse page components

This is the core analysis step. Follow the import tracing process from `analysis-guide.md`.

### 3a. Read the page entry point

For each route discovered in Step 1c, read the `page.tsx` file. Identify:

- Whether it's a thin wrapper (imports a component) or contains significant JSX
- The primary component import path

### 3b. Read the primary component

Read the main component file. For each import, classify it per the analysis guide:

| Classification     | Action                                                          |
| ------------------ | --------------------------------------------------------------- |
| Service            | Read the service file → extract endpoints, methods, payloads   |
| Atom               | Read the atom file → extract state shape, actions, loadable    |
| Type               | Read the type file → extract interface fields                  |
| Child component    | Read the file → trace its imports (max 3 levels deep)          |
| Shared component   | Read `docs/shared-components.md` (do NOT read individual files) |
| Constants          | Read the constants file → extract relevant values              |
| Navigation         | Note `router.push`, `<Link>`, `useParams`, `useSearchParams`  |
| Utility            | Read only if it affects visible UI behavior                    |

### 3c. Build internal analysis artifact

As you trace, build a structured summary (not written to disk — used for Step 5):

```
ANALYSIS:
  routes: [list of routes]
  auth_required: yes/no
  components_read: [list of files read]
  services: [{ function, method, endpoint, request, response }]
  atoms: [{ name, type, state_shape, actions, services_called }]
  types: [{ name, fields }]
  ui_elements: [{ name, type, content, behavior }]
  navigation: [{ trigger, destination, condition }]
  error_states: [{ trigger, ui_result }]
  loading_states: [{ trigger, ui_result }]
  form_fields: [{ name, type, default, validation }]
```

---

## Step 4 — Check auth pattern

Read `src/middleware.ts` and determine:

1. Is the target route in `PUBLIC_PATHS`? → Auth required: no
2. If not in `PUBLIC_PATHS` → Auth required: yes
3. What is the redirect URL pattern? → `/auth/login?redirect=<pathname>`
4. What cookie is checked? → `tone_access_token`

Document the auth requirement and redirect behavior for the feature doc.

---

## Step 5 — Generate feature doc

Using the analysis artifact from Step 3 and the template from `e2e/docs/_template.md`, generate all 8 sections.

### Section 1: Page

- **Route**: list all routes (multi-route pages list all)
- **Component**: path to the primary component file(s)
- **Auth required**: yes/no with redirect details

### Section 2: User Stories

For each distinct user capability on the page:

- Write in the `As a ... I want to ... so that ...` format
- List acceptance criteria as checkboxes (unchecked — tests will check them)
- Include an auth protection user story for dashboard pages
- Each acceptance criterion must be verifiable from the UI (visible text, element presence, navigation)

**How to discover user stories:**

- Each major UI section or feature = one user story
- Each form with submit = one user story
- Each CRUD operation = one user story
- Auth protection = one user story (for dashboard pages)
- Each distinct navigation flow = part of a user story

### Section 3: UI Elements

Create a table for each route/section of the page:

| Element | Type | Content / Label | Behavior |

- **Element**: descriptive name
- **Type**: HTML element or component type (h4, button, text input, Card, etc.)
- **Content / Label**: exact text from JSX, placeholder text, or aria-label
- **Behavior**: what happens on interaction (static, navigates, submits, toggles, etc.)

**Extract exact text** from JSX: string literals, template literals, constant values. Never paraphrase.

### Section 4: Navigation

| Trigger | Destination | Condition |

Capture every navigation path found in Step 3 analysis. Include:
- User-triggered navigation (clicks, form submits)
- Programmatic navigation (router.push on success/error)
- Middleware redirects (auth)
- Keyboard navigation if applicable (Enter key on focused elements)

### Section 5: API Contracts

| Endpoint | Method | Request | Success Response | Error Response |

For each service function called by the page's atoms:
- **Endpoint**: exact path from service file
- **Method**: GET, POST, PUT, DELETE
- **Request**: body or query params (from the service function signature and call site)
- **Success Response**: shape from type files or atom transformation
- **Error Response**: standard `{ detail: "..." }` unless the service handles it differently

If the page makes no API calls (static page), write: "None — this is a static page with hardcoded data. No API calls."

Include response shape examples (JSON) for complex responses, following the agents.md pattern.

### Section 6: Edge Cases

List as checkboxes (unchecked). Discover from:
- Error paths in try/catch blocks
- Conditional renders (empty state, loading state, error state)
- Null/undefined guards in the component
- Array.isArray checks, fallback values
- Form validation edge cases
- Special characters, long values, empty submissions

### Section 7: Business Rules

List as bullet points. Discover from:
- Constants and defaults in the component or form utils
- Conditional logic that enforces rules (role checks, feature flags)
- Data transformation patterns (camelCase ↔ snake_case)
- State management patterns (which atoms, how data flows)
- API integration details (header injection, token management)

### Section 8: Accessibility Requirements

List as checkboxes (unchecked). Check for:
- Heading hierarchy (h1 > h2 > h3 etc.)
- Interactive elements: are they semantic (`<button>`, `<a>`) or non-semantic (`<div onClick>`)
- Form inputs: do they have labels or aria-labels
- Focus management: is focus trapped in modals/dialogs
- Keyboard navigation: can all interactive elements be reached via Tab/Enter
- Screen reader support: aria-live regions, role attributes
- MUI components: note if any accessibility props are overridden

---

## Step 6 — Write to file

Write the complete feature doc to `e2e/docs/<page-name>.md`.

- Use kebab-case for the filename (e.g., `phone-numbers.md`, `forgot-password.md`)
- Ensure valid markdown syntax
- Match the formatting style of existing feature docs

---

## Step 7 — Validate completeness

Cross-check the generated doc against the analysis artifact:

| Check | What to verify |
| ----- | -------------- |
| UI elements | Every interactive element from the component JSX is documented |
| API calls | Every service function called by the page's atoms has an API contract entry |
| Navigation | Every `router.push`, `<Link>`, and middleware redirect is in the Navigation table |
| Form fields | Every form input, select, toggle, and radio is listed in UI Elements with its default |
| State management | Loading, error, and empty states are covered in Edge Cases |
| Auth | Auth requirement matches middleware.ts |
| Types | Response shapes match the type files |

If any gaps are found, update the doc before proceeding.

---

## Step 8 — Output summary

Present a structured report to the user:

```markdown
# Feature Doc Report

**Target**: <page-name>
**Output**: `e2e/docs/<page-name>.md`
**Routes covered**: <list of routes>

---

## Coverage Summary

| Section              | Items |
| -------------------- | ----- |
| User Stories         | N     |
| UI Elements          | N     |
| Navigation Paths     | N     |
| API Contracts        | N     |
| Edge Cases           | N     |
| Business Rules       | N     |
| Accessibility Checks | N     |

---

## Component Trace

| File | Classification | Items extracted |
| ---- | -------------- | --------------- |
| `src/components/...` | Primary component | N elements, N nav paths |
| `src/services/...`   | Service           | N endpoints             |
| `src/atoms/...`      | Atom              | N state fields          |
| ...                  | ...               | ...                     |

---

## Notes

- <any observations, gaps, or warnings>
```

---

## Step 9 — Ask user for next action

After presenting the report, ask:

**How would you like to proceed?**

1. Generate tests for this page (`/generate-tests <page-name> --docs e2e/docs/<page-name>.md`)
2. Refine the feature doc (specify which section to improve)
3. Generate feature doc for another page
4. Done

**Do NOT make any changes until the user explicitly chooses an option.**

---

## Error Handling

If any step fails (file not found, no page matches target, etc.):

1. Log the error to `.claude/error-log.md` using the format in `.claude/rules.md` Section 1
2. Use category `config` for missing files, `runtime` for unexpected errors
3. Inform the user what failed and suggest a fix
4. Do not continue past the failed step

---

## Key Conventions

- **Exact text only** — every string in the doc must come from source code, not from guessing
- **Read `docs/shared-components.md`** instead of individual shared component files
- **3-level import depth limit** — page → component → sub-component → stop
- **No auto-fixes** — document only, never modify source code
- **Error logging** — append to `.claude/error-log.md` per `.claude/rules.md` Section 1
- **Unchecked boxes** — all acceptance criteria and edge cases use `- [ ]` (tests will verify them)
- **Multi-route pages** — list all routes in the Page section, create UI Elements sub-tables per route/section
