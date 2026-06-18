# Tools — Create Flow (E2E scenarios)

> Companion to `frontend/e2e/dashboard/tools-create.spec.ts`. Each scenario ID
> below maps to a Playwright `test(...)` name so a failing run can be triaged
> directly back to a scenario.

## User stories

- As a user, I can create a new **custom** tool from `/tools/create/custom`
  with a name, description, HTTP method, URL, parameter schema, and
  authentication credentials.
- As a user, I can preview the type picker at `/tools/create` and pick
  between a custom tool and a built-in template.
- As a user, picking a template tile pre-fills the custom form via the
  `template_id` query parameter so I can tweak and save.
- As a user, my secrets (api key, bearer token, basic password) are
  persisted such that the form rehydrates them on edit.

## Routes

| Route | Component |
|---|---|
| `/tools/create` | `ToolCreatePage` (type picker) |
| `/tools/create/custom` | `ToolFormPage` (no `toolId`, no template) |
| `/tools/create/custom?template_id={id}` | `ToolFormPage` pre-filled from `GET /tool/get_tool` |

## Key files

- `src/components/tools/ToolCreatePage.tsx` — type picker.
- `src/components/tools/ToolFormPage.tsx` — owns the form state, save, redirect.
- `src/components/tools/CustomToolForm.tsx` — every Custom-tool field.
- `src/components/tools/ParameterBuilder.tsx` — repeating parameter rows.
- `src/atoms/ToolAtom.tsx` — `upsertToolAtom`, `fetchToolsAtom`.
- `src/services/toolService.ts` — axios calls (`/tool/upsert_tool`, `/tool/get_tool`, …).
- `src/schemas/tool.ts` — Zod schemas for the custom form.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| GET | `/tool/get_template_tools` | Picker — list of built-in templates |
| GET | `/tool/get_tool?tool_id={template_id}` | Picker — pre-fill from template |
| **POST** | `/tool/upsert_tool` | Create or save (no body `id` → create) |
| DELETE | `/tool/delete_tool?tool_id={id}` | Per-row Delete on the `/tools` list |

## Scenarios — Custom (TC-001 … TC-FULL)

### Type picker

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-001 | Visit `/tools/create` | Renders the Custom Tool tile + the built-in templates section | `picker renders the Custom tile and built-in templates` |
| TC-002 | Click "Custom Tool" | Navigates to `/tools/create/custom` and the form renders | `clicking Custom Tool navigates to /tools/create/custom` |
| TC-003 | Click a template tile | Navigates to `/tools/create/custom?template_id={id}` and pre-fills the form | (`test.fixme` — depends on the seed catalog) |

### Form identity

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-004 | Header in create mode | Shows Cancel + Create buttons (no Delete) | `header shows Cancel + Create (no Delete in create mode)` |

### Validation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-005 | Blank name + Create | Inline "Required" error | `blank name + Create surfaces an inline error` |
| TC-006 | Blank description + Create | Inline "Required" error | `blank description + Create surfaces an inline error` |
| TC-007 | Invalid URL + Create | Inline URL validation error | `invalid URL + Create surfaces an inline error` |

### Form controls

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-008 | Open method dropdown | Lists GET, POST, PUT, DELETE, PATCH | `HTTP method dropdown exposes all five verbs` |
| TC-009 | Toggle Active checkbox | State flips | `Active checkbox toggles` |
| TC-010 | Click "Add parameter" | Row appears with name/type/description controls | `adding a parameter renders its row controls` |
| TC-011 | Click row's Trash icon | Row is removed | `removing a parameter clears its row` |
| TC-012 | Auth type = API Key | Header + Value fields render | `selecting API Key reveals header + value` |
| TC-013 | Auth type = Bearer | Only the Token field renders | `selecting Bearer reveals only the token field` |
| TC-014 | Auth type = Basic | Username + Password fields render | `selecting Basic reveals username + password` |
| TC-015 | Switch back to "No Authentication" | Conditional sections disappear | `switching back to No Authentication hides conditional fields` |

### Save + redirect

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-016 | Fill required + Create | `POST /tool/upsert_tool`; success toast; redirect to `/tools` | `minimum-required create posts the form and redirects to /tools` |
| TC-017 | Save a second tool with the same name | Form stays on `/tools/create/custom`; an error toast appears | `duplicate-name create surfaces an error toast` |

### Comprehensive flow (every field, every section)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-FULL | Fill **every** writable Custom-tool control + 2 parameters + cycle through every `auth_type` (then settle on `api_key`), save, reload, and verify each persisted value | All filled values rehydrate after reload; tool is deleted in the same test for cleanup | `fills every field + 2 parameters, saves, reloads, and verifies persistence` |

