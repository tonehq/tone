# Feature Doc: Forgot Password

Feature documentation for the `/forgot-password` page. Used by
`/generate-tests forgot-password` (or `--docs e2e/ux_flow_docs/forgot-password.md`) to
ensure all positive and negative user cases are covered alongside the component
source analysis.

The forgot-password page is the entry point of the password reset round-trip.
The user enters their email; the backend always responds with a generic 200
("If the email exists, you will receive a password reset link") so existence
is not leaked; the page swaps to a "Check your email" confirmation panel.

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

## User Workflow Steps

**WF-1: Successful reset request → confirmation panel** (positive)

1. User navigates to `/forgot-password` → expected: form renders with single Email input
2. User types `owner@acme.com` → expected: helperText absent
3. User clicks **Send Reset Link** → expected: button enters loading; `POST /auth/forgot-password` fires with `{ email }`
4. Response is 200 with `{"message": "If the email exists, you will receive a password reset link"}` → expected: success toast "Reset link sent if the email exists" (3 s)
5. `mutation.isSuccess` becomes true → expected: form is replaced by the confirmation panel — heading "Check your email", body "We've sent a password reset link to **owner@acme.com**", outline "Back to login" button with left-arrow icon

**WF-2: Unknown email (same UX)** (positive — backend hides existence)

1. User submits `does-not-exist@nowhere.io` → expected: backend still returns 200 generic message
2. Same toast + confirmation panel as WF-1; the email rendered in bold is the typed value (`does-not-exist@nowhere.io`)

**WF-3: Client-side validation gates submit** (negative)

1. User leaves Email blank and clicks Send Reset Link → expected: RHF prevents `POST /auth/forgot-password`; helperText "Email is required"
2. User types `not-an-email` → expected: helperText "Please enter a valid email"
3. User fixes the email → submission proceeds

**WF-4: Backend 400 missing email** (negative)

1. (Unreachable under healthy Zod) — direct API caller submits empty body
2. Backend returns 400 `{"detail": "email is required"}`
3. Note: `onSubmit` does NOT wrap the mutation in try/catch (see `forgot-password/page.tsx` lines 24–27); the unhandled rejection bubbles to TanStack Query's `isError` state. The success toast does NOT fire. ⚠ no error toast is fired by this page today; the user sees no feedback on failure beyond a button reset

**WF-5: Back-to-login from the form** (positive)

1. User clicks the "Back to login" inline link below the form → expected: navigation to `/login`

**WF-6: Back-to-login from the confirmation panel** (positive)

1. User reaches the confirmation panel (WF-1)
2. User clicks the outline "Back to login" button → expected: navigation to `/login`

**WF-7: Already-authenticated visit** (edge)

1. User has `access_token` in localStorage and visits `/forgot-password` → expected: page still renders the form (no automatic redirect today). Submitting is allowed but pointless. ⚠ unverified guard

**WF-8: Resubmit after success** (edge)

1. User reaches the confirmation panel (WF-1) → expected: there is no "Send another link" button
2. To resubmit, the user must navigate away (e.g. Back to login → /forgot-password) and refill the form — `mutation.isSuccess` does not auto-reset

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

## Success Scenarios

**PS-1: Known email → success toast + confirmation panel**

- **Preconditions**: not authenticated; valid email.
- **Steps**: type `owner@acme.com` → click Send Reset Link.
- **Expected outcome**: success toast "Reset link sent if the email exists"; form replaced by confirmation panel; the bold email reads `owner@acme.com`.
- **Mock API** (`POST /auth/forgot-password`, 200):
  ```json
  { "message": "If the email exists, you will receive a password reset link" }
  ```

**PS-2: Unknown email → identical UX**

- **Preconditions**: not authenticated.
- **Steps**: type `does-not-exist@nowhere.io` → submit.
- **Expected outcome**: same toast + panel; bold email reads `does-not-exist@nowhere.io`.
- **Mock API**: same as PS-1.

**PS-3: Loading state visible during slow request**

- **Preconditions**: backend deliberately slow (300 ms).
- **Steps**: submit valid form.
- **Expected outcome**: button shows "Loading..." with `disabled`; user cannot double-submit.

**PS-4: Navigation to /login via inline link**

- **Steps**: click "Back to login" below the form.
- **Expected outcome**: client-side navigation to `/login`; no network calls.

**PS-5: Navigation to /login via confirmation-panel button**

- **Preconditions**: PS-1 reached.
- **Steps**: click outline "Back to login" button.
- **Expected outcome**: navigation to `/login`.

**PS-6: Mixed-case email is preserved**

