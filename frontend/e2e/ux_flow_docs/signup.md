# Feature Doc: Signup

Feature documentation for the `/signup` page. Used by `/generate-tests signup`
(or `--docs e2e/ux_flow_docs/signup.md`) to ensure all positive and negative user cases
are covered alongside the component source analysis.

The signup page registers a new user + (optionally) a new organization. It
calls `POST /auth/signup` with five fields (`first_name`, `last_name`, `email`,
`password`, optional `organization_name`) and on success swaps the form for a
"Check your email" confirmation panel — the **frontend never auto-logs the
user in** because email verification is required first.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/signup` (under the `(auth)` route group; legacy `/auth/signup` callers should arrive here)
- **Component**: `src/app/(auth)/signup/page.tsx` (default export `SignupPage` — single client component, no Suspense wrapper because it does not use `useSearchParams`)
- **Layout**: `src/app/(auth)/layout.tsx` — shared with the rest of `(auth)/*`
- **Auth required**: no — this is a **public** page
- **Redirect when already authenticated**: not enforced today (no `src/middleware.ts`). A signed-in user can still load `/signup` and submit, which would create a parallel account — discouraged but not blocked. ⚠ unverified whether a future iteration adds a client-side redirect

---

## User Stories

### US-1: Register and trigger an email verification

**As a** new user, **I want to** enter my name, email, password, and optional org name, **so that** the backend creates my account and sends a verification email to me.

**Acceptance criteria**:

- [ ] Heading reads "Create your account" with subtitle "Start building AI voice agents in minutes"
- [ ] Five fields render in this order: First Name, Last Name, Email, Organization Name (optional), Password
- [ ] Required fields (`first_name`, `last_name`, `email`, `password`) show the required indicator
- [ ] "Organization Name" shows the helperText "Optional"
- [ ] Submit button label is "Create Account"; loading state is "Loading..."
- [ ] On 201, the form is replaced by a `MailCheck`-icon panel that reads "Check your email" with the submitted email rendered in bold and an outline "Back to Login" button
- [ ] A success toast appears with title "Account created!" and description "Check your email to verify." (4 s duration)

### US-2: Sign in instead

**As a** returning user who clicked the wrong link, **I want to** click "Sign in" at the bottom of the form, **so that** I am redirected to `/login` without losing my place in the auth flow.

**Acceptance criteria**:

- [ ] Text "Already have an account?" is followed by a "Sign in" link
- [ ] Link href is `/login`

### US-3: Block submission on client-side validation errors

**As a** user, **I want to** see field-level errors before submission, **so that** I do not waste a network round-trip on a malformed payload.

**Acceptance criteria**:

- [ ] Empty First Name → helperText "First name is required"
- [ ] Empty Last Name → helperText "Last name is required"
- [ ] Empty Email → helperText "Email is required"
- [ ] Malformed Email → helperText "Please enter a valid email"
- [ ] Password under 8 chars → helperText "Password must be at least 8 characters"
- [ ] Organization Name is optional — empty is allowed
- [ ] While `signup.isPending === true`, Submit button shows "Loading..." and is `disabled`

### US-4: Recover from "Email already registered"

**As a** user who forgot they already have an account, **I want to** see a clear error toast and a "Sign in" affordance, **so that** I can pivot to logging in.

**Acceptance criteria**:

- [ ] 400 response with `{"detail": "Email already registered"}` surfaces toast title "Email already registered"
- [ ] Form stays populated; user can click the "Sign in" link at the bottom

---

## UI Elements

| Element                       | Type            | Content / Label                                         | Behavior                                                |
| ----------------------------- | --------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| Heading                       | h2              | "Create your account"                                   | Static                                                  |
| Subtitle                      | p               | "Start building AI voice agents in minutes"             | Static                                                  |
| First Name input              | TextInput       | placeholder "Jane"                                      | Required, Zod-validated                                 |
| Last Name input               | TextInput       | placeholder "Doe"                                       | Required, Zod-validated                                 |
| Email input                   | TextInput       | placeholder "you@company.com"                           | Required, Zod-validated                                 |
| Organization Name input       | TextInput       | placeholder "Acme Corp" + helperText "Optional"         | Optional, sent trimmed                                  |
| Password input                | TextInput (pwd) | placeholder "Min. 8 characters"                         | Required, min 8 chars                                   |
| Create Account button         | Button          | "Create Account" → "Loading..."                         | `type="submit"`; disabled while `signup.isPending`      |
| Sign in CTA                   | Link            | "Sign in" (after "Already have an account?")            | Navigates to `/login`                                   |
| MailCheck icon                | lucide icon     | `MailCheck`                                             | Renders only in the success panel                       |
| Confirmation heading          | h2              | "Check your email"                                      | Renders only after `signup.isSuccess === true`          |
| Confirmation body             | p               | "We've sent a verification link to **<email>**"         | `<strong>` wraps the submitted email                    |
| Confirmation help             | p               | "Click the link in the email to verify your account and start using Tone." | Static                       |
| Back to Login button          | Button (outline)| "Back to Login"                                         | Navigates to `/login`                                   |

---

## Input Specifications

Source: `src/schemas/auth.ts` (`signupSchema`).

| Field             | Type     | Required | Validation Rules                                                       | Exact Error Message                      |
| ----------------- | -------- | -------- | ---------------------------------------------------------------------- | ---------------------------------------- |
| First Name        | text     | yes      | `z.string().min(1)`                                                    | "First name is required"                 |
| Last Name         | text     | yes      | `z.string().min(1)`                                                    | "Last name is required"                  |
| Email             | email    | yes      | `z.string().min(1).email()`                                            | "Email is required" / "Please enter a valid email" |
| Organization Name | text     | no       | `z.string().optional()` — no length rule; empty allowed                | n/a                                      |
| Password          | password | yes      | `z.string().min(8)`                                                    | "Password must be at least 8 characters" |

**Button state rules:**

- "Create Account" is **never disabled** by `formState.isValid`; invalid submit surfaces inline helperText instead
- While `signup.isPending === true`, the shadcn `<Button>` renders "Loading..." and sets `disabled`
- Once `signup.isSuccess === true`, the entire form unmounts and the confirmation panel renders instead — there is no way back to the form on this page

---

## Navigation

| Trigger                                       | Destination          | Condition                                  |
| --------------------------------------------- | -------------------- | ------------------------------------------ |
| Successful signup (201)                       | (stays on `/signup`) | Form swaps to the confirmation panel       |
| Click "Sign in" (bottom of form)              | `/login`             | Always                                     |
| Click "Back to Login" (confirmation panel)    | `/login`             | Always                                     |
| Already authenticated visit                   | (stays on `/signup`) | No automatic redirect today ⚠ unverified  |

---

## API Contracts

Payloads sourced from the Postman collection (folder `Authentication`).

| Endpoint        | Method | Request                                                                                          | Success Response                              | Error Response          |
| --------------- | ------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------- | ----------------------- |
| `/auth/signup`  | POST   | `{ email, password, first_name, last_name, organization_name? }` (trimmed before send)           | 201 `AuthLoginResponse` (mirrors `/auth/login`) | `{ "detail": "..." }`   |

### Example: `POST /auth/signup`

Request body (with org):

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "organization_name": "Acme"
}
```

Request body (without org — `organization_name` key omitted, not sent as empty string):

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!",
  "first_name": "Ada",
  "last_name": "Lovelace"
}
```

201 Created response body:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "00000000-0000-0000-0000-000000000001",
    "organization_id": "00000000-0000-0000-0000-000000000100",
    "email": "owner@acme.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "avatar_url": null,
    "role": "owner",
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "last_login_at": null,
    "created_at": "2026-06-17T10:00:00+00:00",
    "updated_at": "2026-06-17T10:00:00+00:00"
  },
  "organization": {
    "id": "00000000-0000-0000-0000-000000000100",
    "name": "Acme",
    "slug": "acme",
    "subscription_tier": "free",
    "status": "active"
  },
  "role": "owner",
  "email_verification_token": "raw-verification-token-leaked-in-response"
}
```

400 Bad Request — duplicate email:

```json
{ "detail": "Email already registered" }
```

400 Bad Request — missing first_name:

```json
{ "detail": "first_name is required" }
```

400 Bad Request — missing email/password:

```json
{ "detail": "Email and password are required" }
```

422 Validation Error:

```json
{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
```

**Note**: The frontend ignores the response payload — `useSignup` does not call `setLoginResponse`, so the user remains signed out after a successful signup. The user must verify their email and then sign in via `/login`.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Full signup with organization swaps to confirmation panel

**Preconditions**:
- User is signed out (no `access_token` in localStorage)
- All five form fields are blank on mount

**Action**:
1. Visit `/signup`
2. Type `Ada` into First Name
3. Type `Lovelace` into Last Name
4. Type `owner@acme.com` into Email
5. Type `Acme` into Organization Name
6. Type `hunter22!` into Password
7. Click the "Create Account" button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/signup` request is recorded
2. Request body equals `{ "email": "owner@acme.com", "password": "hunter22!", "first_name": "Ada", "last_name": "Lovelace", "organization_name": "Acme" }`
3. Request `Content-Type` header is `application/json`

**Observation 2 — Loading state during request**:
1. The "Create Account" button text changes to "Loading..."
2. The "Create Account" button has the `disabled` attribute

**Observation 3 — Success toast**:
1. A Sonner toast appears in `[data-sonner-toast]`
2. Toast title equals `Account created!`
3. Toast description equals `Check your email to verify.`
4. Toast variant is `success`

**Observation 4 — Form unmounts and confirmation panel renders**:
1. The five input fields are no longer in the DOM
2. A heading with text `Check your email` is visible
3. The submitted email `owner@acme.com` is rendered inside a `<strong>` element
4. The `MailCheck` icon is visible above the heading
5. An outline button labelled `Back to Login` is in the DOM

**Observation 5 — No token persistence**:
1. `localStorage.access_token` is NOT set (signup does not call `setLoginResponse`)

**API mock**: `POST /auth/signup` → 201 with the AuthLoginResponse example above.

**Cleanup**: Clear localStorage and cookies in the `afterEach` hook.

---

### TC-HAPPY-002: Signup without organization sends omitted org field

**Preconditions**: User signed out; Organization Name left blank.

**Action**:
1. Visit `/signup`
2. Fill First Name, Last Name, Email, and Password with valid values
3. Leave Organization Name blank
4. Click "Create Account"

**Observation 1 — Request body omits the org key entirely**:
1. Exactly one `POST /auth/signup` request is recorded
2. Request body does NOT include the `organization_name` key (not sent as empty string, not sent as `null`)
3. Body contains exactly four fields: `email`, `password`, `first_name`, `last_name`

**Observation 2 — Confirmation panel renders**:
1. Heading `Check your email` is visible
2. Submitted email is rendered inside a `<strong>` element

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-HAPPY-003: Organization name with surrounding whitespace is trimmed

**Action**:
1. Visit `/signup`
2. Fill required fields validly
3. Type `   Acme   ` (with leading/trailing spaces) into Organization Name
4. Click "Create Account"

**Observation 1 — Request body has trimmed org name**:
1. Request body `organization_name` equals exactly `Acme` (no spaces)

**Observation 2 — Confirmation panel renders**:
1. Heading `Check your email` is visible

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-HAPPY-004: Confirmation panel renders submitted email verbatim

**Preconditions**: Form filled with mixed-case email.

**Action**:
1. Visit `/signup`
2. Fill First Name, Last Name, Password, and (optional) Organization Name
3. Type `Mixed.Case+Tag@Example.COM` into Email
4. Click "Create Account"

**Observation 1 — Email rendered without case-normalisation**:
1. The confirmation panel body contains `<strong>Mixed.Case+Tag@Example.COM</strong>` verbatim
2. The displayed email is not lowercased on the client (`watch('email')` returns the typed value)

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-VALIDATE-001: Empty First Name blocks submit with inline error

**Action**:
1. Visit `/signup`
2. Leave First Name blank
3. Fill the other required fields validly
4. Click "Create Account"

**Observation 1 — No network call fires**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error appears under First Name**:
1. Helper text under the First Name input reads exactly `First name is required`
2. First Name input has the error styling

**Observation 3 — No toast**:
1. No Sonner toast is shown
2. URL is still `/signup`

---

### TC-VALIDATE-002: Empty Last Name blocks submit

**Action**:
1. Visit `/signup`
2. Fill all required fields except Last Name
3. Click "Create Account"

**Observation 1 — No network call**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Last Name reads exactly `Last name is required`

---

### TC-VALIDATE-003: Empty Email blocks submit

**Action**:
1. Visit `/signup`
2. Leave Email blank
3. Fill the other required fields validly
4. Click "Create Account"

**Observation 1 — No network call**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Email is required`

---

### TC-VALIDATE-004: Malformed Email blocks submit

**Action**:
1. Visit `/signup`
2. Fill required fields validly
3. Type `not-an-email` into Email
4. Click "Create Account"

**Observation 1 — No network call**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

---

### TC-VALIDATE-005: Empty Password blocks submit (min(8) rejects empty string)

**Action**:
1. Visit `/signup`
2. Fill all required fields except Password
3. Click "Create Account"

**Observation 1 — No network call**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Password reads exactly `Password must be at least 8 characters`

> Note: Zod `min(8)` rejects the empty string; no separate "Password is required" message is shown.

---

### TC-VALIDATE-006: Short Password (< 8 chars) blocks submit

**Action**:
1. Visit `/signup`
2. Fill required fields validly
3. Type `7charss` (7 chars) into Password
4. Click "Create Account"

**Observation 1 — No network call**:
1. Zero `POST /auth/signup` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Password reads exactly `Password must be at least 8 characters`

---

### TC-ERROR-001: 400 Email already registered surfaces toast

**Action**:
1. Visit `/signup`
2. Fill all required fields with a previously-used email
3. Click "Create Account"

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/signup` request is recorded

**Observation 2 — Error toast**:
1. Toast title equals `Email already registered`
2. Toast variant is `error`

**Observation 3 — Form state preserved**:
1. All five inputs retain their values
2. "Create Account" button re-enables (no longer shows "Loading...")
3. URL is still `/signup`
4. The confirmation panel is NOT in the DOM

**API mock**: `POST /auth/signup` → 400 `{ "detail": "Email already registered" }`.

---

### TC-ERROR-002: 400 Email and password are required surfaces toast

**Action**:
1. Submit a valid-format payload (this branch is unreachable via healthy Zod, but the backend may still return it for direct callers)

**Observation 1 — Error toast**:
1. Toast title equals `Email and password are required`
2. Toast variant is `error`

**API mock**: `POST /auth/signup` → 400 `{ "detail": "Email and password are required" }`.

---

### TC-ERROR-003: 400 first_name is required surfaces toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `first_name is required`

**API mock**: `POST /auth/signup` → 400 `{ "detail": "first_name is required" }`.

---

### TC-ERROR-004: 422 with non-string `detail` falls back to generic toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`
2. Toast variant is `error`

**API mock**: `POST /auth/signup` → 422 `{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }`.

---

### TC-ERROR-005: 500 surfaces the verbatim string `detail`

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Form remains editable**:
1. All five inputs retain their values
2. "Create Account" button re-enables

**API mock**: `POST /auth/signup` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-006: Network failure shows generic fallback toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form state**:
1. All five inputs still contain their typed values
2. "Create Account" button re-enables for retry

**API mock**: route aborted with `failed` status (no response object).

---

### TC-ERROR-007: 401 mid-flow surfaces toast and stays on /signup

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — No auto-redirect**:
1. URL is still `/signup` (this endpoint does not redirect to `/login`)

**API mock**: `POST /auth/signup` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-008: 409 conflict — duplicate email surfaces same toast as FS-7

**Action**:
1. Submit valid-format payload with a duplicate email

**Observation 1 — Error toast**:
1. Toast title equals `Email already registered`

**Observation 2 — Form state**:
1. UX matches TC-ERROR-001 (inputs preserved, button re-enables)

**API mock**: `POST /auth/signup` → 409 `{ "detail": "Email already registered" }`.

> Note: Backend currently uses 400; a future change to 409 must surface the same toast.

---

### TC-NAV-001: Click "Sign in" link below the form navigates to /login

**Action**:
1. Visit `/signup`
2. Click the "Sign in" link below the form

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No network call**:
1. Zero `POST /auth/signup` requests are recorded
2. No full page reload occurs (client-side `<Link>`)

---

### TC-NAV-002: Click "Back to Login" from the confirmation panel

**Preconditions**: TC-HAPPY-001 just completed; confirmation panel is visible.

**Action**:
1. Click the outline "Back to Login" button inside the confirmation panel

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No full page reload**:
1. No full page reload occurs

---

### TC-LOADING-001: Create Account button shows loading state during slow API

**Action**:
1. Visit `/signup`
2. Fill all required fields validly
3. Click "Create Account" against a deliberately slow backend (3500 ms)

**Observation 1 — Button label**:
1. Within 100 ms of click, button text becomes `Loading...`

**Observation 2 — Button disabled attribute**:
1. The button has `disabled` set throughout the 3500 ms window
2. Clicking the button five more times produces zero additional `POST /auth/signup` requests

**Observation 3 — Confirmation panel after resolution**:
1. After ~3500 ms the success toast `Account created!` appears
2. The confirmation panel replaces the form only after the response resolves

**API mock**: `POST /auth/signup` → 201 delayed by 3500 ms.

---

### TC-LOADING-002: Double-submit guard records exactly one request

**Action**:
1. Visit `/signup`
2. Fill all required fields validly
3. Click "Create Account" twice in rapid succession (≤ 100 ms apart) against a slow backend

**Observation 1 — Network**:
1. Exactly one `POST /auth/signup` request is recorded

**Observation 2 — UX**:
1. The button enters the loading state on the first click
2. The second click is a no-op (button disabled while `signup.isPending`)

---

### TC-EDGE-001: Already-authenticated visit still renders the form

**Preconditions**: localStorage already has a valid `access_token`.

**Action**:
1. Visit `/signup`

**Observation 1 — Form renders today**:
1. The signup form is in the DOM (no automatic redirect today)
2. All five input fields are empty

> ⚠ When the client-side authed-user redirect ships, this observation must change: the form must NOT render and URL must become `/home`.

---

### TC-EDGE-002: Whitespace-only Organization Name is treated as undefined

**Action**:
1. Visit `/signup`
2. Fill required fields validly
3. Type `   ` (3 spaces) into Organization Name
4. Click "Create Account"

**Observation 1 — Request body omits the org key**:
1. Request body does NOT include `organization_name` (because `'   '.trim() || undefined` evaluates to `undefined`)

**Observation 2 — Confirmation panel renders**:
1. Heading `Check your email` is visible

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-EDGE-003: Email with leading/trailing whitespace is submitted verbatim

**Action**:
1. Visit `/signup`
2. Fill First Name, Last Name, Password
3. Type `  user@acme.com  ` (with spaces) into Email
4. Click "Create Account"

**Observation 1 — Request body**:
1. Request body `email` equals `  user@acme.com  ` (no client-side trim)

**Observation 2 — Backend behaviour**:
1. If backend returns 400 `Invalid email`, toast title equals `Invalid email`
2. Otherwise 201 confirmation panel renders

> ⚠ unverified whether the backend normalises whitespace — document the observed behaviour.

---

### TC-EDGE-004: First name with XSS attempt is treated as plain text

**Action**:
1. Visit `/signup`
2. Type `<script>alert(1)</script>` into First Name
3. Fill remaining required fields validly
4. Click "Create Account"

**Observation 1 — Payload sent verbatim**:
1. Request body `first_name` equals the literal `<script>alert(1)</script>` string

**Observation 2 — DOM is safe**:
1. Confirmation panel renders normally (it shows email, not name)
2. `window.alert` was not invoked
3. No `<script>` element is injected into the DOM

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-EDGE-005: First/last name with emoji is sent verbatim

**Action**:
1. Visit `/signup`
2. Type `Ada 🎉` into First Name
3. Type `Lovelace 💎` into Last Name
4. Fill remaining required fields validly
5. Click "Create Account"

**Observation 1 — Payload includes emoji**:
1. Request body `first_name` equals `Ada 🎉` (UTF-8)
2. Request body `last_name` equals `Lovelace 💎`

**Observation 2 — No UI breakage**:
1. Confirmation panel renders normally

**API mock**: `POST /auth/signup` → 201 success.

---

### TC-EDGE-006: First name with leading/trailing whitespace is sent verbatim

**Action**:
1. Visit `/signup`
2. Type `  Ada  ` into First Name
3. Fill remaining required fields validly
4. Click "Create Account"

**Observation 1 — Payload not trimmed today**:
1. Request body `first_name` equals `  Ada  ` (no client-side trim)

> ⚠ unverified whether the backend trims. Document the observed behaviour; fail loudly if confirmation panel renders ` Ada `.

---

### TC-EDGE-007: Very long first name (> 500 chars) does not crash the form

**Action**:
1. Visit `/signup`
2. Paste a 600-character string into First Name
3. Fill remaining required fields validly
4. Click "Create Account"

**Observation 1 — Input accepts the value**:
1. First Name input value length equals 600
2. No client-side truncation

**Observation 2 — Network behaviour**:
1. `POST /auth/signup` body contains the full 600-char string
2. If backend rejects with 400/422, toast surfaces the `detail`
3. Form stays populated and re-enables

---

### TC-EDGE-008: Paste with newlines into First Name strips the newline

**Action**:
1. Visit `/signup`
2. Paste `Ada\nLovelace` into First Name

**Observation 1 — Single-line input strips newline**:
1. Input value becomes `AdaLovelace` or `Ada Lovelace` depending on browser
2. Zod accepts the non-empty value

---

### TC-EDGE-009: Whitespace-only First Name passes Zod but is sent verbatim

**Action**:
1. Visit `/signup`
2. Type `   ` (3 spaces) into First Name
3. Fill remaining required fields validly
4. Click "Create Account"

**Observation 1 — Zod accepts because length ≥ 1**:
1. No helperText is shown under First Name
2. Exactly one `POST /auth/signup` request is recorded
3. Request body `first_name` equals `   `

> ⚠ Known gap — tighten the schema to `.trim().min(1)` if this is a problem.

---

### TC-EDGE-010: Submit via Enter key in Password field

**Action**:
1. Visit `/signup`
2. Fill all required fields validly
3. Focus the Password input
4. Press the `Enter` key

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/signup` request is recorded
2. The request body matches the typed values

---

### TC-EDGE-011: Browser back from confirmation panel exits /signup

**Preconditions**: TC-HAPPY-001 completed; user is on the confirmation panel.

**Action**:
1. Press the browser Back button

**Observation 1 — URL navigates away**:
1. URL leaves `/signup` (e.g. lands on the previous referrer)
2. URL is NOT pushed to a new history entry by the in-component swap

> ⚠ Verify in test — Next.js does not push history for the in-component swap.

---

### TC-A11Y-001: Tab order through the form

**Action**:
1. Visit `/signup`
2. Focus the First Name input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Tab order matches design**:
1. Focus moves in the order: First Name → Last Name → Email → Organization Name → Password → password Eye toggle → Create Account → "Sign in" link
2. No focusable element is skipped
3. No focusable element is reached twice

---

### TC-A11Y-002: Validation errors are announced to screen readers

**Action**:
1. Visit `/signup`
2. Click "Create Account" with First Name empty

**Observation 1 — Error is announceable**:
1. Helper text under First Name is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `First name is required`

---

### TC-A11Y-003: Loading button announces state via text, not just a spinner

**Action**:
1. Submit a valid payload against a slow backend

**Observation 1 — Button text changes**:
1. The button's accessible name changes from `Create Account` to `Loading...`
2. The button's `disabled` attribute is set (screen reader announces "disabled")

---

### TC-FULL-001: End-to-end signup lifecycle in one test

**Preconditions**: A unique random email `__e2e__signup_<uuid>@example.com` is generated in the test body (NOT mocked). A test backend is available.

**Action**:
1. Visit `/signup` without auth
2. Click "Create Account" with all fields empty
3. Fill First Name, Last Name, Email, Organization Name, and type `7chars` into Password; click "Create Account"
4. Fix Password to a valid 8+ char value; click "Create Account"
5. Click "Back to Login" inside the confirmation panel
6. Press browser Back
7. Click the "Sign in" link below the form (if form re-rendered)
8. Re-visit `/signup`, fill the same email, and submit again

**Observation 1 — Step 2 yields all required-field errors**:
1. Helper text `First name is required` is visible
2. Helper text `Last name is required` is visible
3. Helper text `Email is required` is visible
4. Helper text `Password must be at least 8 characters` is visible

**Observation 2 — Step 3 yields password-length error**:
1. Helper text under Password becomes `Password must be at least 8 characters`

**Observation 3 — Step 4 succeeds**:
1. Toast title equals `Account created!`
2. Toast description equals `Check your email to verify.`
3. Confirmation panel renders with the submitted email in `<strong>`

**Observation 4 — Step 5 navigates to /login**:
1. URL becomes `/login`

**Observation 5 — Step 6 history navigation**:
1. URL becomes `/signup` (re-render today renders the confirmation panel if `signup.isSuccess` persists in component cache; verify and document)

**Observation 6 — Step 7 navigates to /login**:
1. URL becomes `/login`

**Observation 7 — Step 8 duplicate detection**:
1. Toast title equals `Email already registered`

**Cleanup** (in `finally`):
1. Delete the created user (and the auto-created org if any) via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-LOADING-*` test case above)

- [x] Already-authenticated visit still renders the signup form — see TC-EDGE-001
- [x] Empty Organization Name → `?.trim() || undefined` strips it — see TC-HAPPY-002
- [x] Whitespace-only Organization Name (`"   "`) — see TC-EDGE-002
- [x] Email already registered — see TC-ERROR-001 / TC-ERROR-008
- [x] Double submit — see TC-LOADING-002
- [x] Browser back from confirmation panel — see TC-EDGE-011
- [x] Email with leading/trailing whitespace — see TC-EDGE-003
- [x] First/last name with emoji — see TC-EDGE-005
- [x] First name with leading/trailing whitespace — see TC-EDGE-006
- [x] Very long names (>500 chars) — see TC-EDGE-007
- [x] Paste with newlines into single-line input — see TC-EDGE-008
- [x] Whitespace-only First Name passes Zod — see TC-EDGE-009
- [x] Submit via Enter key — see TC-EDGE-010
- [x] XSS attempt in First Name — see TC-EDGE-004
- [ ] Confirmation panel reads `watch('email')` — if email field had been cleared between submit and response (unlikely), rendered email could be blank ⚠ not tested
- [ ] Password contains the user's email — accepted by Zod; backend may or may not reject ⚠ unverified
- [ ] Non-ASCII password chars — accepted verbatim
- [ ] Network failure mid-submit — see TC-ERROR-006
- [ ] Backend returns 201 but `user.is_verified === true` — frontend still shows the "Check your email" panel
- [ ] Suspense — none on this page (no `useSearchParams`); no fallback flash
- [ ] User leaves the page mid-mutation — TanStack Query's `useMutation` finishes in the background; no UI update

---

## Business Rules

- The signup endpoint creates **both** a user and (when `organization_name` is provided) an organization in a single call — the user becomes the `owner` of the new org
- When `organization_name` is omitted, the backend creates a default workspace for the user (or assigns them to an invitation target — ⚠ unverified path for invite-based signup)
- **Email verification is mandatory** before login; the frontend reflects this by showing the "Check your email" panel and never auto-logging the user in
- The verification token returned in the response payload (`email_verification_token`) is a **backend dev leak** — the frontend never reads it (the user receives the same token by email)
- Password minimum length is enforced at 8 characters client-side (Zod); the backend independently enforces the same rule and returns 400 if the client is bypassed
- Tokens (`access_token` / `refresh_token`) in the 201 response are **not persisted** by the signup page — `useSignup` is a plain mutation; only `useLogin` calls `setLoginResponse`
- The user's email is rendered verbatim in the confirmation panel (no normalisation); backend may or may not lowercase it during storage

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order: First Name → Last Name → Email → Organization Name → Password → Create Account → Sign in link — see TC-A11Y-001
- [x] Validation errors render under the input as `helperText` with `aria-live`/`role="alert"` — see TC-A11Y-002
- [x] "Loading..." button text replaces the spinner-only state for screen readers — see TC-A11Y-003
- [ ] All inputs use the shared `TextInput` which renders a `<label>` associated with the input
- [ ] Required indicators are visible to sighted users **and** announced (TextInput adds the required attribute on the underlying input via RHF Controller)
- [ ] The confirmation panel preserves the heading hierarchy: layout `<h1>` then page `<h2>` "Check your email"
- [ ] Toast container has `aria-live="polite"` (Sonner default); error toasts default to 5000 ms
- [ ] The "Sign in" and "Back to Login" links are real anchors (Next.js `<Link>`), keyboard-focusable, with a primary text color and hover underline
- [ ] `MailCheck` icon in the confirmation panel is decorative; the surrounding heading and body text carry the meaning

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. Title and description render in separate elements inside `[data-sonner-toast]`.

| Trigger                                | Toast title                                  | Toast description           | Variant |
| -------------------------------------- | -------------------------------------------- | --------------------------- | ------- |
| Successful signup                      | `Account created!`                           | `Check your email to verify.` | success |
| 400 email already registered           | `Email already registered`                   | —                           | error   |
| 400 missing email/password             | `Email and password are required`            | —                           | error   |
| 400 first_name is required             | `first_name is required`                     | —                           | error   |
| Any 5xx with string `detail`           | (verbatim, e.g. `Internal Server Error`)     | —                           | error   |
| Any error where `detail` is not string | `Something went wrong. Please try again.`    | —                           | error   |
