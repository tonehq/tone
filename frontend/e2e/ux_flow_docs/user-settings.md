# Feature Doc: User Settings (Profile)

Feature documentation for the per-user profile page. Used by
`/generate-tests user-settings` (or `--docs e2e/ux_flow_docs/user-settings.md`) to
ensure all user cases are covered.

User Settings is the page where the signed-in user updates their identity
(first/last name, avatar URL) and reviews account info (email + role) that is
managed by their workspace admin.

For the workspace-level members directory (invite/remove/role-change), see
`members.md`. This doc focuses on the user-scoped `/settings/profile` page.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

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

**As a** logged-in user, **I want to** see my current name, avatar, email, and role on one page, **so that** I can confirm who I'm signed in as.

**Acceptance criteria**:

- [ ] Page header shows "User settings" + subtitle "Manage your personal account details and how you appear across the workspace."
- [ ] Two-column layout on LG+: left "Account" card (sticky), right "Profile" form
- [ ] Left card shows large avatar (88px, ring-4, gradient fallback), full name, email + Mail icon, role pill, and a verified badge if `user.is_verified`
- [ ] Role pill colors: Owner → amber (Crown), Admin → indigo (ShieldCheck), Member → violet (default)
- [ ] If first/last name are missing, avatar initials fall back to "U"

### US-2: Update first/last name and avatar URL

**As a** logged-in user, **I want to** edit my display name and avatar.

**Acceptance criteria**:

- [ ] Profile form section labelled "01 — Identity"
- [ ] First and Last name inputs are required, max 100 chars each
- [ ] Avatar URL is optional, max 512 chars, must be valid URL when non-empty
- [ ] Live avatar preview swatch updates as the user types
- [ ] Form is `react-hook-form` + `zodResolver` mode `'onChange'`
- [ ] "Save changes" disabled when not dirty, not valid, or submitting
- [ ] Submit calls `PATCH /user/me`; on success, global auth atom updates + "Profile updated" toast
- [ ] On error: `handleApiError` toast; form stays editable

### US-3: See that email and role are read-only

**As a** logged-in user, **I want to** see that email and role can't be changed here.

**Acceptance criteria**:

- [ ] Section labelled "02 — Account" with description "Managed by your workspace owner. Contact an admin to change these."
- [ ] Divider between sections labelled "Read only"
- [ ] Email + Role inputs are `disabled`, render a Lock icon, and pull from `user.email` / `user.role`
- [ ] If no role on the user object, the Role field shows "—"

### US-4: Redirect legacy `/user-settings`

**As a** user navigating from old links, **I want** `/user-settings` to take me to the new page.

**Acceptance criteria**:

- [ ] `/user-settings` redirects to `/settings/profile`
- [ ] Subsequent reloads land directly on `/settings/profile`

---

## UI Elements

