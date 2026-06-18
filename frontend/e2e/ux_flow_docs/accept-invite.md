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

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: New user signs up via invite and lands on /home

**Preconditions**:
- Signed-out browser (no `tone_access_token` in localStorage)
- Valid token for a new email `invitee@acme.com`

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Fill `Lin` into First name and `Mo` into Last name
3. Fill `setupPass789` into Password and Confirm password
4. Click "Create account & join"

**Observation 1 — Validation network request**:
1. Exactly one `GET /auth/validate-invitation?token=raw-invite-token` request is recorded

**Observation 2 — Loading state before validation resolves**:
1. `<AppLoader label="Validating invitation..." />` is visible while pending

**Observation 3 — New-user signup card renders**:
1. `CustomCard` with `CheckCircle` icon is visible
2. Title equals `Join Acme`
3. Description equals `You've been invited to join as a developer. Create your account below.`
4. Email field is pre-filled with `invitee@acme.com` and is `disabled`

**Observation 4 — Accept network request**:
1. Exactly one `POST /auth/accept-invitation` request is recorded
2. Request body equals `{ "token": "raw-invite-token", "password": "setupPass789", "first_name": "Lin", "last_name": "Mo" }`

**Observation 5 — Local storage hydration**:
1. `localStorage.tone_access_token` equals the response `access_token`
2. `localStorage.login_data` is valid JSON containing the response `user.id`

**Observation 6 — React Query guard**:
1. `accepted` state flips to `true` BEFORE `cancelQueries` / `invalidateQueries`
2. `queryClient.cancelQueries` is called for `['invitation', token]`
3. `invalidateQueries` is called with a predicate excluding the `invitation` key (so `me` / `my-org` refetch)

**Observation 7 — Toast + redirect**:
1. Toast title equals `Joined!`
2. Toast description equals `You're now a member of Acme.`
3. URL becomes `/home` within 1s

**API mocks**:
- `GET /auth/validate-invitation?token=raw-invite-token` → 200 (new-user payload)
- `POST /auth/accept-invitation` → 200 (auto-login payload)

**Cleanup**: Clear localStorage and cookies in the `afterEach` hook.

---

### TC-HAPPY-002: Existing-account anonymous accept lands on /login

**Preconditions**:
- Signed-out browser
- Invite token for an email that already has a Tone account

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Click "Accept invitation"

**Observation 1 — Two-button card renders**:
1. `CustomCard` with `LogIn` icon is visible
2. Title equals `Join Acme`
3. Description equals `lin@acme.com already has a Tone account. Accept to add it to Acme, then sign in.`
4. Both buttons are visible: primary "Accept invitation" and outline "Sign in first"

**Observation 2 — Network request on Accept**:
1. Exactly one `POST /auth/accept-invitation` request is recorded
2. Request body equals `{ "token": "raw-invite-token" }` (no password / name fields)

**Observation 3 — Toast + redirect**:
1. Toast title equals `Added to workspace`
2. Toast description equals `Please sign in to access Acme.`
3. URL becomes `/login` within 1s

**API mocks**:
- `GET /auth/validate-invitation` → 200 (existing-user payload)
- `POST /auth/accept-invitation` → 200 `{ "message": "...", "account_exists": true, "email": "invitee@acme.com", "requires_login": true }`

---

### TC-HAPPY-003: Signed-in user one-click accepts and lands on /home

**Preconditions**:
- `useAuthStore().user` is truthy (localStorage has valid `login_data` for `current@example.com`)
- Valid token

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Click "Accept invitation"

**Observation 1 — Signed-in one-click card renders**:
1. `CustomCard` with `Building2` icon is visible
2. Title equals `Join Acme`
3. Description equals `You're signed in as current@example.com. Accept this invite to join as developer.`
4. A single primary "Accept invitation" button is rendered (no "Sign in first")

**Observation 2 — Network request**:
1. Exactly one `POST /auth/accept-invitation` request is recorded
2. Request body equals `{ "token": "raw-invite-token" }`

**Observation 3 — Toast + redirect**:
1. Toast title equals `Joined!`
2. Toast description equals `You're now a member of Acme.`
3. URL becomes `/home` within 1s

**API mocks**:
- `GET /auth/validate-invitation` → 200 (new-user payload or existing — page only cares about validity)
- `POST /auth/accept-invitation` → 200 with `access_token`

---

### TC-HAPPY-004: Legacy `?code=` alias works identically

**Preconditions**:
- Signed-out browser
- Old email with `?code=` alias

