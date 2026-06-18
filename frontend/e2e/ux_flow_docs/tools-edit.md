# Feature Doc: Tools — Edit Flow

Feature documentation for the Tools edit page at `/tools/edit/<id>`. Used by
`/generate-tests tools-edit` (or `--docs e2e/ux_flow_docs/tools-edit.md`) to ensure
all positive and negative scenarios are covered.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## User Stories

### US-1: Hydrate the form from an existing tool

**As an** agent owner, **I want to** open `/tools/edit/<id>` and see every section
pre-filled with the persisted values, **so that** I can make targeted edits without
re-entering known fields.

### US-2: Persist any field change

**As an** agent owner, **I want to** change any field, click Save, and see the
updated values rehydrate after a reload, **so that** edits commit reliably.

### US-3: Round-trip encrypted secrets

**As an** agent owner, **I want to** my encrypted secrets (api key, bearer token,
basic password) to round-trip through the API and re-render on edit, **so that** I
do not have to re-supply them after every save.

### US-4: Delete from the list page

**As an** agent owner, **I want to** delete a custom tool from the `/tools` list via
the per-row Delete icon. (Built-in tools also expose Delete on the edit page via the
kebab menu; custom tools do not.)

### US-5: Handle missing / unknown tool id

**As an** agent owner, **I want to** be redirected back to `/tools` with a toast if
the tool id is missing or unknown, **so that** I never see a stale or empty editor.

---

## Page

- **Route**: `/tools/edit/<id>`
- **Component (wrapper)**: `src/app/(dashboard)/tools/edit/[id]/page.tsx`
- **Main controller**: `src/components/tools/ToolFormPage.tsx` (with `toolId` prop)
- **Custom form**: `src/components/tools/CustomToolForm.tsx`
- **Parameter builder**: `src/components/tools/ParameterBuilder.tsx`
- **List page (delete entry-point)**: `src/components/tools/ToolsListPage.tsx`
- **Service layer**: `src/services/toolService.ts` — `getTool`, `upsertTool`, `deleteTool`
- **Atoms**: `src/atoms/ToolAtom.tsx` — `upsertToolAtom`, `deleteToolAtom`, `fetchToolsAtom`
- **Auth required**: yes (middleware redirects to `/auth/login?redirect=%2Ftools%2Fedit%2F<id>` without `tone_access_token`)

---

## API Contracts

Prefix: `/api/v1`.

| Method | Path                                   | Triggered by                              |
| ------ | -------------------------------------- | ----------------------------------------- |
| GET    | `/tool/get_tool?tool_id={id}`          | Page mount (hydration)                    |
| POST   | `/tool/upsert_tool` (with `id` in body)| Save (same endpoint as create)            |
| DELETE | `/tool/delete_tool?tool_id={id}`       | Row Delete on `/tools` list (cleanup)     |

---

## TE-FULL Field Coverage

`TC-FULL-001` exercises every writable control on the edit form. Each row maps a
section to the form field, its selector, the helper used in `e2e/helpers/toolFixtures.ts`,
and whether persistence is re-asserted after reload.

| Section          | Field                                | Selector                            | Helper                  | Asserted on reload                  |
| ---------------- | ------------------------------------ | ----------------------------------- | ----------------------- | ----------------------------------- |
| Tool definition  | Description                          | `textarea[name="description"]`      | inline `fill`           | yes                                 |
| Tool definition  | Active toggle                        | `#tool-is-active`                   | inline click            | yes                                 |
| Request          | HTTP method                          | `button[name="tool-method"]`        | `setHttpMethod()`       | — (catalog)                         |
| Request          | URL                                  | `input[name="url"]`                 | inline `fill`           | yes                                 |
| Parameters       | Add row × 2                          | `button[name^="param-name-"]`       | `addParameter()`        | row count is yes                    |
| Parameters       | Param name / type / desc / required  | per-row                             | `addParameter()`        | —                                   |
| Authentication   | Auth type cycled bearer → basic → api_key | `button[name="tool-auth-type"]` | `setAuthType()`         | yes (via the api_key downstream fields) |
| Authentication   | API Key header                       | `input[name="tool-auth-header"]`    | inline `fill`           | yes                                 |
| Authentication   | API Key value                        | `input[name="tool-auth-api-key"]`   | inline `fill`           | yes (decrypted on GET)              |

Notes:

