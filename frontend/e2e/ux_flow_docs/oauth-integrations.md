# Feature Doc: OAuth Integrations (Services)

Feature documentation for the Services tab and Available Providers catalog on
the Integrations page. Used by `/generate-tests oauth-integrations` (or
`--docs e2e/ux_flow_docs/oauth-integrations.md`) to ensure all user cases are covered.

OAuth Integrations are per-organization connections to third-party services
(Google Calendar, Google Sheets, custom OAuth 2.0 client-credentials, custom
Bearer tokens) that downstream tools and MCP servers can use at call-time.

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

## User Workflow Steps

**WF-1: Authenticated user lands on the page** (positive)

1. User has `tone_access_token` cookie → expected: middleware allows the route
2. User navigates to `/settings/integrations` → expected: header "Integrations" renders; Available Providers catalog fetches via `GET /oauth/catalog`; Services tab is active by default (`useState<'services'>`)
3. While catalog loads → expected: tiles fall back to the static `OAUTH_PROVIDERS` list from `src/constants/integrations` (every tile treated as `configured: true`)
4. While `POST /oauth/list` is in flight → expected: `OAuthConnectionGridSkeleton` (2 cards) renders inside the Services tab
5. Response arrives with items → expected: each connection card shows provider name, "Connected" green-dot badge, email, "Refreshed X ago", first 3 scope pills (+N more), `ScopeStatus` icon, and "Disconnect" button

**WF-2: Connect Google Calendar via OAuth** (positive)

1. User clicks "Connect" on the Google Calendar tile → expected: `setPendingProvider('google_calendar')`, the button switches to its loading state ("Loading...")
2. Frontend calls `GET /oauth/google_calendar/authorize` → expected: 200 returns `{ auth_url }`
3. Frontend assigns `window.location.href = auth_url` → expected: browser navigates to Google consent
4. Google redirects back to `/api/v1/oauth/google_calendar/callback?code=...&state=...`
5. Backend persists the connection and 307-redirects to `/settings/integrations?provider=google_calendar&status=success`
6. `IntegrationsWithCallback` reads `searchParams` → expected: shows success toast "google calendar connected successfully" (provider slug with `_` replaced by spaces), `window.history.replaceState` strips the query params, `setCallbackProvider` triggers `fetchOAuthAtom`
7. After refetch → expected: new card appears in the Services tab list

**WF-3: Disconnect a service** (positive)

1. User clicks "Disconnect" on a card → expected: `setDisconnectingId(id)`; button gets `loading=true`
2. `DELETE /oauth/disconnect?connection_id=<id>` fires → expected: 200 returns `{ message: "OAuth connection deleted successfully" }`
3. `fetchOAuthAtom` re-runs → expected: card animates out via framer-motion exit; toast "Account disconnected"

**WF-4: Reconnect (yellow/red ScopeStatus)** (positive — catalog provider)

1. User clicks the yellow `ScopeStatus` icon on a catalog connection → expected: `setReconnectingProvider(provider_slug)`
2. `getOAuthAuthorizeUrl(provider)` is called → expected: 200 returns `{ auth_url }`; `window.location.href` is assigned
3. After consent, backend redirects to `/settings/integrations?provider=<slug>&status=success` (same as WF-2 step 6+)
4. The connection row updates in place (backend upserts on `(provider, account_email)` — no duplicate row)

**WF-5: Reconnect MCP-bound OAuth via discovery** (positive)

1. User clicks yellow status on a connection whose `provider_slug` starts with `mcp:` → expected: code path branches into `discoverMcpOAuth`
2. `POST /oauth/mcp/discover` fires with `{ server_url, label }` from `public_metadata.server_url` → expected: 200 returns `{ authorization_url, connection_id }`
3. `window.location.href = authorization_url` → expected: browser navigates to the MCP provider's consent

**WF-6: Create custom OAuth 2.0 credential** (positive)

