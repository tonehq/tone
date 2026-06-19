# Feature Doc: <Page Name>

Feature documentation for test generation. Place in `e2e/ux_flow_docs/<page-name>.md`.

The `/generate-tests` skill auto-discovers docs matching the target page name, or use
`--docs e2e/ux_flow_docs/<page-name>.md` to specify explicitly.

> **Format rule (mandatory):** Every test case in this folder is written as
> **one Action (steps) + multiple Observations (each a set of steps)**.
> See the [Test Cases](#test-cases) section below for the exact shape.
> Do **not** use one-line "scenario → expected" rows.

---

## Page

- **Route**: `/route-path`
- **Component**: `src/app/.../ComponentName.tsx`
- **Layout**: `src/app/.../layout.tsx` (if any)
- **Auth required**: yes / no
- **Redirect when already authenticated**: <describe or "n/a">

---

## User Stories

### US-1: <Short title>

**As a** <user role>, **I want to** <action>, **so that** <outcome>.

**Acceptance criteria**:

- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] <criterion 3>

### US-2: <Short title>

...

---

## UI Elements

| Element         | Type       | Content / Label                 | Behavior                    |
| --------------- | ---------- | ------------------------------- | --------------------------- |
| Welcome heading | h4         | "Welcome to X"                  | Static text                 |
| Submit button   | button     | "Continue"                      | Submits form, shows loading |
| Email input     | text input | placeholder: "Enter your email" | Required, email validation  |

---

## Input Specifications

| Field    | Type     | Required | Validation Rules                              | Exact Error Message            |
| -------- | -------- | -------- | --------------------------------------------- | ------------------------------ |
| Email    | email    | yes      | non-empty, valid email shape                  | "Please enter a valid email"   |
| Password | password | yes      | length ≥ 6                                    | "Password must be ≥ 6 chars"   |

---

## Navigation

| Trigger              | Destination                   | Condition           |
| -------------------- | ----------------------------- | ------------------- |
| Click "Continue"     | `/home`                       | On success          |
| Click "Sign up" link | `/auth/signup`                | Always              |
| No auth cookie       | `/auth/login?redirect=<path>` | Middleware redirect |

---

## API Contracts

| Endpoint      | Method | Request               | Success Response                           | Error Response      |
| ------------- | ------ | --------------------- | ------------------------------------------ | ------------------- |
| `/auth/login` | POST   | `{ email, password }` | `{ access_token, user_id, organizations }` | `{ detail: "..." }` |

---

## Test Cases

> **Format (MANDATORY) — every test case is one Action + multiple Observations.
> Each Action is a numbered list of steps. Each Observation is a numbered list of steps.**
>
> Use ID prefixes by category, e.g. `TC-HAPPY-001`, `TC-VALIDATE-001`, `TC-ERROR-001`,
> `TC-NAV-001`, `TC-A11Y-001`. Number monotonically inside each prefix.

### Template for a single test case

```
### TC-<CATEGORY>-<NNN>: <Short imperative title>

**Preconditions**:
- <preconditions, one bullet each>

**Action** (steps performed by the user / test runner):
1. <step 1 — concrete UI action, e.g. "Visit /auth/login">
2. <step 2 — e.g. "Type 'owner@acme.com' into the Email input">
3. <step 3 — e.g. "Click the Sign In button">

**Observation 1 — <what this observation verifies, e.g. "Network request fires correctly">**:
1. <check 1 — e.g. "Exactly one POST /auth/login request is recorded">
2. <check 2 — e.g. "Request body equals { email, password } with no extra fields">
3. <check 3 — e.g. "Request includes Content-Type: application/json header">

**Observation 2 — <e.g. "Local storage hydrates">**:
1. <check 1 — e.g. "localStorage.access_token equals response.access_token">
2. <check 2 — e.g. "localStorage.login_data is valid JSON containing user.id">

**Observation 3 — <e.g. "User is redirected">**:
1. <check 1 — e.g. "URL becomes /home within 1s">
2. <check 2 — e.g. "Success toast 'Welcome back!' is visible in [data-sonner-toast]">

**API mock (if any)**:
- `POST /auth/login` → 200 with body `{ access_token, refresh_token, user, organization, role }`

**Cleanup**:
- <cleanup steps, e.g. "Clear localStorage; delete test user via admin API">
```

