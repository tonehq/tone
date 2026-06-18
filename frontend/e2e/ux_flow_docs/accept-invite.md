# Feature Doc: Accept Invitation

Feature documentation for the organization-invitation acceptance page. Used by
`/generate-tests accept-invite` (or `--docs e2e/ux_flow_docs/accept-invite.md`) to ensure
both happy-path and error scenarios are covered alongside the component source
analysis.

The Accept Invitation page is a **token-driven** landing page. It:

1. Reads `?token=<raw-invite-token>` (or the legacy `?code=` alias).
2. Validates the token via `GET /auth/validate-invitation?token=...` (React
   Query `useValidateInvitation`).
3. Branches the UI based on validation result + current auth state:
   - **No token** → invalid card.
   - **Loading** → `AppLoader`.
   - **Invalid / expired** → invalid card with `detail` message.
   - **Signed-in user** → "Accept invitation" one-click card.
   - **Email already has a Tone account** (`invitation.account_exists`) →
     two-button card ("Accept" or "Sign in first").
   - **New user** → full signup form (first_name, last_name, password,
     confirm_password) with email locked from the invitation.

On accept, calls `POST /auth/accept-invitation` and routes the user based on
whether the response contains an `access_token` (auto-login) or a
`requires_login: true` flag (must sign in to consume).

---

## Page

- **Route**: `/accept-invite` (query: `?token=<raw-invite-token>` or legacy `?code=<raw-invite-token>`)
- **Component**: `src/app/(auth)/accept-invite/page.tsx`
- **Layout**: `src/app/(auth)/layout.tsx` (shared auth split-screen)
- **Suspense wrapper**: yes — `AcceptInvitePage` wraps `AcceptInviteContent`
  in `<Suspense fallback={<AppLoader />}>`
- **Auth required**: no — public page, but the page **branches** on
  `useAuthStore().user`. Logged-in users see the one-click card; logged-out users
  with an existing account see a two-button card; truly new users see the
  signup form.
- **API hooks** (from `@/lib/api/auth`):
  - `useValidateInvitation(token, enabled)` → `GET /auth/validate-invitation`
    (React Query `useQuery`, `retry: false`, `refetchOnWindowFocus: false`)
  - `useAcceptInvitation()` → `POST /auth/accept-invitation` (React Query mutation)
- **Auth store**: `useAuthStore()` from `src/stores/auth.ts` provides `user` and
  `setLoginResponse`
- **React Query**: `queryClient.invalidateQueries` is used after accept to refresh
  `me`/`my-org` caches; the `invitation` query is **cancelled** + locally
  disabled (via `accepted` state) to prevent a post-accept refetch that would
  return 400

---

## User Stories

### US-1: New user accepts an invitation

**As a** newly invited user without a Tone account, **I want to** create my
account with first/last name and password, **so that** I'm immediately a member
of the inviting organization.

**Acceptance criteria**:

- [ ] Page reads `?token=<raw-invite-token>` (or `?code=` legacy alias) from URL
- [ ] `GET /auth/validate-invitation` returns `{ valid: true, account_exists: false, email, organization_name, role, ... }`
- [ ] Form renders inside a `CustomCard` titled `"Join {organization_name}"`
      with description `"You've been invited to join as a {role}. Create your account below."`
- [ ] Email field is **read-only**, pre-filled from `invitation.email`
- [ ] First name, last name, password, confirm password are required (Zod schema)
- [ ] Submit button reads `"Create account & join"`; while pending it's disabled + spinner
- [ ] On 200 with `access_token`: `setLoginResponse(data)` writes localStorage,
      toast `"Joined!" / "You're now a member of {organization_name}."`,
      `router.push('/home')`
- [ ] React Query: `setAccepted(true)` first, then `queryClient.cancelQueries`
      for `['invitation', token]`, then `invalidateQueries` for everything else

### US-2: Existing-account user accepts an invitation

**As an** existing Tone user (logged out) who is being invited, **I want to**
accept without creating a new account, **so that** the org is added to my
existing membership.

**Acceptance criteria**:

- [ ] When validation returns `account_exists: true`:
  - Renders a `CustomCard` titled `"Join {organization_name}"` with description
    `"{email} already has a Tone account. Accept to add it to {organization_name}, then sign in."`
  - Shows two buttons: `"Accept invitation"` (primary) and `"Sign in first"` (outline)
  - `"Sign in first"` links to
    `/login?next=${encodeURIComponent('/accept-invite?token=' + token)}`
- [ ] Clicking `"Accept invitation"`:
  - Calls `POST /auth/accept-invitation { token }` (no password/name fields)
  - On 200 with `requires_login: true` (no `access_token`): toast
    `"Added to workspace" / "Please sign in to access {organization_name}."`,
    `router.push('/login')`

### US-3: Logged-in user accepts an invitation

**As a** user already signed in to a different org, **I want to** accept a
fresh invite link, **so that** I gain access to the new workspace immediately.

