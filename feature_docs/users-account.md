# Users & Account Settings — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

The **Users & Account Settings** feature owns the user identity surface beyond auth flows: the authenticated user's profile (`GET /me`, `PATCH /me`), and two list endpoints that enumerate org members and pending invites (`POST /get_all_users_for_organization`, `POST /get_all_invited_users_for_organization`). It is a thin layer on top of `AuthService` — most of the heavy logic lives in [[authentication]] and [[organizations-members]]; this surface exists so the frontend can render the "User Settings" page and the members directory without going through the auth router.

- **Target users**: every authenticated user (everyone has a `/me` endpoint), org admins/owners (who list members), and operators (who see pending invites).
- **Problem solved**: separates "what the caller can do to *their own* profile" from "what they can do to *the org*" — the routes here are user-scoped reads/writes, not org admin actions.

Cross-links: [[authentication]] (signup/login mint the JWT that drives `claims.user_id`), [[organizations-members]] (members directory + roles + invites).

## 2. User stories & use cases

- As a **logged-in user**, I want to see my own profile (`first_name`, `last_name`, `avatar_url`, `email`, role) so I can confirm who I'm signed in as.
- As a **logged-in user**, I want to update my display name and avatar from the User Settings page without going through an admin.
- As an **org admin**, I want to list all members of my organization (with role + status + join date) so I can manage who has access.
- As an **org admin**, I want to list pending invites so I can resend or cancel them.
- As an **org-member frontend**, I want the members directory to render as a flat list — no pagination needed since most orgs have ≤ 50 members.

Typical flow: User logs in → sidebar → User Settings → `/user-settings` page mounts → `GET /user/me` fires → form fields populate → user edits name → `PATCH /user/me` → toast "Profile updated".

## 3. Functional requirements

- **`GET /user/me`** returns the caller's full user dict via `AuthService.get_user_me(claims.user_id)`. Includes `id`, `email`, `first_name`, `last_name`, `avatar_url`, `role`, `is_active`, `is_verified`, `auth_provider`, `last_login_at`, `created_at`, `updated_at`, `organization_id`. Sensitive fields (`password_hash`, `auth_provider_id`) are stripped by `User.to_dict()`.
- **`PATCH /user/me`** updates profile fields. Only fields in `AuthService.UPDATABLE_PROFILE_FIELDS = ("first_name", "last_name", "avatar_url")` are persisted — others are silently dropped.
- **`POST /user/get_all_users_for_organization`** returns every member of the caller's org as a flat list. Each row joins `members` to `users` and adds compatibility aliases (`member_id`, `user_id`, `username`, `status`, `role`, `is_default`, `joined_at`) for the frontend's `OrganizationMemberApi` type.
- **`POST /user/get_all_invited_users_for_organization`** returns pending invites (`status="pending"`) for the org as a flat list. Each row includes a `member_id` alias for the frontend's `InvitationsTable` type.
- **In-memory pagination**: list endpoints accept a `ListRequest` body (`page`, `page_size`, `search`, `sort_by`) and slice the Python list in `apply_list_request`. ⚠ No SQL `LIMIT/OFFSET` — full table scan, fine for small orgs.

### Edge cases & failure modes

