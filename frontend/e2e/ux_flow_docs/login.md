# Feature Doc: Login

Feature documentation for the `/login` page. Used by `/generate-tests login` (or
`--docs e2e/ux_flow_docs/login.md`) to ensure all positive and negative user cases are
covered alongside the component source analysis.

The login page is the primary entry point for returning users. It exchanges an
email + password for a JWT access token, a refresh token, and a hydrated
`AuthLoginResponse` payload that drives the Zustand `useAuthStore`. The form is
backed by `react-hook-form` + Zod (`loginSchema`) and the mutation is `useLogin()`
from `@tanstack/react-query`.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/login` (under the `(auth)` route group; legacy `/auth/login` callers should arrive here)
- **Component**: `src/app/(auth)/login/page.tsx` (default export `LoginPage` wraps `LoginPageInner` in `<Suspense fallback={null}>`)
- **Layout**: `src/app/(auth)/layout.tsx` — two-column layout (form left, animated branded panel right on `lg:` and up)
- **Auth required**: no — public page
- **Redirect when already authenticated**: not enforced by middleware today; ⚠ unverified — confirm whether a future iteration adds a client-side redirect

---

## User Stories

### US-1: Sign in with email and password

**As a** returning user, **I want to** enter my email and password and submit, **so that** I land on `/home` with my JWT stored and my workspace selected.

**Acceptance criteria**:

- [ ] Heading reads "Welcome back" and the subtitle reads "Enter your credentials to access your account"
- [ ] Email field (`type="email"`, placeholder `you@company.com`) and Password field (`type="password"`, placeholder `••••••••`) render with the required indicator on Email
- [ ] Submit button label is "Sign In" and uses the shadcn primary `Button` (not `CustomButton`)
- [ ] On 200, `setLoginResponse(data)` persists tokens and login_data into localStorage, success toast "Welcome back!" appears, and the router pushes to `/home`
- [ ] If a `?next=/some-path` query param is present and starts with `/`, the redirect goes to `next` instead of `/home`

### US-2: Recover from a "needs email verification" failure

**As a** user whose account is not yet verified, **I want to** be told to verify my email and given a one-click way to resend the verification link, **so that** I can recover without leaving the login page.

**Acceptance criteria**:

- [ ] If the login error `detail` (case-insensitive) contains the word `verify`, a yellow banner renders inside the form
- [ ] Banner has a "Resend verification email" link-button that is disabled when the email field is empty and shows the "Loading..." state while `useResendVerification` is in flight
- [ ] On success, toast "Verification email sent!" appears

### US-3: Sign in with a code instead

**As a** user who prefers passwordless login, **I want to** click "Sign in with a code instead" and be taken to `/sign-in-with-code`.

### US-4: Forgot password and Sign up affordances

**As a** user, **I want to** click "Forgot password?" or "Sign up", **so that** I can recover access or register without leaving the auth area.

### US-5: Block submission on client-side validation errors

**As a** user, **I want to** see field-level errors before I waste a network round-trip.

### US-6: Carry over a deep-link `next` after auth

**As a** user who was kicked out mid-session, **I want to** be returned to the page I was on.

---

## UI Elements

| Element                       | Type            | Content / Label                                  | Behavior                                                      |
| ----------------------------- | --------------- | ------------------------------------------------ | ------------------------------------------------------------- |
| Welcome heading               | h2              | "Welcome back"                                   | Static                                                        |
| Subtitle                      | p               | "Enter your credentials to access your account"  | Static                                                        |
| Email input                   | TextInput       | placeholder "you@company.com"                    | Required, Zod-validated                                       |
| Password label                | label[htmlFor]  | "Password"                                       | Static                                                        |
| Password input                | TextInput (pwd) | placeholder "••••••••" + Eye/EyeOff toggle       | Required (Zod), min 6 chars                                   |
| Remember me checkbox          | Checkbox        | "Remember me"                                    | UI only — value never read; cosmetic                          |
| Forgot password link          | Link            | "Forgot password?"                               | Navigates to `/forgot-password`                               |
| Verify-email banner           | div             | "Please verify your email before logging in."    | Renders only when `needsVerification` is true                 |
| Resend verification button    | Button (link)   | "Resend verification email"                      | Disabled when `!email` or `resend.isPending`                  |
| Sign In button                | Button          | "Sign In" → "Loading..."                         | `type="submit"`; disabled while `login.isPending`             |
| Sign-in-with-code link        | Link            | "Sign in with a code instead"                    | Navigates to `/sign-in-with-code`                             |
| Sign up CTA                   | Link            | "Sign up"                                        | Navigates to `/signup`                                        |

---

## Input Specifications

Source: `src/schemas/auth.ts` (`loginSchema`).

| Field    | Type     | Required | Validation Rules                                                       | Exact Error Message                                  |
| -------- | -------- | -------- | ---------------------------------------------------------------------- | ---------------------------------------------------- |
| Email    | email    | yes      | `z.string().min(1).email()` — non-empty AND well-formed email          | "Email is required" / "Please enter a valid email"   |
| Password | password | yes      | `z.string().min(6)` — length ≥ 6                                       | "Password must be at least 6 characters"             |

**Button state rules:**

- "Sign In" button is **never disabled** by `formState.isValid` — attempting submit with invalid fields surfaces inline errors instead
- While `login.isPending === true`, the `<Button>` renders the loading label ("Loading...") and is `disabled`
- "Resend verification email" link-button is disabled while `!email` OR `resend.isPending`

---

## Navigation

| Trigger                                       | Destination                          | Condition                                  |
| --------------------------------------------- | ------------------------------------ | ------------------------------------------ |
| Successful login (no `?next`)                 | `/home`                              | 200 from `/auth/login`                     |
| Successful login (`?next=/foo`)               | `/foo`                               | `next.startsWith('/')` is true             |
| Successful login (`?next=https://evil.com`)   | `/home`                              | Open-redirect guard                        |
| Click "Forgot password?"                      | `/forgot-password`                   | Always                                     |
| Click "Sign up"                               | `/signup`                            | Always                                     |
| Click "Sign in with a code instead"           | `/sign-in-with-code`                 | Always                                     |