**Acceptance criteria**:

- [ ] `useAuthStore().user` is non-null → renders a `CustomCard` titled
      `"Join {organization_name}"` with description
      `"You're signed in as {user.email}. Accept this invite to join as {invitation.role}."`
- [ ] One primary button `"Accept invitation"`; while pending, disabled + spinner
- [ ] On 200: `setLoginResponse(data)` (if `access_token`), toast `"Joined!"`,
      `router.push('/home')`

### US-4: Surface invalid / missing / expired tokens

**As a** user clicking a stale or wrong link, **I want to** see a clear error
state with a recovery path.

**Acceptance criteria**:

- [ ] No `?token` and no `?code` → renders invalid `CustomCard` immediately
      (no API call), title `"Invalid invitation"`, description
      `"No invitation token provided."`, `XCircle` icon, "Go to login" button
- [ ] Validation 4xx → invalid `CustomCard` with title `"Invalid invitation"`,
      description from `error.response.data.detail` or fallback
      `"This invitation is invalid or has expired."`, "Go to login" button

### US-5: Auth gating

**As a** signed-out user, **I want to** access `/accept-invite?token=...`
without being redirected to login, **so that** I can sign up via the invite.

**Acceptance criteria**:

- [ ] Page is part of the `(auth)` route group with no `tone_access_token` check;
      validation runs regardless of session state
- [ ] If `?token` is missing, the invalid card renders without any redirect

---

## User Workflow Steps

**WF-1: New user signup via invite** (positive)

1. User clicks `https://app.tone.com/accept-invite?token=raw-invite-token` from email
2. Page mounts, Suspense fallback flashes; `useValidateInvitation(token, true)` fires
   `GET /auth/validate-invitation?token=raw-invite-token`
3. While pending → `<AppLoader label="Validating invitation..." />` rendered
4. 200 with `{ valid: true, account_exists: false, email, role, organization_name, ... }`
   → user is not signed in (`useAuthStore().user === null`) → form variant renders
5. User fills first name, last name, password, confirm password → clicks
   "Create account & join"
6. Zod validates (passwords match, all required) → `POST /auth/accept-invitation`
   with `{ token, password, first_name, last_name }`
7. 200 with `access_token` → `setAccepted(true)`, `cancelQueries(['invitation', token])`,
   `invalidateQueries` for non-invitation keys, `setLoginResponse(data)`,
   toast `"Joined!" / "You're now a member of Acme."`, `router.push('/home')`

**WF-2: Existing account accepts (anonymous)** (positive)

1. User opens link → validation returns `{ valid: true, account_exists: true, email, organization_name, role, ... }`
2. Two-button card renders → user clicks "Accept invitation"
3. `POST /auth/accept-invitation { token }` (no password / name)
4. 200 with `{ requires_login: true, account_exists: true, email, message }`
   (no `access_token`) → toast `"Added to workspace" / "Please sign in to access Acme."`,
   `router.push('/login')`

**WF-3: Signed-in user one-click accepts** (positive)

1. User has localStorage `login_data` + `tone_access_token` for a different org →
   opens invite link
2. `useAuthStore().user` is truthy → "Accept invitation" one-button card renders
3. User clicks Accept → `POST /auth/accept-invitation { token }`
4. 200 with `access_token` → `setLoginResponse(data)` (replaces in-store user
   with the new org context if backend returns it), toast `"Joined!"`,
   `router.push('/home')`

**WF-4: Missing token** (negative)

1. User opens `/accept-invite` (no `?token`, no `?code`) → invalid card renders
   immediately; `useValidateInvitation` early-returns (`enabled: !!token && !accepted`)
2. No API call is made
3. User clicks "Go to login" → `router.push('/login')`

**WF-5: Expired token** (negative)

1. User opens `/accept-invite?token=expired-xyz` → AppLoader shows briefly
2. `GET /auth/validate-invitation` returns 400 `{ "detail": "Invalid or expired invitation" }`
3. Invalid card renders with that detail; "Go to login" button visible

**WF-6: Form validation blocks submit** (negative)

1. New user variant rendered → user clicks "Create account & join" with
   empty fields → Zod blocks submit, helperText errors appear inline; no API call
2. User types short password (`abc`) → Zod error `"Password must be at least 8 characters"`
3. User types mismatched confirm → Zod error `"Passwords do not match"` on
   `confirm_password` field (path-specific refinement)

**WF-7: Legacy `?code=` alias** (positive)

1. User opens `/accept-invite?code=raw-invite-token` (older email) → same as WF-1
   step 1, because `token = searchParams.get('token') || searchParams.get('code') || ''`
2. Validation + accept use `token`; emails containing both query names get
   `?token` precedence

**WF-8: Post-accept refetch guard** (positive)

1. After WF-1 step 7 → `setAccepted(true)` was already set; `useValidateInvitation`
   sees `enabled = !!token && !accepted = false` → no refetch
