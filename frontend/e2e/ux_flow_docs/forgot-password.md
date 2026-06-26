# Feature Doc: Forgot Password

Feature documentation for the `/forgot-password` page. Used by
`/generate-tests forgot-password` (or `--docs e2e/ux_flow_docs/forgot-password.md`) to
ensure all positive and negative user cases are covered alongside the component
source analysis.

The forgot-password page is the entry point of the password reset round-trip.
The user enters their email; the backend always responds with a generic 200
("If the email exists, you will receive a password reset link") so existence
is not leaked; the page swaps to a "Check your email" confirmation panel.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/forgot-password` (under the `(auth)` route group)
- **Component**: `src/app/(auth)/forgot-password/page.tsx` (default export `ForgotPasswordPage` — single client component, no Suspense wrapper because it does not use `useSearchParams`)
- **Layout**: `src/app/(auth)/layout.tsx` — shared with the rest of `(auth)/*`
- **Auth required**: no — this is a **public** page
- **Redirect when already authenticated**: not enforced today (no `src/middleware.ts`). A logged-in user can still load `/forgot-password` and request a reset. ⚠ unverified whether a future iteration adds a client-side redirect to `/home`

---

## User Stories

### US-1: Request a password reset email

**As a** user who forgot their password, **I want to** type my email and click "Send Reset Link", **so that** I receive a reset link in my inbox.

**Acceptance criteria**:

- [ ] Heading reads "Reset password" with subtitle "Enter your email and we'll send you a reset link"
- [ ] Single Email input (`type="email"`) with required indicator
- [ ] Submit button label is "Send Reset Link"; loading state is "Loading..."
- [ ] On 200, the form is replaced by a `MailCheck`-icon panel that reads "Check your email" with the submitted email rendered in bold and an outline "Back to login" button (with `ArrowLeft` icon)
- [ ] A success toast appears with title "Reset link sent if the email exists" (3 s default duration)

### US-2: Back-to-login affordances

**As a** user who realised they remember the password, **I want to** click "Back to login", **so that** I can return to `/login` from either the form or the confirmation panel.

**Acceptance criteria**:

- [ ] Below the form, a small "Back to login" inline link renders with a left-arrow icon (href `/login`)
- [ ] On the confirmation panel, the outline "Back to login" button also navigates to `/login`

### US-3: Block submission on client-side validation errors

**As a** user, **I want to** see field-level errors before submission, **so that** I do not waste a network round-trip on a malformed payload.

**Acceptance criteria**:

- [ ] Empty Email → helperText "Email is required"
- [ ] Malformed Email → helperText "Please enter a valid email"
- [ ] While `mutation.isPending === true`, Submit button shows "Loading..." with `disabled`

### US-4: Tolerate "unknown email" silently

**As a** user, **I want to** see the same success message whether or not my email exists in the system, **so that** account-existence is not leaked through error messages.

**Acceptance criteria**:

- [ ] For both known and unknown emails the backend returns 200 `{"message": "If the email exists, ..."}`
- [ ] The frontend shows the same success toast and confirmation panel in both cases

---

## UI Elements

| Element                       | Type            | Content / Label                                                 | Behavior                                              |
| ----------------------------- | --------------- | --------------------------------------------------------------- | ----------------------------------------------------- |
| Heading                       | h2              | "Reset password"                                                | Static                                                |
| Subtitle                      | p               | "Enter your email and we'll send you a reset link"              | Static                                                |
| Email input                   | TextInput       | label "Email", `type="email"`                                   | Required, Zod-validated                               |
| Send Reset Link button        | Button          | "Send Reset Link" → "Loading..."                                | `type="submit"`; disabled while `mutation.isPending`  |
| Back to login (inline link)   | Link            | "Back to login" + `ArrowLeft` icon                              | Navigates to `/login`                                 |
| MailCheck icon                | lucide icon     | `MailCheck`                                                     | Renders only in the success panel                     |
| Confirmation heading          | h2              | "Check your email"                                              | Renders only after `mutation.isSuccess === true`      |
| Confirmation body             | p               | "We've sent a password reset link to **<email>**"               | `<strong>` wraps the submitted email                  |
| Back to login (outline button)| Button (outline)| "Back to login" + `ArrowLeft` icon                              | Navigates to `/login`                                 |

---

## Input Specifications

Source: `src/schemas/auth.ts` (`forgotPasswordSchema`).

| Field | Type  | Required | Validation Rules                              | Exact Error Message                                |
| ----- | ----- | -------- | --------------------------------------------- | -------------------------------------------------- |
| Email | email | yes      | `z.string().min(1).email()`                   | "Email is required" / "Please enter a valid email" |

**Button state rules:**

- "Send Reset Link" is **never disabled** by `formState.isValid`; invalid submit surfaces inline helperText instead
- While `mutation.isPending === true`, the shadcn `<Button>` renders "Loading..." and sets `disabled`
- Once `mutation.isSuccess === true`, the entire form unmounts and the confirmation panel renders — there is no way back to the form on this page without navigating away

---

## Navigation

| Trigger                                            | Destination                  | Condition                              |
| -------------------------------------------------- | ---------------------------- | -------------------------------------- |
| Successful submit (2xx)                            | (stays on `/forgot-password`)| Form swaps to the confirmation panel   |
| Click "Back to login" (form footer)                | `/login`                     | Always                                 |
| Click "Back to login" (confirmation panel)         | `/login`                     | Always                                 |
| Already authenticated visit                        | (stays on `/forgot-password`)| No automatic redirect today ⚠ unverified |

---

## API Contracts

Payloads sourced from the Postman collection (folder `Authentication`).

| Endpoint                  | Method | Request                       | Success Response                                                          | Error Response          |
| ------------------------- | ------ | ----------------------------- | ------------------------------------------------------------------------- | ----------------------- |
| `/auth/forgot-password`   | POST   | `{ "email": string }`         | 200 `{ "message": "If the email exists, you will receive a password reset link" }` | `{ "detail": "..." }`   |

### Example: `POST /auth/forgot-password`

Request body:

```json
{ "email": "owner@acme.com" }
```

200 OK response body (always generic — protects account existence):

```json
{ "message": "If the email exists, you will receive a password reset link" }
```

400 Bad Request:

```json
{ "detail": "email is required" }
```

422 Validation Error:

```json
{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
```

**Note**: The frontend ignores the response body — `useForgotPassword` mutation result is checked only for success/error state. The toast text is **hard-coded** in the page (`'Reset link sent if the email exists'`) and intentionally matches the backend's generic-message stance.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Known email request swaps to confirmation panel

**Preconditions**:
- User is signed out (no `access_token` in localStorage)
- Email field is blank on mount

**Action**:
1. Visit `/forgot-password`
2. Type `owner@acme.com` into the Email input
3. Click the "Send Reset Link" button

**Observation 1 — Network request**:
1. Exactly one `POST /auth/forgot-password` request is recorded
2. Request body equals `{ "email": "owner@acme.com" }`
3. Request `Content-Type` header is `application/json`

**Observation 2 — Loading state during request**:
1. The "Send Reset Link" button text changes to "Loading..."
2. The "Send Reset Link" button has the `disabled` attribute

**Observation 3 — Success toast**:
1. A Sonner toast appears in `[data-sonner-toast]`
2. Toast title equals `Reset link sent if the email exists`
3. Toast variant is `success`
4. Toast auto-dismisses within ~3s

**Observation 4 — Confirmation panel renders**:
1. The Email input is no longer in the DOM
2. A heading with text `Check your email` is visible
3. The submitted email `owner@acme.com` is rendered inside a `<strong>` element
4. The `MailCheck` icon is visible above the heading
5. An outline button labelled `Back to login` (with `ArrowLeft` icon) is in the DOM

**API mock**: `POST /auth/forgot-password` → 200 `{ "message": "If the email exists, you will receive a password reset link" }`.

**Cleanup**: Clear cookies and localStorage in `afterEach`.

---

### TC-HAPPY-002: Unknown email yields identical success UX (no existence leak)

**Action**:
1. Visit `/forgot-password`
2. Type `does-not-exist@nowhere.io` into the Email input
3. Click "Send Reset Link"

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/forgot-password` request is recorded with body `{ "email": "does-not-exist@nowhere.io" }`

**Observation 2 — Same toast as known-email path**:
1. Toast title equals `Reset link sent if the email exists`

**Observation 3 — Same confirmation panel**:
1. Heading `Check your email` is visible
2. The submitted email `does-not-exist@nowhere.io` is rendered inside `<strong>`

**API mock**: `POST /auth/forgot-password` → 200 generic body (same as TC-HAPPY-001).

---

### TC-HAPPY-003: Mixed-case email is preserved verbatim in the panel

**Action**:
1. Visit `/forgot-password`
2. Type `Mixed.Case+Tag@Example.COM` into Email
3. Click "Send Reset Link"

**Observation 1 — Panel renders the typed value without case-normalisation**:
1. The confirmation panel body contains `<strong>Mixed.Case+Tag@Example.COM</strong>` verbatim

**API mock**: `POST /auth/forgot-password` → 200 success.

---

### TC-VALIDATE-001: Empty Email blocks submit with inline error

**Action**:
1. Visit `/forgot-password`
2. Leave Email blank
3. Click "Send Reset Link"

**Observation 1 — No network call fires**:
1. Zero `POST /auth/forgot-password` requests are recorded

**Observation 2 — Inline error appears under Email**:
1. Helper text under the Email input reads exactly `Email is required`
2. Email input has the error styling

**Observation 3 — No toast and no panel**:
1. No Sonner toast is shown
2. The confirmation panel is NOT in the DOM
3. URL is still `/forgot-password`

---

### TC-VALIDATE-002: Malformed Email blocks submit

**Action**:
1. Visit `/forgot-password`
2. Type `not-an-email` into Email
3. Click "Send Reset Link"

**Observation 1 — No network call**:
1. Zero `POST /auth/forgot-password` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

---

### TC-VALIDATE-003: Email missing `@` symbol blocks submit

**Action**:
1. Visit `/forgot-password`
2. Type `userexample.com` into Email
3. Click "Send Reset Link"

**Observation 1 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

**Observation 2 — No network call**:
1. Zero `POST /auth/forgot-password` requests are recorded

---

### TC-VALIDATE-004: Email with double `@` blocks submit

**Action**:
1. Visit `/forgot-password`
2. Type `a@@b.com` into Email
3. Click "Send Reset Link"

**Observation 1 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

---

### TC-VALIDATE-005: Whitespace-only email blocks submit

**Action**:
1. Visit `/forgot-password`
2. Type `   ` (3 spaces) into Email
3. Click "Send Reset Link"

**Observation 1 — Inline error**:
1. Helper text under Email reads exactly `Please enter a valid email`

> Note: `min(1)` passes (length ≥ 1) but `.email()` rejects.

---

### TC-ERROR-001: 400 backend rejection surfaces no toast today (known gap)

**Action**:
1. Visit `/forgot-password`
2. Type a valid-format email and submit

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/forgot-password` is recorded

**Observation 2 — No toast surfaced**:
1. No Sonner toast (success OR error) appears
2. The success toast `Reset link sent if the email exists` is NOT shown
3. `mutation.isError` becomes true silently

**Observation 3 — Form state**:
1. Email input still contains the typed value
2. "Send Reset Link" button re-enables
3. The confirmation panel is NOT in the DOM
4. URL is still `/forgot-password`

**API mock**: `POST /auth/forgot-password` → 400 `{ "detail": "email is required" }`.

> ⚠ Known gap — `onSubmit` does NOT call `handleApiError` (no try/catch in `forgot-password/page.tsx` lines 24–27). Confirm whether a future iteration adds a catch block.

---

### TC-ERROR-002: 422 validation error surfaces no toast today

**Action**:
1. Submit valid-format email

**Observation 1 — No toast surfaced**:
1. No Sonner toast appears
2. `mutation.isError` becomes true

**Observation 2 — Form state**:
1. Email is preserved
2. Button re-enables

**API mock**: `POST /auth/forgot-password` → 422 `{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }`.

---

### TC-ERROR-003: 500 Internal Server Error surfaces no toast today

**Action**:
1. Submit valid-format email

**Observation 1 — No error toast**:
1. No Sonner toast appears

**Observation 2 — Form state**:
1. Button re-enables

**API mock**: `POST /auth/forgot-password` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-004: Network failure surfaces no toast today

**Action**:
1. Submit valid-format email

**Observation 1 — No toast**:
1. No Sonner toast appears
2. `mutation.isError` becomes true

**Observation 2 — Form state**:
1. Email is preserved; button re-enables

**API mock**: route aborted (no response object).

---

### TC-ERROR-005: 200 with malformed JSON body falls into error branch

**Action**:
1. Submit valid-format email

**Observation 1 — No toast surfaced**:
1. axios rejects parsing; mutation enters the error branch
2. No Sonner toast appears (see ERROR gap)

**API mock**: `POST /auth/forgot-password` → 200 with body `not-json`.

---

### TC-NAV-001: Click inline "Back to login" navigates client-side

**Action**:
1. Visit `/forgot-password`
2. Click the inline "Back to login" link below the form

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No network call**:
1. Zero `POST /auth/forgot-password` requests are recorded
2. No full page reload occurs (client-side `<Link>`)

---

### TC-NAV-002: Click "Back to login" button from confirmation panel

**Preconditions**: TC-HAPPY-001 just completed; confirmation panel is visible.

**Action**:
1. Click the outline "Back to login" button inside the confirmation panel

**Observation 1 — URL change**:
1. URL becomes `/login`

**Observation 2 — No full page reload**:
1. No full page reload occurs

---

### TC-LOADING-001: Slow API keeps Send Reset Link in loading state

**Action**:
1. Visit `/forgot-password`
2. Type a valid email
3. Click "Send Reset Link" against a deliberately slow backend (3500 ms)

**Observation 1 — Button label**:
1. Within 100 ms of click, button text becomes `Loading...`

**Observation 2 — Button disabled attribute**:
1. The button has `disabled` set throughout the 3500 ms window
2. Clicking the button five more times produces zero additional `POST /auth/forgot-password` requests

**Observation 3 — Confirmation panel after resolution**:
1. After ~3500 ms the confirmation panel replaces the form
2. The success toast appears

**API mock**: `POST /auth/forgot-password` → 200 delayed by 3500 ms.

---

### TC-LOADING-002: Double-submit guard records exactly one request

**Action**:
1. Visit `/forgot-password`
2. Type a valid email
3. Click "Send Reset Link" twice in rapid succession (≤ 100 ms apart) against a slow backend

**Observation 1 — Network**:
1. Exactly one `POST /auth/forgot-password` request is recorded

**Observation 2 — UX**:
1. The button enters the loading state on the first click
2. The second click is a no-op (button disabled while `mutation.isPending`)

---

### TC-EDGE-001: Already-authenticated visit still renders the form

**Preconditions**: localStorage has a valid `access_token`.

**Action**:
1. Visit `/forgot-password`

**Observation 1 — Form renders today**:
1. The Email input is in the DOM (no automatic redirect today)
2. The Email input is empty

> ⚠ When the client-side authed-user redirect ships, this observation must change.

---

### TC-EDGE-002: Email with XSS attempt is rejected by Zod

**Action**:
1. Visit `/forgot-password`
2. Type `<script>alert(1)</script>@x.com` into Email
3. Click "Send Reset Link"

**Observation 1 — Zod rejects**:
1. Helper text under Email reads `Please enter a valid email`
2. Zero `POST /auth/forgot-password` requests are recorded

**Observation 2 — DOM is safe**:
1. The literal `<script>` text appears as the input's `value` attribute (rendered as text, not HTML)
2. `window.alert` was not invoked

---

### TC-EDGE-003: Email with emoji / unicode

**Action**:
1. Visit `/forgot-password`
2. Type `🔥user@example.com` into Email
3. Click "Send Reset Link"

**Observation 1 — Zod behaviour depends on implementation**:
1. Either helperText `Please enter a valid email` appears OR the request is submitted

> ⚠ Document the observed helperText behaviour — Zod's `.email()` accepts only ASCII local parts in most versions.

---

### TC-EDGE-004: Very long email (>500 chars) does not crash the form

**Action**:
1. Visit `/forgot-password`
2. Paste a 600-character local-part email
3. Click "Send Reset Link"

**Observation 1 — Input accepts the value**:
1. Email input value length equals 600 (or more, with the domain)

**Observation 2 — Either Zod rejects or backend returns generic 200**:
1. If Zod rejects, helperText `Please enter a valid email` appears and no network call is fired
2. If accepted, `POST /auth/forgot-password` returns the same generic 200 (no leak)

---

### TC-EDGE-005: Paste with newlines into Email strips the newline

**Action**:
1. Visit `/forgot-password`
2. Paste `user@acme.com\nextra` into the Email input

**Observation 1 — Single-line input strips newline**:
1. The Email input value contains no newline character
2. Zod validates the residual value

---

### TC-EDGE-006: Submit via Enter key in Email

**Action**:
1. Visit `/forgot-password`
2. Type a valid email
3. Focus the Email input and press `Enter`

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/forgot-password` request is recorded
2. Body equals `{ "email": "..." }` with the typed value

---

### TC-EDGE-007: Browser back from confirmation panel exits the page

**Preconditions**: TC-HAPPY-001 completed; user is on the confirmation panel.

**Action**:
1. Press the browser Back button

**Observation 1 — URL navigates away**:
1. URL leaves `/forgot-password` to the previous page (the in-component swap did not push history)

---

### TC-EDGE-008: Resubmit after success requires navigating away

**Preconditions**: TC-HAPPY-001 completed; confirmation panel is visible.

**Action**:
1. Inspect the confirmation panel

**Observation 1 — No in-page "Send another link" affordance**:
1. There is no button to re-submit from the confirmation panel
2. `mutation.isSuccess` does not auto-reset

> Note: To resubmit, the user must navigate to `/login` → `/forgot-password` and refill the form.

---

### TC-A11Y-001: Tab order through the form

**Action**:
1. Visit `/forgot-password`
2. Focus the Email input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Tab order matches design**:
1. Focus moves in the order: Email → Send Reset Link → "Back to login" inline link
2. No focusable element is skipped
3. No focusable element is reached twice

---

### TC-A11Y-002: Validation errors are announced to screen readers

**Action**:
1. Visit `/forgot-password`
2. Click "Send Reset Link" with the Email field empty

**Observation 1 — Email error is announceable**:
1. Helper text under Email is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text is exactly `Email is required`

---

### TC-A11Y-003: Loading button announces state via text, not just a spinner

**Action**:
1. Submit a valid email against a slow backend

**Observation 1 — Button text changes**:
1. The button's accessible name changes from `Send Reset Link` to `Loading...`
2. The button's `disabled` attribute is set (screen reader announces "disabled")

---

### TC-FULL-001: End-to-end forgot-password lifecycle in one test

**Preconditions**: A test user `__e2e__fp_<uuid>@example.com` is provisioned via the backend API (NOT mocked).

**Action**:
1. Visit `/forgot-password` without auth
2. Click "Send Reset Link" with the Email field empty
3. Type `not-an-email` and submit
4. Click "Back to login" inline link
5. Navigate back to `/forgot-password`
6. Type the provisioned email and submit
7. Click outline "Back to login" button
8. Navigate to `/forgot-password` again and submit `nobody+__e2e__@example.com`

**Observation 1 — Step 2 yields required-field error**:
1. Helper text `Email is required` is visible

**Observation 2 — Step 3 yields format error**:
1. Helper text under Email becomes `Please enter a valid email`

**Observation 3 — Step 4 navigates to /login**:
1. URL becomes `/login`

**Observation 4 — Step 6 succeeds**:
1. Toast title equals `Reset link sent if the email exists`
2. Confirmation panel renders with the email inside `<strong>`

**Observation 5 — Step 7 navigates to /login**:
1. URL becomes `/login`

**Observation 6 — Step 8 unknown email yields identical UX**:
1. Toast title equals `Reset link sent if the email exists`
2. Confirmation panel renders with the unknown email inside `<strong>`

**Cleanup** (in `finally`):
1. Delete the provisioned user via the backend admin API

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-ERROR-*` test case above)

- [x] Token already set in localStorage when visiting `/forgot-password` — see TC-EDGE-001
- [x] Unknown email — see TC-HAPPY-002
- [x] Backend error path (4xx/5xx/network) — no toast surfaced today — see TC-ERROR-001..TC-ERROR-005
- [x] Confirmation panel renders the typed email verbatim — see TC-HAPPY-003
- [x] Double-submit — see TC-LOADING-002
- [x] Resubmit after success — see TC-EDGE-008
- [x] Browser back from confirmation panel — see TC-EDGE-007
- [x] Whitespace-only email — see TC-VALIDATE-005
- [x] Enter key in the Email input — see TC-EDGE-006
- [x] Slow backend — see TC-LOADING-001
- [ ] Suspense — none on this page (no `useSearchParams`); no fallback flash
- [ ] Repeated rapid submissions of valid emails — each completes the mutation and re-shows the toast; backend rate limiting is the only guard ⚠ unverified
- [ ] Backend reset-link expiry is handled on the `/reset-password` page, not here

---

## Business Rules

- The forgot-password endpoint **never leaks account existence** — both known and unknown emails return the same generic 200 body
- The frontend toast text mirrors this stance: `'Reset link sent if the email exists'` is shown unconditionally on success (it does not say "We sent you an email")
- Password resets are tokenised by the backend and delivered by email; the token lifetime and reuse policy are backend concerns
- The frontend does not display the request payload or the backend's response body — it only branches on `mutation.isSuccess`
- This page is **public** — no `Authorization` header is required (the Axios interceptor will still attach one if a token happens to be in localStorage; the backend ignores it on this endpoint)
- The submit button text "Send Reset Link" is title-cased; the link variant below is sentence-cased "Back to login" — intentional style choice, do not normalise
- Email verification status of the account is irrelevant to this endpoint; an unverified user can still request a reset

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order: Email → Send Reset Link → "Back to login" inline link — see TC-A11Y-001
- [x] Validation errors render as `helperText` with `aria-live`/`role="alert"` — see TC-A11Y-002
- [x] Submit button announces loading state with "Loading..." text — see TC-A11Y-003
- [ ] Email input uses the shared `TextInput` (renders an associated `<label>`) and the required indicator
- [ ] Toast container has `aria-live="polite"` (Sonner default); success toasts default to 3000 ms
- [ ] Confirmation panel preserves heading hierarchy (layout `<h1>` → page `<h2>` "Check your email")
- [ ] The "Back to login" links use real anchors (Next.js `<Link>`) and have a primary text color with hover underline
- [ ] `MailCheck` and `ArrowLeft` icons are decorative; surrounding text carries the meaning
- [ ] Focus remains on the page (no modal/dialog); after the form swaps to the confirmation panel, focus does not auto-move to the new heading ⚠ unverified — a future iteration may want to focus the heading or the Back-to-login button for keyboard users

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. The page **does not** call `handleApiError` on failure today — only the success path triggers a toast.

| Trigger                                       | Toast title                                  | Toast description | Variant |
| --------------------------------------------- | -------------------------------------------- | ----------------- | ------- |
| Successful reset request (any 2xx)            | `Reset link sent if the email exists`        | —                 | success |
| Backend error (4xx / 5xx / network)           | (none — no error toast wired up today)       | —                 | —       |

If a future iteration wraps `mutation.mutateAsync` in try/catch + `handleApiError`, error toasts will surface the backend `detail` string verbatim (same convention as the rest of the auth flow).