- **`UPDATABLE_PROFILE_FIELDS` whitelist drops unknown fields**: ⚠ The frontend's `UserUpdate` schema accepts `phone_number` and `profile` (legacy fields), but `update_user_me` only persists `first_name`, `last_name`, `avatar_url`. Other fields silently no-op — no error, no warning.
- **`avatar_url` can never be cleared**: `update_user_me` does `if field in data and data[field] is not None: setattr(...)`. Passing `avatar_url: null` is a no-op, so users cannot remove their avatar via this endpoint. ⚠
- **`require_org_member` only checks `claims.user_id != ""`** — it does not verify actual org membership. Any valid JWT bypasses the gate. ⚠ See [[authentication]] §4.
- **In Core mode, `get_jwt_claims` overrides `claims.org_id`** with `settings.DEFAULT_ORG_ID` regardless of what was issued in the JWT. ⚠ Means `org_id` in the access token is essentially decorative on Core deployments.
- **Postman collection drift**: the list endpoints are documented as `GET` in `postman_collection/users.postman_collection.json`, but the actual implementation is `POST` with a `ListRequest` body. ⚠
- **No audit logging**: profile updates and member-list reads do not emit audit events.
- **No dedicated pytest suite** for `/user/*` — coverage is incidental via [[authentication]] tests.
- **`PATCH /me` does not return updated user**: response is the updated dict shape, but if the request body is empty, the endpoint is a no-op (`200 OK` with unchanged user).
- **Cross-org leak via `get_all_users_for_organization`**: defends against unauthenticated callers (401) but does NOT defend against a user belonging to multiple orgs — `self.org_id` is set from the JWT, so the caller sees the org they were last authenticated as.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `self.org_id` in `AuthService`. List endpoints filter by `Member.organization_id == target_org`.
- **AuthN**: `Depends(require_org_member)` on every route. Bearer JWT required. No API-key path.
- **RBAC**: ⚠ **Not enforced.** Any authenticated org member can list all other members and all pending invites. There is no `require_admin_or_owner` gate on the list endpoints.
- **Performance**:
  - List endpoints load the full member/invite set into memory and slice in Python. Fine for orgs ≤ 200 members; degrades linearly.
  - No DB-level ordering — sort happens in Python.
- **Observability**: no metrics, no structured logging.
- **EE parity**: `ee/api/v1/users.py` (if present) mirrors all four endpoints with `require_ee_org_member`. Same service.

## 5. Test cases (as-built)

⚠ **No dedicated test file** exists for `/user/*` endpoints. Coverage is incidental.

```
TEST: get_me_authenticated
  GIVEN authenticated user x@y.com in org A
  WHEN  GET /api/v1/user/me
  THEN  200; body has id, email="x@y.com", role, organization_id=A

TEST: get_me_unauthenticated
  WHEN  GET /api/v1/user/me without bearer token
  THEN  401

TEST: patch_me_first_name
  WHEN  PATCH /api/v1/user/me {"first_name": "Ada"}
  THEN  200; user.first_name == "Ada"; updated_at advances

TEST: patch_me_unknown_field_dropped
  WHEN  PATCH /api/v1/user/me {"phone_number": "+15551234567"}
  THEN  200; user.phone_number NOT set (whitelist drops it silently) ⚠

TEST: patch_me_clear_avatar_noop
  WHEN  PATCH /api/v1/user/me {"avatar_url": null}
  THEN  200; user.avatar_url unchanged (null is treated as omitted) ⚠

TEST: get_all_users_for_organization
  GIVEN org A has 3 active members + 1 inactive
  WHEN  POST /api/v1/user/get_all_users_for_organization {}
  THEN  200; items.length == 4; each row has member_id, user_id, username, status, role, is_default, joined_at

TEST: get_all_invited_users_for_organization
  GIVEN org A has 2 pending invites + 1 accepted
  WHEN  POST /api/v1/user/get_all_invited_users_for_organization {}
  THEN  200; items.length == 2; each row has member_id (alias for invite id)

TEST: cross_org_isolation
  GIVEN user in org A
  WHEN  POST /api/v1/user/get_all_users_for_organization
  THEN  rows from org B never appear
```

## 6. Data model / DB schema

**This feature does not own any tables.** It reads/writes:

- `users` — see [[authentication]] §6 for the full schema.
- `members` — see [[authentication]] §6 / [[organizations-members]] §6.
- `invites` — see [[authentication]] §6 / [[organizations-members]] §6.

**Updatable profile fields** (whitelist in `AuthService.UPDATABLE_PROFILE_FIELDS`):
- `first_name` (VARCHAR 100)
- `last_name` (VARCHAR 100)
- `avatar_url` (VARCHAR 512)

