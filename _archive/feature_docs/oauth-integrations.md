# OAuth Integrations — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified — needs human review)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

An **OAuth Integration** is a per-organization connection to an external 3rd-party service (currently Google Calendar and Google Sheets) that the Tone platform can call on behalf of an end user. Each connection lives in the `oauth_connections` table and carries an encrypted access/refresh token pair plus public metadata (the granted email, scope string, expiry epoch). Connections are referenced by downstream features — [[tools]] (`tools.oauth_connection_id`), [[agents]] MCP servers (`mcp_servers.oauth_connection_id`, `agent_mcp_servers.oauth_connection_id`) — so that at call-time a tool / agent can mint a valid Google access token and hit the relevant Google API.

The flow is standard 3-legged OAuth 2.0 Authorization Code: the frontend hits `/oauth/{provider}/authorize` to obtain a Google consent URL, the user grants scopes, Google redirects to `/oauth/{provider}/callback` with a code, the backend exchanges the code for tokens, persists them encrypted, and redirects back to the frontend's `/integrations` page with `?status=success`.

- **Target users**: org admins / agent owners (wire up Google access so calendar / sheets tools become usable) and end users in the org.
- **Problem solved**: gives tools and MCP servers a single, multi-tenant place to obtain valid Google credentials at runtime, with automatic refresh — without each tool re-implementing token storage or scope handling.

## 2. User stories & use cases

- As an **agent owner**, I want to connect my Google Calendar so my voice agent can book meetings via a calendar tool.
- As an **agent owner**, I want to connect Google Sheets so the agent can log call outcomes into a spreadsheet during the call.
- As a user, I want to see which OAuth services my workspace has connected (and the email they were connected with) so I can confirm the right account is in use.
- As a user, I want to disconnect an integration that's no longer needed (revoke storage of its tokens) without breaking the rest of my workspace.
- As a user, I want to **reconnect** the same provider with the same identity and have the platform replace stale tokens in place — not create a duplicate row.
- As a developer wiring a tool, I want to call `OAuthService.get_valid_access_token(provider)` and trust it returns a non-expired access token (refreshing via Google if needed) so I never deal with expiry math myself.

Typical flow: User → `/integrations` → "Available providers" → clicks **Connect** on the Google Calendar tile → frontend calls `GET /oauth/google_calendar/authorize` → redirects to Google consent → Google redirects to backend callback → backend stores tokens → backend redirects to `/integrations?provider=google_calendar&status=success` → frontend shows toast "google calendar connected successfully" and refetches the connections list.

## 3. Functional requirements

- **3-legged OAuth Authorization Code flow** per provider, with `access_type=offline` and `prompt=consent` always passed so Google returns a refresh token even on re-consent.
- **Connection listing** for the caller's org via two endpoints:
  - `GET /oauth/connections` — array; optional `provider` query filter; **scoped to `claims.user_id`** (only connections the calling user created).
  - `POST /oauth/list` — array; optional `provider_slug` in body; **no `user_id` filter applied from the controller** — returns every connection in the org regardless of who created it. ⚠ Inconsistent scoping versus `GET /oauth/connections`.
- **Per-provider lookup**: `GET /oauth/connection?provider=...` returns the most-recently-updated connection for that provider in the org and includes a `connected: bool` flag for the UI to render a connected / not-connected state.
- **Disconnect**: `DELETE /oauth/disconnect?connection_id=<uuid>` hard-deletes the row. ⚠ No org-scope check on the connection — see edge cases.
- **Provider catalogue**: `GET /oauth/providers` returns the bare list of supported provider slugs from `OAUTH_PROVIDERS` in `core/services/oauth_providers.py`.
- **Authorize**: `GET /oauth/{provider}/authorize` builds the Google consent URL and returns `{auth_url}`.
- **Callback**: `GET /oauth/{provider}/callback` exchanges the auth code for tokens, decodes the state, fetches the granted user's email from Google's `oauth2/v2/userinfo`, persists the connection (encrypted), and 307-redirects to the frontend `/integrations` page.
- **State parameter** is `"<org_id>:<user_id>:<provider>"` (colon-joined plain text, no signing, no nonce, no expiry).
- **Reconnect-in-place**: if a connection already exists for the same `(org_id, provider_slug, created_by_user_id [, user_email])`, the create path overwrites its tokens via `_apply_tokens` rather than creating a second row.
- **Automatic token refresh**: `OAuthService.get_valid_access_token_for_connection()` checks `token_expiry`; if within 60s of expiry, it POSTs `refresh_token` grant to the provider's `token_url`, persists the new access token, and returns the new value.
- **Encryption at rest**: tokens stored in the `encrypted_credentials` JSONB column via `core.utils.encryption.encrypt_json` / `decrypt_json`.