TC-FULL exercises the following fields end-to-end. Each row maps a section to the form field, the selector in `frontend/src/components/tools/CustomToolForm.tsx` / `ParameterBuilder.tsx`, the helper used in `frontend/e2e/helpers/toolFixtures.ts`, and whether persistence is asserted after reload.

| Section | Field | Selector | Helper | Asserted on reload |
|---|---|---|---|---|
| Tool definition | Function name | `input[name="name"]` | inline `fill` | yes |
| Tool definition | Description | `textarea[name="description"]` | inline `fill` | yes |
| Tool definition | Active toggle | `#tool-is-active` | inline click | yes |
| Request | HTTP method | `button[name="tool-method"]` | `setHttpMethod()` | — (catalog) |
| Request | URL | `input[name="url"]` | inline `fill` | yes |
| Parameters | Add row × 2 | `button[name^="param-name-"]` | `addParameter()` | row count is yes |
| Parameters | Param name | `input[name="param-name-{rowId}"]` | `addParameter({ name })` | — |
| Parameters | Param type | `button[name="param-type-{rowId}"]` | `addParameter({ type })` | — |
| Parameters | Param description | `input[name="param-desc-{rowId}"]` | `addParameter({ description })` | — |
| Parameters | Param required | `#param-req-{rowId}` | `addParameter({ required })` | — |
| Authentication | Auth type | `button[name="tool-auth-type"]` | `setAuthType()` | yes (via downstream fields) |
| Authentication | API Key header | `input[name="tool-auth-header"]` | inline `fill` | yes |
| Authentication | API Key value | `input[name="tool-auth-api-key"]` | inline `fill` | yes (decrypted on GET) |
| Authentication | Bearer token | `input[name="tool-auth-bearer"]` | inline `fill` | covered by TE-010 |
| Authentication | Basic username | `input[name="tool-auth-username"]` | inline `fill` | — |
| Authentication | Basic password | `input[name="tool-auth-password"]` | inline `fill` | — |

Notes:

- The HTTP method, parameter type, and auth type are catalog-driven shadcn dropdowns; the spec verifies they save without error rather than re-asserting the exact label (which can shift between Radix selection state and label text).
- `auth_config` is encrypted on POST/PUT and decrypted on GET (`core/services/tool_service.py:95,176,208,304`), so the API Key header + value DO round-trip and the spec asserts them after reload.
- Helpers are **best-effort**: if a select option isn't visible (e.g. catalog miss), `pickSelectOptionByLabel()` returns `false` and the test fails clearly rather than continuing with a stale value.

## Coverage map (which scenarios `TC-FULL` transitively exercises)

| Scenario | Transitively covered by TC-FULL? | Notes |
|---|---|---|
| TC-004 Header buttons | yes | implicit (Create button is clicked) |
| TC-008 Method dropdown | yes | PUT is picked |
| TC-009 Active toggle | yes | toggled and re-asserted |
| TC-010 Add parameter | yes | called twice |
| TC-012 API Key reveals header + value | yes | filled + reloaded |
| TC-013 Bearer reveals token | yes | cycled through |
| TC-014 Basic reveals username + password | yes | cycled through |
| TC-015 Auth type switch hides fields | yes | cycled between bearer → basic → api_key |
| TC-016 Save + redirect | yes | the FULL flow ends in a real save |

Scenarios still tracked only via `test.fixme` (TC-003 template pre-fill, TC-CAL-001 Google Calendar, TC-SMS-001 SMS) are *not* exercised by TC-FULL — they need additional org seed data (built-in templates, OAuth connections, Twilio credentials).

## Edge cases

- Empty `/tool/get_template_tools` → the picker still renders the Custom tile (covered by TC-001 + TC-002).
- 409 unique-name conflict → covered by TC-017.
- Server 500 on save → not currently asserted (toast surfaces via `handleApiError`).

## Out of scope (covered elsewhere)

