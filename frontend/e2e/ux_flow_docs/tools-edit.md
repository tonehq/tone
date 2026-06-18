# Tools — Edit Flow (E2E scenarios)

> Companion to `frontend/e2e/dashboard/tools-edit.spec.ts`. Each scenario ID
> below maps to a Playwright `test(...)` name so a failing run can be triaged
> directly back to a scenario.

## User stories

- As a user, I can open `/tools/edit/{id}` and see the existing tool
  pre-filled across every section (definition, request, parameters, auth).
- I can change any field, save, and see the updated values rehydrate after
  a reload.
- My encrypted secrets (api key, bearer token, basic password) round-trip
  through the API and re-render on edit.
- I can delete a custom tool from the `/tools` list (the per-row Delete
  icon). Built-in tools also expose a Delete on their edit page via the
  kebab menu; custom tools do not.
- If the tool id is missing or unknown, the page redirects me back to
  `/tools` with a toast.

## Routes

| Route | Component |
|---|---|
| `/tools/edit/{id}` | `ToolFormPage` with `toolId` prop |

## Key files

- `src/components/tools/ToolFormPage.tsx` — hydration, save, delete, redirect.
- `src/components/tools/CustomToolForm.tsx` — every Custom-tool field.
- `src/components/tools/ParameterBuilder.tsx` — repeating parameter rows.
- `src/components/tools/ToolsListPage.tsx` — `/tools` list, per-row Delete icon.
- `src/services/toolService.ts` — `getTool`, `upsertTool` (with `id`), `deleteTool`.
- `src/atoms/ToolAtom.tsx` — `upsertToolAtom`, `deleteToolAtom`, `fetchToolsAtom`.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| GET | `/tool/get_tool?tool_id={id}` | Page mount |
| **POST** | `/tool/upsert_tool` (with `id`) | Save (the same endpoint is used for create) |
| DELETE | `/tool/delete_tool?tool_id={id}` | Row Delete on `/tools` list |

## Scenarios — Edit (TE-001 … TE-FULL)

### Hydration

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-001 | Visit `/tools/edit/{id}` | `GET /tool/get_tool` fires; form hydrates with name + url + everything else | `loads the tool and hydrates the form` |
| TE-002 | `GET /tool/get_tool` returns 404 | Toast (via `handleApiError`); `router.push('/tools')` | `404 redirects to /tools` |

### Header & meta

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-003 | Built-in edit shows Delete in the kebab menu (custom does NOT) | Custom tool: no Delete on edit page | (`test.fixme` — depends on built-in fixture) |
| TE-004 | Save button label on edit | Reads "Save" (not "Create") | `Save button reads Save on edit` |

### Mutate single fields

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-005 | Edit `description` and save | Toast + reload persists the new value | `description edit persists` |
| TE-007 | Add a parameter and save | Reload shows the new row | `adding a parameter persists` |
| TE-009 | Toggle `Active` and save | Reload reflects the toggle | `toggling Active off persists` |

### Auth round-trip

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-010 | Switch `auth_type` to `bearer` with a fresh token, save | Reload re-renders the bearer field with the same value (decrypted on GET) | `switching api_key → bearer persists the new secret` |

### Delete from list

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-012 | Per-row Delete icon → confirm | `DELETE /tool/delete_tool?tool_id=` fires; row is gone from `/tools` | `row delete removes the tool` |

### Comprehensive flow (every field, every section)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-FULL | Create a throw-away custom tool, change **every** writable control across the form (description, URL, method, active, all auth variants ending on `api_key`, two new parameters), save, reload, verify each persisted value, then delete | All filled values rehydrate after reload; tool is deleted in the same test for cleanup | `mutates every step, saves, reloads and verifies` |

TE-FULL exercises the following fields. Each row maps a section to the form field, the selector, the helper used, and whether persistence is re-asserted after reload.