- `TC-FULL-001` uses a freshly created tool (not the shared `fixtureToolId`) so the assertions only read this test's writes.
- The shared fixture tool is restored between mutation tests (parameter removed, Active flipped back, auth reset to `none`).
- The bearer / basic credentials filled during the cycle are intentionally discarded — only the final `api_key` save is asserted on reload.
- `auth_config` is encrypted on POST/PUT and decrypted on GET (`core/services/tool_service.py:95,176,208,304`), enabling the round-trip assertions.

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.
> ID prefix legend: `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation),
> `TC-ERROR-` (server errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled),
> `TC-EDGE-` (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Hydrate the form from an existing tool

**Preconditions**:
- Authenticated; a tool exists with the id under test

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Hydration request fires**:
1. Exactly one `GET /tool/get_tool?tool_id=<id>` request is recorded
2. The page does NOT show a stale empty form before the response

**Observation 2 — Form fields pre-fill**:
1. Function name input value equals the tool's `name`
2. Description textarea value equals the tool's `description`
3. URL input value equals the tool's `url`
4. Method select reflects the tool's `method`
5. Active checkbox state mirrors the tool's `is_active`
6. Parameters builder rows mirror the tool's `parameters.properties`
7. Auth type select reflects the tool's `auth_type`, and the downstream auth fields are populated from the decrypted `auth_config`

---

### TC-HAPPY-002: Save button label reads "Save" on edit

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Header reflects edit mode**:
1. The primary action button reads `Save` (NOT `Create`)
2. Cancel button is visible to the left of Save

---

### TC-HAPPY-003: Edit description and save persists

**Action**:
1. Visit `/tools/edit/<id>`
2. Clear the Description textarea and type a new value
3. Click "Save"

**Observation 1 — Network call**:
1. Exactly one `POST /tool/upsert_tool` request is recorded
2. The request body contains the tool's `id`
3. The body's `description` equals the new value

**Observation 2 — Success toast**:
1. A Sonner toast appears in `[data-sonner-toast]` with title `Tool updated successfully`

**Observation 3 — Persistence on reload**:
1. After reload, the Description textarea shows the new value

---

### TC-HAPPY-004: Add a parameter and save persists

**Action**:
1. Visit `/tools/edit/<id>`
2. Click "Add parameter"
3. Fill the new row's name, type, description, and required flag
4. Click "Save"

**Observation 1 — Payload includes the new param**:
1. `POST /tool/upsert_tool` body's `parameters.properties` contains the new key
2. If the row was marked required, the new key appears in `parameters.required`

**Observation 2 — Reload renders the new row**:
1. After reload, the Parameters card shows the new row with the saved values

---

### TC-HAPPY-005: Toggle Active off and save persists

**Action**:
1. Visit `/tools/edit/<id>`
2. Toggle the Active checkbox off
3. Click "Save"

**Observation 1 — Payload**:
1. `POST /tool/upsert_tool` body has `is_active: false`

**Observation 2 — Reload reflects the toggle**:
1. After reload, the Active checkbox is unchecked
2. The Status pill on `/tools` reads `Inactive` for this row

---

### TC-HAPPY-006: Switch api_key → bearer and the new secret round-trips

**Action**:
1. Visit `/tools/edit/<id>` for a tool currently using `api_key`
2. Change Authentication to `Bearer Token`
3. Type a fresh bearer token
4. Click "Save"

**Observation 1 — Payload swaps auth_config shape**:
1. `POST /tool/upsert_tool` body has `auth_type: "bearer"`
2. The body has `auth_config: { token: "<the value>" }` (no leftover `header_name` / `api_key`)

**Observation 2 — Reload re-renders the bearer field**:
1. After reload, the auth type select reads `Bearer Token`
2. The Token (password) input is pre-populated with the same value (decrypted on GET)

---

### TC-HAPPY-007: Per-row Delete from /tools removes the tool

**Action**:
1. Visit `/tools`
2. Locate the row for the tool under test
3. Open the row's action menu, click Delete, and confirm

**Observation 1 — Network call**:
1. Exactly one `DELETE /tool/delete_tool?tool_id=<id>` request is recorded

**Observation 2 — Row leaves the table**:
1. After the success response, the row is no longer present in the table
2. `fl.refresh()` runs (a follow-up `POST /tool/list` is recorded)

**Observation 3 — Toast**:
1. Sonner toast title equals `Tool deleted successfully`

---

### TC-VALIDATE-001: Whitespace-only name update is rejected

**Action**:
1. Visit `/tools/edit/<id>`
2. Clear the Function name input and type only spaces
3. Click "Save"

**Observation 1 — No network call**:
1. Zero `POST /tool/upsert_tool` requests are recorded

**Observation 2 — Inline error**:
1. Helper text under the Function name input reads `Name is required`

---

### TC-VALIDATE-002: Name, description, and URL are trimmed on update

**Action**:
1. Visit `/tools/edit/<id>`
2. Replace name, description, and URL with values that have leading/trailing whitespace
3. Click "Save"

**Observation 1 — Trimmed payload OR backend trims**:
1. After reload, the Function name, Description, and URL inputs show the trimmed values

> ⚠ unverified whether trimming happens client-side or server-side — document the current behaviour.

---

### TC-ERROR-001: 404 on hydration redirects to /tools

**Action**:
1. Visit `/tools/edit/<id>` for a non-existent id

**Observation 1 — Toast surfaces via handleApiError**:
1. A Sonner toast appears with the backend `detail` string

**Observation 2 — Redirect**:
1. URL becomes `/tools` within 1s

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 404 `{ "detail": "Tool not found" }`.

---

### TC-ERROR-002: Save 400 (validation) preserves form

**Action**:
1. Visit `/tools/edit/<id>`
2. Edit any field and click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` string

