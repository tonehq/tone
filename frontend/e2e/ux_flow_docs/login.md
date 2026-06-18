# Feature Doc: Login

Feature documentation for the `/login` page. Used by `/generate-tests login` (or
`--docs e2e/ux_flow_docs/login.md`) to ensure all positive and negative user cases are
covered alongside the component source analysis.

The login page is the primary entry point for returning users. It exchanges an
email + password for a JWT access token, a refresh token, and a hydrated
`AuthLoginResponse` payload that drives the Zustand `useAuthStore`. The form is
backed by `react-hook-form` + Zod (`loginSchema`) and the mutation is
`useLogin()` from `@tanstack/react-query`.

---

## Page

- **Route**: `/login` (under the `(auth)` route group; legacy `/auth/login` callers should arrive here)
- **Component**: `src/app/(auth)/login/page.tsx` (default export `LoginPage` wraps `LoginPageInner` in `<Suspense fallback={null}>`)
- **Layout**: `src/app/(auth)/layout.tsx` — two-column layout with the form on the left and the animated branded panel on the right (`hidden lg:flex` on the right column)
- **Auth required**: no — this is a **public** page
- **Redirect when already authenticated**: not enforced by a server middleware today (there is no `src/middleware.ts` — auth gating is client-side). A logged-in user who visits `/login` will see the form; however dashboard routes always run through the `useAuthStore` bootstrap which reads `access_token` from localStorage, and clicking "Sign In" with valid creds simply re-hydrates the store and pushes to `/home`. ⚠ unverified — confirm whether a logged-in user is silently redirected via a client-side `useEffect` in a future iteration.

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
- [ ] Banner text reads "Please verify your email before logging in."
- [ ] Banner has a "Resend verification email" link-button that is disabled when the email field is empty and shows the "Loading..." state while `useResendVerification` is in flight
- [ ] On success, toast "Verification email sent!" appears
- [ ] On failure, `handleApiError(err)` surfaces the backend `detail` as the toast title

### US-3: Sign in with a code instead

**As a** user who prefers passwordless login, **I want to** click "Sign in with a code instead" and be taken to `/sign-in-with-code`, **so that** I can receive a one-time code on email and avoid typing my password.

**Acceptance criteria**:

- [ ] Link "Sign in with a code instead" renders below the Sign In button
- [ ] Clicking the link navigates to `/sign-in-with-code` (client-side `<Link>`)

### US-4: Forgot password and Sign up affordances

**As a** user, **I want to** click "Forgot password?" or "Sign up", **so that** I can recover access or register without leaving the auth area.

**Acceptance criteria**:

- [ ] "Forgot password?" link href is `/forgot-password`
- [ ] "Sign up" link below the form href is `/signup`
- [ ] Both links use the primary text color and hover underline

### US-5: Block submission on client-side validation errors

**As a** user, **I want to** see helpful field-level errors before I waste a network round-trip, **so that** I know which field to fix.

**Acceptance criteria**:

- [ ] Empty Email shows helperText "Email is required" under the Email input
- [ ] Malformed email shows "Please enter a valid email"
- [ ] Password under 6 chars shows "Password must be at least 6 characters"
- [ ] Submit button transitions to "Loading..." with `disabled` while `login.isPending === true`

### US-6: Carry over a deep-link `next` after auth

**As a** user who was kicked out mid-session, **I want to** be returned to the page I was on, **so that** I do not lose context.

**Acceptance criteria**:

- [ ] Visiting `/login?next=/agents/edit/inbound/abc` and submitting valid creds lands me on `/agents/edit/inbound/abc`
- [ ] If `next` is not a relative path (e.g. external URL or missing leading `/`), the redirect falls back to `/home` (open-redirect guard: `nextPath && nextPath.startsWith('/')`)

---

## User Workflow Steps

**WF-1: Standard happy-path login** (positive)

