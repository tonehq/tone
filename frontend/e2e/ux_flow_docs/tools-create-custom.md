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

**As an** agent owner, **I want to** declare each parameter with a name,
type, description, and required flag, **so that** the LLM produces correct
call arguments.

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

## User Workflow Steps

Step-by-step actions per major flow. Used to derive `test(...)` blocks in
`e2e/dashboard/tools-create.spec.ts`. Toast assertions use
`page.locator('[data-sonner-toast]')`.

**WF-1: Author a minimal custom tool** (positive — US-1..US-5)

1. User authenticates and navigates to `/tools/create/custom` → expected: top bar shows "New Tool" + Cancel + Create; no Delete button; the form's Active checkbox is checked.
2. User types `check_inventory` in the name input → expected: top bar header flips to `check_inventory`.
3. User types `Checks product inventory and returns availability.` in the description.
4. User leaves method = POST (default), types `https://api.example.com/inventory` in the URL field.
5. User clicks Create → expected: `customToolSchema` passes; `POST /tool/upsert_tool` fires with `{ name, description, url, method: 'POST', parameters: {}, auth_type: 'none', auth_config: null, is_active: true }`; on 200, toast `Tool created successfully`; URL changes to `/tools`.

**WF-2: Add parameters via the builder** (positive — US-3)

1. User clicks the dashed "Add parameter" → expected: a parameter row appears with name input (focus on entry), type select (default `string`), description input, Required checkbox.
2. User types `product_id` → ticks Required → expected: serialized schema becomes `{ type: 'object', properties: { product_id: { type: 'string', description: '' } }, required: ['product_id'] }`.
3. User clicks "Add parameter" again → fills `limit`, type `number` → expected: schema has both keys; the Parameters count badge reads `2`.
4. User hovers row 1 → the trash icon opacity becomes 1 → clicks it → expected: row 1 is removed and serialized schema drops `product_id`.

**WF-3: Cycle through auth types** (positive — US-4)

1. User picks `Bearer Token` → expected: only a Token (password) input appears.
2. User types `sk-bearer-123` → switches to `Basic Auth` → expected: Token input unmounts; Username + Password appear. The form state retains `authBearerToken === 'sk-bearer-123'` (so flipping back to Bearer restores it).
3. User switches to `API Key` → fills Header `X-Custom-Auth` + Value `sk-api-xyz`.
4. User switches back to `No Authentication` → expected: all four conditional inputs are gone; on save `auth_config` is `null`.

**WF-4: Save validation errors surface inline** (negative — US-1, US-2)

1. User clicks Create with all fields blank → expected: inline helper text "Required" (or the Zod `Name is required` message) appears below the first invalid field; no network call is fired.
2. User types a name, leaves description blank, clicks Create → expected: inline error below Description; no network call.
3. User fills name + description, types `not-a-url` in URL, clicks Create → expected: inline error "Please enter a valid URL"; no network call.

**WF-5: Save duplicate name** (negative — US-5)

1. User fills the form with the name of an existing tool, clicks Create.
2. `POST /tool/upsert_tool` returns 409 → expected: toast title `A tool with name '<name>' already exists in this organization`; user remains on `/tools/create/custom`; the form retains its values; Create button re-enables.

**WF-6: Template pre-fill** (positive — US-7)

1. User visits `/tools/create/custom?template_id=550e8400-tmpl-002` → expected: `GET /tool/get_tool?tool_id=550e8400-tmpl-002` fires; loader spinner shows briefly; if the template's `tool_type` is `custom`, the parameters builder pre-populates with the template's keys.

**WF-7: Cancel** (positive — US-6)

1. User makes some changes → clicks Cancel → expected: `router.back()` (or `/tools` fallback); no confirmation modal.

**WF-8: Auth gating** (negative)

1. Unauthenticated user visits `/tools/create/custom` → expected: 307 redirect → `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom`.

---

## Input Specifications

### `customToolSchema` (Zod)

Source: `src/schemas/tool.ts` (lines 10-14).

| Field         | Type     | Required | Validation Rules                                                       | Exact Error Message              |
| ------------- | -------- | -------- | ---------------------------------------------------------------------- | -------------------------------- |
| Function name | text     | yes      | `z.string().min(1, 'Name is required')`                                 | `Name is required`               |
| Description   | textarea | yes      | `z.string().min(1, 'Description is required')`                          | `Description is required`        |
| URL           | text     | yes      | `z.string().min(1, 'URL is required').url('Please enter a valid URL')` | `URL is required` / `Please enter a valid URL` |