| Element                       | Type        | Content / Label                                                            | Behavior                                          |
| ----------------------------- | ----------- | -------------------------------------------------------------------------- | ------------------------------------------------- |
| Page heading                  | h1          | "User settings"                                                            | Static                                            |
| Page subtitle                 | body1       | "Manage your personal account details…"                                    | Static                                            |
| Account card (left, sticky)   | Card        | gradient border, primary/08 background                                     | Visible LG+; collapses above content otherwise    |
| Avatar (large)                | Avatar      | image or initials, ring-4, gradient bg fallback, verification dot          | Updates live with form changes                    |
| ACCOUNT label                 | Eyebrow     | "ACCOUNT"                                                                  | Static                                            |
| Name display                  | Text        | first_name + last_name (truncated)                                         | Reflects current user                             |
| Email display                 | Text        | Mail icon + user.email                                                     | Reflects current user                             |
| Role pill                     | Pill        | "Owner" / "Admin" / "Member"                                               | Color + icon per role                             |
| Verified badge                | Badge       | "Verified"                                                                 | Only when `user.is_verified`                      |
| Profile section heading       | h2          | "Profile"                                                                  | UserCircle icon                                   |
| Profile subtitle              | body2       | "Update your name, avatar, and how teammates see you."                     | Static                                            |
| Section 01 — Identity         | Section     | "01 — Identity"                                                            | Helper text below                                 |
| First name input              | TextInput   | label "First name", placeholder "Jane"                                     | Required, max 100                                 |
| Last name input               | TextInput   | label "Last name", placeholder "Doe"                                       | Required, max 100                                 |
| Avatar URL input              | TextInput   | placeholder "https://example.com/avatar.png", helper "Paste an image link. Leave blank to use your initials." | Optional, max 512, URL-validated when non-empty |
| Avatar preview swatch         | Avatar (sm) | live preview                                                               | Reflects current avatar_url field value           |
| Read-only divider             | Divider     | "Read only" label                                                          | Static                                            |
| Section 02 — Account          | Section     | "02 — Account"                                                             | Helper: "Managed by your workspace owner. Contact an admin to change these." |
| Email input (read-only)       | TextInput   | Lock icon, value = user.email                                              | `disabled`                                        |
| Role input (read-only)        | TextInput   | Lock icon, value = user.role or "—"                                        | `disabled`                                        |
| Required field hint           | Caption     | "* Required field"                                                         | Static                                            |
| Save changes button           | Button      | "Save changes" → "Saving..." with spinner                                  | Disabled until dirty + valid + not submitting     |

---

## Input Specifications

Source: `src/components/user-settings/ProfileForm.tsx` Zod schema (`profileSchema`).

| Field        | Type        | Required | Validation Rules                                                          | Exact Error Message                                  |
| ------------ | ----------- | -------- | ------------------------------------------------------------------------- | ---------------------------------------------------- |
| `first_name` | TextInput   | Yes      | `z.string().min(1).max(100)`                                              | `First name is required` / `First name must be at most 100 characters` |
| `last_name`  | TextInput   | Yes      | `z.string().min(1).max(100)`                                              | `Last name is required` / `Last name must be at most 100 characters`   |
| `avatar_url` | TextInput   | No       | `z.string().trim().max(512).url().optional().or(z.literal(''))` — must be a valid URL when non-empty; empty allowed | `Avatar URL must be at most 512 characters` / `Enter a valid URL` |
| `email`      | TextInput   | n/a      | `disabled`, `readOnly`, value = `user.email`                              | n/a — read-only                                      |
| `role`       | TextInput   | n/a      | `disabled`, `readOnly`, value = `user.role` or `—`                        | n/a — read-only                                      |

Submit button state machine (`<CustomButton disabled={...}>`):
- Disabled when: `!formState.isValid` OR `formState.isSubmitting` OR `!formState.isDirty`
- Label: `Save changes` → `Saving...` while in flight
- `CustomButton loading={saving}` adds a spinner and forces `disabled`

---

## Navigation

| Trigger                        | Destination                                       | Condition                              |
| ------------------------------ | ------------------------------------------------- | -------------------------------------- |
| Visit `/user-settings`         | `/settings/profile`                               | Server redirect                        |
| Click sidebar "User settings"  | `/settings/profile`                               | Always                                 |
| Click sidebar "Members"        | `/settings/members`                               | Always                                 |
| Click sidebar "Organizations"  | `/settings/organizations`                         | Always                                 |
| Click sidebar "Model Providers"| `/settings/model-providers`                       | Always                                 |
| Click sidebar "Integrations"   | `/settings/integrations`                          | Always                                 |
| Click "Save changes"           | `PATCH /user/me` → auth atom updates → toast      | Form valid + dirty                     |
| No auth cookie                 | `/auth/login?redirect=%2Fsettings%2Fprofile`      | `src/middleware.ts` redirect           |

---

## API Contracts

