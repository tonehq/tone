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

## User Workflow Steps

**WF-1: Request → verify → home** (positive, happy path)

1. User opens `/sign-in-with-code` → expected: `RequestStep` renders with empty
   email field, "Send code" button enabled (RHF defaults `isValid` to allow
   submit; Zod errors render only after blur/submit)
2. User types `owner@acme.com` → blurs → expected: no visible error (Zod passes)
3. User clicks "Send code" → expected: button shows loading state;
   `POST /auth/signin-code/request { "email": "owner@acme.com" }` fires
4. 200 response → expected: success toast `"If the email exists, a code has been sent"`,
   `setEmail('owner@acme.com')` advances inner state, `VerifyStep` mounts
5. `VerifyStep` renders heading "Enter your code" with email in `<strong>` tag;
   `resendIn` initialises to 60 and starts ticking down
6. User types `123456` into the code field → `onValueChange` keeps only digits → RHF value `code: "123456"`
7. User clicks "Verify and sign in" → expected: button shows loading state;
   `POST /auth/signin-code/verify { "email": "owner@acme.com", "code": "123456" }` fires
8. 200 response with `access_token` → `setLoginResponse(data)` writes localStorage;
   toast `"Welcome back!"`; `router.push('/home')` (or `next` if safe)

**WF-2: Request step blocked by Zod** (negative)

1. User opens `/sign-in-with-code` → `RequestStep` renders
2. User submits with empty email → expected: `TextInput` shows `helperText`
   `"Email is required"`; no API call
3. User types `not-an-email` → submits → expected: helperText
   `"Please enter a valid email"`; no API call

**WF-3: Verify step blocked by Zod** (negative)

1. User in `VerifyStep` types `12345` (5 digits) → submits
2. Expected: `helperText` reads `"Enter the 6-digit code"`; no API call

**WF-4: Resend after cooldown** (positive)

1. After WF-1 step 5, user waits 60 seconds → resend link text flips from
   `"Resend in 1s"` to `"Resend code"`, becomes enabled
2. User clicks resend → `POST /auth/signin-code/request` re-fires; toast
   `"A new code has been sent"`; `code` field is cleared; cooldown restarts at 60

**WF-5: Use a different email** (positive)

1. After WF-1 step 5, user clicks "Use a different email" → `email` resets to `''`;
   inner state re-renders `RequestStep` with a fresh form
2. The previous `VerifyStep` is unmounted (resend timer is cleaned up via
   `clearTimeout` in the `useEffect` cleanup)

**WF-6: Open code mailto link with `next` query param** (positive)

1. User opens `/sign-in-with-code?next=/agents/abc` → request step renders as normal
2. After successful verify, expected: `safeNext = '/agents/abc'`; `router.push('/agents/abc')`

**WF-7: Malicious `next` query param** (negative — security guard)

1. User opens `/sign-in-with-code?next=https://evil.com` → request + verify run normally
2. On verify success: `nextPath = 'https://evil.com'`; `safeNext = '/home'` because
   `'https://evil.com'.startsWith('/')` is false
3. `router.push('/home')` — protocol-relative URL `?next=//evil.com` also fails the
   `startsWith('/')` check is true for `//evil.com`, but `router.push('//evil.com')`
   in Next.js stays in-app. ⚠ unverified — confirm Next.js treats `//foo` as a
   same-origin path or external; if external, the guard is insufficient.

**WF-8: Auth gating** (positive — public page)

1. User without `tone_access_token` opens `/sign-in-with-code` → page renders;
   no redirect

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

## Success Scenarios

**PS-1: Request code succeeds**

- **Preconditions**: User opens `/sign-in-with-code`.
- **Steps**: type `owner@acme.com` → click "Send code".
- **Expected outcome**: success toast `"If the email exists, a code has been sent"`
  (Sonner default 3 s); `VerifyStep` renders with the email shown in the subtitle.
