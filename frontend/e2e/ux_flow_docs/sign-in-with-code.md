# Feature Doc: Sign in with Code

Feature documentation for the password-less "sign in with code" page. Used by
`/generate-tests sign-in-with-code` (or `--docs e2e/ux_flow_docs/sign-in-with-code.md`)
to ensure both happy-path and error scenarios are covered alongside the
component source analysis.

Sign-in-with-code is a **two-step** flow:

1. **Request step** — the user types their email; the page calls
   `POST /auth/signin-code/request` and (regardless of whether the email exists)
   shows a generic toast and advances to step 2.
2. **Verify step** — the user types the 6-digit code emailed to them; the page
   calls `POST /auth/signin-code/verify` and on success hydrates the auth store
   and redirects to `next` (if safe) or `/home`.

The verify step also exposes a **resend** action with a 60-second cooldown.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/sign-in-with-code` (optional `?next=<safe-redirect-path>`)
- **Component**: `src/app/(auth)/sign-in-with-code/page.tsx`
- **Inner components** (same file): `RequestStep`, `VerifyStep`, `SignInWithCodeInner`
- **Layout**: `src/app/(auth)/layout.tsx` (shared auth split-screen with `Logo`,
  `ThemeToggle`, and the branded right panel)
- **Suspense wrapper**: yes — outer `SignInWithCodePage` wraps the inner
  `SignInWithCodeInner` in `<Suspense fallback={null}>` because `VerifyStep`
  reads `useSearchParams()` for the `next` query param
- **Auth required**: no — this is a public page
- **API hooks** (from `@/lib/api/auth`):
  - `useRequestSignInCode()` → `POST /auth/signin-code/request`
  - `useVerifySignInCode()` → `POST /auth/signin-code/verify`
- **Auth store**: `useAuthStore.setLoginResponse(data)` (Zustand store at
  `src/stores/auth.ts`) is called on successful verify to write
  `tone_access_token`, `org_tenant_id`, and `login_data` to localStorage

---

## User Stories

### US-1: Request a sign-in code

**As a** returning user, **I want to** request a one-time code by email,
**so that** I can sign in without remembering my password.

**Acceptance criteria**:

- [ ] Page heading shows "Sign in with a code" with subtitle
      "We'll email you a 6-digit code to sign in. No password needed."
      (`SIGNIN_CODE_LENGTH = 6` from `src/schemas/auth.ts`)
- [ ] Email input is required, validated by Zod (`requestSignInCodeSchema`):
      `'Email is required'` / `'Please enter a valid email'`
- [ ] Submit button reads "Send code"; on click → `requestCode.isPending`
      flips the button to loading state (disabled, spinner)
- [ ] Regardless of whether the email exists, a generic success toast appears:
      `"If the email exists, a code has been sent"`
- [ ] On success, the inner state advances to `VerifyStep` (email stored in
      `email` state, passed to `<VerifyStep email={email} />`)
- [ ] A "Sign in with password instead" link below the form navigates to `/login`

### US-2: Enter and submit the 6-digit code

**As a** user who received the code email, **I want to** type the 6-digit code
and sign in, **so that** I'm taken to my dashboard.

**Acceptance criteria**:

- [ ] Heading shows "Enter your code" with subtitle
      "We sent a 6-digit code to **{email}**. It expires in 10 minutes."
- [ ] Code input has `inputMode="numeric"`, `autoComplete="one-time-code"`,
      `maxLength={6}`, label `"6-digit code"`, placeholder `"123456"`
- [ ] `onValueChange` strips non-digits and slices to length 6
      (`digitsOnly(raw) = raw.replace(/\D/g, '').slice(0, 6)`)
- [ ] Zod schema (`verifySignInCodeSchema`) requires `^\d{6}$` →
      error `'Enter the 6-digit code'` for any other length/shape
- [ ] Submit button reads "Verify and sign in"; while pending it is disabled
      and shows the spinner
- [ ] On 200: `setLoginResponse(data)` writes localStorage; success toast
      `"Welcome back!"` (Sonner default 3s); `router.push(safeNext)`
- [ ] `safeNext = nextPath && nextPath.startsWith('/') ? nextPath : '/home'`
      — external URLs and protocol-relative URLs are blocked

### US-3: Resend the code with a cooldown

**As a** user who didn't receive the code, **I want to** resend it, **so that**
I can try again without re-typing my email.

**Acceptance criteria**:

- [ ] Resend link reads `"Resend in {resendIn}s"` when `resendIn > 0` and
      `"Resend code"` when `resendIn === 0`
- [ ] Initial value of `resendIn` is `60` (`RESEND_COOLDOWN_SECONDS`); a 1-second
      interval decrements it via `setTimeout` (recursive) until it reaches `0`
- [ ] Clicking the resend link while `resendIn > 0` early-returns (no API call)
- [ ] Clicking while `resendIn === 0`:
      1. Re-fires `POST /auth/signin-code/request` with the same email
      2. Resets `resendIn = 60`
      3. Clears the code field (`setValue('code', '')`)
      4. Shows success toast `"A new code has been sent"`
- [ ] The resend `Button` is `disabled` while `resendIn > 0` OR while
      `requestCode.isPending`; while pending it also renders the spinner

### US-4: Back to email entry

**As a** user who typed the wrong email, **I want to** go back, **so that** I
can correct it.

**Acceptance criteria**:

- [ ] A "Use a different email" `Button` (variant=link) with an `ArrowLeft`
      icon resets `email` state to `''` via `onBack()`
- [ ] `SignInWithCodeInner` re-renders `RequestStep` (because `email` is
      now empty) with a blank form (the previous form state is unmounted)

### US-5: Auth gating

**As an** unauthenticated visitor, **I want to** access `/sign-in-with-code`
directly, **so that** I can sign in without a password.

**Acceptance criteria**:

- [ ] The route group `(auth)` does not enforce a token; the page is reachable
      without `tone_access_token`
- [ ] Already-logged-in users hitting `/sign-in-with-code` still see the form
      (no auto-redirect to `/home`)

---

## Input Specifications

Source: `src/schemas/auth.ts` (Zod `requestSignInCodeSchema`,
`verifySignInCodeSchema`, `SIGNIN_CODE_LENGTH = 6`).

### Request step

| Field | Type   | Required | Validation Rules                                                  | Exact Error Message                                            |
| ----- | ------ | -------- | ----------------------------------------------------------------- | -------------------------------------------------------------- |
| email | email  | yes      | `z.string().min(1).email()`                                       | `Email is required` (empty) / `Please enter a valid email` (invalid format) |

### Verify step

| Field | Type   | Required | Validation Rules                                                  | Exact Error Message                                            |
| ----- | ------ | -------- | ----------------------------------------------------------------- | -------------------------------------------------------------- |
| code  | text   | yes      | `z.string().min(1).regex(/^\d{6}$/)`; `inputMode="numeric"`, `maxLength={6}`, `autoComplete="one-time-code"`; `onValueChange` strips non-digits and clamps to 6 | `Code is required` (empty) / `Enter the 6-digit code` (any other shape) |

**Button state rules:**

- "Send code" button is **disabled with spinner** while `requestCode.isPending`.
- "Verify and sign in" button is **disabled with spinner** while `verifyCode.isPending`.
- Resend `Button` is **disabled** when `resendIn > 0 || requestCode.isPending`.

---

## UI Elements

| Element                          | Type                  | Content / Label                                                                              | Behavior                                                                          |
| -------------------------------- | --------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Request heading                  | `<h2>`                | "Sign in with a code"                                                                        | Static                                                                            |
| Request subtitle                 | `<p>`                 | "We'll email you a 6-digit code to sign in. No password needed."                             | Uses `SIGNIN_CODE_LENGTH` template literal                                        |
| Email input                      | `TextInput`           | label "Email", placeholder "you@company.com", `isRequired`, `type="email"`                   | Bound to RHF via `control`                                                        |
| Send code button                 | `Button`              | "Send code", `type="submit"`, `className="w-full"`                                            | `loading={requestCode.isPending}`; disabled + spinner while pending                |
| Sign in with password link       | `<Link>`              | "Sign in with password instead", `href="/login"`                                              | Next.js `Link`                                                                    |
| Verify heading                   | `<h2>`                | "Enter your code"                                                                            | Static                                                                            |
| Verify subtitle                  | `<p>`                 | "We sent a 6-digit code to **{email}**. It expires in 10 minutes."                            | `email` rendered in `<strong>`                                                    |
| Code input                       | `TextInput`           | label "6-digit code", placeholder "123456", `inputMode="numeric"`, `autoComplete="one-time-code"`, `maxLength={6}`, `isRequired` | `onValueChange` strips non-digits and slices to 6                                  |
| Verify and sign in button        | `Button`              | "Verify and sign in", `type="submit"`, `className="w-full"`                                   | `loading={verifyCode.isPending}`                                                  |
| Use a different email link       | `Button` (variant=link) | text "Use a different email" with `ArrowLeft` icon                                          | Calls `onBack()` → resets `email` to `''` in parent                                |
| Resend link                      | `Button` (variant=link) | "Resend in {resendIn}s" or "Resend code"                                                    | `disabled={resendIn > 0 || requestCode.isPending}`; `loading={requestCode.isPending}` |
| Form wrapper                     | `Form`                | from `@/components/shared`                                                                   | Renders a native `<form>` with `onSubmit={handleSubmit(onSubmit)}`                  |
| Animated step transitions        | `framer-motion`       | `fadeUp` variants on heading, inputs, and buttons                                            | Slight Y-axis fade-in on each step's mount                                         |

---

## Navigation

| Trigger                                       | Destination                                                                       | Condition                                          |
| --------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------- |
| Successful verify                             | `safeNext` (= `next` if it starts with `/`) else `/home`                          | Always                                             |
| Click "Sign in with password instead"         | `/login`                                                                          | Always                                             |
| Click "Use a different email"                 | stays on `/sign-in-with-code` — inner state reverts to `RequestStep`               | Always                                             |
| Click "Send code" (success)                   | stays on `/sign-in-with-code` — inner state advances to `VerifyStep`              | Always                                             |
| Click "Resend code"                           | stays on `/sign-in-with-code`; only re-requests the code                          | `resendIn === 0` and request not in flight         |
| Logo / ThemeToggle (in layout header)         | Various                                                                          | Layout-level                                        |

---

## API Contracts

Real payloads sourced from
`/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json`
(folder: `Authentication → POST /auth/signin-code/request` and
`POST /auth/signin-code/verify`).

| Endpoint                            | Method | Request                                                  | Success Response                                                                                                                                                                                                                            | Error Response                                                                                       |
| ----------------------------------- | ------ | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `/api/v1/auth/signin-code/request`  | POST   | `{ "email": "owner@acme.com" }`                          | 200: `{ "message": "Sign-in code sent" }`                                                                                                                                                                                                   | 400: `{ "detail": "email is required" }` / 429: `{ "detail": "Too many requests. Try again later." }` |
| `/api/v1/auth/signin-code/verify`   | POST   | `{ "email": "owner@acme.com", "code": "123456" }`        | 200: `AuthLoginResponse` (see example below)                                                                                                                                                                                                | 400: `{ "detail": "Invalid code" }` / 401: `{ "detail": "Invalid or expired code" }`                |

### Example: `POST /auth/signin-code/request` (success)

Request body:

```json
{ "email": "owner@acme.com" }
```

200 OK response body:

```json
{ "message": "Sign-in code sent" }
```

400 Bad Request:

```json
{ "detail": "email is required" }
```

### Example: `POST /auth/signin-code/verify` (success)

Request body:

```json
{
  "email": "owner@acme.com",
  "code": "123456"
}
```

200 OK response body:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9.refresh.signature",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "8c7a8b50-9d0a-4d63-9b3c-1a2b3c4d5e6f",
    "email": "owner@acme.com",
    "first_name": "Ann",
    "last_name": "Acme",
    "role": "owner",
    "is_verified": true
  },
  "organization": {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "Acme"
  }
}
```

