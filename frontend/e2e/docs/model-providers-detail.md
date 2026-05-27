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
