# Feature Doc: Signup

Feature documentation for the `/signup` page. Used by `/generate-tests signup`
(or `--docs e2e/ux_flow_docs/signup.md`) to ensure all positive and negative user cases
are covered alongside the component source analysis.

The signup page registers a new user + (optionally) a new organization. It
calls `POST /auth/signup` with five fields (`first_name`, `last_name`, `email`,
`password`, optional `organization_name`) and on success swaps the form for a
"Check your email" confirmation panel — the **frontend never auto-logs the
user in** because email verification is required first.

---

## Page

- **Route**: `/signup` (under the `(auth)` route group; legacy `/auth/signup` callers should arrive here)
- **Component**: `src/app/(auth)/signup/page.tsx` (default export `SignupPage` — single client component, no Suspense wrapper because it does not use `useSearchParams`)
- **Layout**: `src/app/(auth)/layout.tsx` — shared with the rest of `(auth)/*`
- **Auth required**: no — this is a **public** page
- **Redirect when already authenticated**: not enforced today (no `src/middleware.ts`). A signed-in user can still load `/signup` and submit, which would create a parallel account — discouraged but not blocked. ⚠ unverified whether a future iteration adds a client-side redirect

---

## User Stories

### US-1: Register and trigger an email verification

**As a** new user, **I want to** enter my name, email, password, and optional org name, **so that** the backend creates my account and sends a verification email to me.

**Acceptance criteria**:

- [ ] Heading reads "Create your account" with subtitle "Start building AI voice agents in minutes"
- [ ] Five fields render in this order: First Name, Last Name, Email, Organization Name (optional), Password
- [ ] Required fields (`first_name`, `last_name`, `email`, `password`) show the required indicator
- [ ] "Organization Name" shows the helperText "Optional"
- [ ] Submit button label is "Create Account"; loading state is "Loading..."
- [ ] On 201, the form is replaced by a `MailCheck`-icon panel that reads "Check your email" with the submitted email rendered in bold and an outline "Back to Login" button
- [ ] A success toast appears with title "Account created!" and description "Check your email to verify." (4 s duration)

### US-2: Sign in instead

**As a** returning user who clicked the wrong link, **I want to** click "Sign in" at the bottom of the form, **so that** I am redirected to `/login` without losing my place in the auth flow.

**Acceptance criteria**:

- [ ] Text "Already have an account?" is followed by a "Sign in" link
- [ ] Link href is `/login`

### US-3: Block submission on client-side validation errors

**As a** user, **I want to** see field-level errors before submission, **so that** I do not waste a network round-trip on a malformed payload.

**Acceptance criteria**:

- [ ] Empty First Name → helperText "First name is required"
- [ ] Empty Last Name → helperText "Last name is required"
- [ ] Empty Email → helperText "Email is required"
- [ ] Malformed Email → helperText "Please enter a valid email"
- [ ] Password under 8 chars → helperText "Password must be at least 8 characters"
- [ ] Organization Name is optional — empty is allowed
- [ ] While `signup.isPending === true`, Submit button shows "Loading..." and is `disabled`

### US-4: Recover from "Email already registered"

**As a** user who forgot they already have an account, **I want to** see a clear error toast and a "Sign in" affordance, **so that** I can pivot to logging in.

**Acceptance criteria**:

- [ ] 400 response with `{"detail": "Email already registered"}` surfaces toast title "Email already registered"
- [ ] Form stays populated; user can click the "Sign in" link at the bottom

---

## User Workflow Steps

**WF-1: Successful signup → check-email confirmation panel** (positive)

1. User navigates to `/signup` → expected: form renders with the five inputs
2. User types `Ada` / `Lovelace` / `owner@acme.com` / `Acme` / `hunter22!` → expected: Zod resolver clears all helperText
3. User clicks **Create Account** → expected: button enters loading; `POST /auth/signup` fires with `{ email, password, first_name, last_name, organization_name: 'Acme' }` (trimmed)
4. Response is 201 with `access_token`, `user`, `organization` → expected: success toast "Account created!" + description "Check your email to verify." (4 s)
5. `signup.isSuccess` becomes true → expected: form is replaced by the `MailCheck` confirmation panel — heading "Check your email", body "We've sent a verification link to **owner@acme.com**", "Back to Login" outline button

**WF-2: Signup without an organization** (positive)

1. User fills first/last/email/password but leaves Organization Name blank
2. Submit → expected: payload sends `organization_name: undefined` (the `?.trim() || undefined` shortcut in `authApi.signup`); backend defaults the org
3. Same confirmation panel as WF-1