1. User clicks the header "Custom credential" button → expected: `CustomCredentialModal` opens with title "New Custom Credential" and description "Configure authentication for custom API endpoints."
2. Auth Type is "OAuth 2.0 (client credentials)" by default → expected: Token URL, Client ID, Client Secret, Scope fields render
3. User fills Name `Acme Salesforce`, Token URL `https://acme.my.salesforce.com/services/oauth2/token`, Client ID `3MVG9...`, Client Secret `ABC123...`, optional Scope `api refresh_token`
4. User clicks "Create credential" → expected: button text becomes "Saving..." and is disabled; `POST /oauth/custom_credential` fires
5. On 201 success → expected: modal closes, toast "Custom credential created", `fetchOAuthAtom` re-runs, new card appears with slug starting `custom:`
6. Custom card has no "Reconnect" affordance (per `OAuthConnectionGrid` guard: `provider_slug.startsWith('custom:')`)

**WF-7: Create custom Bearer credential** (positive)

1. User opens the modal → switches Auth Type to "Bearer Token"
2. Fields collapse to Credential Name + Bearer Token (password) only
3. User fills `My API Key` and `bearer-token-xyz` → clicks Create credential → expected: `POST /oauth/custom_credential` with `auth_kind: "bearer"` payload
4. On 201 success → expected: toast "Custom credential created"

**WF-8: Auth gating** (negative)

1. User has no `tone_access_token` cookie and visits `/settings/integrations` → expected: 307 redirect to `/auth/login?redirect=%2Fsettings%2Fintegrations`

**WF-9: OAuth callback returns error** (negative)

1. User cancels Google consent (or backend returns 400 from `/oauth/google_calendar/callback`)
2. Backend redirects to `/settings/integrations?provider=google_calendar&status=error`
3. `IntegrationsWithCallback` reads `searchParams` → because `status !== 'success'`, **no toast is shown today** — the user simply lands on the page with no new card ⚠ unverified opportunity: a future enhancement may add an error toast for `status=error`

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

## Success Scenarios

**PS-1: OAuth catalog renders Google providers**

- **Preconditions**: authenticated.
- **Steps**: navigate to `/settings/integrations`.
- **Expected outcome**: "Google" category section renders with Google Calendar tile + "Connect" button + "OAuth 1 scope" badge.
- **Mock API** (`GET /oauth/catalog`, 200):
  ```json
  {
    "providers": [
      {
        "slug": "google_calendar",
        "name": "Google Calendar",
        "auth_kind": "oauth2",
        "configured": true,
        "scopes": ["https://www.googleapis.com/auth/calendar"]
      }
    ]
  }
  ```

**PS-2: Services tab loads connections**

- **Mock API** (`POST /oauth/list`, 200):
  ```json
  [
    {
      "id": "11111111-2222-3333-4444-555555555555",
      "provider_slug": "google_calendar",
      "label": "Google Calendar",
      "auth_type": "oauth",
      "public_metadata": {
        "user_email": "owner@acme.com",
        "scopes": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email",
        "token_expiry": 1748385600
      },
      "created_by_user_id": "7c2f1a4e-5b9d-4c8e-9a1f-3e5b7c9d2a4f",
      "created_at": "2026-05-27T10:00:00+00:00",
      "updated_at": "2026-05-27T10:00:00+00:00"
    }
  ]
  ```
- **Expected outcome**: one connection card rendered; tab badge shows `1`.

**PS-3: Authorize URL kick-off**

- **Steps**: click "Connect" on Google Calendar tile.
- **Mock API** (`GET /oauth/google_calendar/authorize`, 200):
  ```json
  { "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=XXX.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fapi.tone%2Fapi%2Fv1%2Foauth%2Fgoogle_calendar%2Fcallback&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar&state=org:user:google_calendar&access_type=offline&prompt=consent" }
  ```
- **Expected outcome**: `window.location.href` becomes the `auth_url`. (E2E: intercept the navigation and assert it matches.)

**PS-4: Callback success surfaces toast**

- **Preconditions**: stub navigation to `/settings/integrations?provider=google_calendar&status=success`.
- **Expected outcome**: toast title "google calendar connected successfully" (slug with `_` → spaces); query params stripped via `history.replaceState`; `fetchOAuthAtom` re-runs.

**PS-5: Disconnect succeeds**

- **Steps**: click "Disconnect" on a connected card.
- **Mock API** (`DELETE /oauth/disconnect`, 200): `{ "message": "OAuth connection deleted successfully" }`
- **Expected outcome**: card animates out; toast "Account disconnected".