### Other form state (not Zod-validated)

| Field            | Type      | Required | Validation                                                          | Notes                                                              |
| ---------------- | --------- | -------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Method           | select    | yes      | One of `GET / POST / PUT / DELETE / PATCH`; default POST            | Stored as uppercase                                                |
| Active           | checkbox  | no       | default ON                                                          | `is_active` boolean on the payload                                  |
| Authentication   | select    | no       | `none / api_key / bearer / basic`; default `none`                    | Drives which conditional auth fields render                        |
| Auth header name | text      | conditional | Required-feel when `auth_type === 'api_key'`; blank → defaults to `X-API-Key` on save | Saved under `auth_config.header_name` |
| Auth API key     | password  | conditional | When `api_key`, value is saved under `auth_config.api_key`         |                                                                    |
| Auth bearer token| password  | conditional | When `bearer`, value is saved under `auth_config.token`             |                                                                    |
| Auth username    | text      | conditional | When `basic`, value is saved under `auth_config.username`           |                                                                    |
| Auth password    | password  | conditional | When `basic`, value is saved under `auth_config.password`           |                                                                    |
| Parameters       | repeater  | no       | Rows with empty `name.trim()` are silently dropped on serialize     | Serialized to JSON-Schema `{ type, properties, required? }`         |

### Button state rules

- Create button is `loading=true` and `disabled` while `saving === true`; loading text renders as `Loading...` (CustomButton convention).
- Cancel/Back are never disabled.
- Save icon (Save) swaps to `Loader2` spinner while saving.

---

## Success Scenarios

**PS-1: Minimum-required create succeeds** (US-1..US-5)

- **Preconditions**: authenticated; no tool named `check_inventory` exists.
- **Steps**: navigate to `/tools/create/custom` → fill name `check_inventory`, description `Probe.`, URL `https://api.example.com/inventory` → Create.
- **Expected outcome**: `POST /tool/upsert_tool` fires; toast title `Tool created successfully`; redirects to `/tools`.
- **Mock API** (`POST /tool/upsert_tool`, 200):
  ```json
  {
    "id": "550e8400-newt-001",
    "name": "check_inventory",
    "description": "Probe.",
    "tool_type": "custom",
    "url": "https://api.example.com/inventory",
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

**PS-2: Create with full param + auth combo** (US-3, US-4, US-5)

- **Preconditions**: authenticated.
- **Steps**: fill name `book_room`, description `Books a hotel room.`, URL `https://api.acme.com/rooms/{room_id}/book`, method PUT, add params `room_id (string, required, Resource path id)` + `nights (number, optional, Stay duration)`, auth API Key with header `X-Test-Api-Key` + value `sk-tc-full-secret`, toggle Active OFF → Create.
- **Expected outcome**: `POST /tool/upsert_tool` body matches:
  ```json
  {
    "name": "book_room",
    "description": "Books a hotel room.",
    "url": "https://api.acme.com/rooms/{room_id}/book",
    "method": "PUT",
    "parameters": {
      "type": "object",
      "properties": {
        "room_id": { "type": "string", "description": "Resource path id" },
        "nights": { "type": "number", "description": "Stay duration" }
      },
      "required": ["room_id"]
    },
    "auth_type": "api_key",
    "auth_config": { "header_name": "X-Test-Api-Key", "api_key": "sk-tc-full-secret" },
    "is_active": false
  }
  ```

  Response (200) carries the same fields plus a generated `id`. UI: toast `Tool created successfully`; redirect to `/tools`.

**PS-3: Create with Bearer auth**

- **Steps**: pick Bearer Token → fill token `sk-bearer-abc` → Create.
- **Expected payload**:
  ```json
  { "auth_type": "bearer", "auth_config": { "token": "sk-bearer-abc" } }
  ```

**PS-4: Create with Basic auth**

- **Steps**: pick Basic Auth → fill username `acme` + password `s3cret` → Create.
- **Expected payload**:
  ```json
  { "auth_type": "basic", "auth_config": { "username": "acme", "password": "s3cret" } }
  ```

**PS-5: Create with API Key auth and blank header name**

- **Steps**: pick API Key, leave the Header input blank, fill Value → Create.
- **Expected payload**: `auth_config.header_name === 'X-API-Key'` (default applied at save time).

**PS-6: Template pre-fill loads custom parameters**

