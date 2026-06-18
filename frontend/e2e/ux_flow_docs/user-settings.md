# Feature Doc: User Settings (Profile)

Feature documentation for the per-user profile page. Used by
`/generate-tests user-settings` (or `--docs e2e/ux_flow_docs/user-settings.md`) to
ensure all user cases are covered.

User Settings is the page where the signed-in user updates their identity
(first/last name, avatar URL) and reviews account info (email + role) that is
managed by their workspace admin.

For the workspace-level members directory (invite/remove/role-change), see
`members.md` (already in `e2e/ux_flow_docs/`). This doc focuses on the user-scoped
`/settings/profile` page.

---

## Page

- **Routes**:
  - `/user-settings` — redirects to `/settings/profile`
  - `/settings/profile` — the actual page
- **Wrapper**: `src/app/(dashboard)/settings/profile/page.tsx`
- **Main component**: `src/components/user-settings/UserSettings.tsx`
- **Sub-components**:
  - `src/components/user-settings/ProfileForm.tsx`
  - `AvatarPreview` (inline in `UserSettings.tsx`)
  - `RolePill` (inline in `UserSettings.tsx`)
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fsettings%2Fprofile` without `tone_access_token` cookie)

---

## User Stories

### US-1: View my profile

**As a** logged-in user, **I want to** see my current name, avatar, email,
and role on one page, **so that** I can confirm who I'm signed in as.

**Acceptance criteria**:

- [ ] Page header shows "User settings" + subtitle "Manage your personal account details and how you appear across the workspace."
- [ ] Two-column layout on LG+: left "Account" card (sticky), right "Profile" form
- [ ] Left card shows large avatar (size 88px, ring-4, gradient fallback if no URL), full name, email (with Mail icon), role pill, and a verified badge if `user.is_verified`
- [ ] Role pill colors: Owner → amber (Crown icon), Admin → indigo (ShieldCheck icon), Member → violet (default icon)
- [ ] If first/last name are missing, avatar initials fall back to "U"

### US-2: Update first/last name and avatar URL

**As a** logged-in user, **I want to** edit my display name and avatar,
**so that** I appear correctly to teammates.

**Acceptance criteria**:

- [ ] Profile form section labelled "01 — Identity"
- [ ] First name and Last name inputs are required, max 100 chars each
- [ ] Avatar URL is optional, max 512 chars, must be a valid URL when non-empty
- [ ] Live avatar preview swatch updates as the user types the URL
- [ ] Form is built on `react-hook-form` + `zodResolver` with mode `'onChange'`
- [ ] "Save changes" button is disabled when not dirty, not valid, or submitting
- [ ] Submitting calls `PUT /me` via `updateProfileAtom`; on success the global auth atom updates and a "Profile updated" toast appears
- [ ] On error: `handleApiError` toast, form stays editable

### US-3: See that email and role are read-only

**As a** logged-in user, **I want to** see clearly that email and role can't
be changed here, **so that** I know to ask an admin instead.

**Acceptance criteria**:

- [ ] Section labelled "02 — Account" with description "Managed by your workspace owner. Contact an admin to change these."
- [ ] Divider between sections labelled "Read only"
- [ ] Email + Role inputs are `disabled`, render a left Lock icon, and pull values from `user.email` / `user.role`
- [ ] If no role on the user object, the Role field shows "—"

### US-4: Redirect legacy `/user-settings`

**As a** user navigating from old links, **I want** `/user-settings` to take
me to the new page, **so that** old bookmarks still work.

**Acceptance criteria**:

- [ ] `/user-settings` redirects to `/settings/profile`
- [ ] Subsequent reloads land on `/settings/profile` directly

---

## User Workflow Steps

Drives `frontend/e2e/dashboard/user-settings.spec.ts`. The auth-write endpoint
used by `updateProfileAtom` is `PATCH /user/me` (see `src/lib/api/auth.ts:54`),
NOT `PUT /me` — earlier draft of this doc was wrong on that point.

**WF-1: View my profile** (positive)
1. User signs in via worker fixture → expected: `/home`
2. User clicks sidebar "User settings" → expected: URL `/settings/profile`; left "Account" card visible LG+ with avatar (88px ring-4), name, email, role pill
3. Role pill color matches: Owner→amber + Crown, Admin→indigo + ShieldCheck, Member→violet
4. If `user.is_verified === true` → "Verified" badge visible
5. If `user.first_name` and `user.last_name` both empty → avatar initials fall back to "U"

**WF-2: Update name + avatar URL** (positive)
1. User edits "First name" to `Ada` → expected: form dirty; live avatar preview swatch updates initials to `A?`
2. User edits "Last name" to `Lovelace` → expected: preview shows `AL`
3. User pastes a valid URL into "Avatar URL" → expected: preview swatch swaps to `<img src=URL>` live
4. User clicks "Save changes" → expected: button shows "Saving..." with spinner + `disabled`; `PATCH /user/me` fires with `{first_name, last_name, avatar_url}`
5. Response 200 → expected: success toast title "Profile updated"; form `isDirty` resets to false; Save button re-disabled
6. Global `useAuthStore.setUser` called → sidebar / top bar reflect new name immediately

**WF-3: Validation failure path** (negative)
1. User clears "First name" → expected: inline Zod error "First name is required"; Save button disabled (`!isValid`)
2. User types 101 chars into "Last name" → expected: inline error "Last name must be at most 100 characters"
3. User types `not-a-url` into "Avatar URL" → expected: inline error "Enter a valid URL"; avatar preview falls back to initials
4. User leaves "Avatar URL" empty → expected: NO error (optional, `.or(z.literal(''))`)

**WF-4: Read-only fields** (positive)
1. User inspects "02 — Account" section → expected: "Read only" divider label visible
2. Email input → expected: `disabled` attribute, Lock left icon, value = `user.email`
3. Role input → expected: `disabled`, Lock icon, value = `user.role` or em-dash `—` if absent
4. User attempts to type in either → expected: keystrokes ignored (disabled)

**WF-5: Legacy `/user-settings` redirect** (positive)
1. User navigates to `/user-settings` → expected: server redirect (Next.js) to `/settings/profile`
2. User reloads → expected: lands directly on `/settings/profile` (no re-hop)

---

## Input Specifications

Source: `src/components/user-settings/ProfileForm.tsx` Zod schema (`profileSchema`).

| Field        | Type        | Required | Validation Rules                                                          | Exact Error Message                                  |
| ------------ | ----------- | -------- | ------------------------------------------------------------------------- | ---------------------------------------------------- |
| `first_name` | TextInput   | Yes      | `z.string().min(1).max(100)`                                              | `First name is required` / `First name must be at most 100 characters` |
| `last_name`  | TextInput   | Yes      | `z.string().min(1).max(100)`                                              | `Last name is required` / `Last name must be at most 100 characters`   |
| `avatar_url` | TextInput   | No       | `z.string().trim().max(512).url().optional().or(z.literal(''))` — must be a valid URL when non-empty; empty string allowed | `Avatar URL must be at most 512 characters` / `Enter a valid URL` |
| `email`      | TextInput   | n/a      | `disabled`, `readOnly`, value = `user.email`                              | n/a — read-only                                      |
| `role`       | TextInput   | n/a      | `disabled`, `readOnly`, value = `user.role` or `—`                        | n/a — read-only                                      |

Submit button state machine (`<CustomButton disabled={...}>`):
- Disabled when: `!formState.isValid` OR `formState.isSubmitting` OR `!formState.isDirty`
- Label transitions: `Save changes` → `Saving...` while in flight
- `CustomButton loading={saving}` adds a spinner start-icon and forces `disabled`

---

## Success Scenarios

**PS-1: View profile loads from auth store**
- Preconditions: signed-in user with `first_name="Ada"`, `last_name="Lovelace"`, `email="owner@acme.com"`, `role="owner"`, `is_verified=true`.
- Steps: navigate `/settings/profile`.
- Expected: avatar shows initials `AL` or `<img>` if `avatar_url`; "Verified" badge visible; role pill amber + Crown.
- **Mock API**: `GET /user/me` (only called by `loginViaUI` worker fixture; profile page reads from `useAuthStore`):
  ```json
  {
    "id": "user-uuid",
    "organization_id": "org-uuid",
    "email": "owner@acme.com",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "avatar_url": null,
    "role": "owner",
    "is_active": true,
    "is_verified": true,
    "auth_provider": "local",
    "last_login_at": "2026-05-27T09:55:00+00:00",
    "created_at": "2026-05-20T10:00:00+00:00",
    "updated_at": "2026-05-27T10:00:00+00:00"
  }
  ```

**PS-2: Update name + avatar URL**
- Preconditions: PS-1.
- Steps: change first_name to `Ada G.`, paste avatar URL, click "Save changes".
- Expected: toast "Profile updated" (success); form not dirty; sidebar avatar updates.
- **Mock API**: `PATCH /user/me` request body:
  ```json
  { "first_name": "Ada G.", "last_name": "Lovelace", "avatar_url": "https://r2.example.com/avatars/ada.png" }
  ```
  Success body (200):
  ```json
  {
    "id": "user-uuid",
    "email": "owner@acme.com",
    "first_name": "Ada G.",
    "last_name": "Lovelace",
    "avatar_url": "https://r2.example.com/avatars/ada.png",
    "role": "owner",
    "updated_at": "2026-05-27T10:05:00+00:00"
  }
  ```

**PS-3: Clear avatar URL → null**
- Preconditions: PS-1; user has an existing avatar URL.
- Steps: clear avatar field; click Save.
- Expected: `onSubmit` sends `avatar_url: null` (per code: `data.avatar_url?.trim() ? trim() : null`); toast "Profile updated".
- **Mock API**: `PATCH /user/me` request body includes `"avatar_url": null`.

**PS-4: Legacy `/user-settings` redirect**
- Steps: navigate `/user-settings`.
- Expected: URL becomes `/settings/profile` (Next.js `redirect()`); page renders normally.

---

## Failure Scenarios

**FS-1: Empty first name**
- Steps: clear "First name" field; tab out.
- Expected UI: inline error text under field reads `First name is required`; Save button stays `disabled`; no `PATCH` fires.

**FS-2: Empty last name**
- Same as FS-1 with `Last name is required`.

**FS-3: Oversize first/last name (> 100 chars)**
- Steps: paste 101-char string into "First name".
- Expected UI: inline error `First name must be at most 100 characters`; Save disabled.

**FS-4: Invalid avatar URL**
- Steps: type `not-a-url` into "Avatar URL".
- Expected UI: inline error `Enter a valid URL`; avatar preview swatch falls back to initials; Save disabled.

**FS-5: Oversize avatar URL (> 512 chars)**
- Expected UI: inline error `Avatar URL must be at most 512 characters`; Save disabled.

**FS-6: Save while not dirty**
- Preconditions: form pristine.
- Steps: open page, immediately click Save.
- Expected UI: button is `disabled` (`!formState.isDirty`) — click does nothing; no `PATCH` fires.

**FS-7: 500 on `PATCH /user/me`**
- **Mock API**: `PATCH /user/me` → `500 {"detail": "Internal server error"}`
- Expected UI: error toast title `Internal server error`; form stays dirty + editable; Save button re-enabled.

**FS-8: 401 Unauthorized on save**
- **Mock API**: `PATCH /user/me` → `401 {"detail": "Could not validate credentials"}`
- Expected UI: error toast `Could not validate credentials`; form remains editable. ⚠ unverified: middleware-level redirect to `/auth/login` may occur on the next navigation but not synchronously.

**FS-9: 404 User not found on save**
- **Mock API**: `PATCH /user/me` → `404 {"detail": "User not found"}`
- Expected UI: error toast `User not found`.

**FS-10: 422 Invalid body shape**
- **Mock API**: `PATCH /user/me` → `422 {"detail": [{"loc": ["body", "first_name"], "msg": "str type expected", "type": "type_error.str"}]}`
- Expected UI: `handleApiError` falls back to generic toast `Something went wrong. Please try again.` because `detail` is an array, not a string. Form stays editable.

**FS-11: Network failure on save**
- **Mock API**: `await route.abort('failed')`.
- Expected UI: error toast `Something went wrong. Please try again.`; form remains dirty.

**FS-12: Unauthenticated visit**
- Preconditions: no `tone_access_token` cookie.
- Steps: navigate `/settings/profile`.
- Expected: middleware redirects to `/auth/login?redirect=%2Fsettings%2Fprofile`.

---

## Expected Toast Messages

Source: `src/utils/toast.tsx` (`showToast.success` / `showToast.error`), `src/utils/helpers.ts` (`handleApiError`).

| Trigger                                  | Toast title                                | Toast description | Variant |
| ---------------------------------------- | ------------------------------------------ | ----------------- | ------- |
| `PATCH /user/me` 200 success             | `Profile updated`                          | (none)            | success |
| `PATCH /user/me` non-200 with string `detail` | `<response.data.detail>` (e.g. `User not found`) | (none) | error   |
| `PATCH /user/me` 422 (detail is array)   | `Something went wrong. Please try again.`  | (none)            | error   |
| Network failure / no response            | `Something went wrong. Please try again.`  | (none)            | error   |

> Sonner duration: success = 3000ms, error = 5000ms (per `showToast` defaults).
> Toast selector: `page.locator('[data-sonner-toast]').first()` and assert `toContainText('Profile updated')`.

---

## UI Elements

| Element                       | Type        | Content / Label                                                            | Behavior                                          |
| ----------------------------- | ----------- | -------------------------------------------------------------------------- | ------------------------------------------------- |
| Page heading                  | h1          | "User settings"                                                            | Static                                            |
| Page subtitle                 | body1       | "Manage your personal account details…"                                    | Static                                            |
| Account card (left, sticky)   | Card        | gradient border, primary/08 background                                     | Visible LG+; collapses above content on smaller   |
| Avatar (large)                | Avatar      | image or initials, ring-4, gradient bg fallback, verification dot          | Updates live with form changes                    |
| ACCOUNT label                 | Eyebrow     | "ACCOUNT"                                                                  | Static                                            |
| Name display                  | Text        | first_name + last_name (truncated)                                         | Reflects current user                             |
| Email display                 | Text        | Mail icon + user.email                                                     | Reflects current user                             |
| Role pill                     | Pill        | "Owner" / "Admin" / "Member"                                               | Color + icon per role                             |
| Verified badge                | Badge       | "Verified"                                                                 | Only when `user.is_verified`                      |
| Profile section heading       | h2          | "Profile"                                                                  | UserCircle icon                                   |
| Profile subtitle              | body2       | "Update your name, avatar, and how teammates see you."                     | Static                                            |
| Section 01 — Identity         | Section     | "01 — Identity"                                                            | Helper: "Your name and avatar appear in the sidebar, on shared resources, and in audit logs." |
| First name input              | TextInput   | label "First name", placeholder "Jane"                                     | Required, max 100                                 |
| Last name input               | TextInput   | label "Last name", placeholder "Doe"                                       | Required, max 100                                 |
| Avatar URL input              | TextInput   | placeholder "https://example.com/avatar.png", helper "Paste an image link. Leave blank to use your initials." | Optional, max 512, URL-validated when non-empty |
| Avatar preview swatch         | Avatar (sm) | live preview                                                               | Reflects current avatar_url field value           |
| Read-only divider             | Divider     | "Read only" label                                                          | Static                                            |
| Section 02 — Account          | Section     | "02 — Account"                                                             | Helper: "Managed by your workspace owner. Contact an admin to change these." |
| Email input (read-only)       | TextInput   | Lock icon, value = user.email                                              | `disabled`                                        |
| Role input (read-only)        | TextInput   | Lock icon, value = user.role or "—"                                        | `disabled`                                        |
| Required field hint           | Caption     | "* Required field"                                                         | Static                                            |
| Save changes button           | Button      | "Save changes" + Save icon                                                 | Disabled until dirty + valid + not submitting     |

---

## Navigation

| Trigger                        | Destination                                       | Condition                              |
| ------------------------------ | ------------------------------------------------- | -------------------------------------- |
| Visit `/user-settings`         | `/settings/profile`                               | Redirect                               |
| Click sidebar "User settings"  | `/settings/profile`                               | Always                                 |
| Click sidebar "Members"        | `/settings/members`                               | Always                                 |
| Click sidebar "Organizations"  | `/settings/organizations`                         | Always                                 |
| Click sidebar "Model Providers"| `/settings/model-providers`                       | Always                                 |
| Click sidebar "Integrations"   | `/settings/integrations`                          | Always                                 |
| Click "Save changes"           | `PUT /me` → auth atom updates → toast             | Form valid + dirty                     |
| No auth cookie                 | `/auth/login?redirect=%2Fsettings%2Fprofile`      | `src/middleware.ts` redirect           |

---

## API Contracts

Real backend prefix is `/api/v1/user` (`POST` is NOT used for profile update —
the verb is `PATCH`, not `PUT`). The Jotai write atom is `updateProfileAtom`
in `src/atoms/UserSettingsAtom.tsx`, which calls `authApi.updateMe()` →
`axios.patch<User>('/user/me', payload)`. On success it calls
`useAuthStore.setUser(updated)` so the sidebar / top bar pick up the new
identity immediately.

| Endpoint    | Method | Request                                 | Success Response (User) | Error Response       |
| ----------- | ------ | --------------------------------------- | ----------------------- | -------------------- |
| `/user/me`  | GET    | —                                       | `User` object           | `{ detail: "..." }`  |
| `/user/me`  | PATCH  | `{ first_name, last_name, avatar_url }` | `User` object           | `{ detail: "..." }`  |

### Example — `GET /user/me`

Success body (200):
```json
{
  "id": "user-uuid",
  "organization_id": "org-uuid",
  "email": "owner@acme.com",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "avatar_url": null,
  "role": "owner",
  "is_active": true,
  "is_verified": true,
  "auth_provider": "local",
  "last_login_at": "2026-05-27T09:55:00+00:00",
  "created_at": "2026-05-20T10:00:00+00:00",
  "updated_at": "2026-05-27T10:00:00+00:00"
}
```
Error bodies:
- `401 {"detail": "Could not validate credentials"}`
- `404 {"detail": "User not found"}`

### Example — `PATCH /user/me`

Request body (form sends only the three editable fields; trims whitespace; sends `avatar_url: null` when cleared):
```json
{
  "first_name": "Ada",
  "last_name": "Lovelace",
  "avatar_url": "https://r2.example.com/avatars/ada.png"
}
```
Success body (200):
```json
{
  "id": "user-uuid",
  "email": "owner@acme.com",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "avatar_url": "https://r2.example.com/avatars/ada.png",
  "role": "owner",
  "updated_at": "2026-05-27T10:05:00+00:00"
}
```
Validation error body (422):
```json
{
  "detail": [
    {"loc": ["body", "first_name"], "msg": "str type expected", "type": "type_error.str"}
  ]
}
```
Other error bodies:
- `401 {"detail": "Could not validate credentials"}`
- `404 {"detail": "User not found"}`

> Backend note (Postman collection): `UPDATABLE_PROFILE_FIELDS` whitelist
> silently drops `phone_number` / `profile` etc.; `avatar_url` cannot be
> cleared via PATCH (sending `null` is treated as "omitted" server-side).
> ⚠ unverified for tests: the frontend always sends `avatar_url: null` when
> empty, but the persisted value may stay unchanged. Assert via the response,
> not by re-fetching.

---

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] User object is not yet hydrated → `AppLoader` until hydration completes
- [ ] Empty first or last name on submit → inline Zod error "First name is required" / "Last name is required"
- [ ] Avatar URL not a valid URL (non-empty) → inline Zod error "Enter a valid URL"; preview falls back to initials
- [ ] Avatar URL empty → preview shows initials over the gradient background
- [ ] Avatar image fails to load (404, blocked) → fallback to initials
- [ ] Form not dirty → "Save changes" disabled even if values are valid
- [ ] Network/API error on save → `handleApiError` toast; the form remains dirty and editable
- [ ] Submit while a previous submit is in flight → button disabled, double-submit prevented
- [ ] Email/role displayed as "—" only when the underlying field is genuinely missing on the user object
- [ ] Reset on user prop change → form `reset()` is called when the auth atom emits a new user
- [ ] Avatar image 404 / blocked: `<img>` `onerror` falls back to gradient + initials (handled inside `AvatarPreview`)
- [ ] Save while previous PUT/PATCH in flight: button disabled via `saving = formState.isSubmitting`; click no-ops; cannot enqueue a second request
- [ ] Form `reset()` on user atom emit: `useEffect([user, reset])` re-seeds fields whenever `useAuthStore.user` reference changes — typing in the form WHILE the atom updates can lose user edits (⚠ unverified — confirm with explicit test)
- [ ] Avatar URL with leading/trailing whitespace: schema `.trim()` strips before validation; `onSubmit` also trims again before send
- [ ] Avatar URL with non-HTTP scheme (e.g. `javascript:alert(1)`): Zod `.url()` accepts ANY valid URL incl. `javascript:` — browsers will refuse to load it in `<img>`, falling back to initials. ⚠ unverified — confirm if backend rejects or sanitizes
- [ ] Email or role missing on user object: rendered as `—` (em-dash) in the Role field; `email` field shows `''` when absent
- [ ] Toast stacking: if user clicks Save rapidly across two valid edits, only the first request fires (button stays disabled until prior settles), so toasts don't stack
- [ ] Mobile viewport: two-column layout collapses; Account card stacks above Profile form; same form state behavior

---

## Business Rules

- Email and role are out of scope for self-service edits. Role changes are handled by org owners/admins on `/settings/members` (see `members.md`).
- Avatar URL is stored verbatim — no upload, no CDN proxy. Users paste a URL to a hosted image.
- First/last name length is capped at 100 each (Zod). Avatar URL is capped at 512.
- Successful save updates global auth state immediately so other pages reflect the new identity without a refetch.
- The verified badge is read-only and driven by `user.is_verified`; verification flows happen elsewhere.

---

## Accessibility Requirements

- [ ] Form inputs have associated labels (shared `TextInput` renders the label by default)
- [ ] Read-only fields announce their disabled state (Lock icon + `disabled` attribute)
- [ ] Required field hint ("* Required field") is associated with the form
- [ ] Avatar preview has an `alt` text describing whose avatar it shows
- [ ] Toast notifications are announced via `aria-live` (Sonner default)
- [ ] Section eyebrows ("01 — Identity", "02 — Account") use proper heading hierarchy beneath the page h1
- [ ] Save button is keyboard reachable and announces its loading state ("Saving…") when in flight

---

## E2E Scenarios — gap-filling

> Scenarios use the `US-PROF-` prefix to disambiguate from User Story IDs
> above. Existing PS-/FS-/WF- entries remain unchanged; the table below is the
> append-only gap-fill that `/generate-tests` reads.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-001 | Visit `/settings/profile` without `tone_access_token` cookie | Redirect to `/auth/login?redirect=%2Fsettings%2Fprofile` | `unauthenticated visit redirects to login` |
| US-PROF-002 | Visit with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| US-PROF-003 | Visit `/user-settings` legacy path without auth | Redirect to `/auth/login?redirect=%2Fsettings%2Fprofile` (post-redirect target preserved) | `legacy /user-settings without auth redirects to login with profile redirect` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-010 | `PATCH /user/me` returns 400 with `{detail: "first_name is required"}` | Toast `first_name is required`; form stays dirty + editable | `400 on save shows toast and keeps form intact` |
| US-PROF-011 | `PATCH /user/me` returns 401 mid-flow | Toast `Could not validate credentials`; next navigation redirects to login | `401 on save shows toast and triggers login redirect on nav` |
| US-PROF-012 | `PATCH /user/me` returns 403 (e.g. demoted mid-session) | Toast with backend `detail`; form remains intact | `403 on save shows toast` |
| US-PROF-013 | `PATCH /user/me` returns 409 (e.g. conflict) | Toast with conflict `detail`; form stays dirty | `409 on save shows conflict toast` |
| US-PROF-014 | `PATCH /user/me` returns 500 | Toast `Internal server error`; form intact | `500 on save shows toast` |
| US-PROF-015 | Concurrent edit: another tab updated the user — local atom re-seeds form via `useEffect([user, reset])` | Untyped values are replaced; ensure no crash; (⚠ unverified — typing user may lose edits) | `external user atom update reseeds the form` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-020 | Save with network failure (`route.abort('failed')`) | Toast `Something went wrong. Please try again.`; form stays dirty | `network failure on save shows toast and preserves form` |
| US-PROF-021 | Slow `PATCH /user/me` (>3s) | Save button shows `Saving...` + spinner + `disabled`; no double submit possible | `slow save disables button with Saving state` |
| US-PROF-022 | Save retried after restoring connection | First failed; second succeeds → `Profile updated` toast | `save can be retried after network recovery` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-030 | First name whitespace only (e.g. `"   "`) | Zod `.min(1)` rejects after trim (⚠ confirm trim behavior); inline error `First name is required` | `whitespace-only first name rejected` |
| US-PROF-031 | Leading/trailing whitespace in first name | `onSubmit` sends trimmed value; toast `Profile updated`; reload shows trimmed name | `leading/trailing whitespace is trimmed before submit` |
| US-PROF-032 | First name with emoji + unicode (e.g. `Adä 🚀`) | Accepted; round-trips through PATCH response; sidebar renders unicode | `unicode + emoji name round-trips` |
| US-PROF-033 | First name with `<script>` tag content | Stored verbatim and rendered as text (not executed); no XSS in sidebar / swatch | `script tag in name is escaped on render` |
| US-PROF-034 | Avatar URL with `javascript:` scheme | Zod `.url()` accepts; `<img src=>` refuses; preview falls back to initials | `javascript: scheme URL falls back to initials safely` |
| US-PROF-035 | Avatar URL exactly 512 chars | Accepted; reload returns same URL | `avatar URL at 512-char boundary accepted` |
| US-PROF-036 | Avatar URL 513 chars | Inline error `Avatar URL must be at most 512 characters`; Save disabled | `avatar URL over 512 chars rejected` |
| US-PROF-037 | Avatar URL with leading/trailing whitespace | Trimmed before submit; reload shows clean URL | `avatar URL whitespace trimmed before submit` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-040 | Tab through Identity section | Order: First name → Last name → Avatar URL → Save changes | `keyboard tab order through Identity section` |
| US-PROF-041 | Submit form via Enter key from any focused input | Triggers save (same path as clicking Save) | `Enter key on focused input submits the form` |
| US-PROF-042 | Inline Zod error message has `role="alert"` or aria-live | Screen reader announces error on blur | `inline error is announced by screen readers` |
| US-PROF-043 | Read-only Email/Role inputs announce `disabled` | Keyboard focus skips or announces disabled | `read-only fields announce disabled state` |
| US-PROF-044 | Tab onto Save button when disabled | Button still focusable; Enter / Space is a no-op | `disabled Save button is reachable but inert` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-050 | After successful save, click sidebar `Members` | Navigates to `/settings/members`; updated first name visible in account swatch / top bar | `post-save navigation reflects new name elsewhere` |
| US-PROF-051 | Browser Back from `/settings/profile` after save | Returns to whatever route preceded; no unsaved-changes prompt (form was reset post-save) | `back after save does not prompt for unsaved changes` |
| US-PROF-052 | Browser Back with unsaved edits | Form is left dirty; user navigates anyway (⚠ unverified — no warning today) | `back with dirty form navigates away without prompt` |

### Full lifecycle test

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| US-PROF-FULL | Load `/settings/profile` → edit first_name + last_name + avatar_url → save → reload → assert persistence → revert original values → save | All transitions assert success toast + atom update + reload persistence; `try/finally` restores original profile values | `lifecycle: edit profile → save → reload → revert → save` |