**PS-6: Custom OAuth 2.0 credential created**

- **Steps**: open modal → fill Name + Token URL + Client ID + Client Secret + Scope → Create credential.
- **Mock API** (`POST /oauth/custom_credential`, 201):
  ```json
  {
    "id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
    "provider_slug": "custom:acme-salesforce",
    "name": "Acme Salesforce",
    "auth_kind": "oauth2_client_credentials",
    "is_active": true
  }
  ```
- **Expected outcome**: modal closes; toast "Custom credential created"; list refetches; new card has no Reconnect control.

**PS-7: Custom Bearer credential created**

- **Steps**: switch Auth Type to "Bearer Token" → fill Name + Bearer Token → Create credential.
- **Mock API** (`POST /oauth/custom_credential`, 201):
  ```json
  {
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "provider_slug": "custom:my-api-key",
    "name": "My API Key",
    "auth_kind": "bearer",
    "is_active": true
  }
  ```
- **Expected outcome**: same as PS-6.

**PS-8: MCP discover returns authorize URL**

- **Mock API** (`POST /oauth/mcp/discover`, 200):
  ```json
  { "authorization_url": "https://mcp.example.com/oauth/authorize?client_id=tone&state=abc", "connection_id": "11111111-mcp1-4eee-9aaa-222222222222" }
  ```
- **Expected outcome**: `window.location.href` becomes the `authorization_url`.

**PS-9: Empty services list**

- **Mock API** (`POST /oauth/list`, 200): `[]`
- **Expected outcome**: dashed box reads "No services connected yet — pick one from \"Browse providers\" above." plus "Connect another service" CTA.

---

## Failure Scenarios

**FS-1: OAuth `/authorize` rejects (unsupported provider)**

- **Steps**: click Connect on a tile whose slug isn't backed by configured credentials.
- **Mock API** (`GET /oauth/<slug>/authorize`, 400): `{"detail": "Unsupported provider: gmail"}`
- **Expected UI**: `handleApiError` shows toast titled "Unsupported provider: gmail"; tile button loading state clears.

**FS-2: OAuth `/authorize` 500 (credentials not configured)**

- **Mock API** (500): `{"detail": "OAuth credentials not configured for google_calendar"}`
- **Expected UI**: toast title = "OAuth credentials not configured for google_calendar"; tile button loading state clears.

**FS-3: Catalog fetch fails**

- **Mock API** (`GET /oauth/catalog`, 500): `{"detail": "Failed to load provider catalog"}`
- **Expected UI**: `handleApiError` toast "Failed to load provider catalog"; tiles fall back to the static `OAUTH_PROVIDERS` (page still functional).

**FS-4: Services list unauthorized**

- **Mock API** (`POST /oauth/list`, 401): `{"detail": "Could not validate credentials"}`
- **Expected UI**: state flips to `status: "error"`; toast title = "Could not validate credentials".

**FS-5: Services list forbidden (non-member)**

- **Mock API** (`POST /oauth/list`, 403): `{"detail": "User is not a member of this organization"}`
- **Expected UI**: toast "User is not a member of this organization".

**FS-6: Disconnect 404**

- **Mock API** (`DELETE /oauth/disconnect`, 404): `{"detail": "OAuth connection not found"}`
- **Expected UI**: card remains; toast "OAuth connection not found"; `disconnectingId` clears via `finally` block.

**FS-7: Disconnect 400 invalid UUID**

- **Mock API** (400): `{"detail": "connection_id must be a valid UUID"}`
- **Expected UI**: toast "connection_id must be a valid UUID".

**FS-8: Custom credential blocked by client-side OAuth check**

- **Steps**: open modal, leave Token URL blank, fill rest, click Create credential.
- **Mock API**: not called — imperative check fires first.
- **Expected UI**: error toast title "Token URL, Client ID and Client Secret are required for OAuth 2.0"; modal stays open.

**FS-9: Custom credential blocked by client-side Bearer check**

- **Steps**: switch to Bearer, leave Bearer Token blank, click Create credential.
- **Mock API**: not called.
- **Expected UI**: toast "Token is required for a Bearer credential".

**FS-10: Custom credential backend 400**