- **Steps**: navigate to `/tools/create/custom?template_id=tpl-1`.
- **Mock API** (`GET /tool/get_tool?tool_id=tpl-1`, 200):
  ```json
  {
    "id": "tpl-1",
    "name": "scaffold",
    "tool_type": "custom",
    "is_template": true,
    "parameters": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Search query" }
      }
    }
  }
  ```
- **Expected UI**: parameters builder hydrates with the `query` row; name + description + URL remain blank (template only seeds `parameters`).

**PS-7: Switch auth types preserves state**

- **Steps**: fill bearer `sk-1` → switch to basic → switch back to bearer.
- **Expected UI**: Token input re-renders with value `sk-1` (state was retained in `ToolFormPage` even though the section unmounted).

---

## Failure Scenarios

**FS-1: Blank name (RHF inline)**

- **Steps**: leave all fields blank, click Create.
- **Mock API**: not called — Zod blocks submit.
- **Expected UI**: inline helper text under Name reads `Name is required`; Create button is not stuck in loading.

**FS-2: Blank description (RHF inline)**

- **Steps**: type a name, leave description blank, click Create.
- **Expected UI**: inline helper text under Description reads `Description is required`; no network call.

**FS-3: Blank URL (RHF inline)**

- **Steps**: type name + description, leave URL blank, click Create.
- **Expected UI**: inline helper text under URL reads `URL is required`.

**FS-4: Invalid URL (Zod `url()`)**

- **Steps**: type `not-a-url` in URL.
- **Expected UI**: inline helper text under URL reads `Please enter a valid URL`.

**FS-5: Duplicate name (backend 409)**

- **Mock API** (`POST /tool/upsert_tool`, 409): `{ "detail": "A tool with name 'check_inventory' already exists in this organization" }`
- **Expected UI**: `handleApiError` shows the `detail` verbatim as the toast title; user remains on `/tools/create/custom`; the form retains its values; `saving` flips back to false.

**FS-6: name required at create (backend 400)**

- **Preconditions**: client mutation strips `name` from the payload (defensive — RHF normally blocks this).
- **Mock API** (`POST /tool/upsert_tool`, 400): `{ "detail": "name is required when creating a new tool" }`
- **Expected UI**: toast title is that exact `detail`; form stays put.

**FS-7: description required at create (backend 400)**

- **Mock API** (`POST /tool/upsert_tool`, 400): `{ "detail": "description is required when creating a new tool" }`
- **Expected UI**: toast title matches; form stays put.

**FS-8: OAuth connection not found (backend 400)**

- **Mock API** (`POST /tool/upsert_tool`, 400): `{ "detail": "OAuth connection 42 not found" }`
- **Expected UI**: toast title matches; form stays put. ⚠ The Custom form does NOT expose an OAuth connection picker today, so this branch is mostly defensive — the OAuth-conn payload is only sent by the built-in form.

**FS-9: Server 500**

- **Mock API** (`POST /tool/upsert_tool`, 500): `{ "detail": "Internal server error" }`
- **Expected UI**: toast title `Internal server error`; form stays put.

**FS-10: Network failure (request aborted)**

- **Mock API**: `route.abort('failed')` on save.
- **Expected UI**: `handleApiError` falls back to `Something went wrong. Please try again.` (the default when `detail` is not a string); form stays put; `saving` flips back.

**FS-11: 422 validation (malformed body)**

- **Mock API** (`POST /tool/upsert_tool`, 422):
  ```json
  { "detail": [{ "type": "model_attributes_type", "loc": ["body"], "msg": "Input should be a valid dictionary or object to extract fields from", "input": "not-a-json-object" }] }
  ```
- **Expected UI**: `handleApiError` sees a non-string `detail` and falls back to `Something went wrong. Please try again.` ⚠ unverified — confirm fallback text appears.

**FS-12: Template pre-fill 404 swallowed**

- **Steps**: visit `/tools/create/custom?template_id=does-not-exist`.
- **Mock API** (`GET /tool/get_tool?tool_id=does-not-exist`, 404): `{ "detail": "Tool not found" }`
- **Expected UI**: loader spinner clears; no toast; form opens in the default empty-custom state (the `.catch(() => {})` in `ToolFormPage` swallows the error).

**FS-13: Parameter row with empty name is dropped silently**