401 Unauthorized:

```json
{ "detail": "Invalid or expired code" }
```

400 Bad Request — wrong code:

```json
{ "detail": "Invalid code" }
```

State writes on success: `useAuthStore.setLoginResponse(data)` parses the
response and writes `localStorage` keys `tone_access_token` (= `access_token`),
`org_tenant_id` (= `organization.id`), `login_data` (= JSON of the entire
response), plus updates the in-memory `authAtom`-equivalent zustand slice.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Request → verify → land on /home

**Preconditions**:
- User is signed out (no `tone_access_token` in localStorage)
- Valid backend account `owner@acme.com`

**Action**:
1. Visit `/sign-in-with-code`
2. Type `owner@acme.com` into the Email input
3. Click "Send code"
4. Type `123456` into the 6-digit code input
5. Click "Verify and sign in"

**Observation 1 — Request step network call**:
1. Exactly one `POST /auth/signin-code/request` request is recorded
2. Request body equals `{ "email": "owner@acme.com" }`

**Observation 2 — Step advances to VerifyStep**:
1. Heading text changes to `Enter your code`
2. Subtitle contains `owner@acme.com` rendered in `<strong>`
3. Resend link reads `Resend in 60s` and is disabled

**Observation 3 — Generic success toast on request**:
1. Toast title equals `If the email exists, a code has been sent`