| Section | Field | Selector | Helper | Asserted on reload |
|---|---|---|---|---|
| Tool definition | Description | `textarea[name="description"]` | inline `fill` | yes |
| Tool definition | Active toggle | `#tool-is-active` | inline click | yes |
| Request | HTTP method | `button[name="tool-method"]` | `setHttpMethod()` | — (catalog) |
| Request | URL | `input[name="url"]` | inline `fill` | yes |
| Parameters | Add row × 2 | `button[name^="param-name-"]` | `addParameter()` | row count is yes |
| Parameters | Param name / type / description / required | per-row | `addParameter()` | — |
| Authentication | Auth type cycled bearer → basic → api_key | `button[name="tool-auth-type"]` | `setAuthType()` | yes (via the api_key downstream fields) |
| Authentication | API Key header | `input[name="tool-auth-header"]` | inline `fill` | yes |
| Authentication | API Key value | `input[name="tool-auth-api-key"]` | inline `fill` | yes (decrypted on GET) |

Notes:

- TE-FULL uses a freshly created tool (not the shared `fixtureToolId`) so the assertions only read this test's writes.
- The fixture tool is restored to a clean state between mutation tests (TE-007 removes the param it added, TE-009 flips Active back, TE-010 switches auth back to `none`).
- The bearer / basic credentials filled during the cycle are intentionally discarded — only the final `api_key` save is asserted on reload.

## Coverage map (which scenarios `TE-FULL` transitively exercises)

| Scenario | Transitively covered by TE-FULL? | Notes |
|---|---|---|
| TE-001 Hydration | yes | implicit (form is re-opened after save) |
| TE-005 Description | yes | filled + re-asserted |
| TE-007 Parameter add | yes | two parameters added + asserted on reload |
| TE-009 Active toggle | yes | toggled off + re-asserted |
| TE-010 Auth round-trip | yes (api_key) | bearer/basic are cycled but not asserted |
| TE-012 Delete | yes | the FULL flow ends in a delete |

Scenarios still tracked only via `test.fixme` (TE-003 built-in delete, TE-006 unchanged save toast, TE-008 parameter remove persistence, TE-011 row delete cancel, TE-CAL-001, TE-SMS-001) are *not* exercised by TE-FULL — they need additional fixtures or behaviour we haven't asserted yet.

## Edge cases

- `auth_config` is encrypted on POST/PUT and decrypted on GET in
  `core/services/tool_service.py:95,176,208,304` — that's why TE-010 / TE-FULL
  can re-assert the api_key + bearer values after a reload.
- Built-in tools have a Delete button on the edit page (kebab menu); custom
  tools do not. The list-page Delete icon is the canonical cleanup path for
  custom tools.

## Out of scope (covered elsewhere)

- Create flow → `tools-create.md`.
- List, search, sort → `tools.spec.ts`.
- Built-in tool variants — deferred behind `test.fixme` until OAuth/Twilio
  test seeds exist in CI.

## Cleanup

`beforeAll` creates a shared `__e2e__` fixture tool. Each test that mutates
state either restores the original value or uses a fresh throw-away tool.
`afterAll` deletes the shared fixture via the `/tools` row Delete icon.

---

## Appended Scenarios (gap-fill, ID prefix continues `TE-`)