**Action**:
1. Visit `/accept-invite?code=raw-invite-token`
2. Fill the new-user form and submit

**Observation 1 — Validation uses code value as token**:
1. `GET /auth/validate-invitation?token=raw-invite-token` is recorded (page extracts `code` and uses it as `token`)

**Observation 2 — Rest of flow matches TC-HAPPY-001**:
1. Success card renders; Accept fires; toast `Joined!`; redirect to `/home`

**API mocks**: identical to TC-HAPPY-001, just the URL query name differs.

---

### TC-HAPPY-005: Email field is locked

**Preconditions**:
- TC-HAPPY-001 prereqs; new-user signup card rendered

**Action**:
1. Inspect the Email `TextInput`
2. Attempt to type into the Email field

**Observation 1 — Email value pre-filled**:
1. Email input value equals `invitee@acme.com`

**Observation 2 — HTML disabled attribute set**:
1. The Email `<input>` has the `disabled` attribute present

**Observation 3 — Typing has no effect**:
1. Attempting to type does not change the input value

---

### TC-HAPPY-006: Token precedence — `?token` wins over `?code`

**Preconditions**:
- URL contains both `?token=primary` and `?code=secondary`

**Action**:
1. Visit `/accept-invite?token=primary&code=secondary`

**Observation 1 — Token wins**:
1. `GET /auth/validate-invitation?token=primary` is recorded (NOT `secondary`)

**API mock**: `GET /auth/validate-invitation?token=primary` → 200.

---

### TC-NAV-001: Click "Go to login" from invalid card navigates to /login

**Preconditions**:
- Invalid card rendered (e.g. via TC-VALIDATE-001)

**Action**:
1. Click the "Go to login" button

**Observation 1 — URL change**:
1. URL becomes `/login`

---

### TC-NAV-002: Click "Sign in first" links to /login with encoded next

**Preconditions**:
- TC-HAPPY-002 prereqs; existing-account two-button card rendered

**Action**:
1. Click "Sign in first"

**Observation 1 — URL change with encoded next**:
1. URL becomes `/login?next=%2Faccept-invite%3Ftoken%3Draw-invite-token`