- **Preconditions**: PS-1 with email `Mixed.Case+Tag@Example.COM`.
- **Expected outcome**: panel renders `Mixed.Case+Tag@Example.COM` verbatim.

---

## Failure Scenarios

**FS-1: Empty Email**

- **Mock API**: not called.
- **Expected UI**: helperText "Email is required"; no toast.

**FS-2: Malformed Email**

- **Steps**: type `not-an-email`.
- **Mock API**: not called.
- **Expected UI**: helperText "Please enter a valid email".

**FS-3: Email missing the `@` symbol**

- **Steps**: type `userexample.com`.
- **Expected UI**: helperText "Please enter a valid email".

**FS-4: Email with double `@`**

- **Steps**: type `a@@b.com`.
- **Expected UI**: helperText "Please enter a valid email" (Zod's `email()` rejects).

**FS-5: 400 backend rejection (missing email)**

- **Mock API** (`POST /auth/forgot-password`, 400): `{ "detail": "email is required" }`
- **Expected UI**: ⚠ `onSubmit` does NOT call `handleApiError` (no try/catch — see Workflow WF-4); no toast is shown. The success toast also does NOT fire because the mutation rejected. Button re-enables; form remains. **This is a known gap — confirm whether the next iteration adds a catch block.**

**FS-6: 422 Validation error**

- **Mock API** (`POST /auth/forgot-password`, 422):
  ```json
  { "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
  ```
- **Expected UI**: same as FS-5 — no toast surfaced today; `mutation.isError` becomes true.

**FS-7: 500 Internal Server Error**

- **Mock API** (`POST /auth/forgot-password`, 500): `{ "detail": "Internal Server Error" }`
- **Expected UI**: same as FS-5 — no error toast; button re-enables.

**FS-8: Network failure / no response**

- **Mock API**: route aborted.
- **Expected UI**: same as FS-5 — no toast; `mutation.isError` true.

**FS-9: Double-submit guard**

- **Steps**: click Send Reset Link twice in rapid succession against a slow backend.
- **Expected UI**: second click is a no-op (button disabled while `mutation.isPending`); exactly one `POST /auth/forgot-password` is recorded.

**FS-10: Backend 200 but response body is malformed JSON**

- **Mock API** (`POST /auth/forgot-password`, 200, body `not-json`).
- **Expected UI**: axios rejects parsing; mutation falls into the error branch — no toast surfaced today (see FS-5 gap).

**FS-11: Submit while offline**

- **Steps**: disable network; submit.
- **Expected UI**: button enters loading; mutation eventually rejects with a network error; no toast surfaced today.

**FS-12: Whitespace-only email**

- **Steps**: type `   ` (3 spaces).
- **Expected UI**: helperText "Please enter a valid email" (`min(1)` passes but `.email()` rejects).

**FS-13: Authenticated visit to `/forgot-password` redirects to `/home`**

- **Preconditions**: localStorage has valid `access_token` and the user lands on `/forgot-password`.
- **Expected UI**: client-side guard redirects to `/home`; the form is never rendered. ⚠ Document current behaviour exactly — today the form renders. Update when the guard ships.

**FS-14: Slow API (>3s) keeps Send Reset Link in loading state**

- **Mock API** (`POST /auth/forgot-password`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button text remains "Loading..." with `disabled` for the full duration; clicking again is a no-op; confirmation panel appears only after the response resolves.

**FS-15: Email with XSS / special chars**

- **Steps**: type `<script>alert(1)</script>@x.com`; submit.
- **Expected UI**: Zod's `.email()` rejects → helperText "Please enter a valid email"; no `POST /auth/forgot-password` fires; the literal text renders as plain value in the input (no DOM injection).

**FS-16: Email with emoji / unicode**

- **Steps**: type `🔥user@example.com`; submit.
- **Expected UI**: Zod's `.email()` accepts only ASCII local parts; depending on Zod version this may pass or fail. Document the observed helperText behaviour.

**FS-17: Very long email (>500 chars)**

- **Steps**: type a 600-char local-part email; submit.
- **Expected UI**: input accepts; Zod's `.email()` likely rejects the malformed length; if accepted, `POST /auth/forgot-password` returns the same generic 200 (no leak).

**FS-18: Paste with newlines into Email input**

- **Steps**: paste `user@acme.com\nextra` into Email.
- **Expected UI**: single-line `type="email"` input strips the newline; Zod validates the residual value.

**FS-19: Tab order through the form**

- **Steps**: focus Email → press Tab repeatedly.
- **Expected UI**: focus moves Email → Send Reset Link → "Back to login" inline link.

**FS-20: Submit via Enter key in Email**

- **Steps**: fill valid Email, press Enter while focus is on Email.
- **Expected UI**: form submits exactly as a click on Send Reset Link would.

**FS-21: Helper-text errors are announced via aria-live**

- **Steps**: submit with empty Email.
- **Expected UI**: helperText element renders with `role="alert"` (or `aria-live`) so screen readers announce "Email is required" without focus change.

**FS-22: Browser back from confirmation panel returns to the editable form**

- **Preconditions**: WF-1 completed; user is on the confirmation panel.
- **Steps**: press browser Back.
- **Expected UI**: URL unchanged (the swap is in-component, not a route push); pressing Back exits `/forgot-password` to the previous page.

### Full lifecycle (`*-FULL`)

**FP-FULL: End-to-end forgot-password lifecycle in a single test**

- **Preconditions**: A test user `__e2e__fp_<uuid>@example.com` is provisioned via the backend API in the test body (NOT mocked).
- **Steps in one Playwright test body**:
  1. Visit `/forgot-password` without auth → expect form with single Email input.
  2. Click Send Reset Link with empty Email → expect helperText "Email is required".
  3. Type `not-an-email` → submit → expect helperText "Please enter a valid email".
  4. Click "Back to login" inline link → expect URL `/login`.
  5. Navigate back to `/forgot-password`.
  6. Type the provisioned email → submit → expect success toast "Reset link sent if the email exists"; expect confirmation panel with the email in `<strong>`.
  7. Click outline "Back to login" button → expect URL `/login`.
  8. Navigate to `/forgot-password` again and submit a deliberately-unknown email `nobody+__e2e__@example.com` → expect identical success toast + confirmation panel (no existence leak).
- **Cleanup (in `finally`)**: Delete the provisioned user via the backend admin API.
- **Naming**: `FP-FULL — forgot-password full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. The page **does not** call `handleApiError` on failure today — only the success path triggers a toast.

| Trigger                                       | Toast title                                  | Toast description | Variant |
| --------------------------------------------- | -------------------------------------------- | ----------------- | ------- |
| Successful reset request (any 2xx)            | `Reset link sent if the email exists`        | —                 | success |
| Backend error (4xx / 5xx / network)           | (none — no error toast wired up today)       | —                 | —       |

If a future iteration wraps `mutation.mutateAsync` in try/catch + `handleApiError`, error toasts will surface the backend `detail` string verbatim (same convention as the rest of the auth flow).

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

## Edge Cases

- [ ] Token already set in localStorage when visiting `/forgot-password` — no client-side redirect today; submitting is allowed
- [ ] Unknown email — backend returns the same 200 generic body, frontend behaves identically; confirms the no-existence-leak design
- [ ] Backend error path (4xx/5xx/network) — **no toast is shown today** because `onSubmit` lacks a try/catch (see FS-5..FS-11); `mutation.isError` flips silently
- [ ] Confirmation panel renders the typed email verbatim — case and whitespace are preserved (no trim)
- [ ] Double-submit — disabled button prevents a second `POST`
- [ ] Resubmit after success — no in-page reset; user must navigate away and back
- [ ] Browser back from the confirmation panel — Next.js history pop returns to the form, but RHF state is unmounted, values are gone ⚠ unverified
- [ ] Email field with whitespace-only input — Zod's `.email()` rejects with "Please enter a valid email"
- [ ] Suspense — none on this page (no `useSearchParams`); no fallback flash
- [ ] Enter key in the Email input submits the form (RHF default)
- [ ] Slow backend — the loading state holds the user for up to N seconds; no timeout configured client-side
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

## Accessibility Requirements

- [ ] Tab order: Email → Send Reset Link → "Back to login" inline link
- [ ] Email input uses the shared `TextInput` (renders an associated `<label>`) and the required indicator
- [ ] Validation errors render as `helperText` under the input — not as a toast (avoids screen-reader churn for inline validation)
- [ ] Submit button announces its loading state with "Loading..." text rather than only a spinner
- [ ] Toast container has `aria-live="polite"` (Sonner default); success toasts default to 3000 ms
- [ ] Confirmation panel preserves heading hierarchy (layout `<h1>` → page `<h2>` "Check your email")
- [ ] The "Back to login" links use real anchors (Next.js `<Link>`) and have a primary text color with hover underline
- [ ] `MailCheck` and `ArrowLeft` icons are decorative; surrounding text carries the meaning
- [ ] Focus remains on the page (no modal/dialog); after the form swaps to the confirmation panel, focus does not auto-move to the new heading ⚠ unverified — a future iteration may want to focus the heading or the Back-to-login button for keyboard users
