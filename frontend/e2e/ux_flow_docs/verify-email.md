# Feature Doc: Verify Email

Feature documentation for the email verification page. Used by
`/generate-tests verify-email` (or `--docs e2e/ux_flow_docs/verify-email.md`) to ensure
both happy-path and error scenarios are covered alongside the component source
analysis.

The Verify Email page is a **token-driven** landing page: the user clicks a
link in the verification email, the page extracts the `token` query param, and
fires `POST /auth/verify-email` exactly once on mount. The page never accepts
typed input — there is no form, no resend button on this page. The full UI is
driven by a `status` state of `'loading' | 'success' | 'error'`.

---

## Page

- **Route**: `/verify-email`
- **Component**: `src/app/(auth)/verify-email/page.tsx`
- **Layout**: `src/app/(auth)/layout.tsx` (shared auth split-screen with `Logo`,
  `ThemeToggle`, and the branded right panel)
- **Suspense wrapper**: yes — outer `VerifyEmailPage` wraps the inner
  `VerifyEmailContent` in `<Suspense fallback={<AppLoader className="animate-page" />}>`
  because the inner component reads `useSearchParams()`
- **Auth required**: no — this is a public page (no `middleware.ts` token check;
  the page is part of the public `(auth)` route group)
- **API hook**: `useVerifyEmail()` from `@/lib/api/auth` — `useMutation` wrapping
  `authApi.verifyEmail(token)` which calls `POST /auth/verify-email { token }`

---

## User Stories

### US-1: Verify email via emailed link

**As a** newly signed-up user, **I want to** click the verification link in my
welcome email, **so that** my account is marked verified and I can sign in.

**Acceptance criteria**:

- [ ] Page reads `?token=<raw-verification-token-from-email>` from the URL
- [ ] On mount, the page fires `POST /auth/verify-email` exactly once (even in
      React strict-mode double-render — guarded by `startedRef`)
- [ ] While the request is in flight, the page renders `<AppLoader label="Verifying your email..." />`
- [ ] On 200 success: success state UI shows a green check icon, "Email Verified!"
      heading, supportive copy, and a "Go to Login" button linking to `/login`
- [ ] A success toast "Email verified successfully!" appears (Sonner default 3s)

### US-2: Handle missing or malformed token

**As a** user landing on `/verify-email` without a valid token, **I want to**
see a clear failure state with a recovery path, **so that** I don't get stuck.

**Acceptance criteria**:

- [ ] No `?token` in URL → status flips to `error` immediately (no network call);
      inline error reads "Invalid verification link"
- [ ] Error UI shows a red X icon, "Verification Failed" heading, the error
      message, and a "Back to Login" outline button linking to `/login`
- [ ] No toast is shown when the token is missing (only inline error)

### US-3: Surface backend errors

**As a** user clicking an expired or already-used verification link, **I want to**
see the backend's reason, **so that** I know whether to request a new link.

**Acceptance criteria**:

- [ ] Backend 400 `{"detail":"Invalid or expired verification token"}` → status
      flips to `error`, inline message shows the backend `detail` verbatim
- [ ] Error toast surfaces the same `detail` string as title
- [ ] Falls back to `"Verification failed"` if the response has no `detail`

### US-4: Auth gating

**As an** unauthenticated visitor, **I want to** access `/verify-email` directly,
**so that** clicking the email link works regardless of session state.

**Acceptance criteria**:

- [ ] The route group `(auth)` does not enforce a token; the page is reachable
      without `tone_access_token`
- [ ] Already-logged-in users hitting `/verify-email?token=...` still go through
      the same verify mutation (no auto-redirect to `/home`)

---

## User Workflow Steps

**WF-1: Verify email — happy path** (positive)

1. User clicks `https://app.tone.com/verify-email?token=raw-verification-token-from-email`
   from the welcome email → expected: page mounts, Suspense fallback `AppLoader`
   may flash briefly
2. `VerifyEmailContent` mounts, reads `token` from `useSearchParams()` → expected:
   token is non-null
3. `useEffect` fires once (`startedRef.current` toggles to `true`) →
   `mutation.mutateAsync(token)` → `POST /auth/verify-email { token }`
