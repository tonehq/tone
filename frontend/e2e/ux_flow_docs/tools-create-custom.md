# Feature Doc: Tools — Create Custom

Feature documentation for the Custom Tool authoring page at
`/tools/create/custom`. Used by `/generate-tests tools-create-custom` (or
`--docs e2e/ux_flow_docs/tools-create-custom.md`) to ensure all positive and negative
scenarios are covered.

A **Custom Tool** is a user-defined HTTP function the LLM can call: name +
description + URL + method + parameters (JSON-Schema) + auth. The form lives
under `/tools/create/custom` and shares its `ToolFormPage` wrapper with the
edit route. This doc covers the create-mode subset of that form.

> Cross-references:
>
> - `tools-create.md` — the parent chooser at `/tools/create` (built-in vs custom)
> - `tools-edit.md` — the edit-mode wrapper for the same form
> - `tools.md` — the list at `/tools`

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/tools/create/custom` (accepts an optional `?template_id=<uuid>` query)
- **Component (wrapper)**: `src/app/(dashboard)/tools/create/custom/page.tsx` (wraps `ToolFormPage` in `<Suspense>`)
- **Main controller**: `src/components/tools/ToolFormPage.tsx` (shared with edit + built-in)
- **Form**: `src/components/tools/CustomToolForm.tsx` (this route renders this one because `toolType === 'custom'` is the default)
- **Sub-components**:
  - `src/components/tools/ParameterBuilder.tsx` — repeater for `parameters.properties`
  - `src/components/shared/TextInput`, `SelectInput`, `TextAreaField`, `CheckboxField`
- **Schema**: `src/schemas/tool.ts` → `customToolSchema` (Zod)
- **Auth required**: yes (middleware redirects to
  `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` without `tone_access_token` cookie)

---

## User Stories

### US-1: Define the tool's identity

**As an** agent owner, **I want to** name and describe my custom tool, **so
that** the LLM and other people on my team understand what it does.

**Acceptance criteria**:

- [ ] "Tool Definition" card section with Active checkbox in the top-right
- [ ] Function name input — required, font-mono, placeholder `check_inventory`
- [ ] Description textarea — required, 2 rows tall, placeholder describing inventory
- [ ] Both fields render via shared `TextInput` / `TextAreaField` with RHF + Zod resolver; errors show inline
- [ ] Top bar shows the live value of "Function name" (falls back to "New Tool" / "Edit Tool")
- [ ] Active checkbox flips `isActive` state (default ON)

### US-2: Configure the HTTP request

**As an** agent owner, **I want to** pick an HTTP method and write the
endpoint URL, **so that** the LLM knows where to send the tool call.

**Acceptance criteria**:

- [ ] "Request" card section
- [ ] Method `SelectInput` exposes GET / POST / PUT / DELETE / PATCH (from `METHOD_OPTIONS`); default POST; chip on the right shows the chosen verb color-coded per `METHOD_COLORS`
- [ ] URL `TextInput` — required, font-mono, placeholder `https://api.example.com/inventory/{product_id}`
- [ ] Zod requires the URL to be a valid URL (`z.string().min(1).url('Please enter a valid URL')`); inline error reads `Please enter a valid URL`
- [ ] Helper text below explains `{param}` path placeholders

### US-3: Define LLM-visible parameters

**As an** agent owner, **I want to** declare each parameter with a name, type,
description, and required flag, **so that** the LLM produces correct call arguments.

**Acceptance criteria**:

- [ ] "Parameters" card section with a numeric count badge when `paramCount > 0`
- [ ] Helper text changes by method: GET → "Parameters will be sent as query string values."; POST/PUT/DELETE/PATCH → "Parameters will be sent as JSON request body. Any parameter matching a {placeholder} in the URL will be used as a path value instead."
- [ ] Empty state: single full-width dashed "Add parameter" button
- [ ] Each row: parameter name (font-mono `input[name^=param-name-]`), type dropdown (string / number / integer / boolean / array), description input, Required checkbox, trash icon (hover-only — `opacity-0 group-hover:opacity-100`)
- [ ] On change, `ParameterBuilder` serializes rows to the JSON-Schema `{ type: 'object', properties: {...}, required?: [...] }` and calls `onChange`
- [ ] Rows with empty `name.trim()` are stripped at serialization time

### US-4: Configure authentication

**As an** agent owner, **I want to** select an auth type and supply credentials,
**so that** the tool call passes auth at runtime.

**Acceptance criteria**:

- [ ] `SelectInput` for "Authentication" — options: No Authentication / API Key / Bearer Token / Basic Auth
- [ ] `none` (default) reveals no extra fields
- [ ] `api_key` reveals Header name + Value (password); Header defaults to `X-API-Key` when blank at save time
- [ ] `bearer` reveals a single Token (password) field
- [ ] `basic` reveals Username + Password (password) fields
- [ ] Switching auth type unmounts the previous conditional section but the form keeps the underlying state (`authHeaderName`, `authApiKey`, `authBearerToken`, `authUsername`, `authPassword`) so re-selecting an earlier type restores its value

### US-5: Save the new tool

**As an** agent owner, **I want to** click Create to persist the tool, **so
that** it shows up on `/tools` and can be attached to agents.

**Acceptance criteria**:

- [ ] Top bar shows Cancel + Create (no Delete in create mode)
- [ ] Create runs `handleSubmit(onSave)` with `customToolSchema` validation; first invalid field's error renders inline
- [ ] Saving sends `POST /tool/upsert_tool` via `upsertToolAtom` with `{ name, description, url, method, parameters, auth_type, auth_config, is_active }` (no `id`)
- [ ] Auth config payload is built from `authType`:
  - `api_key` → `{ header_name: authHeaderName || 'X-API-Key', api_key: authApiKey }`
  - `bearer` → `{ token: authBearerToken }`
  - `basic` → `{ username: authUsername, password: authPassword }`
  - `none` → `null`
- [ ] Spinner replaces the Save icon while `saving === true`; the button shows `Loading...` text via `CustomButton`'s `loading` prop, and is `disabled`
- [ ] On success: toast `Tool created successfully`; `fetchTools()` re-runs; `router.push('/tools')`
- [ ] On error: `handleApiError` surfaces backend `detail`; user stays on the form; `saving` flips back to false

### US-6: Cancel without saving