- **Mock API** (`POST /oauth/custom_credential`, 400): `{"detail": "name is required"}`
- **Expected UI**: modal stays open; toast "name is required" (via `handleApiError`).

**FS-11: Empty required Credential Name (Zod)**

- **Steps**: leave Name blank.
- **Expected UI**: Create credential disabled (`formState.isValid === false`); helperText under Name reads "Credential name is required".

**FS-12: Reconnect MCP — missing `server_url`**

- **Preconditions**: MCP connection with no `public_metadata.server_url`.
- **Steps**: click yellow ScopeStatus.
- **Expected UI**: toast "Cannot reconnect: this MCP connection has no stored server URL." (`showToast.error` from `oauth-connection-grid.tsx:61`); no API call fires.

**FS-13: Reconnect for custom credential**

- **Preconditions**: connection with `provider_slug.startsWith('custom:')`.
- **Steps**: somehow trigger `handleReconnect` (typically the card omits the affordance).
- **Expected UI**: toast "Custom credentials cannot be reconnected — recreate the credential instead." — guard on line 48-52 of `oauth-connection-grid.tsx`.

**FS-14: MCP discover 400**

- **Mock API** (`POST /oauth/mcp/discover`, 400): `{"detail": "server_url is required"}`
- **Expected UI**: toast "server_url is required"; reconnect spinner clears.

**FS-15: OAuth callback returns `status=error`**

- **Preconditions**: navigate to `/settings/integrations?provider=google_calendar&status=error`.
- **Expected UI**: page renders normally with no toast (today the callback handler only fires `showToast.success` on `status === 'success'`). ⚠ unverified — confirm there is no negative-path toast yet.

**FS-16: Catalog tile with `configured: false`**

- **Preconditions**: catalog includes `{ "slug": "google_sheets", "configured": false, "scopes": [] }`.
- **Expected UI**: tile button renders as `<CustomButton disabled>Not configured</CustomButton>` with `aria-label="<name> is not configured"`; click does nothing, no `/authorize` call.

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

## Edge Cases

- [ ] Unauthenticated access → middleware redirect
- [ ] `/oauth/catalog` fails → tiles fall back to a static built-in list (page still functional)
- [ ] Provider tile marked `configured: false` → button disabled, "Not configured" badge shown
- [ ] OAuth callback returns `status=error` → error toast, no card added
- [ ] OAuth state mismatch → backend rejects callback; frontend surfaces error toast
- [ ] User cancels Google consent → callback returns no code; user lands back without a new card and no success toast
- [ ] MCP OAuth connection in `status=pending` → hidden from the Services tab list
- [ ] Custom credential without Reconnect: deleting + recreating is the only rotation path
- [ ] Scope status yellow → reconnect launched preserves the same `connection_id` (no duplicate row)
- [ ] Token approaching expiry → backend renews via refresh token; UI badge flips back to green after refetch
- [ ] Auth type switched mid-form in `CustomCredentialModal` → previously entered fields for the other type are cleared
- [ ] Empty list + filters → only the "No services connected yet" empty state is reachable here (no separate filtered state today)
- [ ] Token expiry mid-action: user clicks Disconnect while their JWT expires → backend returns 401 → `handleApiError` shows toast "Could not validate credentials"; `disconnectingId` clears via `finally`; card remains until refetch
- [ ] Duplicate submission: user clicks "Create credential" twice quickly → `saving` flag flips on first click and `disabled` blocks the second; only one `POST /oauth/custom_credential` fires
- [ ] OAuth callback with `status=error`: page renders but `IntegrationsWithCallback` skips the toast branch (only fires on `status === 'success'`); list does not refetch automatically — user must click Refresh
- [ ] MCP-pending OAuth connection (`public_metadata.status === 'pending'`): `OAuthConnectionGrid` filters it out at line 117 — it never renders even though the API returned it
- [ ] Catalog provider with `configured: false`: tile renders disabled "Not configured" button; clicking does nothing; no `/authorize` request fires; tile still counts toward the category section ordering
- [ ] OAuth state mismatch on callback (CSRF-style): backend 400 `{"detail":"Invalid state parameter"}` redirects to the page without `status=success`, so no toast is shown today ⚠ unverified