**Observation 4 — Verify step network call**:
1. Exactly one `POST /auth/signin-code/verify` request is recorded
2. Request body equals `{ "email": "owner@acme.com", "code": "123456" }`

**Observation 5 — Local storage hydration on 200**:
1. `localStorage.tone_access_token` equals the response `access_token`
2. `localStorage.org_tenant_id` equals the response `organization.id`
3. `localStorage.login_data` is valid JSON containing `user.id`

**Observation 6 — Redirect + welcome toast**:
1. URL becomes `/home` within 1s
2. Toast title equals `Welcome back!`

**API mocks**:
- `POST /auth/signin-code/request` → 200 `{ "message": "Sign-in code sent" }`
- `POST /auth/signin-code/verify` → 200 with the AuthLoginResponse example above

**Cleanup**: Clear localStorage and cookies in the `afterEach` hook.

---

### TC-HAPPY-002: `?next=/agents/abc` redirects to /agents/abc on success

**Preconditions**:
- User is signed out
- Valid backend account

**Action**:
1. Visit `/sign-in-with-code?next=/agents/abc`
2. Submit a valid email
3. Submit `123456` as the code

**Observation 1 — Redirect honours `next`**:
1. URL becomes `/agents/abc` (NOT `/home`) within 1s

**Observation 2 — Welcome toast still appears**:
1. Toast title equals `Welcome back!`