### Worked example

### TC-HAPPY-001: Sign in with valid credentials lands on /home

**Preconditions**:
- User is signed out (no `access_token` in localStorage)
- User has a valid account in the backend

**Action**:
1. Visit `/auth/login`
2. Type `owner@acme.com` into the Email input
3. Type `hunter22!` into the Password input
4. Click the "Sign In" button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/login` request is recorded
2. Request body equals `{ "email": "owner@acme.com", "password": "hunter22!" }`
3. Request has no `tenant_id` header (login is pre-tenant)

**Observation 2 — Loading state during request**:
1. The "Sign In" button text changes to "Loading..."
2. The "Sign In" button has the `disabled` attribute
3. Clicking the button a second time does NOT trigger a second `POST /auth/login`

**Observation 3 — Local storage hydration after 200**:
1. `localStorage.access_token` equals the response `access_token`
2. `localStorage.refresh_token` equals the response `refresh_token`
3. `localStorage.login_data` is valid JSON and contains `user.id`
4. `localStorage.active_org_id` equals the response `organization.id`

**Observation 4 — Redirect**:
1. URL becomes `/home` within 1s
2. The login form is no longer in the DOM

**Observation 5 — Toast**:
1. A Sonner toast appears in `[data-sonner-toast]`
2. Toast title text equals `Welcome back!`
3. Toast auto-dismisses within 5s

**API mock**:
- `POST /auth/login` → 200 with body `{ "access_token": "eyJ...", "refresh_token": "eyJ...", "user": { "id": "...", "email": "owner@acme.com" }, "organization": { "id": "...", "name": "Acme" }, "role": "owner" }`

**Cleanup**:
- Clear localStorage and cookies in the `afterEach` hook

---

### Test case categories (use these prefixes)

| Prefix         | Use for                                                                |
| -------------- | ---------------------------------------------------------------------- |
| `TC-HAPPY-`    | Positive / happy-path flows                                            |
| `TC-VALIDATE-` | Client-side validation (required fields, format, length, …)            |
| `TC-ERROR-`    | Server-side errors (4xx / 5xx) and how the UI surfaces them            |
| `TC-NAV-`      | Navigation, links, redirects, deep links, browser back                 |
| `TC-LOADING-`  | Loading / pending / disabled / double-submit guard states              |
| `TC-EDGE-`     | Edge cases (very long input, unicode, paste, offline, slow API, …)    |
| `TC-A11Y-`     | Accessibility (keyboard, focus, ARIA, screen reader)                   |
| `TC-FULL-`     | End-to-end comprehensive lifecycle (one big test that walks all flows) |

---

## Edge Cases (must each appear as a `TC-EDGE-NNN` test case above)

- [ ] Empty form submission (required field validation)
- [ ] Network error during API call
- [ ] Expired auth token
- [ ] Very long input values (> 500 chars)
- [ ] Special characters and unicode (emoji, RTL, etc.)
- [ ] Double-submit / rapid clicking
- [ ] Browser back after success
- [ ] Authenticated user revisits a public page

---

## Business Rules

- <rule 1>
- <rule 2>

---

## Accessibility Requirements (must each appear as a `TC-A11Y-NNN` test case above)

- [ ] All interactive elements reachable via keyboard in a sensible order
- [ ] Proper heading hierarchy (h1 > h2 > h3)
- [ ] Form inputs have associated labels (or `aria-label`)
- [ ] Error messages announced to screen readers (`role="alert"` or `aria-live`)
- [ ] Focus is trapped in modals and restored on close