2. `queryClient.cancelQueries` aborts any pending validation request
3. `invalidateQueries` for non-invitation keys (predicate `q.queryKey?.[0] !== 'invitation'`)
   refreshes `me` and `my-org`

**WF-9: Signed-in user clicks "Sign in first"** (negative — irrelevant flow)

1. The "Sign in first" button only renders when `account_exists: true` AND user
   is signed out. Signed-in users do not see it
2. Clicking it navigates to `/login?next=%2Faccept-invite%3Ftoken%3Draw-invite-token`
3. After login, the redirect logic in `/login` lands the user back on
   `/accept-invite?token=...` and the one-click-accept card now renders (US-3 path)

---

## Input Specifications

Source: `src/schemas/auth.ts` (Zod `acceptInviteSchema`). Form only renders
in the "new user" variant (no signed-in user, no existing account).

| Field            | Type     | Required | Validation Rules                                                                                                       | Exact Error Message                                                                  |
| ---------------- | -------- | -------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| email            | email    | yes      | Pre-filled from `invitation.email`, **read-only** (`disabled`)                                                          | n/a (locked)                                                                         |
| first_name       | text     | yes      | `z.string().min(1)`                                                                                                    | `First name is required`                                                             |
| last_name        | text     | yes      | `z.string().min(1)`                                                                                                    | `Last name is required`                                                              |
| password         | password | yes      | `z.string().min(8)`                                                                                                    | `Password must be at least 8 characters`                                             |
| confirm_password | password | yes      | `z.string().min(1)`; refined `data.password === data.confirm_password` with `path: ['confirm_password']`                | `Please confirm your password` (empty) / `Passwords do not match` (mismatch)         |

**Other inputs** (URL params, not form fields):

| Source    | Field   | Type   | Required | Validation Rules                                              | Exact Error Message                                                  |
| --------- | ------- | ------ | -------- | ------------------------------------------------------------- | -------------------------------------------------------------------- |
| URL query | `token` | string | yes      | Must be non-empty; the legacy `?code=` is accepted as fallback| Inline card with `"No invitation token provided."` when missing      |

**Button state rules:**

- "Create account & join" / "Accept invitation" are **disabled + spinner**
  while `acceptInvitation.isPending`.
- Form submit is blocked client-side by Zod (`zodResolver(acceptInviteSchema)`).

---

## Success Scenarios

**PS-1: New user signs up via invite → auto-login → `/home`**

- **Preconditions**: Signed-out browser; valid token for a new email.
- **Steps**: open `/accept-invite?token=raw-invite-token`; fill first/last/password
  twice; click "Create account & join".
- **Expected outcome**: form submits; `POST /auth/accept-invitation` returns 200
  with `access_token`; toast title `"Joined!"` + description
  `"You're now a member of Acme."`; `router.push('/home')`.