- **Mock API** (`POST /auth/signin-code/request`, 200):
  ```json
  { "message": "Sign-in code sent" }
  ```

**PS-2: Verify code succeeds → redirect to `/home`**

- **Preconditions**: PS-1 completed; no `?next` param.
- **Steps**: type `123456` → click "Verify and sign in".
- **Expected outcome**: `setLoginResponse(data)` writes localStorage
  (`tone_access_token`, `org_tenant_id`, `login_data`); toast `"Welcome back!"`;
  `router.push('/home')`.
- **Mock API** (`POST /auth/signin-code/verify`, 200):
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

**PS-3: Verify code succeeds with safe `next`**

- **Preconditions**: Open `/sign-in-with-code?next=/agents/abc`; PS-1 completed.
- **Steps**: type `123456` → click "Verify and sign in".
- **Expected outcome**: toast `"Welcome back!"`; `router.push('/agents/abc')`.
- **Mock API**: as PS-2.

**PS-4: Resend after cooldown succeeds**

- **Preconditions**: PS-1 completed; user waits 60 s (or test fast-forwards
  the timer).
- **Steps**: click "Resend code".
- **Expected outcome**: code field cleared; toast `"A new code has been sent"`;
  cooldown resets to 60 s.
- **Mock API** (`POST /auth/signin-code/request`, 200): as PS-1.

**PS-5: Use a different email**

- **Preconditions**: PS-1 completed (in `VerifyStep`).
- **Steps**: click "Use a different email".
- **Expected outcome**: inner state re-renders `RequestStep` with blank form;
  no API call.

**PS-6: Sign-in-with-password link**

- **Preconditions**: User on `RequestStep`.
- **Steps**: click "Sign in with password instead".
- **Expected outcome**: `router.push('/login')`; the `Link` component is a
  Next.js `<Link href="/login">`.

---

## Failure Scenarios

**FS-1: Empty email blocks submit**

- **Preconditions**: `RequestStep`.
- **Steps**: leave email empty → click "Send code".
- **Mock API**: not called (Zod blocks submit).
- **Expected UI**: `TextInput` shows `helperText` = `"Email is required"`.

**FS-2: Invalid email format**

- **Steps**: type `not-an-email` → click "Send code".
- **Expected UI**: `helperText` = `"Please enter a valid email"`; no API call.

**FS-3: Request backend 400 — `email is required`**

- **Preconditions**: Somehow the body lacks `email` (manual fetch / dev tools).
- **Mock API** (`POST /auth/signin-code/request`, 400):
  ```json
  { "detail": "email is required" }
  ```
- **Expected UI**: `handleApiError(err)` → toast title `"email is required"`;
  inner state stays on `RequestStep` (no advance).

**FS-4: Request backend 429 (rate limit)**

- **Mock API** (`POST /auth/signin-code/request`, 429):
  ```json
  { "detail": "Too many requests. Try again later." }
  ```
- **Expected UI**: toast title `"Too many requests. Try again later."`;
  stays on `RequestStep`.

**FS-5: Verify code Zod — empty**

- **Steps**: in `VerifyStep`, leave code empty → click "Verify and sign in".
- **Expected UI**: `helperText` = `"Code is required"`; no API call.

**FS-6: Verify code Zod — wrong length**

- **Steps**: type `12345` (5 digits) → submit.
- **Expected UI**: `helperText` = `"Enter the 6-digit code"`; no API call.

**FS-7: Verify code Zod — non-numeric**

- **Steps**: paste `abcdef` → `onValueChange` strips alphas; field ends up
  empty → submit.
- **Expected UI**: `helperText` = `"Code is required"`; no API call.

**FS-8: Verify backend 401 — invalid/expired code**

- **Mock API** (`POST /auth/signin-code/verify`, 401):
  ```json
  { "detail": "Invalid or expired code" }
  ```