**As an** agent owner, **I want to** click Cancel / Back to leave the form,
**so that** I can bail out cleanly.

**Acceptance criteria**:

- [ ] Cancel button (footer-right) and back arrow (header-left) both invoke the same `onBack`/`goBack` callback
- [ ] `useGoBack('/tools')` falls back to `/tools` when `router.back()` would leave the dashboard
- [ ] There is NO unsaved-changes guard in the current implementation — clicking Cancel/Back navigates away without confirmation

### US-7: Pre-fill from a template

**As an** agent owner, **I want to** start a custom tool from a template
selection, **so that** I get the parameter scaffold pre-populated.

**Acceptance criteria**:

- [ ] When the URL is `/tools/create/custom?template_id=<uuid>`, `ToolFormPage` calls `getTool(templateId)` and pre-loads `parameters` from that tool
- [ ] If the template's `tool_type` is built-in (not custom), the page swaps to `BuiltInToolForm` instead of `CustomToolForm`
- [ ] Template loader failures are swallowed silently — the form falls back to the empty custom state

---

## Input Specifications

### `customToolSchema` (Zod)

Source: `src/schemas/tool.ts` (lines 10-14).

| Field         | Type     | Required | Validation Rules                                                       | Exact Error Message              |
| ------------- | -------- | -------- | ---------------------------------------------------------------------- | -------------------------------- |
| Function name | text     | yes      | `z.string().min(1, 'Name is required')`                                | `Name is required`               |
| Description   | textarea | yes      | `z.string().min(1, 'Description is required')`                         | `Description is required`        |
| URL           | text     | yes      | `z.string().min(1, 'URL is required').url('Please enter a valid URL')` | `URL is required` / `Please enter a valid URL` |

### Other form state (not Zod-validated)

| Field            | Type      | Required    | Validation                                                          | Notes                                                              |
| ---------------- | --------- | ----------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Method           | select    | yes         | One of `GET / POST / PUT / DELETE / PATCH`; default POST            | Stored as uppercase                                                |
| Active           | checkbox  | no          | default ON                                                          | `is_active` boolean on the payload                                 |
| Authentication   | select    | no          | `none / api_key / bearer / basic`; default `none`                   | Drives which conditional auth fields render                        |
| Auth header name | text      | conditional | Required-feel when `auth_type === 'api_key'`; blank → defaults to `X-API-Key` on save | Saved under `auth_config.header_name`     |
| Auth API key     | password  | conditional | When `api_key`, value is saved under `auth_config.api_key`          |                                                                    |
| Auth bearer token| password  | conditional | When `bearer`, value is saved under `auth_config.token`             |                                                                    |
| Auth username    | text      | conditional | When `basic`, value is saved under `auth_config.username`           |                                                                    |
| Auth password    | password  | conditional | When `basic`, value is saved under `auth_config.password`           |                                                                    |
| Parameters       | repeater  | no          | Rows with empty `name.trim()` are silently dropped on serialize     | Serialized to JSON-Schema `{ type, properties, required? }`        |

### Button state rules

- Create button is `loading=true` and `disabled` while `saving === true`; loading text renders as `Loading...` (CustomButton convention).
- Cancel/Back are never disabled.
- Save icon (Save) swaps to `Loader2` spinner while saving.

---

## Navigation

| Trigger                                          | Destination                                       | Condition                                |
| ------------------------------------------------ | ------------------------------------------------- | ---------------------------------------- |
| Click back arrow / Cancel                        | `router.back()` → fallback `/tools`               | Always (no unsaved-changes guard)        |
| Click Create with a valid form                   | `POST /tool/upsert_tool` → on 200 → `/tools`      | Form passes Zod validation               |
| Visit with `?template_id=<uuid>`                 | Page hydrates from `GET /tool/get_tool`           | `template_id` query present              |
| Template's `tool_type !== 'custom'`              | Renders `BuiltInToolForm` at the same URL         | After template loads                     |
| No auth cookie                                   | `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` | `src/middleware.ts` redirect             |

---

## API Contracts

Prefix: `/api/v1`. Verified against the Postman `Tools` folder and
`src/services/toolService.ts`.

| Endpoint                  | Method | Request                                                                                                                   | Success                          | Error                                                                                                       |
| ------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `/tool/upsert_tool`       | POST   | `{ name, description, url, method, parameters, auth_type, auth_config, is_active, oauth_connection_id?, meta_data?, id? }` | `200 Tool` (200, not 201 today)  | `400 / 404 / 409 / 422`, see below                                                                          |
| `/tool/get_tool`          | GET    | `?tool_id=<uuid>`                                                                                                          | `200 Tool`                       | `404 { "detail": "Tool not found" }`                                                                        |

### Example — `POST /tool/upsert_tool` (custom, create)

Request body (minimum):

```json
{
  "name": "send_welcome_email",
  "description": "Send welcome email",
  "url": "https://api.acme.com/emails",
  "method": "POST",
  "parameters": {},
  "auth_type": "none",
  "auth_config": null,
  "is_active": true
}
```

Request body (with parameters + API Key auth):

```json
{
  "name": "post_to_crm",
  "description": "Submit a new lead to Acme CRM",
  "url": "https://api.acme.com/leads",
  "method": "POST",
  "parameters": {
    "type": "object",
    "properties": {
      "name": { "type": "string", "description": "Lead full name" },
      "email": { "type": "string", "description": "Lead email" }
    },
    "required": ["name", "email"]
  },
  "auth_type": "api_key",
  "auth_config": { "header_name": "X-API-Key", "api_key": "sk-acme-..." },
  "is_active": true
}
```

200 OK:

```json
{
  "id": "550e8400-newt-001",
  "name": "send_welcome_email",
  "tool_type": "custom",
  "url": "https://api.acme.com/emails",
  "method": "POST",
  "auth_type": "none",
  "auth_config": null,
  "parameters": {},
  "is_active": true,
  "is_template": false,
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:00:00Z"
}
```

400 (name missing):

```json
{ "detail": "name is required when creating a new tool" }
```

400 (description missing):

```json
{ "detail": "description is required when creating a new tool" }
```