**API mocks**: same as TC-HAPPY-001.

---

### TC-HAPPY-003: Resend after cooldown succeeds

**Preconditions**:
- TC-HAPPY-001 step 3 just completed; user is on `VerifyStep`
- Test fast-forwards (or waits) 60 seconds until `resendIn === 0`

**Action**:
1. Click the "Resend code" link

**Observation 1 — Network request**:
1. Exactly one new `POST /auth/signin-code/request` request is recorded
2. Request body equals `{ "email": "owner@acme.com" }`

**Observation 2 — UI resets**:
1. Code field is cleared (value is `""`)
2. Resend link returns to `Resend in 60s` and is disabled

**Observation 3 — Success toast**:
1. Toast title equals `A new code has been sent`

**API mock**: `POST /auth/signin-code/request` → 200.

---

### TC-HAPPY-004: "Use a different email" returns to RequestStep blank

**Preconditions**:
- TC-HAPPY-001 step 3 just completed; user is on `VerifyStep`

**Action**:
1. Click the "Use a different email" link-button

**Observation 1 — Step reverts**:
1. Heading text changes back to `Sign in with a code`
2. Email input is rendered and empty

**Observation 2 — No API call**:
1. Zero additional `POST /auth/signin-code/request` requests are recorded

**Observation 3 — Resend timer cleaned up**:
1. No setState-on-unmounted warnings appear (`clearTimeout` runs in cleanup)

---

### TC-NAV-001: Click "Sign in with password instead" navigates to /login

**Action**:
1. Visit `/sign-in-with-code`
2. Click the "Sign in with password instead" link

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No reload**:
1. No full page reload occurs (Next.js `<Link>`)

---

### TC-VALIDATE-001: Empty email blocks submit on RequestStep

**Action**:
1. Visit `/sign-in-with-code`
2. Leave email empty
3. Click "Send code"

**Observation 1 — No network call**:
1. Zero `POST /auth/signin-code/request` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Email is required`

**Observation 3 — Step did not advance**:
1. Heading remains `Sign in with a code`

---

### TC-VALIDATE-002: Malformed email blocks submit

**Action**:
1. Visit `/sign-in-with-code`
2. Type `not-an-email` into Email
3. Click "Send code"

**Observation 1 — No network call**:
1. Zero `POST /auth/signin-code/request` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

---

### TC-VALIDATE-003: Empty code blocks submit on VerifyStep

**Preconditions**:
- User is on `VerifyStep` (TC-HAPPY-001 steps 1-3 ran)

**Action**:
1. Leave code empty
2. Click "Verify and sign in"

**Observation 1 — No network call**:
1. Zero `POST /auth/signin-code/verify` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under code reads exactly `Code is required`

---

### TC-VALIDATE-004: Wrong-length code (5 digits) blocks submit

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Type `12345` into the code input
2. Click "Verify and sign in"

**Observation 1 — No network call**:
1. Zero `POST /auth/signin-code/verify` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under code reads exactly `Enter the 6-digit code`

---

### TC-VALIDATE-005: Non-numeric paste leaves the field empty

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Paste `abcdef` into the code input
2. Click "Verify and sign in"

**Observation 1 — onValueChange strips alphas**:
1. The code input value is `""`

**Observation 2 — Empty-code error**:
1. Helper text under code reads exactly `Code is required`
2. Zero `POST /auth/signin-code/verify` requests are recorded

---

### TC-ERROR-001: Request 400 "email is required" surfaces toast

**Preconditions**:
- Somehow the body lacks `email` (manual fetch / dev tools)

**Action**:
1. Submit a valid email on RequestStep

**Observation 1 — Error toast via handleApiError**:
1. Toast title equals `email is required`

**Observation 2 — Step does not advance**:
1. Heading remains `Sign in with a code`

**API mock**: `POST /auth/signin-code/request` → 400 `{ "detail": "email is required" }`.

---

### TC-ERROR-002: Request 429 rate-limit surfaces toast

**Action**:
1. Submit a valid email

**Observation 1 — Error toast**:
1. Toast title equals `Too many requests. Try again later.`

**Observation 2 — Stay on RequestStep**:
1. Heading remains `Sign in with a code`

**API mock**: `POST /auth/signin-code/request` → 429 `{ "detail": "Too many requests. Try again later." }`.

---

### TC-ERROR-003: Verify 401 invalid/expired code shows toast and keeps value

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Type `999999` as the code
2. Click "Verify and sign in"

**Observation 1 — Error toast**:
1. Toast title equals `Invalid or expired code`

**Observation 2 — Code field retains value**:
1. The code input value is still `999999` (no auto-clear)

**Observation 3 — Stay on VerifyStep**:
1. Heading remains `Enter your code`

**API mock**: `POST /auth/signin-code/verify` → 401 `{ "detail": "Invalid or expired code" }`.

---

### TC-ERROR-004: Verify 400 wrong code shows toast

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Submit `123456`

**Observation 1 — Error toast**:
1. Toast title equals `Invalid code`

**Observation 2 — Stay on VerifyStep**:
1. Heading remains `Enter your code`

**API mock**: `POST /auth/signin-code/verify` → 400 `{ "detail": "Invalid code" }`.

---

### TC-ERROR-005: Verify 422 with array `detail` falls back to generic toast

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Submit `123456`

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`

