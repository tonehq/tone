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

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Valid token and matching passwords swap to success panel

**Preconditions**:
- User signed out
- URL contains `?token=raw-reset-token-from-email`

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `newSecret123` into New Password
3. Type `newSecret123` into Confirm Password
4. Click the "Reset Password" button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/reset-password` request is recorded
2. Request body equals `{ "token": "raw-reset-token-from-email", "new_password": "newSecret123" }`
3. Body does NOT contain `email` or `confirm_password` keys

**Observation 2 — Loading state during request**:
1. The "Reset Password" button text changes to "Loading..."
2. The "Reset Password" button has the `disabled` attribute

**Observation 3 — Success toast**:
1. A Sonner toast appears in `[data-sonner-toast]`
2. Toast title equals `Password reset successfully`
3. Toast variant is `success`

**Observation 4 — Form unmounts and success panel renders**:
1. The New Password and Confirm Password inputs are no longer in the DOM
2. A heading with text `Password Reset!` is visible
3. Body text reads `Your password has been reset successfully.`
4. A green `CheckCircle` icon is visible
5. A primary button labelled `Sign In` is in the DOM, wrapped in a `<Link href="/login">`

**API mock**: `POST /auth/reset-password` → 200 `{ "message": "Password reset successfully" }`.

**Cleanup**: Clear cookies and localStorage in `afterEach`.

---

### TC-HAPPY-002: Long valid password (boundary) succeeds

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type a 64-character password into New Password
3. Type the same 64-character password into Confirm Password
4. Click "Reset Password"

**Observation 1 — Request body includes full password**:
1. Request body `new_password` length equals 64

**Observation 2 — Success panel renders**:
1. Heading `Password Reset!` is visible

**API mock**: `POST /auth/reset-password` → 200 success.

---

### TC-HAPPY-003: Suspense fallback flashes briefly on first hydration

**Preconditions**: Slow client hydration; cold hard-reload.

**Action**:
1. Hard-reload `/reset-password?token=raw-reset-token-from-email`

**Observation 1 — Suspense fallback visible momentarily**:
1. An `AppLoader` element with class `animate-page` is in the DOM briefly
2. After hydration, the form (New Password, Confirm Password) replaces the loader

> Note: This is the `<Suspense fallback={...}>` boundary because `ResetPasswordContent` reads `useSearchParams()`.

---

### TC-VALIDATE-001: Empty New Password blocks submit

**Preconditions**: Valid token in URL; form visible.

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Leave both fields empty
3. Click "Reset Password"

**Observation 1 — No network call**:
1. Zero `POST /auth/reset-password` requests are recorded

**Observation 2 — Inline error under New Password**:
1. Helper text under New Password reads exactly `Password must be at least 8 characters`

> Note: Empty fails `min(8)`; no separate "required" message is shown.

---

### TC-VALIDATE-002: Empty Confirm Password blocks submit

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type a valid 8+ char password into New Password
3. Leave Confirm Password blank
4. Click "Reset Password"

**Observation 1 — No network call**:
1. Zero `POST /auth/reset-password` requests are recorded

**Observation 2 — Inline error under Confirm Password**:
1. Helper text under Confirm Password reads exactly `Please confirm your password`

---

### TC-VALIDATE-003: Short Password (< 8 chars) blocks submit

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `7chars7` (7 chars) into New Password
3. Type `7chars7` into Confirm Password
4. Click "Reset Password"

**Observation 1 — No network call**:
1. Zero `POST /auth/reset-password` requests are recorded

**Observation 2 — Inline error under New Password**:
1. Helper text under New Password reads exactly `Password must be at least 8 characters`

> Note: Field-level `min(8)` runs before the cross-field refine; "Passwords do not match" is not surfaced when both fields are too short.

---

### TC-VALIDATE-004: Passwords do not match blocks submit

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `valid12345` into New Password
3. Type `OTHER67890` into Confirm Password
4. Click "Reset Password"

**Observation 1 — No network call**:
1. Zero `POST /auth/reset-password` requests are recorded

**Observation 2 — Inline error under Confirm Password**:
1. Helper text under Confirm Password reads exactly `Passwords do not match`
2. The error is associated with the `confirm_password` field (Zod `path: ['confirm_password']`)

---

### TC-ERROR-001: 400 Invalid or expired token surfaces toast

**Preconditions**: stale token in URL.

**Action**:
1. Visit `/reset-password?token=stale-token`
2. Type matching valid passwords in both fields
3. Click "Reset Password"

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/reset-password` is recorded

