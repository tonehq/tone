# Feature Doc: Model Providers — list page

Feature documentation for the `/model-providers` list page. Companion to
`frontend/e2e/dashboard/model-providers.spec.ts`.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/model-providers`
- **Component**: `frontend/src/components/service-providers/ServiceProvidersPage.tsx`
- **Sub-components**:
  - `service-grid.tsx` — infinite-scroll card grid
  - `api-key-create-drawer.tsx` — Add Provider drawer (also used on the detail page Keys tab)
  - `api-key-edit-drawer.tsx` — pencil-icon edit drawer
- **Auth required**: yes (redirects to `/auth/login?redirect=%2Fmodel-providers` without `tone_access_token`)

---

## User Stories

### US-1: View all configured providers as a card grid

**As an** org member, **I want to** see every (provider, service_type) pair I have keys for as a card grid at `/model-providers`, **so that** I can quickly review what is configured.

### US-2: Add a new API key for a chosen provider+service_type

**As an** admin/owner, **I want to** add a new API key for a chosen provider+service_type from a single "Add Provider" drawer (with the option to reuse an existing key on a different service_type), **so that** new providers can be onboarded without leaving the page.

### US-3: Edit the default key from the card

**As an** admin/owner, **I want to** edit the default key (label, description, active/default flags) directly from the card, **so that** I don't have to drill into the detail page for simple changes.

### US-4: Bulk-delete every key for a provider+service_type

**As an** admin/owner, **I want to** bulk-delete every key for a (provider, service_type) pair via the card's trash icon, **so that** I can de-provision an entire integration.

---

## Key files

- `ServiceProvidersPage.tsx` — toolbar + grid + delete modal
- `service-grid.tsx` — infinite-scroll card grid
- `api-key-create-drawer.tsx` — Add Provider drawer
- `api-key-edit-drawer.tsx` — pencil-icon edit drawer
- `frontend/src/atoms/ServicesAtom.tsx` — `servicesAtom`, `fetchServicesAtom`, `upsertServiceAtom`, `deleteProviderAtom`
- `frontend/src/services/servicesService.ts` — axios calls

---

## API endpoints exercised

| Method | Path                                                          | Triggered by                                |
| ------ | ------------------------------------------------------------- | ------------------------------------------- |
| POST   | `/services/list`                                              | grid load + every filter/search/sort change |
| GET    | `/services/providers/catalog`                                 | Add Provider drawer dropdown                |
| POST   | `/services` (201)                                             | Add Provider drawer Submit                  |
| PATCH  | `/services/{id}`                                              | card pencil → edit drawer Save              |
| DELETE | `/services/providers/{provider_id}?service_type=…`            | card trash → bulk delete                    |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. ID prefix legend:
> `TC-HAPPY-` (positive), `TC-VALIDATE-` (client validation), `TC-ERROR-` (server
> errors), `TC-NAV-` (navigation), `TC-LOADING-` (loading/disabled), `TC-EDGE-`
> (edge cases), `TC-A11Y-` (accessibility), `TC-FULL-` (lifecycle).

---

### TC-HAPPY-001: Visit /model-providers renders the header and Add Provider CTA

**Preconditions**:
- Authenticated session with at least zero (any) keys configured.

**Action**:
1. Visit `/model-providers`

**Observation 1 — Header renders**:
1. Page heading "Model Providers" (or equivalent) is visible
2. A total badge appears next to the heading
3. The "Add Provider" CTA button is visible in the header

**Observation 2 — Grid load fires**:
1. Exactly one `POST /services/list` request is recorded on mount

---

### TC-HAPPY-002: Type filter dropdown lists All / LLM / STT / TTS

**Action**:
1. Visit `/model-providers`
2. Open the type filter dropdown

**Observation 1 — Dropdown options**:
1. Options are exactly: All, LLM, STT, TTS

---

### TC-HAPPY-003: Search input is interactive

**Action**:
1. Visit `/model-providers`
2. Type a query into the search input
3. Clear the search input

**Observation 1 — Input state**:
1. The input accepts text and reflects the typed value
2. Clearing returns the input to empty state

**Observation 2 — Debounced refetch**:
1. After the debounce window, `POST /services/list` is re-fired with the search term in the body
2. Clearing the input re-fires `POST /services/list` without the search term

---

### TC-HAPPY-004: Click Add Provider opens drawer with form controls

**Action**:
1. Visit `/model-providers`
2. Click the "Add Provider" CTA

**Observation 1 — Drawer opens**:
1. The drawer is visible
2. Drawer contains a `service_type` select, a `provider` select, and an `api_key` input

**Observation 2 — Provider catalog fetched**:
1. Exactly one `GET /services/providers/catalog` request is recorded when the drawer opens

---

### TC-HAPPY-005: Search gibberish renders the empty state

**Action**:
1. Visit `/model-providers`
2. Type a gibberish string into the search box (e.g. `zzzzzzz_no_match`)

**Observation 1 — Empty-state copy appears**:
1. The grid shows an empty-state element with copy indicating no providers match
2. No card is rendered

---

### TC-HAPPY-006: Valid Create posts the form and the card grid updates

**Preconditions**:
- Drawer is open with provider catalog loaded.

**Action**:
1. Click "Add Provider"
2. Pick a service type and provider via `pickFirstProviderFromCatalog`
3. Fill in a unique `__e2e__` label, description, and a secret
4. Click Create

**Observation 1 — Network request**:
1. Exactly one `POST /services` is recorded
2. Provider id in the body matches an entry from `GET /services/providers/catalog`

**Observation 2 — Success feedback**:
1. A success toast appears in `[data-sonner-toast]`

**Observation 3 — Card grid updates**:
1. A new card matching the label is visible after the list refetch

**Cleanup**:
- The key is deleted in `try/finally`.

---

### TC-VALIDATE-001: Create button disabled when no provider selected

**Action**:
1. Click "Add Provider"
2. Leave the Provider select empty
3. Fill in `api_key`

**Observation 1 — Create button state**:
1. The Create button has the `disabled` attribute
2. Clicking Create produces zero `POST /services` requests

---

### TC-VALIDATE-002: Create button disabled when no api_key entered

**Action**:
1. Click "Add Provider"
2. Pick a provider
3. Leave the API key blank

**Observation 1 — Create button state**:
1. The Create button has the `disabled` attribute
2. Clicking Create produces zero `POST /services` requests

---

### TC-VALIDATE-003: Whitespace-only label disables Create

**Action**:
1. Click "Add Provider"
2. Pick provider + service type
3. Type `   ` (whitespace) into Label
4. Fill in `api_key`

**Observation 1 — Create button state**:
1. The Create button has the `disabled` attribute (after trim)

---

### TC-VALIDATE-004: Whitespace-only api_key disables Create

**Action**:
1. Click "Add Provider"
2. Pick provider + service type and a valid label
3. Type `   ` into API key

**Observation 1 — Create button state**:
1. The Create button is disabled (trim treats as empty)

---

### TC-ERROR-001: Duplicate label per provider surfaces an error toast

**Preconditions**:
- A key already exists with label `__e2e__dup`.

**Action**:
1. Click "Add Provider"
2. Pick the same provider + service type
3. Type the duplicate label `__e2e__dup`
4. Click Create

**Observation 1 — Network**:
1. Exactly one `POST /services` is recorded

**Observation 2 — Error feedback**:
1. An error toast appears with the backend conflict detail
2. The drawer stays open on the create page

**API mock**: `POST /services` → 409 conflict.

---

### TC-ERROR-002: 400 invalid api_key keeps drawer open

**Action**:
1. Open Add Provider, fill valid fields with a malformed api_key
2. Click Create

**Observation 1 — Toast**:
1. Toast surfaces the backend `detail` string

**Observation 2 — Drawer persists**:
1. Drawer remains open
2. Form values are preserved (api_key still in the field)

**API mock**: `POST /services` → 400.

---

### TC-ERROR-003: 401 on create triggers login redirect on next nav

**Action**:
1. Open Add Provider and submit a valid form

**Observation 1 — Toast**:
1. Toast title matches `Could not validate credentials`

**Observation 2 — Next navigation lands on login**:
1. Subsequent navigation triggers a 307 redirect to `/auth/login?redirect=...`

**API mock**: `POST /services` → 401.

---

### TC-ERROR-004: 403 on create shows toast

**Action**:
1. Open Add Provider and submit

**Observation 1 — Toast**:
1. Toast surfaces an access-denied / Forbidden message

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: `POST /services` → 403.

---

### TC-ERROR-005: 500 on create shows toast and preserves form

**Action**:
1. Open Add Provider, fill valid fields
2. Click Create

**Observation 1 — Toast**:
1. A generic error toast is visible

**Observation 2 — Drawer state**:
1. Drawer remains open
2. Form values are intact

**API mock**: `POST /services` → 500.

---

### TC-ERROR-006: 400 on edit keeps drawer open

**Action**:
1. Click a card pencil to open the edit drawer
2. Edit a field
3. Click Save

**Observation 1 — Toast surfaces detail**:
1. Toast displays the backend `detail`

**Observation 2 — Drawer persists**:
1. Edit drawer remains open with edits intact

**API mock**: `PATCH /services/{id}` → 400.

---

### TC-ERROR-007: 403 on edit shows toast

**Action**:
1. Open edit drawer, edit, Save

**Observation 1 — Toast**:
1. Toast title matches `Forbidden`

**Observation 2 — Drawer persists**:
1. Drawer remains open

**API mock**: `PATCH /services/{id}` → 403.

---

### TC-ERROR-008: 404 on edit closes drawer and refetches

**Action**:
1. Open edit drawer for a key
2. Edit and click Save

**Observation 1 — Toast**:
1. Toast title equals `Provider not found`

**Observation 2 — Drawer + list**:
1. Drawer closes
2. `POST /services/list` re-fires to refresh state

**API mock**: `PATCH /services/{id}` → 404.

---

### TC-ERROR-009: 500 on edit preserves edits

**Action**:
1. Open edit drawer, modify a field, Save

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Drawer persists**:
1. Drawer remains open with edits intact

**API mock**: `PATCH /services/{id}` → 500.

---

### TC-ERROR-010: 403 on delete preserves card

**Action**:
1. Click card trash icon
2. Confirm delete in modal

**Observation 1 — Toast**:
1. Toast title is `Forbidden`

**Observation 2 — Card persists**:
1. The card remains in the grid

**API mock**: `DELETE /services/providers/{id}` → 403.

---

### TC-ERROR-011: 404 on delete refetches list

**Action**:
1. Click card trash, confirm delete

**Observation 1 — List refetches**:
1. `POST /services/list` re-fires
2. The (stale) card disappears after refetch

**API mock**: `DELETE /services/providers/{id}` → 404.

---

### TC-ERROR-012: 500 on delete preserves card

**Action**:
1. Click card trash, confirm delete

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Card + modal**:
1. The card remains
2. The confirm modal stays open

**API mock**: `DELETE /services/providers/{id}` → 500.

---

### TC-ERROR-013: List 500 surfaces error toast

**Action**:
1. Visit `/model-providers`

**Observation 1 — Toast**:
1. An error toast is shown

**Observation 2 — Empty grid + retry**:
1. Grid renders empty with a retry affordance

**API mock**: `POST /services/list` → 500.

---

### TC-ERROR-014: Catalog 500 surfaces toast and disables provider picker

**Action**:
1. Click "Add Provider" with a failing catalog

**Observation 1 — Toast**:
1. An error toast appears

**Observation 2 — Dropdown state**:
1. The provider dropdown renders empty
2. The drawer remains open

**API mock**: `GET /services/providers/catalog` → 500.

---

### TC-LOADING-001: Slow create disables button with loading state

**Action**:
1. Open Add Provider, fill valid fields
2. Click Create against a deliberately slow backend (≥3s)

**Observation 1 — Loading state**:
1. The Create button shows a loading label
2. The Create button has the `disabled` attribute

**Observation 2 — No double-submit**:
1. Clicking Create multiple times produces exactly one `POST /services`

**API mock**: `POST /services` → 200 delayed by 3500 ms.

---

### TC-EDGE-001: Network failure on create preserves form

**Action**:
1. Open Add Provider, fill valid fields
2. Click Create with the route aborted (`failed`)

**Observation 1 — Toast**:
1. A generic error toast appears

**Observation 2 — Drawer persists**:
1. Drawer remains open
2. `api_key` field is preserved

---

### TC-EDGE-002: Network failure on edit preserves edits

**Action**:
1. Open edit drawer, modify a field
2. Click Save with the network aborted

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Drawer persists**:
1. Drawer remains open with edits intact

---

### TC-EDGE-003: Network failure on delete preserves card

**Action**:
1. Click card trash, confirm with the network aborted

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Card persists**:
1. The card remains
2. The modal stays open

---

### TC-EDGE-004: Concurrent edit last-write-wins refreshes list

**Preconditions**:
- Two admin sessions are editing the same key.

**Action**:
1. Admin A and Admin B both open the same key's edit drawer
2. Admin B renames first, then Admin A saves their rename

**Observation 1 — Last write wins**:
1. The final card label reflects Admin A's value after the refetch

**Observation 2 — Refetch fires**:
1. `POST /services/list` re-fires after Save

---

### TC-EDGE-005: Label whitespace trimmed before submit

**Action**:
1. Open Add Provider with label `  __e2e__cleanme  `
2. Fill remaining required fields
3. Click Create

**Observation 1 — Trimmed payload**:
1. `POST /services` body label equals `__e2e__cleanme` (trimmed)

**Observation 2 — Card label**:
1. The new card shows the trimmed label

---

### TC-EDGE-006: Label with emoji + unicode round-trips

**Action**:
1. Open Add Provider with label `__e2e__ rocket 🚀 ✨`
2. Submit

**Observation 1 — Body preserves unicode**:
1. `POST /services` body label equals the literal unicode string (UTF-8)

**Observation 2 — Card renders unicode**:
1. The card displays the emoji + unicode characters as visible text

---

### TC-EDGE-007: Script tag in label is escaped on render

**Action**:
1. Open Add Provider with label `<script>alert(1)</script>`
2. Submit

**Observation 1 — Stored verbatim**:
1. `POST /services` body contains the literal string

**Observation 2 — DOM is safe**:
1. The card renders the value as text (`<script>` visible as characters)
2. `window.alert` is never invoked

---

### TC-EDGE-008: Oversized label handled gracefully

**Action**:
1. Open Add Provider with a label of >500 chars
2. Click Create

**Observation 1 — Validation or backend rejection**:
1. Either an inline error appears OR a backend 400 toast is shown
2. The drawer remains open in both branches

---

### TC-EDGE-009: Oversized description handled gracefully

**Action**:
1. Open Add Provider with a description >2000 chars
2. Click Create

**Observation 1 — Acceptance or truncation**:
1. Either the request succeeds OR an inline error reports truncation
2. The drawer remains operable

---

### TC-EDGE-010: Short api_key rejected by backend

**Action**:
1. Open Add Provider with a 4-character api_key
2. Click Create

**Observation 1 — Backend reject**:
1. Backend returns 400 with a `detail`
2. Toast surfaces the detail
3. Drawer stays open

---

### TC-EDGE-011: API key whitespace trimmed before submit

**Action**:
1. Open Add Provider, fill `  sk-xxx  ` (with surrounding whitespace)
2. Submit

**Observation 1 — Trimmed payload**:
1. `POST /services` body api_key equals `sk-xxx` (trimmed)

---

### TC-EDGE-012: Oversized api_key handled gracefully

**Action**:
1. Open Add Provider with a 5000-char api_key
2. Click Create

**Observation 1 — Backend handles**:
1. Either the request succeeds OR backend returns 400 with a `detail`
2. The drawer never crashes

---

### TC-EDGE-013: Empty list shows Add Provider CTA

**Preconditions**:
- Zero keys configured.

**Action**:
1. Visit `/model-providers`

**Observation 1 — Empty state**:
1. An empty-state element renders
2. The "Add Provider" CTA is visible

---

### TC-EDGE-014: LLM filter narrows the grid

**Action**:
1. Visit `/model-providers`
2. Open the type filter and choose LLM

**Observation 1 — Refetch**:
1. `POST /services/list` re-fires with the LLM filter in the body

**Observation 2 — Grid state**:
1. Only LLM cards are visible

---

### TC-EDGE-015: STT filter narrows then clears

**Action**:
1. Visit `/model-providers`
2. Choose STT in the type filter
3. Clear the filter to All

**Observation 1 — STT-only state**:
1. Only STT cards are visible after step 2

**Observation 2 — Full grid restored**:
1. After step 3, all cards reappear

---

### TC-EDGE-016: TTS filter narrows the grid

**Action**:
1. Visit `/model-providers`
2. Choose TTS in the type filter

**Observation 1 — Grid state**:
1. Only TTS cards are visible

---

### TC-EDGE-017: Clearing no-match search restores grid

**Action**:
1. Type a gibberish search that yields no matches
2. Click Clear (or reset)

**Observation 1 — Full grid restored**:
1. All cards are visible again

---

### TC-EDGE-018: Sort by Name reorders cards

**Preconditions**:
- Sort by Name control is exposed.

**Action**:
1. Toggle sort by Name asc, then desc

**Observation 1 — Refetch**:
1. `POST /services/list` re-fires with `sort` params per direction

**Observation 2 — Order changes**:
1. Card order in the grid changes accordingly

---

### TC-EDGE-019: Infinite scroll stops at last page

**Action**:
1. Scroll to the bottom of the grid

**Observation 1 — No further fetch**:
1. No additional `POST /services/list` fires past the last page
2. The infinite-scroll sentinel is hidden

---

### TC-EDGE-020: First page has no backward fetch

**Action**:
1. Visit `/model-providers`

**Observation 1 — Forward-only paging**:
1. No "Previous" request is fired on first load
2. Only forward fetches occur as the user scrolls

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/model-providers`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmodel-providers`

---

### TC-NAV-002: Expired token redirects to login

**Preconditions**:
- Expired `tone_access_token` cookie present.

**Action**:
1. Visit `/model-providers`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmodel-providers`

