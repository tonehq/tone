# Model Providers — detail page (E2E scenarios)

> Companion to `frontend/e2e/dashboard/model-providers-detail.spec.ts`. Two
> tabs are covered here: **API Keys** (AKL-/AKC-/AKE-/AKD-/AKK-) and
> **Models** (MDL-/MDC-/MDE-/MDD-/MDM-).

## User stories

- As an admin/owner, I open `/model-providers/{providerId}/{serviceType}` and see two tabs: API Keys (count) + Models (count).
- I can add, edit, and delete API keys for the chosen (provider, service_type) pair from the Keys tab.
- I can add, edit, and delete provider-models from the Models tab.
- The secret value of an API key is **never** shown after the initial create — the list always shows a masked placeholder.

## Routes

| Route | Component |
|---|---|
| `/model-providers/{providerId}/{serviceType}` | `frontend/src/components/service-providers/ServiceProviderDetailPage.tsx` |

## Key files

- `ServiceProviderDetailPage.tsx` — tab strip, keys table, models table, delete modals.
- `api-key-create-drawer.tsx`, `api-key-edit-drawer.tsx` — Keys CRUD drawers (provider + service_type are locked on the detail page).
- `model-form-drawer.tsx` — Models CRUD drawer (kind dropdown locked to llm/stt/tts).
- `frontend/src/atoms/ServicesAtom.tsx` — `providerKeysAtom`, `providerModelsAtom`, write atoms.
- `frontend/src/services/servicesService.ts` — axios calls.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| POST | `/services/providers/{provider_id}/keys` | Keys-tab list load |
| POST | `/services` (201) | Add API key drawer Submit |
| PATCH | `/services/{id}` | row click → edit drawer Save |
| DELETE | `/services/{id}` | row trash icon → confirm |
| POST | `/services/providers/{provider_id}/models` | Models-tab list load |
| POST | `/services/providers/{provider_id}/models/create` (201, admin/owner) | Add model drawer Save |
| PATCH | `/services/providers/{provider_id}/models/{model_id}` (admin/owner) | row click → edit drawer Save |
| DELETE | `/services/providers/{provider_id}/models/{model_id}` (admin/owner) | row trash icon → confirm |

## Scenarios — API Keys tab (AKL-/AKC-/AKE-/AKD-/AKK-)

### Page identity + rendering

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKL-001 | Detail page loads with Keys tab active | `aria-pressed="true"` on the Keys tab button | `page loads with Keys tab active` |
| AKL-002 | Keys table columns | Name / Type / Status headers visible | `keys table renders the documented columns` |
| AKL-003 | Fixture key appears | Row matches the shared `__e2e__` fixture label | `fixture key appears in the list` |
| AKL-004 | Search by label | Typing gibberish empties the table | `search filters rows by label` |
| AKL-005 | Click Add API key | Drawer opens | `Add API key button opens drawer` |

### Create

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKC-001 | Valid Create | Success toast + new row | `valid Create → row + success toast` |
| AKC-002 | Blank api_key | Create button is disabled | `Create button is disabled with no api_key entered` |
| AKC-003 | Duplicate label | Error toast; drawer stays open | `duplicate label surfaces an error toast` |

### Edit

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKE-001 | Click row | Edit drawer opens | `clicking a row opens the edit drawer` |
| AKE-002 | Edit description | Persists on reload | `editing description persists on reload` |

### Delete

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKD-001 | Row trash icon | Confirm modal opens | `row trash icon opens the confirm modal` |

### Comprehensive flow

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKK-FULL | Create → list → edit description → reload + verify → delete | All in one test with `try/finally` cleanup | `create → list (masked) → edit description → delete` |

## Scenarios — Models tab (MDL-/MDC-/MDE-/MDD-/MDM-)

### Page identity + rendering

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDL-001 | Models tab activates | `aria-pressed="true"` on the Models tab button | `Models tab activates and the table renders` |
| MDL-002 | Models table columns | Name / Kind / Status headers visible | `models table renders the documented columns` |
| MDL-003 | Click Add model | Drawer opens | `Add Model button opens the drawer` |

### Create

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDC-001 | Minimal (name + kind) | Row appears + success toast | `create minimal model (name + kind) succeeds` |
| MDC-002 | All fields (name + display_name + kind + description) | display_name shown preferentially in row | `create with all fields persists` |
| MDC-003 | Blank name | Save is disabled | `Save button is disabled with blank name` |
| MDC-004 | Duplicate name within provider | Error toast (409); drawer stays open | `duplicate name within provider surfaces an error toast` |

### Edit

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDE-002 | Edit display_name | Persists on reload | `editing display_name persists on reload` |

### Delete

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDD-001 | Row trash icon | Confirm modal opens | `trash icon opens confirm modal` |