---

## API Contracts

Endpoint base path is `/api/v1` (injected by `src/utils/axios.ts` via `BACKEND_URL`).

| Endpoint                       | Method | Request                                                | Success Response                                                | Error Response                  |
| ------------------------------ | ------ | ------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------- |
| `/auth/login`                  | POST   | `{ "email": string, "password": string }`              | 200 `AuthLoginResponse`                                         | `{ "detail": "..." }`           |
| `/auth/resend-verification`    | POST   | `{ "email": string }`                                  | 200 `{ "message": "..." }`                                      | `{ "detail": "..." }`           |

### Example: `POST /auth/login`

Request body:

```json
{ "email": "owner@acme.com", "password": "hunter22!" }
```

200 OK:

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": "00000000-0000-0000-0000-000000000001", "email": "owner@acme.com", "role": "owner", "is_verified": true },
  "organization": { "id": "00000000-0000-0000-0000-000000000100", "name": "Acme" },
  "role": "owner"
}
```

401 Unauthorized: `{ "detail": "Invalid email or password" }` | `{ "detail": "Account is deactivated" }` | `{ "detail": "Please verify your email before logging in" }`

400 Bad Request: `{ "detail": "Email and password are required" }`

422 Validation Error: `{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }`

State after success is owned by Zustand `useAuthStore.setLoginResponse(data)` (`src/stores/auth.ts`), which writes to localStorage: `access_token`, `refresh_token`, `login_data`, `user_id`, and `active_org_id`.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Sign in with valid credentials lands on /home

**Preconditions**:
- User is signed out (no `access_token` in localStorage)
- Valid backend account `owner@acme.com` / `hunter22!`

**Action**:
1. Visit `/login`
2. Type `owner@acme.com` into the Email input
3. Type `hunter22!` into the Password input
4. Click the "Sign In" button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/login` request is recorded
2. Request body equals `{ "email": "owner@acme.com", "password": "hunter22!" }`
3. Request `Content-Type` header is `application/json`

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

**API mock**: `POST /auth/login` → 200 with the AuthLoginResponse example above.

**Cleanup**: Clear localStorage and cookies in the `afterEach` hook.

---

### TC-HAPPY-002: Sign in with `?next=/agents` lands on /agents