**Observation 2 — Form intact**:
1. All edited fields retain their values
2. Save button re-enables (no longer in `Loading...` state)
3. URL is still `/tools/edit/<id>`

**API mock**: `POST /tool/upsert_tool` → 400 with `{ "detail": "..." }`.

---

### TC-ERROR-003: Save 401 mid-save surfaces toast (no redirect)

**Action**:
1. Visit `/tools/edit/<id>`
2. Edit a field and click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail`

**Observation 2 — Dirty fields retained, no redirect**:
1. The dirty fields retain their values
2. URL is still `/tools/edit/<id>`

**API mock**: `POST /tool/upsert_tool` → 401 `{ "detail": "Could not validate credentials" }`.

---

### TC-ERROR-004: Save 403 (member tries owner-only) surfaces forbidden toast

**Action**:
1. As a member, visit `/tools/edit/<id>` for an owner-only tool
2. Click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (forbidden message)

**Observation 2 — Form intact**:
1. URL is still `/tools/edit/<id>`
2. All values retained

**API mock**: `POST /tool/upsert_tool` → 403.

---

### TC-ERROR-005: Save 404 (tool deleted by another user) redirects

**Action**:
1. Visit `/tools/edit/<id>`
2. While the editor is open, the tool is deleted by another user
3. Click "Save"

**Observation 1 — Toast**:
1. Toast title equals `Tool not found`

**Observation 2 — Redirect**:
1. URL becomes `/tools`

**API mock**: `POST /tool/upsert_tool` → 404 `{ "detail": "Tool not found" }`.

---

### TC-ERROR-006: Save 409 (duplicate name) surfaces toast

**Action**:
1. Visit `/tools/edit/<id>`
2. Change Function name to a value that collides with another tool
3. Click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (duplicate name message)

**Observation 2 — User stays on form**:
1. URL is still `/tools/edit/<id>`
2. Form retains the typed values

**API mock**: `POST /tool/upsert_tool` → 409.

---

### TC-ERROR-007: Save 500 surfaces generic error toast

**Action**:
1. Visit `/tools/edit/<id>`
2. Edit a field and click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (e.g. `Internal server error`)

**Observation 2 — Save re-enables**:
1. Save button is no longer disabled / no longer reads `Loading...`

**API mock**: `POST /tool/upsert_tool` → 500.

---

### TC-ERROR-008: Hydration 500 surfaces error without redirect

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Toast**:
1. `handleApiError` surfaces a Sonner toast

**Observation 2 — No redirect**:
1. URL remains `/tools/edit/<id>` (500 does NOT redirect; only 404 redirects)

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 500.

---

### TC-ERROR-009: Hydration 403 (lost access) redirects to /tools

**Action**:
1. Visit `/tools/edit/<id>` after losing access mid-session

**Observation 1 — Toast**:
1. Toast title equals the backend `detail`

**Observation 2 — Redirect**:
1. URL becomes `/tools`

**API mock**: `GET /tool/get_tool?tool_id=<id>` → 403.

---

### TC-NAV-001: Unauthenticated edit visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=%2Ftools%2Fedit%2F<id>` is recorded

---