1. User has no `access_token` in localStorage → expected: bootstrap returns `isAuthenticated: false`; page renders
2. User navigates to `/login` → expected: heading "Welcome back" + subtitle render; Suspense fallback `null` flashes invisibly while `useSearchParams` resolves
3. User types `owner@acme.com` into Email and `hunter22!` into Password → expected: Zod resolver reports no errors; helperText absent
4. User clicks **Sign In** → expected: button enters loading state ("Loading..." + `disabled`); `POST /auth/login` fires with `{ email, password }`
5. Response is 200 with `access_token`, `refresh_token`, `user`, `organization`, `role` → expected: `setLoginResponse(data)` writes `access_token`, `refresh_token`, `login_data`, `active_org_id`, and `user_id` into localStorage; success toast "Welcome back!" appears
6. Router pushes to `/home` → expected: URL is `/home`; sidebar layout begins mounting

**WF-2: Deep-link `next` redirect** (positive)

1. User visits `/login?next=/agents` while signed out → expected: form renders normally
2. User submits valid creds → expected: same as WF-1 steps 4–5; final redirect goes to `/agents` (not `/home`)
3. Same flow with `?next=https://evil.com/x` → expected: open-redirect guard fires; redirect goes to `/home`

**WF-3: Email-not-verified recovery** (positive negative)

1. User submits valid-format creds but account is unverified → expected: backend returns 401 with `{"detail": "Please verify your email before logging in"}`
2. `handleApiError(err)` surfaces toast title "Please verify your email before logging in"
3. `needsVerification` evaluates true (detail string contains `verify`) → expected: yellow banner appears below the password field
4. User clicks **Resend verification email** with email still filled → expected: `POST /auth/resend-verification` fires with `{ email }`
5. On 200 → expected: toast "Verification email sent!"; banner remains visible

**WF-4: Invalid credentials** (negative)

1. User submits a non-matching email/password → expected: backend returns 401 with `{"detail": "Invalid email or password"}`
2. `handleApiError(err)` surfaces toast title "Invalid email or password"
3. Form remains populated; loading state clears; user can retry

**WF-5: Client-side validation gates submit** (negative)

1. User leaves Email blank and clicks Sign In → expected: RHF prevents `POST /auth/login`; helperText "Email is required" renders
2. User types `not-an-email` → expected: helperText "Please enter a valid email"
3. User fills a valid email but `12345` password → expected: helperText "Password must be at least 6 characters"
4. User fixes both → expected: helperText clears; Submit proceeds

**WF-6: Account deactivated** (negative)

1. User submits valid creds for a disabled account → expected: 401 `{"detail": "Account is deactivated"}`
2. Toast title = "Account is deactivated"; form stays populated

**WF-7: Click-throughs to siblings** (positive)

1. User clicks "Forgot password?" → expected: navigation to `/forgot-password`
2. User clicks "Sign up" → expected: navigation to `/signup`
3. User clicks "Sign in with a code instead" → expected: navigation to `/sign-in-with-code`

**WF-8: Already-authenticated visit** (edge)

1. User has `access_token` in localStorage and visits `/login` → expected: page still renders the form (no automatic redirect today). Submitting valid creds re-hydrates the store via `setLoginResponse` and pushes to `/home` — see ⚠ in **Page** above.

---

## Input Specifications

Source: `src/schemas/auth.ts` (`loginSchema`).

| Field    | Type     | Required | Validation Rules                                                       | Exact Error Message                       |
| -------- | -------- | -------- | ---------------------------------------------------------------------- | ----------------------------------------- |
| Email    | email    | yes      | `z.string().min(1).email()` — non-empty AND well-formed email          | "Email is required" / "Please enter a valid email" |
| Password | password | yes      | `z.string().min(6)` — length ≥ 6 (note: signup requires 8)             | "Password must be at least 6 characters"  |

**Button state rules:**

- "Sign In" button is **never disabled** by `formState.isValid` (the page does not gate the button); attempting submit with invalid fields surfaces inline errors instead
- While `login.isPending === true`, the `<Button>` renders the loading label ("Loading...") and is disabled by the shadcn primitive
- "Resend verification email" link-button is disabled while `!email` OR `resend.isPending` is true

---

## Success Scenarios

**PS-1: Login succeeds, lands on /home**

