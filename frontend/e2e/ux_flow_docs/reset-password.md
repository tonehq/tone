# Feature Doc: Reset Password

Feature documentation for the `/reset-password` page. Used by
`/generate-tests reset-password` (or `--docs e2e/ux_flow_docs/reset-password.md`) to
ensure all positive and negative user cases are covered alongside the
component source analysis.

The reset-password page is the second leg of the password reset round-trip.
The user arrives via the email link with a `?token=...` query param, enters a
new password + confirmation, and the backend exchanges the token for a
password update. Successful reset shows a success panel and a "Sign In" CTA
back to `/login`.

---

## Page

- **Route**: `/reset-password` (under the `(auth)` route group)
- **Component**: `src/app/(auth)/reset-password/page.tsx` — default export `ResetPasswordPage` wraps the inner client component `ResetPasswordContent` in `<Suspense fallback={<AppLoader className="animate-page" />}>` because the inner reads `useSearchParams()` for the `token` param
- **Layout**: `src/app/(auth)/layout.tsx` — shared with the rest of `(auth)/*`
- **Auth required**: no — this is a **public** page
- **Redirect when already authenticated**: not enforced today (no `src/middleware.ts`). A signed-in user can still load `/reset-password?token=...` and submit. ⚠ unverified whether a future iteration adds a client-side redirect

---

## URL Parameters

| Param  | Required | Purpose                                         | Source                |
| ------ | -------- | ----------------------------------------------- | --------------------- |
| `token`| yes      | Reset token issued by the backend's email link  | `searchParams.get('token')` |

When `token` is missing or empty, a `useEffect` fires `showToast.error('Invalid reset link')` and immediately calls `router.push('/forgot-password')`. The component also returns `null` from its render (no flash of the form). The token is **never read on the client** — it is forwarded verbatim to the backend in the `POST /auth/reset-password` body as `token`.

---

## User Stories

### US-1: Set a new password using the email link

**As a** user who clicked the reset link in my inbox, **I want to** enter a new password twice and submit, **so that** my account password is updated and I can sign in.

**Acceptance criteria**:

- [ ] Heading reads "Set new password" with subtitle "Enter your new password below"
- [ ] Two fields render: New Password (`type="password"`, placeholder `Min. 8 characters`), Confirm Password (`type="password"`, placeholder `Confirm your password`)
- [ ] Both fields show the required indicator
- [ ] Submit button label is "Reset Password"; loading state is "Loading..."
- [ ] On 200, the form is replaced by a green `CheckCircle`-icon panel that reads "Password Reset!" with body "Your password has been reset successfully." and a primary "Sign In" button linking to `/login`
- [ ] A success toast "Password reset successfully" appears (3 s default duration)

### US-2: Reject missing / invalid token early

**As the** system, **I want to** redirect users with a missing token away from this page, **so that** they cannot try to submit a useless form.

**Acceptance criteria**:

- [ ] If `token` is missing or empty on mount, `showToast.error('Invalid reset link')` fires immediately and the page navigates to `/forgot-password`
- [ ] The form does not render in this case (component returns `null`)

### US-3: Block submission on client-side validation errors

**As a** user, **I want to** see field-level errors before submission, **so that** I do not waste a network round-trip on a malformed payload.

**Acceptance criteria**:

- [ ] Password under 8 chars → helperText "Password must be at least 8 characters"
- [ ] Empty Confirm Password → helperText "Please confirm your password"
- [ ] Passwords do not match → helperText "Passwords do not match" (rendered on the `confirm_password` field via Zod `path: ['confirm_password']`)
- [ ] While `mutation.isPending === true`, Submit button shows "Loading..." with `disabled`

### US-4: Recover from "invalid or expired token"

**As a** user who used a stale email link, **I want to** see a clear error message, **so that** I know to request a new link from `/forgot-password`.

**Acceptance criteria**:

- [ ] Backend 400 `{"detail": "Invalid or expired reset token"}` → toast title "Invalid or expired reset token"
- [ ] Form stays editable; user can navigate to `/forgot-password` via the "Back to login" link → "Forgot password" link chain

---

## User Workflow Steps

**WF-1: Successful password reset → success panel** (positive)