**API mock**: `POST /auth/signin-code/verify` → 422 `{ "detail": [{ "type": "missing", "loc": ["body", "code"], "msg": "Field required", "input": {} }] }`.

---

### TC-ERROR-006: Verify 500 surfaces verbatim string

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Submit `123456`

**Observation 1 — Error toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Stay on VerifyStep**:
1. Heading remains `Enter your code`

**API mock**: `POST /auth/signin-code/verify` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-007: Resend during cooldown is a no-op

**Preconditions**:
- User is on `VerifyStep`; `resendIn = 30`

**Action**:
1. Click the resend link

**Observation 1 — No network call**:
1. Zero new `POST /auth/signin-code/request` requests are recorded
2. The `Button` is `disabled` and handler early-returns

**Observation 2 — Label unchanged**:
1. Resend link still reads `Resend in 30s`

---

### TC-ERROR-008: Resend backend error leaves cooldown unchanged

**Preconditions**:
- User is on `VerifyStep`; `resendIn === 0`

**Action**:
1. Click "Resend code"

**Observation 1 — Error toast**:
1. Toast title equals `Too many requests. Try again later.`

**Observation 2 — `resendIn` is NOT reset**:
1. The `setResendIn(RESEND_COOLDOWN_SECONDS)` call is inside the `try` block (only runs on success)
2. The link remains enabled and the user can spam-click

> ⚠ unverified — confirm whether the button stays enabled after the request resolves.

**API mock**: `POST /auth/signin-code/request` → 429 `{ "detail": "Too many requests. Try again later." }`.

---

### TC-ERROR-009: Network failure on request falls back to generic toast

**Action**:
1. Submit a valid email with the route aborted

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Stay on RequestStep**:
1. Heading remains `Sign in with a code`

**API mock**: `POST /auth/signin-code/request` route aborted.

---

### TC-EDGE-001: Verify with stale email after editing localStorage

**Preconditions**:
- User is on `VerifyStep` for `owner@acme.com`
- Someone manually edits localStorage to swap the active org

**Action**:
1. Submit a valid code

**Observation 1 — Auth store is overwritten by response**:
1. `localStorage.login_data` is overwritten with the verify response
2. No leak from the manual edit

**API mock**: `POST /auth/signin-code/verify` → 200.

---

### TC-EDGE-002: Authenticated visit keeps the form rendered

**Preconditions**:
- localStorage has a valid `tone_access_token` (different user)

**Action**:
1. Visit `/sign-in-with-code`

**Observation 1 — Page renders RequestStep normally**:
1. Email input is in the DOM
2. No auto-redirect to `/home`

**Observation 2 — Subsequent verify overwrites session**:
1. Submitting a fresh email + code hydrates the auth store with the new response, overwriting the previous session

> Document this as the current behaviour.

---

### TC-LOADING-001: Slow API on request keeps Send code in loading state

**Action**:
1. Visit `/sign-in-with-code`
2. Submit a valid email with a backend delayed ~3500 ms

**Observation 1 — Button label and disabled state**:
1. Within 100 ms of click, the "Send code" button shows the loading spinner and is `disabled`
2. The disabled state persists throughout the 3500 ms window

**Observation 2 — Double-click is a no-op**:
1. Clicking again during loading produces zero additional `POST /auth/signin-code/request` requests

**Observation 3 — Step advances after resolution**:
1. After ~3500 ms `VerifyStep` mounts
2. Toast `If the email exists, a code has been sent` appears

**API mock**: `POST /auth/signin-code/request` → 200 delayed by 3500 ms.

---

### TC-LOADING-002: Slow API on verify keeps Verify and sign in in loading state

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Submit `123456` with a backend delayed ~3500 ms

**Observation 1 — Button disabled with spinner**:
1. "Verify and sign in" shows the spinner and is `disabled` for the full 3500 ms

**Observation 2 — Double-click is a no-op**:
1. Clicking again produces zero additional `POST /auth/signin-code/verify` requests