**WF-3: Organization name with surrounding whitespace** (positive)

1. User types `   Acme   ` for Organization Name
2. Submit → expected: payload sends `organization_name: 'Acme'` (trimmed before send)

**WF-4: Email already registered** (negative)

1. User enters an email that already exists
2. Submit → expected: 400 `{"detail": "Email already registered"}`
3. `handleApiError` surfaces toast "Email already registered"; form remains in submission state-reset (button re-enables), inputs keep user values; `signup.isSuccess` stays false

**WF-5: Client-side validation gates submit** (negative)

1. User leaves all required fields blank and submits → expected: helperText appears under First Name, Last Name, Email, Password; no `POST /auth/signup` is fired
2. User enters `7chars` password → expected: helperText "Password must be at least 8 characters"
3. User fixes all errors → submission proceeds

**WF-6: Navigation to login** (positive)

1. User clicks "Sign in" link at the bottom → expected: navigation to `/login`
2. User reaches confirmation panel (WF-1) and clicks "Back to Login" → expected: navigation to `/login`

**WF-7: Already-authenticated visit** (edge)

1. User has `access_token` in localStorage and visits `/signup` → expected: page still renders the form (no automatic redirect today). Submitting will create a second account if the email is different — ⚠ unverified guard, treat as edge

---

## Input Specifications

Source: `src/schemas/auth.ts` (`signupSchema`).

| Field             | Type     | Required | Validation Rules                                                       | Exact Error Message                      |
| ----------------- | -------- | -------- | ---------------------------------------------------------------------- | ---------------------------------------- |
| First Name        | text     | yes      | `z.string().min(1)`                                                    | "First name is required"                 |
| Last Name         | text     | yes      | `z.string().min(1)`                                                    | "Last name is required"                  |
| Email             | email    | yes      | `z.string().min(1).email()`                                            | "Email is required" / "Please enter a valid email" |
| Organization Name | text     | no       | `z.string().optional()` — no length rule; empty allowed                | n/a                                      |
| Password          | password | yes      | `z.string().min(8)`                                                    | "Password must be at least 8 characters" |

**Button state rules:**

- "Create Account" is **never disabled** by `formState.isValid`; invalid submit surfaces inline helperText instead
- While `signup.isPending === true`, the shadcn `<Button>` renders "Loading..." and sets `disabled`
- Once `signup.isSuccess === true`, the entire form unmounts and the confirmation panel renders instead — there is no way back to the form on this page

---

## Success Scenarios

**PS-1: Full signup with org → confirmation panel**

