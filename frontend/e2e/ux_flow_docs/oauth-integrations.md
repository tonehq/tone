# Feature Doc: OAuth Integrations (Services)

Feature documentation for the Services tab and Available Providers catalog on
the Integrations page. Used by `/generate-tests oauth-integrations` (or
`--docs e2e/ux_flow_docs/oauth-integrations.md`) to ensure all user cases are covered.

OAuth Integrations are per-organization connections to third-party services
(Google Calendar, Google Sheets, custom OAuth 2.0 client-credentials, custom
Bearer tokens) that downstream tools and MCP servers can use at call-time.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/settings/integrations` (Services tab + Available Providers catalog above the tabs). `/integrations` redirects here.
- **Component**: `src/components/settings/Integrations.tsx`
- **Sub-components**:
  - `src/components/integrations/available-integrations-catalog.tsx`
  - `src/components/integrations/oauth-connection-grid.tsx`
  - `src/components/integrations/oauth-connection-card.tsx`
  - `src/components/integrations/oauth-connection-grid-skeleton.tsx`
  - `src/components/integrations/custom-credential-modal.tsx`
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fsettings%2Fintegrations` without `tone_access_token` cookie)

---

## User Stories

### US-1: Connect a Google service via OAuth

**As an** agent owner, **I want to** connect Google Calendar with my Google
account, **so that** my voice agent can book meetings during a call.

**Acceptance criteria**:

- [ ] "Available providers" section shows a Google category with Google Calendar and Google Sheets tiles
- [ ] Tile shows provider icon, name, description, "OAuth" badge + scope count
- [ ] Clicking "Connect" calls `GET /oauth/{provider}/authorize` and assigns `window.location.href` to the returned URL
- [ ] After Google consent, callback redirects to `/settings/integrations?provider=google_calendar&status=success`
- [ ] On return, the page detects the query params and shows a success toast "Google Calendar connected successfully"
- [ ] `OAuthConnectionGrid` refetches; a new card appears in the Services tab

### US-2: View connected services

**As a** user, **I want to** see which OAuth services my workspace has
connected, **so that** I can confirm the right account is in use.

**Acceptance criteria**:

- [ ] Services tab has the heading "Services" with a Plug icon and count badge
- [ ] Loading state renders `OAuthConnectionGridSkeleton` with 2 placeholder cards
- [ ] Each card shows: provider name, "Connected" green-dot badge, user email (with Mail icon), "Refreshed X time ago" (Clock icon), scope pills (first 3 + "+N more"), `ScopeStatus` icon (green/yellow/red), and a "Disconnect" button (Unplug icon)
- [ ] MCP connections with `status === 'pending'` are filtered out of the list
- [ ] Empty state shows "No services connected yet — pick one from 'Browse providers' above." + "Connect another service" button

### US-3: Reconnect to refresh tokens or grant new scopes

**As a** user, **I want to** reconnect an existing OAuth connection without
disconnecting first, **so that** I can fix an expired token or grant missing
scopes in place.

**Acceptance criteria**:

- [ ] Clicking the `ScopeStatus` icon (when yellow/red) launches a reconnect flow
- [ ] For catalog providers: calls `GET /oauth/{provider}/authorize` again
- [ ] For MCP-bound OAuth connections: calls `POST /oauth/mcp/discover` with the server URL
- [ ] After the OAuth round-trip, the same connection row updates in place (does not create a duplicate)

### US-4: Create a custom credential

**As an** admin, **I want to** register a custom OAuth 2.0 client-credentials
or Bearer token, **so that** tools that don't have a built-in provider tile can
still authenticate.

**Acceptance criteria**:

- [ ] Top-right "Custom credential" button (KeyRound icon) opens `CustomCredentialModal`
- [ ] Modal asks for Authentication Type ("OAuth 2.0 (client credentials)" or "Bearer Token") + Credential Name
- [ ] OAuth 2.0 flow adds: Token URL, Client ID, Client Secret (password), Scope (optional)
- [ ] Bearer flow adds: Bearer Token (password)
- [ ] "Create credential" calls `POST /oauth/custom_credential`
- [ ] On success: modal closes, list refetches, toast "Custom credential created"
- [ ] New row appears in the connections list with a `custom:<name>` slug
- [ ] Custom credentials have no "Reconnect" affordance (must be recreated to rotate)

### US-5: Disconnect a service

**As a** user, **I want to** remove an integration I no longer use, **so that**
its tokens are revoked from Tone.

**Acceptance criteria**:

- [ ] "Disconnect" button on a card calls `DELETE /oauth/disconnect` with the connection id
- [ ] Card animates out (framer-motion exit)
- [ ] Toast "Account disconnected"
- [ ] No leftover entry remains in the list after refetch

### US-6: Refresh the page state

**As a** user, **I want to** trigger a refresh of both lists without reloading
the page, **so that** I can pick up changes made elsewhere.

**Acceptance criteria**:

- [ ] Top-right "Refresh" button (RefreshCw icon) refetches OAuth connections + channels
- [ ] Skeletons render during the refetch
- [ ] No state is lost (modals, tab selection, scroll position)

---

## Input Specifications

### CustomCredentialModal — OAuth 2.0 client-credentials

Source: `src/components/integrations/custom-credential-modal.tsx` lines 17-26 (`schema`) and lines 68-104 (`onFormSubmit`).

| Field             | Type     | Required (per flow)  | Validation Rules                                                                    | Exact Error Message                                                       |
| ----------------- | -------- | -------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Authentication Type | select | yes                  | Default `oauth2_client_credentials`. Toggle flips field set                         | n/a                                                                       |
| Credential Name   | text     | yes (both flows)     | `z.string().min(1)`                                                                 | "Credential name is required" (inline helperText)                          |
| Token URL         | text     | yes (OAuth 2.0)      | non-empty after trim; checked imperatively in `onFormSubmit`                        | Toast: "Token URL, Client ID and Client Secret are required for OAuth 2.0" |
| Client ID         | text     | yes (OAuth 2.0)      | non-empty after trim                                                                | Same toast as above                                                       |
| Client Secret     | password | yes (OAuth 2.0)      | non-empty after trim                                                                | Same toast as above                                                       |
| Scope             | text     | no                   | optional, trimmed, omitted if empty                                                 | n/a                                                                       |