Real backend prefix is `/api/v1/user` and the update verb is `PATCH` (not `PUT`). The Jotai write atom is `updateProfileAtom` in `src/atoms/UserSettingsAtom.tsx`, which calls `authApi.updateMe()` → `axios.patch<User>('/user/me', payload)`. On success it calls `useAuthStore.setUser(updated)` so the sidebar / top bar pick up the new identity immediately.

| Endpoint    | Method | Request                                 | Success Response (User) | Error Response       |
| ----------- | ------ | --------------------------------------- | ----------------------- | -------------------- |
| `/user/me`  | GET    | —                                       | `User` object           | `{ detail: "..." }`  |
| `/user/me`  | PATCH  | `{ first_name, last_name, avatar_url }` | `User` object           | `{ detail: "..." }`  |

### Example — `GET /user/me`

200 OK:
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
Errors:
- `401 {"detail": "Could not validate credentials"}`
- `404 {"detail": "User not found"}`

### Example — `PATCH /user/me`

Request body (form sends only the three editable fields; trims; sends `avatar_url: null` when cleared):
```json
{ "first_name": "Ada", "last_name": "Lovelace", "avatar_url": "https://r2.example.com/avatars/ada.png" }
```
200 OK:
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
400 example: `{"detail": "first_name is required"}`
401 example: `{"detail": "Could not validate credentials"}`
403 example: `{"detail": "Forbidden"}`
404 example: `{"detail": "User not found"}`
409 example: `{"detail": "Conflict"}`
422 example: `{"detail": [{"loc": ["body", "first_name"], "msg": "str type expected", "type": "type_error.str"}]}`
500 example: `{"detail": "Internal server error"}`

> Backend note: `UPDATABLE_PROFILE_FIELDS` whitelist silently drops `phone_number` / `profile` etc.; `avatar_url` may not be clearable via PATCH (sending `null` may be treated as "omitted" server-side). ⚠ unverified — assert via the response, not by re-fetching.

---

## Expected Toast Messages

Source: `src/utils/toast.tsx` (`showToast.success` / `showToast.error`), `src/utils/helpers.ts` (`handleApiError`).

| Trigger                                  | Toast title                                | Toast description | Variant |
| ---------------------------------------- | ------------------------------------------ | ----------------- | ------- |
| `PATCH /user/me` 200 success             | `Profile updated`                          | (none)            | success |
| `PATCH /user/me` non-200 with string `detail` | `<response.data.detail>` (e.g. `User not found`) | (none) | error   |
| `PATCH /user/me` 422 (detail is array)   | `Something went wrong. Please try again.`  | (none)            | error   |
| Network failure / no response            | `Something went wrong. Please try again.`  | (none)            | error   |

> Sonner duration: success = 3000ms, error = 5000ms. Selector: `page.locator('[data-sonner-toast]').first()`.

---

## Test Cases

---

### TC-HAPPY-001: View profile loads from auth store

**Preconditions**:
- Signed-in user: `first_name="Ada"`, `last_name="Lovelace"`, `email="owner@acme.com"`, `role="owner"`, `is_verified=true`

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Header + chrome**:
1. Page `h1` reads `User settings`
2. Subtitle reads `Manage your personal account details and how you appear across the workspace.`

**Observation 2 — Account card (LG+)**:
1. Avatar shows initials `AL` (or `<img>` if `avatar_url` set)
2. Name display reads `Ada Lovelace`
3. Email display contains `owner@acme.com` next to a Mail icon
4. Role pill shows `Owner` with amber color + Crown icon
5. `Verified` badge is visible

**Observation 3 — Identity section pre-filled**:
1. First name input value equals `Ada`
2. Last name input value equals `Lovelace`
3. Avatar URL input value is empty (or matches `avatar_url`)

**Observation 4 — Read-only fields**:
1. Email input is `disabled` with Lock icon and value `owner@acme.com`
2. Role input is `disabled` with Lock icon and value `owner`

---

### TC-HAPPY-002: Profile renders fallbacks when names are missing