- Edit flow (TE-###) → `tools-edit.md`.
- List page, search, sort, pagination → `tools.spec.ts`.
- Built-in tool variants (Google Calendar, SMS, Sheets) → deferred behind `test.fixme` placeholders.

## Cleanup

Real-backend writes are namespaced with `__e2e__` in tool names. Each test that saves a tool also deletes it (via the per-row Delete icon on the `/tools` list, which calls `DELETE /tool/delete_tool`). Custom tools have no Delete button on the edit page — only built-in tools expose one via the kebab menu — so the list-page delete is the canonical cleanup path.

---

## Appended Scenarios (gap-fill, ID prefix continues `TC-`)

These rows extend the original TC coverage with auth, error-state, network, input-edge-case and accessibility scenarios. Real-backend conventions apply (`__e2e__` prefix, try/finally cleanup in the same test body); no `page.route` mocks unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-018 | Visit `/tools/create` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Ftools%2Fcreate` | `unauthenticated picker visit redirects to login` |
| TC-019 | Visit `/tools/create/custom` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Ftools%2Fcreate%2Fcustom` | `unauthenticated custom visit redirects to login` |
| TC-020 | Visit picker with an expired token | Middleware 307 → `/auth/login?redirect=…`; expired cookie cleared | `expired token on picker redirects to login` |
| TC-021 | Non-member tries to create a tool | Access-denied / `/home` redirect; no `GET /tool/get_template_tools` fires | `non-member is denied access to tools create` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-022 | `POST /tool/upsert_tool` returns 401 mid-create | Toast with backend `detail`; form intact; no auto-redirect | `create 401 surfaces error toast` |
| TC-023 | `POST /tool/upsert_tool` returns 403 (member tries owner-only org action) | Toast with backend `detail`; form intact | `create 403 surfaces forbidden toast` |
| TC-024 | `POST /tool/upsert_tool` returns 422 (validation array) | Falls back to `Something went wrong. Please try again.`; form intact | `create 422 falls back to generic error toast` |
| TC-025 | `POST /tool/upsert_tool` returns 500 | Generic backend `detail` toast; Create button re-enables | `create 500 surfaces generic error toast` |
| TC-026 | `GET /tool/get_template_tools` returns 500 | Picker renders only the Custom tile; no templates section; no toast | `template-list 500 falls back to custom-only picker` |
| TC-027 | Template pre-fill — `GET /tool/get_tool?tool_id=<id>` returns 500 (not 404) | Loader clears; form falls back to empty Custom state; no toast | `template pre-fill 500 falls back silently` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-028 | Offline / network failure on Create | Error toast (`Something went wrong. Please try again.`); every form field retains its value | `network failure on save preserves the form` |
| TC-029 | Slow `POST /tool/upsert_tool` (>3s) | Create button renders `Loading...` and `disabled`; second click blocked | `slow save disables the create button and shows loading text` |
| TC-030 | Slow `GET /tool/get_template_tools` (>3s) | Picker shows a skeleton/loader for the templates section without blocking the Custom tile | `slow template list keeps the custom tile usable` |
| TC-031 | Network drop while typing parameters | Local form state preserved; subsequent save retries with all params intact | `parameter rows survive a transient network drop` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-032 | Whitespace-only name | Inline "Required" / Zod error; no `POST /tool/upsert_tool` fires | `whitespace-only name fails validation` |
| TC-033 | Leading/trailing whitespace in `name` and `description` | Trimmed before persist; reload shows trimmed values | `name and description are trimmed on save` |
| TC-034 | Special chars (`<script>alert(1)</script>`, emoji, unicode) in name + description + URL params | Accepted; round-trip on reload renders text verbatim; no XSS execution | `special chars and unicode round-trip without xss` |
| TC-035 | Very long URL (>500 chars) | Either accepted by Zod `url()` or rejected with helpful message; no client crash | `very long URL is bounded with feedback` |
| TC-036 | Paste multiline content into single-line URL input | Newlines stripped; saved URL is single-line | `pasting newlines into URL strips them` |
| TC-037 | Parameter row name with surrounding whitespace | Trimmed before serialization to JSON-Schema | `parameter name whitespace is trimmed before serialize` |
| TC-038 | Special characters in parameter description | Accepted; round-trip after save | `parameter description accepts special characters` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TC-039 | Tab order through the create form | Name → Description → Method → URL → Add parameter → Authentication → Cancel → Create | `tab order through the form reaches every control` |
| TC-040 | Press Enter on the Name input | Triggers Create (primary action submit) | `enter on name input triggers create` |
| TC-041 | Validation error has `role="alert"` / aria-live | Screen readers announce the Zod error without manual focus | `validation error is announced via aria-live` |
| TC-042 | Parameter row trash icon is always reachable to screen readers | Has `aria-label="Remove parameter"` even though opacity is 0 visually | `trash icon is reachable to assistive tech regardless of hover` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| TC-018..021 | (new) | Auth gating for picker + custom routes + role gating |
| TC-022..027 | TC-017 (duplicate name 409) | Adds 401/403/422/500 + template-list and template-pre-fill error paths |
| TC-028..031 | (new) | Network resilience for save + template list + typing |
| TC-032..038 | TC-005, TC-006, TC-007 | Promotes basic validation into edge-case sweep |
| TC-039..042 | Accessibility checklist | Promotes a11y bullets into runnable scenarios |