**Observation 2 — Cookie cleanup**:
1. The expired cookie is cleared by middleware

---

### TC-NAV-003: Member role cannot see Add Provider CTA

**Preconditions**:
- Authenticated as a member (non-admin/owner).

**Action**:
1. Visit `/model-providers`

**Observation 1 — Read-only grid**:
1. Cards are visible read-only

**Observation 2 — CTA hidden/disabled**:
1. The "Add Provider" CTA is hidden or disabled

---

### TC-NAV-004: Direct create as member surfaces 403 toast

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Invoke `POST /services` directly (e.g. via console / API call)

**Observation 1 — Toast**:
1. Toast title contains `Forbidden`

**API response**: `POST /services` → 403.

---

### TC-NAV-005: Member cannot delete provider keys

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Inspect a card

**Observation 1 — Trash hidden/disabled**:
1. The trash icon is hidden or disabled

---

### TC-NAV-006: Card click navigates to detail page

**Action**:
1. Visit `/model-providers`
2. Click any card

**Observation 1 — URL change**:
1. URL becomes `/model-providers/{providerId}/{serviceType}`

---

### TC-NAV-007: Back from detail preserves list filter state

**Preconditions**:
- A filter or search was set before clicking a card. ⚠ unverified.

**Action**:
1. Set a filter/search on `/model-providers`
2. Click a card
3. Press browser Back