4. While pending → expected: `status === 'loading'`, `<AppLoader label="Verifying your email..." />` rendered
5. 200 response arrives → expected: `setStatus('success')`, success toast
   "Email verified successfully!" rendered, success UI replaces loader
6. User clicks the "Go to Login" button → expected: `<Link href="/login">` navigates
   to `/login`

**WF-2: Missing token** (negative)

1. User opens `https://app.tone.com/verify-email` directly (no `?token`) → expected:
   page mounts
2. `useEffect` runs → `token` is `null` → `setStatus('error')`, `setErrorMsg('Invalid verification link')`
3. `startedRef.current` remains `false`; no API call is made → expected: zero
   network requests to `/auth/verify-email`
4. Error UI shows red X + "Verification Failed" + "Invalid verification link"
5. User clicks "Back to Login" → expected: navigates to `/login`

**WF-3: Expired or already-used token** (negative)

1. User opens `/verify-email?token=expired-xyz` → expected: page mounts, loader shows
2. `POST /auth/verify-email` → backend returns `400 {"detail":"Invalid or expired verification token"}`
3. Mutation rejects → `setStatus('error')`, `setErrorMsg('Invalid or expired verification token')`,
   error toast title = `"Invalid or expired verification token"`
4. User clicks "Back to Login" → expected: navigates to `/login`

**WF-4: Strict mode double-render guard** (positive)

1. In dev, React 19 strict-mode causes effects to run twice → expected:
   `startedRef.current` flips to `true` on the first invocation; the second pass
   early-returns; `POST /auth/verify-email` is called **exactly once**

**WF-5: Backend network failure** (negative)

1. User opens `/verify-email?token=any` → loader shows
2. `POST /auth/verify-email` → backend returns 500 (no `detail`) → expected:
   `errorMsg` falls back to `"Verification failed"`; error toast title = `"Verification failed"`

---

## Input Specifications

This page has **no form inputs**. The only "input" is the `token` URL query parameter.

| Source        | Field   | Type   | Required | Validation Rules                                                                                                                                                | Exact Error Message            |
| ------------- | ------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| URL query     | `token` | string | yes      | Must be present; no client-side format check (any non-empty string is sent to backend). Backend validates token is a known, unexpired email-verification token. | "Invalid verification link" (when missing) / backend `detail` (when invalid) |

**Behavioural rules:**

- The page short-circuits to error state when `token` is `null`/empty (no API call).
- `startedRef` (a `useRef<boolean>`) prevents duplicate `POST /auth/verify-email`
  calls on rerender.

---

## Success Scenarios

**PS-1: Valid token → success UI + toast + Go to Login link**

- **Preconditions**: User has a fresh, unused verification token in URL.
- **Steps**: open `/verify-email?token=raw-verification-token-from-email`.
- **Expected outcome**: loader appears briefly; after response, success UI shows
  green check, "Email Verified!" heading, copy `"Your email has been verified successfully. Please log in to continue."`, "Go to Login" `Button` in a `<Link href="/login">`; toast title `"Email verified successfully!"` appears.
- **Mock API** (`POST /auth/verify-email`, 200):
  ```json
  {
    "message": "Email verified successfully",
    "user": {
      "id": "8c7a8b50-9d0a-4d63-9b3c-1a2b3c4d5e6f",
      "email": "owner@acme.com",
      "is_verified": true
    }
  }
  ```

**PS-2: Suspense fallback renders before client hydration**

- **Preconditions**: Slow hydration (throttle CPU 4x).
- **Steps**: open `/verify-email?token=raw-verification-token-from-email`.
- **Expected outcome**: outer `VerifyEmailPage` Suspense fallback `AppLoader`
  is visible during hydration; once `VerifyEmailContent` mounts, the inner
  `AppLoader` with label `"Verifying your email..."` replaces it.

**PS-3: Strict mode — single API call**

- **Preconditions**: Dev mode with React strict-mode double-render.
- **Steps**: open `/verify-email?token=raw-verification-token-from-email`.
- **Expected outcome**: only one `POST /auth/verify-email` request is recorded;
  success UI renders normally.