⚠ The `users` table has many more columns (`preferences`, `notification_settings`, etc.) that this endpoint does NOT expose for editing.

## 7. API design

All endpoints under prefix `/api/v1/user`. Auth: JWT bearer (`require_org_member`). RBAC: ⚠ none enforced.

| Method | Path                                                  | Purpose                                                |
|--------|-------------------------------------------------------|--------------------------------------------------------|
| GET    | `/user/me`                                            | Get caller's user dict                                 |
| PATCH  | `/user/me`                                            | Update caller's profile (whitelisted fields only)      |
| POST   | `/user/get_all_users_for_organization`                | List all members of caller's org (flat array)          |
| POST   | `/user/get_all_invited_users_for_organization`        | List pending invites for caller's org (flat array)     |

### Response shapes

**`GET /me`** — `User.to_dict()`:
```json
{
  "id": "uuid", "organization_id": "uuid",
  "email": "x@y.com", "first_name": "Ada", "last_name": "Lovelace",
  "avatar_url": "https://...", "role": "owner",
  "is_active": true, "is_verified": true, "auth_provider": "local",
  "last_login_at": "2026-05-27T10:00:00+00:00",
  "created_at": "2026-05-20T10:00:00+00:00",
  "updated_at": "2026-05-27T10:00:00+00:00"
}
```

**`POST /get_all_users_for_organization`** — array of rows, each:
```json
{
  "id": "uuid", "organization_id": "uuid", "email": "x@y.com", "first_name": "Ada", "last_name": "Lovelace",
  "avatar_url": null, "role": "owner", "is_active": true, "is_verified": true, "auth_provider": "local",
  "last_login_at": "...", "created_at": "...", "updated_at": "...",
  "member_id": "uuid", "user_id": "uuid", "username": "Ada Lovelace",
  "status": "active", "is_default": true, "joined_at": "2026-05-20T10:00:00+00:00"
}
```

**`POST /get_all_invited_users_for_organization`** — array of invite rows, each:
```json
{
  "id": "uuid", "organization_id": "uuid", "email": "new@user.com", "name": "New User",
  "role": "developer", "status": "pending", "invited_by": "uuid",
  "expires_at": "2026-06-03T10:00:00+00:00", "accepted_at": null,
  "created_at": "2026-05-27T10:00:00+00:00",
  "member_id": "uuid"
}
```

### Referenced but not present

- ⚠ No `DELETE /user/me` (account deletion).
- ⚠ No `POST /user/me/avatar` (avatar upload endpoint — frontend would need to upload to R2 directly and pass the URL via `PATCH /me`).
- ⚠ No `GET /user/{id}` (look up another user by ID — the only access is via member listing).
- ⚠ No `PATCH /user/me/password` (password change is at [[authentication]] `/auth/change-password`).

## 8. Backend implementation

- **Controller**: `core/api/v1/users.py` — 4 endpoints, thin wrappers calling `AuthService` methods.
- **Service**: `core/services/auth_service.py` — `AuthService` owns user logic. Methods used:
  - `get_user_me(user_id)` — returns `User.to_dict()`.
  - `update_user_me(user_id, data)` — applies the `UPDATABLE_PROFILE_FIELDS` whitelist.
  - `get_all_users_for_organization(org_id)` — joins `Member` to `User`, returns enriched array with FE-compat aliases.
  - `get_all_invited_users_for_organization(org_id)` — filters `Invite` to `status="pending"`, returns array.
- **EE controller**: `ee/api/v1/users.py` (if present) — mirrors with `require_ee_org_member`.
- **Pagination helper**: `apply_list_request(items, body)` — slices the Python list (no SQL `LIMIT/OFFSET`).
- **No dedicated test file**.

## 9. Frontend implementation