**Observation 3 — Redirect after resolution**:
1. URL becomes `/home` only after the response resolves

**API mock**: `POST /auth/signin-code/verify` → 200 delayed by 3500 ms.

---

### TC-EDGE-003: Network failure on verify preserves code value

**Preconditions**:
- User is on `VerifyStep`; code field contains `123456`

**Action**:
1. Click "Verify and sign in" with the route aborted

**Observation 1 — Generic toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Code field preserved**:
1. The code input still contains `123456`
2. The "Verify and sign in" button re-enables

**API mock**: `POST /auth/signin-code/verify` route aborted.

---

### TC-EDGE-004: XSS attempt in email is rejected by Zod

**Action**:
1. Visit `/sign-in-with-code`
2. Type `<script>alert(1)</script>@x.com` into Email
3. Click "Send code"

**Observation 1 — Zod rejects**:
1. Helper text under Email reads `Please enter a valid email`
2. Zero `POST /auth/signin-code/request` requests are recorded

**Observation 2 — DOM is safe**:
1. The literal `<script>` text appears as the input's `value` attribute (rendered as text)
2. `window.alert` was not invoked

---

### TC-EDGE-005: Email containing emoji is documented behaviour

**Action**:
1. Visit `/sign-in-with-code`
2. Type `user+🔥@example.com` into Email
3. Click "Send code"

**Observation 1 — Behaviour depends on Zod**:
1. If Zod's `.email()` accepts the ASCII portion, the request fires and `VerifyStep` mounts with the email rendered verbatim in `<strong>`
2. If rejected, helper text `Please enter a valid email` appears

> Document observed behaviour against the current Zod version.

---

### TC-EDGE-006: Pasting spaces into the code field strips to digits

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Paste `1 2 3 4 5 6` into the code input

**Observation 1 — onValueChange strips non-digits**:
1. The code input value is exactly `123456`

**Observation 2 — Zod passes on submit**:
1. Clicking "Verify and sign in" fires exactly one `POST /auth/signin-code/verify`

---

### TC-EDGE-007: Pasting newlines into the code field strips them

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Paste `123\n456` into the code input

**Observation 1 — Newline stripped**:
1. The code input value is exactly `123456`

---

### TC-EDGE-008: Pasting >6 digits clamps to first 6

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Paste `123456789012` into the code input

**Observation 1 — Sliced to 6**:
1. The code input value is exactly `123456`

---

### TC-EDGE-009: Submit via Enter key in code field

**Preconditions**:
- User is on `VerifyStep`; code field contains `123456`

**Action**:
1. Focus the code input
2. Press the `Enter` key

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/signin-code/verify` request is recorded
2. Request body equals `{ "email": "owner@acme.com", "code": "123456" }`

**API mock**: `POST /auth/signin-code/verify` → 200.

---

### TC-EDGE-010: Edited code in dev tools to 5 chars still blocked by Zod

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Use dev tools to set the code input value to `12345`
2. Click "Verify and sign in"

**Observation 1 — Zod blocks submission**:
1. Helper text under code reads `Enter the 6-digit code`
2. Zero `POST /auth/signin-code/verify` requests are recorded

---

### TC-EDGE-011: Code expires after 11 minutes — submit returns 401

**Preconditions**:
- User leaves the tab on `VerifyStep` for 11 minutes

**Action**:
1. Submit any 6-digit code

**Observation 1 — Backend rejects**:
1. Toast title equals `Invalid or expired code`
2. Code field retains value

**API mock**: `POST /auth/signin-code/verify` → 401 `{ "detail": "Invalid or expired code" }`.

---

### TC-EDGE-012: Resend timer continues ticking while tab is backgrounded

**Preconditions**:
- User is on `VerifyStep`; `resendIn = 60`

**Action**:
1. Background the tab for 30 seconds
2. Foreground the tab

**Observation 1 — Remaining time reflects elapsed seconds**:
1. Resend label reads `Resend in 30s` (or near) — JS timer keeps running unless browser throttles

---

### TC-EDGE-013: User opens a second tab and verifies first

**Preconditions**:
- User opens `/sign-in-with-code` in tab A; advances to `VerifyStep`
- User opens the same flow in tab B, verifies successfully

**Action**:
1. Submit the code in tab A

**Observation 1 — Backend rejects in tab A**:
1. Toast title equals `Invalid or expired code`

**API mock** (tab A): `POST /auth/signin-code/verify` → 401.

---

### TC-EDGE-014: Refreshing mid-flow resets to RequestStep

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Press browser Refresh

**Observation 1 — RequestStep re-renders**:
1. Heading reads `Sign in with a code`
2. Email input is empty (React-only state reset)

**Observation 2 — No errors fire**:
1. No console errors during the reset

---

### TC-NAV-002: Browser back from VerifyStep exits the page

**Preconditions**:
- WF-1 step 5 reached (i.e. `VerifyStep` rendered)

**Action**:
1. Press the browser Back button

**Observation 1 — Back exits the page**:
1. URL is no longer `/sign-in-with-code` (the step swap did NOT push history)

---

### TC-NAV-003: Open-redirect guard blocks `?next=https://evil.com`