**Preconditions**:
- User is signed out
- Valid backend account

**Action**:
1. Visit `/login?next=/agents`
2. Type a valid email and password
3. Click "Sign In"

**Observation 1 — Network call is unchanged**:
1. `POST /auth/login` body has no `next` field — the redirect is purely client-side

**Observation 2 — Redirect target honours `next`**:
1. URL becomes `/agents` (NOT `/home`) within 1s
2. The agents page renders (its h1 / sidebar item is visible)

**Observation 3 — Toast**:
1. Success toast `Welcome back!` is visible

---

### TC-HAPPY-003: Resend verification email succeeds after a 401 verify error

**Preconditions**:
- TC-ERROR-003 has just run, so the yellow verify-email banner is visible and the Email field still contains `unverified@acme.com`

**Action**:
1. Click the "Resend verification email" link-button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/resend-verification` request is recorded
2. Request body equals `{ "email": "unverified@acme.com" }`

**Observation 2 — Loading state on the link-button**:
1. The link-button text becomes "Loading..."
2. The link-button has the `disabled` attribute while the request is in flight

**Observation 3 — Success toast**:
1. A Sonner toast appears with title `Verification email sent!`
2. The yellow banner remains visible (it is not auto-dismissed)

**API mock**: `POST /auth/resend-verification` → 200 `{ "message": "If the email exists, a verification link has been sent" }`.

---

### TC-VALIDATE-001: Empty Email blocks submit with inline error

**Preconditions**: Login form visible; both fields blank.

**Action**:
1. Visit `/login`
2. Leave both fields empty
3. Click "Sign In"

**Observation 1 — No network call fires**:
1. Zero `POST /auth/login` requests are recorded
2. Zero `POST /auth/resend-verification` requests are recorded

**Observation 2 — Inline error appears under Email**:
1. Helper text under the Email input reads exactly `Email is required`
2. Email input has the error styling (border-destructive)
3. Email input receives focus

**Observation 3 — Form state is preserved**:
1. URL is still `/login`
2. No toast is shown

---

### TC-VALIDATE-002: Malformed email blocks submit

**Action**:
1. Visit `/login`
2. Type `not-an-email` into Email
3. Type `hunter22!` into Password
4. Click "Sign In"

**Observation 1 — No network call**:
1. Zero `POST /auth/login` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

---

### TC-VALIDATE-003: Short password (< 6 chars) blocks submit

**Action**:
1. Visit `/login`
2. Type a valid email
3. Type `12345` (5 chars) into Password
4. Click "Sign In"

**Observation 1 — No network call**:
1. Zero `POST /auth/login` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Password reads exactly `Password must be at least 6 characters`

---

### TC-ERROR-001: 401 invalid credentials surfaces toast

**Action**:
1. Visit `/login`
2. Type a valid-format email and password
3. Click "Sign In"

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/login` is recorded

**Observation 2 — Error toast**:
1. Toast title equals `Invalid email or password`
2. Toast variant is `error`

**Observation 3 — Form state**:
1. Email and Password inputs retain their values (form is not cleared)
2. "Sign In" button re-enables (no longer shows "Loading...")
3. URL is still `/login`

**API mock**: `POST /auth/login` → 401 `{ "detail": "Invalid email or password" }`.

---

### TC-ERROR-002: 401 deactivated account surfaces toast (no verify banner)

**Action**:
1. Visit `/login`
2. Submit valid-format credentials for a disabled account

**Observation 1 — Error toast**:
1. Toast title equals `Account is deactivated`

**Observation 2 — No verify banner**:
1. The yellow "Please verify your email before logging in." banner is NOT in the DOM
2. The "Resend verification email" link-button is NOT in the DOM

**API mock**: `POST /auth/login` → 401 `{ "detail": "Account is deactivated" }`.

---

### TC-ERROR-003: 401 email-not-verified surfaces toast and yellow banner

**Action**:
1. Visit `/login`
2. Type `unverified@acme.com` into Email
3. Type a valid-format password
4. Click "Sign In"

**Observation 1 — Error toast**:
1. Toast title equals `Please verify your email before logging in`

**Observation 2 — Yellow banner appears**:
1. A yellow banner is visible inside the form, below the Password field
2. Banner contains a "Resend verification email" link-button
3. The link-button is enabled (because Email is non-empty)