- **Preconditions**: not authenticated; form valid.
- **Steps**: type email + password → click Sign In.
- **Expected outcome**: localStorage now contains `access_token`, `refresh_token`, `login_data`, `active_org_id`, `user_id`; success toast "Welcome back!"; URL is `/home`.
- **Mock API** (`POST /auth/login`, 200):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "00000000-0000-0000-0000-000000000001",
      "email": "owner@acme.com",
      "role": "owner",
      "is_verified": true
    },
    "organization": { "id": "00000000-0000-0000-0000-000000000100", "name": "Acme" },
    "role": "owner"
  }
  ```

**PS-2: Login with `?next=/agents` lands on /agents**

- **Preconditions**: PS-1 backend response; URL has `?next=/agents`.
- **Expected outcome**: success toast as above; router push is `/agents` (not `/home`).

**PS-3: Login with malicious `?next=https://evil.com` lands on /home**

- **Preconditions**: PS-1 backend response; URL has `?next=https://evil.com`.
- **Expected outcome**: open-redirect guard kicks in; redirect goes to `/home`.

**PS-4: Resend verification succeeds after a 401 verify error**

- **Preconditions**: WF-3 reached the yellow banner.
- **Steps**: click "Resend verification email" with email still filled.
- **Expected outcome**: toast "Verification email sent!" appears.
- **Mock API** (`POST /auth/resend-verification`, 200):
  ```json
  { "message": "If the email exists, a verification link has been sent" }
  ```

**PS-5: Loading state visible during slow login**

- **Preconditions**: backend deliberately slow (300 ms).
- **Steps**: submit valid form.
- **Expected outcome**: button shows "Loading..." with `disabled` attribute; user cannot double-submit.

**PS-6: Navigation to /signup**

- **Steps**: click the "Sign up" link below the form.
- **Expected outcome**: client-side navigation to `/signup`; no network calls.

**PS-7: Navigation to /forgot-password**

- **Steps**: click "Forgot password?" link.
- **Expected outcome**: client-side navigation to `/forgot-password`.

---

## Failure Scenarios

**FS-1: Empty Email**

- **Preconditions**: Login form visible; both fields blank.
- **Steps**: click Sign In.
- **Mock API**: not called — Zod blocks submit.
- **Expected UI behavior**: helperText under Email reads "Email is required"; no toast; URL unchanged.

**FS-2: Malformed Email**

- **Steps**: type `not-an-email`, fill any password ≥ 6 chars, submit.
- **Mock API**: not called.
- **Expected UI**: helperText "Please enter a valid email".

**FS-3: Short Password**

- **Steps**: type valid email + `123` (3 chars), submit.
- **Mock API**: not called.
- **Expected UI**: helperText "Password must be at least 6 characters".

**FS-4: 401 Invalid credentials**

- **Mock API** (`POST /auth/login`, 401): `{ "detail": "Invalid email or password" }`
- **Expected UI**: error toast title "Invalid email or password" (5000 ms default duration); form remains populated; button re-enables.

**FS-5: 401 Account is deactivated**

- **Mock API** (`POST /auth/login`, 401): `{ "detail": "Account is deactivated" }`
- **Expected UI**: toast title "Account is deactivated"; no yellow banner (detail does not contain `verify`).

**FS-6: 401 Please verify your email before logging in**

- **Mock API** (`POST /auth/login`, 401): `{ "detail": "Please verify your email before logging in" }`
- **Expected UI**: toast title "Please verify your email before logging in"; yellow banner appears with the "Resend verification email" button.

**FS-7: 400 Missing fields**

- **Mock API** (`POST /auth/login`, 400): `{ "detail": "Email and password are required" }`
- **Expected UI**: toast title "Email and password are required". (In practice unreachable when Zod is healthy — see PS-5 caveat about the form not gating submit on `isValid`.)

**FS-8: 422 Validation error**

- **Mock API** (`POST /auth/login`, 422):
  ```json
  { "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
  ```
- **Expected UI**: `handleApiError` falls back to "Something went wrong. Please try again." (detail is not a string).

**FS-9: 500 Internal Server Error**

- **Mock API** (`POST /auth/login`, 500): `{ "detail": "Internal Server Error" }`
- **Expected UI**: toast title "Internal Server Error"; button re-enables.

**FS-10: Network failure / no response**

- **Mock API**: route aborted with `failed` status.
- **Expected UI**: `handleApiError` shows toast "Something went wrong. Please try again." (no response object on `error`).

**FS-11: Resend verification 400 already verified**

- **Preconditions**: yellow banner visible (WF-3).
- **Mock API** (`POST /auth/resend-verification`, 400): `{ "detail": "Email is already verified" }`
- **Expected UI**: toast title "Email is already verified"; banner persists.