**Preconditions**: `first_name=""`, `last_name=""`, `role` absent.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Avatar fallback**:
1. Initials display `U`

**Observation 2 — Role field fallback**:
1. Role input value equals `—` (em-dash)

---

### TC-HAPPY-003: Update name + avatar URL

**Preconditions**: Signed in with `first_name="Ada"`, `last_name="Lovelace"`.

**Action**:
1. Visit `/settings/profile`
2. Change `First name` to `Ada G.`
3. Paste `https://r2.example.com/avatars/ada.png` into `Avatar URL`
4. Click `Save changes`

**Observation 1 — Live preview**:
1. As `First name` is edited, the avatar preview swatch reflects the new initials
2. After pasting URL, the preview swatch renders `<img src=URL>`

**Observation 2 — Network**:
1. Exactly one `PATCH /user/me` is recorded
2. Request body equals `{ "first_name": "Ada G.", "last_name": "Lovelace", "avatar_url": "https://r2.example.com/avatars/ada.png" }`

**Observation 3 — Loading state**:
1. The Save button shows `Saving...` and `disabled` during the request

**Observation 4 — Toast + form reset**:
1. A Sonner success toast appears with title `Profile updated`
2. After response, the form `isDirty` resets to false
3. The Save button re-disables

**Observation 5 — Global atom update**:
1. The sidebar / top bar reflect the new name immediately (no reload)

**API mock**: `PATCH /user/me` → 200 with response including the updated `first_name`.

---

### TC-HAPPY-004: Clear avatar URL sends null

**Preconditions**: User has an existing avatar URL.

**Action**:
1. Visit `/settings/profile`
2. Clear the Avatar URL field
3. Click `Save changes`

**Observation 1 — Request body**:
1. `PATCH /user/me` body contains `"avatar_url": null`

**Observation 2 — Toast**:
1. Success toast `Profile updated` appears

> ⚠ Backend may treat `null` as "omitted"; assert via the response, not a refetch.

---

### TC-HAPPY-005: Avatar URL with whitespace is trimmed before submit

**Action**:
1. Visit `/settings/profile`
2. Type `  https://example.com/me.png  ` into Avatar URL
3. Click Save

**Observation 1 — Trimmed payload**:
1. PUT body `avatar_url` equals `https://example.com/me.png` (no leading/trailing whitespace)

**Observation 2 — Persisted clean**:
1. After reload the field shows the trimmed URL

---

### TC-HAPPY-006: Avatar URL at 512-char boundary accepted

**Action**:
1. Visit `/settings/profile`
2. Paste a 512-char valid URL into Avatar URL
3. Click Save

**Observation 1 — Accepted**:
1. PUT fires; success toast appears
2. After reload the field shows the same URL

---

### TC-HAPPY-007: Leading/trailing whitespace in first name is trimmed

**Action**:
1. Visit `/settings/profile`
2. Type `  Ada  ` into First name
3. Click Save

**Observation 1 — Trimmed payload**:
1. PUT body `first_name` equals `Ada`

**Observation 2 — Reload**:
1. After reload the field shows `Ada` (trimmed)

---

### TC-HAPPY-008: Unicode + emoji name round-trips

**Action**:
1. Visit `/settings/profile`
2. Type `Adä 🚀` into First name
3. Click Save

**Observation 1 — Round-trips**:
1. PUT body contains the unicode + emoji literal
2. Sidebar / top bar render unicode after success
3. After reload the field still shows `Adä 🚀`

---

### TC-VALIDATE-001: Empty first name shows inline error

**Action**:
1. Visit `/settings/profile`
2. Clear `First name`
3. Blur the input

**Observation 1 — Inline error**:
1. Helper text under the field reads `First name is required`

**Observation 2 — Save blocked**:
1. The Save button has `disabled`
2. Zero `PATCH /user/me` requests are recorded

---

### TC-VALIDATE-002: Empty last name shows inline error