**Action**:
1. Visit `/sign-in-with-code?next=https://evil.com`
2. Submit a valid email and code

**Observation 1 — Redirect falls back to /home**:
1. `safeNext = '/home'` because `'https://evil.com'.startsWith('/')` is false
2. URL becomes `/home` (NOT `https://evil.com`)
3. No navigation event targets an external origin

**API mocks**: as TC-HAPPY-001.

---

### TC-NAV-004: Protocol-relative `?next=//evil.com` — known risk

**Action**:
1. Visit `/sign-in-with-code?next=//evil.com`
2. Submit a valid email and code

**Observation 1 — startsWith('/') is true**:
1. `safeNext = '//evil.com'` (passes the guard)
2. `router.push('//evil.com')` runs

**Observation 2 — Verify actual destination**:
1. Verify whether Next.js treats `//evil.com` as a same-origin path or an external URL

> ⚠ Known potential open-redirect risk — document the actual observed redirect destination and fail the test if the user lands off-origin.

**API mocks**: as TC-HAPPY-001.

---

### TC-A11Y-001: Tab order through RequestStep

**Action**:
1. Visit `/sign-in-with-code`
2. Focus the Email input
3. Press Tab repeatedly

**Observation 1 — Tab order**:
1. Focus moves Email → Send code → "Sign in with password instead" link
2. No focusable element is skipped or reached twice

---

### TC-A11Y-002: Tab order through VerifyStep

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Focus the code input
2. Press Tab repeatedly

**Observation 1 — Tab order**:
1. Focus moves Code → Verify and sign in → Use a different email → Resend

---

### TC-A11Y-003: Numeric keypad and one-time-code autofill on code input

**Action**:
1. Open `/sign-in-with-code` on a mobile browser (or inspect the input attributes)
2. Focus the code input

**Observation 1 — Mobile keyboard hints**:
1. The code input has `inputMode="numeric"` and `autoComplete="one-time-code"`
2. On iOS / Android, the numeric keypad appears and OS-level OTP autofill suggestion is offered

---

### TC-A11Y-004: Helper-text errors announced via aria-live

**Preconditions**:
- User is on `VerifyStep`

**Action**:
1. Submit `12345` (5 digits)

**Observation 1 — Code error is announceable**:
1. Helper text under the code input is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `Enter the 6-digit code`

---

### TC-A11Y-005: Resend Button uses real disabled, not just CSS

**Preconditions**:
- User is on `VerifyStep`; `resendIn = 60`

**Action**:
1. Inspect the resend `Button`

**Observation 1 — Real disabled attribute**:
1. The resend `Button` has the `disabled` HTML attribute (so SR users hear "dimmed/unavailable")

---

### TC-A11Y-006: Loading button announces via spinner + visible text

**Action**:
1. Submit a valid email with a slow backend

**Observation 1 — Loading state**:
1. The "Send code" button shows the spinner + remains visible
2. The button has `disabled` set

> ⚠ Consider adding `aria-busy` while `isPending` so SR explicitly announces the wait.

---

### TC-A11Y-007: Missing page-level h1 — heading hierarchy gap

**Action**:
1. Inspect both steps for heading hierarchy

**Observation 1 — Only h2 present**:
1. Both steps use `<h2>`; there is no `<h1>` on the page
2. The layout's `Logo` is decorative

> ⚠ Consider a visually-hidden `<h1>` for SR users.

---

### TC-FULL-001: End-to-end sign-in-with-code lifecycle

**Preconditions**:
- A test user `__e2e__sc_<uuid>@example.com` is provisioned and verified via the backend API
- A sign-in code is fetched after `POST /auth/signin-code/request` (via a test-only admin endpoint or by reading the dev mailbox / DB)

**Action**:
1. Visit `/sign-in-with-code` without auth
2. Submit with empty email
3. Submit `not-an-email`
4. Click "Sign in with password instead"
5. Navigate back to `/sign-in-with-code`
6. Submit the provisioned email
7. Submit code `12345`
8. Submit a wrong 6-digit code
9. Click "Use a different email"
10. Re-submit the same email; fetch a new code; submit it
11. Sign out (clear localStorage); visit `/sign-in-with-code?next=/agents`; repeat request + verify
12. Sign out; visit `/sign-in-with-code?next=https://evil.com`; repeat request + verify

**Observation 1 — Step 1 renders RequestStep**:
1. Heading reads `Sign in with a code`

**Observation 2 — Step 2 inline error**:
1. Helper text `Email is required` visible