**Observation 2 — After-login flow lands back on invite**:
1. Following login redirects user back to `/accept-invite?token=raw-invite-token` (via login's `next` handler)
2. The signed-in one-click card now renders (US-3 path)

---

### TC-NAV-003: Click "Sign in" beneath the new-user form navigates with next

**Preconditions**:
- TC-HAPPY-001 prereqs; new-user signup card rendered

**Action**:
1. Click the "Sign in" link below the form

**Observation 1 — URL change with encoded next**:
1. URL becomes `/login?next=%2Faccept-invite%3Ftoken%3Draw-invite-token`

**Observation 2 — RHF state discarded on unmount**:
1. No confirm-leave guard fires (form state is dropped silently)

---

### TC-VALIDATE-001: Missing both `?token` and `?code` shows invalid card with no API call

**Action**:
1. Visit `/accept-invite`

**Observation 1 — No network call**:
1. Zero `GET /auth/validate-invitation` requests are recorded
2. `enabled: !!token && !accepted` is false (`token === ''`)

**Observation 2 — Invalid card rendered**:
1. `XCircle` icon is visible
2. Title equals `Invalid invitation`
3. Description equals `No invitation token provided.`
4. A "Go to login" `<Button>` is rendered inside a `<Link href="/login">`

---

### TC-VALIDATE-002: Empty `?token=` shows the same invalid card

**Action**:
1. Visit `/accept-invite?token=`

**Observation 1 — No API call**:
1. Zero `GET /auth/validate-invitation` requests are recorded

**Observation 2 — Same invalid card**:
1. `XCircle`, `Invalid invitation`, `No invitation token provided.`, "Go to login" button

---

### TC-VALIDATE-003: Empty first name blocks submit

**Preconditions**:
- TC-HAPPY-001 prereqs; new-user form rendered

**Action**:
1. Leave First name blank; fill the remaining fields validly
2. Click "Create account & join"

**Observation 1 — No network call**:
1. Zero `POST /auth/accept-invitation` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under First name reads exactly `First name is required`

---

### TC-VALIDATE-004: Empty last name blocks submit

**Preconditions**:
- New-user form rendered

**Action**:
1. Leave Last name blank; fill the remaining fields validly
2. Click "Create account & join"

**Observation 1 — No network call**:
1. Zero `POST /auth/accept-invitation` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Last name reads exactly `Last name is required`

---

### TC-VALIDATE-005: Short password (<8 chars) blocks submit

**Preconditions**:
- New-user form rendered

**Action**:
1. Type `abc` (3 chars) into Password and Confirm password
2. Click "Create account & join"

**Observation 1 — No network call**:
1. Zero `POST /auth/accept-invitation` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Password reads exactly `Password must be at least 8 characters`

---

### TC-VALIDATE-006: Passwords mismatch blocks submit

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill Password with `abcd1234`
2. Fill Confirm password with `abcd9999`
3. Click "Create account & join"

**Observation 1 — No network call**:
1. Zero `POST /auth/accept-invitation` requests are recorded

**Observation 2 — Inline error on Confirm**:
1. Helper text under Confirm password reads exactly `Passwords do not match`
2. The error appears on the `confirm_password` field (Zod path refinement)

---

### TC-VALIDATE-007: Empty confirm password blocks submit

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill Password validly
2. Leave Confirm password blank
3. Click "Create account & join"

**Observation 1 — No network call**:
1. Zero `POST /auth/accept-invitation` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Confirm password reads exactly `Please confirm your password`

---

### TC-ERROR-001: Validation 400 invalid/expired token shows backend `detail`

**Action**:
1. Visit `/accept-invite?token=expired-xyz`

**Observation 1 — Network call**:
1. Exactly one `GET /auth/validate-invitation?token=expired-xyz` request is recorded

**Observation 2 — Invalid card with backend detail**:
1. `XCircle` icon visible
2. Title equals `Invalid invitation`
3. Description equals `Invalid or expired invitation` (from `error.response.data.detail`)
4. "Go to login" button rendered

**API mock**: `GET /auth/validate-invitation` → 400 `{ "detail": "Invalid or expired invitation" }`.

---

### TC-ERROR-002: Validation 200 with `valid: false` shows fallback description

**Action**:
1. Visit `/accept-invite?token=any`

**Observation 1 — Page enters !invitation?.valid branch**:
1. Invalid card renders
2. Description equals `This invitation is invalid or has expired.` (fallback)

**API mock**: `GET /auth/validate-invitation` → 200 `{ "valid": false, "email": "", "role": "", "organization_id": "", "organization_name": "", "account_exists": false }`.

---

### TC-ERROR-003: Validation 5xx with missing `detail` falls back

**Action**:
1. Visit `/accept-invite?token=any`

**Observation 1 — Invalid card with fallback description**:
1. Description equals `This invitation is invalid or has expired.` (because `detail` is missing)

**API mock**: `GET /auth/validate-invitation` → 500 `{}`.

---

### TC-ERROR-004: Accept 400 "token is required" surfaces toast

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill the form validly
2. Click "Create account & join"

**Observation 1 — Error toast via handleApiError**:
1. Toast title equals `token is required`

**Observation 2 — Card stays in form mode**:
1. New-user form is still visible
2. The submit button re-enables

**API mock**: `POST /auth/accept-invitation` → 400 `{ "detail": "token is required" }`.

---

### TC-ERROR-005: Accept 400 "Invitation already accepted" surfaces toast

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill the form validly
2. Click "Create account & join"

**Observation 1 — Error toast**:
1. Toast title equals `Invitation already accepted`

**Observation 2 — Card stays; submit re-enables**:
1. New-user form is still visible

> ⚠ unverified — actual backend message may differ; this is the most likely shape.

**API mock**: `POST /auth/accept-invitation` → 400 `{ "detail": "Invitation already accepted" }`.

---

### TC-ERROR-006: Accept 401 "Could not validate credentials" surfaces toast

**Preconditions**:
- Existing-account two-button card rendered

**Action**:
1. Click "Accept invitation"

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Card stays visible**:
1. Two-button card is still in the DOM

**API mock**: `POST /auth/accept-invitation` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-007: Accept 5xx surfaces verbatim string

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill the form validly and submit

**Observation 1 — Error toast**:
1. Toast title equals `Internal Server Error`

**Observation 2 — Card stays; submit re-enables**:
1. Form still visible; button re-enabled

**API mock**: `POST /auth/accept-invitation` → 500 `{ "detail": "Internal Server Error" }`.

---

### TC-ERROR-008: Accept 422 with array `detail` falls back to generic toast

**Preconditions**:
- New-user form rendered

**Action**:
1. Submit a valid form

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.`

**API mock**: `POST /auth/accept-invitation` → 422 `{ "detail": [{ "type": "value_error", "loc": ["body", "password"], "msg": "String should have at least 8 characters", "input": "abc" }] }`.

---

### TC-ERROR-009: Accept 409 "already a member" surfaces toast

**Preconditions**:
- Signed-in or existing-account card rendered

**Action**:
1. Click "Accept invitation"

**Observation 1 — Error toast**:
1. Toast title equals `User is already a member of this organization`

**Observation 2 — Card stays; submit re-enables**:
1. Card still visible

**API mock**: `POST /auth/accept-invitation` → 409 `{ "detail": "User is already a member of this organization" }`.

---

### TC-ERROR-010: Network failure on validate shows fallback invalid card

**Action**:
1. Visit `/accept-invite?token=any` with the validate route aborted

**Observation 1 — Invalid card with fallback description**:
1. Description equals `This invitation is invalid or has expired.`

**Observation 2 — React Query retry disabled**:
1. Only one validation attempt is recorded (no retry — `retry: false`)

**API mock**: `GET /auth/validate-invitation` route aborted.

---

### TC-ERROR-011: Network failure on accept preserves form data

**Preconditions**:
- New-user form rendered; all four fields filled

**Action**:
1. Click "Create account & join" with the accept route aborted

**Observation 1 — Generic toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form values preserved**:
1. First name, Last name, Password, Confirm password still contain typed values

**Observation 3 — Button re-enables**:
1. The "Create account & join" button is no longer disabled and no longer shows the spinner

**API mock**: `POST /auth/accept-invitation` route aborted.

---

### TC-LOADING-001: Slow validate API keeps AppLoader visible

**Action**:
1. Visit `/accept-invite?token=any` with the validate response delayed ~3500 ms

**Observation 1 — AppLoader visible throughout**:
1. `<AppLoader label="Validating invitation..." />` is visible for the full 3500 ms

**Observation 2 — Card mounts only after resolution**:
1. The appropriate card (new-user / existing-account / signed-in) renders only after the response

**API mock**: `GET /auth/validate-invitation` → 200 delayed by 3500 ms.

---

### TC-LOADING-002: Slow accept API keeps button in loading state

**Preconditions**:
- New-user form rendered

**Action**:
1. Fill the form validly
2. Click "Create account & join" with the accept response delayed ~3500 ms

**Observation 1 — Button disabled with spinner**:
1. "Create account & join" shows the spinner and is `disabled` for the full duration

**Observation 2 — Double-click is a no-op**:
1. Clicking again produces zero additional `POST /auth/accept-invitation` requests

**Observation 3 — Toast + redirect only after resolution**:
1. Toast `Joined!` appears only after the response resolves
2. URL becomes `/home` only after the response resolves

**API mock**: `POST /auth/accept-invitation` → 200 delayed by 3500 ms.

---

### TC-EDGE-001: User edits localStorage to fake login during invite flow

**Preconditions**:
- Valid `?token=...` URL
- localStorage pre-seeded with garbage `login_data`

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Click "Accept invitation" on the signed-in one-click card

**Observation 1 — Page renders signed-in card with fake email**:
1. Title `Join Acme` with description showing the fake user's email

**Observation 2 — Backend rejects on Accept**:
1. Toast surfaces backend `detail` (e.g. `Could not validate credentials`)

**API mocks**:
- `GET /auth/validate-invitation` → 200
- `POST /auth/accept-invitation` → 401

---

### TC-EDGE-002: Tab closed mid-accept

**Preconditions**:
- TC-HAPPY-001 step 4 in flight (mutation pending)

**Action**:
1. Close the tab before response resolves

**Observation 1 — No client-side abort**:
1. No `AbortController` is wired into the mutation; the backend may still process
2. No client-visible behaviour to assert (browser-level)

---

### TC-EDGE-003: Token with URL-encoded special chars (`+`, `=`, `/`)

**Preconditions**:
- URL is `/accept-invite?token=abc%2Bdef%3D%3D` (encodes `+` and `==`)

**Action**:
1. Visit the encoded URL

**Observation 1 — Validate request uses decoded value**:
1. `GET /auth/validate-invitation?token=abc+def==` is recorded

**Observation 2 — Card renders normally**:
1. Whatever card the validation result implies renders (e.g. new-user form)

**API mock**: `GET /auth/validate-invitation` → 200 (new-user payload).

---

### TC-EDGE-004: Very long token (>256 chars)

**Action**:
1. Visit `/accept-invite?token=<256-char-string>`

**Observation 1 — No client-side truncation**:
1. `GET /auth/validate-invitation?token=<full-string>` is recorded with the full token

**Observation 2 — Backend may reject**:
1. If backend has a max-length column, validation 400 → invalid card; otherwise normal flow

---

### TC-EDGE-005: First name with XSS is sent verbatim and rendered safely

**Preconditions**:
- New-user form rendered

**Action**:
1. Type `<script>alert(1)</script>` into First name
2. Fill remaining fields validly
3. Click "Create account & join"

**Observation 1 — Payload sends the literal string**:
1. `POST /auth/accept-invitation` body has `first_name` exactly `<script>alert(1)</script>`

**Observation 2 — DOM is safe**:
1. React escapes the value wherever rendered
2. `window.alert` was not invoked

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-EDGE-006: First / last name with emoji

**Preconditions**:
- New-user form rendered

**Action**:
1. Type `Lin 🎉` into First name and `Mo 💎` into Last name
2. Fill remaining fields validly and submit

**Observation 1 — Payload includes emoji verbatim**:
1. `POST /auth/accept-invitation` body has `first_name: "Lin 🎉"` and `last_name: "Mo 💎"`

**Observation 2 — Success path runs normally**:
1. Toast `Joined!`, URL `/home`

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-EDGE-007: Very long first name (>500 chars)

**Preconditions**:
- New-user form rendered

**Action**:
1. Paste a 600-char string into First name
2. Fill remaining fields validly and submit

**Observation 1 — Input accepts the full value**:
1. First name input value length equals 600 (no client-side maxLength)

**Observation 2 — Backend may reject**:
1. If backend has a max length, surface its `detail` in a toast

---

### TC-EDGE-008: Paste with newlines into single-line input

**Preconditions**:
- New-user form rendered

**Action**:
1. Paste `Lin\nMo` into First name

**Observation 1 — Single-line input strips newline**:
1. First name input value is `LinMo` (the browser strips newlines at paste time)

---

### TC-EDGE-009: Whitespace-only First name passes Zod min(1)

**Preconditions**:
- New-user form rendered

**Action**:
1. Type `   ` (3 spaces) into First name
2. Fill remaining fields and submit

**Observation 1 — Zod passes**:
1. `POST /auth/accept-invitation` is recorded; body `first_name` is `"   "`

> ⚠ Today Zod `min(1)` passes; payload is sent. Document the gap.

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-EDGE-010: Trailing whitespace in password is preserved (no trim)

**Preconditions**:
- New-user form rendered

**Action**:
1. Type `validPass1   ` (3 trailing spaces) in both Password and Confirm password
2. Submit

**Observation 1 — Payload sends verbatim**:
1. `POST /auth/accept-invitation` body `password` equals `"validPass1   "` (no trim)

**Observation 2 — Subsequent login must use the same value**:
1. Documented: the user must reuse the literal value (including whitespace) for future logins

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-EDGE-011: Authenticated visit with mismatched email

**Preconditions**:
- localStorage `login_data` is for `other@example.com`
- Invite is for `invitee@acme.com`

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Click "Accept invitation"

**Observation 1 — Signed-in one-click card renders with current email**:
1. Description reads `You're signed in as other@example.com. Accept this invite to join as developer.`

**Observation 2 — Accept result varies**:
1. Backend may succeed or 400 depending on email-mismatch policy
2. If 400, toast surfaces the `detail`

> Document the observed outcome.

---

### TC-EDGE-012: Post-accept refetch guard — no refetch after accepted

**Preconditions**:
- TC-HAPPY-001 just succeeded; `accepted` state is `true`

**Action**:
1. Inspect the React Query call log immediately after the mutation resolves

**Observation 1 — `useValidateInvitation` is disabled**:
1. `enabled = !!token && !accepted = false`
2. No new `GET /auth/validate-invitation` request fires

**Observation 2 — `cancelQueries` aborts pending validation**:
1. Any in-flight validation is cancelled
2. `invalidateQueries` for non-invitation keys (predicate `q.queryKey?.[0] !== 'invitation'`) refreshes `me`, `my-org`

---

### TC-EDGE-013: Refresh after successful accept shows invalid card

**Preconditions**:
- TC-HAPPY-001 succeeded; `accepted` state was set in-memory only

**Action**:
1. Reload the page (URL still `/accept-invite?token=raw-invite-token`)

**Observation 1 — `accepted` resets**:
1. The in-memory `accepted = true` does NOT persist across navigations

**Observation 2 — Backend rejects consumed token**:
1. `GET /auth/validate-invitation` returns 400 → invalid card with backend `detail`

> Acceptable UX since the user is already redirected on first success.

**API mock**: `GET /auth/validate-invitation` → 400 `{ "detail": "Invalid or expired invitation" }`.

---

### TC-EDGE-014: Two tabs to the same invite link

**Preconditions**:
- Tab A and Tab B both opened to `/accept-invite?token=raw-invite-token`
- Tab A submits Accept first

**Action**:
1. Submit Accept in Tab B after Tab A's mutation resolves

**Observation 1 — Tab A succeeds**:
1. Tab A receives 200; toast `Joined!`; URL `/home`

**Observation 2 — Tab B fails**:
1. Tab B receives 400 on accept (consumed token); toast with backend `detail`

**API mocks**:
- Tab A: `POST /auth/accept-invitation` → 200
- Tab B: `POST /auth/accept-invitation` → 400

---

### TC-EDGE-015: Offline / connection-down on validate

**Action**:
1. Visit `/accept-invite?token=raw-invite-token` while offline

**Observation 1 — Page enters error branch**:
1. Invalid card renders with fallback description `This invitation is invalid or has expired.`

**API mock**: `GET /auth/validate-invitation` aborted.

---

### TC-EDGE-016: Password input Eye toggle does not submit the form

**Preconditions**:
- New-user form rendered

**Action**:
1. Click the Eye icon inside the Password field

**Observation 1 — Form not submitted**:
1. Zero `POST /auth/accept-invitation` requests are recorded
2. The Eye toggle has `tabIndex={-1}` and does not act as a submit trigger

**Observation 2 — Password visibility toggles**:
1. The Password input's `type` switches between `password` and `text`

---

### TC-EDGE-017: Submit button is double-click safe

**Preconditions**:
- New-user form rendered; all fields filled

**Action**:
1. Click "Create account & join" twice in rapid succession (≤100 ms apart)

**Observation 1 — Single network request**:
1. Exactly one `POST /auth/accept-invitation` request is recorded

**Observation 2 — Button enters loading state**:
1. The button shows the spinner on first click
2. Second click is a no-op (`acceptInvitation.isPending` disables it)

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-EDGE-018: Form leaves dirty state without confirm-leave guard

**Preconditions**:
- New-user form rendered with partial input

**Action**:
1. Click the "Sign in" link beneath the form

**Observation 1 — Navigation succeeds without confirmation**:
1. URL becomes `/login?next=...`
2. No confirm-leave dialog appears
3. RHF state is discarded on unmount

---

### TC-EDGE-019: `?token=` with whitespace fails validation

**Preconditions**:
- URL is `/accept-invite?token=%20valid%20`

**Action**:
1. Visit the URL

**Observation 1 — Validate with verbatim value**:
1. `GET /auth/validate-invitation?token= valid ` is recorded (`searchParams.get` returns the value verbatim)

**Observation 2 — Invalid card**:
1. Backend 400 → invalid card renders

**API mock**: `GET /auth/validate-invitation` → 400.

---

### TC-EDGE-020: Submit via Enter key in Confirm password

**Preconditions**:
- New-user form rendered; all four fields filled validly

**Action**:
1. Focus Confirm password
2. Press the `Enter` key

**Observation 1 — Form submits**:
1. Exactly one `POST /auth/accept-invitation` request is recorded
2. Request body matches the typed values

**API mock**: `POST /auth/accept-invitation` → 200.

---

### TC-NAV-004: Browser back from /home after accept

**Preconditions**:
- TC-HAPPY-001 succeeded; user is on `/home`

**Action**:
1. Press the browser Back button

**Observation 1 — URL returns to /accept-invite**:
1. URL becomes `/accept-invite?token=raw-invite-token`

**Observation 2 — Re-validation rejects consumed token**:
1. `GET /auth/validate-invitation` fires and returns 400
2. Invalid card renders

> Acceptable UX.

**API mock** (on re-mount): `GET /auth/validate-invitation` → 400 `{ "detail": "Invalid or expired invitation" }`.

---

### TC-A11Y-001: AppLoader exposes role=status with label

**Action**:
1. Visit `/accept-invite?token=any` with a slow validate response
2. Inspect the loader DOM node

**Observation 1 — Loading announced**:
1. The `AppLoader` root has `role="status"`
2. The loader exposes `aria-label="Loading"` (or the `label` prop value `Validating invitation...`)

---

### TC-A11Y-002: CustomCard exposes CardTitle and description for SR

**Action**:
1. Trigger any of the cards (new-user / existing-account / signed-in / invalid)
2. Inspect the DOM hierarchy

**Observation 1 — Semantic title element**:
1. `<CardTitle>` (rendered as `<h3>` by shadcn) is present with the card title text

**Observation 2 — Description paragraph**:
1. A `<p>` (or equivalent) element renders the card description

---

### TC-A11Y-003: All buttons are real `<button>` and keyboard reachable

**Action**:
1. Render any card variant
2. Tab through the page

**Observation 1 — Real button elements**:
1. Accept / Cancel / Sign in / Go to login are all real `<button>` elements

**Observation 2 — Tab reaches every actionable element**:
1. Tab order reaches every button + link visible on the card

---

### TC-A11Y-004: Email field disabled state announced

**Preconditions**:
- New-user form rendered

**Action**:
1. Inspect the Email `<input>`

**Observation 1 — disabled attribute set**:
1. The Email `<input>` has `disabled` (SR users hear "edit text, dimmed")

---

### TC-A11Y-005: Helper-text errors render via RHF and announce via aria-live

**Preconditions**:
- New-user form rendered

**Action**:
1. Click "Create account & join" with mismatched passwords

**Observation 1 — Inline error renders**:
1. Helper text under Confirm password is `Passwords do not match`

**Observation 2 — aria-live region**:
1. The helper text is rendered inside an element with `role="alert"` (or `aria-live="polite"`)

---

### TC-A11Y-006: Toast surface is an aria-live region

**Action**:
1. Trigger any toast (e.g. accept success or error)
2. Inspect the Sonner toast container

**Observation 1 — Live region attributes**:
1. Sonner's toast container has `aria-live="polite"` (or `assertive`)
2. SR users hear the success / error message after Accept resolves

---

### TC-A11Y-007: Color is not the only differentiator between card variants

**Action**:
1. Render each card variant
2. Inspect the icon + title text combinations

**Observation 1 — Icon + title pairs**:
1. Invalid card uses red `XCircle` + title `Invalid invitation`
2. New-user card uses green `CheckCircle` + title `Join {organization_name}`
3. Signed-in card uses `Building2` + title `Join {organization_name}`
4. Existing-account card uses `LogIn` + title `Join {organization_name}`

---

### TC-A11Y-008: Missing page-level h1 — heading hierarchy gap

**Action**:
1. Inspect the rendered page for headings

**Observation 1 — Only CardTitle (h3) is present**:
1. Headings are `<CardTitle>` rendered as `<h3>` by shadcn
2. No page-level `<h1>` exists

> ⚠ Consider a page-level `<h1>` for SR users.

---

### TC-A11Y-009: Focus management after validation resolves

**Action**:
1. Visit `/accept-invite?token=raw-invite-token`
2. Wait for validation to resolve and a card to render
3. Inspect `document.activeElement`

**Observation 1 — Focus stays on body**:
1. `document.activeElement` is `<body>` after the card swaps in (no auto-focus on primary action)

> ⚠ Consider moving focus to the card's primary action so keyboard users don't tab from the top. ⚠ unverified — confirm whether `CustomCard` has any focus management.

---

### TC-A11Y-010: Tab order through the new-user form

**Preconditions**:
- New-user form rendered

**Action**:
1. Focus the page and press Tab repeatedly

**Observation 1 — Tab order matches design**:
1. Focus moves Email (disabled, skipped or focusable but inert) → First name → Last name → Password → password Eye toggle → Confirm password → Confirm password Eye toggle → "Create account & join" → "Sign in" link
2. No focusable element is reached twice

---

### TC-FULL-001: End-to-end accept-invite lifecycle

**Preconditions**:
- An admin user `__e2e__ai_admin_<uuid>@example.com` with an organization is provisioned via the backend API
- An invite for a new email `__e2e__ai_invitee_<uuid>@example.com` is created via the backend Members API; the raw invitation token is captured (or via a test-only admin endpoint)

**Action**:
1. Visit `/accept-invite` (no token)
2. Click "Go to login"
3. Navigate to `/accept-invite?token=clearly-bad-token`
4. Navigate to `/accept-invite?token=<valid>` (new-user variant)
5. Submit empty fields
6. Submit with `abc` password
7. Submit with mismatched passwords
8. Submit the valid form
9. Verify the user is a member of the org by hitting a backend list-members API
10. Navigate back to `/accept-invite?token=<valid>` (consumed)
11. Click the legacy alias `?code=<another-valid-token>` (create a second invite first)
12. Sign out, then visit `/accept-invite?token=<valid-for-existing-email>`
13. Click "Accept invitation"

**Observation 1 — Step 1 shows invalid card**:
1. Invalid card `Invalid invitation` / `No invitation token provided.` with a "Go to login" button
2. Zero `GET /auth/validate-invitation` requests recorded

**Observation 2 — Step 2 navigates to /login**:
1. URL becomes `/login`

**Observation 3 — Step 3 shows invalid card with backend detail**:
1. AppLoader briefly visible
2. Invalid card with backend `detail`

**Observation 4 — Step 4 shows new-user signup card**:
1. New-user form with email locked to invitee email

**Observation 5 — Step 5 yields three inline errors**:
1. Helper text under First name, Last name, Password all visible

**Observation 6 — Step 6 yields short-password error**:
1. Helper text `Password must be at least 8 characters` visible

**Observation 7 — Step 7 yields mismatch error**:
1. Helper text `Passwords do not match` on Confirm password

**Observation 8 — Step 8 succeeds and lands on /home**:
1. Toast title `Joined!`, description `You're now a member of <org_name>.`
2. URL becomes `/home`
3. `localStorage.tone_access_token` is set

**Observation 9 — Step 9 confirms backend membership**:
1. The list-members API confirms the user is now a member of the org

**Observation 10 — Step 10 shows invalid card on consumed token**:
1. Invalid card renders (backend rejects the consumed token)

**Observation 11 — Step 11 legacy `?code=` alias works**:
1. Validation succeeds; appropriate card renders

**Observation 12 — Step 12 shows two-button card**:
1. Existing-account card `Accept invitation` / `Sign in first` rendered

**Observation 13 — Step 13 lands on /login**:
1. Toast title `Added to workspace`, description `Please sign in to access <org_name>.`
2. URL becomes `/login`

**Cleanup** (in `finally`):
1. Delete the provisioned admin user, invitee user, both orgs, and any pending invitations via the backend admin API

---

## Edge Cases (each appears as a `TC-EDGE-*` or related test case above)

- [x] Both `?token=` and `?code=` present in URL — see TC-HAPPY-006
- [x] Token URL-encoded special chars — see TC-EDGE-003
- [x] Very long token (>256 chars) — see TC-EDGE-004
- [x] Validation 4xx → invalid card, no retry — see TC-ERROR-001 / TC-ERROR-010
- [x] React Query post-accept refetch guard — see TC-EDGE-012
- [x] `invalidateQueries` predicate skips invitation key — see TC-EDGE-012
- [x] Refresh after success → re-validation rejects — see TC-EDGE-013
- [x] Two tabs to the same invite link — see TC-EDGE-014
- [x] Logged-in user with a different email — see TC-EDGE-011
- [x] Offline connection on validate — see TC-EDGE-015
- [x] Password Eye toggle does not submit (`tabIndex={-1}`) — see TC-EDGE-016
- [x] Submit button is double-click safe — see TC-EDGE-017
- [x] Form leaves dirty state with no confirm-leave guard — see TC-EDGE-018
- [x] Whitespace `?token=` — see TC-EDGE-019
- [x] Submit via Enter — see TC-EDGE-020
- [x] XSS in first name — see TC-EDGE-005
- [x] Emoji in name fields — see TC-EDGE-006
- [x] Very long name (>500 chars) — see TC-EDGE-007
- [x] Paste with newlines into single-line input — see TC-EDGE-008
- [x] Whitespace-only first name — see TC-EDGE-009
- [x] Trailing whitespace in password preserved — see TC-EDGE-010

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

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] `AppLoader` exposes `role="status"` and label — see TC-A11Y-001
- [x] `CustomCard` exposes `CardTitle` (h3) + description — see TC-A11Y-002
- [x] All buttons real `<button>` and keyboard reachable — see TC-A11Y-003
- [x] Email field `disabled` is announced — see TC-A11Y-004
- [x] Form errors render via RHF `fieldState.error.message` with aria-live — see TC-A11Y-005
- [x] Sonner toast surface is `aria-live="polite"` — see TC-A11Y-006
- [x] Color is not the only differentiator — see TC-A11Y-007
- [x] No page-level `<h1>` (gap) — see TC-A11Y-008
- [x] No focus management after card swap (gap) — see TC-A11Y-009
- [x] Tab order through new-user form — see TC-A11Y-010

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