**API mock**: `POST /auth/login` → 401 `{ "detail": "Please verify your email before logging in" }`.

---

### TC-ERROR-004: 422 with non-string `detail` falls back to generic toast

**Action**:
1. Submit valid-format credentials

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`
2. Toast variant is `error`

**API mock**: `POST /auth/login` → 422 `{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }`.

---

### TC-ERROR-005: 500 surfaces the verbatim string `detail`

**Action**:
1. Submit valid-format credentials

**Observation 1 — Error toast**:
1. Toast title equals `Internal Server Error`

**API mock**: `POST /auth/login` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-006: Network failure shows generic fallback toast

**Action**:
1. Submit valid-format credentials

**Observation 1 — Error toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form state**:
1. Email and Password are still populated
2. "Sign In" button re-enables

**API mock**: route aborted with `failed` status (no response object).

---

### TC-ERROR-007: Resend verification 400 "already verified"

**Preconditions**: yellow banner visible (TC-ERROR-003 ran).

**Action**:
1. Click "Resend verification email"

**Observation 1 — Error toast**:
1. Toast title equals `Email is already verified`

**Observation 2 — Banner persists**:
1. The yellow banner is still in the DOM after the toast appears

**API mock**: `POST /auth/resend-verification` → 400 `{ "detail": "Email is already verified" }`.

---

### TC-NAV-001: Click "Forgot password?" navigates client-side

**Action**:
1. Visit `/login`
2. Click "Forgot password?"

**Observation 1 — URL change**:
1. URL becomes `/forgot-password`

**Observation 2 — No network call**:
1. Zero `POST /auth/login` requests are recorded
2. No full page reload occurs (client-side `<Link>`)

---

### TC-NAV-002: Click "Sign up" navigates client-side

**Action**:
1. Visit `/login`
2. Click the "Sign up" link below the form

**Observation 1 — URL change**: URL becomes `/signup`.

**Observation 2 — No reload**: no full page reload occurs.

---

### TC-NAV-003: Click "Sign in with a code instead" navigates client-side

**Action**:
1. Visit `/login`
2. Click "Sign in with a code instead"

**Observation 1 — URL change**: URL becomes `/sign-in-with-code`.

---

### TC-NAV-004: Open-redirect guard ignores `?next=https://evil.com`

**Action**:
1. Visit `/login?next=https://evil.com`
2. Submit valid creds

**Observation 1 — Redirect falls back to /home**:
1. URL becomes `/home` (NOT `https://evil.com`)
2. No navigation event targets an external origin

**API mock**: `POST /auth/login` → 200 success.

---

### TC-NAV-005: Browser back from /home after login

**Preconditions**: TC-HAPPY-001 just completed and URL is `/home`.

**Action**:
1. Press the browser Back button

**Observation 1 — History navigation**:
1. URL becomes `/login`

**Observation 2 — Login form re-renders**:
1. The Email and Password inputs are present and empty (no auto-fill from session)

> ⚠ When the client-side authed-user redirect ships, update this observation: a logged-in user on `/login` should be sent back to `/home`.

---

### TC-LOADING-001: Sign In button shows loading state during slow API

**Action**:
1. Visit `/login`
2. Submit valid creds against a deliberately slow backend (3500 ms)

**Observation 1 — Button label**:
1. Within 100 ms of click, button text becomes `Loading...`

**Observation 2 — Button disabled attribute**:
1. The button has `disabled` set throughout the 3500 ms window
2. Clicking the button five more times produces zero additional `POST /auth/login` requests

**Observation 3 — Success after resolution**:
1. After ~3500 ms the success toast `Welcome back!` appears
2. URL becomes `/home`

**API mock**: `POST /auth/login` → 200 delayed by 3500 ms.

---

### TC-LOADING-002: Double-submit guard records exactly one request

**Action**:
1. Visit `/login`
2. Fill valid creds
3. Click "Sign In" twice in rapid succession (≤ 100 ms apart)

**Observation 1 — Network**:
1. Exactly one `POST /auth/login` request is recorded

**Observation 2 — UX**:
1. The button enters the loading state on the first click
2. The second click is a no-op