**FS-12: Resend verification with empty email**

- **Steps**: clear the Email field while the banner is visible, then click Resend.
- **Expected UI**: button is `disabled` (`!email`); no network call.

**FS-13: Double-submit guard**

- **Steps**: click Sign In twice in rapid succession against a slow backend.
- **Expected UI**: second click is a no-op — the `<Button>` is `disabled` while `loading=true`; only one `POST /auth/login` is recorded.

**FS-14: Trailing whitespace in email**

- **Steps**: type `  user@acme.com  ` (no client-side trim today).
- **Mock API** (`POST /auth/login`, 401): backend rejects, returns `{ "detail": "Invalid email or password" }`.
- **Expected UI**: toast "Invalid email or password" — ⚠ unverified whether the backend normalises the email.

**FS-15: Backend returns malformed JSON**

- **Mock API** (`POST /auth/login`, 200, body: `"not-json"`).
- **Expected UI**: axios rejects; `handleApiError` falls back to "Something went wrong. Please try again."

**FS-16: Authenticated visit to `/auth/login` redirects to `/home`**

- **Preconditions**: localStorage has a valid (non-expired) `access_token` / `login_data` and the user lands on `/auth/login`.
- **Expected UI**: client-side guard (or middleware once wired) redirects to `/home`; login form is never rendered. ⚠ Document the current behaviour exactly — today the form renders. Update this scenario if a future iteration adds the redirect.

**FS-17: Slow API (>3s) keeps Sign In button in loading state**