- **Steps**: add a parameter row, leave the Name field blank, fill description → Create.
- **Expected UI**: payload's `parameters.properties` does NOT contain an empty-string key — `rowsToSchema` skips rows where `name.trim()` is empty.

**FS-14: Two parameter rows with the same name**

- **Steps**: add two rows both named `query` with different descriptions → Create.
- **Expected UI**: payload's `parameters.properties.query` carries the LAST row's value (object spread semantics); no client-side warning. ⚠ This is a UI quirk — consider adding a duplicate-name guard in the future.

**FS-15: Switch auth type after typing wipes the visible field**

- **Steps**: pick API Key → type Value `sk-1` → switch to Bearer.
- **Expected UI**: API Key input unmounts; the value `sk-1` is held in `ToolFormPage`'s `authApiKey` state, so switching back to API Key restores it (per PS-7). Submitting under Bearer sends `auth_config: { token: '' }` because `authBearerToken` is blank.

**FS-16: Double submit guard**

- **Steps**: user clicks Create twice quickly.
- **Expected UI**: the first click flips `saving` to true and the Create button becomes `disabled` + loading; the second click is blocked. Only one `POST /tool/upsert_tool` fires.

**FS-17: Back during in-flight save**

- **Steps**: click Create → before the response, click the back arrow.
- **Expected UI**: navigation completes immediately (no guard). The pending request resolves in the background; if it errors, no toast surfaces (component unmounted). ⚠ unverified — if `handleApiError` runs on an unmounted component, Sonner still queues the toast. Confirm.

**FS-18: 401 mid-save**

- **Mock API** (`POST /tool/upsert_tool`, 401): `{ "detail": "Could not validate credentials" }`
- **Expected UI**: toast title matches; no auto-redirect to login (axios interceptor does not auto-logout today).

**FS-19: Template route flips to built-in form**

- **Steps**: visit `/tools/create/custom?template_id=tpl-built-in-1` where the template has `tool_type: 'google_calendar'`.
- **Mock API** (`GET /tool/get_tool`, 200):
  ```json
  { "id": "tpl-built-in-1", "name": "google_calendar", "tool_type": "google_calendar", "is_template": true, "parameters": {} }
  ```
- **Expected UI**: `ToolFormPage` sets `toolType` to `google_calendar`, so the page swaps to `BuiltInToolForm` (NOT `CustomToolForm`). Tests for `/tools/create/custom` should NOT assert custom-only inputs in this case. ⚠ This is a routing oddity — the URL says `custom` but the form rendered is built-in.

**FS-20: Auth gating redirect**

- **Preconditions**: no `tone_access_token` cookie.
- **Steps**: visit `/tools/create/custom`.
- **Expected UI**: 307 redirect → `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom`.

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
| Bearer Token — Token input    | TextInput (password) | label "Token", placeholder "Enter bearer token"                       | Saved as `auth_config.token`                                     |
| Basic Auth — Username input   | TextInput        | label "Username", placeholder "username"                                 | Saved as `auth_config.username`                                  |
| Basic Auth — Password input   | TextInput (password) | label "Password", placeholder "password"                              | Saved as `auth_config.password`                                  |

---

## Navigation

| Trigger                                          | Destination                                       | Condition                                |
| ------------------------------------------------ | ------------------------------------------------- | ---------------------------------------- |
| Click back arrow / Cancel                        | `router.back()` → fallback `/tools`              | Always (no unsaved-changes guard)        |
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
| `/tool/get_tool`          | GET    | `?tool_id=<uuid>`                                                                                                          | `200 Tool`                       | `404 { "detail": "Tool not found" }`                                                                         |

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

## Edge Cases