---

### TC-EDGE-001: Email with leading/trailing whitespace is submitted verbatim

**Action**:
1. Type `  user@acme.com  ` (with spaces) into Email
2. Type a valid password
3. Click "Sign In"

**Observation 1 — Request body**:
1. `POST /auth/login` body equals `{ "email": "  user@acme.com  ", "password": "..." }` (no client-side trim)

**Observation 2 — Backend rejection surfaces**:
1. If backend returns 401, toast title equals `Invalid email or password`

> ⚠ unverified whether the backend normalises whitespace — document the current behaviour and update if normalisation is added.

---

### TC-EDGE-002: Emoji / unicode in password is sent verbatim

**Action**:
1. Type a valid email
2. Type `pass🔥word` (8 chars including emoji) into Password
3. Click "Sign In"

**Observation 1 — Request body**:
1. `POST /auth/login` body password field equals the literal `pass🔥word` (UTF-8, not URL-encoded)

**Observation 2 — Login succeeds**:
1. Success toast appears
2. URL becomes `/home`

**API mock**: `POST /auth/login` → 200.

---

### TC-EDGE-003: Very long password (> 500 chars) does not crash the form

**Action**:
1. Type a valid email
2. Paste a 600-character password
3. Click "Sign In"

**Observation 1 — Input accepts the value**:
1. Password input value length equals 600
2. No client-side truncation

**Observation 2 — Network request**:
1. `POST /auth/login` body contains the full 600-char password

**Observation 3 — Form remains responsive after backend reply**:
1. After backend 401, form is still interactable; toast surfaces the `detail`

---

### TC-EDGE-004: XSS attempt in Email is treated as plain text

**Action**:
1. Type `<script>alert(1)</script>@x.com` into Email
2. Type a valid password
3. Click "Sign In"

**Observation 1 — Zod rejects**:
1. Helper text under Email reads `Please enter a valid email`
2. Zero `POST /auth/login` requests are recorded

**Observation 2 — DOM is safe**:
1. The literal `<script>` text appears as the input's `value` attribute (rendered as text, not HTML)
2. `window.alert` was not invoked

---

### TC-EDGE-005: Submit via Enter key in Password field