**Observation 2 — Error toast**:
1. Toast title equals `Invalid or expired reset token`
2. Toast variant is `error`

**Observation 3 — Form stays editable**:
1. Both password inputs retain their values
2. "Reset Password" button re-enables
3. The success panel is NOT in the DOM

**API mock**: `POST /auth/reset-password` → 400 `{ "detail": "Invalid or expired reset token" }`.

---

### TC-ERROR-002: 400 token and new_password are required surfaces toast

**Action**:
1. Submit valid-format passwords (unreachable under healthy Zod, but backend may still return it for direct callers)

**Observation 1 — Error toast**:
1. Toast title equals `token and new_password are required`

**API mock**: `POST /auth/reset-password` → 400 `{ "detail": "token and new_password are required" }`.

---

### TC-ERROR-003: 400 server-side password-length echo surfaces toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Password must be at least 8 characters`

**Observation 2 — Form stays editable**:
1. Inputs preserved; button re-enables

**API mock**: `POST /auth/reset-password` → 400 `{ "detail": "Password must be at least 8 characters" }`.

---

### TC-ERROR-004: 404 User not found surfaces toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `User not found`

**Observation 2 — Form stays editable**:
1. Inputs preserved; button re-enables

**API mock**: `POST /auth/reset-password` → 404 `{ "detail": "User not found" }`.

---

### TC-ERROR-005: 422 with non-string `detail` falls back to generic toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`
2. Toast variant is `error`

**API mock**: `POST /auth/reset-password` → 422 `{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }`.

---

### TC-ERROR-006: 500 surfaces the verbatim string `detail`

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Form re-enables**:
1. Both inputs retain their values
2. Button re-enables

**API mock**: `POST /auth/reset-password` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-007: Network failure shows generic fallback toast

**Action**:
1. Submit valid-format payload

**Observation 1 — Error toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form state**:
1. Both password inputs still contain typed values
2. Button re-enables

**API mock**: route aborted (no response object).

---

### TC-ERROR-008: Token reuse (already-consumed token) yields 400

**Preconditions**: Token was already used for a previous reset.

**Action**:
1. Visit `/reset-password?token=already-used-token`
2. Submit matching valid passwords

**Observation 1 — Error toast**:
1. Toast title equals `Invalid or expired reset token`

**Observation 2 — Form stays editable**:
1. Inputs preserved; button re-enables

**API mock**: `POST /auth/reset-password` → 400 `{ "detail": "Invalid or expired reset token" }`.

---

### TC-NAV-001: Missing `?token=` triggers toast and redirect to /forgot-password

**Action**:
1. Visit `/reset-password` (no query string)

**Observation 1 — Error toast fires immediately**:
1. A Sonner toast with title `Invalid reset link` appears
2. Toast variant is `error`

**Observation 2 — Redirect happens on mount**:
1. URL becomes `/forgot-password` within 1s of mount

**Observation 3 — Form does not flash**:
1. The New Password and Confirm Password inputs are never visible in the DOM (render returns `null` while the `useEffect` redirect fires)

---

### TC-NAV-002: Empty `?token=` triggers toast and redirect

**Action**:
1. Visit `/reset-password?token=`

**Observation 1 — Same bounce as TC-NAV-001**:
1. Toast title equals `Invalid reset link`
2. URL becomes `/forgot-password`
3. The form does not render (empty string is falsy)

---

### TC-NAV-003: Click "Sign In" from success panel navigates to /login

**Preconditions**: TC-HAPPY-001 just completed; success panel is visible.

**Action**:
1. Click the primary "Sign In" button inside the success panel

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No full page reload**:
1. No full page reload occurs (client-side `<Link>`)

---