- [ ] Unauthenticated access → middleware redirect to `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom`
- [ ] No unsaved-changes guard — Cancel + Back leave immediately even mid-edit
- [ ] Template `?template_id` with built-in `tool_type` flips to `BuiltInToolForm` at the same URL (URL still says `/tools/create/custom`)
- [ ] Switching auth type retains per-type state in `ToolFormPage` so re-selecting restores values
- [ ] API Key header defaults to `X-API-Key` if blank at save time
- [ ] Method defaults to POST when missing/loaded as empty
- [ ] Parameter rows with empty name are stripped silently on serialize
- [ ] Duplicate parameter names overwrite each other (no client warning) ⚠ quirk
- [ ] Top-bar title reflects RHF's live `name` value — typing into Name updates the bar immediately
- [ ] Trash icon on a parameter row is `opacity-0` until hover; tests that need to click it should `click({ force: true })` (matches the existing `tools-create.spec.ts` pattern)
- [ ] Save spinner: Create button's `loading` prop renders "Loading..." text; the `Save` icon swaps to `Loader2` spinner
- [ ] `loading` state on the page: when `?template_id` is in the URL, `loading === true` for the duration of `GET /tool/get_tool`; the page renders `<AppLoader label="Loading…" />` until the template arrives
- [ ] Form fields use shared `TextInput` / `TextAreaField` — error helperText appears inline; do not pass `error` to a parent FormRow (would duplicate the message)
- [ ] The `tool_type === 'custom'` path in `ToolFormPage` does NOT support OAuth connection / `oauth_connection_id` in the UI; only the built-in path does
- [ ] `executeSave` only redirects to `/tools` when `isEditMode === false` (create mode); edit mode stays on the page and just updates `saved` to true
- [ ] `useFacetedList` is not used on this page — there's no list to filter
- [ ] Saving with parameter rows whose Required is checked but Name is blank: the row is dropped, so the `required` array on the JSON-Schema omits it (no orphan entry)

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

## Accessibility Requirements