### Comprehensive flow

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDM-FULL | Create → search → edit display → delete; reload + verify each step | All in one test with `try/finally` cleanup | `create → search → edit display → delete` |

MDM-FULL field-coverage:

| Section | Field | Selector | Helper | Asserted on reload |
|---|---|---|---|---|
| Add model drawer | Name | `input[name="name"]` (in dialog) | `createProviderModelViaUI({ name })` | row appears |
| Add model drawer | Display name | `input[name="display_name"]` (in dialog) | inline fill | shown preferentially in row |
| Add model drawer | Kind | `button[id="kind"]` (in dialog) | `pickSelectOptionByLabel('LLM')` | — (kind badge color asserted indirectly) |
| Add model drawer | Description | `textarea[name="description"]` (in dialog) | inline fill | — |
| Edit model drawer | display_name | `input[name="display_name"]` | inline fill | yes |
| Models tab | Row trash | per-row `button[aria-label="Delete model"]` | `deleteProviderModelViaUI` | row count drops to 0 |

## Coverage map

| Scenario | Covered by AKK-FULL? |
|---|---|
| AKC-001 valid Create | yes |
| AKE-002 description round-trip | yes |
| AKD-001 trash icon → modal | partially (FULL goes straight to delete) |

| Scenario | Covered by MDM-FULL? |
|---|---|
| MDC-001 minimal create | yes |
| MDE-002 display_name round-trip | yes |
| MDD-001 trash modal | partially (FULL goes straight to delete) |

## Deferred (`test.fixme` / `test.skip`)

- `AKR-MASK` (assert one-time reveal of the plaintext secret via `page.waitForResponse` interception) — deferred to a follow-up. The FE never re-renders the secret, so a regression is unlikely without explicit UI changes. Backend masking is already covered by pytest under `test-cases/`.
- `AKE-003` toggle Active off on a key → persists on reload — relies on the edit drawer reliably exposing the Active checkbox; revisit after the drawer's accessibility surface is firmed up.
- `MDE-003` toggle Active off on a model — same reason.
- `MDC-005` admin/owner-only model CRUD (a non-owner sees no Add button) — skipped. Needs a non-owner membership seed which CI doesn't provide today (same gap as Members `MR-002`).
- `AKE-ROT` rotate-secret flow — there is no UI for rotation; to rotate, the user must delete and recreate. Document only.

## Safety notes

- **No `is_default=true` writes** — the user's agent saves pull the default key, so flipping it would break unrelated workflows.
- **Models are global** (`core/services/model_provider_service.py:121–124` — no `org_id` column on `ProviderModel`). Every model the test creates is visible to every org. The spec `__e2e__`-prefixes every model name AND deletes in `try/finally`.

## Cleanup