### TC-NAV-002: Expired token on edit redirects to login

**Preconditions**: `tone_access_token` cookie set but expired.

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Middleware redirect**:
1. A 307 redirect to `/auth/login?redirect=...` is recorded
2. The expired cookie is cleared

---

### TC-NAV-003: Non-member is denied access to the tool editor

**Preconditions**: signed-in user is NOT a member of the tool's organization.

**Action**:
1. Visit `/tools/edit/<id>`

**Observation 1 — Access denied / redirect**:
1. Either an access-denied state renders OR the URL redirects to `/tools`
2. Zero `GET /tool/get_tool` requests are recorded

---

### TC-LOADING-001: Slow save shows Loading... and disables the Save button

**Action**:
1. Visit `/tools/edit/<id>`
2. Edit a field
3. Click "Save" against a slow backend (>3 seconds)

**Observation 1 — Button state**:
1. Save button text becomes `Loading...`
2. Save button has the `disabled` attribute

**Observation 2 — Double-submit blocked**:
1. Clicking Save a second time during the in-flight call records exactly one `POST /tool/upsert_tool`

---

### TC-LOADING-002: Slow tool load shows loader until hydration completes

**Action**:
1. Visit `/tools/edit/<id>` against a slow backend (>3 seconds on `GET /tool/get_tool`)

**Observation 1 — Loader visibility**:
1. `<AppLoader>` is visible the whole time the GET is in flight
2. No flash of empty form occurs before hydration

---

### TC-EDGE-001: Network failure on save preserves the form

**Action**:
1. Visit `/tools/edit/<id>`
2. Edit a field
3. Click "Save" with the network forced offline

**Observation 1 — Error toast**:
1. Toast title equals `Something went wrong. Please try again.`

**Observation 2 — Dirty fields preserved**:
1. All edited fields retain their values
2. URL is still `/tools/edit/<id>`

**API mock**: route aborted with `failed` status.

---

### TC-EDGE-002: Concurrent edit conflict surfaces as a toast

**Action**:
1. Visit `/tools/edit/<id>`
2. While editing, another user updates the same tool
3. Click "Save"

**Observation 1 — Toast**:
1. Toast title equals the backend `detail` (conflict message)

**Observation 2 — Dirty fields retained**:
1. The user can reload without losing the dirty-field values OR explicitly discard

**API mock**: `POST /tool/upsert_tool` → 409 or 412.

---

### TC-EDGE-003: Special chars and unicode round-trip without xss

**Action**:
1. Visit `/tools/edit/<id>`
2. Insert `<script>alert(1)</script>`, emoji, and unicode into name, description, URL, and a parameter description
3. Click "Save"

**Observation 1 — Payload contains literal text**:
1. `POST /tool/upsert_tool` body carries the exact characters typed

**Observation 2 — Reload renders text verbatim**:
1. The persisted values appear in the inputs after reload as plain text
2. `window.alert` was NOT invoked

---

### TC-EDGE-004: Very long description (>500 chars) is bounded with feedback

**Action**:
1. Visit `/tools/edit/<id>`
2. Replace the description with a 600-character string
3. Click "Save"

**Observation 1 — Either accepted or bounded**:
1. EITHER the form saves and the new value appears after reload OR a helpful inline error appears
2. The page does not crash

---

### TC-EDGE-005: Pasting newlines into single-line inputs strips them

**Action**:
1. Visit `/tools/edit/<id>`
2. Paste multiline content into the Function name input
3. Paste multiline content into the URL input
4. Click "Save"

**Observation 1 — Saved values are single-line**:
1. After reload, neither value contains `\n`

---

### TC-EDGE-006: Whitespace-only parameter name is stripped on update

**Action**:
1. Visit `/tools/edit/<id>`
2. Add a parameter row with only whitespace in its Name field
3. Click "Save"

**Observation 1 — Payload omits the empty-name row**:
1. `POST /tool/upsert_tool` body's `parameters.properties` does NOT contain an empty-string key
2. The `required` array does NOT include an orphan entry

---

### TC-EDGE-007: Long API Key secret update round-trips encrypted

**Action**:
1. Visit `/tools/edit/<id>` for a tool with `api_key` auth
2. Replace the API Key Value with a >1000-character secret
3. Click "Save"

**Observation 1 — Payload carries the full secret**:
1. `POST /tool/upsert_tool` body's `auth_config.api_key` equals the typed string