- **Routes** (under `frontend/src/app/(dashboard)/`):
  - `/user-settings` — `user-settings/page.tsx` — single-page profile form (not tabbed).
  - `/members` — see [[organizations-members]] for the directory page (consumes the same `/user/get_all_users_for_organization` endpoint).
- **Components** (`frontend/src/components/user-settings/`):
  - Profile form using `react-hook-form` + Zod validation.
  - Avatar uploader (if implemented — upload to R2 then send URL to `PATCH /me`).
- **API service**: `frontend/src/services/userService.ts` — wrappers for `getUserMe`, `updateUserMe`, `getAllUsersForOrganization`, `getAllInvitedUsersForOrganization`.
- **State**: Jotai atoms in `frontend/src/atoms/UserSettingsAtom.tsx` — `userProfileAtom`, `updateProfileAtom` (write-only async atom).
- **Validation**: Zod schemas in `frontend/src/schemas/auth.ts` or `frontend/src/schemas/user.ts`.
- **Form layout**: single page (not modal/drawer). Only ~3 editable fields.
- **Toast / errors**: `showToast.success` / `handleApiError`.

## 10. Postman collection & examples

`postman_collection/users.postman_collection.json`. ⚠ Documents list endpoints as `GET` but they are `POST`.

### GET /api/v1/user/me

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/user/me"
```

```json
{
  "id": "uuid", "organization_id": "uuid", "email": "owner@acme.com",
  "first_name": "Ada", "last_name": "Lovelace", "avatar_url": null,
  "role": "owner", "is_active": true, "is_verified": true,
  "auth_provider": "local", "last_login_at": "2026-05-27T10:00:00+00:00",
  "created_at": "2026-05-20T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}
```

### PATCH /api/v1/user/me

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"first_name": "Ada", "last_name": "Lovelace"}' \
  "$BASE_URL/api/v1/user/me"
```

Response: same shape as `GET /me`.

### POST /api/v1/user/get_all_users_for_organization

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{}' "$BASE_URL/api/v1/user/get_all_users_for_organization"
```

Returns: array of enriched member rows (see §7).

### POST /api/v1/user/get_all_invited_users_for_organization

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{}' "$BASE_URL/api/v1/user/get_all_invited_users_for_organization"
```

Returns: array of pending invite rows (see §7).

## 11. Next steps

- [ ] ⚠ **Add a `DELETE /user/me`** account-deletion endpoint (soft delete + tombstone).
- [ ] ⚠ **Allow clearing `avatar_url`**: change the whitelist check from `is not None` to `field in data` so `null` clears the field.
- [ ] ⚠ **Add `phone_number`, `preferences`, `notification_settings`** to the editable whitelist (or document they're admin-only).
- [ ] ⚠ **Fix Postman collection** to mark list endpoints as `POST` not `GET`.
- [ ] ⚠ **Add RBAC**: list-members endpoint should probably require admin/owner role (or document that all members can see the directory).
- [ ] ⚠ **Add SQL-level pagination** on the list endpoints — switch from in-memory slice to `LIMIT/OFFSET`.
- [ ] ⚠ **Add audit logging** for `PATCH /me` (profile changes are non-trivial security events).
- [ ] **Add a dedicated test file** `tests/test_users.py` covering §5.
- [ ] **Avatar upload endpoint**: add `POST /user/me/avatar` (multipart) that uploads to R2 and updates `avatar_url` in one call.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `UPDATABLE_PROFILE_FIELDS` whitelist silently drops `phone_number`/`profile`/etc.; (2) `avatar_url` cannot be cleared (null is treated as omitted); (3) `require_org_member` only checks JWT presence, not actual membership; (4) Core overrides `claims.org_id` with `DEFAULT_ORG_ID` — JWT org claim is decorative; (5) Postman collection lists endpoints as `GET` but they are `POST`; (6) no audit logging; (7) no dedicated pytest suite; (8) in-memory pagination — doesn't scale.
