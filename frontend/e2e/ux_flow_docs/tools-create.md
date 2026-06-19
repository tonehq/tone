# Feature Doc: Tools — Create Flow

Feature documentation for the Tools create flow rooted at `/tools/create` (chooser) and
`/tools/create/custom` (custom form). Used by `/generate-tests tools-create` (or
`--docs e2e/ux_flow_docs/tools-create.md`) to ensure all positive and negative
scenarios are covered. The deeper custom-form internals (every field, every auth
type, every edge case) live in `tools-create-custom.md`; this doc covers the
chooser + the higher-level create flow.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## User Stories

- As a user, I can preview the type picker at `/tools/create` and pick between a
  custom tool and a built-in template.
- As a user, picking a template tile pre-fills the custom form via the
  `template_id` query parameter so I can tweak and save.
- As a user, I can create a new **custom** tool from `/tools/create/custom` with a
  name, description, HTTP method, URL, parameter schema, and authentication
  credentials.
- As a user, my secrets (api key, bearer token, basic password) are persisted such
  that the form rehydrates them on edit.

---

## Routes

| Route                                        | Component                                          |
| -------------------------------------------- | -------------------------------------------------- |
| `/tools/create`                              | `ToolCreatePage` (type picker)                     |
| `/tools/create/custom`                       | `ToolFormPage` (no `toolId`, no template)          |
| `/tools/create/custom?template_id={id}`      | `ToolFormPage` pre-filled from `GET /tool/get_tool`|

---

## Key Files

- `src/components/tools/ToolCreatePage.tsx` — type picker.
- `src/components/tools/ToolFormPage.tsx` — owns the form state, save, redirect.
- `src/components/tools/CustomToolForm.tsx` — every Custom-tool field.
- `src/components/tools/ParameterBuilder.tsx` — repeating parameter rows.
- `src/atoms/ToolAtom.tsx` — `upsertToolAtom`, `fetchToolsAtom`.
- `src/services/toolService.ts` — axios calls (`/tool/upsert_tool`, `/tool/get_tool`, …).
- `src/schemas/tool.ts` — Zod schemas for the custom form.

---

## API Endpoints Exercised

| Method | Path                                       | Triggered by                                          |
| ------ | ------------------------------------------ | ----------------------------------------------------- |
| GET    | `/tool/get_template_tools`                 | Picker — list of built-in templates                   |
| GET    | `/tool/get_tool?tool_id={template_id}`     | Picker — pre-fill from template                       |
| POST   | `/tool/upsert_tool`                        | Create or save (no body `id` → create)                |
| DELETE | `/tool/delete_tool?tool_id={id}`           | Per-row Delete on the `/tools` list (cleanup)         |

---

## TC-FULL Field Coverage

`TC-FULL-001` exercises every writable Custom-tool control end-to-end. Each row maps
a section to the form field, the selector in `frontend/src/components/tools/CustomToolForm.tsx`
or `ParameterBuilder.tsx`, the helper used in `frontend/e2e/helpers/toolFixtures.ts`,
and whether persistence is asserted after reload.

| Section          | Field                  | Selector                            | Helper                       | Asserted on reload         |
| ---------------- | ---------------------- | ----------------------------------- | ---------------------------- | -------------------------- |
| Tool definition  | Function name          | `input[name="name"]`                | inline `fill`                | yes                        |
| Tool definition  | Description            | `textarea[name="description"]`      | inline `fill`                | yes                        |
| Tool definition  | Active toggle          | `#tool-is-active`                   | inline click                 | yes                        |
| Request          | HTTP method            | `button[name="tool-method"]`        | `setHttpMethod()`            | — (catalog)                |
| Request          | URL                    | `input[name="url"]`                 | inline `fill`                | yes                        |
| Parameters       | Add row × 2            | `button[name^="param-name-"]`       | `addParameter()`             | row count is yes           |
| Parameters       | Param name             | `input[name="param-name-{rowId}"]`  | `addParameter({ name })`     | —                          |
| Parameters       | Param type             | `button[name="param-type-{rowId}"]` | `addParameter({ type })`     | —                          |
| Parameters       | Param description      | `input[name="param-desc-{rowId}"]`  | `addParameter({ description })` | —                       |
| Parameters       | Param required         | `#param-req-{rowId}`                | `addParameter({ required })` | —                          |
| Authentication   | Auth type              | `button[name="tool-auth-type"]`     | `setAuthType()`              | yes (via downstream fields)|
| Authentication   | API Key header         | `input[name="tool-auth-header"]`    | inline `fill`                | yes                        |
| Authentication   | API Key value          | `input[name="tool-auth-api-key"]`   | inline `fill`                | yes (decrypted on GET)     |
| Authentication   | Bearer token           | `input[name="tool-auth-bearer"]`    | inline `fill`                | covered by TC-FULL on edit |
| Authentication   | Basic username         | `input[name="tool-auth-username"]`  | inline `fill`                | —                          |
| Authentication   | Basic password         | `input[name="tool-auth-password"]`  | inline `fill`                | —                          |