**Observation 2 — Reload decrypts to the same value**:
1. After reload, the API Key Value input value equals the original typed string verbatim

---

### TC-A11Y-001: Tab order through the edit form

**Action**:
1. Visit `/tools/edit/<id>`
2. Focus the Function name input
3. Press `Tab` repeatedly until focus exits the form

**Observation 1 — Tab order matches design**:
1. Focus moves in the order: Name → Description → Active → Method → URL → Add parameter → Authentication → Cancel → Save
2. No focusable element is skipped or reached twice

---

### TC-A11Y-002: Enter on the URL input triggers Save

**Action**:
1. Visit `/tools/edit/<id>`
2. Focus the URL input
3. Press `Enter`

**Observation 1 — Submit fires**:
1. Exactly one `POST /tool/upsert_tool` request is recorded

---

### TC-A11Y-003: Validation errors are announced via aria-live on edit

**Action**:
1. Visit `/tools/edit/<id>`
2. Clear the Name field and click "Save"

**Observation 1 — Error announced**:
1. Helper text under Name is rendered inside an element with `role="alert"` (or `aria-live="polite"`)
2. The error text reads `Name is required`

---

### TC-A11Y-004: Save spinner is announced to assistive tech

**Action**:
1. Visit `/tools/edit/<id>`
2. Click "Save" against a slow backend

**Observation 1 — Busy state announced**:
1. Save button has `aria-busy="true"` (or its label changes to `Loading...`)
2. The `disabled` attribute is set (screen reader announces "disabled")

---

### TC-A11Y-005: Per-row Delete confirmation modal traps focus and restores it

**Action**:
1. Visit `/tools`
2. Open a row's action menu and click Delete
3. Press `Escape` to dismiss the confirmation modal

**Observation 1 — Focus trap**:
1. While the modal is open, `Tab` cycles only between modal-internal elements

**Observation 2 — Focus restoration**:
1. After Escape, focus returns to the row action menu trigger

---

### TC-FULL-001: Mutate every step, save, reload, and verify

**Preconditions**:
- A throw-away `__e2e__` Custom tool is created at the start of the test (NOT mocked)

**Action**:
1. Authenticate and visit `/tools/edit/<the throw-away id>`
2. Change Description to a new `__e2e__` string
3. Change URL to a new `__e2e__` URL with a `{param}` placeholder
4. Change HTTP method to `PUT`
5. Toggle the Active checkbox off
6. Add two new parameter rows (different names, types, descriptions, required flags)
7. Cycle Authentication: select Bearer Token, type a value; select Basic Auth, fill username + password; select API Key
8. Fill API Key Header `X-Test-Api-Key` and API Key Value `sk-__e2e__-secret`
9. Click "Save"
10. Reload the page (revisit `/tools/edit/<id>`)
11. Visit `/tools`, locate the row, open the action menu, click Delete, and confirm

**Observation 1 — Save fires once**:
1. Exactly one `POST /tool/upsert_tool` request is recorded for step 9
2. The body's `id` equals the throw-away tool's id

**Observation 2 — Success toast on save**:
1. Toast title equals `Tool updated successfully`

**Observation 3 — Reload rehydrates every changed field**:
1. Description matches the typed value
2. URL matches the typed value
3. Method select reads `PUT`
4. Active checkbox is unchecked
5. Parameters card shows the two new rows with their saved values
6. Auth type select reads `API Key`
7. API Key Header input value equals `X-Test-Api-Key`
8. API Key Value input value equals `sk-__e2e__-secret` (decrypted on GET)

**Observation 4 — Cleanup deletes the tool**:
1. The DELETE call from step 11 records `DELETE /tool/delete_tool?tool_id=<id>`
2. Toast `Tool deleted successfully` appears
3. The row is no longer present on `/tools`

**Cleanup** (in `finally`):
1. If the cleanup DELETE failed, call the backend directly to remove the throw-away tool by id

---

## Edge Cases (each appears as a `TC-EDGE-*` test case above)

- [x] Network failure on save — see TC-EDGE-001
- [x] Concurrent edit conflict — see TC-EDGE-002
- [x] Special chars / unicode / XSS — see TC-EDGE-003
- [x] Very long description — see TC-EDGE-004
- [x] Newlines in single-line inputs — see TC-EDGE-005
- [x] Whitespace-only parameter name — see TC-EDGE-006
- [x] Long encrypted secret round-trip — see TC-EDGE-007

---

## Business Rules