### Supported providers (from `OAUTH_PROVIDERS` in `core/services/oauth_providers.py`)

| Slug              | Auth URL                                            | Token URL                              | Scopes                                                                              |
|-------------------|-----------------------------------------------------|----------------------------------------|-------------------------------------------------------------------------------------|
| `google_calendar` | `https://accounts.google.com/o/oauth2/v2/auth`      | `https://oauth2.googleapis.com/token`  | `calendar` + `userinfo.email`                                                       |
| `google_sheets`   | `https://accounts.google.com/o/oauth2/v2/auth`      | `https://oauth2.googleapis.com/token`  | `spreadsheets` + `userinfo.email`                                                   |

Both share the same `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — there is no per-provider client id today.

### Edge cases & failure modes

- **State parameter is unsigned**: anyone who can intercept or guess a valid `(org_id, user_id, provider)` triple can craft a callback URL for an attacker-controlled Google account. ⚠ **No CSRF protection** — not implemented.
- **State parsing** uses `state.split(":")` and tuple-unpacks into 3 parts. If the state has more or fewer colons it raises `ValueError` and becomes a 400 "Invalid state parameter".
- **`DELETE /oauth/disconnect` is not org-scoped**: `OAuthService.delete_connection` fetches the row by UUID alone — there is no `organization_id == self.org_id` filter. ⚠ A user in org A can delete a connection in org B if they know the UUID.
- **`GET /oauth/connection` is not user-scoped**: returns the most-recently-updated row for the provider in the org, regardless of `created_by_user_id`. ⚠
- **`POST /oauth/list` ignores `claims.user_id`**: returns every connection in the org (no user filter), unlike `GET /oauth/connections` which filters by caller. The frontend's `OAuthConnectionGrid` uses `POST /oauth/list`. ⚠
- **Soft delete not implemented**: hard `db.delete` + `commit`. No `deleted_at` column.
- **`auth_type` is always `oauth`** in the OAuth flow path.
- **`expires_in` missing from provider response**: `token_expiry` is stored as `None` and the refresh check is skipped — would return a cached expired token forever. ⚠
- **Refresh token rotation**: handled correctly — preserves old refresh token if not returned.
- **Stored credentials cannot be decrypted**: returns 400 "Stored credentials could not be decrypted. Please reconnect." ✓
- **No refresh token**: returns 400 "Token expired and no refresh token available... Please reconnect." ✓
- **Concurrent reconnects** of the same identity race on `_apply_tokens` — last writer wins; no optimistic locking.
- **Missing OAuth credentials in env**: returns 500 "OAuth credentials not configured for {provider}".
- **Userinfo lookup is best-effort**: wrapped in `try / except: pass`. `user_email` may be `null` on the saved connection.
- **Postman collection drift**: example bodies use legacy flat shape (numeric `"id": 1`, top-level `provider`/`user_email`/`scopes`) — but the actual response is `{id: uuid, provider_slug, label, auth_type, public_metadata: {...}, ...}`. ⚠

## 4. Non-functional requirements

- **Multi-tenancy**: ⚠ **Partially enforced.** List paths use `BaseService.query` (org-filtered). But `get_connection(connection_id)` and therefore `delete_connection` bypass the helper.
- **RBAC**: ⚠ **Not enforced.** Any org member can connect/disconnect.
- **CSRF on state parameter**: ⚠ **Not implemented.** State is plain text, not signed.
- **Secrets at rest**: ✓ `encrypted_credentials` JSONB is AES-encrypted.
- **Token refresh**: ✓ Implemented synchronously inside `get_valid_access_token_for_connection`. No background job.
- **Audit logging**: ⚠ Not implemented on connect or disconnect.
- **EE / Core parity**: EE controller is a **near-verbatim copy** of Core. ⚠ Drift risk.
- **Observability**: no metrics, no structured logs around connect / refresh failures.

## 5. Test cases (as-built)

⚠ **No dedicated test file exists** for OAuth integrations under `tests/`. The cases below are the locked-in behaviors implied by the controller + service.

```
TEST: list_providers
  WHEN  GET /oauth/providers
  THEN  200; body == {"providers": ["google_calendar", "google_sheets"]}