- **Mock API**: as PS-1.

**PS-4: User clicks "Go to Login" after success**

- **Preconditions**: PS-1 success state.
- **Steps**: click "Go to Login".
- **Expected outcome**: route changes to `/login`; verify-email page unmounts.

**PS-5: Logged-in user verifies email**

- **Preconditions**: `useAuthStore` has a hydrated user; user lands on
  `/verify-email?token=raw-verification-token-from-email` from a re-sent link.
- **Steps**: page loads.
- **Expected outcome**: page runs the same mutation, success UI renders; no
  auto-redirect happens — user must click "Go to Login". ⚠ unverified — confirm
  there is no global "redirect authed user away from auth pages" middleware.

---

## Failure Scenarios

**FS-1: No `token` query param → inline error, no API call**

- **Preconditions**: User opens `/verify-email` directly.
- **Steps**: navigate.
- **Mock API**: not called.
- **Expected UI behavior**: error UI with `"Verification Failed"` heading and
  `"Invalid verification link"` body; "Back to Login" button visible; no toast.

**FS-2: Empty `token` query param** (e.g. `/verify-email?token=`)

- **Mock API**: not called (`token === ''` is falsy).
- **Expected UI**: same as FS-1 — `"Invalid verification link"` inline error.

**FS-3: Invalid / expired token (400)**

- **Preconditions**: User opens `/verify-email?token=expired-xyz`.
- **Mock API** (`POST /auth/verify-email`, 400):
  ```json
  { "detail": "Invalid or expired verification token" }
  ```
- **Expected UI**: error UI; `errorMsg = "Invalid or expired verification token"`;
  toast title = `"Invalid or expired verification token"`.

**FS-4: Already-verified email (400)**

- **Preconditions**: Token belongs to a user whose email is already verified —
  the verify-email endpoint itself rejects re-use. (Note: the `Email is already verified`
  detail comes from `POST /auth/resend-verification`, not `/auth/verify-email`,
  but the same 400 shape is plausible here.) ⚠ unverified.
- **Mock API** (`POST /auth/verify-email`, 400):
  ```json
  { "detail": "Email is already verified" }
  ```
- **Expected UI**: error UI showing `"Email is already verified"` verbatim;
  toast title same.

**FS-5: Missing `detail` on error → fallback**

- **Mock API** (`POST /auth/verify-email`, 400): `{}`
- **Expected UI**: `errorMsg = "Verification failed"` (the page's fallback
  literal); toast title = `"Verification failed"`.

**FS-6: 401 Unauthorized**

- **Mock API** (`POST /auth/verify-email`, 401):
  ```json
  { "detail": "Could not validate credentials" }
  ```
- **Expected UI**: error UI with `"Could not validate credentials"`; toast title same.
  Axios interceptor's `if (status === 401) {}` empty block does **not**
  auto-redirect today.

**FS-7: 404 Not Found**

- **Mock API** (`POST /auth/verify-email`, 404):
  ```json
  { "detail": "Verification token not found" }
  ```
- **Expected UI**: error UI showing `"Verification token not found"`; toast title same.

**FS-8: 500 Internal Server Error**

- **Mock API** (`POST /auth/verify-email`, 500):
  ```json
  { "detail": "Internal Server Error" }
  ```
- **Expected UI**: error UI showing `"Internal Server Error"`; toast title same.

**FS-9: 422 Validation Error — `detail` is array**

- **Mock API** (`POST /auth/verify-email`, 422):
  ```json
  {
    "detail": [
      {
        "type": "missing",
        "loc": ["body", "token"],
        "msg": "Field required",
        "input": {}
      }
    ]
  }
  ```
- **Expected UI**: page reads `err.response.data.detail` — when it is an array,
  the truthy check `detail || 'Verification failed'` yields the array (truthy)
  which React will render as concatenated string of objects → effectively the
  page falls back to displaying nothing useful. ⚠ unverified — confirm with manual run
  whether `setErrorMsg` receives an object array; if so this is a UX bug worth
  noting in the spec.

**FS-10: Network error (offline, ECONNREFUSED)**