- **Mock APIs**:
  - `GET /auth/validate-invitation?token=raw-invite-token`, 200:
    ```json
    {
      "valid": true,
      "email": "invitee@acme.com",
      "role": "developer",
      "organization_id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
      "organization_name": "Acme",
      "account_exists": false
    }
    ```
  - `POST /auth/accept-invitation`, 200:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.signature",
      "refresh_token": "eyJhbGciOiJIUzI1NiJ9.refresh.signature",
      "token_type": "bearer",
      "user": {
        "id": "8c7a8b50-9d0a-4d63-9b3c-1a2b3c4d5e6f",
        "email": "invitee@acme.com",
        "first_name": "Lin",
        "last_name": "Mo",
        "role": "developer",
        "is_verified": true
      },
      "organization": {
        "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
        "name": "Acme"
      }
    }
    ```

**PS-2: Existing-account anonymous accept → `/login`**

- **Preconditions**: Signed-out browser; invite for an email that already has a
  Tone account.
- **Steps**: open `/accept-invite?token=...`; click "Accept invitation".
- **Expected outcome**: `POST /auth/accept-invitation { token }`; response has
  `requires_login: true` (no `access_token`); toast title
  `"Added to workspace"` + description
  `"Please sign in to access Acme."`; `router.push('/login')`.
- **Mock APIs**:
  - `GET /auth/validate-invitation`, 200: `account_exists: true` shape (as
    above with `account_exists` flipped).
  - `POST /auth/accept-invitation`, 200:
    ```json
    {
      "message": "You have been added to the organization. Please sign in to continue.",
      "account_exists": true,
      "email": "invitee@acme.com",
      "requires_login": true
    }
    ```

**PS-3: Signed-in user one-click accepts**

- **Preconditions**: `useAuthStore().user` truthy (e.g. seeded localStorage with
  a valid `login_data`); valid token for the same email.
- **Steps**: open `/accept-invite?token=...`; click "Accept invitation".
- **Expected outcome**: same toast / redirect as PS-1 (`/home`).
- **Mock APIs**: same as PS-1.

**PS-4: Legacy `?code=` query name**

- **Preconditions**: signed-out; old email with `?code=` alias.
- **Steps**: open `/accept-invite?code=raw-invite-token`.
- **Expected outcome**: validation uses `code` value as `token`; rest of flow
  identical to PS-1.
- **Mock APIs**: identical to PS-1, just the URL query name differs.

**PS-5: Email lock**

- **Preconditions**: PS-1 prereqs.
- **Steps**: confirm the email `TextInput` reads `invitee@acme.com` and is
  `disabled` (cannot be edited).
- **Expected outcome**: HTML attribute `disabled` present on input.

**PS-6: Refresh-query guard prevents post-accept 400**

- **Preconditions**: PS-1 success path.
- **Steps**: complete signup → after redirect, manually navigate back to
  `/accept-invite?token=raw-invite-token`.
- **Expected outcome**: `accepted` is `true` only within the in-memory React
  component (does not persist across navigations); on re-mount the page will
  re-call validate-invitation and (because the token is now consumed) get a 400
  → invalid card renders. This is acceptable UX.

---

## Failure Scenarios

**FS-1: Missing both `?token` and `?code`**

- **Preconditions**: User opens `/accept-invite`.
- **Steps**: navigate.
- **Mock API**: not called (`enabled: !!token && !accepted` is false; `token === ''`).
- **Expected UI**: invalid `CustomCard` with `XCircle` icon, title
  `"Invalid invitation"`, description `"No invitation token provided."`,
  "Go to login" button.

**FS-2: Empty `?token=`**

- **Steps**: open `/accept-invite?token=`.
- **Expected UI**: same as FS-1 — `token = ''` is falsy.

**FS-3: Validation 400 — invalid token**

- **Mock API** (`GET /auth/validate-invitation`, 400):
  ```json
  { "detail": "Invalid or expired invitation" }
  ```
- **Expected UI**: invalid card with description `"Invalid or expired invitation"`
  (from `error.response.data.detail`); "Go to login" button.

**FS-4: Validation 200 but `valid: false`**

- **Mock API** (`GET /auth/validate-invitation`, 200):
  ```json
  { "valid": false, "email": "", "role": "", "organization_id": "", "organization_name": "", "account_exists": false }
  ```
- **Expected UI**: page enters the `!invitation?.valid` branch → invalid card
  with fallback description `"This invitation is invalid or has expired."`.

**FS-5: Validation 5xx (network)**

- **Mock API** (`GET /auth/validate-invitation`, 500): `{}`
- **Expected UI**: invalid card with fallback description (because `detail`
  is missing).

**FS-6: Form Zod — empty first name**

- **Steps**: in new-user form, leave first name blank → submit.
- **Expected UI**: helperText `"First name is required"` under first_name;
  no API call.

**FS-7: Form Zod — short password**

- **Steps**: type `abc` (3 chars).
- **Expected UI**: helperText `"Password must be at least 8 characters"`; no API call.

**FS-8: Form Zod — passwords mismatch**

- **Steps**: password `abcd1234`, confirm `abcd9999` → submit.
- **Expected UI**: helperText `"Passwords do not match"` under `confirm_password`
  (path-specific refinement); no API call.

**FS-9: Form Zod — empty confirm**

- **Steps**: password filled, confirm empty → submit.
- **Expected UI**: helperText `"Please confirm your password"` under
  `confirm_password`; no API call.

**FS-10: Accept backend 400 — token missing**

- **Mock API** (`POST /auth/accept-invitation`, 400):
  ```json
  { "detail": "token is required" }
  ```
- **Expected UI**: `handleApiError(err)` → toast title `"token is required"`;
  card stays in form mode; submit button re-enables.

**FS-11: Accept backend 400 — already accepted**

- **Mock API** (`POST /auth/accept-invitation`, 400):
  ```json
  { "detail": "Invitation already accepted" }
  ```
- **Expected UI**: toast title `"Invitation already accepted"`; card stays;
  submit re-enables. ⚠ unverified — actual backend message may differ; this
  is the most likely shape.

**FS-12: Accept backend 401 — unauthorised existing-user accept**

- **Preconditions**: Existing-account two-button card.
- **Mock API** (`POST /auth/accept-invitation`, 401):
  ```json
  { "detail": "Could not validate credentials" }
  ```
- **Expected UI**: toast title `"Could not validate credentials"`; card stays.

**FS-13: Accept backend 5xx**

- **Mock API** (`POST /auth/accept-invitation`, 500):
  ```json
  { "detail": "Internal Server Error" }
  ```
- **Expected UI**: toast title `"Internal Server Error"`; card stays; submit re-enables.

**FS-14: Accept backend 422 — non-string `detail`**

- **Mock API** (`POST /auth/accept-invitation`, 422):
  ```json
  {
    "detail": [
      {
        "type": "value_error",
        "loc": ["body", "password"],
        "msg": "String should have at least 8 characters",
        "input": "abc"
      }
    ]
  }
  ```
- **Expected UI**: `handleApiError` parses `detail.errors` if present; for an
  array shape it falls back to `"Something went wrong. Please try again."`.

**FS-15: User edits localStorage to fake login during invite flow**

- **Preconditions**: User opens valid `?token=...` URL but pre-seeds localStorage
  with garbage `login_data`.
- **Expected UI**: zustand bootstrap may set `user` to a partial object → page
  renders the "signed-in" one-click card with `{user.email}` showing the fake
  value; on Accept the backend rejects with 401 → toast.

**FS-16: Tab closed mid-accept**

- **Preconditions**: PS-1 step 6 in flight.
- **Expected UI**: no AbortController is wired into the mutation; the request
  may still complete server-side; UI is unmounted so no state writes attempted.

**FS-17: Slow API (>3s) on validate keeps loader visible**

- **Mock API** (`GET /auth/validate-invitation`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: `AppLoader` with label "Validating invitation..." stays visible for the full duration; the appropriate card (new-user / existing-account / signed-in) renders only after the response resolves.

**FS-18: Slow API (>3s) on accept keeps button in loading state**

- **Mock API** (`POST /auth/accept-invitation`, 200 but delayed ~3500 ms): success after delay.
- **Expected UI**: button stays disabled with spinner; toast + redirect happen only after the response.

**FS-19: Network failure on validate**

- **Mock API**: `GET /auth/validate-invitation` aborted.
- **Expected UI**: invalid card with fallback description "This invitation is invalid or has expired."; React Query `retry: false` prevents re-fires.

**FS-20: Network failure on accept preserves form data**

- **Mock API**: `POST /auth/accept-invitation` aborted.
- **Expected UI**: toast "Something went wrong. Please try again."; all four form inputs still contain typed values; button re-enables.

**FS-21: First name with XSS / unicode**

- **Steps**: in new-user form, type `<script>alert(1)</script>` into First name; fill remaining fields; submit.
- **Mock API** (`POST /auth/accept-invitation`, 200): success.
- **Expected UI**: payload sends the literal string; React escapes it when rendering anywhere; no DOM injection.

**FS-22: First / last name with emoji**

- **Steps**: type `Lin 🎉` / `Mo 💎`; submit.
- **Expected UI**: payload includes emoji verbatim; success path runs normally.

**FS-23: Very long first name (>500 chars)**

- **Steps**: type a 600-char First name; submit.
- **Expected UI**: input accepts (no maxLength); backend may reject — surface its `detail`.

**FS-24: Paste with newlines into a single-line input**

- **Steps**: paste `Lin\nMo` into First name.
- **Expected UI**: single-line input strips the newline at paste time.

**FS-25: Whitespace-only First name**

- **Steps**: type `   ` (3 spaces); submit.
- **Expected UI**: ⚠ today Zod `min(1)` passes; payload is sent. Document the gap.

**FS-26: Trailing whitespace in password is preserved (no trim)**

- **Steps**: type `validPass1   ` (3 trailing spaces) in both password fields; submit.
- **Expected UI**: payload sends the value verbatim (no trim); backend accepts; subsequent login must use the same value.

**FS-27: Authenticated visit with mismatched email**

- **Preconditions**: localStorage `login_data` is for `other@example.com`; invite is for `invitee@acme.com`.
- **Expected UI**: signed-in one-click card renders showing "You're signed in as other@example.com. Accept this invite to join as developer."; clicking Accept may succeed or 400 depending on backend policy. Document the observed outcome.

**FS-28: Tab order through new-user form**

- **Steps**: focus the page → press Tab repeatedly.
- **Expected UI**: focus moves Email (disabled, skipped or focusable but inert) → First name → Last name → Password → password Eye toggle → Confirm password → Confirm password Eye toggle → "Create account & join" → "Sign in" link.

**FS-29: Submit via Enter key in Confirm password**

- **Steps**: fill all required fields validly, focus Confirm password, press Enter.
- **Expected UI**: form submits exactly as clicking Create account & join would.

**FS-30: Helper-text errors are announced via aria-live**

- **Steps**: submit with mismatched passwords.
- **Expected UI**: helperText "Passwords do not match" under Confirm password renders with `role="alert"` (or `aria-live`) so screen readers announce it.

**FS-31: Browser back from `/home` after accept**

- **Preconditions**: PS-1 completed; user is on `/home`.
- **Steps**: press browser Back.
- **Expected UI**: history returns to `/accept-invite?token=...`; on re-mount the page validates the now-consumed token → renders the invalid card (acceptable UX).

**FS-32: `?token=` URL with whitespace**

- **Preconditions**: URL is `/accept-invite?token=%20valid%20`.
- **Expected UI**: `searchParams.get('token')` returns the value verbatim; validation likely 400 → invalid card.

**FS-33: Conflict (409) on accept — already a member**

- **Mock API** (`POST /auth/accept-invitation`, 409): `{ "detail": "User is already a member of this organization" }`
- **Expected UI**: toast title "User is already a member of this organization"; card stays; submit re-enables.

### Full lifecycle (`*-FULL`)

**AI-FULL: End-to-end accept-invite lifecycle in a single test**

- **Preconditions**:
  - An admin user `__e2e__ai_admin_<uuid>@example.com` with an organization is provisioned via the backend API.
  - An invite for a new email `__e2e__ai_invitee_<uuid>@example.com` is created via the backend Members API; the raw invitation token is captured from the response (or via a test-only admin endpoint).
- **Steps in one Playwright test body**:
  1. Visit `/accept-invite` (no token) → expect invalid card "Invalid invitation" / "No invitation token provided." with a "Go to login" button; no `GET /auth/validate-invitation` request.
  2. Click "Go to login" → expect URL `/login`.
  3. Navigate to `/accept-invite?token=clearly-bad-token` → expect AppLoader briefly; then invalid card with the backend `detail`.
  4. Navigate to `/accept-invite?token=<valid>` (new-user variant) → expect new-user signup card with email locked.
  5. Submit empty fields → expect inline helperText on First name, Last name, Password.
  6. Submit `abc` password → expect "Password must be at least 8 characters".
  7. Submit mismatched passwords → expect "Passwords do not match" on Confirm.
  8. Submit valid form → expect toast title "Joined!" with description "You're now a member of `<org_name>`."; expect URL `/home`; verify localStorage has `tone_access_token`.
  9. Verify the user is actually a member of the org by hitting a backend list-members API.
  10. Navigate back to `/accept-invite?token=<valid>` (consumed) → expect invalid card (backend rejects the consumed token).
  11. Click the legacy alias `?code=<another-valid-token>` (create a second invite first) → expect validation succeeds (alias works).
  12. Sign out, then visit `/accept-invite?token=<valid-for-existing-email>` (use the just-created user's email for a new org) → expect two-button card "Accept invitation" / "Sign in first".
  13. Click Accept → expect toast "Added to workspace" / "Please sign in to access `<org_name>`." → expect URL `/login`.
- **Cleanup (in `finally`)**: Delete the provisioned admin user, invitee user, both orgs, and any pending invitations via the backend admin API.
- **Naming**: `AI-FULL — accept-invite full lifecycle`.

---

## Expected Toast Messages

Toasts use Sonner via `showToast` (`src/lib/toast.ts`). Errors are routed
through `handleApiError(err)` which uses `response.data.detail` as the toast
title when it is a string; falls back to `"Something went wrong. Please try again."`.

Two of the success toasts include both a title **and** description (Sonner
renders the description as a smaller sub-line).

| Trigger                                                           | Toast title          | Toast description                                              | Variant |
| ----------------------------------------------------------------- | -------------------- | -------------------------------------------------------------- | ------- |
| Accept 200 with `access_token` (auto-login) and `invitation` set  | `Joined!`            | `You're now a member of {invitation.organization_name}.`       | success |
| Accept 200 with `access_token` and `invitation` missing           | `Joined!`            | `You joined the workspace.`                                    | success |
| Accept 200 without `access_token` (existing user) and `invitation` set | `Added to workspace` | `Please sign in to access {invitation.organization_name}.`     | success |
| Accept 200 without `access_token` and `invitation` missing        | `Added to workspace` | `Please sign in to continue.`                                  | success |
| Any 4xx/5xx with string `detail`                                  | backend `detail`     | —                                                              | error   |
| Any error with non-string `detail`                                | `Something went wrong. Please try again.` | —                                         | error   |