1. User clicks the email link → expected: lands on `/reset-password?token=raw-reset-token-from-email`
2. `useEffect` reads `token` → expected: token is truthy, no redirect; form renders inside the Suspense boundary (fallback `AppLoader` is only visible during the initial Suspense resolve)
3. User types `newSecret123` into New Password and `newSecret123` into Confirm Password → expected: Zod resolver clears helperText (passwords match and length ≥ 8)
4. User clicks **Reset Password** → expected: button enters loading; `POST /auth/reset-password` fires with `{ token, new_password }`
5. Response is 200 with `{"message": "Password reset successfully"}` → expected: success toast "Password reset successfully" (3 s default)
6. `mutation.isSuccess` becomes true → expected: form is replaced by the success panel — green `CheckCircle` icon, heading "Password Reset!", body "Your password has been reset successfully.", primary "Sign In" button linking to `/login`

**WF-2: Missing `token` query param → bounce** (negative)

1. User visits `/reset-password` (no query string) → expected: `useEffect` fires `showToast.error('Invalid reset link')` and `router.push('/forgot-password')`
2. Render returns `null` so the form does not flash

**WF-3: Empty `token` query param → bounce** (negative)

1. User visits `/reset-password?token=` → expected: same as WF-2 (empty string is falsy)

**WF-4: Passwords do not match** (negative)

1. User types `newSecret123` and `OTHER_pass456` → expected: helperText "Passwords do not match" appears under Confirm Password
2. Submit is gated; no `POST /auth/reset-password` is fired

**WF-5: Invalid or expired token** (negative)

1. User submits a stale link's token → expected: 400 `{"detail": "Invalid or expired reset token"}`
2. `handleApiError(err)` surfaces toast "Invalid or expired reset token"; form remains editable; success panel does NOT render

**WF-6: Password too short** (negative)

1. User types `short` (5 chars) → expected: helperText "Password must be at least 8 characters" under New Password
2. Submit is gated

**WF-7: Already-authenticated visit** (edge)

1. User has `access_token` in localStorage and visits `/reset-password?token=...` → expected: page still renders (no automatic redirect today); submitting still updates the backend account password

**WF-8: Back-to-login link** (positive)

1. User clicks the inline "Back to login" link below the form → expected: navigation to `/login`

**WF-9: Sign In from the success panel** (positive)

1. User reaches the success panel (WF-1)
2. User clicks the primary **Sign In** button → expected: navigation to `/login`

---

## Input Specifications

Source: `src/schemas/auth.ts` (`resetPasswordSchema`).

| Field             | Type     | Required | Validation Rules                                                                              | Exact Error Message                       |
| ----------------- | -------- | -------- | --------------------------------------------------------------------------------------------- | ----------------------------------------- |
| New Password      | password | yes      | `z.string().min(8)`                                                                           | "Password must be at least 8 characters"  |
| Confirm Password  | password | yes      | `z.string().min(1)`                                                                           | "Please confirm your password"            |
| (cross-field)     | —        | —        | `.refine(data => data.password === data.confirm_password)` with `path: ['confirm_password']`  | "Passwords do not match" (on confirm field) |

**Button state rules:**

- "Reset Password" is **never disabled** by `formState.isValid`; invalid submit surfaces inline helperText instead
- While `mutation.isPending === true`, the shadcn `<Button>` renders "Loading..." and sets `disabled`
- Once `mutation.isSuccess === true`, the entire form unmounts and the success panel renders — there is no way back to the form on this page

---

## Success Scenarios

**PS-1: Valid token + matching passwords → success panel**

- **Preconditions**: not authenticated; URL has `?token=raw-reset-token-from-email`.
- **Steps**: type `newSecret123` in both fields → click Reset Password.
- **Expected outcome**: success toast "Password reset successfully"; form replaced by success panel (green checkmark, "Password Reset!", "Sign In" button).
- **Mock API** (`POST /auth/reset-password`, 200):
  ```json
  { "message": "Password reset successfully" }
  ```

**PS-2: Long valid password (max length boundary)**

- **Steps**: type a 64-char password in both fields; submit.
- **Expected outcome**: same as PS-1 (no upper bound enforced client-side).

**PS-3: Click Sign In from the success panel**

- **Preconditions**: PS-1 reached.
- **Steps**: click "Sign In" inside the success panel.
- **Expected outcome**: navigation to `/login`.

**PS-4: Suspense fallback briefly visible**

- **Preconditions**: slow client hydration.
- **Steps**: hard-reload `/reset-password?token=...`.
- **Expected outcome**: `AppLoader` (with class `animate-page`) renders momentarily before the form appears; this is the `<Suspense fallback={...}>` boundary because `ResetPasswordContent` reads `useSearchParams()`.

**PS-5: Loading indicator visible during slow submit**