Notes:

- The HTTP method, parameter type, and auth type are catalog-driven shadcn dropdowns; the spec verifies they save without error rather than re-asserting the exact label.
- `auth_config` is encrypted on POST/PUT and decrypted on GET (`core/services/tool_service.py:95,176,208,304`), so the API Key header + value DO round-trip and the spec asserts them after reload.
- Helpers are best-effort: if a select option isn't visible (e.g. catalog miss), `pickSelectOptionByLabel()` returns `false` and the test fails clearly rather than continuing with a stale value.

---

## Cleanup

Real-backend writes are namespaced with `__e2e__` in tool names. Each test that
saves a tool also deletes it (via the per-row Delete icon on the `/tools` list,
which calls `DELETE /tool/delete_tool`). Custom tools have no Delete button on
the edit page — only built-in tools expose one via the kebab menu — so the
list-page delete is the canonical cleanup path.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Picker renders the Custom tile and built-in templates

**Preconditions**: authenticated.

**Action**:
1. Visit `/tools/create`

**Observation 1 — Custom tile present**:
1. A "Custom Tool" tile is rendered
2. The tile is clickable

**Observation 2 — Built-in templates section**:
1. `GET /tool/get_template_tools` is recorded
2. Each template returned in the response renders as a tile in the built-in section

---

### TC-HAPPY-002: Clicking Custom Tool navigates to /tools/create/custom

**Action**:
1. Visit `/tools/create`
2. Click the "Custom Tool" tile

**Observation 1 — Navigation**:
1. URL becomes `/tools/create/custom`

**Observation 2 — Custom form renders**:
1. The Function name input is visible
2. The Description textarea is visible
3. The Cancel + Create buttons are visible in the header

---

### TC-HAPPY-003: Header shows Cancel + Create (no Delete) in create mode

**Action**:
1. Visit `/tools/create/custom`

**Observation 1 — Header buttons**:
1. A Cancel button is visible
2. A Create button is visible
3. No Delete button is rendered in create mode

---

### TC-HAPPY-004: HTTP method dropdown exposes all five verbs

**Action**:
1. Visit `/tools/create/custom`
2. Open the method dropdown