### CustomCredentialModal — Bearer Token

| Field         | Type     | Required        | Validation Rules                                  | Exact Error Message                              |
| ------------- | -------- | --------------- | ------------------------------------------------- | ------------------------------------------------ |
| Bearer Token  | password | yes (Bearer)    | non-empty after trim                              | Toast: "Token is required for a Bearer credential" |

**Button state rules:**

- "Create credential" is **disabled** while `!formState.isValid`.
- Text flips to "Saving..." while `saving === true`.

---

## Expected Toast Messages

Source files: `src/components/integrations/oauth-connection-grid.tsx`, `src/components/integrations/custom-credential-modal.tsx`, `src/app/(dashboard)/settings/integrations/page.tsx`, `src/utils/helpers.ts`.

| Trigger                                                | Toast title                                                          | Toast description | Variant  |
| ------------------------------------------------------ | -------------------------------------------------------------------- | ----------------- | -------- |
| Callback `?status=success`                             | `<provider slug with _→space> connected successfully` (e.g. "google calendar connected successfully") | —                 | success  |
| Disconnect succeeds                                    | `Account disconnected`                                               | —                 | success  |
| Custom credential created                              | `Custom credential created`                                          | —                 | success  |
| Custom credential OAuth fields missing                 | `Token URL, Client ID and Client Secret are required for OAuth 2.0`  | —                 | error    |
| Custom credential Bearer token missing                 | `Token is required for a Bearer credential`                          | —                 | error    |
| Reconnect attempted on a `custom:` connection          | `Custom credentials cannot be reconnected — recreate the credential instead.` | —        | error    |
| Reconnect attempted on MCP connection with no `server_url` | `Cannot reconnect: this MCP connection has no stored server URL.` | —                 | error    |
| Any API error with string `detail` (via `handleApiError`) | `<detail string verbatim>` (e.g. "Unsupported provider: gmail")  | —                 | error    |
| Any API error where `detail` is not a string           | `Something went wrong. Please try again.`                            | —                 | error    |
| Callback `?status=error`                               | (no toast today) ⚠ unverified                                        | —                 | n/a      |

---

## UI Elements

| Element                       | Type        | Content / Label                                                | Behavior                                                       |
| ----------------------------- | ----------- | -------------------------------------------------------------- | -------------------------------------------------------------- |
| Available providers heading   | h2          | "Available providers" + Sparkles icon                          | Static                                                         |
| Catalog tile (Google)         | Card        | icon + name + description + "OAuth N scopes" badge + "Connect" | Click "Connect" launches OAuth authorize                       |
| Catalog tile (not configured) | Card        | "Not configured" badge + disabled button                       | Backend marked `configured: false`                             |
| Custom credential button      | Button      | "Custom credential" + KeyRound icon                            | Opens `CustomCredentialModal`                                  |
| Refresh button                | Button      | RefreshCw icon                                                 | Refetches OAuth + channel lists                                |
| Services tab                  | Tab         | "Services" + Plug icon + count badge                           | Switches the right pane to `OAuthConnectionGrid`               |
| Connection card               | Card        | provider name + "Connected" badge + email + timestamp          | Click on `ScopeStatus` → reconnect; click "Disconnect" → DELETE |
| Scope pill                    | Pill        | scope string                                                   | Up to 3 visible; "+N more" overflow indicator                  |
| Scope status icon             | Icon        | check / warning / x                                            | Color = green/yellow/red; clickable to reconnect               |
| Disconnect button             | Button      | "Disconnect" + Unplug icon                                     | Calls `disconnectOAuthAtom`                                    |
| Empty state                   | Dashed box  | "No services connected yet — pick one from 'Browse providers' above." | Includes a "Connect another service" CTA                       |
| Auth type select              | SelectInput | "OAuth 2.0 (client credentials)" / "Bearer Token"              | Required; toggles which fields render below                    |
| Credential name input         | TextInput   | "Enter credential name"                                        | Required                                                       |
| Token URL input               | TextInput   | "https://auth.example.com/oauth/token"                         | Required when OAuth 2.0 is selected                            |
| Client ID input               | TextInput   | —                                                              | Required when OAuth 2.0 is selected                            |
| Client Secret input           | TextInput (pwd) | —                                                          | Required when OAuth 2.0 is selected                            |
| Scope input                   | TextInput   | "e.g. read write (space separated, optional)"                  | Optional                                                       |
| Bearer Token input            | TextInput (pwd) | —                                                          | Required when Bearer is selected                               |
| Create credential button      | Button      | "Create credential"                                            | Submits the modal; "Creating…" while in flight                 |

---

## Navigation

| Trigger                                      | Destination                                                         | Condition                                              |
| -------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------ |
| Visit `/integrations`                        | `/settings/integrations`                                            | Redirect                                               |
| Click "Connect" on a catalog tile            | Provider OAuth consent URL (external)                               | Tile provider is `configured`                          |
| Provider OAuth callback                      | `/settings/integrations?provider=<key>&status=success` / `error`     | Backend redirect                                       |
| Click "Custom credential"                    | `CustomCredentialModal` opens                                        | Always                                                 |
| Click "Refresh"                              | Refetches both lists                                                 | Always                                                 |
| Click `ScopeStatus` icon on a card           | OAuth re-authorize flow (catalog) or MCP discover modal              | Status is yellow or red                                |
| Click "Disconnect"                           | Card animates out, connection removed                                | Always                                                 |
| Switch tab                                   | Updates `?tab=` query param                                          | Always                                                 |
| No auth cookie                               | `/auth/login?redirect=%2Fsettings%2Fintegrations`                    | `src/middleware.ts` redirect                           |

---

## API Contracts

Real payloads sourced from `/Users/thilak/Documents/Tone/postman_collection/Tone-API.postman_collection.json` (folder: `OAuth Integrations`). Frontend service contracts are in `src/services/oauthService.ts`.