- **Preconditions**: backend deliberately slow (300 ms).
- **Steps**: submit valid form.
- **Expected outcome**: button shows "Loading..." with `disabled`; user cannot double-click.

**PS-6: Back-to-login link works while form is editable**

- **Steps**: click inline "Back to login" link.
- **Expected outcome**: navigation to `/login`.

---

## Failure Scenarios

**FS-1: Missing `token` query param → bounce + toast**

- **Preconditions**: URL is `/reset-password` (no query string).
- **Steps**: visit the URL.
- **Mock API**: not called.
- **Expected UI**: `showToast.error('Invalid reset link')` (5000 ms default error duration); `router.push('/forgot-password')` fires; render returns `null` (form does not flash).

**FS-2: Empty `token` query param → bounce + toast**

- **Preconditions**: URL is `/reset-password?token=`.
- **Expected UI**: same as FS-1 (empty string is falsy).

**FS-3: Empty New Password**

- **Preconditions**: valid token; form visible.
- **Mock API**: not called.
- **Expected UI**: helperText "Password must be at least 8 characters" under New Password (empty fails `min(8)`).

**FS-4: Empty Confirm Password**

- **Steps**: fill New Password, leave Confirm blank, submit.
- **Mock API**: not called.
- **Expected UI**: helperText "Please confirm your password" under Confirm Password.

**FS-5: Short Password (< 8 chars)**

- **Steps**: type `7chars7` (7 chars) in both fields.
- **Expected UI**: helperText "Password must be at least 8 characters" under New Password (the refine for match runs after the per-field rules pass).

**FS-6: Passwords do not match**

- **Steps**: type `valid12345` and `OTHER67890`.
- **Mock API**: not called.
- **Expected UI**: helperText "Passwords do not match" under Confirm Password (Zod `refine` with `path: ['confirm_password']`).

**FS-7: 400 Invalid or expired reset token**

- **Preconditions**: stale token in URL.
- **Mock API** (`POST /auth/reset-password`, 400): `{ "detail": "Invalid or expired reset token" }`
- **Expected UI**: toast title "Invalid or expired reset token"; form stays editable; button re-enables; success panel does NOT render.

**FS-8: 400 token and new_password are required**

- **Mock API** (`POST /auth/reset-password`, 400): `{ "detail": "token and new_password are required" }`
- **Expected UI**: toast title "token and new_password are required". (Unreachable under healthy Zod, since both fields are required client-side.)

**FS-9: 400 Password must be at least 8 characters (server echo)**

- **Mock API** (`POST /auth/reset-password`, 400): `{ "detail": "Password must be at least 8 characters" }`
- **Expected UI**: toast title "Password must be at least 8 characters"; form stays editable.

**FS-10: 404 User not found**

- **Mock API** (`POST /auth/reset-password`, 404): `{ "detail": "User not found" }`
- **Expected UI**: toast title "User not found"; form stays editable.

**FS-11: 422 Validation error**

- **Mock API** (`POST /auth/reset-password`, 422):
  ```json
  { "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
  ```
- **Expected UI**: `handleApiError` falls back to "Something went wrong. Please try again." (detail is not a string).

**FS-12: 500 Internal Server Error**

- **Mock API** (`POST /auth/reset-password`, 500): `{ "detail": "Internal Server Error" }`
- **Expected UI**: toast title "Internal Server Error"; form re-enables.

**FS-13: Network failure**

- **Mock API**: route aborted.
- **Expected UI**: toast "Something went wrong. Please try again." (no response object).

**FS-14: Double-submit guard**

- **Steps**: click Reset Password twice in rapid succession against a slow backend.
- **Expected UI**: second click is a no-op (button disabled while `mutation.isPending`); exactly one `POST /auth/reset-password` is recorded.

**FS-15: Token reuse (already-consumed token)**

- **Preconditions**: token was already used for a previous reset.
- **Mock API** (`POST /auth/reset-password`, 400): `{ "detail": "Invalid or expired reset token" }`
- **Expected UI**: same as FS-7.

**FS-16: Slow API (>3s) keeps Reset Password button in loading state**