**Observation 1 — All verbs visible**:
1. The options list contains `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

---

### TC-HAPPY-005: Active checkbox toggles

**Action**:
1. Visit `/tools/create/custom`
2. Click the Active checkbox

**Observation 1 — State flip**:
1. The checkbox state changes from checked → unchecked (it defaults to ON)
2. Clicking it again restores the previous state

---

### TC-HAPPY-006: Adding a parameter renders its row controls

**Action**:
1. Visit `/tools/create/custom`
2. Click "Add parameter"

**Observation 1 — New row appears**:
1. A parameter row is rendered with name input, type select, description input, Required checkbox, and trash icon
2. The Parameters card's count badge increments

---

### TC-HAPPY-007: Removing a parameter clears its row

**Action**:
1. Visit `/tools/create/custom`
2. Click "Add parameter"
3. Hover the row to reveal the trash icon
4. Click the trash icon

**Observation 1 — Row removed**:
1. The parameter row is no longer in the DOM
2. The Parameters count badge decrements (or hides when 0)

---

### TC-HAPPY-008: Selecting API Key reveals header + value

**Action**:
1. Visit `/tools/create/custom`
2. Open the Authentication select and pick "API Key"

**Observation 1 — Conditional fields render**:
1. A Header `TextInput` is visible
2. A Value `TextInput` (password) is visible

---

### TC-HAPPY-009: Selecting Bearer reveals only the token field

**Action**:
1. Visit `/tools/create/custom`
2. Open the Authentication select and pick "Bearer Token"

**Observation 1 — Conditional fields render**:
1. Only a Token (password) input is visible
2. Header / Value / Username / Password fields are NOT in the DOM

---

### TC-HAPPY-010: Selecting Basic reveals username + password

**Action**:
1. Visit `/tools/create/custom`
2. Open the Authentication select and pick "Basic Auth"

**Observation 1 — Conditional fields render**:
1. A Username `TextInput` is visible
2. A Password `TextInput` (password) is visible

---

### TC-HAPPY-011: Switching back to No Authentication hides conditional fields

**Action**:
1. Visit `/tools/create/custom`
2. Pick "API Key", then pick "Bearer Token", then pick "Basic Auth"
3. Pick "No Authentication"

**Observation 1 — Conditional sections disappear**:
1. No Header, Value, Token, Username, or Password fields are in the DOM
2. Only the Authentication select remains visible in this section

---

### TC-HAPPY-012: Minimum-required create posts the form and redirects to /tools

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name `__e2e__check_inventory`
3. Fill Description `Checks product inventory and returns availability.`
4. Leave Method = POST (default)
5. Fill URL `https://api.example.com/inventory`
6. Click "Create"

**Observation 1 — Network call**:
1. Exactly one `POST /tool/upsert_tool` request is recorded
2. The request body equals `{ name, description, url, method: "POST", parameters: {}, auth_type: "none", auth_config: null, is_active: true }` (no `id`)

**Observation 2 — Success toast**:
1. Sonner toast title equals `Tool created successfully`

**Observation 3 — Redirect**:
1. URL becomes `/tools` within 1s

**Cleanup**:
1. Delete the new tool via per-row Delete on `/tools`

---

### TC-NAV-001: Clicking a template tile pre-fills the form (deferred)

> ⚠ Deferred (`test.fixme`) — depends on the seed catalog. When seeded, the
> click on a template tile should navigate to `/tools/create/custom?template_id=<id>`
> and pre-fill the form via `GET /tool/get_tool?tool_id=<template_id>`.

---

### TC-NAV-002: Unauthenticated picker visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools%2Fcreate` is recorded

---

### TC-NAV-003: Unauthenticated custom visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create/custom`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` is recorded

---

### TC-NAV-004: Expired token on picker redirects to login

**Preconditions**: expired `tone_access_token` cookie.

**Action**:
1. Visit `/tools/create`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=...` is recorded
2. The expired cookie is cleared

---

### TC-NAV-005: Non-member is denied access to tools create

**Preconditions**: signed-in user is NOT a member of the target organization.

**Action**:
1. Visit `/tools/create`

**Observation 1 — Access denied / redirect**:
1. Either an access-denied state renders OR the URL redirects to `/home`
2. Zero `GET /tool/get_template_tools` requests are recorded

---

### TC-VALIDATE-001: Blank name + Create surfaces an inline error

**Action**:
1. Visit `/tools/create/custom`
2. Leave the Function name blank
3. Fill Description + URL with valid values
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Function name reads `Name is required` (or `Required`)

---

### TC-VALIDATE-002: Blank description + Create surfaces an inline error

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + URL with valid values
3. Leave Description blank
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Description reads `Description is required` (or `Required`)

---

### TC-VALIDATE-003: Invalid URL + Create surfaces an inline error

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description with valid values
3. Type `not-a-url` into URL
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under URL reads `Please enter a valid URL`

---

### TC-ERROR-001: Duplicate name create surfaces an error toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name with the name of an existing tool
3. Fill Description + URL with valid values
4. Click "Create"

**Observation 1 — Form stays put**:
1. URL is still `/tools/create/custom`
2. All input values are preserved

**Observation 2 — Error toast**:
1. Sonner toast title equals the backend `detail` (typically the verbatim
   `A tool with name '<name>' already exists in this organization`)

**API mock**: `POST /tool/upsert_tool` → 409.

---

### TC-ERROR-002: Create 401 surfaces error toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail`