**Action**:
1. Visit `/settings/profile`
2. Clear `Last name`
3. Blur the input

**Observation 1 — Inline error**:
1. Helper text reads `Last name is required`

**Observation 2 — Save blocked**:
1. Save button disabled; zero PATCH requests

---

### TC-VALIDATE-003: Oversize first name (> 100 chars) is rejected

**Action**:
1. Visit `/settings/profile`
2. Paste a 101-char string into `First name`

**Observation 1 — Inline error**:
1. Helper text reads `First name must be at most 100 characters`

**Observation 2 — Save blocked**:
1. Save button disabled

---

### TC-VALIDATE-004: Invalid avatar URL is rejected

**Action**:
1. Visit `/settings/profile`
2. Type `not-a-url` into Avatar URL
3. Blur

**Observation 1 — Inline error**:
1. Helper text reads `Enter a valid URL`

**Observation 2 — Preview fallback**:
1. Avatar preview swatch falls back to initials

**Observation 3 — Save blocked**:
1. Save button disabled

---

### TC-VALIDATE-005: Oversize avatar URL (> 512 chars) is rejected

**Action**:
1. Visit `/settings/profile`
2. Paste a 513-char URL into Avatar URL

**Observation 1 — Inline error**:
1. Helper text reads `Avatar URL must be at most 512 characters`

**Observation 2 — Save blocked**:
1. Save button disabled

---

### TC-VALIDATE-006: Avatar URL empty is allowed (no error)

**Action**:
1. Visit `/settings/profile`
2. Leave Avatar URL empty

**Observation 1 — No error**:
1. No helper text under Avatar URL
2. Other field validity rules still apply

---

### TC-VALIDATE-007: Save while not dirty is a no-op

**Preconditions**: Form pristine.

**Action**:
1. Visit `/settings/profile`
2. Immediately click Save

**Observation 1 — Save disabled**:
1. Save button has `disabled` (`!formState.isDirty`)

**Observation 2 — No network**:
1. Zero `PATCH /user/me` requests are recorded

---

### TC-VALIDATE-008: Whitespace-only first name rejected

**Action**:
1. Visit `/settings/profile`
2. Type `   ` into First name

**Observation 1 — Inline error**:
1. Helper text reads `First name is required` (Zod `.min(1)` after trim)

> ⚠ confirm trim behavior in the Zod schema.

---

### TC-ERROR-001: 400 on PATCH shows toast and keeps form intact

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast**:
1. Toast text equals `first_name is required`

**Observation 2 — Form preserved**:
1. Form is still dirty and editable

**API mock**: `PATCH /user/me` → `400 { "detail": "first_name is required" }`.

---

### TC-ERROR-002: 401 on PATCH shows toast and triggers login redirect on nav

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast**:
1. Toast text equals `Could not validate credentials`

**Observation 2 — Form preserved**:
1. Form remains dirty + editable

**Observation 3 — Login redirect on next nav**:
1. Navigating to another protected route lands on `/auth/login`

**API mock**: PATCH → `401 { "detail": "Could not validate credentials" }`.

---

### TC-ERROR-003: 403 on PATCH shows toast

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast + form preserved**:
1. Toast surfaces the `detail`
2. Form stays editable

**API mock**: PATCH → `403 { "detail": "Forbidden" }`.

---

### TC-ERROR-004: 404 on PATCH shows toast

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast**:
1. Toast title equals `User not found`

**API mock**: PATCH → `404 { "detail": "User not found" }`.

---

### TC-ERROR-005: 409 on PATCH shows conflict toast

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast + form preserved**:
1. Toast surfaces the conflict `detail`
2. Form stays dirty

**API mock**: PATCH → `409 { "detail": "Conflict" }`.

---

### TC-ERROR-006: 422 (detail is array) falls back to generic toast

**Action**:
1. Edit First name; click Save

**Observation 1 — Generic toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is an array, not a string)

**Observation 2 — Form preserved**:
1. Form stays editable

