# Organizations, Members & Invites — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

An **Organization** is the multi-tenant boundary of the Tone platform — every other resource (agents, configs, calls, knowledge base, channels, tools) belongs to exactly one org via `organization_id`. This feature owns the org CRUD surface, member management (invite/accept/cancel/remove, role updates), and org-level settings. On Core deployments (`IS_MULTI_TENANT=false`) every user falls into a single `DEFAULT_ORG_ID` and seats are capped at 3; the Enterprise edition lifts the cap to the license's `seats` value and adds Firebase signup and org switching.

- **Target users**: org owners (control roster, billing tier, settings), org admins (manage members & invites), members (read-only on org metadata).
- **Problem solved**: a single place to provision tenants, gate seat counts by license, and route invites through email — without each feature having to re-implement membership.

Cross-links: [[authentication]] (signup/invite endpoints), [[users-account]] (user profile + member directory), [[oauth-integrations]] (per-org connections).

## 2. User stories & use cases

- As a new owner, I want to sign up and get an org created automatically (see [[authentication]] `/signup`).
- As an org owner, I want to invite a new teammate by email — they receive a link, click, set a password, and become a member.
- As an org owner, I want to update a member's role (`owner`, `admin`, `developer`, `observer`) without removing them.
- As an org owner, I want to remove a member from the org without deleting their user record.
- As an org admin, I want to see all pending invites and cancel or resend them.
- As an org owner, I want to view + edit org-level settings (JSONB blob — branding, defaults, etc.).
- As any user, I want to see the org I currently belong to via `GET /organization/me`.

Typical flow: Owner → Settings → Members → "Invite" button → modal with email + role → submit → backend creates `Invite` row + sends email → invitee clicks link → `/accept-invite?token=...` → backend validates → user creates password (new account) or signs in (existing) → `Member` row added → invitee redirected to dashboard.

## 3. Functional requirements

- **Org info**: `GET /organization/me` returns the org dict for the caller's current org.
- **Invitations**: `POST /organization/invite_user_to_organization` creates an `Invite` row (token + role + email), sends an email via `MailService.send_invite_email`.
- **Validation**: `GET /organization/validate_invitation?token=...` returns `{valid, email, role, organization_id, organization_name, account_exists}`.
- **Accept**: two paths:
  - `GET /organization/accept_invitation?token=...` — accepts (legacy path; assumes existing user is logged in).
  - `POST /organization/accept_invitation_with_password` — for new users; takes `{token, password, first_name, last_name}`.
- **Resend / cancel**: `POST /organization/resend_invitation` rotates token + sends email; `DELETE /organization/cancel_invitation` hard-deletes the invite.
- **Member management**: `DELETE /organization/remove_user_from_organization`, `POST /organization/update_member_role`.
- **Role catalog**: `GET /organization/roles` returns `[{role, description}]` for the 4 canonical roles: `owner`, `admin`, `developer`, `observer`.
- **Settings**: `GET /organization/settings` and `PUT /organization/settings` — opaque JSONB blob on the `organizations` row.
- **Access requests**: `GET /organization/access_requests` and `POST /organization/handle_access_request` — both currently return 501 in Core (`AuthService.handle_access_request`).
- **Seat cap**: `check_member_limit(db)` enforces Core cap of 3 members and EE license `seats`. Owner-protection: cannot remove or demote the last owner.

### Edge cases & failure modes

- **⚠ Three service methods missing from Core**: `core/api/v1/organizations.py` calls `accept_invitation`, `validate_invitation_token`, `accept_invitation_with_password` on `AuthService` — but those methods are **not defined**. The correct v2 names are `accept_invitation_by_token`, `validate_invitation_by_token`. These endpoints will 500 at runtime. The EE controller and the `/auth` router use the correct names. ⚠ Critical bug.
- **⚠ `require_admin_or_owner` is name-only**: the dependency in `core/middleware/auth.py` does not actually check `claims.role`. Every "admin-only" endpoint in this controller is wide open to any authenticated org member.
- **⚠ Invite tokens stored plaintext** in `invites.token`. See [[authentication]] §3 — verification/reset tokens are sha256-hashed but invitations are not.
- **⚠ Frontend role enum mismatch**:
  - `InviteMemberModal` offers `admin/member/viewer`.
  - `MembersTable` offers `owner/admin/member/viewer`.
  - Server `/roles` returns `owner/admin/developer/observer`.
  - Result: a member can be invited with role `member` (stored verbatim in the DB) but the server's permission helpers expect `developer`. ⚠ Permission drift.