**Observation 1 — Return URL**:
1. URL becomes `/model-providers`

**Observation 2 — Filter state**:
1. The previously applied filter/search is still active. ⚠ unverified — confirm.

---

### TC-NAV-008: Closing drawer restores focus to trigger

**Action**:
1. Click "Add Provider"
2. Close the drawer via the X button

**Observation 1 — Drawer closes + URL stable**:
1. Drawer is no longer in the DOM
2. URL is unchanged

**Observation 2 — Focus restored**:
1. Focus returns to the "Add Provider" CTA

---

### TC-A11Y-001: Add Provider drawer tab order matches visual order

**Action**:
1. Open the Add Provider drawer
2. Tab through the fields

**Observation 1 — Tab order**:
1. Focus moves Service type → Provider → Label → Description → API key → Create

---

### TC-A11Y-002: Enter key submits Add Provider drawer

**Action**:
1. Open drawer, fill valid fields
2. Focus a field and press Enter

**Observation 1 — Submit**:
1. Exactly one `POST /services` request fires

---

### TC-A11Y-003: Drawer traps focus and restores on close

**Action**:
1. Open the drawer
2. Press Tab repeatedly to wrap
3. Press Escape

**Observation 1 — Focus trap**:
1. Tab cycles within the drawer (does not leak to background)