| Endpoint                              | Method | Request                                                                                   | Success Response                                                | Error Response                                          |
| ------------------------------------- | ------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------- |
| `/oauth/list`                         | POST   | `{ "provider_slug": "google_calendar"\|null }`                                            | `OAuthConnection[]` (org-wide; ⚠ not user-scoped per Postman)   | `{ "detail": "..." }`                                   |
| `/oauth/catalog`                      | GET    | —                                                                                         | `{ "providers": [{ slug, name, auth_kind, configured, scopes }] }` | `{ "detail": "Failed to load provider catalog" }` (500) |
| `/oauth/{provider}/authorize`         | GET    | —                                                                                         | `{ "auth_url": "https://accounts.google.com/..." }`             | `{ "detail": "Unsupported provider: ..." }` (400)       |
| `/oauth/{provider}/callback`          | GET    | `?code=&state=`                                                                           | 307 redirect to `/settings/integrations?provider=<slug>&status=success` | 307 with `status=error` OR 400 JSON with `detail`       |
| `/oauth/disconnect?connection_id=<id>`| DELETE | —                                                                                         | `{ "message": "OAuth connection deleted successfully" }`        | `{ "detail": "OAuth connection not found" }` (404)      |
| `/oauth/mcp/discover`                 | POST   | `{ "server_url", "label?", "return_to?" }`                                                | `{ "authorization_url", "connection_id" }`                      | `{ "detail": "server_url is required" }` (400)          |
| `/oauth/custom_credential`            | POST   | OAuth 2.0: `{ name, auth_kind: "oauth2_client_credentials", token_url, client_id, client_secret, scope? }` · Bearer: `{ name, auth_kind: "bearer", token }` | 201 `OAuthConnection`                                           | `{ "detail": "name is required" }` (400)                |

### Example: `GET /oauth/catalog` — 200 OK

```json
{ "providers": [
  { "slug": "google_calendar", "name": "Google Calendar", "auth_kind": "oauth2", "configured": true, "scopes": ["https://www.googleapis.com/auth/calendar"] },
  { "slug": "google_sheets", "name": "Google Sheets", "auth_kind": "oauth2", "configured": false, "scopes": [] }
] }
```

### Example: `POST /oauth/list`

Request: `{ "provider_slug": null }`

200 OK:

```json
[{
  "id": "11111111-2222-3333-4444-555555555555",
  "provider_slug": "google_calendar",
  "label": "Google Calendar",
  "auth_type": "oauth",
  "public_metadata": { "user_email": "owner@acme.com", "scopes": "https://www.googleapis.com/auth/calendar", "token_expiry": 1748385600 },
  "created_by_user_id": "7c2f1a4e-5b9d-4c8e-9a1f-3e5b7c9d2a4f",
  "created_at": "2026-05-27T10:00:00+00:00",
  "updated_at": "2026-05-27T10:00:00+00:00"
}]
```

401: `{ "detail": "Could not validate credentials" }` · 403: `{ "detail": "User is not a member of this organization" }`

### Example: `GET /oauth/google_calendar/authorize`

200 OK: `{ "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=XXX&redirect_uri=...&response_type=code&scope=...&state=org%3Auser%3Agoogle_calendar&access_type=offline&prompt=consent" }`

400: `{ "detail": "Unsupported provider: gmail" }` · 500: `{ "detail": "OAuth credentials not configured for google_calendar" }`

### Example: `POST /oauth/custom_credential` (OAuth 2.0)

Request:

```json
{ "name": "Acme Salesforce", "auth_kind": "oauth2_client_credentials", "token_url": "https://acme.my.salesforce.com/services/oauth2/token", "client_id": "3MVG9...", "client_secret": "ABC123...", "scope": "api refresh_token" }
```

201 Created:

```json
{ "id": "99999999-aaaa-bbbb-cccc-dddddddddddd", "provider_slug": "custom", "name": "Acme Salesforce", "auth_kind": "oauth2_client_credentials", "is_active": true }
```

Bearer variant request: `{ "name": "My API Key", "auth_kind": "bearer", "token": "bearer-xyz" }` · 400: `{ "detail": "name is required" }`

### Example: `DELETE /oauth/disconnect?connection_id=<id>`

200: `{ "message": "OAuth connection deleted successfully" }` · 400: `{ "detail": "connection_id must be a valid UUID" }` · 404: `{ "detail": "OAuth connection not found" }`

### Example: `POST /oauth/mcp/discover`

Request: `{ "server_url": "https://mcp.example.com", "label": "Example MCP", "return_to": "/integrations" }`

200 OK: `{ "authorization_url": "https://mcp.example.com/oauth/authorize?client_id=...&state=...", "connection_id": "11111111-mcp1-4eee-9aaa-222222222222" }`

400: `{ "detail": "server_url is required" }`

State is held in `src/atoms/OAuthAtom.tsx`: `oauthAtom` (read), `fetchOAuthAtom`,
`disconnectOAuthAtom`, `resetOAuthAtom`.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.

---

### TC-HAPPY-001: Authenticated user lands on /settings/integrations (WF-1 / PS-1 / PS-2)

**Preconditions**:
- User has `tone_access_token` cookie

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Header and tab render**:
1. Header text reads `Integrations`
2. The Services tab is active by default

**Observation 2 — Catalog fetch fires**:
1. Exactly one `GET /oauth/catalog` request is recorded
2. The Google category section renders with a Google Calendar tile
3. Tile contains a `Connect` button and an `OAuth 1 scope` badge

**Observation 3 — Services list fetch fires**:
1. Exactly one `POST /oauth/list` request is recorded
2. The skeleton (`OAuthConnectionGridSkeleton` with 2 placeholder cards) renders during the wait
3. After resolution, one connection card with `Connected` green-dot badge, email `owner@acme.com`, and `Disconnect` button renders
4. Services tab badge shows `1`

**API mocks**: `GET /oauth/catalog` → PS-1 body; `POST /oauth/list` → PS-2 body.

---

### TC-HAPPY-002: Catalog fallback to static list while loading (WF-1 step 3)

**Preconditions**: Authenticated.

**Action**:
1. Navigate to `/settings/integrations` while `GET /oauth/catalog` is slow

**Observation 1 — Static fallback during load**:
1. Tiles fall back to the static `OAUTH_PROVIDERS` list from `src/constants/integrations`
2. Every fallback tile is treated as `configured: true`

---

### TC-HAPPY-003: Connect Google Calendar via OAuth — authorize kick-off (WF-2 / PS-3)

**Preconditions**: TC-HAPPY-001 loaded; Google Calendar tile visible.

**Action**:
1. Click `Connect` on the Google Calendar tile