These rows extend the original TE coverage with auth, error-state, network, input-edge-case and accessibility scenarios. Real-backend conventions apply (`__e2e__` prefix, try/finally cleanup in the same test body); no `page.route` mocks unless explicitly stated.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-013 | Visit `/tools/edit/<id>` without `tone_access_token` | Middleware 307 → `/auth/login?redirect=%2Ftools%2Fedit%2F<id>` | `unauthenticated edit visit redirects to login` |
| TE-014 | Visit edit URL with an expired token | Middleware 307 → `/auth/login?redirect=…`; expired cookie cleared | `expired token on edit redirects to login` |
| TE-015 | Non-member tries to open a tool they don't own | Access-denied / `/tools` redirect; no `GET /tool/get_tool` fires | `non-member is denied access to the tool editor` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-016 | `POST /tool/upsert_tool` returns 400 (validation) | Toast with backend `detail`; form intact; Save re-enabled | `update 400 surfaces validation toast and preserves form` |
| TE-017 | `POST /tool/upsert_tool` returns 401 mid-save | Toast with backend `detail`; dirty fields retained; no auto-redirect | `update 401 surfaces error toast without redirect` |
| TE-018 | Member tries to save changes on an owner-only tool → 403 | Toast with backend `detail`; form intact | `update 403 surfaces forbidden toast` |
| TE-019 | Tool deleted by another user mid-edit → save returns 404 | Toast `Tool not found`; redirect to `/tools` | `update 404 redirects back to /tools` |
| TE-020 | `POST /tool/upsert_tool` returns 409 (duplicate name) | Toast with backend `detail`; user stays on form with values | `update 409 surfaces duplicate name toast` |
| TE-021 | `POST /tool/upsert_tool` returns 500 | Generic backend `detail` toast; form intact; Save re-enabled | `update 500 surfaces generic error toast` |
| TE-022 | `GET /tool/get_tool` returns 500 (not 404) | `handleApiError` toast; user remains on page (no redirect for 500) | `hydration 500 surfaces error toast without redirect` |
| TE-023 | Hydration 403 (lost access mid-session) | Toast with backend `detail`; redirect to `/tools` | `hydration 403 redirects back to /tools` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-024 | Offline / network failure on Save | Error toast (`Something went wrong. Please try again.`); dirty fields preserved; no partial commit | `network failure on save preserves the form` |
| TE-025 | Slow `POST /tool/upsert_tool` (>3s) | Save button shows `Loading...` + `disabled`; second click blocked | `slow save disables the save button and shows loading text` |
| TE-026 | Slow `GET /tool/get_tool` (>3s) | `<AppLoader>` visible until response; no flash of empty form | `slow tool load shows loader until hydration completes` |
| TE-027 | Concurrent edit — tool updated by another user mid-edit; save returns 409 / 412 | Toast with backend `detail`; user can refresh without losing dirty fields | `concurrent edit conflict is surfaced as a toast` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-028 | Replace `name` with whitespace-only string and save | Inline `Name is required` Zod error; no `POST /tool/upsert_tool` fires | `whitespace-only name update is rejected` |
| TE-029 | Add leading/trailing whitespace to `name`, `description`, `url`; save | Trimmed before persist; reload shows trimmed values | `name description and url are trimmed on update` |
| TE-030 | Insert special chars (`<script>alert(1)</script>`, emoji, unicode) into name, description, URL, param description | Accepted on save; round-trip on reload renders text verbatim; no XSS execution | `special chars and unicode round-trip without xss` |
| TE-031 | Replace description with >500-character text | Accepted or bounded with helpful message; no client crash | `very long description update is bounded with feedback` |
| TE-032 | Paste multiline content into single-line `name` / `url` input | Newlines stripped; saved values are single-line | `pasting newlines into single-line inputs strips them` |
| TE-033 | Add a parameter row with whitespace-only name | Row stripped on serialize (consistent with create); payload's `parameters.properties` does NOT contain an empty-string key | `whitespace-only parameter name is stripped on update` |
| TE-034 | Update an API Key value with very long secret (>1000 chars) | Persisted encrypted; decrypted on GET matches verbatim | `long api key secret update round-trips encrypted` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| TE-035 | Tab order through the edit form | Name → Description → Active → Method → URL → Add parameter → Authentication → Cancel → Save | `tab order through the edit form reaches every control` |
| TE-036 | Press Enter on the URL input | Triggers Save (primary action submit) | `enter on URL input triggers save` |
| TE-037 | Zod validation error has `role="alert"` / aria-live | Screen readers announce `Name is required` / `Please enter a valid URL` without manual focus | `validation errors are announced via aria-live on edit` |
| TE-038 | Loading spinner state announces busy | While saving, Save button has `aria-busy="true"` or equivalent | `save spinner is announced to assistive tech` |
| TE-039 | Per-row Delete confirmation modal on `/tools` traps focus and restores it | Focus enters modal; Escape closes; focus returns to row action menu trigger | `delete confirmation modal traps focus and restores on close` |

### Coverage map additions

| New scenario | Replaces / extends | Notes |
|---|---|---|
| TE-013..015 | (new) | Auth + role gating for the edit route |
| TE-016..023 | TE-002 (404 redirect) | Adds 400/401/403/409/500 save paths + 403/500 hydration paths |
| TE-024..027 | (new) | Network resilience for save + hydration + concurrent edit |
| TE-028..034 | TE-005, TE-007, TE-009 | Promotes basic field validation into edge-case sweep + encrypted secret round-trip |
| TE-035..039 | Accessibility checklist | Promotes a11y bullets into runnable scenarios |