**Observation 2 — Restore on close**:
1. Escape closes the drawer
2. Focus returns to the "Add Provider" CTA

---

### TC-A11Y-004: Inline errors are announced

**Action**:
1. Open drawer
2. Trigger an inline `is required` helper (e.g. blur a required field)

**Observation 1 — ARIA**:
1. The inline error element has `role="alert"` (or `aria-live`)

---

### TC-A11Y-005: Delete confirm modal is keyboard-operable

**Action**:
1. Click card trash
2. Tab to Confirm button and press Enter

**Observation 1 — Confirmation**:
1. The delete confirmation triggers

---

### TC-A11Y-006: api_key field uses password input and toggles visibility

**Action**:
1. Open the Add Provider drawer
2. Inspect the api_key input
3. Toggle the visibility control

**Observation 1 — Default masked**:
1. The api_key input has `type="password"` initially

**Observation 2 — Toggle reveals**:
1. Toggling the eye control switches type to `text`
2. Toggling again returns to `password`

---

### TC-FULL-001: Lifecycle — create → search → assert card → delete → assert gone

**Preconditions**:
- Authenticated. No prior `__e2e__` key exists.

**Action**:
1. Visit `/model-providers`
2. Click "Add Provider"
3. Use `pickFirstProviderFromCatalog({ serviceType })` to choose a provider
4. Fill in a unique `__e2e__` label, description, and api_key
5. Click Create
6. Search for the new label in the toolbar
7. Click the per-card delete icon and confirm
8. Cleanup: ensure the key is deleted in `try/finally`