**Observation 2 — Form intact, no auto-redirect**:
1. URL is still `/tools/create/custom`
2. All field values are preserved

**API mock**: `POST /tool/upsert_tool` → 401.

---

### TC-ERROR-003: Create 403 surfaces forbidden toast

**Action**:
1. As a member (with limited org permissions), visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (forbidden message)

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 403.

---

### TC-ERROR-004: Create 422 falls back to generic error toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Generic toast**:
1. Toast title equals `Something went wrong. Please try again.` (because `detail` is a non-string array)

**Observation 2 — Form intact**:
1. URL is still `/tools/create/custom`

**API mock**: `POST /tool/upsert_tool` → 422 with `detail: [{...}]`.

---

### TC-ERROR-005: Create 500 surfaces generic error toast

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields and click "Create"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` string

**Observation 2 — Create button re-enables**:
1. The Create button is no longer disabled / no longer reads `Loading...`

**API mock**: `POST /tool/upsert_tool` → 500.

---

### TC-ERROR-006: template-list 500 falls back to custom-only picker

**Action**:
1. Visit `/tools/create`

**Observation 1 — Custom tile present**:
1. The Custom Tool tile renders

**Observation 2 — No template tiles, no toast**:
1. No template tile is rendered
2. No Sonner toast appears

**API mock**: `GET /tool/get_template_tools` → 500.

---

### TC-ERROR-007: template pre-fill 500 falls back silently

**Action**:
1. Visit `/tools/create/custom?template_id=<id>`

**Observation 1 — Loader clears**:
1. `<AppLoader>` is removed from the DOM after the GET resolves

**Observation 2 — Empty Custom form**:
1. Function name, Description, URL are blank
2. Parameters builder is in its empty state
3. No Sonner toast appears

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 500.

---

### TC-LOADING-001: Slow save disables the create button and shows loading text

**Action**:
1. Visit `/tools/create/custom`
2. Fill required fields
3. Click "Create" against a slow backend (>3 seconds)

**Observation 1 — Button state**:
1. Create button text becomes `Loading...`
2. Create button has the `disabled` attribute

**Observation 2 — Double-submit blocked**:
1. Clicking Create again during the in-flight call records exactly one `POST /tool/upsert_tool`

---

### TC-LOADING-002: Slow template list keeps the custom tile usable

**Action**:
1. Visit `/tools/create` against a slow `GET /tool/get_template_tools` (>3 seconds)

**Observation 1 — Custom tile remains interactive**:
1. The Custom Tool tile is rendered and clickable
2. The templates section shows a skeleton or loader (not blocking the page)

---

### TC-EDGE-001: Network failure on save preserves the form

**Action**:
1. Visit `/tools/create/custom`
2. Fill every field with non-default values
3. Click "Create" with the network forced offline

**Observation 1 — Error toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — All values retained**:
1. Function name, Description, URL, Active state, parameter rows, and auth fields keep their typed values

**API mock**: route aborted with `failed` status.

---

### TC-EDGE-002: Parameter rows survive a transient network drop

**Action**:
1. Visit `/tools/create/custom`
2. Add 3 parameter rows and fill each
3. Force a transient network drop (offline) then restore
4. Click "Create"

**Observation 1 — Rows preserved across the drop**:
1. After restoring connectivity, the 3 parameter rows are still visible with their typed values

**Observation 2 — Save fires with all params**:
1. `POST /tool/upsert_tool` body's `parameters.properties` contains keys for all 3 rows

---

### TC-EDGE-003: Whitespace-only name fails validation

**Action**:
1. Visit `/tools/create/custom`
2. Type only spaces into the Function name input
3. Fill Description + URL with valid values
4. Click "Create"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under Function name reads `Name is required` (or `Required`)

---

### TC-EDGE-004: Name and description are trimmed on save

**Action**:
1. Visit `/tools/create/custom`
2. Type `  __e2e__trim_name  ` into Function name (leading/trailing spaces)
3. Type `  __e2e__ description  ` into Description
4. Fill URL with a valid URL
5. Click "Create"

**Observation 1 — Reload shows trimmed values**:
1. After navigating to `/tools/edit/<new id>`, Function name input equals `__e2e__trim_name`
2. Description textarea equals `__e2e__ description` (the inner whitespace is preserved; only outer is trimmed)

> ⚠ unverified whether trimming happens client-side or server-side — assert end-state.

---

### TC-EDGE-005: Special chars and unicode round-trip without xss

**Action**:
1. Visit `/tools/create/custom`
2. Type `<script>alert(1)</script>` + emoji + unicode into Function name, Description, URL placeholder, and a parameter description
3. Click "Create"

**Observation 1 — Payload carries verbatim**:
1. `POST /tool/upsert_tool` body fields carry the literal characters typed

**Observation 2 — Reload renders text verbatim**:
1. After reload via `/tools/edit/<new id>`, all values appear as plain text
2. `window.alert` was NOT invoked

---

### TC-EDGE-006: Very long URL is bounded with feedback

**Action**:
1. Visit `/tools/create/custom`
2. Type a 600-character URL into the URL input
3. Click "Create"

**Observation 1 — Either accepted or rejected**:
1. EITHER the form saves and the new URL appears after reload OR a helpful inline error message appears
2. The page does NOT crash

---

### TC-EDGE-007: Pasting newlines into URL strips them

**Action**:
1. Visit `/tools/create/custom`
2. Paste multiline content into the URL input
3. Fill Function name + Description
4. Click "Create"

**Observation 1 — Saved URL is single-line**:
1. After reload, the URL input value does NOT contain `\n`

---

### TC-EDGE-008: Parameter name whitespace is trimmed before serialize

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL
3. Add a parameter row with `  trimmed_param  ` (whitespace) as its Name
4. Click "Create"

**Observation 1 — Payload key has no surrounding whitespace**:
1. `POST /tool/upsert_tool` body's `parameters.properties` contains `trimmed_param` (NOT `  trimmed_param  `)

---

### TC-EDGE-009: Parameter description accepts special characters

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name + Description + URL
3. Add a parameter row with a description containing emoji, unicode, and `<script>`
4. Click "Create"

**Observation 1 — Payload carries verbatim**:
1. The parameter's `description` in the payload equals the literal typed string

**Observation 2 — Reload renders text verbatim**:
1. After reload, the parameter description input shows the same string with no XSS execution

---

### TC-A11Y-001: Tab order through the form reaches every control

**Action**:
1. Visit `/tools/create/custom`
2. Focus the Function name input
3. Press `Tab` repeatedly

**Observation 1 — Order**:
1. Focus moves Name → Description → Method → URL → Add parameter → Authentication → Cancel → Create
2. No focusable element is skipped or reached twice

---

### TC-A11Y-002: Enter on name input triggers create

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name, Description, and URL with valid values
3. Focus the Function name input and press `Enter`

**Observation 1 — Submit fires**:
1. Exactly one `POST /tool/upsert_tool` request is recorded

---

### TC-A11Y-003: Validation error is announced via aria-live

**Action**:
1. Visit `/tools/create/custom`
2. Click "Create" with all fields blank

**Observation 1 — Error announced**:
1. The first inline helper text is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text equals the matching Zod message

---

### TC-A11Y-004: Trash icon is reachable to assistive tech regardless of hover

**Action**:
1. Visit `/tools/create/custom`
2. Add a parameter row
3. Without hovering, inspect the trash icon button

**Observation 1 — Accessible label**:
1. The trash icon button has `aria-label="Remove parameter"`
2. The button is focusable (Tab reaches it) even though the icon is `opacity-0` visually

---

### TC-FULL-001: Fills every field + 2 parameters, saves, reloads, and verifies persistence

**Preconditions**: authenticated; no existing tool named `__e2e__full_create`.

**Action**:
1. Visit `/tools/create/custom`
2. Fill Function name `__e2e__full_create`
3. Fill Description `__e2e__ comprehensive create coverage`
4. Set Method to `PUT`
5. Fill URL `https://api.example.com/full/{id}/save`
6. Click "Add parameter" twice; fill row 1 (name `id`, type `string`, description `Path id`, Required ON) and row 2 (name `count`, type `number`, description `Count`)
7. Toggle the Active checkbox off
8. Cycle Authentication: Bearer Token (type token) → Basic Auth (fill username + password) → API Key
9. Fill API Key Header `X-Test-Api-Key` + Value `sk-__e2e__-secret`
10. Click "Create"
11. After landing on `/tools`, locate the new row and click into `/tools/edit/<new id>`
12. After verifying, navigate back to `/tools` and per-row Delete the tool