- **Preconditions**: not authenticated; valid form.
- **Steps**: fill all five fields → click Create Account.
- **Expected outcome**: success toast "Account created!" / "Check your email to verify."; form replaced by confirmation panel; submitted email rendered in bold inside the panel.
- **Mock API** (`POST /auth/signup`, 201):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "00000000-0000-0000-0000-000000000001",
      "organization_id": "00000000-0000-0000-0000-000000000100",
      "email": "owner@acme.com",
      "first_name": "Ada",
      "last_name": "Lovelace",
      "avatar_url": null,
      "role": "owner",
      "is_active": true,
      "is_verified": false,
      "auth_provider": "local",
      "last_login_at": null,
      "created_at": "2026-06-17T10:00:00+00:00",
      "updated_at": "2026-06-17T10:00:00+00:00"
    },
    "organization": {
      "id": "00000000-0000-0000-0000-000000000100",
      "name": "Acme",
      "slug": "acme",
      "subscription_tier": "free",
      "status": "active"
    },
    "role": "owner",
    "email_verification_token": "raw-verification-token-leaked-in-response"
  }
  ```

**PS-2: Signup without organization → confirmation panel**

- **Preconditions**: not authenticated; Organization Name left blank.
- **Steps**: fill first/last/email/password; submit.
- **Expected outcome**: same confirmation panel as PS-1; payload sends `organization_name: undefined`; backend assigns a default workspace.

**PS-3: Trimmed organization name**

- **Steps**: type `  Acme  ` for Organization Name; submit.
- **Expected outcome**: confirmation panel; the request body has `organization_name: "Acme"`.

**PS-4: Click "Back to Login" from the confirmation panel**

- **Preconditions**: PS-1 reached.
- **Steps**: click the outline "Back to Login" button.
- **Expected outcome**: navigation to `/login`.

**PS-5: Loading indicator visible during slow signup**

- **Preconditions**: backend deliberately slow.
- **Steps**: submit valid form.
- **Expected outcome**: button renders "Loading..." with `disabled`; user cannot double-click.

**PS-6: Navigation to /login via bottom link**

- **Steps**: click "Sign in" link at the bottom of the form.
- **Expected outcome**: client-side navigation to `/login`; no network calls.

**PS-7: Confirmation panel renders submitted email verbatim**

- **Preconditions**: PS-1 submitted email `Mixed.Case+Tag@Example.COM`.
- **Expected outcome**: panel body shows `Mixed.Case+Tag@Example.COM` verbatim (no client-side lowercasing — `watch('email')` returns the typed value).

---

## Failure Scenarios

**FS-1: Empty First Name**

- **Mock API**: not called.
- **Expected UI**: helperText "First name is required" under First Name; no toast; form unchanged.

**FS-2: Empty Last Name**

- **Expected UI**: helperText "Last name is required".

**FS-3: Empty Email**

- **Expected UI**: helperText "Email is required".

**FS-4: Malformed Email**

- **Steps**: type `not-an-email`.
- **Expected UI**: helperText "Please enter a valid email".

**FS-5: Empty Password**

- **Expected UI**: helperText "Password must be at least 8 characters" (Zod's `min(8)` rejects empty strings; required-string is not separately enforced).

**FS-6: Short Password (< 8 chars)**

- **Steps**: type `7charss` (7 chars).
- **Expected UI**: helperText "Password must be at least 8 characters".

**FS-7: 400 Email already registered**

- **Mock API** (`POST /auth/signup`, 400): `{ "detail": "Email already registered" }`
- **Expected UI**: toast title "Email already registered"; button re-enables; form remains populated.

**FS-8: 400 Email and password are required**

- **Mock API** (`POST /auth/signup`, 400): `{ "detail": "Email and password are required" }`
- **Expected UI**: toast title "Email and password are required". (Unreachable under healthy Zod, but the backend still returns it for direct API callers.)

**FS-9: 400 first_name is required**

- **Mock API** (`POST /auth/signup`, 400): `{ "detail": "first_name is required" }`
- **Expected UI**: toast title "first_name is required".

**FS-10: 422 Validation error (malformed body)**

- **Mock API** (`POST /auth/signup`, 422):
  ```json
  { "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
  ```
- **Expected UI**: `handleApiError` falls back to "Something went wrong. Please try again." (detail is not a string).

**FS-11: 500 Internal Server Error**

- **Mock API** (`POST /auth/signup`, 500): `{ "detail": "Internal Server Error" }`
- **Expected UI**: toast "Internal Server Error"; form stays editable.

**FS-12: Network failure**

- **Mock API**: route aborted.
- **Expected UI**: toast "Something went wrong. Please try again.".

**FS-13: Double-submit guard**

- **Steps**: click Create Account twice in rapid succession against a slow backend.
- **Expected UI**: second click is a no-op (button disabled while `signup.isPending`); exactly one `POST /auth/signup` is recorded.

**FS-14: Organization name with only whitespace**

- **Steps**: type `   ` (3 spaces) for Organization Name.
- **Mock API** (`POST /auth/signup`, 201): same as PS-1.
- **Expected UI**: payload sends `organization_name: undefined` (`'   '.trim() || undefined` → `undefined`); backend defaults the org.

**FS-15: Email with leading/trailing whitespace**

- **Steps**: type `  user@acme.com  `; submit.
- **Mock API**: depends on backend normalization (⚠ unverified). If backend rejects: `{ "detail": "Invalid email" }` → toast "Invalid email"; otherwise 201.

**FS-16: Authenticated visit to `/signup` redirects to `/home`**

- **Preconditions**: localStorage has valid `access_token` and the user lands on `/signup`.
- **Expected UI**: client-side guard redirects to `/home`; the signup form is never rendered. ⚠ Document current behaviour exactly — today the form renders. Update once the guard ships.

**FS-17: Slow API (>3s) keeps Create Account button in loading state**

- **Mock API** (`POST /auth/signup`, 201 but delayed ~3500 ms): success after delay.
- **Expected UI**: button text stays "Loading..." with `disabled` for the full duration; clicking again is a no-op; confirmation panel appears only after the response resolves.

**FS-18: Network failure during submit preserves form data**

- **Mock API**: route aborted to simulate offline.
- **Expected UI**: toast "Something went wrong. Please try again."; all five inputs still contain their typed values; button re-enables for retry.

**FS-19: 401 mid-flow (rare for signup) surfaces toast**

- **Mock API** (`POST /auth/signup`, 401): `{ "detail": "Could not validate credentials" }`
- **Expected UI**: toast title "Could not validate credentials"; user remains on `/signup`; no auto-redirect to `/login` from this endpoint.

**FS-20: 409 conflict — duplicate email (alternative to FS-7)**

- **Mock API** (`POST /auth/signup`, 409): `{ "detail": "Email already registered" }`
- **Expected UI**: toast "Email already registered"; identical UX to FS-7 (the backend currently uses 400 but a future change to 409 must surface the same toast).

**FS-21: First name with XSS / unicode**

- **Steps**: type `<script>alert(1)</script>` into First Name; fill remaining fields validly; submit.
- **Mock API** (`POST /auth/signup`, 201): success.
- **Expected UI**: payload sends the literal string; the confirmation panel renders the submitted email (not the name), so no script executes in the DOM. Re-fetching the user shows the name escaped as text.

**FS-22: First / last name with emoji**

- **Steps**: type `Ada 🎉` / `Lovelace 💎`; fill remaining fields; submit.
- **Mock API** (`POST /auth/signup`, 201): success.
- **Expected UI**: payload includes the emoji verbatim; no UI breakage.

**FS-23: First name with leading / trailing whitespace**

- **Steps**: type `  Ada  ` for First Name.
- **Expected UI**: payload sends the value verbatim today (no client-side trim — ⚠ unverified). Backend may or may not trim. Document the observed behaviour and fail loudly if the confirmation panel renders ` Ada `.

**FS-24: Very long first name (>500 chars)**

- **Steps**: type a 600-char First Name; submit.
- **Expected UI**: input accepts the value (no client maxlength); backend likely rejects with 400 / 422 → toast surfaces the `detail`; form stays populated.

**FS-25: Paste with newlines into a single-line input**

- **Steps**: paste `Ada\nLovelace` into the First Name field.
- **Expected UI**: single-line input strips the newline at paste time; value becomes `AdaLovelace` or `Ada Lovelace` depending on browser; Zod accepts non-empty value.

**FS-26: Whitespace-only First Name fails validation**

- **Steps**: type `   ` for First Name; fill other fields validly; submit.
- **Expected UI**: ⚠ today Zod `min(1)` passes because `'   '.length >= 1`; the value is sent to the backend. Treat as a gap — assert observed behaviour and tighten the schema to `.trim().min(1)` if needed.

**FS-27: Tab order through the form**

- **Steps**: focus First Name → press Tab repeatedly.
- **Expected UI**: focus moves First Name → Last Name → Email → Organization Name → Password → password Eye toggle → Create Account → "Sign in" link.

**FS-28: Submit via Enter key in Password**

- **Steps**: fill all required fields validly, focus the Password input, press Enter.
- **Expected UI**: form submits exactly as a click on Create Account would.

**FS-29: Helper-text errors are announced via aria-live**

- **Steps**: submit with empty First Name.
- **Expected UI**: helperText element renders with `role="alert"` (or `aria-live`) so screen readers announce "First name is required" without focus change.

**FS-30: Browser back from confirmation panel**

- **Preconditions**: WF-1 completed; user is on the confirmation panel.
- **Steps**: press browser Back.
- **Expected UI**: URL unchanged (history was not pushed on the swap); pressing Back leaves `/signup` entirely (e.g. lands on the previous referrer). ⚠ verify in test — Next.js does not push history for the in-component swap.

### Full lifecycle (`*-FULL`)

**SU-FULL: End-to-end signup lifecycle in a single test**

- **Preconditions**: A unique random email `__e2e__signup_<uuid>@example.com` is generated in the test body (NOT mocked).
- **Steps in one Playwright test body**:
  1. Visit `/signup` without auth → expect form with five inputs rendered.
  2. Submit with all fields empty → expect helperText on First Name, Last Name, Email, Password.
  3. Submit valid fields except `7chars` password → expect "Password must be at least 8 characters".
  4. Submit valid fields → expect success toast "Account created!" with description "Check your email to verify."; expect confirmation panel with the submitted email in `<strong>`.
  5. Click "Back to Login" inside the confirmation panel → expect URL `/login`.
  6. Press browser Back → expect URL `/signup` (form unmounted on success — confirmation panel re-renders today since `signup.isSuccess` may persist in the component cache; verify and document).
  7. Click "Sign in" link below the form (if form re-rendered) → expect URL `/login`.
  8. Re-submit the same email from a fresh `/signup` visit → expect toast "Email already registered" (duplicate check).
- **Cleanup (in `finally`)**: Delete the created user (and the auto-created org if any) via the backend admin API.
- **Naming**: `SU-FULL — signup full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` from `@/lib/toast`. Title and description render in separate elements inside `[data-sonner-toast]`.

| Trigger                                | Toast title                                  | Toast description           | Variant |
| -------------------------------------- | -------------------------------------------- | --------------------------- | ------- |
| Successful signup                      | `Account created!`                           | `Check your email to verify.` | success |
| 400 email already registered           | `Email already registered`                   | —                           | error   |
| 400 missing email/password             | `Email and password are required`            | —                           | error   |
| 400 first_name is required             | `first_name is required`                     | —                           | error   |
| Any 5xx with string `detail`           | (verbatim, e.g. `Internal Server Error`)     | —                           | error   |
| Any error where `detail` is not string | `Something went wrong. Please try again.`    | —                           | error   |

---

## UI Elements

| Element                       | Type            | Content / Label                                         | Behavior                                                |
| ----------------------------- | --------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| Heading                       | h2              | "Create your account"                                   | Static                                                  |
| Subtitle                      | p               | "Start building AI voice agents in minutes"             | Static                                                  |
| First Name input              | TextInput       | placeholder "Jane"                                      | Required, Zod-validated                                 |
| Last Name input               | TextInput       | placeholder "Doe"                                       | Required, Zod-validated                                 |
| Email input                   | TextInput       | placeholder "you@company.com"                           | Required, Zod-validated                                 |
| Organization Name input       | TextInput       | placeholder "Acme Corp" + helperText "Optional"         | Optional, sent trimmed                                  |
| Password input                | TextInput (pwd) | placeholder "Min. 8 characters"                         | Required, min 8 chars                                   |
| Create Account button         | Button          | "Create Account" → "Loading..."                         | `type="submit"`; disabled while `signup.isPending`      |
| Sign in CTA                   | Link            | "Sign in" (after "Already have an account?")            | Navigates to `/login`                                   |
| MailCheck icon                | lucide icon     | `MailCheck`                                             | Renders only in the success panel                       |
| Confirmation heading          | h2              | "Check your email"                                      | Renders only after `signup.isSuccess === true`          |
| Confirmation body             | p               | "We've sent a verification link to **<email>**"         | `<strong>` wraps the submitted email                    |
| Confirmation help             | p               | "Click the link in the email to verify your account and start using Tone." | Static                       |
| Back to Login button          | Button (outline)| "Back to Login"                                         | Navigates to `/login`                                   |

---

## Navigation

| Trigger                                       | Destination          | Condition                                  |
| --------------------------------------------- | -------------------- | ------------------------------------------ |
| Successful signup (201)                       | (stays on `/signup`) | Form swaps to the confirmation panel       |
| Click "Sign in" (bottom of form)              | `/login`             | Always                                     |
| Click "Back to Login" (confirmation panel)    | `/login`             | Always                                     |
| Already authenticated visit                   | (stays on `/signup`) | No automatic redirect today ⚠ unverified  |

---

## API Contracts

Payloads sourced from the Postman collection (folder `Authentication`).

| Endpoint        | Method | Request                                                                                          | Success Response                              | Error Response          |
| --------------- | ------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------- | ----------------------- |
| `/auth/signup`  | POST   | `{ email, password, first_name, last_name, organization_name? }` (trimmed before send)           | 201 `AuthLoginResponse` (mirrors `/auth/login`) | `{ "detail": "..." }`   |

### Example: `POST /auth/signup`

Request body (with org):

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "organization_name": "Acme"
}
```

Request body (without org — `organization_name` key omitted, not sent as empty string):

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!",
  "first_name": "Ada",
  "last_name": "Lovelace"
}
```

201 Created response body:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "00000000-0000-0000-0000-000000000001",
    "organization_id": "00000000-0000-0000-0000-000000000100",
    "email": "owner@acme.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "avatar_url": null,
    "role": "owner",
    "is_active": true,
    "is_verified": false,
    "auth_provider": "local",
    "last_login_at": null,
    "created_at": "2026-06-17T10:00:00+00:00",
    "updated_at": "2026-06-17T10:00:00+00:00"
  },
  "organization": {
    "id": "00000000-0000-0000-0000-000000000100",
    "name": "Acme",
    "slug": "acme",
    "subscription_tier": "free",
    "status": "active"
  },
  "role": "owner",
  "email_verification_token": "raw-verification-token-leaked-in-response"
}
```

