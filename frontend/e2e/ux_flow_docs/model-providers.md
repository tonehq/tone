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

---

## Gap-filling scenarios

> Rows below extend the tables above. New IDs continue after the highest
> existing per family (MPL-005 → MPL-010+, MPC-005 → MPC-010+, MPE-003 →
> MPE-010+, MPD-001 → MPD-010+). MPP-FULL is preserved.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPL-010 | Visit `/model-providers` without auth | Redirects to `/auth/login?redirect=%2Fmodel-providers` | `unauthenticated visit redirects to login` |
| MPL-011 | Visit with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| MPL-012 | Member (non-admin/owner) opens page | Cards visible read-only; `Add Provider` CTA hidden / disabled | `member role cannot see Add Provider CTA` |
| MPC-010 | Member calls `POST /services` directly | Backend returns 403; toast `Forbidden` | `direct create as member surfaces 403 toast` |
| MPD-010 | Member clicks card trash | Trash hidden / disabled per role | `member cannot delete provider keys` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-011 | `POST /services` returns 400 invalid api_key shape | Toast with backend `detail`; drawer stays open | `400 invalid api_key keeps drawer open` |
| MPC-012 | `POST /services` returns 401 mid-flow | Toast `Could not validate credentials`; next nav hits login redirect | `401 on create triggers login redirect on next nav` |
| MPC-013 | `POST /services` returns 403 | Access denied toast; drawer stays open | `403 on create shows toast` |
| MPC-014 | `POST /services` returns 500 | Generic error toast; drawer intact | `500 on create shows toast and preserves form` |
| MPE-010 | `PATCH /services/{id}` returns 400 | Toast; drawer stays open with edits | `400 on edit keeps drawer open` |
| MPE-011 | `PATCH /services/{id}` returns 403 | Toast `Forbidden`; drawer stays open | `403 on edit shows toast` |
| MPE-012 | `PATCH /services/{id}` returns 404 (deleted by another session) | Drawer closes; list refetches; toast `Provider not found` | `404 on edit closes drawer and refetches` |
| MPE-013 | `PATCH /services/{id}` returns 500 | Toast; drawer stays open with edits intact | `500 on edit preserves edits` |
| MPD-011 | `DELETE /services/providers/{id}` returns 403 | Toast; card remains | `403 on delete shows toast and preserves card` |
| MPD-012 | `DELETE /services/providers/{id}` returns 404 | Card disappears after refetch | `404 on delete refetches list` |
| MPD-013 | `DELETE /services/providers/{id}` returns 500 | Toast; card remains; modal stays open | `500 on delete preserves card` |
| MPL-013 | `POST /services/list` returns 500 | Error toast; empty grid with retry affordance | `list 500 surfaces toast` |
| MPL-014 | `GET /services/providers/catalog` returns 500 (Add drawer) | Provider dropdown empty + toast; drawer remains open | `catalog 500 surfaces toast and disables provider picker` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-020 | Network failure on Create (`route.abort('failed')`) | Toast; drawer stays open with form intact (api_key preserved) | `network failure on create preserves form` |
| MPE-020 | Network failure on Edit | Toast; drawer stays open with edits intact | `network failure on edit preserves edits` |
| MPD-020 | Network failure on Delete | Toast; card remains; modal stays open | `network failure on delete preserves card` |
| MPC-021 | Slow `POST /services` (>3s) | Create button shows loading + `disabled`; no double-submit | `slow create disables button with loading state` |
| MPE-021 | Concurrent: another admin renames the same key | On Save, last-write-wins; list refetches with latest | `concurrent edit last-write-wins refreshes list` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-030 | Label whitespace only | Create disabled (after trim) | `whitespace-only label disables Create` |
| MPC-031 | Label leading/trailing whitespace | Trimmed before submit; card shows clean label | `label whitespace trimmed before submit` |
| MPC-032 | Label with emoji + unicode | Accepted; card renders unicode | `unicode + emoji label round-trips` |
| MPC-033 | Label `<script>alert(1)</script>` | Stored verbatim; rendered as text | `script tag in label is escaped on render` |
| MPC-034 | Label >500 chars | Inline error or backend 400; drawer stays open | `oversized label handled gracefully` |
| MPC-035 | Description >2000 chars | Either accepted or truncated with inline error | `oversized description handled gracefully` |
| MPC-036 | API key whitespace only | Create disabled (trim treats as empty) | `whitespace-only api_key disables Create` |
| MPC-037 | API key shorter than provider minimum (e.g. 4 chars) | Backend 400 + toast; drawer stays open | `short api_key rejected by backend` |
| MPC-038 | API key with leading/trailing whitespace | Trimmed before submit; round-trips as cleaned key | `api_key whitespace trimmed before submit` |
| MPC-039 | API key 5000 chars (very long token) | Either accepted or 400 with `detail`; never crashes drawer | `oversized api_key handled gracefully` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPC-040 | Tab through Add Provider drawer | Order: Service type → Provider → Label → Description → API key → Create | `Add Provider drawer tab order matches visual order` |
| MPC-041 | Submit drawer via Enter | Triggers Create if valid | `Enter key submits Add Provider drawer` |
| MPC-042 | Drawer traps focus + restores on close | Tab wraps; Escape closes; focus returns to `Add Provider` CTA | `drawer traps focus and restores on close` |
| MPC-043 | Inline `is required` helpers have `role="alert"` | Screen reader announces on blur | `inline errors are announced` |
| MPD-030 | Delete confirm modal keyboard-operable | Tab to Confirm; Enter confirms | `Delete confirm modal is keyboard-operable` |
| MPL-015 | API key input has `type="password"` and toggleable visibility | Toggling reveals; default state hides | `api_key field uses password input and toggles visibility` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPL-016 | Empty list (no keys configured) | Empty state with `Add Provider` CTA | `empty list shows Add Provider CTA` |
| MPL-017 | Type filter `LLM` | Only LLM cards visible | `LLM filter narrows the grid` |
| MPL-018 | Type filter `STT` then clear | Only STT cards visible, then full grid | `STT filter narrows then clears` |
| MPL-019 | Type filter `TTS` | Only TTS cards visible | `TTS filter narrows the grid` |
| MPL-020 | Search no-match → click `Clear` (or reset) | Full grid restored | `clearing no-match search restores grid` |
| MPL-021 | Sort by Name (if exposed) | Cards reorder asc/desc | `sort by name reorders cards` |
| MPL-022 | Infinite scroll boundary (last page) | No further fetch attempt; sentinel hidden | `infinite scroll stops at last page` |
| MPL-023 | Pagination / infinite scroll on first page | No `Previous` fetch; only forward | `first page has no backward fetch` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPN-010 | Click a card | Navigates to `/model-providers/{providerId}/{serviceType}` (detail page) | `card click navigates to detail page` |
| MPN-011 | Browser Back after navigating to detail | Returns to list with previous filter / search state preserved (⚠ unverified — confirm) | `back from detail preserves list filter state` |
| MPN-012 | Open Add Provider drawer, close via X | Drawer closes; URL unchanged; focus restored | `closing drawer restores focus to trigger` |

### Full lifecycle test (additional)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MPP-EXT | Create provider key → search → assert card → open detail via click → return → bulk delete via trash → assert gone | All transitions assert toast / row mutations; `try/finally` deletes the key | `lifecycle: create → search → navigate detail → return → delete` |