TEST: authorize_unsupported_provider
  WHEN  GET /oauth/foobar/authorize
  THEN  400; detail "Unsupported provider: foobar"

TEST: authorize_missing_client_credentials
  GIVEN GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET empty
  WHEN  GET /oauth/google_calendar/authorize
  THEN  500; detail "OAuth credentials not configured for google_calendar"

TEST: authorize_happy_path
  WHEN  GET /oauth/google_calendar/authorize
  THEN  200; body.auth_url contains state="<org>:<user>:google_calendar"
        and access_type=offline, prompt=consent

TEST: callback_invalid_state
  WHEN  GET /oauth/google_calendar/callback?code=abc&state=not_a_colon_triple
  THEN  400; detail "Invalid state parameter"

TEST: callback_provider_mismatch
  WHEN  GET /oauth/google_calendar/callback?code=abc&state=<org>:<user>:google_sheets
  THEN  400; detail "Provider mismatch in state"

TEST: callback_token_exchange_failed
  GIVEN Google returns non-200 on token endpoint
  THEN  400; detail starts with "Token exchange failed:"

TEST: callback_happy_path
  GIVEN Google returns {access_token, refresh_token, expires_in}
  THEN  307 redirect to <APPLICATION_URL>/integrations?provider=google_calendar&status=success
        AND oauth_connections row inserted with encrypted_credentials

TEST: reconnect_in_place
  GIVEN existing connection for (org, google_calendar, user, same_email)
  WHEN  callback completes again with new tokens
  THEN  the existing row's encrypted_credentials updated; no new row created

TEST: disconnect_happy_path
  WHEN  DELETE /oauth/disconnect?connection_id=<uuid>
  THEN  200; row hard-deleted

TEST: disconnect_cross_org   ⚠ EXPECTED TO FAIL — bug
  GIVEN connection X in org A, caller in org B
  WHEN  DELETE /oauth/disconnect?connection_id=X.id
  THEN  EXPECT 404; ACTUAL 200 (row deleted) — multi-tenancy bypass

TEST: refresh_on_expired_token
  GIVEN connection with token_expiry < now()
  THEN  POSTs refresh_token grant to Google, updates row, returns new access_token

TEST: refresh_without_refresh_token
  GIVEN expired connection with refresh_token=null
  THEN  raises 400 "Token expired and no refresh token available... Please reconnect."