**Action**:
1. Fill valid Email and Password
2. Focus the Password input
3. Press the `Enter` key

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/login` request is recorded
2. The request body matches the typed values

---

### TC-EDGE-006: Token already in localStorage when visiting /login

**Preconditions**: localStorage already has a valid `access_token` and `login_data`.

**Action**:
1. Visit `/login`

**Observation 1 — Form still renders today**:
1. The login form is in the DOM (no automatic redirect today)
2. Email and Password inputs are empty

> ⚠ When the client-side authed-user redirect ships, this observation must change: the form must NOT render and URL must become `/home`.

---

### TC-A11Y-001: Tab order through the form

**Action**:
1. Visit `/login`
2. Focus the Email input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Tab order matches design**:
1. Focus moves in the order: Email → Password → password-Eye toggle → Remember me → Forgot password → Sign In → "Sign in with a code instead" → "Sign up"
2. No focusable element is skipped
3. No focusable element is reached twice

---

### TC-A11Y-002: Validation errors are announced to screen readers

**Action**:
1. Visit `/login`
2. Click "Sign In" with both fields empty

**Observation 1 — Email error is announceable**:
1. Helper text under Email is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `Email is required`

**Observation 2 — Password error is announceable**:
1. Helper text under Password is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `Password must be at least 6 characters`

---

### TC-A11Y-003: Loading button announces state via text, not just a spinner

**Action**:
1. Submit valid creds against a slow backend

**Observation 1 — Button text changes**:
1. The button's accessible name changes from `Sign In` to `Loading...`
2. The button's `disabled` attribute is set (screen reader announces "disabled")

---

### TC-A11Y-004: Password input is associated with its label

**Action**:
1. Visit `/login`
2. Inspect the Password input and its label

**Observation 1 — Programmatic association**:
1. `<label htmlFor="password">Password</label>` is present
2. The password input has `id="password"` and `name="password"`
3. Clicking the label moves focus to the input

---

### TC-FULL-001: End-to-end login lifecycle in one test

**Preconditions**: A test user `__e2e__login_<uuid>@example.com` is provisioned via a backend admin API call inside the test (NOT mocked).

**Action**:
1. Visit `/login` without auth cookie
2. Click "Sign In" with both fields empty
3. Type `not-an-email` and click "Sign In"
4. Type a valid email and `12345` (5 chars) into Password and click "Sign In"
5. Type the test user's email and a wrong password and click "Sign In"
6. Type the test user's correct password and click "Sign In"
7. After landing on `/home`, press browser Back
8. Click "Forgot password?", then browser Back
9. Click "Sign in with a code instead", then browser Back
10. Click "Sign up"

**Observation 1 — Step 2 yields both inline errors**:
1. Helper text `Email is required` is visible
2. Helper text `Password must be at least 6 characters` is visible

**Observation 2 — Step 3 yields email-format error**:
1. Helper text under Email becomes `Please enter a valid email`

**Observation 3 — Step 4 yields password-length error**:
1. Helper text under Password becomes `Password must be at least 6 characters`

**Observation 4 — Step 5 yields 401 toast**:
1. Toast title equals `Invalid email or password`
2. Form remains populated

**Observation 5 — Step 6 succeeds**:
1. Toast title equals `Welcome back!`
2. URL becomes `/home`
3. `localStorage.access_token` is set

**Observation 6 — Step 7 returns to /login**:
1. URL is `/login`

**Observation 7 — Step 8 visits and returns**:
1. URL goes to `/forgot-password` then back to `/login`

**Observation 8 — Step 9 visits and returns**:
1. URL goes to `/sign-in-with-code` then back to `/login`

**Observation 9 — Step 10 visits signup**:
1. URL becomes `/signup`

**Cleanup** (in `finally`):
1. Delete the test user via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above)

- [x] Token already in localStorage when visiting `/login` — see TC-EDGE-006
- [x] `?next` does not start with `/` — see TC-NAV-004
- [x] Email field with leading/trailing whitespace — see TC-EDGE-001
- [x] Emoji / unicode in password — see TC-EDGE-002
- [x] Very long password (> 500 chars) — see TC-EDGE-003
- [x] XSS in email input — see TC-EDGE-004
- [x] Submit via Enter key — see TC-EDGE-005
- [x] Double-submit / rapid clicking — see TC-LOADING-002

---

## Business Rules

- Login is **public**; no auth header is sent on the request itself
- Successful login overwrites any existing `access_token` / `refresh_token` / `login_data` / `active_org_id` in localStorage with the fresh response — there is no merge step
- The selected organization after login is `data.organization.id` (preferred) or the first entry in `data.organizations[]` (fallback)
- Email verification is gated by the backend; the frontend never decides locally whether the account is verified
- The "Remember me" checkbox is currently **cosmetic** — toggling it does not change cookie/localStorage lifetimes
- The login endpoint never returns a 403; deactivated and unverified are both 401s with distinct `detail` strings, and the frontend branches on the substring `verify` to show the yellow banner

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order is Email → Password → eye-toggle → Remember me → Forgot password → Sign In → code-instead → Sign up — see TC-A11Y-001
- [x] Validation errors are announced via `role="alert"` / `aria-live` — see TC-A11Y-002
- [x] Loading state announced via visible text "Loading..." — see TC-A11Y-003
- [x] Password input is programmatically associated with its label — see TC-A11Y-004

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. `handleApiError` passes the backend `response.data.detail` string as the toast **title** (no description). When `detail` is not a string, it uses the title `Something went wrong. Please try again.`.

| Trigger                                          | Toast title                                            | Variant |
| ------------------------------------------------ | ------------------------------------------------------ | ------- |
| Successful login                                 | `Welcome back!`                                        | success |
| Resend verification succeeds                     | `Verification email sent!`                             | success |
| 401 invalid credentials                          | `Invalid email or password`                            | error   |
| 401 account deactivated                          | `Account is deactivated`                               | error   |
| 401 email not verified                           | `Please verify your email before logging in`           | error   |
| 400 missing fields                               | `Email and password are required`                      | error   |
| 5xx with string `detail`                         | (verbatim `detail`)                                    | error   |
| Any error where `detail` is not a string         | `Something went wrong. Please try again.`              | error   |