- **Mock API** (`POST /auth/reset-password`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button text stays "Loading..." with `disabled` for the full duration; clicking again is a no-op; success panel appears only after the response resolves.

**FS-17: Network failure during submit preserves form data**

- **Mock API**: route aborted.
- **Expected UI**: toast "Something went wrong. Please try again."; both password inputs still contain typed values; button re-enables.

**FS-18: Password with XSS / special chars**

- **Steps**: type `<script>alert(1)</script>x123` in both password fields; submit with valid token.
- **Mock API** (`POST /auth/reset-password`, 200): success.
- **Expected UI**: payload sends the literal string; success panel renders normally; no DOM injection from the password.

**FS-19: Password with emoji / unicode**

- **Steps**: type `pass🔥word1` in both fields; submit.
- **Mock API** (`POST /auth/reset-password`, 200): success.
- **Expected UI**: payload includes the emoji verbatim; success panel renders.

**FS-20: Very long password (>500 chars)**

- **Steps**: type a 600-char password in both fields; submit.
- **Expected UI**: input accepts (no maxLength); backend may reject — surface its `detail`. If accepted, success panel renders.

**FS-21: Paste with newlines into password fields**

- **Steps**: paste `newSecret\n123` into New Password.
- **Expected UI**: single-line `type="password"` input strips the newline at paste time; resulting value passes Zod's `min(8)` if length permits.

**FS-22: Whitespace-only password fails validation**

- **Steps**: type `        ` (8 spaces) in both fields; submit.
- **Expected UI**: ⚠ today Zod `min(8)` passes because length is 8; payload is sent. Document the gap — tighten schema with `.trim()` and re-check if needed.

**FS-23: Tab order through the form**

- **Steps**: focus New Password → press Tab repeatedly.
- **Expected UI**: focus moves New Password → New Password Eye toggle → Confirm Password → Confirm Password Eye toggle → Reset Password → "Back to login" inline link.

**FS-24: Submit via Enter key in Confirm Password**

- **Steps**: fill both fields with valid matching passwords, focus Confirm Password, press Enter.
- **Expected UI**: form submits exactly as a click on Reset Password would; `POST /auth/reset-password` fires once.

**FS-25: Helper-text errors are announced via aria-live**

- **Steps**: submit with mismatched passwords.
- **Expected UI**: helperText "Passwords do not match" under Confirm Password renders with `role="alert"` (or `aria-live`) so screen readers announce the mismatch.

**FS-26: Browser back from success panel**

- **Preconditions**: WF-1 completed; user is on the success panel.
- **Steps**: press browser Back.
- **Expected UI**: URL unchanged (in-component swap); pressing Back exits `/reset-password` to the previous page. If user re-navigates to the same URL the consumed token now returns 400.

**FS-27: Authenticated visit with `?token=` proceeds normally**

- **Preconditions**: localStorage has valid `access_token` (different user) and the URL is `/reset-password?token=<valid>`.
- **Expected UI**: form renders; submitting updates the password of the **token's owner** (not the logged-in user); after success the success panel renders. Treat as documented edge — no auto-redirect today.

**FS-28: Token query param with leading / trailing whitespace**

- **Preconditions**: URL is `/reset-password?token=%20valid%20` (URL-encoded spaces).
- **Expected UI**: `searchParams.get('token')` returns the value verbatim; payload sends ` valid ` to the backend → likely 400 "Invalid or expired reset token".

### Full lifecycle (`*-FULL`)

**RP-FULL: End-to-end reset-password lifecycle in a single test**

- **Preconditions**: A test user `__e2e__rp_<uuid>@example.com` is provisioned via the backend API. A valid reset token is fetched by triggering `POST /auth/forgot-password` against the same user and reading the token from the backend (test-only admin endpoint or DB peek).
- **Steps in one Playwright test body**:
  1. Visit `/reset-password` (no token) → expect toast "Invalid reset link" and redirect to `/forgot-password`.
  2. Navigate to `/reset-password?token=` → expect same bounce.
  3. Navigate to `/reset-password?token=<valid>` → expect form rendered.
  4. Submit with empty passwords → expect helperText "Password must be at least 8 characters".
  5. Type `short` in both → expect helperText "Password must be at least 8 characters".
  6. Type `valid12345` and `OTHER67890` → expect helperText "Passwords do not match" on Confirm.
  7. Type matching `validNew123` in both → submit → expect toast "Password reset successfully" and success panel with "Password Reset!" heading.
  8. Click "Sign In" inside the success panel → expect URL `/login`.
  9. Sign in with the new password against the provisioned user → expect successful login (verifies the password was actually updated).
  10. Re-visit `/reset-password?token=<valid>` with the same (now consumed) token → submit → expect toast "Invalid or expired reset token".
  11. Click inline "Back to login" → expect URL `/login`.
- **Cleanup (in `finally`)**: Delete the provisioned user via the backend admin API; clear cookies/localStorage.
- **Naming**: `RP-FULL — reset-password full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. Title and description render in separate elements inside `[data-sonner-toast]`. `handleApiError` (in `src/lib/toast.ts`) passes the backend `response.data.detail` string as the toast **title** (no description); when `detail` is not a string, it uses the title "Something went wrong. Please try again."

| Trigger                                          | Toast title                                  | Toast description | Variant |
| ------------------------------------------------ | -------------------------------------------- | ----------------- | ------- |
| Successful reset                                 | `Password reset successfully`                | —                 | success |
| Missing or empty `?token=`                       | `Invalid reset link`                         | —                 | error   |
| 400 invalid/expired token                        | `Invalid or expired reset token`             | —                 | error   |
| 400 missing fields                               | `token and new_password are required`        | —                 | error   |
| 400 short password (server echo)                 | `Password must be at least 8 characters`     | —                 | error   |
| 404 user not found                               | `User not found`                             | —                 | error   |
| Any 5xx with string `detail`                     | (verbatim, e.g. `Internal Server Error`)     | —                 | error   |
| Any error where `detail` is not a string         | `Something went wrong. Please try again.`    | —                 | error   |

---

## UI Elements

| Element                       | Type            | Content / Label                                       | Behavior                                                  |
| ----------------------------- | --------------- | ----------------------------------------------------- | --------------------------------------------------------- |
| Heading                       | h2              | "Set new password"                                    | Static                                                    |
| Subtitle                      | p               | "Enter your new password below"                       | Static                                                    |
| New Password input            | TextInput (pwd) | label "New Password", placeholder "Min. 8 characters" | Required, min 8 chars (Zod)                               |
| Confirm Password input        | TextInput (pwd) | label "Confirm Password", placeholder "Confirm your password" | Required, must match `password`                    |
| Reset Password button         | Button          | "Reset Password" → "Loading..."                       | `type="submit"`; disabled while `mutation.isPending`      |
| Back to login (inline link)   | Link            | "Back to login" + `ArrowLeft` icon                    | Navigates to `/login`                                     |
| CheckCircle icon (success)    | lucide icon     | `CheckCircle` (green)                                 | Renders only in the success panel                         |
| Success heading               | h2              | "Password Reset!"                                     | Renders only after `mutation.isSuccess === true`          |
| Success body                  | p               | "Your password has been reset successfully."          | Static                                                    |
| Sign In button (success)      | Button          | "Sign In"                                             | Wrapped in `<Link href="/login">` — navigates to `/login` |
| Suspense fallback             | AppLoader       | spinner with class `animate-page`                     | Visible while the inner `useSearchParams` consumer hydrates |

---

## Navigation

| Trigger                                  | Destination                          | Condition                              |
| ---------------------------------------- | ------------------------------------ | -------------------------------------- |
| Successful submit (200)                  | (stays on `/reset-password`)         | Form swaps to the success panel        |
| Click "Sign In" (success panel)          | `/login`                             | Always                                 |
| Click "Back to login" (form)             | `/login`                             | Always                                 |
| Missing or empty `?token=`               | `/forgot-password`                   | On mount (via `useEffect`)             |
| Already authenticated visit              | (stays on `/reset-password`)         | No automatic redirect today ⚠ unverified |

---

## API Contracts

Payloads sourced from the Postman collection (folder `Authentication`).

| Endpoint                | Method | Request                                                | Success Response                              | Error Response          |
| ----------------------- | ------ | ------------------------------------------------------ | --------------------------------------------- | ----------------------- |
| `/auth/reset-password`  | POST   | `{ "token": string, "new_password": string }`          | 200 `{ "message": "Password reset successfully" }` | `{ "detail": "..." }`   |

### Example: `POST /auth/reset-password`

Request body:

```json
{
  "token": "raw-reset-token-from-email",
  "new_password": "newSecret123"
}
```

200 OK response body:

```json
{ "message": "Password reset successfully" }
```

400 Bad Request — missing fields:

```json
{ "detail": "token and new_password are required" }
```

400 Bad Request — password too short:

```json
{ "detail": "Password must be at least 8 characters" }
```

400 Bad Request — invalid/expired token:

```json
{ "detail": "Invalid or expired reset token" }
```

404 Not Found:

```json
{ "detail": "User not found" }
```

422 Validation Error:

```json
{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
```

**Note**: The frontend sends only `token` and `new_password` — it does not send the user's email, because the backend resolves the user from the token. The token is forwarded verbatim from the URL query string (no client-side decoding or trimming).

---

## Edge Cases

- [ ] `?token=` is missing → toast "Invalid reset link" + redirect to `/forgot-password`
- [ ] `?token=` is an empty string → same as missing (empty string is falsy)
- [ ] `?token=` has URL-encoded chars (e.g. `+`, `%2F`) → `searchParams.get` URL-decodes once; the decoded value is forwarded verbatim
- [ ] Token already used → backend 400 "Invalid or expired reset token" → toast surfaces; form stays editable
- [ ] Token expired (past TTL) → same backend error path as above
- [ ] User clicks the reset link twice rapidly → first click consumes the token; second visit sees `mutation.isSuccess` only if both hit the same in-memory React Query cache (different tabs do not share cache, so the second tab will see a normal form load → submit → 400)
- [ ] Already-authenticated visit — submission still hits the endpoint and updates the password of the **token's owner**, regardless of who is signed in locally
- [ ] Suspense fallback `AppLoader` flashes only on first hydration; subsequent in-app navigations do not re-trigger it
- [ ] Browser back from the success panel → Next.js history pop returns to the editable form, but the success state is gone and `mutation.isSuccess` is true — render result is the success panel again unless TanStack Query state was reset (it is not — ⚠ unverified, treat as edge)
- [ ] Refresh after success — the URL still has the (consumed) token; the form re-renders editable; submitting hits 400 "Invalid or expired reset token"
- [ ] Confirm Password matches New Password but both are < 8 chars → field-level `min(8)` fires before the cross-field refine, so the user sees "Password must be at least 8 characters" (not "Passwords do not match")
- [ ] Password contains the user's email or username — accepted client-side; backend may or may not reject ⚠ unverified
- [ ] Trailing whitespace in password — submitted verbatim (no trim)
- [ ] Enter key in either password field submits the form (RHF default)
- [ ] Long password (> 1 KB) — accepted client-side; backend may reject ⚠ unverified

---

## Business Rules

- The reset token is **single-use** — the backend invalidates it after a successful exchange
- The token has a TTL (backend-controlled); after expiry the same `Invalid or expired reset token` error surfaces
- Password minimum length is enforced at 8 characters both client-side (Zod) and server-side; the client and server messages are identical strings
- The frontend never displays or persists the reset token — it is read from the URL and forwarded straight to the backend
- This page is **public** — no `Authorization` header is required for the reset call (the Axios interceptor still attaches one if a token happens to be in localStorage; the backend ignores it for this endpoint)
- A successful reset **does not auto-log the user in** — the user must visit `/login` and authenticate with the new password (the response only contains a `message` string, no JWT)
- Token reuse, password reuse history, and password complexity rules beyond `min(8)` are backend concerns and surface as the appropriate `detail` strings
- The success panel uses a green color (Tailwind `green-100` / `green-600`) instead of the primary brand color — this is the only auth-flow success panel that does so, intentional visual reassurance after a security-sensitive action

---

## Accessibility Requirements

- [ ] Tab order: New Password → Confirm Password → Reset Password → Back to login link
- [ ] Both password inputs use the shared `TextInput` and have associated `<label>` elements via the `label` prop
- [ ] Required indicators are visible to sighted users **and** announced
- [ ] Validation errors render under the input as `helperText` (RHF `fieldState.error.message`) — not as toasts
- [ ] Cross-field "Passwords do not match" error is associated with the Confirm Password field via Zod `path: ['confirm_password']` — screen readers announce it under the correct input
- [ ] Submit button announces its loading state with "Loading..." text rather than only a spinner
- [ ] Toast container has `aria-live="polite"` (Sonner default); error toasts default to 5000 ms, success toasts to 3000 ms
- [ ] Suspense fallback `AppLoader` should have an accessible label (e.g. `role="status"` or `aria-label="Loading"`) — ⚠ unverified, confirm `AppLoader` markup
- [ ] Success panel heading "Password Reset!" preserves the heading hierarchy (layout `<h1>` then page `<h2>`)
- [ ] `CheckCircle` and `ArrowLeft` icons are decorative; surrounding text carries the meaning
- [ ] Focus does not auto-move on form → success-panel swap ⚠ unverified — a future iteration may want to focus the heading or the Sign In button for keyboard users
- [ ] No client-side autocomplete attributes are set on the password inputs; password managers should still match by `name="password"` / `name="confirm_password"` ⚠ unverified