**Observation 1 — Pending state**:
1. `setPendingProvider('google_calendar')` is reflected — the tile button shows `Loading...`

**Observation 2 — Authorize request fires**:
1. Exactly one `GET /oauth/google_calendar/authorize` request is recorded

**Observation 3 — Navigation to consent URL**:
1. `window.location.href` is assigned the returned `auth_url`
2. The intercepted navigation matches `https://accounts.google.com/o/oauth2/v2/auth?...`

**API mock**: `GET /oauth/google_calendar/authorize` → 200 PS-3 body.

---

### TC-HAPPY-004: OAuth callback success surfaces toast and refetches list (WF-2 steps 4–7 / PS-4)

**Preconditions**: Authenticated; stub navigation to `/settings/integrations?provider=google_calendar&status=success`.

**Action**:
1. Navigate to `/settings/integrations?provider=google_calendar&status=success`

**Observation 1 — Success toast**:
1. Toast title equals `google calendar connected successfully` (slug `_` → space)
2. Toast variant is `success`

**Observation 2 — Query params stripped**:
1. `window.history.replaceState` is invoked
2. URL becomes `/settings/integrations` (without query)

**Observation 3 — List refetch**:
1. `fetchOAuthAtom` re-runs (i.e. `POST /oauth/list` re-fires)
2. New card for `google_calendar` appears in the Services tab

---

### TC-HAPPY-005: Disconnect a service succeeds (WF-3 / PS-5)

**Preconditions**: TC-HAPPY-001 loaded; at least one connected card.

**Action**:
1. Click `Disconnect` on the card

**Observation 1 — Loading state**:
1. The button enters its loading state (`disconnectingId === id`)

**Observation 2 — Disconnect request**:
1. Exactly one `DELETE /oauth/disconnect?connection_id=<id>` request fires

**Observation 3 — Card animates out + toast**:
1. The card animates out via framer-motion exit
2. Toast title equals `Account disconnected`
3. After refetch, the row is no longer in the DOM

**API mock**: `DELETE /oauth/disconnect` → 200 `{"message":"OAuth connection deleted successfully"}`.

---

### TC-HAPPY-006: Reconnect (yellow ScopeStatus) for catalog provider (WF-4)

**Preconditions**: TC-HAPPY-001; a connection card has a yellow `ScopeStatus` icon (catalog provider).

**Action**:
1. Click the yellow `ScopeStatus` icon

**Observation 1 — Reconnect state**:
1. `setReconnectingProvider(provider_slug)` reflects in UI loading state

**Observation 2 — Authorize re-fires**:
1. `GET /oauth/{provider}/authorize` fires
2. `window.location.href` is assigned the returned `auth_url`

**Observation 3 — Row updates in place after callback**:
1. After consent callback redirect, the same connection row updates in place
2. No duplicate card is created (backend upserts on `(provider, account_email)`)

---

### TC-HAPPY-007: Reconnect MCP-bound OAuth via discovery (WF-5 / PS-8)

**Preconditions**: A connection with `provider_slug` starting with `mcp:` and a valid `public_metadata.server_url`.

**Action**:
1. Click the yellow `ScopeStatus` icon on the MCP connection

**Observation 1 — Discover request**:
1. Exactly one `POST /oauth/mcp/discover` request fires
2. Request body contains `server_url` and `label` from `public_metadata`

**Observation 2 — Navigation to MCP consent**:
1. `window.location.href` is assigned the returned `authorization_url`

**API mock**: `POST /oauth/mcp/discover` → PS-8 body.

---

### TC-HAPPY-008: Create custom OAuth 2.0 credential (WF-6 / PS-6)

**Preconditions**: TC-HAPPY-001 loaded.

**Action**:
1. Click the header `Custom credential` button
2. Auth Type is `OAuth 2.0 (client credentials)` by default
3. Fill Name `Acme Salesforce`
4. Fill Token URL `https://acme.my.salesforce.com/services/oauth2/token`
5. Fill Client ID `3MVG9...`
6. Fill Client Secret `ABC123...`
7. Fill optional Scope `api refresh_token`
8. Click `Create credential`

**Observation 1 — Modal renders correctly**:
1. Modal title reads `New Custom Credential`
2. Description reads `Configure authentication for custom API endpoints.`
3. OAuth 2.0 fields (Token URL, Client ID, Client Secret, Scope) are visible

**Observation 2 — Loading state on submit**:
1. Button text becomes `Saving...`
2. Button has the `disabled` attribute

**Observation 3 — Request payload**:
1. Exactly one `POST /oauth/custom_credential` request fires
2. Request body has `auth_kind: "oauth2_client_credentials"` with all fields populated

**Observation 4 — Success surface**:
1. Modal closes
2. Toast title equals `Custom credential created`
3. `POST /oauth/list` re-fires
4. New card appears with slug starting `custom:`
5. The new card has NO Reconnect affordance

**API mock**: `POST /oauth/custom_credential` → 201 PS-6 body.

---

### TC-HAPPY-009: Create custom Bearer credential (WF-7 / PS-7)

**Preconditions**: TC-HAPPY-001; modal opened.

**Action**:
1. Switch Auth Type to `Bearer Token`
2. Fill Name `My API Key`
3. Fill Bearer Token `bearer-token-xyz`
4. Click `Create credential`

**Observation 1 — Fields collapse**:
1. Only Credential Name + Bearer Token (password) fields are visible
2. Token URL / Client ID / Client Secret / Scope are no longer rendered

**Observation 2 — Request payload**:
1. `POST /oauth/custom_credential` request body has `auth_kind: "bearer"`

**Observation 3 — Success surface**:
1. Toast title equals `Custom credential created`

**API mock**: `POST /oauth/custom_credential` → 201 PS-7 body.

---

### TC-HAPPY-010: Empty services list shows empty-state CTA (PS-9)

**Preconditions**: Authenticated.

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Empty state copy**:
1. Dashed box reads `No services connected yet — pick one from "Browse providers" above.`
2. A `Connect another service` CTA is present

**API mock**: `POST /oauth/list` → `[]`.

---

### TC-HAPPY-011: Refresh button refetches both lists (US-6 / OAI-054)

**Preconditions**: TC-HAPPY-001 loaded; user is inside an open modal.

**Action**:
1. Click the `Refresh` button (RefreshCw icon)