---

## Business Rules

- OAuth tokens are stored AES-encrypted on the backend (`oauth_connections.encrypted_tokens`); the frontend never sees raw access or refresh tokens.
- The same provider + identity should always reuse one row — backend upserts on `(provider, account_email)`. The UI must not create duplicate cards on reconnect.
- Custom credentials live alongside provider credentials but cannot be re-authorized — they must be deleted and recreated to rotate.
- Available Providers ordering: Google category first, then Productivity, Dev & CRM, Other (when present), per `available-integrations-catalog.tsx`.
- The success toast title matches the provider's display name (e.g. "Google Calendar connected successfully"), not the slug.

---

## Accessibility Requirements

- [ ] Catalog tiles are keyboard reachable; the primary "Connect" button is a real `<button>` with an accessible label
- [ ] Disabled "Not configured" buttons announce their disabled state to screen readers
- [ ] Tab switches preserve focus within the active pane after the URL updates
- [ ] `CustomCredentialModal` traps focus and restores it on close
- [ ] Password-type inputs (Client Secret, Bearer Token) have `type="password"` and visible field labels
- [ ] Scope status icon has an accessible name describing why it is yellow/red (e.g. `aria-label="Reconnect — scope missing"`)
- [ ] Toast titles are announced via `aria-live` (Sonner default)

---

## E2E Scenarios — gap-filling