**Observation 1 — Catalog fetch**:
1. `GET /services/providers/catalog` is recorded when the drawer opens

**Observation 2 — Create success**:
1. Exactly one `POST /services` is recorded with the chosen provider id
2. A success toast appears

**Observation 3 — Search narrows to the new card**:
1. After typing the label in search, the grid contains the new card
2. No other cards are visible

**Observation 4 — Delete**:
1. `DELETE /services/providers/{provider_id}?service_type=…` is recorded
2. Grid card count drops to 0 for that label
3. A success toast for delete appears

---

### TC-FULL-002: Lifecycle — create → search → navigate detail → return → delete

**Preconditions**:
- Authenticated.

**Action**:
1. Create a `__e2e__` provider key as in TC-FULL-001 steps 1–5
2. Search for the new label
3. Click the card to navigate to detail
4. Press browser Back
5. Bulk-delete via the card trash icon
6. Cleanup in `try/finally`

**Observation 1 — Detail navigation**:
1. URL becomes `/model-providers/{providerId}/{serviceType}`

**Observation 2 — Return to list**:
1. URL returns to `/model-providers`

**Observation 3 — Delete**:
1. `DELETE /services/providers/{...}` fires
2. The card is removed from the grid

---

## Field coverage map (TC-FULL-001)