**Observation 1 — Save fires once**:
1. Exactly one `POST /tool/upsert_tool` is recorded
2. The body has no `id` field

**Observation 2 — Success toast and redirect**:
1. Toast title equals `Tool created successfully`
2. URL becomes `/tools` within 1s

**Observation 3 — Reload rehydrates every persisted field**:
1. Function name equals `__e2e__full_create`
2. Description equals `__e2e__ comprehensive create coverage`
3. URL equals the typed URL
4. Method select reads `PUT`
5. Active checkbox is unchecked
6. Two parameter rows are visible with the saved name / type / description / required values
7. Authentication select reads `API Key`
8. API Key Header value equals `X-Test-Api-Key`
9. API Key Value equals `sk-__e2e__-secret` (decrypted on GET)

**Observation 4 — Cleanup deletes the tool**:
1. The DELETE call from step 12 records `DELETE /tool/delete_tool?tool_id=<id>`
2. Toast `Tool deleted successfully` appears
3. The row is no longer present on `/tools`

**Cleanup** (in `finally`):
1. If the per-row delete failed, call the backend directly to remove the throw-away tool by id

---

## Coverage map (which scenarios TC-FULL-001 transitively exercises)

| Scenario              | Transitively covered by TC-FULL-001? | Notes                                      |
| --------------------- | ------------------------------------ | ------------------------------------------ |
| TC-HAPPY-003 (header) | yes                                  | implicit (Create button is clicked)        |
| TC-HAPPY-004 (method) | yes                                  | PUT is picked                              |
| TC-HAPPY-005 (Active) | yes                                  | toggled and re-asserted                    |
| TC-HAPPY-006 (Add)    | yes                                  | called twice                               |
| TC-HAPPY-008 (API Key)| yes                                  | filled + reloaded                          |
| TC-HAPPY-009 (Bearer) | yes                                  | cycled through                             |
| TC-HAPPY-010 (Basic)  | yes                                  | cycled through                             |
| TC-HAPPY-011 (switch) | yes                                  | cycled bearer → basic → api_key            |
| TC-HAPPY-012 (Save)   | yes                                  | the FULL flow ends in a real save          |

