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

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Valid token shows success UI, toast, and Go-to-Login

**Preconditions**:
- User opens a fresh, unused verification link

**Action**:
1. Visit `/verify-email?token=raw-verification-token-from-email`

**Observation 1 — Network request**:
1. Exactly one `POST /auth/verify-email` request is recorded
2. Request body equals `{ "token": "raw-verification-token-from-email" }`
3. Request `Content-Type` header is `application/json`

**Observation 2 — Loading state before response**:
1. `<AppLoader label="Verifying your email..." />` is visible while pending
2. No success or error UI is in the DOM during loading

**Observation 3 — Success UI replaces loader**:
1. Green `CheckCircle` icon is visible in the rounded green wrapper
2. `<h2>` heading reads exactly `Email Verified!`
3. Body `<p>` reads exactly `Your email has been verified successfully. Please log in to continue.`
4. A "Go to Login" `<Button>` is rendered inside a `<Link href="/login">`

**Observation 4 — Toast**:
1. A Sonner toast appears in `[data-sonner-toast]`
2. Toast title equals `Email verified successfully!`
3. Toast variant is `success`

**API mock**: `POST /auth/verify-email` → 200 with the body from PS-1 above.

---

### TC-HAPPY-002: Suspense fallback renders before inner content hydrates

**Preconditions**:
- Browser CPU throttling enabled (e.g. 4x) to delay hydration

**Action**:
1. Visit `/verify-email?token=raw-verification-token-from-email`

**Observation 1 — Outer Suspense fallback**:
1. The outer `VerifyEmailPage` Suspense `AppLoader` (no label) is visible during initial hydration

**Observation 2 — Inner loader replaces it**:
1. Once `VerifyEmailContent` mounts, the inner `AppLoader` with label `Verifying your email...` replaces the outer fallback

---

### TC-HAPPY-003: Strict mode double-render fires exactly one API call

**Preconditions**:
- Running in dev mode where React 19 strict-mode runs effects twice

**Action**:
1. Visit `/verify-email?token=raw-verification-token-from-email`

**Observation 1 — Single network request**:
1. Exactly one `POST /auth/verify-email` request is recorded
2. `startedRef.current` is `true` after first invocation; second pass early-returns

**Observation 2 — Success UI still renders normally**:
1. The success card with `Email Verified!` heading is visible
2. Toast `Email verified successfully!` appears

**API mock**: `POST /auth/verify-email` → 200.

---

### TC-NAV-001: Click "Go to Login" after success navigates to /login

**Preconditions**:
- TC-HAPPY-001 just completed; success UI is visible

**Action**:
1. Click the "Go to Login" button

**Observation 1 — URL change**:
1. URL becomes `/login`
2. The verify-email page is no longer in the DOM

**Observation 2 — No additional network calls**:
1. Zero additional `POST /auth/verify-email` requests are recorded

---

### TC-HAPPY-004: Logged-in user verifies email and still stays on the page

**Preconditions**:
- `useAuthStore` has a hydrated user (localStorage `tone_access_token` set)
- Token is valid

**Action**:
1. Visit `/verify-email?token=raw-verification-token-from-email`

**Observation 1 — Same mutation runs**:
1. Exactly one `POST /auth/verify-email` request is recorded
2. Success UI renders

**Observation 2 — No auto-redirect**:
1. URL remains `/verify-email?...` until the user clicks "Go to Login"

> ⚠ unverified — confirm there is no global "redirect authed user away from auth pages" middleware.

**API mock**: `POST /auth/verify-email` → 200.

---

### TC-VALIDATE-001: Missing `?token` shows inline error and fires no API call

**Preconditions**:
- User opens the page directly with no query string

**Action**:
1. Visit `/verify-email`

**Observation 1 — Zero network calls**:
1. Zero `POST /auth/verify-email` requests are recorded
2. `startedRef.current` remains `false`