| Section             | Field        | Selector                                              | Helper                                            | Asserted                          |
| ------------------- | ------------ | ----------------------------------------------------- | ------------------------------------------------- | --------------------------------- |
| Add Provider drawer | Service type | `button[id="service_type"]`                           | `pickFirstProviderFromCatalog({ serviceType })`   | indirect (provider list filters)  |
| Add Provider drawer | Provider     | `button[id="provider_id"]`                            | `pickFirstProviderFromCatalog`                    | id from `/services/providers/catalog` |
| Add Provider drawer | Label        | `input[name="label"]`                                 | inline fill                                       | label appears in card grid        |
| Add Provider drawer | Description  | `textarea[name="description"]`                        | inline fill                                       | —                                 |
| Add Provider drawer | API key      | `input[name="api_key"]`                               | inline fill                                       | — (never re-displayed)            |
| List                | Search box   | `input[placeholder="Search providers or services…"]`  | inline fill                                       | narrows grid to the new card      |
| Card                | Delete icon  | per-card `button[aria-label*="Delete"]`               | `deleteApiKeyViaUI`                               | row count drops to 0              |

---

## Deferred (`test.fixme`)

- `MPC-004` (reuse-key path) — needs a 2-service-type seed (a single provider with both LLM and STT keys). Re-enable once that seed exists.
- `MPE-001..MPE-003` (list-page pencil edit) — covered by the detail-page Edit scenarios (`AKE-` in `model-providers-detail.md`).
- `MPD-002` (confirm-delete removes card) — covered by TC-FULL-001.