- [ ] Page heading hierarchy: the form does not render an `<h1>` (the dashboard layout's heading is elsewhere); the top bar's tool name is a `<span>`. Tests that assert page identity should use the back-arrow `aria-label="Back"` or the Cancel button.
- [ ] Back arrow has `aria-label="Back"`
- [ ] All `TextInput` / `TextAreaField` instances render an associated `<Typography>` label (shared component default)
- [ ] Method `SelectInput` exposes the verb as text; chip on the right is decorative
- [ ] Active checkbox renders via shared `CheckboxField` with `id="tool-is-active"` and an associated label
- [ ] Parameter Required checkbox is associated with the row via `id={`param-req-${row.id}`}`
- [ ] Trash icons on parameter rows have `aria-label="Remove parameter"` (always exposed to screen readers even though opacity is 0 visually)
- [ ] Helper text under inputs is rendered as `helperText` (shared component) so it is associated with the input for assistive tech
- [ ] Cancel / Create buttons are keyboard reachable; Enter activates Create; Escape does NOT auto-cancel (intentional — there's no unsaved-changes guard, so Escape would silently lose work)
- [ ] Conditional auth sections (`api_key` / `bearer` / `basic`) mount inputs with consistent label text so SR users always know which auth scheme is active

---

## Appended Scenarios (gap-fill, ID prefix `TCC-`)

These rows extend the original PS/FS coverage with auth, error-state, network, input-edge-case, accessibility and lifecycle scenarios so `/generate-tests` can produce a comprehensive Custom-tool create spec. Real-backend conventions apply (`__e2e__` prefix, try/finally cleanup in the same test body); no `page.route` mocks unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-001 | Visit `/tools/create/custom` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` | `unauthenticated visit redirects to login` |
| TCC-002 | Visit `/tools/create/custom?template_id=<id>` without auth | Middleware 307 → `/auth/login?redirect=…` (encoded query preserved) | `unauthenticated template visit redirects with redirect preserved` |
| TCC-003 | Visit with an expired token | Middleware 307 → `/auth/login?redirect=…`; expired cookie cleared | `expired token redirects to login and clears cookie` |
| TCC-004 | Non-member tries to author a custom tool | Access-denied / `/home` redirect; no `POST /tool/upsert_tool` fires | `non-member is denied access to custom tool create` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-005 | `POST /tool/upsert_tool` returns 403 (member tries owner-only org action) | Toast with backend `detail`; form intact | `create 403 surfaces forbidden toast` |
| TCC-006 | `POST /tool/upsert_tool` returns 404 (organization missing) | Toast with backend `detail`; form intact | `create 404 surfaces missing-organization toast` |
| TCC-007 | `GET /tool/get_tool` for `template_id` returns 401 | Loader clears; form falls back to empty Custom state; no toast | `template pre-fill 401 falls back silently` |
| TCC-008 | `GET /tool/get_tool` for `template_id` returns 500 | Loader clears; form falls back to empty Custom state; no toast | `template pre-fill 500 falls back silently` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-009 | Slow `POST /tool/upsert_tool` (>3s) | Create button shows `Loading...` + `disabled` until response; second click blocked | `slow save disables the create button and shows loading text` |
| TCC-010 | Slow `GET /tool/get_tool?tool_id=<template>` (>3s) | `<AppLoader>` visible the whole time; no premature blank-form render | `slow template fetch keeps the loader visible` |
| TCC-011 | Network drop after typing every field, before clicking Create | Local state preserved; subsequent Create after network restoration fires the payload with the full body | `form data survives a transient network drop` |
| TCC-012 | Concurrent edit — duplicate name created by another user mid-form returns 409 on Create | Toast with backend `detail`; user stays on form with values | `concurrent duplicate name 409 surfaces toast` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-013 | Whitespace-only Function name | Inline `Name is required` Zod error; no `POST /tool/upsert_tool` fires | `whitespace-only name fails validation` |
| TCC-014 | Leading/trailing whitespace in name and description | Trimmed before persist (or backend trims); reloaded tool shows trimmed values | `name and description are trimmed on save` |
| TCC-015 | Special chars (`<script>alert(1)</script>`, emoji, unicode) in name, description, URL placeholder | Accepted; round-trip on reload renders text verbatim; no XSS execution | `special chars and unicode round-trip without xss` |
| TCC-016 | Very long description (>500 chars) | Accepted or truncated with helpful message; no client crash | `very long description is bounded with feedback` |
| TCC-017 | URL with leading/trailing whitespace | Trimmed before Zod `url()` check OR rejected with `Please enter a valid URL` | `URL whitespace handling is consistent` |
| TCC-018 | Paste multiline content into single-line URL input | Newlines stripped; resulting URL passes Zod `url()` validation only if otherwise valid | `pasting newlines into URL strips them` |
| TCC-019 | Add 10+ parameter rows | All rows serialize into `parameters.properties`; row count badge updates; payload roundtrips on reload | `large parameter list serializes correctly` |
| TCC-020 | API Key Value with very long secret (>1000 chars) | Persisted encrypted; decrypted on reload matches verbatim | `long api key secret round-trips encrypted` |
| TCC-021 | Bearer token with unicode / special chars | Persisted encrypted; decrypted on reload matches verbatim | `unicode bearer token round-trips encrypted` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-022 | Tab order through the create form | Name → Description → Active → Method → URL → Add parameter → Authentication → Cancel → Create | `tab order through the form reaches every control` |
| TCC-023 | Press Enter on the URL input | Triggers Create (primary action submit) | `enter on URL input triggers create` |
| TCC-024 | Zod validation error has `role="alert"` / aria-live | Screen readers announce `Name is required` / `URL is required` / `Please enter a valid URL` without manual focus | `validation errors are announced via aria-live` |
| TCC-025 | Loading spinner state announces busy | While saving, Create button has `aria-busy="true"` or equivalent; screen readers announce "Loading" | `save spinner is announced to assistive tech` |
| TCC-026 | Trash icon on parameter row is reachable to assistive tech | `aria-label="Remove parameter"` exposed even when `opacity-0` visually | `trash icon is reachable regardless of hover state` |

### Full lifecycle (`TCC-FULL`)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TCC-FULL | Authenticate → visit `/tools/create/custom` → fill name `__e2e__book_room` → description → set method PUT → URL `https://api.acme.com/rooms/{room_id}/book` → add two parameter rows (`room_id` string required, `nights` number optional) → cycle auth Bearer → Basic → API Key (header `X-Test-Api-Key`, value `sk-__e2e__-secret`) → toggle Active OFF → Create → assert success toast and redirect to `/tools` → reload by visiting `/tools/edit/<id>` → verify every field (name, description, URL, method, params, auth header, auth key, is_active=false) → return to `/tools` → row Delete + confirm → row gone | All filled values rehydrate after reload; encrypted secrets decrypt on GET; cleanup runs in the same test body via `try/finally` even if assertions fail mid-way | `fills every field, saves, reloads, verifies, and deletes` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| TCC-001..004 | FS-20 (auth gating redirect) | Adds template-aware redirect + role gating |
| TCC-005..008 | FS-5..FS-12 | Adds 403/404 save paths + 401/500 template pre-fill paths |
| TCC-009..012 | FS-16 (double-submit guard) | Adds slow/save/network drop + concurrent dup |
| TCC-013..021 | FS-1..FS-4, FS-13..FS-15 | Promotes basic validation into edge-case sweep + long-input + encrypted secret round-trip |
| TCC-022..026 | Accessibility checklist | Promotes a11y bullets into runnable scenarios |
| TCC-FULL | (new) | Single-test sweep of the create-custom flow with reload verification + cleanup |