```

## 6. Data model / DB schema

**Table: `oauth_connections`** (`core/models/oauth_connection.py`)

| Column                  | Type        | Null | Default               | Notes                                                              |
|-------------------------|-------------|------|-----------------------|--------------------------------------------------------------------|
| id                      | UUID        | NO   | `gen_random_uuid()`   | PK                                                                 |
| organization_id         | UUID        | NO   | —                     | Indexed; multi-tenancy boundary                                   |
| provider_slug           | VARCHAR(80) | NO   | —                     | e.g. `google_calendar`, `google_sheets`                            |
| label                   | VARCHAR(80) | YES  | —                     | Human display                                                      |
| auth_type               | VARCHAR(30) | NO   | —                     | `oauth` \| `api_key` \| `bearer` (callback hard-codes `oauth`)     |
| encrypted_credentials   | JSONB       | YES  | —                     | AES-encrypted `{access_token, refresh_token}` blob                 |
| public_metadata         | JSONB       | YES  | —                     | `{user_email, scopes, token_expiry}` — plaintext                   |
| created_by_user_id      | UUID        | NO   | —                     | FK → `users.id`                                                    |
| created_at              | TIMESTAMPTZ | NO   | `now()`               |                                                                    |
| updated_at              | TIMESTAMPTZ | NO   | `now()`               | Bumped on `_apply_tokens` reconnect                                |

**Indexes**: `ix_oauth_connections_organization_id`. No unique constraint on `(organization_id, provider_slug, created_by_user_id)` — uniqueness is enforced in application code.

**No soft delete**: there is no `deleted_at` column.

**Relationships** (FK on the child side):
- `tools.oauth_connection_id → oauth_connections.id` (`ON DELETE SET NULL`)
- `mcp_servers.oauth_connection_id → oauth_connections.id` (`ON DELETE SET NULL`)
- `agent_mcp_servers.oauth_connection_id → oauth_connections.id` (`ON DELETE SET NULL`)

⚠ **Cascade implication**: disconnecting an OAuth connection nulls the FK on all dependent tools / MCP servers. There is no UI surfacing of "this disconnect will break N tools".

## 7. API design

All endpoints under prefix `/api/v1/oauth`. Auth: JWT bearer (`require_org_member` in Core, `require_ee_org_member` in EE) — except `GET /oauth/providers` and `GET /oauth/{provider}/callback` which are unauthenticated. RBAC: ⚠ none enforced.

### Implemented

| Method | Path                                | Auth          | Purpose                                                                |
|--------|-------------------------------------|---------------|------------------------------------------------------------------------|
| GET    | `/oauth/connections`                | org member    | List caller's connections in org (user-scoped); optional `provider` filter |
| POST   | `/oauth/list`                       | org member    | List all org connections (not user-scoped ⚠); optional `provider_slug` filter |
| GET    | `/oauth/connection`                 | org member    | Most-recent connection for a provider in the org + `connected` flag    |
| DELETE | `/oauth/disconnect`                 | org member    | Hard delete by `connection_id` (not org-scoped ⚠)                     |
| GET    | `/oauth/providers`                  | none          | List supported provider slugs                                          |
| GET    | `/oauth/{provider}/authorize`       | org member    | Build Google consent URL; returns `{auth_url}`                         |
| GET    | `/oauth/{provider}/callback`        | none          | Token exchange + persist + 307 redirect                                 |

### Response shapes

`OAuthConnection.to_dict()`:
```json
{
  "id": "uuid", "provider_slug": "google_calendar", "label": "Google Calendar",
  "auth_type": "oauth",
  "public_metadata": {
    "user_email": "user@gmail.com",
    "scopes": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email",
    "token_expiry": 1748385600
  },
  "created_by_user_id": "uuid", "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}
```

### Referenced but not present

- ⚠ No `POST /oauth/{id}/test` connectivity check.
- ⚠ No explicit refresh endpoint — refresh happens server-side inside `OAuthService`.
- ⚠ No PATCH on a connection.

## 8. Backend implementation

- **Controllers**: `core/api/v1/oauth.py` (Core, `require_org_member`) and `ee/api/v1/oauth.py` (EE, `require_ee_org_member`). Near-identical; ⚠ keep them in sync.
- **Service**: `core/services/oauth_service.py` — `OAuthService(BaseService)`. CRUD + token methods + reconnect-in-place.
- **Provider registry**: `core/services/oauth_providers.py` — `OAUTH_PROVIDERS` dict.
- **Model**: `core/models/oauth_connection.py` — `OAuthConnection(OrgScopedModel)`. Override of `to_dict` ensures `encrypted_credentials` is **never** serialized. ✓
- **Encryption**: `core/utils/encryption.py` — `encrypt_json` / `decrypt_json`.
- **Token consumer**: `core/services/custom_tool_service.py` — when a tool's runtime path detects `google_calendar`, it mints a fresh Google access token before hitting Google APIs.
- **No Celery tasks**, no scheduled refresh.
- **No audit logging** on connect or disconnect. ⚠

## 9. Frontend implementation

- **Route**: `/integrations` — `frontend/src/app/(dashboard)/integrations/page.tsx`. Reads `?provider=...&status=success` from the URL (callback redirect target), shows a Sonner toast, and cleans up the URL.
- **Main component**: `frontend/src/components/settings/Integrations.tsx` — "Available providers" catalog + "Your integrations" tabs (Services / Channels).
- **Available tiles**: pressing **Connect** calls `getOAuthAuthorizeUrl(providerKey)` and then `window.location.href = url`.
- **Connection list**: `OAuthConnectionGrid` shows one card per connection with provider visual, label, granted email, and a Disconnect button.
- **State**: `frontend/src/atoms/OAuthAtom.tsx` — Jotai write-only atoms (`oauthAtom`, `fetchOAuthAtom`, `disconnectOAuthAtom`, `resetOAuthAtom`).
- **Service module**: `frontend/src/services/oauthService.ts` — `listOAuthConnections`, `getOAuthConnections`, `getOAuthConnectionByProvider`, `disconnectOAuth`, `getOAuthProviders`, `getOAuthAuthorizeUrl`.
- **Types**: `frontend/src/types/oauth.ts`.
- **Provider catalogue is hard-coded in the frontend**: `OAUTH_PROVIDERS` in `frontend/src/constants/integrations.tsx`. ⚠ Any new provider added to the backend will not appear on the catalog until the frontend constant is updated.
- **Layout mode**: no form — the OAuth flow is a redirect.

## 10. Postman collection & examples

Two collections: `postman_collection/oauth.postman_collection.json` (generated) and `postman/OAuth_API.postman_collection.json` (hand-organized). ⚠ Generated collection example bodies use legacy flat shape — should be regenerated.

### GET /api/v1/oauth/providers

```bash
curl "$BASE_URL/api/v1/oauth/providers"
```

```json
{ "providers": ["google_calendar", "google_sheets"] }
```

### GET /api/v1/oauth/google_calendar/authorize

```json
{ "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=ORG%3AUSER%3Agoogle_calendar&access_type=offline&prompt=consent" }
```

### GET /api/v1/oauth/connections

```json
[{
  "id": "550e8400-...", "provider_slug": "google_calendar", "label": "Google Calendar", "auth_type": "oauth",
  "public_metadata": {"user_email": "owner@acme.com", "scopes": "...", "token_expiry": 1748385600},
  "created_by_user_id": "11111111-...", "created_at": "2026-05-27T10:00:00+00:00", "updated_at": "2026-05-27T10:00:00+00:00"
}]
```

### GET /api/v1/oauth/connection

Connected:
```json
{ "id": "uuid", "provider_slug": "google_calendar", "...": "...", "connected": true }
```

Not connected:
```json
{ "connected": false, "provider": "google_calendar" }
```

### DELETE /api/v1/oauth/disconnect

```bash
curl -X DELETE "$BASE_URL/api/v1/oauth/disconnect?connection_id=550e8400-..."
```

```json
{ "message": "OAuth connection deleted successfully" }
```

## 11. Next steps

- [ ] ⚠ **Fix cross-org disconnect/get**: `OAuthService.get_connection` must filter by `self.org_id`. As-is, any authenticated user can delete or read any connection by UUID.
- [ ] ⚠ **Sign / store the `state` parameter**: today the state is plain `"<org>:<user>:<provider>"`. Add HMAC + nonce + TTL.
- [ ] ⚠ **Align `POST /oauth/list` scoping with `GET /oauth/connections`** — pick workspace-wide or per-user.
- [ ] ⚠ **Add audit logging** via `AuditService.log_resource_created/deleted` in the callback and disconnect paths.
- [ ] ⚠ **Add RBAC**: connect / disconnect should require admin or owner role.
- [ ] ⚠ **Surface dependent tools on disconnect**: count `tools.oauth_connection_id = X` etc. and warn/block.
- [ ] **Soft delete the connection** (add `deleted_at` column).
- [ ] **Expose a richer providers catalogue** — `GET /oauth/providers` should return display metadata so the frontend doesn't hard-code tiles.
- [ ] **Regenerate Postman examples**.
- [ ] **Add a real test suite** under `tests/` covering callback happy path, invalid state, cross-org bypass, etc.
- [ ] **Add more providers** — Gmail, Outlook, Slack, Notion, HubSpot.
- [ ] **De-duplicate EE controller**.
- [ ] **Resilience: handle missing `expires_in`** in the token response.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) `OAuthService.get_connection` and `delete_connection` are not org-scoped — cross-org read/delete by UUID is possible; (2) the OAuth `state` parameter is unsigned plaintext, no CSRF protection; (3) `POST /oauth/list` returns all org connections regardless of caller, while `GET /oauth/connections` filters by caller — inconsistent; (4) no audit logging on connect or disconnect; (5) no RBAC; (6) `DELETE /oauth/disconnect` is a hard delete (no `deleted_at` column); (7) disconnecting nulls dependent FKs with no UI warning; (8) `GET /oauth/providers` returns only slugs — frontend hard-codes display metadata; (9) Postman example responses are stale (legacy flat shape); (10) Core and EE controllers are near-duplicates that will drift; (11) no dedicated test file for OAuth flow.