**Observation 1 — Both lists refetch**:
1. `POST /oauth/list` fires again
2. The OAuth + channels lists are refetched

**Observation 2 — State is not lost**:
1. The open modal remains open
2. Form state inside the modal is intact

---

### TC-NAV-001: Unauthenticated visit redirects to login (OAI-001 / WF-8)

**Preconditions**: No `tone_access_token` cookie.

**Action**:
1. Visit `/settings/integrations`

**Observation 1 — Middleware redirect**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fintegrations`

---

### TC-NAV-002: Legacy /integrations without auth redirects to login (OAI-002)

**Preconditions**: No auth cookie.

**Action**:
1. Visit `/integrations`

**Observation 1 — Redirect to login with same post-redirect target**:
1. URL becomes `/auth/login?redirect=%2Fsettings%2Fintegrations`

---

### TC-NAV-003: Expired token redirects to login (OAI-003)

**Preconditions**: Expired `tone_access_token` cookie.

**Action**:
1. Visit `/settings/integrations`

**Observation 1 — Redirect + cleanup**:
1. URL becomes the login redirect
2. Expired cookie cleared

---

### TC-NAV-004: Member cannot create custom credential (OAI-004)

**Preconditions**: Logged-in member (non-admin).

**Action**:
1. Open the `Custom credential` modal
2. Fill required fields and click `Create credential`

**Observation 1 — Either modal opens but Save 403s, or button is hidden**:
1. If modal opens, `POST /oauth/custom_credential` returns 403 with a toast
2. OR the `Custom credential` button is hidden for the member role

---

### TC-NAV-005: Member cannot disconnect existing connection (OAI-005)

**Preconditions**: Logged-in member; existing connection card visible.

**Action**:
1. Click `Disconnect` on a card

**Observation 1 — 403 returned**:
1. Backend returns 403
2. Toast title equals `Forbidden`
3. Card remains in the list

---

### TC-NAV-006: OAuth callback success returns to page and refreshes list (OAI-050)

**Preconditions**: TC-HAPPY-003 has navigated to provider consent and consent succeeded.

**Action**:
1. Land back on `/settings/integrations?provider=google_calendar&status=success`

**Observation 1 — Final URL after stripping**:
1. URL ends `/settings/integrations` (query stripped via `history.replaceState`)

**Observation 2 — New card appears**:
1. `POST /oauth/list` re-fires
2. The new card is visible

---

### TC-NAV-007: OAuth callback error returns to page without toast (FS-15 / OAI-051 / WF-9)

**Preconditions**: User cancelled consent OR backend returned an error.

**Action**:
1. Navigate to `/settings/integrations?provider=google_calendar&status=error`

**Observation 1 — No toast today**:
1. Zero Sonner toasts appear (current behavior — only `status === 'success'` fires a toast)

**Observation 2 — No new card**:
1. No new card is added to the Services list

> ⚠ unverified — confirm there is no negative-path toast yet.

---

### TC-NAV-008: Tab switch updates query param (OAI-052)

**Action**:
1. Switch tab between Services and MCP / Knowledge Base

**Observation 1 — URL query param updates**:
1. `?tab=` query param is updated
2. The right pane swaps to the new tab

**Observation 2 — Counts persist**:
1. Tab badge counts persist across switches

---

### TC-NAV-009: Browser back after callback skips OAuth provider history (OAI-053)

**Preconditions**: User completed OAuth callback flow.

**Action**:
1. Press browser Back

**Observation 1 — Returns to upstream history entry**:
1. URL returns to the upstream history entry
2. The browser does not navigate back to the OAuth provider

---

### TC-ERROR-001: /authorize 400 (unsupported provider) (FS-1)

**Action**:
1. Click `Connect` on a tile whose slug is not backed by configured credentials

**Observation 1 — Error toast**:
1. Toast title equals `Unsupported provider: gmail`

**Observation 2 — Tile state recovers**:
1. The tile button's loading state clears

**API mock**: `GET /oauth/<slug>/authorize` → 400 `{"detail":"Unsupported provider: gmail"}`.

---

### TC-ERROR-002: /authorize 500 (credentials not configured) (FS-2)

**Action**:
1. Click `Connect` on the affected tile

**Observation 1 — Error toast**:
1. Toast title equals `OAuth credentials not configured for google_calendar`

**Observation 2 — Tile state recovers**:
1. Tile button loading clears

**API mock**: `GET /oauth/<slug>/authorize` → 500.

---

### TC-ERROR-003: Catalog fetch fails (FS-3)

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Error toast**:
1. Toast title equals `Failed to load provider catalog`

**Observation 2 — Static fallback rendered**:
1. Tiles fall back to the static `OAUTH_PROVIDERS` list
2. Page is still functional

**API mock**: `GET /oauth/catalog` → 500.

---

### TC-ERROR-004: Services list 401 unauthorized (FS-4)

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Error state**:
1. State flips to `status: "error"`
2. Toast title equals `Could not validate credentials`

**API mock**: `POST /oauth/list` → 401.

---

### TC-ERROR-005: Services list 403 forbidden (FS-5)

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Forbidden toast**:
1. Toast title equals `User is not a member of this organization`

**API mock**: `POST /oauth/list` → 403.

---

### TC-ERROR-006: Disconnect 404 — connection not found (FS-6)

**Action**:
1. Click `Disconnect` on a card

**Observation 1 — Card remains**:
1. The card is still in the DOM after the failure

**Observation 2 — Error toast + state cleanup**:
1. Toast title equals `OAuth connection not found`
2. `disconnectingId` clears via the `finally` block

**API mock**: `DELETE /oauth/disconnect` → 404.

---

### TC-ERROR-007: Disconnect 400 invalid UUID (FS-7)

**Action**:
1. Trigger Disconnect with a malformed id

**Observation 1 — Error toast**:
1. Toast title equals `connection_id must be a valid UUID`

**API mock**: `DELETE /oauth/disconnect` → 400.

---

### TC-ERROR-008: Custom credential blocked by OAuth client-side check (FS-8)

**Preconditions**: Modal open; Auth Type OAuth 2.0.

**Action**:
1. Leave Token URL blank
2. Fill the rest
3. Click `Create credential`

**Observation 1 — No network call**:
1. Zero `POST /oauth/custom_credential` requests are recorded

**Observation 2 — Error toast**:
1. Toast title equals `Token URL, Client ID and Client Secret are required for OAuth 2.0`

**Observation 3 — Modal stays open**:
1. The modal is still in the DOM

---

### TC-ERROR-009: Custom credential blocked by Bearer client-side check (FS-9)

**Preconditions**: Modal open; Auth Type Bearer.

**Action**:
1. Leave Bearer Token blank
2. Click `Create credential`

**Observation 1 — No network call**:
1. Zero `POST /oauth/custom_credential` requests fire

**Observation 2 — Error toast**:
1. Toast title equals `Token is required for a Bearer credential`

---

### TC-ERROR-010: Custom credential backend 400 (FS-10 / OAI-010)

**Preconditions**: Modal open; all required fields filled.

**Action**:
1. Click `Create credential`

**Observation 1 — Modal stays open**:
1. Modal is still in the DOM

**Observation 2 — Backend error toast**:
1. Toast title equals `name is required` (or other backend `detail`)
2. Form state is intact

**API mock**: `POST /oauth/custom_credential` → 400 `{"detail":"name is required"}`.

---

### TC-ERROR-011: Empty Credential Name (Zod) (FS-11)

**Action**:
1. Open modal
2. Leave Name blank
3. Fill other required fields

**Observation 1 — Create disabled**:
1. The `Create credential` button is `disabled` (`formState.isValid === false`)

**Observation 2 — Inline helper text**:
1. Helper text under Name reads `Credential name is required`

---

### TC-ERROR-012: Reconnect MCP — missing server_url (FS-12)

**Preconditions**: MCP connection with no `public_metadata.server_url`.

**Action**:
1. Click the yellow ScopeStatus icon

**Observation 1 — Guard toast**:
1. Toast title equals `Cannot reconnect: this MCP connection has no stored server URL.`

**Observation 2 — No API call fires**:
1. Zero `POST /oauth/mcp/discover` requests are recorded

---

### TC-ERROR-013: Reconnect for custom credential is guarded (FS-13)

**Preconditions**: Connection with `provider_slug` starting `custom:`.

**Action**:
1. Trigger `handleReconnect` (programmatically, since affordance is normally hidden)

**Observation 1 — Guard toast**:
1. Toast title equals `Custom credentials cannot be reconnected — recreate the credential instead.`

---

### TC-ERROR-014: MCP discover 400 (FS-14)

**Action**:
1. Click yellow ScopeStatus on an MCP connection
2. Backend returns 400

**Observation 1 — Error toast**:
1. Toast title equals `server_url is required`

**Observation 2 — Reconnect spinner clears**:
1. The button's loading state clears

**API mock**: `POST /oauth/mcp/discover` → 400.

---

### TC-ERROR-015: Catalog tile with configured:false is disabled (FS-16)

**Preconditions**: Catalog includes `google_sheets` with `configured: false`.

**Action**:
1. Locate the `google_sheets` tile
2. Try clicking the disabled button

**Observation 1 — Disabled button + aria-label**:
1. The button renders as `<CustomButton disabled>Not configured</CustomButton>`
2. Button has `aria-label="<name> is not configured"`

**Observation 2 — No API call fires**:
1. Zero `/authorize` requests are recorded on click

---

### TC-ERROR-016: Custom credential 401 mid-flow (OAI-011)

**Action**:
1. Fill custom credential modal and submit

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Next nav triggers login redirect**:
1. Subsequent navigation hits the middleware login redirect

**API mock**: `POST /oauth/custom_credential` → 401.

---

### TC-ERROR-017: Custom credential 403 (OAI-012)

**Action**:
1. Fill modal and submit

**Observation 1 — Toast**:
1. Toast title surfaces the backend `detail` (e.g. access denied)

**Observation 2 — Modal stays open**:
1. Modal is still in the DOM

**API mock**: `POST /oauth/custom_credential` → 403.

---

### TC-ERROR-018: Custom credential 409 duplicate name (OAI-013)

**Action**:
1. Fill modal with a duplicate name
2. Submit

**Observation 1 — Conflict toast**:
1. Toast title equals the backend `detail` (conflict message)
2. Modal stays open

**API mock**: `POST /oauth/custom_credential` → 409.

---

### TC-ERROR-019: Custom credential 500 (OAI-014)

**Action**:
1. Fill modal and submit

**Observation 1 — Generic error toast**:
1. Toast title surfaces backend detail OR `Something went wrong. Please try again.`

**Observation 2 — Form preserved**:
1. Modal stays open; form fields intact

**API mock**: `POST /oauth/custom_credential` → 500.

---

### TC-ERROR-020: Disconnect 401 mid-flow (OAI-015)

**Action**:
1. Click Disconnect on a card

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Card remains; next nav redirects**:
1. Card is still in the list
2. Subsequent navigation triggers the login redirect

**API mock**: `DELETE /oauth/disconnect` → 401.

---

### TC-ERROR-021: Disconnect 500 preserves card (OAI-016)

**Action**:
1. Click Disconnect

**Observation 1 — Error toast**:
1. Toast title equals `Internal server error` (or backend detail)

**Observation 2 — Card preserved + cleanup**:
1. Card remains in the list
2. `disconnectingId` clears via finally

**API mock**: `DELETE /oauth/disconnect` → 500.

---

### TC-ERROR-022: Authorize 401 surfaces toast (OAI-017)

**Action**:
1. Click `Connect` on a tile

**Observation 1 — Error toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Tile clears + no navigation**:
1. Tile loading state clears
2. No browser navigation occurs

**API mock**: `GET /oauth/{provider}/authorize` → 401.

---

### TC-LOADING-001: Network failure on Connect surfaces toast (OAI-020)

**Action**:
1. Click `Connect` while the network is offline

**Observation 1 — Tile loading clears + toast**:
1. Tile loading state clears
2. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — No navigation**:
1. No browser navigation occurs

**API mock**: `route.abort('failed')` for `/authorize`.

---

### TC-LOADING-002: Network failure on Disconnect preserves card (OAI-021)

**Action**:
1. Click Disconnect while offline

**Observation 1 — Toast + recovery**:
1. Toast title equals `Something went wrong. Please try again.`
2. Card remains in the list
3. Loading state clears

---

### TC-LOADING-003: Network failure on Create custom credential preserves form (OAI-022)

**Action**:
1. Submit modal while offline

**Observation 1 — Toast + form preserved**:
1. Toast appears
2. Modal stays open with form intact

---

### TC-LOADING-004: Slow create disables button with Saving state (OAI-023)

**Preconditions**: API delays > 3 s.

**Action**:
1. Submit the modal

**Observation 1 — Saving state + double-submit guard**:
1. Button text equals `Saving...`
2. Button has `disabled` attribute
3. Clicking again fires zero additional `POST /oauth/custom_credential` requests

---

### TC-LOADING-005: Slow list shows skeleton and resolves smoothly (OAI-024)

**Preconditions**: `POST /oauth/list` delays > 3 s.

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Skeleton stays visible**:
1. `OAuthConnectionGridSkeleton` is visible during the wait

**Observation 2 — No flicker on resolve**:
1. Skeleton is replaced by cards without visual flicker

---

### TC-LOADING-006: Concurrent disconnect handled gracefully (OAI-025)

**Preconditions**: Another admin disconnects the same connection between paint and click.

**Action**:
1. Click Disconnect

**Observation 1 — First Disconnect succeeds**:
1. The request returns 200

**Observation 2 — Second click yields 404 + cleanup**:
1. Second `DELETE /oauth/disconnect` returns 404
2. Toast appears
3. Card is removed on next refetch

---

### TC-EDGE-001: Whitespace-only credential name disables Create (OAI-030)

**Action**:
1. Open modal
2. Type only whitespace into Credential Name

**Observation 1 — Inline helper + disabled button**:
1. Helper text reads `Credential name is required`
2. `Create credential` button is disabled

---

### TC-EDGE-002: Unicode + emoji credential name round-trips (OAI-031)

**Action**:
1. Open modal
2. Type a name containing emoji and unicode characters

**Observation 1 — Accepted by form**:
1. Form accepts the value
2. After successful submit, the card renders the unicode/emoji name as plain text

---

### TC-EDGE-003: Script tag in name is escaped on render (OAI-032)

**Action**:
1. Type `<script>alert(1)</script>` into Credential Name
2. Submit

**Observation 1 — Stored verbatim, rendered as text**:
1. Card renders the literal `<script>` text (not as HTML)
2. `window.alert` was not invoked

---

### TC-EDGE-004: Oversized credential name handled gracefully (OAI-033)

**Action**:
1. Type > 500 chars into Credential Name
2. Submit

**Observation 1 — Either inline error or backend 400**:
1. Either an inline error appears, or backend returns 400 with a toast
2. Modal stays open

---

### TC-EDGE-005: Whitespace-only Token URL fails imperative check (OAI-034)

**Action**:
1. Type only whitespace into Token URL
2. Fill other fields
3. Click `Create credential`

**Observation 1 — Error toast**:
1. Toast title equals `Token URL, Client ID and Client Secret are required for OAuth 2.0`

**Observation 2 — Modal stays open**:
1. Modal is still in the DOM

---

### TC-EDGE-006: Token URL whitespace trimmed before submit (OAI-035)

**Action**:
1. Type ` https://auth.example.com/oauth/token ` (leading/trailing whitespace) into Token URL
2. Submit