**Observation 2 — Error UI renders inline**:
1. Red `XCircle` icon is visible in the rounded red wrapper
2. `<h2>` heading reads exactly `Verification Failed`
3. Body `<p>` reads exactly `Invalid verification link`
4. A "Back to Login" outline `<Button>` is rendered inside a `<Link href="/login">`

**Observation 3 — No toast is shown**:
1. No Sonner toast appears in `[data-sonner-toast]`

---

### TC-VALIDATE-002: Empty `?token=` value shows the same inline error

**Action**:
1. Visit `/verify-email?token=`

**Observation 1 — No API call**:
1. Zero `POST /auth/verify-email` requests are recorded (`token === ''` is falsy)

**Observation 2 — Error UI matches missing-token case**:
1. `<h2>` reads `Verification Failed`
2. Body reads `Invalid verification link`
3. No toast appears

---

### TC-ERROR-001: 400 invalid or expired token shows backend `detail`

**Action**:
1. Visit `/verify-email?token=expired-xyz`

**Observation 1 — Network call fires**:
1. Exactly one `POST /auth/verify-email` request is recorded with body `{ "token": "expired-xyz" }`

**Observation 2 — Error UI**:
1. Red `XCircle` icon visible
2. `<h2>` reads `Verification Failed`
3. Body reads exactly `Invalid or expired verification token`

**Observation 3 — Error toast**:
1. Toast title equals `Invalid or expired verification token`
2. Toast variant is `error`

**API mock**: `POST /auth/verify-email` → 400 `{ "detail": "Invalid or expired verification token" }`.

---

### TC-ERROR-002: 400 already-verified email shows backend `detail`

**Action**:
1. Visit `/verify-email?token=consumed-xyz`

**Observation 1 — Error UI**:
1. Body reads exactly `Email is already verified`

**Observation 2 — Toast title matches**:
1. Toast title equals `Email is already verified`

> Note: the `Email is already verified` detail comes from `POST /auth/resend-verification`, not `/auth/verify-email`, but the same 400 shape is plausible here. ⚠ unverified.

**API mock**: `POST /auth/verify-email` → 400 `{ "detail": "Email is already verified" }`.

---

### TC-ERROR-003: Missing `detail` field falls back to "Verification failed"

**Action**:
1. Visit `/verify-email?token=any`