`beforeAll` creates a fixture API key via `createApiKeyViaUI` on the first LLM provider in the catalog. `afterAll` deletes it. Every Keys / Models test either:
- mutates the shared fixture and reverts (e.g. AKE-002 leaves the edited description in place because the description doesn't break later tests), OR
- uses a freshly-created throw-away in `try/finally` so it self-cleans.

---

## Gap-filling scenarios

> Rows below extend the tables above. New IDs continue after the highest
> existing per family. `AKK-FULL` and `MDM-FULL` are preserved; `AKK-EXT` and
> `MDM-EXT` add additional lifecycle coverage.

### Auth & access control — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKL-010 | Visit detail page without auth | Redirects to `/auth/login?redirect=%2Fmodel-providers%2F{id}%2F{type}` | `unauthenticated visit redirects to login` |
| AKL-011 | Visit with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| AKL-012 | Member (non-admin/owner) opens Keys tab | Rows visible read-only; `Add API key` CTA hidden / disabled | `member role cannot add API key` |
| AKC-010 | Member submits create directly | 403; toast `Forbidden` | `direct create as member surfaces 403 toast` |
| AKE-010 | Member clicks a row | Edit drawer opens read-only or save disabled | `member role cannot edit API key` |
| AKD-010 | Member clicks row trash | Trash hidden / disabled | `member cannot delete API key` |

### Backend error states — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKC-011 | `POST /services` returns 400 | Toast; drawer stays open with form intact | `400 on create keeps drawer open` |
| AKC-012 | `POST /services` returns 401 | Toast `Could not validate credentials`; next nav redirects to login | `401 on create triggers login redirect on next nav` |
| AKC-013 | `POST /services` returns 403 | Toast `Forbidden`; drawer stays open | `403 on create shows toast` |
| AKC-014 | `POST /services` returns 500 | Generic error toast; drawer intact | `500 on create shows toast` |
| AKE-011 | `PATCH /services/{id}` returns 400 | Toast; drawer stays open with edits | `400 on edit keeps drawer open` |
| AKE-012 | `PATCH /services/{id}` returns 404 (already deleted) | Drawer closes; list refetches | `404 on edit closes drawer and refetches` |
| AKE-013 | `PATCH /services/{id}` returns 409 (duplicate label) | Toast with conflict detail; drawer open | `409 on edit shows conflict toast` |
| AKE-014 | `PATCH /services/{id}` returns 500 | Toast; drawer stays open with edits intact | `500 on edit preserves edits` |
| AKD-011 | `DELETE /services/{id}` returns 403 | Toast; row remains | `403 on delete shows toast` |
| AKD-012 | `DELETE /services/{id}` returns 404 | Row disappears after refetch | `404 on delete refetches list` |
| AKD-013 | `DELETE /services/{id}` returns 500 | Toast; row remains; modal stays open | `500 on delete preserves row` |
| AKL-013 | `POST /services/providers/{id}/keys` returns 500 | Error toast; empty table with retry affordance | `keys list 500 surfaces toast` |

### Network resilience — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKC-020 | Network failure on Create | Toast; drawer stays open with form intact | `network failure on create preserves form` |
| AKC-021 | Slow `POST /services` (>3s) | Create button shows loading + `disabled` | `slow create disables button` |
| AKE-020 | Network failure on Edit | Toast; drawer stays open with edits intact | `network failure on edit preserves edits` |
| AKD-020 | Network failure on Delete | Toast; row remains | `network failure on delete preserves row` |
| AKE-021 | Concurrent edit (another admin renames same key) | Last-write-wins; list refetches | `concurrent edit last-write-wins` |

### Input edge cases — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKC-030 | Label whitespace only | Create disabled | `whitespace-only label disables Create` |
| AKC-031 | Label leading/trailing whitespace | Trimmed before submit | `label whitespace trimmed before submit` |
| AKC-032 | Label with emoji + unicode | Accepted; row renders unicode | `unicode + emoji label round-trips` |
| AKC-033 | Label `<script>alert(1)</script>` | Stored verbatim; rendered as text | `script tag in label is escaped on render` |
| AKC-034 | Label >500 chars | Inline error or backend 400 | `oversized label handled gracefully` |
| AKC-035 | API key whitespace only | Create disabled | `whitespace-only api_key disables Create` |
| AKC-036 | API key with leading/trailing whitespace | Trimmed before submit | `api_key whitespace trimmed before submit` |
| AKC-037 | API key shorter than provider minimum | Backend 400 + toast | `short api_key rejected by backend` |
| AKC-038 | API key 5000 chars | Either accepted or 400; no crash | `oversized api_key handled gracefully` |
| AKL-014 | Secret value never shown after Create | Row always renders masked placeholder; secret not in DOM after navigation | `secret value is masked after create and not in DOM after reload` |

### Accessibility & keyboard — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKC-040 | Tab through Create drawer | Order: Label → Description → API key → Active → Default → Create | `Create drawer tab order matches visual order` |
| AKC-041 | Submit drawer via Enter | Triggers Create if valid | `Enter key submits Create drawer` |
| AKC-042 | Drawer traps focus + restores on close | Tab wraps; Escape closes; focus restored | `drawer traps focus and restores on close` |
| AKC-043 | API key field uses `type="password"` and toggleable visibility | Toggling reveals; default hides | `api_key field uses password input` |
| AKE-030 | Inline error messages have `role="alert"` | Screen reader announces | `inline errors are announced` |
| AKD-030 | Delete confirm modal keyboard-operable | Tab to Confirm; Enter confirms | `Delete confirm modal is keyboard-operable` |

### List-specific scenarios — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKL-015 | Empty Keys list for provider | Empty state with `Add API key` CTA | `empty keys list shows add CTA` |
| AKL-016 | Search no-match | `No matches` empty state | `no-match search shows empty state` |
| AKL-017 | Sort by Name | Rows reorder asc/desc | `sort by name reorders rows` |
| AKL-018 | Sort by Status | Active rows grouped per direction | `sort by status reorders rows` |

### Cross-feature navigation — API Keys tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKN-010 | Click Models tab | `aria-pressed="true"` flips to Models; URL `?tab=models` | `tab switch updates aria-pressed and URL` |
| AKN-011 | Click back chevron / breadcrumb | Returns to `/model-providers` list | `back navigation returns to list` |
| AKN-012 | Browser Back after editing | Returns to previous route; no unsaved-changes prompt | `back after edit does not prompt for unsaved changes` |

### Full lifecycle test (additional) — API Keys

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| AKK-EXT | Create key (default off, active on) → search → edit label + description → reload + verify → delete | All toasts + row mutations asserted; `try/finally` deletes key on failure | `lifecycle: create → search → edit → reload → delete (extended)` |

---

### Auth & access control — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDL-010 | Member opens Models tab | Rows read-only; `Add model` CTA hidden / disabled | `member role cannot add model` |
| MDC-010 | Member submits Create model directly | 403; toast `Forbidden` | `direct create as member surfaces 403 toast` |
| MDE-010 | Member clicks model row | Edit drawer opens read-only | `member role cannot edit model` |
| MDD-010 | Member clicks model trash | Trash hidden / disabled | `member cannot delete model` |

### Backend error states — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDC-011 | `POST /services/providers/{id}/models/create` returns 400 | Toast; drawer stays open with form intact | `400 on create keeps drawer open` |
| MDC-012 | Create returns 401 | Toast; next nav hits login redirect | `401 on create triggers login redirect` |
| MDC-013 | Create returns 403 | Toast `Forbidden`; drawer open | `403 on create shows toast` |
| MDC-014 | Create returns 500 | Generic error toast; drawer intact | `500 on create shows toast` |
| MDE-011 | `PATCH /services/providers/{id}/models/{model_id}` returns 400 | Toast; drawer stays open with edits | `400 on edit keeps drawer open` |
| MDE-012 | Edit returns 404 | Drawer closes; list refetches | `404 on edit closes drawer and refetches` |
| MDE-013 | Edit returns 409 (duplicate name) | Toast with conflict detail; drawer open | `409 on edit shows conflict toast` |
| MDE-014 | Edit returns 500 | Toast; drawer stays open with edits intact | `500 on edit preserves edits` |
| MDD-011 | Delete returns 403 | Toast; row remains | `403 on delete shows toast` |
| MDD-012 | Delete returns 404 | Row disappears after refetch | `404 on delete refetches list` |
| MDD-013 | Delete returns 500 | Toast; row remains; modal open | `500 on delete preserves row` |
| MDL-013 | `POST /services/providers/{id}/models` returns 500 | Error toast; empty table with retry affordance | `models list 500 surfaces toast` |

### Network resilience — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDC-020 | Network failure on Create | Toast; drawer stays open | `network failure on create preserves form` |
| MDC-021 | Slow Create (>3s) | Save button shows loading + `disabled` | `slow create disables button` |
| MDE-020 | Network failure on Edit | Toast; drawer stays open with edits | `network failure on edit preserves edits` |
| MDD-020 | Network failure on Delete | Toast; row remains | `network failure on delete preserves row` |
| MDE-021 | Concurrent edit on same model | Last-write-wins; list refetches | `concurrent edit last-write-wins` |

### Input edge cases — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDC-030 | Name whitespace only | Save disabled | `whitespace-only name disables Save` |
| MDC-031 | Name leading/trailing whitespace | Trimmed before submit | `name whitespace trimmed before submit` |
| MDC-032 | Name with emoji + unicode | Accepted; row renders unicode | `unicode + emoji name round-trips` |
| MDC-033 | Name `<script>alert(1)</script>` | Stored verbatim; rendered as text | `script tag in name is escaped on render` |
| MDC-034 | Name >500 chars | Inline error or backend 400 | `oversized name handled gracefully` |
| MDC-035 | display_name >500 chars | Inline error or backend 400 | `oversized display_name handled gracefully` |
| MDC-036 | Description >2000 chars | Either accepted or truncated | `oversized description handled gracefully` |

### Accessibility & keyboard — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDC-040 | Tab through Add model drawer | Order: Name → display_name → Kind → Description → Save | `Add model drawer tab order matches visual order` |
| MDC-041 | Submit via Enter | Triggers Save if valid | `Enter key submits Add model drawer` |
| MDC-042 | Drawer traps focus + restores | Tab wraps; Escape closes; focus restored | `drawer traps focus and restores on close` |
| MDE-030 | Inline error messages have `role="alert"` | Screen reader announces | `inline errors are announced` |
| MDD-030 | Delete confirm modal keyboard-operable | Tab to Confirm; Enter confirms | `Delete confirm modal is keyboard-operable` |

### List-specific scenarios — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDL-014 | Empty Models list | Empty state with `Add model` CTA | `empty models list shows add CTA` |
| MDL-015 | Search no-match | Empty state | `no-match search shows empty state` |
| MDL-016 | Sort by Name | Rows reorder asc/desc | `sort by name reorders rows` |
| MDL-017 | Filter by Kind = LLM | Only LLM rows visible | `kind filter narrows to LLM` |

### Cross-feature navigation — Models tab

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDN-010 | Switch to API Keys tab | URL updates; counts persist; rows refetch | `tab switch updates aria-pressed and URL` |
| MDN-011 | Browser Back after creating a model | Returns to previous route; no unsaved-changes prompt | `back after create does not prompt for unsaved changes` |

### Full lifecycle test (additional) — Models

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MDM-EXT | Create model with all fields → search → edit display_name + description → reload + verify → delete | All toasts + row mutations asserted; `try/finally` deletes model on failure | `lifecycle: create (all fields) → search → edit → reload → delete (extended)` |