### TC-NAV-004: Click inline "Back to login" link while form is editable

**Preconditions**: Valid token in URL; form visible.

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Click the inline "Back to login" link below the form

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No network call**:
1. Zero `POST /auth/reset-password` requests are recorded

---

### TC-LOADING-001: Slow API keeps Reset Password button in loading state

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type matching valid passwords
3. Click "Reset Password" against a deliberately slow backend (3500 ms)

**Observation 1 — Button label**:
1. Within 100 ms of click, button text becomes `Loading...`

**Observation 2 — Button disabled attribute**:
1. The button has `disabled` set throughout the 3500 ms window
2. Clicking the button five more times produces zero additional `POST /auth/reset-password` requests

**Observation 3 — Success panel after resolution**:
1. After ~3500 ms the success toast `Password reset successfully` appears
2. The success panel replaces the form

**API mock**: `POST /auth/reset-password` → 200 delayed by 3500 ms.

---

### TC-LOADING-002: Double-submit guard records exactly one request

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type matching valid passwords
3. Click "Reset Password" twice in rapid succession (≤ 100 ms apart) against a slow backend

**Observation 1 — Network**:
1. Exactly one `POST /auth/reset-password` request is recorded

**Observation 2 — UX**:
1. The button enters the loading state on the first click
2. The second click is a no-op (button disabled while `mutation.isPending`)

---

### TC-EDGE-001: Already-authenticated visit with valid token submits normally

**Preconditions**: localStorage has a valid `access_token` (different user); URL has `?token=raw-reset-token-from-email`.

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Submit matching valid passwords

**Observation 1 — Form renders today**:
1. The form is visible (no automatic redirect today)

**Observation 2 — Submission updates the token's owner**:
1. `POST /auth/reset-password` body sends `{ token, new_password }` (no email; no auth-derived user id)
2. Success panel renders on 200

> Note: The password belongs to the **token's owner**, not the logged-in user.

---

### TC-EDGE-002: Token query param with URL-encoded whitespace

**Preconditions**: URL is `/reset-password?token=%20valid%20`.

**Action**:
1. Visit `/reset-password?token=%20valid%20`
2. Submit matching valid passwords

**Observation 1 — `searchParams.get` URL-decodes once**:
1. `POST /auth/reset-password` body `token` equals ` valid ` (with literal leading/trailing spaces)

**Observation 2 — Backend likely rejects**:
1. If backend returns 400 `Invalid or expired reset token`, toast title equals `Invalid or expired reset token`

---

### TC-EDGE-003: Refresh after success — consumed token returns 400

**Preconditions**: TC-HAPPY-001 just completed; success panel is visible; URL still has the (now consumed) token.

**Action**:
1. Hard-refresh the page
2. Submit matching valid passwords again

**Observation 1 — Form re-renders editable**:
1. The success panel is gone after refresh
2. Both password inputs are in the DOM

**Observation 2 — Backend rejects consumed token**:
1. `POST /auth/reset-password` is recorded
2. Toast title equals `Invalid or expired reset token`

**API mock**: `POST /auth/reset-password` → 400 invalid token.

---

### TC-EDGE-004: Browser back from success panel

**Preconditions**: TC-HAPPY-001 completed; success panel is visible.

**Action**:
1. Press the browser Back button

**Observation 1 — URL navigates away**:
1. URL leaves `/reset-password` (the in-component swap did not push history)

> ⚠ unverified — TanStack Query state is not reset, so re-visiting `/reset-password?token=...` could render the success panel again unless cache was invalidated.

---

### TC-EDGE-005: Password with XSS / special chars is sent verbatim

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `<script>alert(1)</script>x123` into New Password
3. Type the same string into Confirm Password
4. Click "Reset Password"

**Observation 1 — Payload sent verbatim**:
1. Request body `new_password` equals the literal `<script>alert(1)</script>x123` string

**Observation 2 — DOM is safe**:
1. Success panel renders normally
2. No `<script>` element is injected into the DOM
3. `window.alert` was not invoked

**API mock**: `POST /auth/reset-password` → 200 success.

---