**Observation 1 — Trimmed payload**:
1. `POST /oauth/custom_credential` body has the URL without surrounding whitespace

---

### TC-EDGE-007: javascript: Token URL rejected by backend (OAI-036)

**Action**:
1. Type `javascript:alert(1)` into Token URL
2. Submit

**Observation 1 — Backend 400**:
1. `POST /oauth/custom_credential` returns 400
2. Toast surfaces backend `detail`

**Observation 2 — Modal stays open**:
1. Modal remains visible

---

### TC-EDGE-008: Oversized client secret handled gracefully (OAI-037)

**Action**:
1. Paste a > 2000-character Client Secret
2. Submit

**Observation 1 — Either accepted or 400**:
1. Either backend accepts (stores AES-encrypted) or returns 400
2. Modal stays open

---

### TC-EDGE-009: Whitespace-only Bearer Token fails imperative check (OAI-038)

**Preconditions**: Auth Type Bearer.

**Action**:
1. Type only whitespace into Bearer Token
2. Submit

**Observation 1 — Error toast**:
1. Toast title equals `Token is required for a Bearer credential`

---

### TC-EDGE-010: Auth Type toggle clears unrelated fields (OAI-039)

**Action**:
1. Fill OAuth 2.0 fields (Token URL, Client ID, Client Secret)
2. Switch Auth Type to `Bearer Token`
3. Fill Bearer Token
4. Submit