- **Mock API**: route aborted → axios throws without `response` object.
- **Expected UI**: `(err as any)?.response?.data?.detail` is `undefined`, so
  `errorMsg = "Verification failed"`; toast title = `"Verification failed"`.

**FS-11: Very long token URL (e.g. 1024+ chars)**

- **Mock API** (`POST /auth/verify-email`, 200): same as PS-1.
- **Expected UI**: success UI renders unchanged; no token truncation client-side.

**FS-12: Token containing URL-encoded special chars**

- **Preconditions**: link is `/verify-email?token=abc%2Bdef%3D%3D` (`+` and `==`).
- **Mock API** (`POST /auth/verify-email`, 200) with body
  `{ "token": "abc+def==" }`: success.
- **Expected UI**: `useSearchParams().get('token')` returns the decoded value;
  axios posts JSON body with decoded value; success UI renders.

**FS-13: Slow API (>3s) keeps loader visible**

- **Mock API** (`POST /auth/verify-email`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: `AppLoader` with label "Verifying your email..." remains visible for the full duration; only after the response resolves does the success UI render. No additional requests fire even if the user re-renders.

**FS-14: Network failure / offline during the mutation**

- **Mock API**: route aborted.
- **Expected UI**: `errorMsg` falls back to "Verification failed"; error UI renders with "Back to Login" button; toast title "Verification failed".

**FS-15: Authenticated visit to `/verify-email?token=...`**

- **Preconditions**: localStorage has valid `access_token` (different user or same user re-verifying).
- **Expected UI**: page runs the same mutation; on success the success UI renders. No auto-redirect to `/home`. Clicking "Go to Login" navigates to `/login` even though the user is already authenticated. ⚠ Document this as the current behaviour.

**FS-16: Token with XSS / special chars (`<script>`)**

- **Preconditions**: URL is `/verify-email?token=<script>alert(1)</script>` (browser will URL-encode).
- **Mock API** (`POST /auth/verify-email`, 400): `{ "detail": "Invalid or expired verification token" }`.
- **Expected UI**: error UI renders the backend `detail` verbatim; the `<script>` substring is rendered as plain text (React escapes by default — no DOM injection).

**FS-17: Very long token (>500 chars)**

- **Preconditions**: URL has a 1024-char token.
- **Mock API** (`POST /auth/verify-email`, 200): success.
- **Expected UI**: success UI renders unchanged; no truncation client-side.

**FS-18: Whitespace-only token**

- **Preconditions**: URL is `/verify-email?token=%20%20%20` (3 spaces).
- **Mock API** (`POST /auth/verify-email`, 400): `{ "detail": "Invalid or expired verification token" }`.
- **Expected UI**: token is truthy (non-empty string) → mutation fires; backend rejects; error UI renders.

**FS-19: Tab order through the success / error UI**

- **Preconditions**: success or error UI visible.
- **Steps**: focus the page body → press Tab repeatedly.
- **Expected UI**: focus moves through the layout's ThemeToggle → main CTA ("Go to Login" or "Back to Login") only. There is no form on this page.

**FS-20: Enter key activates the visible CTA**

- **Preconditions**: success or error UI visible; CTA button has focus.
- **Steps**: press Enter.
- **Expected UI**: navigates to `/login`.

**FS-21: Error message is announced via aria-live**

- **Preconditions**: FS-1 (missing token) error state.
- **Expected UI**: the inline error body renders inside an `aria-live="polite"` region (or has `role="alert"`) so screen readers announce "Invalid verification link" once the status flips to `error`.

**FS-22: Browser back from success / error UI**

- **Preconditions**: success or error UI rendered.
- **Steps**: press browser Back.
- **Expected UI**: URL returns to whatever was before `/verify-email` (typically nothing — the link comes from email). The page does not push history on the status flip.

### Full lifecycle (`*-FULL`)

**VE-FULL: End-to-end verify-email lifecycle in a single test**

- **Preconditions**: A test user `__e2e__ve_<uuid>@example.com` is provisioned via the backend signup API; a verification token is fetched from the response (the signup endpoint currently includes `email_verification_token` for dev environments) or from a test-only admin endpoint.
- **Steps in one Playwright test body**:
  1. Visit `/verify-email` (no token) → expect error UI "Verification Failed" / "Invalid verification link"; no `POST /auth/verify-email` request.
  2. Click "Back to Login" → expect URL `/login`.
  3. Navigate to `/verify-email?token=` → expect same error UI; no network call.
  4. Navigate to `/verify-email?token=<valid>` → expect AppLoader briefly; then success UI "Email Verified!" with green check and a toast "Email verified successfully!".
  5. Click "Go to Login" → expect URL `/login`.
  6. Sign in with the provisioned user's credentials → expect successful login (verifies the user is actually marked verified server-side).
  7. Navigate back to `/verify-email?token=<valid>` (consumed) → expect error UI with backend `detail` ("Invalid or expired verification token") and a toast.
- **Cleanup (in `finally`)**: Delete the provisioned user (and any auto-created org) via the backend admin API.
- **Naming**: `VE-FULL — verify-email full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` (`src/lib/toast.ts`). Sonner renders title
and (optional) description as separate elements inside `[data-sonner-toast]`.

| Trigger                                           | Toast title                         | Toast description | Variant |
| ------------------------------------------------- | ----------------------------------- | ----------------- | ------- |
| Verify-email mutation 200                         | `Email verified successfully!`       | —                 | success |
| Verify-email mutation 4xx with string `detail`    | (backend `detail` verbatim)         | —                 | error   |
| Verify-email mutation with no `detail`            | `Verification failed`               | —                 | error   |
| Missing `token` query param                       | (no toast — inline error only)      | —                 | —       |

Note: the page does **not** call `handleApiError` — it manually extracts
`detail` and calls `showToast.error(detail)` inline. Default error duration is
5 s.

---

## UI Elements

| Element                | Type       | Content / Label                                                              | Behavior                                                                  |
| ---------------------- | ---------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Loading spinner        | `AppLoader`| label "Verifying your email..."                                              | Renders while `status === 'loading'`; SVG voice-wave bars + `role="status"`|
| Success icon           | `CheckCircle` (lucide) | h-8 w-8 text-green-600 in rounded-full bg-green-100 wrapper      | Rendered when `status === 'success'`                                       |
| Success heading        | `<h2>`     | "Email Verified!"                                                            | Rendered on success                                                       |
| Success body           | `<p>`      | "Your email has been verified successfully. Please log in to continue."      | Rendered on success                                                       |
| Go to Login button     | `Button`   | "Go to Login" (inside `<Link href="/login">`)                                | Navigates to `/login`                                                     |
| Failure icon           | `XCircle` (lucide) | h-8 w-8 text-red-600 in rounded-full bg-red-100 wrapper             | Rendered when `status === 'error'`                                        |
| Failure heading        | `<h2>`     | "Verification Failed"                                                        | Rendered on error                                                         |
| Failure body           | `<p>`      | `errorMsg` (either `"Invalid verification link"`, `"Verification failed"`, or backend `detail`) | Renders dynamic message                            |
| Back to Login button   | `Button` (variant=`outline`) | "Back to Login" (inside `<Link href="/login">`)            | Navigates to `/login`                                                     |
| Outer Suspense fallback| `AppLoader`| no label                                                                     | Renders during initial hydration before `VerifyEmailContent` mounts        |

---

## Navigation

| Trigger                                | Destination               | Condition                                       |
| -------------------------------------- | ------------------------- | ----------------------------------------------- |
| Click "Go to Login" (success state)    | `/login`                  | Always                                          |
| Click "Back to Login" (error state)    | `/login`                  | Always                                          |
| Visit `/verify-email` without `?token` | stays on `/verify-email`  | Renders error state immediately, no redirect    |
| Visit `/verify-email?token=...`        | stays on `/verify-email`  | Fires mutation; success/error UI replaces loader|
| Logo / ThemeToggle (in layout header)  | Various (logo → home if signed in) | Layout-level — not page logic            |

---

## API Contracts

Real payloads sourced from
`/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json`
(folder: `Authentication → POST /auth/verify-email`).

| Endpoint                    | Method | Request                                  | Success Response                                                                                  | Error Response                                                                |
| --------------------------- | ------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `/api/v1/auth/verify-email` | POST   | `{ "token": "<raw-verification-token>" }` | 200: `{ "message": "Email verified successfully", "user": { "id": "...", "email": "...", "is_verified": true } }` | 400: `{ "detail": "token is required" }` / `{ "detail": "Invalid or expired verification token" }` |

### Example: `POST /auth/verify-email` (success)

Request body:

```json
{
  "token": "raw-verification-token-from-email"
}
```

200 OK response body:

```json
{
  "message": "Email verified successfully",
  "user": {
    "id": "8c7a8b50-9d0a-4d63-9b3c-1a2b3c4d5e6f",
    "email": "owner@acme.com",
    "is_verified": true
  }
}
```

### Example: 400 — missing token (request body had no `token` field)

```json
{ "detail": "token is required" }
```

### Example: 400 — token expired or already consumed

```json
{ "detail": "Invalid or expired verification token" }
```

The page only consumes `data.detail` for the error UI; the success body's `user`
object is unused by the page (the user is expected to sign in afterwards).

---

## Edge Cases

- [ ] Page opened without `?token` → instant error state, zero network calls
- [ ] Page opened with empty `?token=` → instant error state, zero network calls
- [ ] React strict-mode double-render → mutation fires exactly once (`startedRef` guard)
- [ ] Token already used (e.g. user clicked link twice in two tabs) → backend 400,
      error toast + inline error
- [ ] Backend returns `detail: null` → falls back to `"Verification failed"`
- [ ] Backend returns `detail` as object/array → page renders `errorMsg` truthy
      but React stringifies poorly (⚠ unverified UX hole)
- [ ] Page is reachable without auth — no middleware redirect even when user has
      no `tone_access_token`
- [ ] Tab is closed mid-request → axios call is not aborted via
      `AbortController` (the mutation has no signal); on a slow connection the
      backend may still process the verification
- [ ] User clicks "Go to Login" while loading → loader replaced by route change;
      no toast races (`useMutation` won't fire `setStatus` on an unmounted component)
- [ ] User opens two tabs to `/verify-email?token=...` simultaneously → first wins,
      second hits a 400 expired token, shows error UI
- [ ] User refreshes the success page → fires mutation again, second call returns
      400 "already verified" or similar → error UI replaces success UI (UX gap)
- [ ] User pastes a token with `&` in it (URL-unsafe) → `useSearchParams()` returns
      only the substring before `&`, mutation fails with 400

---

## Business Rules

- A verification token is single-use: backend invalidates it on first success.
- Tokens are time-limited (backend-controlled TTL — typical: 24 hours).
- The verify-email endpoint does **not** log the user in: a successful response
  flips `is_verified` on the user record only. The user must visit `/login`.
- The page is public — there is no `tone_access_token` requirement; this is a
  deliberate UX choice so verification links work in any browser session.
- The token is sent as a **POST body** (not query string), so it does not appear
  in server logs or browser history.

---

## Accessibility Requirements

- [ ] `AppLoader` exposes `role="status"` and `aria-label="Loading"` (or the
      provided `label` prop) so screen readers announce the loading state
- [ ] Success / failure icons are decorative — they should be wrapped in a parent
      with a textual heading (`<h2>`) so SR users get the same information
- [ ] Both "Go to Login" and "Back to Login" CTAs are real `<Button>` rendered
      inside `<Link>` — keyboard tab focus reaches them
- [ ] Toast messages render as a Sonner `aria-live` region; the inline error
      heading + body provide the same info if toasts are dismissed
- [ ] Heading hierarchy: `<h2>` is the only heading on the success/error states
      — there is no `<h1>` on the page (layout-level `Logo` is decorative). ⚠
      consider adding visually-hidden `<h1>"Email Verification"</h1>` for SR users
- [ ] Color is not the only differentiator: success uses green CheckCircle +
      "Email Verified!" text; error uses red XCircle + "Verification Failed" text
- [ ] No automatic focus management — focus stays on `<body>` after status flips;
      this is acceptable for non-form UIs but the SR live region for the toast
      is the primary announcement
