# Model Providers — list page (E2E scenarios)

> Companion to `frontend/e2e/dashboard/model-providers.spec.ts`. Each
> scenario ID maps to a Playwright `test(...)` name so a failing run can be
> triaged directly back to a scenario.

## User stories

- As an org member, I see every (provider, service_type) pair I have keys for as a card grid at `/model-providers`.
- As an admin/owner, I can add a new API key for a chosen provider+service_type from a single "Add Provider" drawer (with the option to reuse an existing key on a different service_type).
- As an admin/owner, I can edit the default key (label, description, active/default flags) directly from the card without leaving the list.
- As an admin/owner, I can bulk-delete every key for a (provider, service_type) pair via the card's trash icon.

## Routes

| Route | Component |
|---|---|
| `/model-providers` | `frontend/src/components/service-providers/ServiceProvidersPage.tsx` |

## Key files

- `ServiceProvidersPage.tsx` — toolbar + grid + delete modal.
- `service-grid.tsx` — infinite-scroll card grid.
- `api-key-create-drawer.tsx` — Add Provider drawer (also used on the detail page Keys tab).
- `api-key-edit-drawer.tsx` — pencil-icon edit drawer.
- `frontend/src/atoms/ServicesAtom.tsx` — `servicesAtom`, `fetchServicesAtom`, `upsertServiceAtom`, `deleteProviderAtom`.
- `frontend/src/services/servicesService.ts` — axios calls.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| POST | `/services/list` | grid load + every filter/search/sort change |
| GET | `/services/providers/catalog` | Add Provider drawer dropdown |
| POST | `/services` (201) | Add Provider drawer Submit |
| PATCH | `/services/{id}` | card pencil → edit drawer Save |
| DELETE | `/services/providers/{provider_id}?service_type=…` | card trash → bulk delete |

## Scenarios — list page (MPL-/MPC-/MPE-/MPD-/MPP-)

### Page identity + rendering

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPL-001 | Visit `/model-providers` | Header + total badge + Add Provider CTA | `renders the header + Add Provider CTA` |
| MPL-002 | Open the type filter | Dropdown lists All / LLM / STT / TTS | `type filter dropdown lists all/llm/stt/tts` |
| MPL-003 | Search input | Accepts text + debounces; clears cleanly | `search input is interactive` |
| MPL-004 | Click Add Provider | Drawer opens with service_type + provider + api_key controls | `Add Provider drawer opens with service_type + provider fields` |
| MPL-005 | Search gibberish | Empty-state copy appears | `empty state when search matches nothing` |

### Create — validation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-002 | Submit with no provider selected | Create button is disabled | `Create button is disabled with no provider selected` |
| MPC-003 | Submit with no api_key entered | Create button is disabled | `Create button is disabled with no api_key entered` |

### Create — happy path + duplicates

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-001 | Fill the drawer with a unique label + secret → Create | Success toast; provider id resolved from `/services/providers/catalog`; key is deleted in `try/finally` | `valid Create posts the form and the card grid updates` |
| MPC-005 | Re-submit the same label on the same provider | Error toast (409); drawer stays on the create page | `duplicate label per provider surfaces an error toast` |

### Delete

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPD-001 | Card trash icon | Confirm modal opens | `card trash opens confirmation modal` |

### Comprehensive flow

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPP-FULL | Create → search → assert card → delete → assert gone | Every step asserts a toast or row mutation; the key is deleted in `try/finally` | `create → assert card → delete → assert gone` |

MPP-FULL field-coverage:

| Section | Field | Selector | Helper | Asserted |
|---|---|---|---|---|
| Add Provider drawer | Service type | `button[id="service_type"]` | `pickFirstProviderFromCatalog({ serviceType })` | indirect (provider list filters) |
| Add Provider drawer | Provider | `button[id="provider_id"]` | `pickFirstProviderFromCatalog` | id resolved from `/services/providers/catalog` |
| Add Provider drawer | Label | `input[name="label"]` | inline fill | label appears in card grid |
| Add Provider drawer | Description | `textarea[name="description"]` | inline fill | — |
| Add Provider drawer | API key | `input[name="api_key"]` | inline fill | — (never re-displayed) |
| List | Search box | `input[placeholder="Search providers or services…"]` | inline fill | narrows the grid to the new card |
| Card | Delete icon | per-card `button[aria-label*="Delete"]` | `deleteApiKeyViaUI` | row count drops to 0 |

## Coverage map

| Scenario | Covered by MPP-FULL? |
|---|---|
| MPC-001 valid Create | yes |
| MPD-001 trash opens modal | partially (the FULL flow uses the bulk-delete-by-row path) |
| MPL-003 search interactive | yes |

## Deferred (`test.fixme`)

- `MPC-004` reuse-key path — needs a 2-service-type seed (a single provider with both LLM and STT keys). Re-enable once that seed exists.
- `MPE-001..MPE-003` list-page pencil edit — covered by the detail-page Edit scenarios (`AKE-` in `model-providers-detail.md`).
- `MPD-002` confirm-delete removes the card — covered by MPP-FULL.

## Cleanup

Every test that creates a key cancels it in `try/finally` via `deleteApiKeyViaUI`. Labels are `__e2e__key_*`-prefixed so any leftovers from aborted runs can be swept by API.