---

## UI Elements

| Element                          | Type               | Content / Label                                                                                          | Behavior                                                                                            |
| -------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Loading state                    | `AppLoader`        | label "Validating invitation..."                                                                         | Renders while `useValidateInvitation` is in flight                                                  |
| Invalid card (no token)          | `CustomCard`       | `XCircle` icon (h-12 w-12 text-destructive), title "Invalid invitation", description "No invitation token provided." | "Go to login" `Button` inside `<Link href="/login">`                              |
| Invalid card (validation error)  | `CustomCard`       | `XCircle` icon, title "Invalid invitation", description = `error.response.data.detail` or "This invitation is invalid or has expired." | "Go to login" `Button`                                                       |
| Signed-in accept card            | `CustomCard`       | `Building2` icon in primary/10 rounded wrapper, title "Join {organization_name}", description "You're signed in as {user.email}. Accept this invite to join as {role}." | Single `Button` "Accept invitation", loading prop bound to `acceptInvitation.isPending`              |
| Existing-account accept card     | `CustomCard`       | `LogIn` icon in primary/10 rounded wrapper, title "Join {organization_name}", description "{email} already has a Tone account. Accept to add it to {organization_name}, then sign in." | Two buttons: primary "Accept invitation" + outline "Sign in first" linking to `/login?next=...`     |
| New-user signup card             | `CustomCard`       | `CheckCircle` icon in primary/10 rounded wrapper, title "Join {organization_name}", description "You've been invited to join as a {role}. Create your account below." | Form with email (disabled), first_name + last_name in grid, password, confirm_password, submit button |
| Email field (form)               | `TextInput`        | label "Email", value `invitation.email`, no `control` prop, `disabled`                                   | Read-only — cannot be edited                                                                        |
| First name field                 | `TextInput`        | label "First name", `isRequired`                                                                         | Bound to RHF via `control`                                                                          |
| Last name field                  | `TextInput`        | label "Last name", `isRequired`                                                                          | Bound to RHF via `control`                                                                          |
| Password field                   | `TextInput`        | label "Password", `type="password"`, `isRequired`                                                        | Bound to RHF via `control`                                                                          |
| Confirm password field           | `TextInput`        | label "Confirm password", `type="password"`, `isRequired`                                                | Bound to RHF via `control`                                                                          |
| Create account & join button     | `Button`           | "Create account &amp; join", `type="submit"`, `className="w-full"`                                       | `loading={acceptInvitation.isPending}`                                                              |
| "Already have an account?" line  | text + `<Link>`    | "Already have an account?" + "Sign in" link to `/login?next=%2Faccept-invite%3Ftoken%3D...`              | Renders below the form                                                                              |
| Form wrapper                     | `Form`             | from `@/components/shared`                                                                               | Wraps native `<form onSubmit={handleSubmit(onSubmitNewUser)}>`                                       |