**Observation 1 — Error UI body**:
1. Body reads exactly `Verification failed` (the page's literal fallback)

**Observation 2 — Toast title**:
1. Toast title equals `Verification failed`

**API mock**: `POST /auth/verify-email` → 400 `{}`.

---

### TC-ERROR-004: 401 Unauthorized renders backend `detail`

**Action**:
1. Visit `/verify-email?token=any`

**Observation 1 — Error UI**:
1. Body reads exactly `Could not validate credentials`

**Observation 2 — No auto-redirect**:
1. URL remains `/verify-email?token=any` — the axios interceptor's empty 401 block does NOT redirect today

**API mock**: `POST /auth/verify-email` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-005: 404 Not Found renders backend `detail`

**Action**:
1. Visit `/verify-email?token=any`

**Observation 1 — Error UI**:
1. Body reads exactly `Verification token not found`

**Observation 2 — Toast**:
1. Toast title equals `Verification token not found`

**API mock**: `POST /auth/verify-email` → 404 `{ "detail": "Verification token not found" }`.

---

### TC-ERROR-006: 500 Internal Server Error surfaces the verbatim string

**Action**:
1. Visit `/verify-email?token=any`

**Observation 1 — Error UI**:
1. Body reads exactly `Internal Server Error`

**Observation 2 — Toast**:
1. Toast title equals `Internal Server Error`

**API mock**: `POST /auth/verify-email` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-007: 422 with array `detail` falls back ungracefully

**Action**:
1. Visit `/verify-email?token=any`

**Observation 1 — Error UI**:
1. The page reads `err.response.data.detail` — when it is an array, the truthy check `detail || 'Verification failed'` yields the array (truthy)
2. React stringifies the array into a poor representation (effectively unreadable text)

> ⚠ unverified — confirm with manual run whether `setErrorMsg` receives an object array; if so this is a UX bug worth noting in the spec.

**API mock**: `POST /auth/verify-email` → 422 `{ "detail": [{ "type": "missing", "loc": ["body", "token"], "msg": "Field required", "input": {} }] }`.

---

### TC-ERROR-008: Network failure falls back to "Verification failed"

**Action**:
1. Visit `/verify-email?token=any` with the route aborted

**Observation 1 — Error UI body**:
1. Body reads `Verification failed` (because `(err as any)?.response?.data?.detail` is undefined)

**Observation 2 — Toast**:
1. Toast title equals `Verification failed`

**Observation 3 — Back-to-Login still visible**:
1. The "Back to Login" outline button is rendered

**API mock**: `POST /auth/verify-email` route aborted (no response).

---

### TC-NAV-002: Click "Back to Login" after error navigates to /login

**Preconditions**:
- TC-VALIDATE-001 or TC-ERROR-001 just rendered the error UI

**Action**:
1. Click the "Back to Login" button

**Observation 1 — URL change**:
1. URL becomes `/login`

---

### TC-LOADING-001: Slow API keeps the loader visible for the full duration

**Action**:
1. Visit `/verify-email?token=any` with a deliberately slow backend (3500 ms delay)

**Observation 1 — AppLoader stays visible throughout**:
1. `<AppLoader label="Verifying your email..." />` is visible from mount until ~3500 ms
2. The success UI does not appear until the response resolves

**Observation 2 — Exactly one request**:
1. Only one `POST /auth/verify-email` request fires even if the user re-renders

**API mock**: `POST /auth/verify-email` → 200 delayed by 3500 ms.

---

### TC-EDGE-001: URL-encoded special characters are decoded by useSearchParams

**Preconditions**:
- Link is `/verify-email?token=abc%2Bdef%3D%3D` (encodes `+` and `==`)

**Action**:
1. Visit the encoded URL

**Observation 1 — Request body uses decoded value**:
1. `POST /auth/verify-email` body equals `{ "token": "abc+def==" }`

**Observation 2 — Success UI renders**:
1. Success card with `Email Verified!` is visible

**API mock**: `POST /auth/verify-email` → 200.

---

### TC-EDGE-002: Very long token (>1024 chars) is sent unchanged

**Action**:
1. Visit `/verify-email?token=<1024-char-string>`

**Observation 1 — No client-side truncation**:
1. `POST /auth/verify-email` body `token` length equals 1024

**Observation 2 — Success UI renders**:
1. Success card is visible without UI breakage

**API mock**: `POST /auth/verify-email` → 200.

---

### TC-EDGE-003: Token with `<script>` is rendered as plain text in error body

**Preconditions**:
- URL is `/verify-email?token=<script>alert(1)</script>` (browser encodes it)

**Action**:
1. Visit the URL

**Observation 1 — Backend rejects**:
1. `POST /auth/verify-email` is called with the decoded token

**Observation 2 — DOM is safe**:
1. The error body renders the backend `detail` verbatim
2. The `<script>` substring (if present in `detail`) is rendered as text — React escapes by default
3. `window.alert` was not invoked

**API mock**: `POST /auth/verify-email` → 400 `{ "detail": "Invalid or expired verification token" }`.

---

### TC-EDGE-004: Whitespace-only token still fires the mutation

**Preconditions**:
- URL is `/verify-email?token=%20%20%20` (3 spaces)

**Action**:
1. Visit the URL

**Observation 1 — Mutation fires**:
1. Token is truthy (non-empty string) → `POST /auth/verify-email` body is `{ "token": "   " }`

**Observation 2 — Backend rejects**:
1. Error UI renders with backend `detail`

**API mock**: `POST /auth/verify-email` → 400 `{ "detail": "Invalid or expired verification token" }`.

---

### TC-EDGE-005: Token containing `&` is truncated by useSearchParams

**Preconditions**:
- URL is `/verify-email?token=foo&bar`

**Action**:
1. Visit the URL

**Observation 1 — Token is the substring before `&`**:
1. `useSearchParams().get('token')` returns `"foo"`
2. Mutation fires with `{ "token": "foo" }` and gets 400

**API mock**: `POST /auth/verify-email` → 400 `{ "detail": "Invalid or expired verification token" }`.

---

### TC-EDGE-006: User opens two tabs with the same token

**Action**:
1. Open `/verify-email?token=raw-verification-token-from-email` in tab A
2. Open the same URL in tab B before A completes

**Observation 1 — First wins**:
1. Tab A receives 200 and renders the success UI
2. Tab B receives 400 (consumed token) and renders the error UI

**API mock**: first request → 200; subsequent → 400 `{ "detail": "Invalid or expired verification token" }`.

---

### TC-EDGE-007: User refreshes the success page consumes-again gap

**Preconditions**:
- TC-HAPPY-001 just succeeded

**Action**:
1. Reload the page (still on `/verify-email?token=raw-verification-token-from-email`)

**Observation 1 — Second mutation fires**:
1. Exactly one new `POST /auth/verify-email` request is recorded

**Observation 2 — Error UI replaces success UI**:
1. Error UI renders with backend `detail` (e.g. `Email is already verified` or `Invalid or expired verification token`)

> UX gap — refreshing post-success surfaces an error to the user.

**API mock**: `POST /auth/verify-email` → 400.

---

### TC-EDGE-008: User clicks "Go to Login" during loading

**Action**:
1. Visit `/verify-email?token=any` with a slow backend
2. Click "Go to Login" while the loader is showing (if any anchor is reachable)

**Observation 1 — Navigation succeeds**:
1. URL becomes `/login` if a CTA is reachable during loading
2. No setState-on-unmounted warning fires (React Query handles this)

> Note: there is no CTA on the loading state today, so this primarily verifies that the mutation does not cause warnings if the component unmounts before resolution.

---

### TC-EDGE-009: Tab is closed mid-request

**Action**:
1. Visit `/verify-email?token=any` with a slow backend
2. Close the tab before response resolves

**Observation 1 — No client-side abort**:
1. The mutation has no `AbortController` signal — the backend may still process the verification
2. No client-visible behaviour to assert (browser-level)

---

### TC-NAV-003: Browser back from success / error UI

**Preconditions**:
- Success or error UI rendered

**Action**:
1. Press the browser Back button

**Observation 1 — History navigation**:
1. URL returns to whatever was before `/verify-email` (typically blank — link comes from email)
2. The page does not push history on the status flip

---

### TC-A11Y-001: AppLoader exposes role=status with label

**Action**:
1. Visit `/verify-email?token=any` (with a slow backend so the loader is visible)
2. Inspect the loader DOM node

**Observation 1 — Loading state announced**:
1. The `AppLoader` root has `role="status"`
2. The loader exposes an accessible name from `aria-label="Loading"` or the `label` prop (`Verifying your email...`)

---

### TC-A11Y-002: Success and failure icons are decorative; heading conveys state

**Action**:
1. Trigger success (TC-HAPPY-001) → inspect DOM
2. Trigger error (TC-ERROR-001) → inspect DOM

**Observation 1 — Headings present in both states**:
1. Success state has `<h2>Email Verified!</h2>`
2. Error state has `<h2>Verification Failed</h2>`

**Observation 2 — Icons do not depend on color alone**:
1. Success uses green `CheckCircle` + "Email Verified!" text
2. Error uses red `XCircle` + "Verification Failed" text — SR users get the same information via the heading

---

### TC-A11Y-003: CTA buttons are keyboard reachable

**Action**:
1. After success (or error) UI renders, focus the page body
2. Press Tab repeatedly

**Observation 1 — Tab order reaches the CTA**:
1. Focus moves through the layout's ThemeToggle and then the main CTA ("Go to Login" or "Back to Login")
2. There is no form on this page

**Observation 2 — Enter activates the CTA**:
1. With the CTA focused, pressing Enter navigates to `/login`

---

### TC-A11Y-004: Error / success messages are announced via aria-live

**Action**:
1. Trigger TC-VALIDATE-001 (missing token)
2. Inspect the inline error body and toast surface

**Observation 1 — Inline error region**:
1. The inline error body renders inside an `aria-live="polite"` region (or has `role="alert"`) so SR users hear `Invalid verification link` on flip to error

**Observation 2 — Toast region**:
1. The Sonner toast container renders in an `aria-live` region so successful/failed states are announced

---

### TC-A11Y-005: Missing page-level h1 — heading hierarchy gap

**Action**:
1. Inspect the rendered page hierarchy on success and error states

**Observation 1 — Only h2 present**:
1. `<h2>` is the only heading on success/error states; there is no `<h1>`
2. The layout-level `Logo` is decorative

> ⚠ Consider adding a visually-hidden `<h1>"Email Verification"</h1>` for SR users.

---

### TC-FULL-001: End-to-end verify-email lifecycle

**Preconditions**:
- A test user `__e2e__ve_<uuid>@example.com` is provisioned via the backend signup API
- A verification token is fetched from the response or a test-only admin endpoint

**Action**:
1. Visit `/verify-email` (no token)
2. Click "Back to Login"
3. Navigate to `/verify-email?token=` (empty)
4. Navigate to `/verify-email?token=<valid>`
5. Click "Go to Login"
6. Sign in with the provisioned user's credentials
7. Navigate back to `/verify-email?token=<valid>` (now consumed)

**Observation 1 — Step 1 shows invalid card**:
1. Error UI `Verification Failed` / `Invalid verification link`
2. Zero `POST /auth/verify-email` requests recorded

**Observation 2 — Step 2 navigates to /login**:
1. URL becomes `/login`

**Observation 3 — Step 3 still shows invalid card**:
1. Error UI renders identical to step 1; no network call

**Observation 4 — Step 4 shows success**:
1. AppLoader briefly visible
2. Success UI `Email Verified!` with green check
3. Toast `Email verified successfully!` appears

**Observation 5 — Step 5 navigates to /login**:
1. URL becomes `/login`

**Observation 6 — Step 6 logs in**:
1. Login succeeds (verifies the user is actually marked verified server-side)

**Observation 7 — Step 7 surfaces consumed-token error**:
1. Error UI shows backend `detail` `Invalid or expired verification token`
2. Toast title matches

**Cleanup** (in `finally`):
1. Delete the provisioned user (and any auto-created org) via the backend admin API

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above)