- **⚠ Dead FE helpers in `userService.ts`**: `validateInvitation`, `acceptInvitationWithPassword` reference the broken `/organization/...` endpoints; no component imports them today.
- **⚠ Owner-protection guards are partial**: `remove_user_from_organization` and `update_member_role` block removing/demoting the last owner, but **org deletion** is not gated (and no `DELETE /organization` endpoint exists — see below).
- **Resend reuses the row**: `resend_invitation` rotates `token` + `expires_at` on the existing pending invite. Postman example showing 400 on re-resend is stale.
- **No audit logging** anywhere in this controller.
- **No Celery**: email send is synchronous via Resend SDK in the request path. ⚠ A slow SMTP backend will block the API thread.
- **Core seat cap of 3** is hard-coded in `check_member_limit`; EE reads `OrganizationLicense.seats`.
- **Owner-roster invariant**: an org can have multiple owners. Demoting the last owner returns 400. But there is no enforcement that an org must always have at least one member.
- **No `DELETE /organization`** endpoint — orgs cannot be deleted via the API today.
- **No `PATCH /organization`** for name/slug updates either.

## 4. Non-functional requirements

- **Multi-tenancy**: enforced via `claims.org_id` → `self.org_id` in `AuthService`. Cross-org reads are structurally prevented in service helpers (`_get_user_by_email`, `_membership_for`).
- **RBAC**: ⚠ **Not enforced.** `require_admin_or_owner` is a stub.
- **Performance**: lists are small (max ~100 members per org), no pagination needed.
- **Email delivery**: synchronous Resend SDK call, wrapped in `try/except`. ⚠ Quiet failure mode.
- **Observability**: no audit log, no metrics.
- **EE parity**: `ee/api/v1/organizations.py` mirrors the same routes with `require_ee_org_member`. EE also adds `switch_organization` and uses license seats.

## 5. Test cases (as-built)

⚠ **No dedicated test file** for `/organization/*` endpoints. The cases below are the locked-in behaviors.

```
TEST: get_organization_me
  GIVEN authenticated user in org A
  WHEN  GET /api/v1/organization/me
  THEN  200; body has id=A, name, slug, subscription_tier, status

TEST: invite_user_happy_path
  GIVEN authenticated owner in org A
  WHEN  POST /api/v1/organization/invite_user_to_organization
        body {"email":"new@example.com","role":"developer"}
  THEN  200; new Invite row in db; email sent via Resend

TEST: invite_user_already_member
  GIVEN x@y.com is already a member of org A
  WHEN  POST /api/v1/organization/invite_user_to_organization
  THEN  400 "User is already a member of this organization"

TEST: validate_invitation
  GIVEN pending invite for new@example.com
  WHEN  GET /api/v1/organization/validate_invitation?token=...
  THEN  ⚠ 500 — `AuthService.validate_invitation_token` does not exist on Core

TEST: accept_invitation_with_password
  GIVEN pending invite + no existing account
  WHEN  POST /api/v1/organization/accept_invitation_with_password
  THEN  ⚠ 500 — `AuthService.accept_invitation_with_password` does not exist

TEST: resend_invitation
  GIVEN pending invite
  WHEN  POST /api/v1/organization/resend_invitation?invite_id=...
  THEN  200; invite token rotated; email re-sent

TEST: cancel_invitation
  GIVEN pending invite
  WHEN  DELETE /api/v1/organization/cancel_invitation?invite_id=...
  THEN  200; invite row hard-deleted

TEST: remove_member
  GIVEN member X in org A (role=developer)
  WHEN  DELETE /api/v1/organization/remove_user_from_organization?user_id=X
  THEN  200; Member row deleted

TEST: remove_last_owner_blocked
  GIVEN org A has exactly 1 owner
  WHEN  DELETE /api/v1/organization/remove_user_from_organization?user_id=owner_id
  THEN  400 "Cannot remove the last owner"

TEST: update_member_role_demote_last_owner_blocked
  WHEN  POST /api/v1/organization/update_member_role
        body {"member_id":..., "new_role":"developer"} (only owner)
  THEN  400 "Cannot change role of the last owner"

TEST: get_roles
  WHEN  GET /api/v1/organization/roles
  THEN  200; [{role:"owner",...}, {role:"admin",...}, {role:"developer",...}, {role:"observer",...}]

TEST: settings_roundtrip
  WHEN  PUT /api/v1/organization/settings {"settings": {"brand_color": "#000"}}
  THEN  200; subsequent GET returns the same blob

TEST: access_requests_not_supported
  WHEN  GET /api/v1/organization/access_requests
  THEN  200; [] (Core stubs it as empty)
  WHEN  POST /api/v1/organization/handle_access_request
  THEN  501 "Organization access requests are not supported on the v2 auth schema"
```