---

## Navigation

| Trigger                                                           | Destination                                                                       | Condition                                              |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Accept 200 with `access_token`                                    | `/home`                                                                           | Any acceptance path that returns tokens                |
| Accept 200 without `access_token` (existing-account anonymous)    | `/login`                                                                          | `requires_login: true`                                 |
| Click "Go to login" (invalid card, two variants)                  | `/login`                                                                          | Always                                                 |
| Click "Sign in first" (existing-account card)                     | `/login?next=%2Faccept-invite%3Ftoken%3D<token>`                                  | Only rendered when `account_exists` AND user signed out |
| Click "Sign in" (link beneath new-user form)                      | `/login?next=%2Faccept-invite%3Ftoken%3D<token>`                                  | Always rendered on new-user form                       |
| Visit `/accept-invite` with no token                              | stays on page (invalid card renders inline)                                       | No redirect                                            |
| Visit `/accept-invite?token=...`                                  | stays on page                                                                     | Validation drives which card renders                   |

---

## API Contracts

Real payloads sourced from
`/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json`
(folder: `Authentication → GET /auth/validate-invitation` and
`POST /auth/accept-invitation`).

| Endpoint                              | Method | Request                                                                                                          | Success Response                                                                                                                                                                          | Error Response                                                                |
| ------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- |
| `/api/v1/auth/validate-invitation`    | GET    | query: `?token=<raw-invite-token>`                                                                               | 200: `InvitationValidation` (see example)                                                                                                                                                  | 400: `{ "detail": "Invalid or expired invitation" }`                          |
| `/api/v1/auth/accept-invitation`      | POST   | `{ "token": "...", "password"?: "...", "first_name"?: "...", "last_name"?: "..." }` — password/name omitted for existing/signed-in users | 200: `AuthLoginResponse` (new user, auto-login) **or** `{ message, account_exists: true, email, requires_login: true }` (existing user)                                                  | 400: `{ "detail": "token is required" }`                                      |