**Observation 1 — Previously entered other-type fields cleared on submit**:
1. Submitted payload does NOT contain `token_url`, `client_id`, `client_secret` fields

---

### TC-EDGE-011: Duplicate submission blocked by saving flag

**Action**:
1. Click `Create credential` twice rapidly

**Observation 1 — Only one request fires**:
1. Exactly one `POST /oauth/custom_credential` request is recorded
2. `disabled` blocks the second click

---

### TC-EDGE-012: Token expiry mid-disconnect still cleans up

**Preconditions**: Token expires while Disconnect is in flight.

**Action**:
1. Click Disconnect
2. Backend returns 401

**Observation 1 — Toast + cleanup**:
1. Toast title equals `Could not validate credentials`
2. `disconnectingId` clears via finally
3. Card remains until next refetch

---

### TC-EDGE-013: MCP-pending OAuth connection hidden from list

**Preconditions**: API returns an item with `public_metadata.status === 'pending'`.

**Action**:
1. Navigate to `/settings/integrations`

**Observation 1 — Filtered out**:
1. The pending row is NOT rendered (filtered at `OAuthConnectionGrid` line 117)
2. Other connections still render normally

---

### TC-EDGE-014: Catalog provider with configured:false counted in ordering

**Preconditions**: Catalog includes a `configured: false` tile.

**Action**:
1. Inspect catalog ordering

**Observation 1 — Tile renders with disabled button but counted**:
1. Tile renders with the disabled "Not configured" button
2. Tile still counts toward its category section ordering
3. Click does nothing — no `/authorize` request fires

---

### TC-EDGE-015: OAuth state mismatch on callback yields no toast (⚠ unverified)

**Action**:
1. Navigate to `/settings/integrations` after a backend `Invalid state parameter` rejection