- `auth_config` is encrypted on POST/PUT and decrypted on GET (`core/services/tool_service.py:95,176,208,304`), enabling secret round-trip on reload.
- Built-in tools have a Delete button on the edit page (kebab menu); custom tools do NOT. The list-page Delete icon is the canonical cleanup path for custom tools.
- 404 on hydration redirects to `/tools`; 500 does NOT redirect (user remains on the editor).
- Per-row delete on `/tools` uses the React Query mutation `useDeleteTool` so the on-success cache invalidation cleans up other read sites (e.g. agent editor's tool picker).

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Tab order Name → Description → Active → Method → URL → Add parameter → Authentication → Cancel → Save — see TC-A11Y-001
- [x] Enter on URL triggers Save — see TC-A11Y-002
- [x] Zod errors announced via `role="alert"` / `aria-live` — see TC-A11Y-003
- [x] Loading spinner announced via `aria-busy` / `Loading...` — see TC-A11Y-004
- [x] Delete confirmation modal traps focus and restores it — see TC-A11Y-005

---

## Scenario ID Mapping

| Old scenario ID | New TC ID         | Spec test name                                                  |
| --------------- | ----------------- | --------------------------------------------------------------- |
| TE-001          | TC-HAPPY-001      | loads the tool and hydrates the form                            |
| TE-002          | TC-ERROR-001      | 404 redirects to /tools                                         |
| TE-003          | (deferred)        | (`test.fixme` — depends on built-in fixture)                    |
| TE-004          | TC-HAPPY-002      | Save button reads Save on edit                                  |
| TE-005          | TC-HAPPY-003      | description edit persists                                       |
| TE-007          | TC-HAPPY-004      | adding a parameter persists                                     |
| TE-009          | TC-HAPPY-005      | toggling Active off persists                                    |
| TE-010          | TC-HAPPY-006      | switching api_key → bearer persists the new secret              |
| TE-012          | TC-HAPPY-007      | row delete removes the tool                                     |
| TE-013          | TC-NAV-001        | unauthenticated edit visit redirects to login                   |
| TE-014          | TC-NAV-002        | expired token on edit redirects to login                        |
| TE-015          | TC-NAV-003        | non-member is denied access to the tool editor                  |
| TE-016          | TC-ERROR-002      | update 400 surfaces validation toast and preserves form         |
| TE-017          | TC-ERROR-003      | update 401 surfaces error toast without redirect                |
| TE-018          | TC-ERROR-004      | update 403 surfaces forbidden toast                             |
| TE-019          | TC-ERROR-005      | update 404 redirects back to /tools                             |
| TE-020          | TC-ERROR-006      | update 409 surfaces duplicate name toast                        |
| TE-021          | TC-ERROR-007      | update 500 surfaces generic error toast                         |
| TE-022          | TC-ERROR-008      | hydration 500 surfaces error toast without redirect             |
| TE-023          | TC-ERROR-009      | hydration 403 redirects back to /tools                          |
| TE-024          | TC-EDGE-001       | network failure on save preserves the form                      |
| TE-025          | TC-LOADING-001    | slow save disables the save button and shows loading text       |
| TE-026          | TC-LOADING-002    | slow tool load shows loader until hydration completes           |
| TE-027          | TC-EDGE-002       | concurrent edit conflict is surfaced as a toast                 |
| TE-028          | TC-VALIDATE-001   | whitespace-only name update is rejected                         |
| TE-029          | TC-VALIDATE-002   | name description and url are trimmed on update                  |
| TE-030          | TC-EDGE-003       | special chars and unicode round-trip without xss                |
| TE-031          | TC-EDGE-004       | very long description update is bounded with feedback           |
| TE-032          | TC-EDGE-005       | pasting newlines into single-line inputs strips them            |
| TE-033          | TC-EDGE-006       | whitespace-only parameter name is stripped on update            |
| TE-034          | TC-EDGE-007       | long api key secret update round-trips encrypted                |
| TE-035          | TC-A11Y-001       | tab order through the edit form reaches every control           |
| TE-036          | TC-A11Y-002       | enter on URL input triggers save                                |
| TE-037          | TC-A11Y-003       | validation errors are announced via aria-live on edit           |
| TE-038          | TC-A11Y-004       | save spinner is announced to assistive tech                     |
| TE-039          | TC-A11Y-005       | delete confirmation modal traps focus and restores on close     |
| TE-FULL         | TC-FULL-001       | mutates every step, saves, reloads and verifies                 |
