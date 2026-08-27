# Authentication — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

**Authentication** is the identity layer for the Tone platform. It covers email/password signup with optional organization creation, login, refresh-token rotation, password reset, email verification, and invitation-based onboarding. The Core edition runs on a JWT-based stateless model (`HS256` access + refresh tokens) and a single default organization fallback; the Enterprise edition adds Firebase signup, org-switching, and richer multi-tenant flows.

- **Target users**: every user of the platform — owners signing up new orgs, members accepting invitations, developers logging into dashboards, and integrations refreshing access tokens.
- **Problem solved**: a self-contained, stateless auth surface that works for both the single-tenant Core (`IS_MULTI_TENANT=false`, everyone falls into `DEFAULT_ORG_ID`) and the multi-tenant Enterprise edition, without requiring an external identity provider.

## 2. User stories & use cases

- As a **new owner**, I want to sign up with an organization name so I get an account, an org, and an owner role in one call.
- As a **new user without an organization**, I want to sign up and be auto-attached to the default org so I can start using the product immediately on Core deployments.
- As an **invited member**, I want to click the invite link and either log in (if I already have an account) or set a password (if I don't) — never go through a separate signup form.
- As a **returning user**, I want my access token to expire quickly but my refresh token to keep me logged in for weeks.
- As a **forgotten-password user**, I want a one-time email link that lets me set a new password without knowing the old one.
- As a **forgetful user**, I want to resend the verification email if the first one expires.

Typical flows:

1. **Signup**: `POST /signup` → user + org + owner-member rows created → verification email sent → access/refresh tokens returned. User must verify before login works (`is_verified` check in `login_v2`).
2. **Invitation**: org admin invites email → `POST /accept-invitation` with token → if account exists, just attach `Member`; if not, require `password` and create the user + mark verified.
3. **Login**: `POST /login` → `verify_password` → `last_login_at` updated → access + refresh issued.
4. **Refresh**: `POST /refresh` with refresh token → new access + refresh issued.

## 3. Functional requirements

- **Email/password signup** (`POST /signup`). If `organization_name` is provided, a new `Organization` is created with `subscription_tier="free"`, `status="active"`, and the user is given `role="owner"`. Otherwise the user is attached to `settings.DEFAULT_ORG_ID` (created lazily by `ensure_default_organization`) with `role="developer"`.
- **Email verification** is required before login — `verify_email_by_token` flips `User.is_verified=True` and marks the `EmailRequest` row `consumed`.
- **Login** (`POST /login`) returns access + refresh tokens, current user, current organization, and role, via `_build_auth_tokens`. The `member.role` overrides `user.role` in the payload.
- **Refresh** (`POST /refresh`) decodes the refresh JWT, fetches the user + default member, and issues a fresh pair.
- **Logout** (`POST /logout`) is a **client-side no-op** — it returns `{"message": "Logged out"}` without invalidating anything. ⚠ Server-side blacklist is a TODO (see comment in `auth_service.logout`).
- **Password reset** is a two-step flow: `POST /forgot-password` issues a 1-hour token (stored as a sha256 hash in `EmailRequest` with `purpose="reset"`), then `POST /reset-password` consumes it and updates the password.
- **Change password** (`POST /change-password`) sets a new password for the authenticated user. ⚠ It does **not** verify the current password — anyone holding an access token can rotate the credential.
- **Invitation flow** (`GET /validate-invitation`, `POST /accept-invitation`) — invite tokens live on the `invites` table directly (no hashing) with a 7-day TTL. The accept endpoint optionally accepts a JWT and asserts the calling user's email matches the invite.
- **Email tokens are hashed** at rest — only the sha256 hash is stored in `EmailRequest.token_hash`. Raw tokens are sent over the wire once and never stored.
- **Legacy aliases** are kept: `GET /resend_verification_email` and `GET /forget-password` (query-string forms) for older clients. Modern POST equivalents do the same work.
- **`GET /me`** returns `{user, organization}` for the authenticated principal.

### Edge cases & failure modes

- `signup` with an already-registered email → `400 "Email already registered"`. No email enumeration via timing — but the response is fast either way.
- `signup` response **includes `email_verification_token`** as a top-level field (see `_build_auth_tokens(..., email_verification_token=raw_token)`). ⚠ This leaks the raw verification token in the HTTP response — anyone with access to the response body bypasses the email loop. Either intentional (Core dev convenience) or a security gap. Verify intent.
- `signup` returns access + refresh tokens **before** email verification, but `login_v2` blocks unverified users with `401 "Please verify your email before logging in"`. The freshly issued tokens still work for endpoints that don't re-check verification — ⚠ surface area for inconsistent behavior.
- `forgot_password` and `resend_verification_email` are **asymmetric** about enumeration: forgot-password always returns the generic "if the email exists" message, but `resend_verification_email` raises `400 "Email is already verified"` for verified users. ⚠ This leaks whether a verified account exists for that address.
- `reset_password_by_token` enforces `len(new_password) >= 8`. `change_password_for_user` enforces the same. ⚠ Signup itself does **not** validate password length — clients can sign up with `"a"`.
- `change_password` accepts `body["new_password"]` only — no `current_password` field. See note above.
- `accept_invitation` with a different logged-in user → `403 "This invitation was sent to a different email address."` But invitation tokens are stored **plaintext** in the DB; anyone with read access to `invites.token` can hijack pending invites. ⚠
- Refresh tokens are stateless and **not rotated/blacklisted** — a leaked refresh JWT remains valid until `expires_at`. ⚠
- The signup `organization_name` field is also accepted via `org_name` or `profile.org_name` — three aliases for the same field, kept for legacy clients.
- `_slugify` clips org slugs to 50 chars and appends `secrets.token_hex(3)` on collision. Empty/non-alnum names degrade to `"org"`.
- Removing the last owner is blocked (`400 "Cannot remove the last owner"`), but only in `remove_user_from_organization`/`update_member_role`. ⚠ Hard-deleting a user via direct SQL bypasses this.
- `last_login_ip` column exists on `users` but **is never populated** anywhere in the codebase. ⚠ Either dead column or planned-but-unfinished feature.
- The legacy `forget_password_legacy` (`GET /forget-password`) calls `forgot_password` directly — same behavior, different verb.
- Email sending is best-effort: `try/except Exception` around `MailService().send_*_email`. Token is stored even if the email fails to deliver. ⚠ Quiet failure mode for users who never receive the email.

## 4. Non-functional requirements

- **Stateless JWT**: HS256, signed with `settings.JWT_SECRET`. Defaults to a development secret if unset — ⚠ verify production deployments override it.
- **Token lifetimes**: access ≈ 24h, refresh ≈ 30d (whatever `JWTManager.access_token_expire_seconds()` returns). No `jti` claim → cannot revoke individually.
- **Multi-tenancy**: Core single-tenants everyone into `DEFAULT_ORG_ID` when `IS_MULTI_TENANT=false`. EE allows true multi-org with `switch_organization`. The `_membership_for(user)` helper resolves "current org" as `is_default=True` first, falling back to any membership.
- **RBAC**: ⚠ The Core controller depends on `get_jwt_claims` only. No `require_role`/`require_permission` calls. Any authenticated user can hit any non-public endpoint. Role data is **issued** in the JWT and exposed via `claims.role`, but enforcement is the caller's responsibility.
- **Password hashing**: `core/utils/security.hash_password` / `verify_password` — assume bcrypt-equivalent. Verify before claiming compliance.
- **Token storage**: verification + reset tokens stored as sha256 in `EmailRequest`. Invitation tokens stored plaintext in `invites.token`. ⚠ Inconsistent.
- **Observability**: No structured audit logging on auth events — only Python `logger.exception` on email delivery failures. ⚠ No "login" / "password reset" trail.
- **Rate limiting**: ⚠ **None** at the controller layer. Brute-force login, signup spam, and forgot-password floods are not throttled in code. Rely on upstream proxy/WAF.

## 5. Test cases (as-built)

`test-cases/test_auth.py` exists and patches `ee.api.v1.auth.EEAuthService` — ⚠ it is wired to the EE service surface and **does not exercise the Core router**. There is no `test_auth_core.py`. Treat the cases below as the locked-in spec inferred from `auth_service.py`.

```
TEST: signup_creates_user_and_org
  GIVEN no user with email "x@y.com"
  WHEN  POST /signup {"email":"x@y.com","password":"hunter22","first_name":"X","organization_name":"Acme"}
  THEN  201; response has user.id, organization.id, role="owner",
        access_token, refresh_token, email_verification_token (⚠ leak)

TEST: signup_without_org_attaches_default
  GIVEN IS_MULTI_TENANT=false
  WHEN  POST /signup with no organization_name
  THEN  201; user.organization_id == DEFAULT_ORG_ID, role="developer"

TEST: signup_duplicate_email
  GIVEN x@y.com exists
  WHEN  POST /signup with same email
  THEN  400 "Email already registered"

TEST: login_unverified
  GIVEN x@y.com exists with is_verified=False
  WHEN  POST /login
  THEN  401 "Please verify your email before logging in"

TEST: login_wrong_password
  WHEN  POST /login with bad password
  THEN  401 "Invalid email or password"

TEST: refresh_token_roundtrip
  GIVEN valid refresh_token
  WHEN  POST /refresh
  THEN  200; new access + refresh issued

TEST: refresh_with_invalid_token
  WHEN  POST /refresh {"refresh_token": "tampered"}
  THEN  401

TEST: verify_email_consumes_token
  GIVEN unverified user with pending EmailRequest(purpose="verification")
  WHEN  POST /verify-email {"token": raw}
  THEN  200; user.is_verified=true; subsequent /verify-email with same token → 400

TEST: forgot_password_unknown_email
  WHEN  POST /forgot-password {"email":"nope@x.com"}
  THEN  200 generic message (no enumeration)

TEST: reset_password_short
  WHEN  POST /reset-password with new_password="abc"
  THEN  400 "Password must be at least 8 characters"

TEST: change_password_no_current
  GIVEN authenticated user
  WHEN  POST /change-password {"new_password":"newpass12"}
  THEN  200 — current password is NOT required (⚠)

TEST: validate_invitation
  GIVEN pending invite for x@y.com
  WHEN  GET /validate-invitation?token=...
  THEN  200; {valid, email, role, organization_id, organization_name, account_exists}

TEST: accept_invitation_new_account
  GIVEN pending invite, no user with that email
  WHEN  POST /accept-invitation {"token","password","first_name"}
  THEN  200; user + member created, invite.status="accepted", tokens returned

TEST: accept_invitation_wrong_user
  GIVEN authenticated user whose email != invite.email
  WHEN  POST /accept-invitation
  THEN  403 "This invitation was sent to a different email address."
```

## 6. Data model / DB schema

**Table: `users`** (`core/models/user.py`)

| Column            | Type          | Null | Default       | Notes                                          |
|-------------------|---------------|------|---------------|------------------------------------------------|
| id                | UUID          | NO   | `uuid4()`     | PK                                             |
| organization_id   | UUID          | YES  | —             | FK → `organizations.id` ON DELETE SET NULL     |
| email             | VARCHAR(255)  | NO   | —             | Unique, indexed                                |
| password_hash     | VARCHAR(255)  | YES  | —             | Null for SSO-only users                        |
| first_name        | VARCHAR(100)  | YES  | —             |                                                |
| last_name         | VARCHAR(100)  | YES  | —             |                                                |
| avatar_url        | VARCHAR(512)  | YES  | —             |                                                |
| role              | VARCHAR(50)   | NO   | `'developer'` | Mirrored on `Member.role`; member wins in JWT |
| is_active         | BOOL          | NO   | `true`        |                                                |
| is_verified       | BOOL          | NO   | `false`       |                                                |
| auth_provider     | VARCHAR(50)   | NO   | `'local'`     |                                                |
| auth_provider_id  | VARCHAR(255)  | YES  | —             |                                                |
| last_login_at     | TIMESTAMPTZ   | YES  | —             |                                                |
| last_login_ip     | VARCHAR(45)   | YES  | —             | ⚠ Never written by Core                         |
| preferences       | JSONB         | YES  | `{}`          |                                                |
| notification_settings | JSONB     | YES  | `{}`          |                                                |
| created_at        | TIMESTAMPTZ   | NO   | `now()`       |                                                |
| updated_at        | TIMESTAMPTZ   | NO   | `now()`       | onupdate=`now()`                              |
| deleted_at        | TIMESTAMPTZ   | YES  | —             | Soft delete                                    |

**Table: `members`** (`core/models/member.py`)

| Column          | Type        | Null | Default    | Notes                                       |
|-----------------|-------------|------|------------|---------------------------------------------|
| id              | UUID        | NO   | `uuid4()`  | PK                                          |
| user_id         | UUID        | NO   | —          | FK → users.id                               |
| organization_id | UUID        | NO   | —          | FK → organizations.id                       |
| role            | VARCHAR(50) | NO   | —          | `owner` / `admin` / `developer` / `observer`|
| is_default      | BOOL        | NO   | `false`    | The membership picked when no org context   |
| joined_at       | TIMESTAMPTZ | NO   | `now()`    |                                             |

**Table: `invites`** (`core/models/invite.py`)

| Column          | Type         | Null | Default    | Notes                                |
|-----------------|--------------|------|------------|--------------------------------------|
| id              | UUID         | NO   | `uuid4()`  | PK                                   |
| organization_id | UUID         | NO   | —          | FK → organizations.id, indexed       |
| email           | VARCHAR(255) | NO   | —          | Indexed                              |
| name            | VARCHAR(200) | YES  | —          |                                      |
| role            | VARCHAR(50)  | NO   | `'developer'`|                                    |
| token           | VARCHAR(255) | NO   | —          | Unique, indexed; ⚠ stored plaintext  |
| invited_by      | UUID         | NO   | —          | FK → users.id                        |
| status          | VARCHAR(50)  | NO   | `'pending'`| `pending` / `accepted` / `cancelled` |
| expires_at      | TIMESTAMPTZ  | NO   | —          | TTL 7 days from create               |
| accepted_at     | TIMESTAMPTZ  | YES  | —          |                                      |
| created_at      | TIMESTAMPTZ  | NO   | `now()`    |                                      |

**Table: `email_requests`** (`core/models/email_request.py`)

Holds verification + reset tokens via the `purpose` discriminator. `token_hash` is sha256 of the raw token. `delivery_status` ∈ `{pending, sent, consumed, expired}`. Indexed on `to_email`.

**Indexes** declared on column level:
- `users.email` unique; `users.organization_id` indexed
- `invites.organization_id`, `invites.email`, `invites.token` indexed
- `email_requests.to_email` indexed

## 7. API design

All endpoints under prefix `/api/v1/auth` (router prefix from `main.py:101`). Auth: most endpoints are public; `change-password`, `me` require a valid access token; `accept-invitation` accepts an **optional** token (different code path when present vs absent). RBAC: none enforced.

### Implemented (Core)

| Method | Path                              | Auth     | Purpose                                       |
|--------|-----------------------------------|----------|-----------------------------------------------|
| POST   | `/auth/signup`                    | public   | Create user (+ optional org) + send verification email |
| POST   | `/auth/login`                     | public   | Email/password login → access + refresh       |
| POST   | `/auth/refresh`                   | public   | Refresh access token                          |
| POST   | `/auth/logout`                    | public   | Client-side no-op (⚠ stateless)               |
| POST   | `/auth/verify-email`              | public   | Consume verification token                    |
| POST   | `/auth/resend-verification`       | public   | Resend verification email                     |
| POST   | `/auth/forgot-password`           | public   | Send password-reset email                     |
| POST   | `/auth/reset-password`            | public   | Consume reset token + set new password        |
| POST   | `/auth/change-password`           | bearer   | Change password for authenticated user        |
| GET    | `/auth/me`                        | bearer   | `{user, organization}` for current principal  |
| GET    | `/auth/validate-invitation`       | public   | Inspect invitation by token                   |
| POST   | `/auth/accept-invitation`         | optional | Accept invite (create or attach user)         |
| GET    | `/auth/resend_verification_email` | public   | Legacy alias for resend-verification          |
| GET    | `/auth/forget-password`           | public   | Legacy alias for forgot-password              |

### EE-only additions

EE mounts its own router (`ee/api/v1/auth.py` if present) ahead of Core. The EE service typically adds:
- `POST /auth/check_organization_exists`
- `POST /auth/signup_with_firebase` (Core stubs this as `501 Not Implemented`)
- `POST /auth/verify_user_email` (legacy code-based verification — shimmed to `verify_email_by_token`)
- `POST /auth/switch_organization`
- `POST /auth/acceptForgotPassword` (legacy alias — Core service shim returns same behavior)

⚠ Verify EE router contents — Core does not import EE files.

### Response shape (login/signup/refresh)

```json
{
  "access_token": "eyJhbGciOi…",
  "refresh_token": "eyJhbGciOi…",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid", "email": "x@y.com", "organization_id": "uuid",
    "first_name": "X", "last_name": "Y", "role": "owner",
    "is_verified": true, "auth_provider": "local"
  },
  "organization": { "id": "uuid", "name": "Acme", "slug": "acme", … },
  "role": "owner"
}
```

Signup additionally returns `"email_verification_token": "raw"` at the top level (⚠ token leak — see §3).

## 8. Backend implementation

- **Controller**: `core/api/v1/auth.py` — thin: validates body, delegates to `AuthService` methods.
- **Service**: `core/services/auth_service.py` — owns the v2 schema logic. Helpers: `_get_user_by_email`, `_membership_for`, `_build_auth_tokens`, `_store_token`, `_consume_token`, `ensure_default_organization`, `_slugify`.
- **JWT**: `core/middleware/auth.py` — `JWTManager` (issue/decode), `JWTClaims` dataclass, `get_jwt_claims` / `get_optional_jwt_claims` dependencies. Tokens carry `user_id`, `email`, `org_id`, `role`, `exp`.
- **Email**: `core/services/email_service.py:MailService` — `send_signup_email`, `send_forgot_password_email`, `send_invite_email`. Best-effort: failures are logged but swallowed.
- **Token storage**:
  - Verification + reset → `EmailRequest` rows, sha256-hashed, `purpose` discriminator.
  - Invitation → plaintext `Invite.token` (⚠ inconsistency).
- **Password hashing**: `core/utils/security.hash_password` / `verify_password`.
- **Models touched**: `User`, `Member`, `Invite`, `Organization`, `EmailRequest`.
- **No Celery / background tasks** — email sending happens inline in the request handler.

EE: `ee/api/v1/auth.py` + `ee/services/auth_service.py` (if present) add Firebase signup and multi-org switching. Core is the fallback; EE overrides via earlier mount in `main.py:87-98`.

## 9. Frontend implementation

- **Routes** under `frontend/src/app/(auth)/`:
  - `login/page.tsx`
  - `signup/page.tsx`
  - `forgot-password/page.tsx`
  - `reset-password/page.tsx`
  - `verify-email/page.tsx`
  - `accept-invite/page.tsx`
- **Services**:
  - `frontend/src/services/auth/` (and possibly `frontend/src/lib/api/auth.ts`) — axios wrappers calling the endpoints above. The legacy `auth/helper.tsx` may still reference dead `/org/create_tenants` endpoints — ⚠ verify before relying.
- **State**: Jotai atoms for the current user + access token, plus a token-refresh interceptor on the axios instance.
- **Form schemas**: zod schemas in `frontend/src/schemas/auth.ts` (if present). ⚠ Verify password-policy parity with backend — backend enforces `len >= 8` only at reset/change, not at signup.
- **Layout**: `frontend/src/app/(auth)/layout.tsx` provides the unauthenticated chrome (logo, marketing copy, etc.).
- **Toast / errors**: standard project toast utility (`showToast.error` / `success`).

## 10. Postman collection & examples

`postman_collection/auth.postman_collection.json` covers the legacy + modern surface. ⚠ Some requests likely target pre-v2 shapes (`username`, `profile.org_name`); the modern endpoints accept these via the compat shims in `signup_v2`/`signup`.

### POST /api/v1/auth/signup

```json
{
  "email": "owner@acme.com",
  "password": "hunter22!",
  "first_name": "Ada",
  "last_name": "Lovelace",
  "organization_name": "Acme"
}
```

Response 201 — shape under §7, plus `email_verification_token`.

```bash
curl -X POST "$BASE_URL/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@y.com","password":"hunter22!","first_name":"X","organization_name":"Acme"}'
```

### POST /api/v1/auth/login

```json
{ "email": "owner@acme.com", "password": "hunter22!" }
```

Response 200 — full token + user + org payload.

### POST /api/v1/auth/refresh

```json
{ "refresh_token": "eyJhbGciOi…" }
```

### POST /api/v1/auth/verify-email

```json
{ "token": "raw-token-from-email" }
```

Response 200 `{"message":"Email verified successfully","user":{…}}`.

### POST /api/v1/auth/forgot-password

```json
{ "email": "owner@acme.com" }
```

Always returns `{"message":"If the email exists, you will receive a password reset link"}`.

### POST /api/v1/auth/reset-password

```json
{ "token": "raw-reset-token", "new_password": "newpass12" }
```

### POST /api/v1/auth/accept-invitation

```json
{ "token": "raw-invite-token", "password": "setupNow1", "first_name": "Lin", "last_name": "Mo" }
```

If the invite email already belongs to a user with `password_hash`, the `password` field is ignored and a Member row is added; otherwise the user is created or completed.

## 11. Next steps

This feature is **already built**. Use the items below when modifying it or when filling in the gaps flagged above.

- [ ] ⚠ **Stop leaking `email_verification_token` in the signup response.** Either the field is a dev-only convenience and should be gated by `settings.ENV != "production"`, or removed entirely.
- [ ] ⚠ **Require current password in `change-password`.** The endpoint should accept `{current_password, new_password}` and verify the current one before rotating.
- [ ] ⚠ **Add rate limiting** to `/login`, `/signup`, `/forgot-password`, `/resend-verification`. Brute-force is currently uncapped at the app layer.
- [ ] ⚠ **Make enumeration responses symmetric.** Return the generic `"If the email exists…"` from `resend_verification_email` even when the user is already verified.
- [ ] ⚠ **Hash invite tokens** the same way verification/reset tokens are hashed (`sha256`). Store only `token_hash`; send the raw token via email.
- [ ] ⚠ **Add a refresh-token blacklist / rotation table** so logout can actually invalidate sessions. Alternative: switch to opaque refresh tokens with a `sessions` table.
- [ ] ⚠ **Wire `last_login_ip`** in `login_v2` (`User.last_login_ip = request.client.host` with proxy header awareness — see [[organizations-members]] for the same pattern).
- [ ] ⚠ **Add audit logging** for signup, login, password reset, password change, invitation accept/cancel. No trail exists today.
- [ ] ⚠ **Validate password length at signup** (currently only enforced at reset/change). Unify the policy in one helper.
- [ ] ⚠ **Verify `test-cases/test_auth.py` actually exercises Core.** Today it patches `ee.api.v1.auth.EEAuthService` — likely dead for Core. Add a parallel `test_auth_core.py`.
- [ ] ⚠ **Decide the future of legacy aliases** (`GET /resend_verification_email`, `GET /forget-password`). Deprecate and remove if no clients depend on them.
- [ ] Refresh the Postman collection to match v2 request bodies (drop `username`, `profile.org_name`).
- [ ] Document role semantics with [[organizations-members]] — the four canonical roles are listed in `auth_service.get_roles_by_scope`: owner / admin / developer / observer.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `email_verification_token` leak in signup response; (2) `change-password` does not require current password; (3) no rate limiting on auth endpoints; (4) invitation tokens stored plaintext; (5) refresh tokens are stateless and cannot be revoked; (6) `last_login_ip` column exists but is never populated; (7) test suite targets EE service surface, leaving Core uncovered.