**Observation 3 — Step 3 format error**:
1. Helper text `Please enter a valid email` visible

**Observation 4 — Step 4 navigates to /login**:
1. URL becomes `/login`

**Observation 5 — Step 6 advances to VerifyStep**:
1. Toast `If the email exists, a code has been sent` visible
2. VerifyStep heading with email in `<strong>` rendered

**Observation 6 — Step 7 length error**:
1. Helper text `Enter the 6-digit code` visible

**Observation 7 — Step 8 wrong code toast**:
1. Toast title `Invalid or expired code`
2. Code field retains value

**Observation 8 — Step 9 reverts to RequestStep blank**:
1. Heading back to `Sign in with a code`; email empty

**Observation 9 — Step 10 lands on /home**:
1. Toast title `Welcome back!`
2. URL becomes `/home`
3. `localStorage.tone_access_token` is set

**Observation 10 — Step 11 lands on /agents**:
1. URL becomes `/agents`

**Observation 11 — Step 12 open-redirect guard**:
1. URL becomes `/home` (open-redirect guard rejects external `next`)

**Cleanup** (in `finally`):
1. Delete the provisioned user via the backend admin API

---

## Edge Cases (each appears as a `TC-EDGE-*` or related test case above)

- [x] User refreshes the page mid-flow — see TC-EDGE-014
- [x] User opens a second tab and verifies first — see TC-EDGE-013
- [x] User pastes a code with spaces — see TC-EDGE-006
- [x] User pastes a 7-character code — see TC-EDGE-008
- [x] iOS auto-fill `one-time-code` — see TC-A11Y-003
- [x] Send code double-click while pending — see TC-LOADING-001
- [x] Verify and sign in double-click while pending — see TC-LOADING-002
- [x] `next` open-redirect (https://evil.com) — see TC-NAV-003
- [x] `next` protocol-relative (`//evil.com`) — see TC-NAV-004
- [x] `next` with query string (`/agents?org=foo`) passes through unchanged — covered by TC-NAV-003 / TC-HAPPY-002 pattern
- [x] User leaves the tab on `VerifyStep` for 11 minutes — see TC-EDGE-011
- [x] Resend timer continues ticking while tab is backgrounded — see TC-EDGE-012
- [x] Dev-tools edited code to 5 chars — see TC-EDGE-010
- [x] Send code spam-click debounced by `isPending` — see TC-LOADING-001

---

## Business Rules

- Sign-in codes are **6 digits** (`SIGNIN_CODE_LENGTH = 6`); the constant is
  exposed from `src/schemas/auth.ts` and used by both the schema regex and the
  UI copy.
- Codes expire after **10 minutes** (per the page subtitle; backend-enforced).
- The request endpoint always returns 200 with the generic message regardless
  of whether the email exists — prevents account enumeration.
- The resend cooldown is **60 seconds** (`RESEND_COOLDOWN_SECONDS = 60`), enforced
  client-side only; backend may have its own rate limit (typically 429 → toast).
- Successful verify hydrates the auth store with `access_token`, `refresh_token`,
  `user`, and `organization` — the user is logged in immediately, no extra step.
- The `next` redirect param is sanitised: only paths starting with `/` are honoured.
  All other inputs (absolute URLs, missing param) fall back to `/home`.
- The page is public — it is part of the `(auth)` route group, no
  `tone_access_token` requirement.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab navigation reaches every actionable element (request step) — see TC-A11Y-001
- [x] Tab navigation reaches every actionable element (verify step) — see TC-A11Y-002
- [x] `inputMode="numeric"` + `autoComplete="one-time-code"` — see TC-A11Y-003
- [x] Helper text errors render via RHF `fieldState.error.message` — see TC-A11Y-004
- [x] Resend `Button` uses real `disabled` — see TC-A11Y-005
- [x] Loading button announces via spinner — see TC-A11Y-006
- [x] No `<h1>` on the page — see TC-A11Y-007

---

## Expected Toast Messages

Toasts use Sonner via `showToast` (`src/lib/toast.ts`). All errors are routed
through `handleApiError(err)` which uses `response.data.detail` as the toast
title when it is a string, otherwise falls back to
`"Something went wrong. Please try again."`.

| Trigger                                                | Toast title                                       | Toast description | Variant |
| ------------------------------------------------------ | ------------------------------------------------- | ----------------- | ------- |
| Request code 200                                       | `If the email exists, a code has been sent`       | —                 | success |
| Verify code 200                                        | `Welcome back!`                                   | —                 | success |
| Resend after cooldown 200                              | `A new code has been sent`                        | —                 | success |
| Any backend 4xx/5xx with string `detail`               | backend `detail` (e.g. `Invalid or expired code`) | —                 | error   |
| Any backend error with non-string `detail`             | `Something went wrong. Please try again.`         | —                 | error   |