**API mock**: PATCH → `422 { "detail": [{ "loc": ["body", "first_name"], "msg": "str type expected", "type": "type_error.str" }] }`.

---

### TC-ERROR-007: 500 on PATCH shows toast and preserves form

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast**:
1. Toast title equals `Internal server error`

**Observation 2 — Form preserved**:
1. Form stays dirty + editable; Save re-enables

**API mock**: PATCH → `500 { "detail": "Internal server error" }`.

---

### TC-ERROR-008: External user atom update reseeds the form

**Preconditions**: Form has been edited (dirty).

**Action**:
1. Trigger an external update to `useAuthStore.user` (e.g. via fixture)

**Observation 1 — Form reseeds**:
1. Form values are re-seeded from the new user (no crash)
2. ⚠ Typing user may lose unsaved edits — document current behaviour

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fprofile`

---

### TC-NAV-002: Expired token redirects to login

**Preconditions**: Expired `tone_access_token`.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Redirect + cleanup**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fprofile`
2. Expired cookie is cleared

---

### TC-NAV-003: Legacy /user-settings redirects to /settings/profile

**Action**:
1. Visit `/user-settings`

**Observation 1 — Redirect**:
1. URL becomes `/settings/profile`
2. The Profile page renders

---

### TC-NAV-004: Legacy /user-settings without auth redirects to login with profile redirect

**Preconditions**: No auth cookie.

**Action**:
1. Visit `/user-settings`