---

## Cleanup

Every test that creates a key cancels it in `try/finally` via `deleteApiKeyViaUI`. Labels are `__e2e__key_*`-prefixed so any leftovers from aborted runs can be swept by API.

---

## Mapping: old scenario IDs → new TC IDs

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| MPL-001         | TC-HAPPY-001      | renders the header + Add Provider CTA                                |
| MPL-002         | TC-HAPPY-002      | type filter dropdown lists all/llm/stt/tts                           |
| MPL-003         | TC-HAPPY-003      | search input is interactive                                          |
| MPL-004         | TC-HAPPY-004      | Add Provider drawer opens with service_type + provider fields        |
| MPL-005         | TC-HAPPY-005      | empty state when search matches nothing                              |
| MPC-001         | TC-HAPPY-006      | valid Create posts the form and the card grid updates                |
| MPC-002         | TC-VALIDATE-001   | Create button is disabled with no provider selected                  |
| MPC-003         | TC-VALIDATE-002   | Create button is disabled with no api_key entered                    |
| MPC-030         | TC-VALIDATE-003   | whitespace-only label disables Create                                |
| MPC-036         | TC-VALIDATE-004   | whitespace-only api_key disables Create                              |
| MPC-005         | TC-ERROR-001      | duplicate label per provider surfaces an error toast                 |
| MPC-011         | TC-ERROR-002      | 400 invalid api_key keeps drawer open                                |
| MPC-012         | TC-ERROR-003      | 401 on create triggers login redirect on next nav                    |
| MPC-013         | TC-ERROR-004      | 403 on create shows toast                                            |
| MPC-014         | TC-ERROR-005      | 500 on create shows toast and preserves form                         |
| MPE-010         | TC-ERROR-006      | 400 on edit keeps drawer open                                        |
| MPE-011         | TC-ERROR-007      | 403 on edit shows toast                                              |
| MPE-012         | TC-ERROR-008      | 404 on edit closes drawer and refetches                              |
| MPE-013         | TC-ERROR-009      | 500 on edit preserves edits                                          |
| MPD-011         | TC-ERROR-010      | 403 on delete shows toast and preserves card                         |
| MPD-012         | TC-ERROR-011      | 404 on delete refetches list                                         |
| MPD-013         | TC-ERROR-012      | 500 on delete preserves card                                         |
| MPL-013         | TC-ERROR-013      | list 500 surfaces toast                                              |
| MPL-014         | TC-ERROR-014      | catalog 500 surfaces toast and disables provider picker              |
| MPC-021         | TC-LOADING-001    | slow create disables button with loading state                       |
| MPC-020         | TC-EDGE-001       | network failure on create preserves form                             |
| MPE-020         | TC-EDGE-002       | network failure on edit preserves edits                              |
| MPD-020         | TC-EDGE-003       | network failure on delete preserves card                             |
| MPE-021         | TC-EDGE-004       | concurrent edit last-write-wins refreshes list                       |
| MPC-031         | TC-EDGE-005       | label whitespace trimmed before submit                               |
| MPC-032         | TC-EDGE-006       | unicode + emoji label round-trips                                    |
| MPC-033         | TC-EDGE-007       | script tag in label is escaped on render                             |
| MPC-034         | TC-EDGE-008       | oversized label handled gracefully                                   |
| MPC-035         | TC-EDGE-009       | oversized description handled gracefully                             |
| MPC-037         | TC-EDGE-010       | short api_key rejected by backend                                    |
| MPC-038         | TC-EDGE-011       | api_key whitespace trimmed before submit                             |
| MPC-039         | TC-EDGE-012       | oversized api_key handled gracefully                                 |
| MPL-016         | TC-EDGE-013       | empty list shows Add Provider CTA                                    |
| MPL-017         | TC-EDGE-014       | LLM filter narrows the grid                                          |
| MPL-018         | TC-EDGE-015       | STT filter narrows then clears                                       |
| MPL-019         | TC-EDGE-016       | TTS filter narrows the grid                                          |
| MPL-020         | TC-EDGE-017       | clearing no-match search restores grid                               |
| MPL-021         | TC-EDGE-018       | sort by name reorders cards                                          |
| MPL-022         | TC-EDGE-019       | infinite scroll stops at last page                                   |
| MPL-023         | TC-EDGE-020       | first page has no backward fetch                                     |
| MPL-010         | TC-NAV-001        | unauthenticated visit redirects to login                             |
| MPL-011         | TC-NAV-002        | expired token redirects to login                                     |
| MPL-012         | TC-NAV-003        | member role cannot see Add Provider CTA                              |
| MPC-010         | TC-NAV-004        | direct create as member surfaces 403 toast                           |
| MPD-010         | TC-NAV-005        | member cannot delete provider keys                                   |
| MPN-010         | TC-NAV-006        | card click navigates to detail page                                  |
| MPN-011         | TC-NAV-007        | back from detail preserves list filter state                         |
| MPN-012         | TC-NAV-008        | closing drawer restores focus to trigger                             |
| MPC-040         | TC-A11Y-001       | Add Provider drawer tab order matches visual order                   |
| MPC-041         | TC-A11Y-002       | Enter key submits Add Provider drawer                                |
| MPC-042         | TC-A11Y-003       | drawer traps focus and restores on close                             |
| MPC-043         | TC-A11Y-004       | inline errors are announced                                          |
| MPD-030         | TC-A11Y-005       | Delete confirm modal is keyboard-operable                            |
| MPL-015         | TC-A11Y-006       | api_key field uses password input and toggles visibility             |
| MPP-FULL        | TC-FULL-001       | create → assert card → delete → assert gone                          |
| MPP-EXT         | TC-FULL-002       | lifecycle: create → search → navigate detail → return → delete       |