- **Expected UI**: `handleApiError(err)` → toast title `"Invalid or expired code"`;
  user remains on `VerifyStep`; code field retains the typed value (no auto-clear).

**FS-9: Verify backend 400 — wrong code**

- **Mock API** (`POST /auth/signin-code/verify`, 400):
  ```json
  { "detail": "Invalid code" }
  ```
- **Expected UI**: toast title `"Invalid code"`; stays on `VerifyStep`.

**FS-10: Verify backend 422 — `detail` is array**

- **Mock API** (`POST /auth/signin-code/verify`, 422):
  ```json
  {
    "detail": [
      {
        "type": "missing",
        "loc": ["body", "code"],
        "msg": "Field required",
        "input": {}
      }
    ]
  }
  ```
- **Expected UI**: `handleApiError` only stringifies `detail` when it is a string;
  for array `detail` it falls back to `"Something went wrong. Please try again."`
  in the toast.

**FS-11: Verify backend 500**

- **Mock API** (`POST /auth/signin-code/verify`, 500):
  ```json
  { "detail": "Internal Server Error" }
  ```
- **Expected UI**: toast title `"Internal Server Error"`; stays on `VerifyStep`.

**FS-12: Resend during cooldown is a no-op**

- **Preconditions**: `VerifyStep`, `resendIn = 30`.
- **Steps**: click resend link.
- **Mock API**: not called (`Button` is `disabled` + handler early-returns).
- **Expected UI**: no toast, no API call; label still reads `"Resend in 30s"`.

**FS-13: Resend backend error**

- **Preconditions**: `resendIn === 0`.
- **Mock API** (`POST /auth/signin-code/request`, 429):
  ```json
  { "detail": "Too many requests. Try again later." }
  ```
- **Expected UI**: toast title `"Too many requests. Try again later."`;
  `resendIn` is **not** reset (the `setResendIn(RESEND_COOLDOWN_SECONDS)` call
  is inside the `try` block, after the await — only runs on success).
- **Gotcha**: on error, the link remains enabled and the user can spam-click.
  ⚠ unverified — confirm whether the button stays enabled after the request
  resolves.

**FS-14: Verify with stale email after editing localStorage**

- **Preconditions**: `VerifyStep` for `owner@acme.com`. Someone manually edits
  localStorage to swap the active org.
- **Steps**: submit valid code.
- **Expected UI**: backend ties code to original email → succeeds; auth store
  is overwritten by the response → no leak from the manual edit.

**FS-15: Network error (offline) on request**

- **Mock API**: aborted; no response.
- **Expected UI**: `handleApiError(err)` → toast title falls back to
  `"Something went wrong. Please try again."`; stays on `RequestStep`.

**FS-16: Authenticated visit to `/sign-in-with-code` keeps form rendered**

- **Preconditions**: localStorage has valid `access_token` (different user).
- **Expected UI**: page renders `RequestStep` form normally — no auto-redirect to `/home`. Submitting a fresh email + code still hydrates the auth store with the response, overwriting the previous session. Document this as the current behaviour.

**FS-17: Slow API (>3s) on request keeps Send code in loading state**