- **Mock API** (`POST /auth/login`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button text remains "Loading..." with `disabled` for the full duration; no second `POST /auth/login` fires if the user clicks again; success toast and redirect happen only after the response resolves.

**FS-18: Network failure / offline during submit preserves form data**

- **Mock API**: route aborted to simulate offline.
- **Expected UI**: toast "Something went wrong. Please try again."; Email and Password inputs still contain the typed values; button re-enables for retry.

**FS-19: Email with embedded XSS / special chars**

- **Steps**: type `<script>alert(1)</script>@x.com` into Email and any password ≥ 6 chars; submit.
- **Expected UI**: Zod's `.email()` rejects → helperText "Please enter a valid email"; no `POST /auth/login` fires; the literal `<script>` text is rendered as plain text in the input value (no HTML injection in the DOM).

**FS-20: Emoji / unicode in password**

- **Steps**: type a valid email and `pass🔥word` (8 chars including emoji); submit.
- **Mock API** (`POST /auth/login`, 200): success.
- **Expected UI**: payload includes the emoji verbatim (no encoding errors); login succeeds and redirects to `/home`.

**FS-21: Very long password (>500 chars)**

- **Steps**: type a 600-char password.
- **Expected UI**: input accepts the value (no client-side maxlength); `POST /auth/login` fires with the full string; backend response (likely 401 invalid creds) is surfaced as a toast — form stays intact.

**FS-22: Paste with newlines into Email input**

- **Steps**: paste `user@acme.com\nextra` into the Email field.
- **Expected UI**: single-line `type="email"` input strips the newline at paste time; value becomes `user@acme.com extra` or `user@acme.com` depending on browser behaviour; Zod surfaces "Please enter a valid email" if the residual value is invalid. ⚠ unverified — confirm browser behaviour for `type="email"` paste.

**FS-23: Tab order through the form**

- **Steps**: focus Email → press Tab repeatedly.
- **Expected UI**: focus moves Email → Password → password Eye toggle → Remember me → Forgot password → (verify-banner button if visible) → Sign In → "Sign in with a code instead" → "Sign up" in the order documented in the Accessibility section.

**FS-24: Submit via Enter key in Password**

- **Steps**: fill valid Email and Password, focus the Password input, press Enter.
- **Expected UI**: form submits as if Sign In was clicked; `POST /auth/login` fires once.

**FS-25: Helper-text errors are announced via aria-live**

- **Steps**: submit with empty Email.
- **Expected UI**: helperText element renders with `role="alert"` (or `aria-live`), so screen readers announce "Email is required" without focus change.

**FS-26: Browser back from `/home` after login**

- **Preconditions**: PS-1 completed; user is now on `/home`.
- **Steps**: press browser Back.
- **Expected UI**: history returns to `/auth/login` URL; since the user is now authenticated, the FS-16 redirect (when implemented) sends them straight back to `/home`. Today (no redirect) the login form is shown but submitting again is harmless.

### Full lifecycle (`*-FULL`)

**LG-FULL: End-to-end login lifecycle in a single test**

- **Preconditions**: A test user `__e2e__login_<uuid>@example.com` is provisioned via a backend API setup call inside the test (NOT mocked).
- **Steps in one Playwright test body**:
  1. Visit `/auth/login` without auth cookie → expect form rendered.
  2. Submit with empty fields → expect inline "Email is required" + "Password must be at least 6 characters".
  3. Submit malformed email → expect "Please enter a valid email".
  4. Submit wrong-password against the provisioned user → expect toast "Invalid email or password"; form stays populated.
  5. Submit correct credentials → expect toast "Welcome back!" and URL `/home`.
  6. Press Back → expect URL `/auth/login` (form re-rendered today; redirect when implemented).
  7. Click "Forgot password?" → expect URL `/forgot-password`.
  8. Click browser Back → expect URL `/auth/login`.
  9. Click "Sign in with a code instead" → expect URL `/sign-in-with-code`.
  10. Click browser Back → expect URL `/auth/login`.
  11. Click "Sign up" → expect URL `/signup`.
- **Cleanup (in `finally`)**: Delete the test user via the backend admin API; clear cookies/localStorage. Cleanup runs in the same test body — no `afterEach` hook.
- **Naming**: `LG-FULL — login full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. Sonner renders title and (optional) description as separate elements inside `[data-sonner-toast]`. `handleApiError` (in `src/lib/toast.ts`) passes the backend `response.data.detail` string as the toast **title** (no description). When `detail` is not a string, it uses the title `Something went wrong. Please try again.`

| Trigger                                          | Toast title                                            | Toast description | Variant |
| ------------------------------------------------ | ------------------------------------------------------ | ----------------- | ------- |
| Successful login                                 | `Welcome back!`                                        | —                 | success |
| Resend verification succeeds                     | `Verification email sent!`                             | —                 | success |
| 401 invalid credentials                          | `Invalid email or password`                            | —                 | error   |
| 401 account deactivated                          | `Account is deactivated`                               | —                 | error   |
| 401 email not verified                           | `Please verify your email before logging in`           | —                 | error   |
| 400 missing fields                               | `Email and password are required`                      | —                 | error   |
| 5xx with string `detail`                         | (verbatim `detail`, e.g. `Internal Server Error`)      | —                 | error   |
| Any error where `detail` is not a string         | `Something went wrong. Please try again.`              | —                 | error   |

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
| Sign up CTA                   | Link            | "Sign up" (after "Don't have an account?")       | Navigates to `/signup`                                        |
| Logo (layout)                 | Logo            | Tone logo                                        | In the left column header                                     |
| ThemeToggle (layout)          | Button          | Sun / Moon                                       | Toggles `next-themes`                                         |

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
| Already authenticated visit                   | (stays on `/login`)                  | No automatic redirect today ⚠ unverified  |

---

## API Contracts

Payloads sourced from the Postman collection (`postman_collection/Tone-API.postman_collection.json`, folder `Authentication`). Endpoint base path is `/api/v1` (injected by `src/utils/axios.ts` via `BACKEND_URL`).

| Endpoint                       | Method | Request                                                | Success Response                                                | Error Response                  |
| ------------------------------ | ------ | ------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------- |
| `/auth/login`                  | POST   | `{ "email": string, "password": string }`              | 200 `AuthLoginResponse` (see below)                             | `{ "detail": "..." }`           |
| `/auth/resend-verification`    | POST   | `{ "email": string }`                                  | 200 `{ "message": "..." }`                                      | `{ "detail": "..." }`           |

### Example: `POST /auth/login`

Request body:

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!"
}
```

200 OK response body:

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "owner@acme.com",
    "role": "owner",
    "is_verified": true
  },
  "organization": { "id": "00000000-0000-0000-0000-000000000100", "name": "Acme" },
  "role": "owner"
}
```

401 Unauthorized — invalid creds:

```json
{ "detail": "Invalid email or password" }
```

401 Unauthorized — deactivated:

```json
{ "detail": "Account is deactivated" }
```

401 Unauthorized — needs verification:

```json
{ "detail": "Please verify your email before logging in" }
```

400 Bad Request:

```json
{ "detail": "Email and password are required" }
```

422 Validation Error:

```json
{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
```

### Example: `POST /auth/resend-verification`

Request body:

```json
{ "email": "owner@acme.com" }
```

200 OK:

```json
{ "message": "If the email exists, a verification link has been sent" }
```

400 Bad Request:

```json
{ "detail": "Email is already verified" }
```

State after success is owned by Zustand `useAuthStore.setLoginResponse(data)` (`src/stores/auth.ts`), which writes to localStorage: `access_token`, `refresh_token`, `login_data`, `user_id`, and `active_org_id` (from `data.organization.id` or `data.organizations[0].id`).

---

## Edge Cases

- [ ] Token already in localStorage when visiting `/login` — no client-side redirect today; submitting succeeds and re-hydrates the store
- [ ] `?next` is missing — defaults to `/home`
- [ ] `?next` does not start with `/` (e.g. `?next=evil.com`) — open-redirect guard falls back to `/home`
- [ ] `?next` is a relative path with query/hash (e.g. `?next=/agents?tab=outbound`) — pushed verbatim; ⚠ unverified that nested query params are not double-encoded
- [ ] Double-submit — `<Button>` `disabled` during `login.isPending` prevents the second click from firing `POST /auth/login`
- [ ] Password field with trailing whitespace — submitted verbatim (no client-side trim)
- [ ] Email field with leading/trailing whitespace — submitted verbatim; backend normalisation behaviour ⚠ unverified
- [ ] Backend returns 200 but `access_token` missing — `setLoginResponse` skips the localStorage write for that field but still flips `isAuthenticated: true` if any token-like field is present; subsequent dashboard mount will fail axios auth — ⚠ unverified, treat as backend contract violation
- [ ] User clicks Resend verification with the banner visible, then changes the Email — the resend call uses the latest `watch('email')` value
- [ ] The Suspense fallback is `null`, so during the initial mount of the `useSearchParams`-dependent inner component the page area is briefly empty (no flash of "Loading…")
- [ ] Hitting Enter in the password field submits the form (RHF's default form behaviour)
- [ ] `needsVerification` is true only when **the backend's `detail` string contains `verify`** — a future copy change ("please confirm your email") would silently disable the resend banner
- [ ] Browser autofill — both inputs use `name="email"` / `name="password"` so password managers can match them

---

## Business Rules

- Login is **public**; no auth header is sent on the request itself (Axios interceptor still attaches `Authorization` if a token happens to be in localStorage but the backend ignores it on this endpoint)
- Successful login overwrites any existing `access_token` / `refresh_token` / `login_data` / `active_org_id` in localStorage with the fresh response — there is no merge step
- The selected organization after login is `data.organization.id` (preferred) or the first entry in `data.organizations[]` (fallback); the user can switch orgs after they reach the dashboard
- Email verification is gated by the backend; the frontend never decides locally whether the account is verified
- The "Remember me" checkbox is currently **cosmetic** — toggling it does not change cookie/localStorage lifetimes (no expiration is set by the client; refresh-token lifetime is governed by the backend)
- The login endpoint never returns a 403; deactivated and unverified are both 401s with distinct `detail` strings, and the frontend branches on the substring `verify` to show the yellow banner

---

## Accessibility Requirements

- [ ] Tab order: Email → Password → Remember me → Forgot password → (banner button if visible) → Sign In → "Sign in with a code instead" → "Sign up"
- [ ] Email input has `label="Email"` (via shared `TextInput`)
- [ ] Password input is associated with `<label htmlFor="password">Password</label>` and has `name="password"` so password managers can match it
- [ ] Validation errors render under the input as `helperText`, not as a toast (avoids screen-reader churn)
- [ ] Submit button announces its loading state with the literal text "Loading..." rather than only a spinner
- [ ] Toast container has `aria-live="polite"` (Sonner default); error toasts default to 5000 ms so screen readers have time to announce
- [ ] The form trap is the page itself — no modal/dialog is involved; focus is preserved across re-renders by RHF
- [ ] Theme toggle in the layout has an accessible name; the layout heading hierarchy is `<h1>` (right column branding) + `<h2>` (form heading) — no skipped levels