400 Bad Request — duplicate email:

```json
{ "detail": "Email already registered" }
```

400 Bad Request — missing first_name:

```json
{ "detail": "first_name is required" }
```

400 Bad Request — missing email/password:

```json
{ "detail": "Email and password are required" }
```

422 Validation Error:

```json
{ "detail": [{ "loc": ["body"], "msg": "field required", "type": "value_error.missing" }] }
```

**Note**: The frontend ignores the response payload — `useSignup` does not call `setLoginResponse`, so the user remains signed out after a successful signup. The user must verify their email and then sign in via `/login`.

---

## Edge Cases

- [ ] Already-authenticated visit — page still renders the signup form (no client-side redirect today)
- [ ] Empty Organization Name → `?.trim() || undefined` strips it; payload omits the field entirely
- [ ] Whitespace-only Organization Name (`"   "`) — same treatment as empty (`undefined` is sent)
- [ ] Email already registered — toast surfaces, form values preserved, user can pivot to "Sign in"
- [ ] Double submit — `<Button disabled>` while `signup.isPending`; only one `POST /auth/signup` fires
- [ ] Browser back from the confirmation panel — Next.js history pop returns to the editable form, but the RHF state was unmounted on success, so values are gone ⚠ unverified
- [ ] Confirmation panel reads `watch('email')` — if the email field had been cleared between submit and response (unlikely in practice), the rendered email could be blank
- [ ] Long names (>100 chars) — frontend has no max-length; backend behaviour ⚠ unverified
- [ ] Password contains the user's email — accepted by Zod; backend may or may not reject ⚠ unverified
- [ ] User pastes a password with non-ASCII chars — accepted verbatim
- [ ] Network failure mid-submit — `signup.isError` becomes true but no `isSuccess`; form remains; toast surfaces fallback string
- [ ] Backend returns 201 but `user.is_verified === true` (auto-verify in some dev envs) — frontend still shows the "Check your email" panel because it does not branch on `is_verified`
- [ ] Suspense — none on this page (no `useSearchParams`), so there is no fallback flash
- [ ] Quick-typed submit (Enter key in any input) — RHF default behaviour submits the form
- [ ] User leaves the page mid-mutation — TanStack Query's `useMutation` finishes in the background; no UI update because the component is unmounted