## 6. Data model / DB schema

**Table: `organizations`** (`core/models/organization.py`)

| Column            | Type          | Null | Default     | Notes                                             |
|-------------------|---------------|------|-------------|---------------------------------------------------|
| id                | UUID          | NO   | `uuid4()`   | PK                                                |
| name              | VARCHAR(255)  | NO   | —           | Display                                           |
| slug              | VARCHAR(50)   | NO   | —           | Unique; URL-safe                                  |
| description       | TEXT          | YES  | —           |                                                   |
| subscription_tier | VARCHAR(50)   | NO   | `'free'`    | `free` / `pro` / `enterprise`                     |
| status            | VARCHAR(50)   | NO   | `'active'`  | `active` / `suspended` / `deleted`                |
| settings          | JSONB         | YES  | `{}`        | Opaque blob (branding, defaults)                  |
| created_at        | TIMESTAMPTZ   | NO   | `now()`     |                                                   |
| updated_at        | TIMESTAMPTZ   | NO   | `now()`     |                                                   |

**Table: `members`** — see [[authentication]] §6.

**Table: `invites`** — see [[authentication]] §6.

**Indexes**: `organizations.slug` unique. `members.user_id`, `members.organization_id`. `invites.organization_id`, `invites.email`, `invites.token`.

**Migration notes**: standard pattern.

## 7. API design

All endpoints under prefix `/api/v1/organization`. Auth: JWT bearer (`require_org_member`). RBAC: ⚠ stubbed.

| Method | Path                                              | Purpose                                              |
|--------|---------------------------------------------------|------------------------------------------------------|
| GET    | `/organization/me`                                | Current org for caller                               |
| POST   | `/organization/invite_user_to_organization`       | Create invite + send email                           |
| GET    | `/organization/accept_invitation`                 | Legacy accept (logged-in user) ⚠ broken on Core      |
| GET    | `/organization/validate_invitation`               | Inspect invite by token ⚠ broken on Core             |
| POST   | `/organization/accept_invitation_with_password`   | Accept + create account ⚠ broken on Core             |
| DELETE | `/organization/cancel_invitation`                 | Cancel pending invite                                |
| POST   | `/organization/resend_invitation`                 | Rotate token + resend email                          |
| DELETE | `/organization/remove_user_from_organization`     | Remove member from org                               |
| POST   | `/organization/update_member_role`                | Change a member's role                               |
| GET    | `/organization/settings`                          | Read org settings JSONB                              |
| PUT    | `/organization/settings`                          | Update org settings JSONB                            |
| GET    | `/organization/access_requests`                   | Empty array on Core                                  |
| POST   | `/organization/handle_access_request`             | 501 on Core                                          |
| GET    | `/organization/roles`                             | List role catalog                                    |

### Referenced but not present

- ⚠ No `DELETE /organization` — orgs cannot be deleted.
- ⚠ No `PATCH /organization` — org name/slug/tier cannot be updated.
- ⚠ No `POST /organization/transfer_ownership` — must manually update roles.

## 8. Backend implementation

- **Controller**: `core/api/v1/organizations.py` — 14 endpoints. ⚠ Three call non-existent `AuthService` methods.
- **EE Controller**: `ee/api/v1/organizations.py` — mirrors with `require_ee_org_member`; uses correct method names.
- **Service**: `core/services/auth_service.py` owns most logic. Methods:
  - `invite_user_to_organization`, `validate_invitation_by_token`, `accept_invitation_by_token`, `cancel_invitation`, `resend_invitation`
  - `remove_user_from_organization`, `update_member_role`, `get_roles_by_scope`
  - `get_organization_me`, `get_organization_settings`, `update_organization_settings`
- **Email**: `core/services/email_service.MailService.send_invite_email` (Resend SDK, synchronous).
- **Seat enforcement**: `check_member_limit(db)` middleware/helper called before invite/accept.
- **No audit logging.**
- **No Celery / background tasks** — emails are synchronous.

## 9. Frontend implementation