### TC-EDGE-006: Password with emoji / unicode is sent verbatim

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `pass🔥word1` into both password fields
3. Click "Reset Password"

**Observation 1 — Payload includes emoji**:
1. Request body `new_password` equals `pass🔥word1` (UTF-8)

**Observation 2 — Success panel renders**:
1. Heading `Password Reset!` is visible

**API mock**: `POST /auth/reset-password` → 200 success.

---

### TC-EDGE-007: Very long password (> 500 chars) does not crash the form

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Paste a 600-character password into both fields
3. Click "Reset Password"

**Observation 1 — Input accepts the value**:
1. Both password inputs have value length 600
2. No client-side truncation

**Observation 2 — Network behaviour**:
1. `POST /auth/reset-password` body contains the full 600-char password
2. If backend rejects, toast surfaces the `detail`
3. If accepted, success panel renders

---

### TC-EDGE-008: Paste with newlines into password fields strips the newline

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Paste `newSecret\n123` into New Password

**Observation 1 — Single-line input strips newline**:
1. The New Password input value contains no newline character
2. The residual value is checked against Zod's `min(8)`

---

### TC-EDGE-009: Whitespace-only password passes Zod (known gap)

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `        ` (8 spaces) into both password fields
3. Click "Reset Password"

**Observation 1 — Zod accepts because length is 8**:
1. No helperText is shown under either password field
2. Exactly one `POST /auth/reset-password` is recorded
3. Request body `new_password` equals `        ` (8 spaces)

> ⚠ Known gap — tighten schema with `.trim()` if needed.

---

### TC-EDGE-010: Submit via Enter key in Confirm Password

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type matching valid passwords in both fields
3. Focus the Confirm Password input
4. Press the `Enter` key

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/reset-password` request is recorded
2. Body matches the typed passwords

---

### TC-EDGE-011: Confirm < 8 chars shows length error (not match error)

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `short` (5 chars) into New Password
3. Type `short` (5 chars) into Confirm Password
4. Click "Reset Password"

**Observation 1 — Field-level rule fires first**:
1. Helper text under New Password reads exactly `Password must be at least 8 characters`
2. Helper text `Passwords do not match` is NOT shown (the cross-field refine runs after the per-field rule)

---

### TC-A11Y-001: Tab order through the form

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Focus the New Password input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Tab order matches design**:
1. Focus moves in the order: New Password → New Password Eye toggle → Confirm Password → Confirm Password Eye toggle → Reset Password → "Back to login" inline link
2. No focusable element is skipped
3. No focusable element is reached twice

---

### TC-A11Y-002: Cross-field "Passwords do not match" is announced under Confirm

**Action**:
1. Visit `/reset-password?token=raw-reset-token-from-email`
2. Type `valid12345` into New Password
3. Type `OTHER67890` into Confirm Password
4. Click "Reset Password"

**Observation 1 — Error associated with the Confirm field**:
1. Helper text under Confirm Password is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `Passwords do not match`
3. The error is NOT rendered under New Password (Zod `path: ['confirm_password']`)

---

### TC-A11Y-003: Loading button announces state via text, not just a spinner

**Action**:
1. Submit valid matching passwords against a slow backend

**Observation 1 — Button text changes**:
1. The button's accessible name changes from `Reset Password` to `Loading...`
2. The button's `disabled` attribute is set (screen reader announces "disabled")

---

### TC-FULL-001: End-to-end reset-password lifecycle in one test

**Preconditions**: A test user `__e2e__rp_<uuid>@example.com` is provisioned via the backend API. A valid reset token is fetched (by triggering `POST /auth/forgot-password` and reading via test-only admin endpoint or DB peek).

**Action**:
1. Visit `/reset-password` (no token)
2. Visit `/reset-password?token=`
3. Visit `/reset-password?token=<valid>`
4. Submit with empty passwords
5. Type `short` (5 chars) in both fields; submit
6. Type `valid12345` and `OTHER67890`; submit
7. Type matching `validNew123` in both; submit
8. Click "Sign In" inside the success panel
9. Sign in via `/login` with the provisioned user and the new password
10. Re-visit `/reset-password?token=<valid>` with the now-consumed token; submit matching valid passwords
11. Click inline "Back to login"

**Observation 1 — Step 1 bounces**:
1. Toast title equals `Invalid reset link`
2. URL becomes `/forgot-password`

**Observation 2 — Step 2 bounces identically**:
1. Toast title equals `Invalid reset link`
2. URL becomes `/forgot-password`

**Observation 3 — Step 3 renders the form**:
1. New Password and Confirm Password inputs are visible

**Observation 4 — Step 4 yields password-length error**:
1. Helper text under New Password reads `Password must be at least 8 characters`

**Observation 5 — Step 5 yields password-length error**:
1. Helper text under New Password reads `Password must be at least 8 characters`

**Observation 6 — Step 6 yields mismatch error**:
1. Helper text under Confirm Password reads `Passwords do not match`

**Observation 7 — Step 7 succeeds**:
1. Toast title equals `Password reset successfully`
2. Success panel renders with heading `Password Reset!`

**Observation 8 — Step 8 navigates to /login**:
1. URL becomes `/login`

**Observation 9 — Step 9 verifies the password actually changed**:
1. Login succeeds against the provisioned user with the new password

**Observation 10 — Step 10 token reuse rejected**:
1. Toast title equals `Invalid or expired reset token`

**Observation 11 — Step 11 navigates back to login**:
1. URL becomes `/login`

**Cleanup** (in `finally`):
1. Delete the provisioned user via the backend admin API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` / `TC-NAV-*` / `TC-ERROR-*` test case above)