Scenarios still tracked only via `test.fixme` (TC-NAV-001 template pre-fill, built-in
variants like Google Calendar / SMS) are NOT exercised by TC-FULL-001 — they need
additional org seed data (built-in templates, OAuth connections, Twilio credentials).

---

## Edge Cases

- Empty `/tool/get_template_tools` → the picker still renders the Custom tile (covered by TC-HAPPY-001 + TC-HAPPY-002).
- 409 unique-name conflict → covered by TC-ERROR-001.
- Server 500 on save → covered by TC-ERROR-005.

---

## Out of Scope (covered elsewhere)

- Edit flow → `tools-edit.md`.
- List page, search, sort, pagination → `tools.md`.
- Custom-form internals at full depth (every field, every error, every quirk) → `tools-create-custom.md`.
- Built-in tool variants (Google Calendar, SMS, Sheets) → deferred behind `test.fixme` placeholders.

---

## Scenario ID Mapping

| Old scenario ID | New TC ID         | Spec test name                                                         |
| --------------- | ----------------- | ---------------------------------------------------------------------- |
| TC-001          | TC-HAPPY-001      | picker renders the Custom tile and built-in templates                  |
| TC-002          | TC-HAPPY-002      | clicking Custom Tool navigates to /tools/create/custom                 |
| TC-003          | TC-NAV-001        | (deferred — `test.fixme`)                                              |
| TC-004          | TC-HAPPY-003      | header shows Cancel + Create (no Delete in create mode)                |
| TC-005          | TC-VALIDATE-001   | blank name + Create surfaces an inline error                           |
| TC-006          | TC-VALIDATE-002   | blank description + Create surfaces an inline error                    |
| TC-007          | TC-VALIDATE-003   | invalid URL + Create surfaces an inline error                          |
| TC-008          | TC-HAPPY-004      | HTTP method dropdown exposes all five verbs                            |
| TC-009          | TC-HAPPY-005      | Active checkbox toggles                                                |
| TC-010          | TC-HAPPY-006      | adding a parameter renders its row controls                            |
| TC-011          | TC-HAPPY-007      | removing a parameter clears its row                                    |
| TC-012          | TC-HAPPY-008      | selecting API Key reveals header + value                               |
| TC-013          | TC-HAPPY-009      | selecting Bearer reveals only the token field                          |
| TC-014          | TC-HAPPY-010      | selecting Basic reveals username + password                            |
| TC-015          | TC-HAPPY-011      | switching back to No Authentication hides conditional fields           |
| TC-016          | TC-HAPPY-012      | minimum-required create posts the form and redirects to /tools         |
| TC-017          | TC-ERROR-001      | duplicate-name create surfaces an error toast                          |
| TC-018          | TC-NAV-002        | unauthenticated picker visit redirects to login                        |
| TC-019          | TC-NAV-003        | unauthenticated custom visit redirects to login                        |
| TC-020          | TC-NAV-004        | expired token on picker redirects to login                             |
| TC-021          | TC-NAV-005        | non-member is denied access to tools create                            |
| TC-022          | TC-ERROR-002      | create 401 surfaces error toast                                        |
| TC-023          | TC-ERROR-003      | create 403 surfaces forbidden toast                                    |
| TC-024          | TC-ERROR-004      | create 422 falls back to generic error toast                           |
| TC-025          | TC-ERROR-005      | create 500 surfaces generic error toast                                |
| TC-026          | TC-ERROR-006      | template-list 500 falls back to custom-only picker                     |
| TC-027          | TC-ERROR-007      | template pre-fill 500 falls back silently                              |
| TC-028          | TC-EDGE-001       | network failure on save preserves the form                             |
| TC-029          | TC-LOADING-001    | slow save disables the create button and shows loading text            |
| TC-030          | TC-LOADING-002    | slow template list keeps the custom tile usable                        |
| TC-031          | TC-EDGE-002       | parameter rows survive a transient network drop                        |
| TC-032          | TC-EDGE-003       | whitespace-only name fails validation                                  |
| TC-033          | TC-EDGE-004       | name and description are trimmed on save                               |
| TC-034          | TC-EDGE-005       | special chars and unicode round-trip without xss                       |
| TC-035          | TC-EDGE-006       | very long URL is bounded with feedback                                 |
| TC-036          | TC-EDGE-007       | pasting newlines into URL strips them                                  |
| TC-037          | TC-EDGE-008       | parameter name whitespace is trimmed before serialize                  |
| TC-038          | TC-EDGE-009       | parameter description accepts special characters                       |
| TC-039          | TC-A11Y-001       | tab order through the form reaches every control                       |
| TC-040          | TC-A11Y-002       | enter on name input triggers create                                    |
| TC-041          | TC-A11Y-003       | validation error is announced via aria-live                            |
| TC-042          | TC-A11Y-004       | trash icon is reachable to assistive tech regardless of hover          |
| TC-FULL         | TC-FULL-001       | fills every field + 2 parameters, saves, reloads, and verifies persistence |