> The doc above uses PS-/FS-/WF- narrative scenarios. The table below adds
> compact `OAI-` IDs that `/generate-tests` consumes alongside them. New IDs
> are appended after any existing OAI- (none yet) — start at OAI-001.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-001 | Visit `/settings/integrations` without auth | Redirects to `/auth/login?redirect=%2Fsettings%2Fintegrations` | `unauthenticated visit redirects to login` |
| OAI-002 | Visit `/integrations` legacy path without auth | Redirects to login with the same post-redirect target | `legacy /integrations without auth redirects to login` |
| OAI-003 | Visit with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| OAI-004 | Member (non-admin) opens `Custom credential` modal | Modal opens but Save returns 403 with toast; or button hidden per role | `member role cannot create custom credential` |
| OAI-005 | Member clicks `Disconnect` on a card | Returns 403; toast `Forbidden`; card stays in list | `member cannot disconnect existing connection` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-010 | `POST /oauth/custom_credential` returns 400 with string `detail` | Toast `<detail>`; modal stays open with form intact | `400 on custom credential keeps modal open with toast` |
| OAI-011 | `POST /oauth/custom_credential` returns 401 mid-flow | Toast `Could not validate credentials`; next nav hits login redirect | `401 on save triggers login redirect on next nav` |
| OAI-012 | `POST /oauth/custom_credential` returns 403 | Access denied toast; modal stays open | `403 on save shows toast and keeps modal open` |
| OAI-013 | `POST /oauth/custom_credential` returns 409 (duplicate name) | Toast with conflict detail; modal stays open | `409 duplicate name surfaces conflict toast` |
| OAI-014 | `POST /oauth/custom_credential` returns 500 | Generic error toast; modal intact | `500 on save shows toast and preserves form` |
| OAI-015 | `DELETE /oauth/disconnect` returns 401 mid-flow | Toast `Could not validate credentials`; card remains; next nav redirects | `disconnect 401 shows toast and triggers login redirect` |
| OAI-016 | `DELETE /oauth/disconnect` returns 500 | Toast `Internal server error`; card remains; `disconnectingId` clears via finally | `disconnect 500 shows toast and preserves card` |
| OAI-017 | `GET /oauth/{provider}/authorize` returns 401 | Toast `Could not validate credentials`; tile loading clears; no navigation | `authorize 401 surfaces toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-020 | Network failure on Connect (`route.abort('failed')` for /authorize) | Tile loading clears; toast `Something went wrong`; no navigation | `network failure on Connect surfaces toast` |
| OAI-021 | Network failure on Disconnect | Toast; card remains; loading clears | `network failure on Disconnect preserves card` |
| OAI-022 | Network failure on Create custom credential | Toast; modal stays open with form intact | `network failure on custom credential preserves form` |
| OAI-023 | Slow `POST /oauth/custom_credential` (>3s) | `Create credential` shows `Saving...` and is disabled; double-submit blocked | `slow create disables button with Saving state` |
| OAI-024 | Slow `GET /oauth/list` (>3s) | Skeleton shows for the duration; no flicker on resolve | `slow list shows skeleton and resolves smoothly` |
| OAI-025 | Concurrent: another admin disconnects same connection between paint and click | First Disconnect succeeds (200), second 404 → toast + card removed on refetch | `concurrent disconnect handled gracefully` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-030 | Credential Name whitespace only | Helper text `Credential name is required`; Create disabled | `whitespace-only credential name disables Create` |
| OAI-031 | Credential Name with emoji + unicode | Accepted; row renders unicode | `unicode + emoji credential name round-trips` |
| OAI-032 | Credential Name `<script>alert(1)</script>` | Stored verbatim; rendered as text | `script tag in name is escaped on render` |
| OAI-033 | Credential Name >500 chars | Inline error or backend 400; modal stays open | `oversized credential name handled gracefully` |
| OAI-034 | Token URL whitespace only | Toast `Token URL, Client ID and Client Secret are required for OAuth 2.0`; modal open | `whitespace-only Token URL fails imperative check` |
| OAI-035 | Token URL with leading/trailing whitespace | Trimmed before submit | `Token URL whitespace trimmed before submit` |
| OAI-036 | Token URL with `javascript:` scheme | Rejected by backend (400) → toast; modal stays open | `javascript: Token URL rejected by backend` |
| OAI-037 | Client Secret >2000 chars | Either accepted (backend stores AES) or 400; modal stays open | `oversized client secret handled gracefully` |
| OAI-038 | Bearer Token whitespace only | Toast `Token is required for a Bearer credential` | `whitespace-only Bearer Token fails imperative check` |
| OAI-039 | Auth Type toggled mid-form | Previously entered fields for other auth type are cleared on submit | `auth type toggle clears unrelated fields` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-040 | Tab through OAuth 2.0 modal | Order: Auth Type → Name → Token URL → Client ID → Client Secret → Scope → Create | `OAuth 2.0 modal tab order matches visual order` |
| OAI-041 | Tab through Bearer modal | Order: Auth Type → Name → Bearer Token → Create | `Bearer modal tab order matches visual order` |
| OAI-042 | Submit modal via Enter | Triggers Create if valid | `Enter key submits modal` |
| OAI-043 | Modal traps focus + restores it on close | Tab wraps; Escape closes; focus returns to `Custom credential` button | `modal traps focus and restores on close` |
| OAI-044 | Inline `Credential name is required` helper has `role="alert"` / aria-live | Screen reader announces on blur | `inline errors are announced` |
| OAI-045 | `ScopeStatus` icon button has accessible name | `aria-label` describes reconnect intent | `scope status icon has accessible label` |
| OAI-046 | `Connect` tile reachable via Tab + Enter | Same flow as click | `Connect tile is keyboard-operable` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-050 | Tile `Connect` → callback success → land back on page | URL ends `/settings/integrations`; query stripped via `history.replaceState`; new card appears | `OAuth callback success returns to page and refreshes list` |
| OAI-051 | Tile `Connect` → user cancels Google consent → callback returns error | URL `/settings/integrations?provider=...&status=error`; no toast (current behavior); no new card | `OAuth callback error returns to page without toast` |
| OAI-052 | Tab switch Services ↔ MCP / Knowledge Base | Updates `?tab=`; pane swaps; counts persist | `tab switch updates query param` |
| OAI-053 | Browser Back after callback redirect | Returns to upstream history entry, not to the OAuth provider | `back after callback skips OAuth provider history` |
| OAI-054 | Click `Refresh` while modal is open | Lists refetch; modal remains open; form state intact | `refresh preserves modal state` |

### Full lifecycle test

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OAI-FULL | Open Custom Credential modal → fill OAuth 2.0 fields → Create → assert row + success toast → click ScopeStatus (verify guard toast for `custom:`) → Disconnect → assert row gone + success toast | All toasts + DOM mutations asserted; `try/finally` deletes the credential even if interim assertions fail | `lifecycle: create custom OAuth → verify → disconnect` |