- **Routes**:
  - `/organizations` — `frontend/src/app/(dashboard)/organizations/page.tsx` (org switcher / list, may be EE-only).
  - `/members` — `frontend/src/app/(dashboard)/members/page.tsx` — directory + invite controls.
  - Accept link target: `/accept-invite?token=...` (in `(auth)` group — see [[authentication]] §9).
- **Components**:
  - `InviteMemberModal.tsx` — email + role select. ⚠ Hard-codes `admin/member/viewer` enum (drifts from backend's `owner/admin/developer/observer`).
  - `MembersTable.tsx` — list members + actions (edit role, remove). ⚠ Same enum drift.
  - `InvitationsTable.tsx` — list pending invites + actions (resend, cancel).
- **API service**: `frontend/src/services/organizationService.ts` — wrappers for all 14 endpoints.
- **State**: Jotai atoms for members list, invitations list, current org.
- **Toast / errors**: `showToast.success` / `handleApiError`.

## 10. Postman collection & examples

`postman_collection/organizations.postman_collection.json`.

### GET /api/v1/organization/me

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/organization/me"
```

```json
{
  "id": "uuid", "name": "Acme", "slug": "acme",
  "description": null, "subscription_tier": "free", "status": "active",
  "settings": {}, "created_at": "...", "updated_at": "..."
}
```

### POST /api/v1/organization/invite_user_to_organization

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","role":"developer","name":"New User"}' \
  "$BASE_URL/api/v1/organization/invite_user_to_organization"
```

```json
{
  "id": "uuid", "organization_id": "uuid", "email": "new@example.com",
  "name": "New User", "role": "developer", "status": "pending",
  "invited_by": "uuid", "expires_at": "2026-06-03T10:00:00+00:00",
  "accepted_at": null, "created_at": "2026-05-27T10:00:00+00:00"
}
```

### POST /api/v1/organization/update_member_role

```json
{"member_id": "uuid", "new_role": "admin"}
```

### GET /api/v1/organization/roles

```json
[
  {"role": "owner", "description": "Full access to organization"},
  {"role": "admin", "description": "Administrative access"},
  {"role": "developer", "description": "Standard developer access"},
  {"role": "observer", "description": "Read-only access"}
]
```

### PUT /api/v1/organization/settings

```json
{"settings": {"brand_color": "#3366CC", "default_voice": "elevenlabs_aria"}}
```

## 11. Next steps

- [ ] ⚠ **Fix the 3 broken Core endpoints**: `accept_invitation`, `validate_invitation_token`, `accept_invitation_with_password` in `core/api/v1/organizations.py` call non-existent service methods. Either rename to `*_by_token` (matches v2) or add the missing methods.
- [ ] ⚠ **Implement actual `require_admin_or_owner`** in `core/middleware/auth.py`. It is currently a name-only stub.
- [ ] ⚠ **Hash invite tokens** (sha256 like verification/reset). See [[authentication]] §11.
- [ ] ⚠ **Unify role enum**: server returns `owner/admin/developer/observer`; FE modals offer `admin/member/viewer`. Pick one set and update FE constants.
- [ ] ⚠ **Move email send off the request path** to a Celery / RQ background job to remove the SMTP latency from invite/accept.
- [ ] ⚠ **Add audit logging** for invite/accept/cancel/remove/role-change.
- [ ] ⚠ **Delete dead FE helpers** in `userService.ts` (`validateInvitation`, `acceptInvitationWithPassword`).
- [ ] Add `PATCH /organization` for name/slug/tier updates.
- [ ] Add `DELETE /organization` (soft delete; cascade to all org resources).
- [ ] Add tests under `tests/test_organizations.py`.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) Three Core endpoints (`accept_invitation`, `validate_invitation_token`, `accept_invitation_with_password`) call non-existent `AuthService` methods — they 500 at runtime; (2) `require_admin_or_owner` middleware is a name-only stub — admin-only endpoints are wide open; (3) Invitation tokens stored plaintext while verification/reset tokens are sha256-hashed; (4) Role enum drift: server `owner/admin/developer/observer`, FE `admin/member/viewer`; (5) Dead FE helpers in `userService.ts`; (6) Owner-protection guards exist for remove/role-change but not for org delete (and no delete endpoint exists); (7) Email send is synchronous via Resend in the request path; (8) No audit logging anywhere; (9) Core caps seats at 3, EE uses license `seats`; (10) Access-request endpoints stubbed (501) on Core.