---

## Business Rules

- The signup endpoint creates **both** a user and (when `organization_name` is provided) an organization in a single call — the user becomes the `owner` of the new org
- When `organization_name` is omitted, the backend creates a default workspace for the user (or assigns them to an invitation target — ⚠ unverified path for invite-based signup)
- **Email verification is mandatory** before login; the frontend reflects this by showing the "Check your email" panel and never auto-logging the user in
- The verification token returned in the response payload (`email_verification_token`) is a **backend dev leak** — the frontend never reads it (the user receives the same token by email)
- Password minimum length is enforced at 8 characters client-side (Zod); the backend independently enforces the same rule and returns 400 if the client is bypassed
- Tokens (`access_token` / `refresh_token`) in the 201 response are **not persisted** by the signup page — `useSignup` is a plain mutation; only `useLogin` calls `setLoginResponse`
- The user's email is rendered verbatim in the confirmation panel (no normalisation); backend may or may not lowercase it during storage

---

## Accessibility Requirements

- [ ] Tab order: First Name → Last Name → Email → Organization Name → Password → Create Account → Sign in link
- [ ] All inputs use the shared `TextInput` which renders a `<label>` associated with the input
- [ ] Required indicators are visible to sighted users **and** announced (TextInput adds the required attribute on the underlying input via RHF Controller)
- [ ] Validation errors render under the input as `helperText` (RHF `fieldState.error.message`) — not as a toast
- [ ] The confirmation panel preserves the heading hierarchy: layout `<h1>` then page `<h2>` "Check your email"
- [ ] "Loading..." button text replaces the spinner-only state so screen readers announce the wait
- [ ] Toast container has `aria-live="polite"` (Sonner default); error toasts default to 5000 ms
- [ ] The "Sign in" and "Back to Login" links are real anchors (Next.js `<Link>`), keyboard-focusable, with a primary text color and hover underline
- [ ] `MailCheck` icon in the confirmation panel is decorative; the surrounding heading and body text carry the meaning