- [x] `?token=` is missing → toast + redirect — see TC-NAV-001
- [x] `?token=` is an empty string — see TC-NAV-002
- [x] `?token=` has URL-encoded chars — see TC-EDGE-002
- [x] Token already used — see TC-ERROR-008
- [x] Token expired (past TTL) — same path as TC-ERROR-001
- [x] Already-authenticated visit — see TC-EDGE-001
- [x] Suspense fallback `AppLoader` flash — see TC-HAPPY-003
- [x] Browser back from success panel — see TC-EDGE-004
- [x] Refresh after success — see TC-EDGE-003
- [x] Confirm < 8 chars + matching New < 8 chars — see TC-EDGE-011
- [x] Trailing whitespace in password (whitespace-only) — see TC-EDGE-009
- [x] Enter key in either password field submits the form — see TC-EDGE-010
- [x] Long password (> 500 chars) — see TC-EDGE-007
- [x] Password with XSS — see TC-EDGE-005
- [x] Password with emoji — see TC-EDGE-006
- [x] Paste with newlines into password fields — see TC-EDGE-008
- [ ] User clicks the reset link twice rapidly — first click consumes the token; the second tab will see a normal form load → submit → 400 ⚠ not tested separately (covered by TC-ERROR-008)
- [ ] Password contains the user's email or username — accepted client-side; backend may or may not reject ⚠ unverified

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

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order: New Password → Confirm Password → Reset Password → Back to login link — see TC-A11Y-001
- [x] Cross-field "Passwords do not match" error is associated with the Confirm Password field — see TC-A11Y-002
- [x] Submit button announces its loading state with "Loading..." text rather than only a spinner — see TC-A11Y-003
- [ ] Both password inputs use the shared `TextInput` and have associated `<label>` elements via the `label` prop
- [ ] Required indicators are visible to sighted users **and** announced
- [ ] Validation errors render under the input as `helperText` — not as toasts
- [ ] Toast container has `aria-live="polite"` (Sonner default); error toasts default to 5000 ms, success toasts to 3000 ms
- [ ] Suspense fallback `AppLoader` should have an accessible label (e.g. `role="status"` or `aria-label="Loading"`) — ⚠ unverified, confirm `AppLoader` markup
- [ ] Success panel heading "Password Reset!" preserves the heading hierarchy (layout `<h1>` then page `<h2>`)
- [ ] `CheckCircle` and `ArrowLeft` icons are decorative; surrounding text carries the meaning
- [ ] Focus does not auto-move on form → success-panel swap ⚠ unverified
- [ ] No client-side autocomplete attributes are set on the password inputs ⚠ unverified

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