- [x] Page opened without `?token` — see TC-VALIDATE-001
- [x] Page opened with empty `?token=` — see TC-VALIDATE-002
- [x] React strict-mode double-render — see TC-HAPPY-003
- [x] Token already used — see TC-ERROR-002 / TC-EDGE-006
- [x] Backend returns `detail: null` — see TC-ERROR-003
- [x] Backend returns `detail` as object/array — see TC-ERROR-007
- [x] Page reachable without auth — see TC-HAPPY-004
- [x] Tab closed mid-request — see TC-EDGE-009
- [x] User clicks CTA during loading — see TC-EDGE-008
- [x] Two tabs to the same `?token=...` — see TC-EDGE-006
- [x] User refreshes the success page — see TC-EDGE-007
- [x] Token with `&` truncated — see TC-EDGE-005
- [x] Whitespace-only token — see TC-EDGE-004
- [x] URL-encoded special chars — see TC-EDGE-001
- [x] Very long token — see TC-EDGE-002
- [x] XSS in token — see TC-EDGE-003

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

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] `AppLoader` exposes `role="status"` and label — see TC-A11Y-001
- [x] Success / failure icons decorative; heading conveys state — see TC-A11Y-002
- [x] CTA buttons keyboard reachable — see TC-A11Y-003
- [x] Toasts + inline errors announced via `aria-live` — see TC-A11Y-004
- [x] Heading hierarchy gap (no `<h1>`) — see TC-A11Y-005

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