400 (template not editable — defensive; the custom create flow shouldn't hit this):

```json
{ "detail": "Template tools cannot be edited" }
```

404 (update target gone — edit-mode share):

```json
{ "detail": "Tool not found" }
```

409 (duplicate name):

```json
{ "detail": "A tool with name 'send_welcome_email' already exists in this organization" }
```

### Example — `GET /tool/get_tool?tool_id=<uuid>` (template pre-fill)

200 OK:

```json
{ "id": "tpl-1", "name": "scaffold", "tool_type": "custom", "is_template": true, "parameters": { "type": "object", "properties": { "query": { "type": "string" } } } }
```

404 Not Found:

```json
{ "detail": "Tool not found" }
```

State is held in `ToolFormPage`'s local React state (NOT in a Jotai atom):
`toolType`, `name`, `description`, `url`, `method`, `parameters`, `authType`,
five auth field strings, `isActive`, `metaData`, `builtInAuthConfig`,
`oauthConnectionId`. The Jotai atoms involved are `upsertToolAtom`,
`fetchToolsAtom`, and (edit-mode only) `deleteToolAtom`.

---

## UI Elements

| Element                       | Type             | Content / Label                                                          | Behavior                                                       |
| ----------------------------- | ---------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Top bar — back arrow          | Icon button      | aria-label "Back"                                                        | `onBack` → `useGoBack('/tools')`                                |
| Top bar — title               | span             | live `name` (or "New Tool" / "Edit Tool" fallback)                       | Reflects RHF `watch('name')`                                    |
| Top bar — Cancel              | Button (default) | "Cancel"                                                                 | Same as back arrow                                              |
| Top bar — Create / Save       | Button (primary) | "Create" (create) / "Save" (edit) + Save / Loader2 icon                  | `disabled + loading` while `saving === true`                    |
| Tool Definition card          | Section          | "Tool Definition" header + Active checkbox                                | Active flips `isActive`                                          |
| Function name input           | TextInput        | required, placeholder `check_inventory`, font-mono                       | RHF + Zod                                                        |
| Description textarea          | TextAreaField    | required, placeholder describing inventory, 2 rows                       | RHF + Zod                                                        |
| Request card                  | Section          | "Request" header + helper text below input                               | Static                                                           |
| Method select                 | SelectInput      | options GET / POST / PUT / DELETE / PATCH                                | Default POST; chip on the right reflects color                  |
| URL input                     | TextInput        | required, placeholder `https://api.example.com/inventory/{product_id}`   | RHF + Zod `url()`                                                |
| Method chip                   | Span             | colored verb badge                                                        | Driven by `METHOD_COLORS`                                        |
| Parameters card               | Section          | "Parameters" header + count badge when `paramCount > 0`                  | Helper text branches on method                                   |
| Empty params CTA              | Button (default) | dashed "Add parameter"                                                    | Adds the first row                                               |
| Parameter row                 | div              | name + type + description + Required checkbox + trash icon (hover)        | Rows with empty name dropped on serialize                       |
| Authentication select         | SelectInput      | None / API Key / Bearer / Basic                                          | Drives which conditional section renders                         |
| API Key — Header input        | TextInput        | label "Header", placeholder "X-API-Key"                                  | Defaults to `X-API-Key` if blank at save time                    |
| API Key — Value input         | TextInput (password) | label "Value", placeholder "sk-..."                                  | Saved as `auth_config.api_key`                                   |
| Bearer Token — Token input    | TextInput (password) | label "Token", placeholder "Enter bearer token"                      | Saved as `auth_config.token`                                     |
| Basic Auth — Username input   | TextInput        | label "Username", placeholder "username"                                 | Saved as `auth_config.username`                                  |
| Basic Auth — Password input   | TextInput (password) | label "Password", placeholder "password"                             | Saved as `auth_config.password`                                  |

---

## Expected Toast Messages

Sonner toasts via `showToast`. Errors run through `handleApiError`
(`src/utils/helpers.ts`) which passes backend `detail` (when it's a string)
as the title; non-string `detail` falls back to the default.

| Trigger                                                  | Toast title                                                | Toast description | Variant |
| -------------------------------------------------------- | ---------------------------------------------------------- | ----------------- | ------- |
| Create success                                           | `Tool created successfully`                                | —                 | success |
| Update success (edit-mode share)                         | `Tool updated successfully`                                | —                 | success |
| Delete success (edit-mode only)                          | `Tool deleted successfully`                                | —                 | success |
| Create — 409 duplicate                                   | `A tool with name '<name>' already exists in this organization` | —            | error   |
| Create — 400 name required                               | `name is required when creating a new tool`                | —                 | error   |
| Create — 400 description required                        | `description is required when creating a new tool`         | —                 | error   |
| Create — 400 OAuth conn not found (defensive, custom)    | `OAuth connection <id> not found`                          | —                 | error   |
| Create — 5xx with string `detail`                        | (backend `detail` string verbatim, e.g. `Internal server error`) | —          | error   |
| Create — non-string `detail` (e.g. 422 array)            | `Something went wrong. Please try again.`                  | —                 | error   |
| Template pre-fill failure                                | (none — swallowed silently)                                | —                 | —       |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Minimum-required create succeeds

**Preconditions**:
- Authenticated; no tool named `check_inventory` exists in the org

**Action**:
1. Visit `/tools/create/custom`
2. Type `check_inventory` into the Function name input
3. Type `Probe.` into the Description textarea
4. Type `https://api.example.com/inventory` into the URL input
5. Leave Method = POST (default) and Active = ON (default)
6. Click "Create"

**Observation 1 — Network call**:
1. Exactly one `POST /tool/upsert_tool` request is recorded
2. The body equals `{ name: 'check_inventory', description: 'Probe.', url: 'https://api.example.com/inventory', method: 'POST', parameters: {}, auth_type: 'none', auth_config: null, is_active: true }`
3. No `id` field is present in the body

**Observation 2 — Success toast**:
1. Sonner toast appears in `[data-sonner-toast]` with title `Tool created successfully`

**Observation 3 — Redirect**:
1. URL becomes `/tools` within 1s
2. The Custom form is no longer in the DOM

**API mock**: `POST /tool/upsert_tool` → 200 with the returned tool object including a generated `id`.

---

### TC-HAPPY-002: Create with full param + auth combo

**Preconditions**: authenticated.

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name `book_room`, Description `Books a hotel room.`, URL `https://api.acme.com/rooms/{room_id}/book`
3. Set Method to PUT
4. Click "Add parameter"; fill name `room_id`, type `string`, description `Resource path id`, required ON
5. Click "Add parameter"; fill name `nights`, type `number`, description `Stay duration`, required OFF
6. Pick Authentication = API Key; fill Header `X-Test-Api-Key`, Value `sk-tc-full-secret`
7. Toggle Active OFF
8. Click "Create"

**Observation 1 — Request body matches**:
1. `POST /tool/upsert_tool` body has `method: "PUT"`
2. `body.parameters.properties` contains `room_id` (string) and `nights` (number) with the typed descriptions
3. `body.parameters.required` equals `["room_id"]`
4. `body.auth_type` equals `"api_key"`
5. `body.auth_config` equals `{ header_name: "X-Test-Api-Key", api_key: "sk-tc-full-secret" }`
6. `body.is_active` equals `false`

**Observation 2 — Success toast + redirect**:
1. Toast title equals `Tool created successfully`
2. URL becomes `/tools` within 1s

---

### TC-HAPPY-003: Create with Bearer auth

**Action**:
1. Visit `/tools/create/custom`
2. Fill required Function name, Description, URL
3. Pick Authentication = Bearer Token
4. Type `sk-bearer-abc` into the Token field
5. Click "Create"

**Observation 1 — Payload**:
1. `POST /tool/upsert_tool` body has `auth_type: "bearer"`
2. The body has `auth_config: { token: "sk-bearer-abc" }`

---

### TC-HAPPY-004: Create with Basic auth

**Action**:
1. Visit `/tools/create/custom`
2. Fill required Function name, Description, URL
3. Pick Authentication = Basic Auth
4. Fill Username `acme`, Password `s3cret`
5. Click "Create"

**Observation 1 — Payload**:
1. `POST /tool/upsert_tool` body has `auth_type: "basic"`
2. The body has `auth_config: { username: "acme", password: "s3cret" }`

---

### TC-HAPPY-005: Create with API Key auth and blank header name

**Action**:
1. Visit `/tools/create/custom`
2. Fill required Function name, Description, URL
3. Pick Authentication = API Key
4. Leave the Header input blank
5. Fill the Value field with `sk-xyz`
6. Click "Create"

**Observation 1 — Header defaults applied at save**:
1. `POST /tool/upsert_tool` body's `auth_config.header_name` equals `X-API-Key`
2. The body's `auth_config.api_key` equals `sk-xyz`

---

### TC-HAPPY-006: Template pre-fill loads custom parameters

**Action**:
1. Visit `/tools/create/custom?template_id=tpl-1`

**Observation 1 — Hydration request**:
1. Exactly one `GET /tool/get_tool?tool_id=tpl-1` request is recorded

**Observation 2 — Parameters hydrate, identity fields remain blank**:
1. The Parameters card shows a row for `query` of type `string`
2. Function name, Description, URL inputs are blank (template only seeds `parameters`)

**API mock**: `GET /tool/get_tool?tool_id=tpl-1` → 200 with a custom-template tool that has `parameters.properties.query`.

---

### TC-HAPPY-007: Switch auth types preserves state

**Action**:
1. Visit `/tools/create/custom`
2. Pick Authentication = Bearer Token; type `sk-1` into the Token field
3. Pick Authentication = Basic Auth
4. Pick Authentication = Bearer Token again

**Observation 1 — Bearer token value restored**:
1. The Token input is re-rendered with value `sk-1`

---

### TC-VALIDATE-001: Blank name (RHF inline)

**Action**:
1. Visit `/tools/create/custom`
2. Leave all fields blank
3. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error under Name**:
1. Helper text under the Function name input reads `Name is required`

**Observation 3 — Button state**:
1. The Create button is NOT stuck in the `Loading...` state

---

### TC-VALIDATE-002: Blank description (RHF inline)

**Action**:
1. Visit `/tools/create/custom`
2. Type a Function name
3. Leave Description blank
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error under Description**:
1. Helper text under the Description textarea reads `Description is required`

---

### TC-VALIDATE-003: Blank URL (RHF inline)

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description
3. Leave URL blank
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error under URL**:
1. Helper text under the URL input reads `URL is required`

---

### TC-VALIDATE-004: Invalid URL (Zod url())

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description
3. Type `not-a-url` into the URL input
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error under URL**:
1. Helper text under the URL input reads `Please enter a valid URL`

---

### TC-VALIDATE-005: Whitespace-only name fails validation

**Action**:
1. Visit `/tools/create/custom`
2. Type only spaces into Function name
3. Fill Description + URL with valid values
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under the Function name reads `Name is required`

---

### TC-ERROR-001: Duplicate name (backend 409)

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name with the name of an existing tool
3. Fill Description + URL
4. Click "Create"

**Observation 1 — Error toast (verbatim detail)**:
1. Toast title equals `A tool with name 'check_inventory' already exists in this organization`

**Observation 2 — Form intact, no redirect**:
1. URL is still `/tools/create/custom`
2. Function name, Description, URL retain their typed values

**Observation 3 — Create button re-enables**:
1. The button is no longer disabled or in `Loading...` state

**API mock**: `POST /tool/upsert_tool` → 409.

---

### TC-ERROR-002: Name required at create (backend 400)

**Preconditions**: client mutation strips `name` from the payload (defensive — RHF normally blocks this).

**Action**:
1. Visit `/tools/create/custom`
2. Submit a payload missing the `name` field (via direct mutation)

**Observation 1 — Toast**:
1. Toast title equals `name is required when creating a new tool`

**Observation 2 — Form stays put**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 400 with that `detail`.

---

### TC-ERROR-003: Description required at create (backend 400)

**Action**:
1. Visit `/tools/create/custom`
2. Submit a payload missing the `description` field

**Observation 1 — Toast**:
1. Toast title equals `description is required when creating a new tool`

**Observation 2 — Form stays put**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 400 with that `detail`.

---

### TC-ERROR-004: OAuth connection not found (defensive backend 400)

> ⚠ The Custom form does NOT expose an OAuth connection picker today, so this branch is mostly defensive — the OAuth-conn payload is only sent by the built-in form.

**Action**:
1. Visit `/tools/create/custom`
2. Submit a payload with `oauth_connection_id` set (via direct mutation)

**Observation 1 — Toast**:
1. Toast title equals `OAuth connection 42 not found` (verbatim `detail`)

**Observation 2 — Form stays put**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 400 `{ "detail": "OAuth connection 42 not found" }`.

---

### TC-ERROR-005: Server 500

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals `Internal server error`

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`
2. All field values are preserved

**API mock**: `POST /tool/upsert_tool` → 500.

---

### TC-ERROR-006: 422 validation (malformed body)

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Generic fallback toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is a non-string array)

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 422 with `detail: [{ type: "model_attributes_type", loc: ["body"], ... }]`.

> ⚠ unverified — confirm fallback text appears exactly.

---

### TC-ERROR-007: 401 mid-save

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — No auto-redirect to login**:
1. URL is still `/tools/create/custom` (axios interceptor does not auto-logout today)

**API mock**: `POST /tool/upsert_tool` → 401.

---

### TC-ERROR-008: Create 403 surfaces forbidden toast

**Action**:
1. As a member trying an owner-only org action, visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (forbidden message)

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 403.

---

### TC-ERROR-009: Create 404 surfaces missing-organization toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail`

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 404 (organization missing).

---

### TC-ERROR-010: Template pre-fill 404 swallowed silently

**Action**:
1. Visit `/tools/create/custom?template_id=does-not-exist`

**Observation 1 — Loader clears**:
1. `<AppLoader>` is no longer in the DOM after the GET resolves

**Observation 2 — Empty Custom form rendered, no toast**:
1. Function name, Description, URL are blank
2. No Sonner toast appears

**API mock**: `GET /tool/get_tool?tool_id=does-not-exist` → 404.

---

### TC-ERROR-011: Template pre-fill 401 falls back silently

**Action**:
1. Visit `/tools/create/custom?template_id=<id>`

**Observation 1 — Loader clears + empty Custom form**:
1. `<AppLoader>` is removed
2. The form renders blank
3. No Sonner toast appears

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 401.

---

### TC-ERROR-012: Template pre-fill 500 falls back silently

**Action**:
1. Visit `/tools/create/custom?template_id=<id>`

**Observation 1 — Loader clears + empty Custom form**:
1. `<AppLoader>` is removed
2. The form renders blank
3. No Sonner toast appears

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 500.

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create/custom`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` is recorded

---

### TC-NAV-002: Unauthenticated template visit preserves the redirect

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create/custom?template_id=<id>`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=...` is recorded
2. The encoded query (`?template_id=<id>`) is preserved in the redirect URL

---

### TC-NAV-003: Expired token redirects to login and clears cookie

**Preconditions**: expired `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create/custom`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=...` is recorded
2. The expired cookie is cleared

---

### TC-NAV-004: Non-member is denied access to custom tool create

**Preconditions**: signed-in user is NOT a member of the target organization.

**Action**:
1. Visit `/tools/create/custom`

**Observation 1 — Access denial**:
1. Either an access-denied state renders OR the URL redirects to `/home`
2. Zero `POST /tool/upsert_tool` requests are recorded

---

### TC-NAV-005: Cancel navigates back without confirmation

**Action**:
1. Visit `/tools/create/custom`
2. Fill some fields (so the form is dirty)
3. Click "Cancel"

**Observation 1 — Navigation immediate**:
1. URL becomes `/tools` (or wherever `router.back()` would go) within 1s
2. No confirmation modal appears

**Observation 2 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

---

### TC-NAV-006: Template route flips to built-in form

**Action**:
1. Visit `/tools/create/custom?template_id=tpl-built-in-1`

**Observation 1 — Page swaps to BuiltInToolForm**:
1. After the GET resolves, the Custom-tool form's specific inputs (Function name, URL, ParameterBuilder) are NOT in the DOM
2. The built-in form's section (e.g. OAuth connection picker) is rendered

> ⚠ Routing oddity — the URL says `custom` but the form rendered is built-in.

**API mock**: `GET /tool/get_tool?tool_id=tpl-built-in-1` → 200 with `{ tool_type: "google_calendar", is_template: true, parameters: {} }`.

---

### TC-LOADING-001: Slow save disables the create button and shows loading text

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Click "Create" against a slow backend (>3 seconds)

**Observation 1 — Button state**:
1. Create button text becomes `Loading...`
2. Create button has the `disabled` attribute
3. The Save icon is replaced by a `Loader2` spinner

**Observation 2 — Double-submit blocked**:
1. Clicking Create again during the in-flight call records exactly one `POST /tool/upsert_tool`

---

### TC-LOADING-002: Slow template fetch keeps the loader visible

**Action**:
1. Visit `/tools/create/custom?template_id=<id>` against a slow `GET /tool/get_tool` (>3 seconds)

**Observation 1 — Loader visible the entire time**:
1. `<AppLoader label="Loading…">` is in the DOM the whole time
2. No flash of empty form occurs

---

### TC-LOADING-003: Double submit guard records one request

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Click "Create" twice in rapid succession (≤100 ms apart)

**Observation 1 — Network**:
1. Exactly one `POST /tool/upsert_tool` request is recorded

**Observation 2 — Button state**:
1. The button flips to `Loading...` + `disabled` on the first click
2. The second click is a no-op

---

### TC-EDGE-001: Parameter row with empty name is dropped silently

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL
3. Click "Add parameter"; leave the Name field blank but fill the description
4. Click "Create"

**Observation 1 — Payload omits the empty-name row**:
1. `POST /tool/upsert_tool` body's `parameters.properties` does NOT contain an empty-string key

---

### TC-EDGE-002: Two parameter rows with the same name — last wins

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL
3. Click "Add parameter"; fill name `query` and description A
4. Click "Add parameter"; fill name `query` and description B
5. Click "Create"

**Observation 1 — Last value wins**:
1. `POST /tool/upsert_tool` body's `parameters.properties.query.description` equals B

**Observation 2 — No client-side warning**:
1. No inline duplicate-name warning is shown

> ⚠ This is a UI quirk — consider adding a duplicate-name guard in the future.

---

### TC-EDGE-003: Switching auth type wipes the visible field but keeps the value

**Action**:
1. Visit `/tools/create/custom`
2. Pick Authentication = API Key
3. Type `sk-1` into the Value field
4. Pick Authentication = Bearer Token

**Observation 1 — API Key Value input unmounts**:
1. The API Key Value input is no longer in the DOM

**Observation 2 — Switching back restores the value**:
1. Picking Authentication = API Key again shows the Value field pre-populated with `sk-1`

**Observation 3 — Submitting under Bearer sends blank token**:
1. Clicking Create at this point records `POST /tool/upsert_tool` with `auth_config: { token: "" }`

---

### TC-EDGE-004: Back during in-flight save

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"
3. Before the response returns, click the back arrow

**Observation 1 — Navigation immediate**:
1. URL becomes `/tools` (or `router.back()` target) without waiting for the response

**Observation 2 — Pending request resolves silently**:
1. If the request errors after unmount, no Sonner toast is shown ⚠ unverified — Sonner may still queue the toast

---

### TC-EDGE-005: Network failure (request aborted)

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Click "Create" with the network forced offline

**Observation 1 — Error toast (default fallback)**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Form intact, saving cleared**:
1. URL is still `/tools/create/custom`
2. All field values are preserved
3. The Create button is no longer disabled

**API mock**: `route.abort('failed')` on save.

---

### TC-EDGE-006: Network drop after typing but before Create

**Action**:
1. Visit `/tools/create/custom`
2. Fill every field with non-default values
3. Force a transient network drop (offline) then restore
4. Click "Create"

**Observation 1 — All values preserved across the drop**:
1. After restoring connectivity, every typed value is still in the form

**Observation 2 — Save fires with full body**:
1. `POST /tool/upsert_tool` body contains every typed field

---

### TC-EDGE-007: Concurrent duplicate name 409 surfaces toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name with a value that another user creates concurrently
3. Click "Create"

**Observation 1 — Toast (verbatim detail)**:
1. Toast title equals the backend `detail` (typically the verbatim duplicate-name message)

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`
2. All field values are preserved

**API mock**: `POST /tool/upsert_tool` → 409.

---

### TC-EDGE-008: Leading/trailing whitespace in name and description is trimmed on save

**Action**:
1. Visit `/tools/create/custom`
2. Type `  __e2e__leading_trailing  ` into Function name
3. Type `  __e2e__ description has padding  ` into Description
4. Fill URL with a valid URL
5. Click "Create"

**Observation 1 — Reload shows trimmed values**:
1. After landing on `/tools` and entering `/tools/edit/<new id>`, Function name input equals `__e2e__leading_trailing`
2. Description textarea content's outer whitespace is removed

> ⚠ unverified whether trim happens client-side or server-side — assert end-state.

---

### TC-EDGE-009: Special chars and unicode round-trip without xss

**Action**:
1. Visit `/tools/create/custom`
2. Type `<script>alert(1)</script>`, emoji, and unicode into Function name, Description, URL placeholder, and a parameter description
3. Click "Create"

**Observation 1 — Payload carries verbatim**:
1. `POST /tool/upsert_tool` body's fields contain the literal characters typed

**Observation 2 — Reload renders text verbatim**:
1. After reload via `/tools/edit/<new id>`, every persisted value appears as plain text
2. `window.alert` was NOT invoked

---

### TC-EDGE-010: Very long description (>500 chars) is bounded with feedback

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + URL
3. Paste a 600-character string into Description
4. Click "Create"

**Observation 1 — Either accepted or bounded**:
1. EITHER the form saves and the description appears verbatim after reload OR a helpful inline error appears
2. The page does NOT crash

---

### TC-EDGE-011: URL whitespace handling is consistent

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description
3. Type `  https://api.acme.com/x  ` (leading + trailing space) into URL
4. Click "Create"

**Observation 1 — Either trimmed or rejected**:
1. EITHER the form saves and the persisted URL equals `https://api.acme.com/x` (trimmed) OR the inline error reads `Please enter a valid URL`

> ⚠ unverified — assert whichever the current behaviour is.

---

### TC-EDGE-012: Pasting newlines into URL strips them

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description
3. Paste multiline content into the URL input
4. Click "Create"

**Observation 1 — Single-line URL passes Zod**:
1. Either the resulting URL passes Zod `url()` validation (because the newlines were stripped) and saves, OR the inline error reads `Please enter a valid URL`

---

### TC-EDGE-013: Large parameter list serializes correctly

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL
3. Click "Add parameter" 10 times; fill each row with distinct names and types
4. Click "Create"

**Observation 1 — All rows serialize**:
1. `POST /tool/upsert_tool` body's `parameters.properties` contains 10 keys
2. The Parameters count badge reads `10`

**Observation 2 — Reload renders all rows**:
1. After reload via `/tools/edit/<new id>`, the Parameters card shows 10 rows with their saved values

---

### TC-EDGE-014: Long API Key secret round-trips encrypted

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Pick API Key auth
4. Fill API Key Header `X-Test` and Value with a >1000-character secret
5. Click "Create"

**Observation 1 — Payload carries the full secret**:
1. `POST /tool/upsert_tool` body's `auth_config.api_key` equals the typed string

**Observation 2 — Reload decrypts to the same value**:
1. After reload via `/tools/edit/<new id>`, the API Key Value input equals the original typed string verbatim

---

### TC-EDGE-015: Unicode bearer token round-trips encrypted

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Pick Bearer Token auth
4. Type a bearer token containing unicode and special chars
5. Click "Create"

**Observation 1 — Payload carries verbatim**:
1. `POST /tool/upsert_tool` body's `auth_config.token` equals the typed string

**Observation 2 — Reload decrypts to the same value**:
1. After reload via `/tools/edit/<new id>`, the Bearer Token input equals the original typed string verbatim

---

### TC-A11Y-001: Tab order through the form reaches every control

**Action**:
1. Visit `/tools/create/custom`
2. Focus the Function name input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Order**:
1. Focus moves Name → Description → Active → Method → URL → Add parameter → Authentication → Cancel → Create
2. No focusable element is skipped or reached twice

---

### TC-A11Y-002: Enter on URL input triggers create

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL with valid values
3. Focus the URL input and press `Enter`

**Observation 1 — Submit fires**:
1. Exactly one `POST /tool/upsert_tool` request is recorded

---

### TC-A11Y-003: Validation errors are announced via aria-live

**Action**:
1. Visit `/tools/create/custom`
2. Click "Create" with all fields blank

**Observation 1 — First error announced**:
1. The helper text containing `Name is required` (and subsequent errors `URL is required` / `Please enter a valid URL` where applicable) is rendered inside an element with `role="alert"` (or `aria-live="polite"`)

---

### TC-A11Y-004: Save spinner is announced to assistive tech

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Click "Create" against a slow backend

**Observation 1 — Busy state announced**:
1. Create button has `aria-busy="true"` OR its accessible name changes to `Loading...`
2. The `disabled` attribute is set (screen reader announces "disabled")

---

### TC-A11Y-005: Trash icon is reachable regardless of hover state

**Action**:
1. Visit `/tools/create/custom`
2. Click "Add parameter"
3. Without hovering, inspect the trash icon button

**Observation 1 — Accessible label**:
1. The trash icon button has `aria-label="Remove parameter"`
2. The button is focusable via Tab even though it is `opacity-0` visually

---

### TC-FULL-001: Fills every field, saves, reloads, verifies, and deletes

**Preconditions**:
- Authenticated against a real backend; no existing tool named `__e2e__book_room`

**Action**:
1. Authenticate and visit `/tools/create/custom`
2. Type `__e2e__book_room` into Function name
3. Type `__e2e__ Books a hotel room.` into Description
4. Set Method to `PUT`
5. Type `https://api.acme.com/rooms/{room_id}/book` into URL
6. Click "Add parameter"; fill name `room_id`, type `string`, description `Resource path id`, Required ON
7. Click "Add parameter"; fill name `nights`, type `number`, description `Stay duration`, Required OFF
8. Cycle Authentication: pick Bearer Token, type a value; pick Basic Auth, fill username + password; pick API Key
9. Fill API Key Header `X-Test-Api-Key` and Value `sk-__e2e__-secret`
10. Toggle the Active checkbox OFF
11. Click "Create"
12. After landing on `/tools`, locate the new row and click into `/tools/edit/<new id>` to verify persistence
13. Return to `/tools`, open the row's action menu, click Delete, and confirm

**Observation 1 — Save fires once**:
1. Exactly one `POST /tool/upsert_tool` request is recorded for step 11
2. The body has no `id` field

**Observation 2 — Success toast + redirect**:
1. Toast title equals `Tool created successfully`
2. URL becomes `/tools` within 1s

**Observation 3 — Reload rehydrates every persisted field**:
1. Function name input value equals `__e2e__book_room`
2. Description textarea value equals `__e2e__ Books a hotel room.`
3. URL input value equals `https://api.acme.com/rooms/{room_id}/book`
4. Method select reads `PUT`
5. Active checkbox is unchecked
6. The Parameters card shows two rows (`room_id` string + Required ON; `nights` number + Required OFF) with the saved descriptions
7. Authentication select reads `API Key`
8. API Key Header input value equals `X-Test-Api-Key`
9. API Key Value input value equals `sk-__e2e__-secret` (decrypted on GET)

**Observation 4 — Cleanup deletes the tool**:
1. The DELETE call from step 13 records `DELETE /tool/delete_tool?tool_id=<id>`
2. Toast `Tool deleted successfully` appears
3. The row is no longer present on `/tools`

**Cleanup** (in `finally`):
1. If the per-row delete failed, call the backend directly to remove the throw-away tool by id

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above or is covered elsewhere)

- [x] Unauthenticated access → see TC-NAV-001
- [x] No unsaved-changes guard on Cancel/Back — see TC-NAV-005
- [x] Template `?template_id` with built-in `tool_type` flips to `BuiltInToolForm` — see TC-NAV-006
- [x] Switching auth type retains per-type state — see TC-EDGE-003
- [x] API Key header defaults to `X-API-Key` if blank at save time — see TC-HAPPY-005
- [x] Parameter rows with empty name are stripped silently — see TC-EDGE-001
- [x] Duplicate parameter names overwrite each other — see TC-EDGE-002
- [x] Network failure on save — see TC-EDGE-005
- [x] Special chars / unicode / XSS — see TC-EDGE-009
- [x] Very long description — see TC-EDGE-010
- [x] Long encrypted secret round-trip — see TC-EDGE-014
- [x] Unicode bearer token round-trip — see TC-EDGE-015
- [x] Large parameter list serialises — see TC-EDGE-013
- [x] Save spinner / double-submit guard — see TC-LOADING-001, TC-LOADING-003

Other documented but not separately scenario-ised edges:

- Method defaults to POST when missing/loaded as empty
- Top-bar title reflects RHF's live `name` value — typing into Name updates the bar immediately
- Trash icon is `opacity-0` until hover; tests that need to click it should `click({ force: true })`
- `loading` state on the page: when `?template_id` is in the URL, `loading === true` for the duration of `GET /tool/get_tool`; the page renders `<AppLoader>` until the template arrives
- Form fields use shared `TextInput` / `TextAreaField` — error helperText appears inline; do not pass `error` to a parent FormRow (would duplicate the message)
- The `tool_type === 'custom'` path in `ToolFormPage` does NOT support OAuth connection / `oauth_connection_id` in the UI; only the built-in path does
- `executeSave` only redirects to `/tools` when `isEditMode === false` (create mode); edit mode stays on the page and just updates `saved` to true
- `useFacetedList` is not used on this page — there's no list to filter
- Saving with parameter rows whose Required is checked but Name is blank: the row is dropped, so the `required` array on the JSON-Schema omits it (no orphan entry)

---

## Business Rules

- Custom tool authoring is one of two branches under `/tools/create` (the other being built-in templates). Visiting `/tools/create/custom` directly skips the chooser.
- The form is shared with `/tools/edit/<id>` via `ToolFormPage`; create-mode differs by: no Delete button, top-bar title "New Tool", primary button reads "Create", and successful save redirects to `/tools` (edit-mode stays on the page).
- `upsert_tool` is the single create-or-update endpoint (the `PUT /tool/update_tool` route in the Postman collection is marked BUGGY and not used by the frontend).
- Auth credentials are stored AES-encrypted on the server (`core/utils/encryption.py`); the frontend only ever sees plaintext values it submits, and after reload the values are returned decrypted by `GET /tool/get_tool`.
- The Custom tool's `tool_type` is always `custom` on the backend; the frontend doesn't send it explicitly on create (the backend defaults it).
- Method is normalized to uppercase by `ToolFormPage` (`(tool.method ?? '').toUpperCase()` on load); on save the frontend sends whatever the SelectInput has set, which is always one of the uppercase variants.
- `is_active` defaults to `true` on a fresh create; toggling Active before saving sends `is_active: false`.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order through the form reaches every control — see TC-A11Y-001
- [x] Enter on the URL input triggers Create — see TC-A11Y-002
- [x] Validation errors are announced via `role="alert"` / `aria-live` — see TC-A11Y-003
- [x] Save spinner is announced to assistive tech — see TC-A11Y-004
- [x] Trash icon is reachable regardless of hover — see TC-A11Y-005

Other documented but not separately scenario-ised a11y bullets:

- Page heading hierarchy: the form does not render an `<h1>` (dashboard layout owns the heading); the top-bar tool name is a `<span>`. Tests that assert page identity should use the back-arrow `aria-label="Back"` or the Cancel button.
- Back arrow has `aria-label="Back"`
- All `TextInput` / `TextAreaField` instances render an associated `<Typography>` label (shared component default)
- Method `SelectInput` exposes the verb as text; the chip on the right is decorative
- Active checkbox renders via shared `CheckboxField` with `id="tool-is-active"` and an associated label
- Parameter Required checkbox is associated with the row via `id={`param-req-${row.id}`}`
- Helper text under inputs is rendered as `helperText` (shared component) so it is associated with the input for assistive tech
- Cancel / Create buttons are keyboard reachable; Enter activates Create; Escape does NOT auto-cancel (intentional — there is no unsaved-changes guard, so Escape would silently lose work)
- Conditional auth sections (`api_key` / `bearer` / `basic`) mount inputs with consistent label text so SR users always know which auth scheme is active

---

## Scenario ID Mapping

| Old scenario ID | New TC ID         | Spec test name                                                          |
| --------------- | ----------------- | ----------------------------------------------------------------------- |
| PS-1            | TC-HAPPY-001      | minimum-required create succeeds                                        |
| PS-2            | TC-HAPPY-002      | create with full param + auth combo                                     |
| PS-3            | TC-HAPPY-003      | create with Bearer auth                                                 |
| PS-4            | TC-HAPPY-004      | create with Basic auth                                                  |
| PS-5            | TC-HAPPY-005      | create with API Key auth and blank header name                          |
| PS-6            | TC-HAPPY-006      | template pre-fill loads custom parameters                               |
| PS-7            | TC-HAPPY-007      | switch auth types preserves state                                       |
| FS-1            | TC-VALIDATE-001   | blank name (RHF inline)                                                 |
| FS-2            | TC-VALIDATE-002   | blank description (RHF inline)                                          |
| FS-3            | TC-VALIDATE-003   | blank URL (RHF inline)                                                  |
| FS-4            | TC-VALIDATE-004   | invalid URL (Zod `url()`)                                               |
| FS-5            | TC-ERROR-001      | duplicate name (backend 409)                                            |
| FS-6            | TC-ERROR-002      | name required at create (backend 400)                                   |
| FS-7            | TC-ERROR-003      | description required at create (backend 400)                            |
| FS-8            | TC-ERROR-004      | OAuth connection not found (backend 400)                                |
| FS-9            | TC-ERROR-005      | server 500                                                              |
| FS-10           | TC-EDGE-005       | network failure (request aborted)                                       |
| FS-11           | TC-ERROR-006      | 422 validation (malformed body)                                         |
| FS-12           | TC-ERROR-010      | template pre-fill 404 swallowed                                         |
| FS-13           | TC-EDGE-001       | parameter row with empty name is dropped silently                       |
| FS-14           | TC-EDGE-002       | two parameter rows with the same name                                   |
| FS-15           | TC-EDGE-003       | switch auth type after typing wipes the visible field                   |
| FS-16           | TC-LOADING-003    | double submit guard                                                     |
| FS-17           | TC-EDGE-004       | back during in-flight save                                              |
| FS-18           | TC-ERROR-007      | 401 mid-save                                                            |
| FS-19           | TC-NAV-006        | template route flips to built-in form                                   |
| FS-20           | TC-NAV-001        | auth gating redirect                                                    |
| TCC-001         | TC-NAV-001        | unauthenticated visit redirects to login                                |
| TCC-002         | TC-NAV-002        | unauthenticated template visit redirects with redirect preserved        |
| TCC-003         | TC-NAV-003        | expired token redirects to login and clears cookie                      |
| TCC-004         | TC-NAV-004        | non-member is denied access to custom tool create                       |
| TCC-005         | TC-ERROR-008      | create 403 surfaces forbidden toast                                     |
| TCC-006         | TC-ERROR-009      | create 404 surfaces missing-organization toast                          |
| TCC-007         | TC-ERROR-011      | template pre-fill 401 falls back silently                               |
| TCC-008         | TC-ERROR-012      | template pre-fill 500 falls back silently                               |
| TCC-009         | TC-LOADING-001    | slow save disables the create button and shows loading text             |
| TCC-010         | TC-LOADING-002    | slow template fetch keeps the loader visible                            |
| TCC-011         | TC-EDGE-006       | form data survives a transient network drop                             |
| TCC-012         | TC-EDGE-007       | concurrent duplicate name 409 surfaces toast                            |
| TCC-013         | TC-VALIDATE-005   | whitespace-only name fails validation                                   |
| TCC-014         | TC-EDGE-008       | name and description are trimmed on save                                |
| TCC-015         | TC-EDGE-009       | special chars and unicode round-trip without xss                        |
| TCC-016         | TC-EDGE-010       | very long description is bounded with feedback                          |
| TCC-017         | TC-EDGE-011       | URL whitespace handling is consistent                                   |
| TCC-018         | TC-EDGE-012       | pasting newlines into URL strips them                                   |
| TCC-019         | TC-EDGE-013       | large parameter list serializes correctly                               |
| TCC-020         | TC-EDGE-014       | long api key secret round-trips encrypted                               |
| TCC-021         | TC-EDGE-015       | unicode bearer token round-trips encrypted                              |
| TCC-022         | TC-A11Y-001       | tab order through the form reaches every control                        |
| TCC-023         | TC-A11Y-002       | enter on URL input triggers create                                      |
| TCC-024         | TC-A11Y-003       | validation errors are announced via aria-live                           |
| TCC-025         | TC-A11Y-004       | save spinner is announced to assistive tech                             |
| TCC-026         | TC-A11Y-005       | trash icon is reachable regardless of hover state                       |
| TCC-FULL        | TC-FULL-001       | fills every field, saves, reloads, verifies, and deletes                |