**Observation 1 — No toast today**:
1. Zero Sonner toasts appear (only `status=success` triggers a toast)

> ⚠ unverified — confirm there's no negative-path toast.

---

### TC-A11Y-001: OAuth 2.0 modal tab order matches visual order (OAI-040)

**Preconditions**: Modal open; Auth Type OAuth 2.0.

**Action**:
1. Focus the first field
2. Press Tab repeatedly

**Observation 1 — Tab order**:
1. Order is: Auth Type → Name → Token URL → Client ID → Client Secret → Scope → Create
2. Every field is reachable

---

### TC-A11Y-002: Bearer modal tab order matches visual order (OAI-041)

**Preconditions**: Modal open; Auth Type Bearer.

**Action**:
1. Tab through fields

**Observation 1 — Tab order**:
1. Order is: Auth Type → Name → Bearer Token → Create

---

### TC-A11Y-003: Enter key submits modal (OAI-042)

**Preconditions**: Modal open with valid fields.

**Action**:
1. Press Enter while focused on a text field

**Observation 1 — Submits like Create click**:
1. `POST /oauth/custom_credential` fires

---

### TC-A11Y-004: Modal traps focus and restores on close (OAI-043)

**Action**:
1. Open the modal
2. Tab through repeatedly
3. Press Escape

**Observation 1 — Focus trapped inside**:
1. Tab cycles within modal
2. Focus does not escape behind the modal

**Observation 2 — Restored on close**:
1. After Escape, focus returns to the `Custom credential` button

---

### TC-A11Y-005: Inline errors announced via aria-live (OAI-044)

**Action**:
1. Blur Credential Name while it is empty

**Observation 1 — Helper text role**:
1. `Credential name is required` helper text has `role="alert"` or `aria-live`
2. Screen readers announce the error on blur

---

### TC-A11Y-006: Scope status icon has accessible label (OAI-045)

**Action**:
1. Inspect a yellow/red `ScopeStatus` icon

**Observation 1 — aria-label describes reconnect intent**:
1. Icon button has an `aria-label` that describes the reconnect action / status

---

### TC-A11Y-007: Connect tile is keyboard-operable (OAI-046)

**Action**:
1. Focus a `Connect` tile via Tab
2. Press Enter

**Observation 1 — Same flow as click**:
1. `GET /oauth/{provider}/authorize` fires

---

### TC-FULL-001: End-to-end custom OAuth credential lifecycle (OAI-FULL)

**Preconditions**: Authenticated admin.

**Action**:
1. Open the Custom Credential modal
2. Fill OAuth 2.0 fields (Name, Token URL, Client ID, Client Secret)
3. Click `Create credential`
4. Click the new card's `ScopeStatus` icon (to verify the guard toast for `custom:`)
5. Click `Disconnect` on the card

**Observation 1 — Step 3 — Success**:
1. Toast title equals `Custom credential created`
2. New row appears in the list

**Observation 2 — Step 4 — Reconnect guard for custom**:
1. Toast title equals `Custom credentials cannot be reconnected — recreate the credential instead.`
2. No API call fires

**Observation 3 — Step 5 — Disconnect success**:
1. Card animates out
2. Toast title equals `Account disconnected`
3. Row is gone after refetch

**Cleanup** (in `try/finally`):
1. If the credential still exists at end of test, delete it via the backend API
2. Clear cookies and localStorage

---

## Edge Cases (each appears as a `TC-EDGE-*` / `TC-NAV-*` / `TC-LOADING-*` test case above)

- [x] Unauthenticated access → see TC-NAV-001
- [x] `/oauth/catalog` fails → static fallback list → see TC-ERROR-003
- [x] Provider tile marked `configured: false` → see TC-ERROR-015 / TC-EDGE-014
- [x] OAuth callback returns `status=error` → see TC-NAV-007
- [x] OAuth state mismatch → see TC-EDGE-015 (`⚠ unverified`)
- [x] User cancels Google consent → covered by TC-NAV-007
- [x] MCP OAuth connection in `status=pending` hidden → see TC-EDGE-013
- [x] Custom credential without Reconnect → see TC-ERROR-013
- [x] Scope status yellow reconnect preserves connection_id → see TC-HAPPY-006
- [x] Token approaching expiry — UI badge flips back to green after refetch — covered by business rules + TC-HAPPY-011
- [x] Auth type switched mid-form → see TC-EDGE-010
- [x] Empty list + filters → covered by TC-HAPPY-010 (no filtered state today)
- [x] Token expiry mid-action → see TC-EDGE-012
- [x] Duplicate submission blocked → see TC-EDGE-011
- [x] OAuth callback with status=error skips toast → see TC-NAV-007
- [x] MCP-pending filtered → see TC-EDGE-013
- [x] Catalog `configured: false` counts toward ordering → see TC-EDGE-014

---

## Business Rules

- OAuth tokens are stored AES-encrypted on the backend (`oauth_connections.encrypted_tokens`); the frontend never sees raw access or refresh tokens.
- The same provider + identity should always reuse one row — backend upserts on `(provider, account_email)`. The UI must not create duplicate cards on reconnect.
- Custom credentials live alongside provider credentials but cannot be re-authorized — they must be deleted and recreated to rotate.
- Available Providers ordering: Google category first, then Productivity, Dev & CRM, Other (when present), per `available-integrations-catalog.tsx`.
- The success toast title matches the provider's display name (e.g. "Google Calendar connected successfully"), not the slug.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Catalog tiles keyboard reachable; primary `Connect` is a real button → see TC-A11Y-007
- [x] Disabled "Not configured" announces disabled state → see TC-ERROR-015
- [x] Tab switches preserve focus → covered in TC-NAV-008
- [x] Custom credential modal traps focus + restores → see TC-A11Y-004
- [x] Password-type inputs have `type="password"` + labels → covered in UI elements
- [x] Scope status icon has accessible name → see TC-A11Y-006
- [x] Toast titles announced via `aria-live` (Sonner default) → covered by general toast assertions
- [x] OAuth 2.0 modal tab order → see TC-A11Y-001
- [x] Bearer modal tab order → see TC-A11Y-002
- [x] Enter submits modal → see TC-A11Y-003
- [x] Inline errors announced → see TC-A11Y-005