**Observation 1 — Redirect target**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fprofile` (post-redirect target preserved)

---

### TC-NAV-005: After successful save, sidebar / top bar reflect new name

**Preconditions**: Signed in.

**Action**:
1. Edit First name to `Updated`
2. Save
3. Click sidebar `Members`

**Observation 1 — Updated name elsewhere**:
1. URL becomes `/settings/members`
2. The account swatch / top bar shows `Updated` as the first name

---

### TC-NAV-006: Browser back after save does not prompt

**Preconditions**: Just saved successfully.

**Action**:
1. Press browser Back

**Observation 1 — Plain navigation**:
1. Navigation proceeds without an unsaved-changes prompt (form was reset post-save)

---

### TC-NAV-007: Browser back with unsaved edits navigates without prompt

**Preconditions**: Form is dirty.

**Action**:
1. Press browser Back

**Observation 1 — No warning today**:
1. Navigation proceeds (⚠ unverified — no warning today)

---

### TC-LOADING-001: Slow save disables button with Saving state

**Action**:
1. Edit First name
2. Click Save against a delayed (~3500 ms) backend

**Observation 1 — Loading**:
1. The Save button text becomes `Saving...`
2. The Save button has `disabled` throughout
3. Clicking Save multiple times records exactly one `PATCH /user/me`

**Observation 2 — Success after resolve**:
1. After ~3500 ms the success toast appears
2. Save button re-disables (form reset)

**API mock**: PATCH → 200 delayed by 3500 ms.

---

### TC-EDGE-001: Network failure on save preserves form

**Action**:
1. Edit First name; click Save

**Observation 1 — Toast + form dirty**:
1. Toast title equals `Something went wrong. Please try again.`
2. Form stays dirty

**API mock**: `await route.abort('failed')`.

---

### TC-EDGE-002: Save can be retried after network recovery

**Action**:
1. Edit First name; click Save (first attempt fails with network error)
2. Click Save again (second attempt succeeds)

**Observation 1 — First attempt fails**:
1. Error toast appears
2. Form stays dirty

**Observation 2 — Second attempt succeeds**:
1. PATCH fires and 200s
2. Success toast `Profile updated` appears

---

### TC-EDGE-003: Avatar image fails to load → fallback to initials

**Preconditions**: Avatar URL points to a 404 or blocked URL.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Fallback**:
1. The avatar `<img>` `onerror` triggers
2. The avatar falls back to gradient + initials

---

### TC-EDGE-004: Save while previous PATCH in flight cannot enqueue a second

**Action**:
1. Edit First name; click Save against a delayed backend
2. Click Save again before the first resolves

**Observation 1 — Single request**:
1. Exactly one `PATCH /user/me` is recorded
2. The button is disabled between clicks

---

### TC-EDGE-005: User atom emit resets the form

**Action**:
1. Visit `/settings/profile`
2. Trigger an external auth atom update

**Observation 1 — Form reseeds**:
1. `useEffect([user, reset])` re-seeds the form fields
2. ⚠ Typing during this update may lose edits

---

### TC-EDGE-006: XSS attempt in first name is escaped on render

**Action**:
1. Edit First name to `<script>alert(1)</script>`
2. Click Save

**Observation 1 — Escaped render**:
1. The PATCH body contains the literal string
2. The sidebar / swatch render the literal text
3. `window.alert` is not invoked

---

### TC-EDGE-007: javascript: URL avatar falls back to initials safely

**Action**:
1. Edit Avatar URL to `javascript:alert(1)`
2. Click Save

**Observation 1 — Zod accepts (`.url()` allows scheme)**:
1. The PATCH body contains the literal URL

**Observation 2 — Browser refuses**:
1. The `<img>` refuses to load it; preview falls back to initials
2. No script executes

---

### TC-EDGE-008: Toast stacking is prevented across rapid saves

**Action**:
1. Edit First name; click Save
2. While the first PATCH is in flight, click Save several more times

**Observation 1 — Single toast**:
1. Only one success toast appears
2. The button is disabled between submits

---

### TC-EDGE-009: Mobile viewport collapses two-column layout

**Preconditions**: Viewport < `lg`.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Stacked layout**:
1. Account card stacks above Profile form
2. Same form-state behaviour applies (dirty / save disabled logic identical)

---

### TC-EDGE-010: Email at exactly persisted email length is shown verbatim

**Preconditions**: User email is at the maximum length the backend persists.

**Action**:
1. Visit `/settings/profile`

**Observation 1 — Email rendered**:
1. The email input value equals the persisted email verbatim
2. No truncation marker is present in the input

---

### TC-A11Y-001: Form inputs have associated labels

**Action**:
1. Visit `/settings/profile`
2. Inspect First name, Last name, Avatar URL inputs

**Observation 1 — Programmatic labels**:
1. Each input has either a `<label>` with `htmlFor` matching its `id`, or `aria-label`

---

### TC-A11Y-002: Read-only fields announce disabled state

**Action**:
1. Visit `/settings/profile`
2. Tab focus through to Email and Role inputs

**Observation 1 — Disabled announced**:
1. Email and Role inputs have the `disabled` attribute
2. Both have a Lock icon
3. Keyboard focus either skips or announces "disabled"

---

### TC-A11Y-003: Inline error message is announced

**Action**:
1. Visit `/settings/profile`
2. Trigger an inline Zod error on a required field

**Observation 1 — ARIA**:
1. The inline error element has `role="alert"` or `aria-live="polite"`

---

### TC-A11Y-004: Tab order through Identity section

**Action**:
1. Visit `/settings/profile`
2. Focus First name and Tab repeatedly

**Observation 1 — Order**:
1. Focus moves First name → Last name → Avatar URL → Save changes

---

### TC-A11Y-005: Enter on a focused input submits the form

**Action**:
1. Visit `/settings/profile`
2. Fill valid values
3. Press Enter while focused inside any input

**Observation 1 — Submit fires**:
1. Exactly one `PATCH /user/me` is recorded

---

### TC-A11Y-006: Disabled Save button is reachable but inert

**Preconditions**: Form not dirty.

**Action**:
1. Tab focus onto the Save button
2. Press Enter (or Space)

**Observation 1 — Inert**:
1. Save button is reachable via keyboard
2. Pressing Enter / Space records zero `PATCH /user/me` requests

---

### TC-A11Y-007: Loading state announced via visible text

**Action**:
1. Click Save against a slow backend

**Observation 1 — Accessible name changes**:
1. The button's accessible name becomes `Saving...`
2. The button has `disabled` (screen reader announces "disabled")

---

### TC-A11Y-008: Avatar preview has alt text

**Action**:
1. Visit `/settings/profile` with a valid avatar URL

**Observation 1 — alt attribute**:
1. The avatar `<img>` has an `alt` describing whose avatar it shows

---

### TC-FULL-001: Lifecycle — edit profile → save → reload → revert → save

**Preconditions**: Signed-in test user.

**Action**:
1. Visit `/settings/profile`; record original `first_name`, `last_name`, `avatar_url`
2. Edit all three fields to test values
3. Click Save and wait for `Profile updated` toast
4. Reload the page
5. Assert the new values are still present
6. Restore original values (try/finally)
7. Click Save again

**Observation 1 — First save succeeds**:
1. `PATCH /user/me` is recorded with the new values
2. Success toast appears
3. Form `isDirty` resets

**Observation 2 — Auth atom reflects update**:
1. The sidebar / top bar show the new name immediately

**Observation 3 — Persistence on reload**:
1. After reload the form fields show the new values

**Observation 4 — Revert succeeds**:
1. Second `PATCH /user/me` is recorded with original values
2. Success toast appears

**Cleanup** (`try/finally`):
1. Restore original profile values via direct API call if the second save fails

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above)

- [x] Unauthenticated access → middleware redirect — see TC-NAV-001
- [x] Empty first/last name on submit → inline Zod error — see TC-VALIDATE-001, TC-VALIDATE-002
- [x] Invalid avatar URL → inline error + preview falls back — see TC-VALIDATE-004
- [x] Avatar URL empty allowed — see TC-VALIDATE-006
- [x] Avatar image fails to load → fallback to initials — see TC-EDGE-003
- [x] Form not dirty → Save disabled — see TC-VALIDATE-007
- [x] Network/API error on save → handleApiError toast — see TC-EDGE-001
- [x] Submit while previous in flight → button disabled — see TC-EDGE-004
- [x] Reset on user prop change — see TC-EDGE-005
- [x] Avatar URL whitespace trimmed — see TC-HAPPY-005
- [x] Avatar URL `javascript:` scheme — see TC-EDGE-007
- [x] XSS in name escaped on render — see TC-EDGE-006
- [x] Toast stacking prevented — see TC-EDGE-008
- [x] Mobile viewport stacks columns — see TC-EDGE-009
- [x] Unicode + emoji name round-trips — see TC-HAPPY-008
- [x] Avatar URL at 512 boundary accepted — see TC-HAPPY-006
- [x] Avatar URL >512 rejected — see TC-VALIDATE-005
- [x] First name whitespace-only — see TC-VALIDATE-008
- [x] First name leading/trailing whitespace trimmed — see TC-HAPPY-007

---

## Business Rules

- Email and role are out of scope for self-service edits. Role changes are handled by org owners/admins on `/settings/members`.
- Avatar URL is stored verbatim — no upload, no CDN proxy. Users paste a URL to a hosted image.
- First/last name length is capped at 100 each (Zod). Avatar URL is capped at 512.
- Successful save updates global auth state immediately so other pages reflect the new identity without a refetch.
- The verified badge is read-only and driven by `user.is_verified`.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Form inputs have associated labels — see TC-A11Y-001
- [x] Read-only fields announce disabled state — see TC-A11Y-002
- [x] Inline errors announced via `role="alert"` / aria-live — see TC-A11Y-003
- [x] Tab order through Identity section — see TC-A11Y-004
- [x] Enter on focused input submits form — see TC-A11Y-005
- [x] Disabled Save button reachable but inert — see TC-A11Y-006
- [x] Loading state announced via visible text — see TC-A11Y-007
- [x] Avatar preview has alt text — see TC-A11Y-008