- **Mock API** (`POST /auth/signin-code/request`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button stays disabled with spinner for the full duration; clicking again is a no-op; `VerifyStep` mounts only after the response resolves.

**FS-18: Slow API (>3s) on verify keeps Verify and sign in in loading state**

- **Mock API** (`POST /auth/signin-code/verify`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button stays disabled with spinner; redirect only fires after the response.

**FS-19: Network failure on verify preserves code value**

- **Mock API**: route aborted.
- **Expected UI**: toast "Something went wrong. Please try again."; code field still contains the typed 6 digits; button re-enables.

**FS-20: Email with XSS / special chars**

- **Steps**: type `<script>alert(1)</script>@x.com` in the request step.
- **Expected UI**: Zod's `.email()` rejects → helperText "Please enter a valid email"; no API call; literal text renders as plain value in the input.

**FS-21: Email with emoji on `RequestStep`**

- **Steps**: type `user+🔥@example.com`.
- **Expected UI**: Zod's `.email()` likely accepts the ASCII portion — document observed behaviour. If accepted, request fires and `VerifyStep` mounts with the email rendered verbatim in `<strong>`.

**FS-22: Code with whitespace via paste**

- **Steps**: paste `1 2 3 4 5 6` into the code field.
- **Expected UI**: `onValueChange` strips non-digits via `digitsOnly` → field value `123456`; Zod passes; submit allowed.

**FS-23: Code paste with newlines**

- **Steps**: paste `123\n456` into the code field.
- **Expected UI**: `digitsOnly` strips the newline → field value `123456`; Zod passes.

**FS-24: Very long pasted code (>6 digits)**

- **Steps**: paste `123456789012`.
- **Expected UI**: `digitsOnly` slices to 6 → field value `123456`; Zod passes.

**FS-25: Tab order through `RequestStep`**

- **Steps**: focus the page → press Tab repeatedly.
- **Expected UI**: focus moves Email → Send code → "Sign in with password instead" link.

**FS-26: Tab order through `VerifyStep`**

- **Steps**: focus the page → press Tab repeatedly.
- **Expected UI**: focus moves Code → Verify and sign in → Use a different email → Resend.

**FS-27: Submit via Enter key in code field**

- **Steps**: type a valid 6-digit code, press Enter while focus is on the code input.
- **Expected UI**: form submits exactly as clicking Verify and sign in would.

**FS-28: Helper-text errors are announced via aria-live**

- **Steps**: in `VerifyStep`, submit with `12345` (5 digits).
- **Expected UI**: helperText "Enter the 6-digit code" renders with `role="alert"` (or `aria-live`) so screen readers announce the error.

**FS-29: Browser back from `VerifyStep` to `RequestStep`**

- **Preconditions**: WF-1 step 5 reached.
- **Steps**: press browser Back.
- **Expected UI**: URL was not pushed when advancing from request → verify (the swap is in-component); pressing Back exits `/sign-in-with-code` to the previous page.

**FS-30: Protocol-relative `?next=//evil.com` is treated as in-app path**

- **Preconditions**: URL has `?next=//evil.com`; complete request + verify successfully.
- **Expected UI**: `safeNext = '//evil.com'` (passes `startsWith('/')`); `router.push('//evil.com')` — verify whether Next.js treats this as a same-origin path. ⚠ Known potential open-redirect risk — document the actual observed redirect destination and fail the test if the user lands off-origin.

### Full lifecycle (`*-FULL`)

**SC-FULL: End-to-end sign-in-with-code lifecycle in a single test**

- **Preconditions**: A test user `__e2e__sc_<uuid>@example.com` is provisioned and verified via the backend API. A sign-in code is fetched after `POST /auth/signin-code/request` (via a test-only admin endpoint or by reading the dev mailbox / DB).
- **Steps in one Playwright test body**:
  1. Visit `/sign-in-with-code` without auth → expect `RequestStep` rendered.
  2. Submit with empty email → expect helperText "Email is required".
  3. Submit `not-an-email` → expect helperText "Please enter a valid email".
  4. Click "Sign in with password instead" → expect URL `/login`.
  5. Navigate back to `/sign-in-with-code`.
  6. Submit the provisioned email → expect success toast "If the email exists, a code has been sent" and `VerifyStep` rendered with the email in `<strong>`.
  7. Submit code `12345` → expect helperText "Enter the 6-digit code".
  8. Submit a wrong 6-digit code → expect toast "Invalid or expired code"; stay on `VerifyStep`; code field retains value.
  9. Click "Use a different email" → expect `RequestStep` re-rendered blank.
  10. Re-submit the same email → fetch a new code → submit the new code → expect toast "Welcome back!" and URL `/home`; verify localStorage has `tone_access_token`.
  11. Sign out (clear localStorage) and visit `/sign-in-with-code?next=/agents` → repeat request + verify successfully → expect redirect to `/agents` (not `/home`).
  12. Sign out and visit `/sign-in-with-code?next=https://evil.com` → repeat request + verify → expect redirect to `/home` (open-redirect guard).
- **Cleanup (in `finally`)**: Delete the provisioned user via the backend admin API.
- **Naming**: `SC-FULL — sign-in-with-code full lifecycle`.

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

## Edge Cases

- [ ] User refreshes the page mid-flow (after step 1) → inner `email` state is
      reset (React-only), user is back to `RequestStep`; no error
- [ ] User opens a second tab and verifies first → the original tab's verify call
      returns 401 `"Invalid or expired code"` on submit
- [ ] User pastes a code with spaces (`"123 456"`) → `onValueChange` strips spaces,
      RHF stores `"123456"`, Zod passes
- [ ] User pastes a 7-character code → `digitsOnly` slices to 6; only first 6 are kept
- [ ] User uses iOS auto-fill `one-time-code` → `autoComplete` triggers OS suggestion
      bar; on tap, the input is filled with the OTP
- [ ] User clicks "Send code" while a previous request is in flight → `requestCode.isPending`
      keeps the button disabled, preventing double submit
- [ ] User clicks "Verify and sign in" while a previous verify is in flight →
      same `isPending` guard
- [ ] `next` param is an open redirect attempt (`https://evil.com`) → `safeNext`
      defaults to `/home`
- [ ] `next` param is a protocol-relative URL (`//evil.com`) → `startsWith('/')`
      is `true`, so `router.push('//evil.com')` runs. ⚠ unverified — Next.js
      may treat this as an in-app path, but it is a known open-redirect risk
- [ ] `next` param contains a query string (`/agents?org=foo`) → passes through
      unchanged
- [ ] User leaves the tab on `VerifyStep` for 11 minutes → backend invalidates
      the code; the next submit returns 401 `"Invalid or expired code"`
- [ ] Resend timer continues to tick even when the tab is backgrounded (JS timer
      keeps running unless throttled by the browser) — the user sees correct
      remaining time on focus
- [ ] User opens dev tools and edits the `code` input to `"12345"` (5 chars)
      → Zod blocks submission with `"Enter the 6-digit code"`
- [ ] Toast spam: clicking "Send code" twice quickly → second click is debounced
      by `requestCode.isPending`; only one request is sent

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

## Accessibility Requirements

- [ ] Tab navigation reaches every actionable element: email input → "Send code"
      → "Sign in with password instead" link (request step); code input →
      "Verify and sign in" → "Use a different email" → "Resend" (verify step)
- [ ] `TextInput` with `inputMode="numeric"` triggers the numeric keypad on
      mobile; `autoComplete="one-time-code"` enables OS-level OTP autofill
- [ ] Code field's `maxLength={6}` is enforced both as an HTML attribute and via
      the `digitsOnly` `onValueChange` slice
- [ ] Form errors render as `helperText` under each input via RHF's `fieldState.error.message`
      — `TextInput` itself does not duplicate error rendering
- [ ] Buttons announce loading state via the spinner; the visual text remains
      visible during loading. ⚠ consider adding an `aria-busy` attribute while
      `isPending` so SR announces the wait
- [ ] Resend `Button` uses real `disabled` (not just CSS) so SR users hear
      "dimmed/unavailable" during cooldown
- [ ] The "Use a different email" link is a real `<Button variant="link">` —
      keyboard activation triggers `onBack` correctly
- [ ] Headings are `<h2>` (no `<h1>` on the page; the layout's `Logo` is decorative).
      ⚠ consider a visually-hidden `<h1>` for SR users
- [ ] Sonner toasts render in an `aria-live` region so successful/failed states
      are announced