### Example: `GET /auth/validate-invitation?token=raw-invite-token`

200 OK response body (new user):

```json
{
  "valid": true,
  "email": "invitee@acme.com",
  "role": "developer",
  "organization_id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
  "organization_name": "Acme",
  "account_exists": false
}
```

200 OK response body (existing user):

```json
{
  "valid": true,
  "email": "lin@acme.com",
  "role": "admin",
  "organization_id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
  "organization_name": "Acme",
  "account_exists": true
}
```

400 Bad Request:

```json
{ "detail": "Invalid or expired invitation" }
```

### Example: `POST /auth/accept-invitation` — new user

Request body:

```json
{
  "token": "raw-invite-token",
  "password": "setupPass789",
  "first_name": "Lin",
  "last_name": "Mo"
}
```

200 OK response body:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9.refresh.signature",
  "token_type": "bearer",
  "user": {
    "id": "8c7a8b50-9d0a-4d63-9b3c-1a2b3c4d5e6f",
    "email": "invitee@acme.com",
    "first_name": "Lin",
    "last_name": "Mo",
    "role": "developer",
    "is_verified": true
  },
  "organization": {
    "id": "f4d22a9c-1b6e-4f8c-9d2e-7e3b8a1f2c11",
    "name": "Acme"
  }
}
```

### Example: `POST /auth/accept-invitation` — existing user, requires login

Request body (no password / name fields):

```json
{ "token": "raw-invite-token" }
```

200 OK response body:

```json
{
  "message": "You have been added to the organization. Please sign in to continue.",
  "account_exists": true,
  "email": "invitee@acme.com",
  "requires_login": true
}
```

400 Bad Request:

```json
{ "detail": "token is required" }
```

Frontend logic for branching the response (in `handleAcceptResult`): the page
checks `result?.access_token`. If truthy, calls `setLoginResponse(result)` and
routes to `/home`. Otherwise routes to `/login`.

---

## Edge Cases

- [ ] Both `?token=` and `?code=` present in the URL → `token` wins (`searchParams.get('token') || searchParams.get('code')`)
- [ ] Token URL-encoded special chars (`+`, `=`, `/`) → `searchParams.get` returns
      decoded value; axios sends decoded body
- [ ] Very long token (e.g. 256+ chars) → not truncated client-side; backend may
      reject if its column has a max length
- [ ] Validation 4xx → invalid card; React Query has `retry: false` so no
      hammering the backend
- [ ] React Query post-accept refetch guard: `setAccepted(true)` flips
      `useValidateInvitation`'s `enabled` to false **before**
      `queryClient.invalidateQueries`, preventing a 400 refetch on a now-consumed token
- [ ] `invalidateQueries({ predicate: q => q.queryKey?.[0] !== 'invitation' })`
      refreshes `me`, `my-org`, etc. while leaving the consumed invitation query alone
- [ ] User refreshes the page after successful accept → `accepted` local state
      is reset; validation re-fires; backend returns 400 (consumed) → invalid card.
      Acceptable UX since the user is already redirected on first success
- [ ] User opens two tabs to the same invite link → first wins; second hits 400
      on accept → toast error
- [ ] Logged-in user with a DIFFERENT email than the invite → page still renders
      the signed-in one-click card; backend may 400 on accept ("email mismatch")
      → toast error. ⚠ unverified — confirm backend behaviour
- [ ] User opens link while connection is offline → validation throws; page
      enters the `error` branch with fallback description
- [ ] Password input fields render an Eye toggle (via `TextInput` shared
      component) — the toggle does not trigger form submit (`tabIndex={-1}`)
- [ ] Submit button is double-click safe: `acceptInvitation.isPending` disables
      it until the mutation settles
- [ ] Form leaves dirty state when user clicks "Sign in" link → RHF state is
      discarded on unmount; no confirm-leave guard

---

## Business Rules

- Invitation tokens are single-use. Accepting consumes the token server-side;
  subsequent validation returns 400.
- Tokens are time-limited (backend-controlled TTL; backend returns
  `"Invalid or expired invitation"` for both invalid and expired states — the
  page does not distinguish).
- Anonymous accept (signed-out user with `account_exists: true`) does **not**
  return tokens — the user must sign in to start a session for the new org.
- New-user accept returns tokens and the user is logged in immediately.
- The page is part of the `(auth)` route group with no `tone_access_token`
  requirement; this is deliberate so invite links work for both signed-in and
  signed-out users.
- The email is **fixed** by the invitation: the form pre-fills and locks the
  email field, so the user cannot change which email the account is created for.
- The role is **fixed** by the invitation (set when the invite was sent from
  the Members page); the user has no choice over their role in the new org.
- `?code=` is an alias for `?token=` — older invite emails used `?code=`; both
  must work indefinitely so legacy emails do not break.

---

## Accessibility Requirements

- [ ] `AppLoader` exposes `role="status"` and an `aria-label` (or `label` prop)
- [ ] `CustomCard` exposes `<CardTitle>` (semantic heading) and a description
      paragraph for the title + summary
- [ ] All `Button`s are real `<button>` elements; keyboard tab navigation reaches
      Accept / Cancel / Sign in / Go to login
- [ ] Email field is `disabled` — SR users hear "edit text, dimmed" which
      conveys read-only state
- [ ] Form errors render as `helperText` under each input via RHF
      `fieldState.error.message` — `TextInput` does not duplicate error rendering
- [ ] The Sonner toast surface is an `aria-live="polite"` region; SR users hear
      the success/error message after Accept resolves
- [ ] Color is not the only differentiator: invalid card uses red XCircle + title
      "Invalid invitation"; valid cards use green CheckCircle / Building2 / LogIn
      with descriptive titles
- [ ] Headings are `<CardTitle>` (rendered as `<h3>` by shadcn's `CardTitle`).
      ⚠ consider a page-level `<h1>` for SR users
- [ ] Focus management: after the validation resolves and the card swaps in,
      focus stays on `<body>`; consider moving focus to the card's primary action
      so keyboard users don't need to tab from the top. ⚠ unverified — confirm
      whether `CustomCard` has any focus management
