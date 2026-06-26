# Feature Doc: Model Providers — detail page

Feature documentation for the `/model-providers/{providerId}/{serviceType}` detail
page. Companion to `frontend/e2e/dashboard/model-providers-detail.spec.ts`. Two
tabs are covered: **API Keys** and **Models**.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/model-providers/{providerId}/{serviceType}`
- **Component**: `frontend/src/components/service-providers/ServiceProviderDetailPage.tsx`
- **Sub-components**:
  - `api-key-create-drawer.tsx`, `api-key-edit-drawer.tsx` — Keys CRUD drawers
  - `model-form-drawer.tsx` — Models CRUD drawer (kind locked to llm/stt/tts)
- **Auth required**: yes (redirects to `/auth/login?redirect=...` without `tone_access_token`)

---

## User Stories

### US-1: View tabs with counts

**As an** admin/owner, **I want to** open `/model-providers/{providerId}/{serviceType}` and see two tabs: API Keys (count) + Models (count).

### US-2: Add / edit / delete API keys for the provider+service_type pair

**As an** admin/owner, **I want to** add, edit, and delete API keys for the chosen (provider, service_type) pair from the Keys tab.

### US-3: Add / edit / delete provider models

**As an** admin/owner, **I want to** add, edit, and delete provider-models from the Models tab.

### US-4: Plaintext secret never re-shown

**As an** admin/owner, **I want** the secret value of an API key to be **never** shown after the initial create — the list always shows a masked placeholder.

---

## Key files

- `ServiceProviderDetailPage.tsx` — tab strip, keys table, models table, delete modals
- `api-key-create-drawer.tsx`, `api-key-edit-drawer.tsx` — Keys CRUD drawers (provider + service_type locked)
- `model-form-drawer.tsx` — Models CRUD drawer
- `frontend/src/atoms/ServicesAtom.tsx` — `providerKeysAtom`, `providerModelsAtom`, write atoms
- `frontend/src/services/servicesService.ts` — axios calls

---

## API endpoints exercised

| Method | Path                                                                            | Triggered by                          |
| ------ | ------------------------------------------------------------------------------- | ------------------------------------- |
| POST   | `/services/providers/{provider_id}/keys`                                        | Keys-tab list load                    |
| POST   | `/services` (201)                                                               | Add API key drawer Submit             |
| PATCH  | `/services/{id}`                                                                | row click → edit drawer Save          |
| DELETE | `/services/{id}`                                                                | row trash icon → confirm              |
| POST   | `/services/providers/{provider_id}/models`                                      | Models-tab list load                  |
| POST   | `/services/providers/{provider_id}/models/create` (201, admin/owner)            | Add model drawer Save                 |
| PATCH  | `/services/providers/{provider_id}/models/{model_id}` (admin/owner)             | row click → edit drawer Save          |
| DELETE | `/services/providers/{provider_id}/models/{model_id}` (admin/owner)             | row trash → confirm                   |

---

## Test Cases — API Keys

> Every test case is **one Action + multiple Observations**. ID prefix legend:
> `TC-HAPPY-`, `TC-VALIDATE-`, `TC-ERROR-`, `TC-NAV-`, `TC-LOADING-`,
> `TC-EDGE-`, `TC-A11Y-`, `TC-FULL-`.

---

### TC-HAPPY-001: Page loads with Keys tab active

**Action**:
1. Visit `/model-providers/{providerId}/{serviceType}`

**Observation 1 — Tab state**:
1. The Keys tab button has `aria-pressed="true"`

**Observation 2 — Keys list fires**:
1. Exactly one `POST /services/providers/{provider_id}/keys` is recorded on mount

---

### TC-HAPPY-002: Keys table renders the documented columns

**Action**:
1. Visit the detail page

**Observation 1 — Column headers**:
1. Headers Name, Type, Status are visible in the keys table

---

### TC-HAPPY-003: Fixture key appears in the list

**Preconditions**:
- The shared `beforeAll` fixture key (`__e2e__` prefixed) exists.

**Action**:
1. Visit the detail page

**Observation 1 — Row visible**:
1. A row matches the `__e2e__` fixture label

---

### TC-HAPPY-004: Search filters rows by label

**Action**:
1. Type gibberish into the search field

**Observation 1 — No rows**:
1. The keys table renders zero rows

---

### TC-HAPPY-005: Add API key button opens drawer

**Action**:
1. Click "Add API key"

**Observation 1 — Drawer opens**:
1. The Add API key drawer is visible
2. Provider + service_type fields are locked (read-only/disabled)

---

### TC-HAPPY-006: Valid Create → row + success toast

**Action**:
1. Click "Add API key"
2. Fill label + api_key
3. Click Create

**Observation 1 — Network**:
1. Exactly one `POST /services` is recorded

**Observation 2 — Success feedback**:
1. A success toast appears

**Observation 3 — Row visible**:
1. A new row matching the label appears in the keys table

**Cleanup**: delete the key in `try/finally`.

---

### TC-HAPPY-007: Clicking a row opens the edit drawer

**Action**:
1. Click an existing key row

**Observation 1 — Drawer opens**:
1. The edit drawer is visible with fields pre-populated

---

### TC-HAPPY-008: Editing description persists on reload

**Action**:
1. Click a key row
2. Edit the description field
3. Click Save
4. Reload the page

**Observation 1 — Save fires**:
1. Exactly one `PATCH /services/{id}` is recorded

**Observation 2 — Persistence**:
1. After reload, the new description is visible on the row / in the edit drawer

---

### TC-HAPPY-009: Row trash icon opens the confirm modal

**Action**:
1. Click the trash icon on a row

**Observation 1 — Modal**:
1. The confirm modal is visible

---

### TC-VALIDATE-001: Create button is disabled with no api_key entered

**Action**:
1. Open Add API key drawer
2. Fill label but leave api_key blank

**Observation 1 — Button state**:
1. The Create button is `disabled`
2. Clicking Create produces zero `POST /services` requests

---

### TC-VALIDATE-002: Whitespace-only label disables Create

**Action**:
1. Open Add API key drawer
2. Type `   ` into Label, fill api_key

**Observation 1 — Button state**:
1. The Create button is disabled

---

### TC-VALIDATE-003: Whitespace-only api_key disables Create

**Action**:
1. Open drawer, fill label
2. Type `   ` into api_key

**Observation 1 — Button state**:
1. Create is disabled

---

### TC-ERROR-001: Duplicate label surfaces an error toast

**Preconditions**:
- A key already exists with label `__e2e__dup`.

**Action**:
1. Open Add API key drawer
2. Submit a duplicate label

**Observation 1 — Toast**:
1. An error toast is visible

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: `POST /services` → 409.

---

### TC-ERROR-002: 400 on create keeps drawer open

**Action**:
1. Open Add API key drawer, fill and Submit

**Observation 1 — Toast surfaces detail**:
1. Toast displays the backend `detail`

**Observation 2 — Drawer state**:
1. Drawer remains open with form intact

**API mock**: `POST /services` → 400.

---

### TC-ERROR-003: 401 on create triggers login redirect on next nav

**Action**:
1. Submit Add API key

**Observation 1 — Toast**:
1. Toast title matches `Could not validate credentials`

**Observation 2 — Next nav**:
1. Subsequent navigation redirects to `/auth/login?redirect=...`

**API mock**: `POST /services` → 401.

---

### TC-ERROR-004: 403 on create shows toast

**Action**:
1. Submit Add API key

**Observation 1 — Toast**:
1. Toast title matches `Forbidden`

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: `POST /services` → 403.

---

### TC-ERROR-005: 500 on create shows toast

**Action**:
1. Submit Add API key

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Drawer state**:
1. Drawer remains open intact

**API mock**: `POST /services` → 500.

---

### TC-ERROR-006: 400 on edit keeps drawer open

**Action**:
1. Open edit drawer, edit a field, Save

**Observation 1 — Toast**:
1. Toast displays the backend `detail`

**Observation 2 — Drawer persists**:
1. Edit drawer stays open with edits intact

**API mock**: `PATCH /services/{id}` → 400.

---

### TC-ERROR-007: 404 on edit closes drawer and refetches

**Action**:
1. Open edit drawer and Save

**Observation 1 — Drawer + list**:
1. Drawer closes
2. The keys list refetches

**API mock**: `PATCH /services/{id}` → 404.

---

### TC-ERROR-008: 409 on edit shows conflict toast

**Action**:
1. Open edit drawer, rename to a conflicting label, Save

**Observation 1 — Toast**:
1. Toast surfaces the conflict detail

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: `PATCH /services/{id}` → 409.

---

### TC-ERROR-009: 500 on edit preserves edits

**Action**:
1. Open edit drawer, edit, Save

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Drawer persists**:
1. Drawer stays open with edits intact

**API mock**: `PATCH /services/{id}` → 500.

---

### TC-ERROR-010: 403 on delete shows toast

**Action**:
1. Click row trash, confirm

**Observation 1 — Toast**:
1. Toast title matches `Forbidden`

**Observation 2 — Row persists**:
1. The row remains in the table

**API mock**: `DELETE /services/{id}` → 403.

---

### TC-ERROR-011: 404 on delete refetches list

**Action**:
1. Click row trash, confirm

**Observation 1 — List refetches**:
1. Keys list endpoint re-fires
2. The stale row disappears after refetch

**API mock**: `DELETE /services/{id}` → 404.

---

### TC-ERROR-012: 500 on delete preserves row

**Action**:
1. Click row trash, confirm

**Observation 1 — Toast**:
1. Generic error toast is visible

**Observation 2 — Row + modal**:
1. The row remains
2. The confirm modal stays open

**API mock**: `DELETE /services/{id}` → 500.

---

### TC-ERROR-013: Keys list 500 surfaces toast

**Action**:
1. Visit the detail page

**Observation 1 — Toast**:
1. An error toast appears

**Observation 2 — Empty table + retry**:
1. The table renders empty with a retry affordance

**API mock**: `POST /services/providers/{id}/keys` → 500.

---

### TC-LOADING-001: Slow create disables button

**Action**:
1. Open Add API key drawer, fill, Submit with a ≥3s slow backend

**Observation 1 — Loading state**:
1. Create button shows loading + `disabled`

**Observation 2 — No double-submit**:
1. Multi-click yields exactly one `POST /services`

**API mock**: `POST /services` → 200 delayed 3500 ms.

---

### TC-EDGE-001: Network failure on create preserves form

**Action**:
1. Open drawer, fill, Submit with route aborted

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Drawer persists**:
1. Drawer stays open with form intact

---

### TC-EDGE-002: Network failure on edit preserves edits

**Action**:
1. Open edit drawer, modify, Save with route aborted

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Drawer persists**:
1. Drawer stays open with edits intact

---

### TC-EDGE-003: Network failure on delete preserves row

**Action**:
1. Click trash, confirm with route aborted

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Row persists**:
1. Row remains

---

### TC-EDGE-004: Concurrent edit last-write-wins

**Action**:
1. Two admins open the same key's edit drawer
2. The second one saves first, then the first one saves

**Observation 1 — Last write wins**:
1. The final row reflects the first admin's value after refetch

---

### TC-EDGE-005: Label whitespace trimmed before submit

**Action**:
1. Open Add API key drawer with label `  __e2e__cleanme  `
2. Submit

**Observation 1 — Trimmed payload**:
1. `POST /services` body label equals `__e2e__cleanme`

---

### TC-EDGE-006: Unicode + emoji label round-trips

**Action**:
1. Open drawer with label `__e2e__ 🔥 unicode`
2. Submit

**Observation 1 — Body preserves unicode**:
1. The request body contains the literal unicode string

**Observation 2 — Row renders unicode**:
1. The row displays the unicode characters as visible text

---

### TC-EDGE-007: Script tag in label is escaped on render

**Action**:
1. Open drawer with label `<script>alert(1)</script>`
2. Submit

**Observation 1 — Stored verbatim**:
1. The request body contains the literal string

**Observation 2 — DOM is safe**:
1. The label renders as text
2. `window.alert` is never invoked

---

### TC-EDGE-008: Oversized label handled gracefully

**Action**:
1. Open drawer with a >500-char label
2. Submit

**Observation 1 — Inline or backend error**:
1. Either an inline error appears OR backend returns 400 with a toast

---

### TC-EDGE-009: API key whitespace trimmed before submit

**Action**:
1. Open drawer, fill `  sk-xxx  ` into api_key
2. Submit

**Observation 1 — Trimmed payload**:
1. Body api_key equals `sk-xxx`

---

### TC-EDGE-010: Short api_key rejected by backend

**Action**:
1. Open drawer with api_key of 4 chars
2. Submit

**Observation 1 — Toast**:
1. Backend 400 toast appears
2. Drawer stays open

---

### TC-EDGE-011: Oversized api_key handled gracefully

**Action**:
1. Open drawer with a 5000-char api_key
2. Submit

**Observation 1 — Backend handles**:
1. Either the request succeeds OR backend 400 with toast
2. The drawer never crashes

---

### TC-EDGE-012: Secret value is masked after create and not in DOM after reload

**Action**:
1. Create a key via the drawer
2. Navigate away and back / reload

**Observation 1 — Always masked**:
1. The row renders a masked placeholder for the secret

**Observation 2 — Not in DOM**:
1. The plaintext api_key value is not present anywhere in the rendered DOM after reload

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**:
- No `tone_access_token` cookie.

**Action**:
1. Visit `/model-providers/{id}/{type}`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmodel-providers%2F{id}%2F{type}`

---

### TC-NAV-002: Expired token redirects to login

**Preconditions**:
- Expired token cookie.

**Action**:
1. Visit the detail page

**Observation 1 — Redirect**:
1. URL becomes the login redirect

**Observation 2 — Cookie cleanup**:
1. The expired cookie is cleared

---

### TC-NAV-003: Member role cannot add API key

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Visit detail page

**Observation 1 — Read-only**:
1. Key rows are visible read-only
2. "Add API key" CTA is hidden or disabled

---

### TC-NAV-004: Direct create as member surfaces 403 toast

**Action**:
1. Submit `POST /services` directly as a member

**Observation 1 — Toast**:
1. Toast title equals `Forbidden`

**API**: 403.

---

### TC-NAV-005: Member role cannot edit API key

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Click a row

**Observation 1 — Read-only drawer**:
1. Edit drawer opens read-only OR Save is disabled

---

### TC-NAV-006: Member cannot delete API key

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Inspect a row

**Observation 1 — Trash hidden/disabled**:
1. The trash icon is hidden or disabled

---

### TC-NAV-007: Tab switch updates aria-pressed and URL

**Action**:
1. Visit detail page (Keys tab active)
2. Click the Models tab

**Observation 1 — Tab state**:
1. Models tab button has `aria-pressed="true"`
2. URL contains `?tab=models`

---

### TC-NAV-008: Back navigation returns to list

**Action**:
1. Click the back chevron / breadcrumb

**Observation 1 — Return URL**:
1. URL becomes `/model-providers`

---

### TC-NAV-009: Back after edit does not prompt for unsaved changes

**Action**:
1. Open edit drawer, modify a field, close
2. Press browser Back

**Observation 1 — No prompt**:
1. No unsaved-changes prompt appears
2. Navigation completes

---

### TC-A11Y-001: Create drawer tab order matches visual order

**Action**:
1. Open Add API key drawer
2. Tab through fields

**Observation 1 — Tab order**:
1. Focus moves Label → Description → API key → Active → Default → Create

---

### TC-A11Y-002: Enter key submits Create drawer

**Action**:
1. Open drawer, fill valid fields
2. Press Enter

**Observation 1 — Submit**:
1. Exactly one `POST /services` fires

---

### TC-A11Y-003: Drawer traps focus and restores on close

**Action**:
1. Open drawer
2. Tab to wrap
3. Press Escape

**Observation 1 — Focus trap**:
1. Tab cycles within drawer

**Observation 2 — Restore on close**:
1. Escape closes drawer
2. Focus returns to the trigger

---

### TC-A11Y-004: api_key field uses password input and toggles visibility

**Action**:
1. Open drawer
2. Inspect api_key input and toggle visibility

**Observation 1 — Default masked**:
1. The api_key input has `type="password"`

**Observation 2 — Toggle reveals**:
1. Toggling switches type to `text`, then back

---

### TC-A11Y-005: Inline errors are announced

**Action**:
1. Trigger a required-field error

**Observation 1 — ARIA**:
1. Inline error element has `role="alert"` (or `aria-live`)

---

### TC-A11Y-006: Delete confirm modal is keyboard-operable

**Action**:
1. Click row trash
2. Tab to Confirm, press Enter

**Observation 1 — Confirmation triggers**:
1. The delete request fires

---

### TC-EDGE-013: Empty keys list shows add CTA

**Preconditions**:
- No keys exist for this provider+service_type.

**Action**:
1. Visit the detail page

**Observation 1 — Empty state**:
1. An empty-state element renders with the "Add API key" CTA

---

### TC-EDGE-014: No-match search shows empty state

**Action**:
1. Type a gibberish search query

**Observation 1 — Empty state**:
1. A `No matches` empty state is visible

---

### TC-EDGE-015: Sort by name reorders rows

**Action**:
1. Toggle sort by Name asc / desc

**Observation 1 — Row order**:
1. Rows reorder according to direction

---

### TC-EDGE-016: Sort by status reorders rows

**Action**:
1. Toggle sort by Status

**Observation 1 — Grouping**:
1. Active rows are grouped per direction

---

### TC-FULL-001: Lifecycle — create → list (masked) → edit description → reload + verify → delete

**Action**:
1. Open Add API key drawer
2. Fill label `__e2e__lifecycle`, description, and api_key
3. Click Create
4. Verify the new row appears with the secret masked
5. Click the row, edit description, Save
6. Reload the page
7. Click row trash, confirm delete
8. Cleanup in `try/finally`

**Observation 1 — Create**:
1. Exactly one `POST /services` is recorded
2. Success toast is visible

**Observation 2 — Masked secret**:
1. The row renders a masked placeholder
2. Plaintext api_key is not in the DOM

**Observation 3 — Edit persists**:
1. `PATCH /services/{id}` fires with the new description
2. After reload, the new description is visible

**Observation 4 — Delete**:
1. `DELETE /services/{id}` fires
2. The row disappears from the table

---

### TC-FULL-002: Lifecycle — create → search → edit → reload → delete (extended)

**Action**:
1. Create a key with `default off, active on`
2. Search to narrow to the new row
3. Edit label + description, Save
4. Reload
5. Delete
6. Cleanup in `try/finally`

**Observation 1 — Create**:
1. `POST /services` records `is_default=false, is_active=true`
2. Success toast appears

**Observation 2 — Search narrows**:
1. Only the new row is visible

**Observation 3 — Edit**:
1. `PATCH /services/{id}` body contains new label + description
2. Reload shows the new values

**Observation 4 — Delete**:
1. `DELETE /services/{id}` fires
2. Row removed; success toast shown

---

## Test Cases — Provider Models

---

### TC-HAPPY-001: Models tab activates and the table renders

**Action**:
1. Visit detail page
2. Click the Models tab

**Observation 1 — Tab state**:
1. Models tab button has `aria-pressed="true"`

**Observation 2 — List fires**:
1. `POST /services/providers/{provider_id}/models` is recorded

---

### TC-HAPPY-002: Models table renders the documented columns

**Action**:
1. Open Models tab

**Observation 1 — Column headers**:
1. Headers Name, Kind, Status are visible

---

### TC-HAPPY-003: Add Model button opens the drawer

**Action**:
1. Click "Add model"

**Observation 1 — Drawer opens**:
1. The Add model drawer is visible
2. The Kind dropdown is locked to llm/stt/tts

---

### TC-HAPPY-004: Create minimal model (name + kind) succeeds

**Action**:
1. Click Add model
2. Fill name = `__e2e__minimal`, choose Kind
3. Click Save

**Observation 1 — Network**:
1. Exactly one `POST /services/providers/{id}/models/create` is recorded

**Observation 2 — Row + toast**:
1. The new row appears in the table
2. Success toast is visible

**Cleanup**: delete the model in `try/finally`.

---

### TC-HAPPY-005: Create with all fields persists

**Action**:
1. Click Add model
2. Fill name, display_name, kind, description
3. Click Save

**Observation 1 — Row display name**:
1. The row shows `display_name` preferentially over `name`

---

### TC-HAPPY-006: Editing display_name persists on reload

**Action**:
1. Click a model row
2. Edit display_name, Save
3. Reload page

**Observation 1 — Save**:
1. `PATCH /services/providers/{id}/models/{model_id}` is recorded

**Observation 2 — Persistence**:
1. After reload, the row reflects the new display_name

---

### TC-HAPPY-007: Trash icon opens confirm modal

**Action**:
1. Click a row's trash icon

**Observation 1 — Modal**:
1. Confirm modal is visible

---

### TC-VALIDATE-001: Save button is disabled with blank name

**Action**:
1. Open Add model drawer
2. Leave name blank

**Observation 1 — Button state**:
1. Save is disabled

---

### TC-VALIDATE-002: Whitespace-only name disables Save

**Action**:
1. Open drawer
2. Type `   ` into name

**Observation 1 — Button state**:
1. Save is disabled

---

### TC-ERROR-001: Duplicate name within provider surfaces an error toast

**Preconditions**:
- A model with name `__e2e__dup` already exists.

**Action**:
1. Open Add model drawer
2. Submit `__e2e__dup`

**Observation 1 — Toast**:
1. Error toast is visible (409 conflict)

**Observation 2 — Drawer persists**:
1. Drawer stays open

---

### TC-ERROR-002: 400 on create keeps drawer open

**Action**:
1. Submit Add model

**Observation 1 — Toast**:
1. Backend `detail` is surfaced

**Observation 2 — Drawer persists**:
1. Drawer stays open with form intact

**API mock**: `POST .../models/create` → 400.

---

### TC-ERROR-003: 401 on create triggers login redirect

**Action**:
1. Submit Add model

**Observation 1 — Toast**:
1. Toast surfaces auth error

**Observation 2 — Next nav**:
1. Subsequent navigation redirects to login

**API mock**: 401.

---

### TC-ERROR-004: 403 on create shows toast

**Action**:
1. Submit Add model

**Observation 1 — Toast**:
1. Toast title matches `Forbidden`

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: 403.

---

### TC-ERROR-005: 500 on create shows toast

**Action**:
1. Submit Add model

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Drawer persists**:
1. Drawer stays open intact

**API mock**: 500.

---

### TC-ERROR-006: 400 on edit keeps drawer open

**Action**:
1. Open edit drawer, modify, Save

**Observation 1 — Toast**:
1. Toast surfaces `detail`

**Observation 2 — Drawer persists**:
1. Drawer stays open with edits

**API mock**: `PATCH .../models/{model_id}` → 400.

---

### TC-ERROR-007: 404 on edit closes drawer and refetches

**Action**:
1. Open edit drawer, Save

**Observation 1 — Drawer + list**:
1. Drawer closes
2. List refetches

**API mock**: 404.

---

### TC-ERROR-008: 409 on edit shows conflict toast

**Action**:
1. Open edit drawer, rename to a duplicate, Save

**Observation 1 — Toast**:
1. Toast surfaces conflict detail

**Observation 2 — Drawer persists**:
1. Drawer stays open

**API mock**: 409.

---

### TC-ERROR-009: 500 on edit preserves edits

**Action**:
1. Open edit drawer, edit, Save

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Drawer persists**:
1. Drawer stays open with edits intact

**API mock**: 500.

---

### TC-ERROR-010: 403 on delete shows toast

**Action**:
1. Click row trash, confirm

**Observation 1 — Toast**:
1. Toast title matches `Forbidden`

**Observation 2 — Row persists**:
1. Row remains

**API mock**: 403.

---

### TC-ERROR-011: 404 on delete refetches list

**Action**:
1. Click row trash, confirm

**Observation 1 — Refetch**:
1. Models list refetches
2. Row disappears after refetch

**API mock**: 404.

---

### TC-ERROR-012: 500 on delete preserves row

**Action**:
1. Click row trash, confirm

**Observation 1 — Toast**:
1. Generic error toast

**Observation 2 — Row + modal**:
1. Row remains
2. Modal stays open

**API mock**: 500.

---

### TC-ERROR-013: Models list 500 surfaces toast

**Action**:
1. Open Models tab

**Observation 1 — Toast**:
1. Error toast is visible

**Observation 2 — Empty + retry**:
1. Empty table with retry affordance

**API mock**: `POST .../providers/{id}/models` → 500.

---

### TC-LOADING-001: Slow create disables button

**Action**:
1. Open Add model drawer
2. Submit with ≥3s slow backend

**Observation 1 — Loading state**:
1. Save button shows loading + `disabled`

---

### TC-EDGE-001: Network failure on create preserves form

**Action**:
1. Submit Add model with route aborted

**Observation 1 — Toast + drawer**:
1. Generic error toast
2. Drawer stays open

---

### TC-EDGE-002: Network failure on edit preserves edits

**Action**:
1. Save edit with route aborted

**Observation 1 — Toast + drawer**:
1. Generic error toast
2. Drawer stays open with edits

---

### TC-EDGE-003: Network failure on delete preserves row

**Action**:
1. Confirm delete with route aborted

**Observation 1 — Toast + row**:
1. Generic error toast
2. Row remains

---

### TC-EDGE-004: Concurrent edit last-write-wins

**Action**:
1. Two admins edit the same model; second saves first, first then saves

**Observation 1 — Last write wins**:
1. Final row value reflects the first admin's save

---

### TC-EDGE-005: Name whitespace trimmed before submit

**Action**:
1. Open Add model with name `  __e2e__model  `
2. Submit

**Observation 1 — Trimmed payload**:
1. Body name equals `__e2e__model`

---

### TC-EDGE-006: Unicode + emoji name round-trips

**Action**:
1. Submit name `__e2e__ 🤖 unicode`

**Observation 1 — Body preserves unicode**:
1. Request body contains the literal unicode string

**Observation 2 — Row renders unicode**:
1. The row displays the emoji + unicode as visible text

---

### TC-EDGE-007: Script tag in name is escaped on render

**Action**:
1. Submit name `<script>alert(1)</script>`

**Observation 1 — Stored verbatim**:
1. Body contains the literal string

**Observation 2 — DOM is safe**:
1. The name renders as text
2. `window.alert` never invoked

---

### TC-EDGE-008: Oversized name handled gracefully

**Action**:
1. Submit name >500 chars

**Observation 1 — Inline or backend error**:
1. Either an inline error appears OR backend 400 toast

---

### TC-EDGE-009: Oversized display_name handled gracefully

**Action**:
1. Submit display_name >500 chars

**Observation 1 — Inline or backend error**:
1. Either an inline error appears OR backend 400 toast

---

### TC-EDGE-010: Oversized description handled gracefully

**Action**:
1. Submit description >2000 chars

**Observation 1 — Accept or truncate**:
1. Either accepted or truncation reported via inline error

---

### TC-EDGE-011: Empty models list shows add CTA

**Preconditions**:
- No models exist for this provider.

**Action**:
1. Open Models tab

**Observation 1 — Empty state**:
1. Empty-state renders with "Add model" CTA

---

### TC-EDGE-012: No-match search shows empty state

**Action**:
1. Type gibberish into the search input

**Observation 1 — Empty state**:
1. `No matches` empty state visible

---

### TC-EDGE-013: Sort by name reorders rows

**Action**:
1. Toggle sort by Name asc/desc

**Observation 1 — Row order**:
1. Rows reorder according to direction

---

### TC-EDGE-014: Kind filter narrows to LLM

**Action**:
1. Filter by Kind = LLM

**Observation 1 — Rows**:
1. Only LLM rows are visible

---

### TC-NAV-001: Member role cannot add model

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Open Models tab

**Observation 1 — Read-only**:
1. Rows are visible
2. "Add model" CTA hidden or disabled

---

### TC-NAV-002: Direct create as member surfaces 403 toast

**Action**:
1. Submit Add model as member

**Observation 1 — Toast**:
1. Toast title equals `Forbidden`

**API**: 403.

---

### TC-NAV-003: Member role cannot edit model

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Click a model row

**Observation 1 — Read-only drawer**:
1. Edit drawer opens read-only

---

### TC-NAV-004: Member cannot delete model

**Preconditions**:
- Authenticated as a member.

**Action**:
1. Inspect a row

**Observation 1 — Trash hidden/disabled**:
1. Trash icon is hidden or disabled

---

### TC-NAV-005: Tab switch updates aria-pressed and URL

**Action**:
1. From Models tab, click API Keys tab

**Observation 1 — Tab state + URL**:
1. API Keys button has `aria-pressed="true"`
2. URL updates accordingly
3. Counts persist; rows refetch

---

### TC-NAV-006: Back after create does not prompt for unsaved changes

**Action**:
1. Create a model
2. Press browser Back

**Observation 1 — No prompt**:
1. No unsaved-changes prompt
2. Navigation completes

---

### TC-A11Y-001: Add model drawer tab order matches visual order

**Action**:
1. Open Add model drawer
2. Tab through fields

**Observation 1 — Tab order**:
1. Focus moves Name → display_name → Kind → Description → Save

---

### TC-A11Y-002: Enter key submits Add model drawer

**Action**:
1. Open drawer, fill valid fields, press Enter

**Observation 1 — Submit**:
1. Exactly one create request fires

---

### TC-A11Y-003: Drawer traps focus and restores on close

**Action**:
1. Open drawer, Tab to wrap, press Escape

**Observation 1 — Focus trap**:
1. Tab cycles within drawer

**Observation 2 — Restore on close**:
1. Focus returns to the trigger

---

### TC-A11Y-004: Inline errors are announced

**Action**:
1. Trigger a required error

**Observation 1 — ARIA**:
1. Inline error has `role="alert"` (or `aria-live`)

---

### TC-A11Y-005: Delete confirm modal is keyboard-operable

**Action**:
1. Click row trash, Tab to Confirm, press Enter

**Observation 1 — Confirmation triggers**:
1. Delete request fires

---

### TC-FULL-001: Lifecycle — create → search → edit display → delete

**Action**:
1. Open Add model drawer
2. Fill name = `__e2e__lifecycle`, kind, optional display_name + description
3. Save
4. Search the new name to narrow the table
5. Click the row and edit display_name
6. Reload
7. Click trash, confirm delete
8. Cleanup in `try/finally`

**Observation 1 — Create**:
1. `POST .../models/create` recorded
2. Success toast visible

**Observation 2 — Search narrows**:
1. Only the new row is visible

**Observation 3 — Edit persists**:
1. `PATCH .../models/{model_id}` body contains new display_name
2. Reload shows the new display_name

**Observation 4 — Delete**:
1. `DELETE .../models/{model_id}` fires
2. Row removed; success toast

---

### TC-FULL-002: Lifecycle extended — create (all fields) → search → edit → reload → delete

**Action**:
1. Create a model with name + display_name + kind + description
2. Search the new name
3. Edit display_name + description, Save
4. Reload
5. Delete
6. Cleanup in `try/finally`

**Observation 1 — Create all fields**:
1. Request body includes all four fields
2. Row shows display_name preferentially

**Observation 2 — Search narrows**:
1. Only the new row visible

**Observation 3 — Edit + reload**:
1. Edit fires PATCH with new fields
2. Reload reflects both edits

**Observation 4 — Delete**:
1. DELETE fires
2. Row removed

---

## Field coverage map (TC-FULL-001 Models)

| Section            | Field         | Selector                                                | Helper                                  | Asserted on reload                         |
| ------------------ | ------------- | ------------------------------------------------------- | --------------------------------------- | ------------------------------------------ |
| Add model drawer   | Name          | `input[name="name"]` (in dialog)                        | `createProviderModelViaUI({ name })`    | row appears                                |
| Add model drawer   | Display name  | `input[name="display_name"]` (in dialog)                | inline fill                             | shown preferentially in row                |
| Add model drawer   | Kind          | `button[id="kind"]` (in dialog)                         | `pickSelectOptionByLabel('LLM')`        | kind badge color asserted indirectly       |
| Add model drawer   | Description   | `textarea[name="description"]` (in dialog)              | inline fill                             | —                                          |
| Edit model drawer  | display_name  | `input[name="display_name"]`                            | inline fill                             | yes                                        |
| Models tab         | Row trash     | per-row `button[aria-label="Delete model"]`             | `deleteProviderModelViaUI`              | row count drops to 0                       |

---

## Deferred (`test.fixme` / `test.skip`)

- `AKR-MASK` (assert one-time reveal of the plaintext secret via `page.waitForResponse` interception) — deferred. The FE never re-renders the secret, so regression is unlikely without explicit UI changes. Backend masking is already covered by pytest under `test-cases/`.
- `AKE-003` (toggle Active off on a key → persists on reload) — relies on the edit drawer exposing the Active checkbox; revisit after the drawer's a11y surface is firmed up.
- `MDE-003` (toggle Active off on a model) — same reason.
- `MDC-005` (admin/owner-only model CRUD; non-owner sees no Add button) — skipped. Needs a non-owner membership seed which CI doesn't provide today.
- `AKE-ROT` (rotate-secret flow) — no UI for rotation; to rotate, user must delete and recreate. Document only.

---

## Safety notes

- **No `is_default=true` writes** — the user's agent saves pull the default key, so flipping it would break unrelated workflows.
- **Models are global** (`core/services/model_provider_service.py:121–124` — no `org_id` column on `ProviderModel`). Every model the test creates is visible to every org. The spec `__e2e__`-prefixes every model name AND deletes in `try/finally`.

---

## Cleanup

`beforeAll` creates a fixture API key via `createApiKeyViaUI` on the first LLM provider in the catalog. `afterAll` deletes it. Every Keys / Models test either mutates the shared fixture and reverts (e.g. AKE-002 leaves the edited description in place because it doesn't break later tests), OR uses a freshly-created throw-away in `try/finally` so it self-cleans.

---

## Mapping: old scenario IDs → new TC IDs

### API Keys

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| AKL-001         | TC-HAPPY-001      | page loads with Keys tab active                                      |
| AKL-002         | TC-HAPPY-002      | keys table renders the documented columns                            |
| AKL-003         | TC-HAPPY-003      | fixture key appears in the list                                      |
| AKL-004         | TC-HAPPY-004      | search filters rows by label                                         |
| AKL-005         | TC-HAPPY-005      | Add API key button opens drawer                                      |
| AKC-001         | TC-HAPPY-006      | valid Create → row + success toast                                   |
| AKE-001         | TC-HAPPY-007      | clicking a row opens the edit drawer                                 |
| AKE-002         | TC-HAPPY-008      | editing description persists on reload                               |
| AKD-001         | TC-HAPPY-009      | row trash icon opens the confirm modal                               |
| AKC-002         | TC-VALIDATE-001   | Create button is disabled with no api_key entered                    |
| AKC-030         | TC-VALIDATE-002   | whitespace-only label disables Create                                |
| AKC-035         | TC-VALIDATE-003   | whitespace-only api_key disables Create                              |
| AKC-003         | TC-ERROR-001      | duplicate label surfaces an error toast                              |
| AKC-011         | TC-ERROR-002      | 400 on create keeps drawer open                                      |
| AKC-012         | TC-ERROR-003      | 401 on create triggers login redirect on next nav                    |
| AKC-013         | TC-ERROR-004      | 403 on create shows toast                                            |
| AKC-014         | TC-ERROR-005      | 500 on create shows toast                                            |
| AKE-011         | TC-ERROR-006      | 400 on edit keeps drawer open                                        |
| AKE-012         | TC-ERROR-007      | 404 on edit closes drawer and refetches                              |
| AKE-013         | TC-ERROR-008      | 409 on edit shows conflict toast                                     |
| AKE-014         | TC-ERROR-009      | 500 on edit preserves edits                                          |
| AKD-011         | TC-ERROR-010      | 403 on delete shows toast                                            |
| AKD-012         | TC-ERROR-011      | 404 on delete refetches list                                         |
| AKD-013         | TC-ERROR-012      | 500 on delete preserves row                                          |
| AKL-013         | TC-ERROR-013      | keys list 500 surfaces toast                                         |
| AKC-021         | TC-LOADING-001    | slow create disables button                                          |
| AKC-020         | TC-EDGE-001       | network failure on create preserves form                             |
| AKE-020         | TC-EDGE-002       | network failure on edit preserves edits                              |
| AKD-020         | TC-EDGE-003       | network failure on delete preserves row                              |
| AKE-021         | TC-EDGE-004       | concurrent edit last-write-wins                                      |
| AKC-031         | TC-EDGE-005       | label whitespace trimmed before submit                               |
| AKC-032         | TC-EDGE-006       | unicode + emoji label round-trips                                    |
| AKC-033         | TC-EDGE-007       | script tag in label is escaped on render                             |
| AKC-034         | TC-EDGE-008       | oversized label handled gracefully                                   |
| AKC-036         | TC-EDGE-009       | api_key whitespace trimmed before submit                             |
| AKC-037         | TC-EDGE-010       | short api_key rejected by backend                                    |
| AKC-038         | TC-EDGE-011       | oversized api_key handled gracefully                                 |
| AKL-014         | TC-EDGE-012       | secret value is masked after create and not in DOM after reload      |
| AKL-010         | TC-NAV-001        | unauthenticated visit redirects to login                             |
| AKL-011         | TC-NAV-002        | expired token redirects to login                                     |
| AKL-012         | TC-NAV-003        | member role cannot add API key                                       |
| AKC-010         | TC-NAV-004        | direct create as member surfaces 403 toast                           |
| AKE-010         | TC-NAV-005        | member role cannot edit API key                                      |
| AKD-010         | TC-NAV-006        | member cannot delete API key                                         |
| AKN-010         | TC-NAV-007        | tab switch updates aria-pressed and URL                              |
| AKN-011         | TC-NAV-008        | back navigation returns to list                                      |
| AKN-012         | TC-NAV-009        | back after edit does not prompt for unsaved changes                  |
| AKC-040         | TC-A11Y-001       | Create drawer tab order matches visual order                         |
| AKC-041         | TC-A11Y-002       | Enter key submits Create drawer                                      |
| AKC-042         | TC-A11Y-003       | drawer traps focus and restores on close                             |
| AKC-043         | TC-A11Y-004       | api_key field uses password input                                    |
| AKE-030         | TC-A11Y-005       | inline errors are announced                                          |
| AKD-030         | TC-A11Y-006       | Delete confirm modal is keyboard-operable                            |
| AKL-015         | TC-EDGE-013       | empty keys list shows add CTA                                        |
| AKL-016         | TC-EDGE-014       | no-match search shows empty state                                    |
| AKL-017         | TC-EDGE-015       | sort by name reorders rows                                           |
| AKL-018         | TC-EDGE-016       | sort by status reorders rows                                         |
| AKK-FULL        | TC-FULL-001       | create → list (masked) → edit description → delete                   |
| AKK-EXT         | TC-FULL-002       | lifecycle: create → search → edit → reload → delete (extended)       |

### Provider Models

| Old scenario ID | New TC ID         | Spec test name                                                       |
| --------------- | ----------------- | -------------------------------------------------------------------- |
| MDL-001         | TC-HAPPY-001      | Models tab activates and the table renders                           |
| MDL-002         | TC-HAPPY-002      | models table renders the documented columns                          |
| MDL-003         | TC-HAPPY-003      | Add Model button opens the drawer                                    |
| MDC-001         | TC-HAPPY-004      | create minimal model (name + kind) succeeds                          |
| MDC-002         | TC-HAPPY-005      | create with all fields persists                                      |
| MDE-002         | TC-HAPPY-006      | editing display_name persists on reload                              |
| MDD-001         | TC-HAPPY-007      | trash icon opens confirm modal                                       |
| MDC-003         | TC-VALIDATE-001   | Save button is disabled with blank name                              |
| MDC-030         | TC-VALIDATE-002   | whitespace-only name disables Save                                   |
| MDC-004         | TC-ERROR-001      | duplicate name within provider surfaces an error toast               |
| MDC-011         | TC-ERROR-002      | 400 on create keeps drawer open                                      |
| MDC-012         | TC-ERROR-003      | 401 on create triggers login redirect                                |
| MDC-013         | TC-ERROR-004      | 403 on create shows toast                                            |
| MDC-014         | TC-ERROR-005      | 500 on create shows toast                                            |
| MDE-011         | TC-ERROR-006      | 400 on edit keeps drawer open                                        |
| MDE-012         | TC-ERROR-007      | 404 on edit closes drawer and refetches                              |
| MDE-013         | TC-ERROR-008      | 409 on edit shows conflict toast                                     |
| MDE-014         | TC-ERROR-009      | 500 on edit preserves edits                                          |
| MDD-011         | TC-ERROR-010      | 403 on delete shows toast                                            |
| MDD-012         | TC-ERROR-011      | 404 on delete refetches list                                         |
| MDD-013         | TC-ERROR-012      | 500 on delete preserves row                                          |
| MDL-013         | TC-ERROR-013      | models list 500 surfaces toast                                       |
| MDC-021         | TC-LOADING-001    | slow create disables button                                          |
| MDC-020         | TC-EDGE-001       | network failure on create preserves form                             |
| MDE-020         | TC-EDGE-002       | network failure on edit preserves edits                              |
| MDD-020         | TC-EDGE-003       | network failure on delete preserves row                              |
| MDE-021         | TC-EDGE-004       | concurrent edit last-write-wins                                      |
| MDC-031         | TC-EDGE-005       | name whitespace trimmed before submit                                |
| MDC-032         | TC-EDGE-006       | unicode + emoji name round-trips                                     |
| MDC-033         | TC-EDGE-007       | script tag in name is escaped on render                              |
| MDC-034         | TC-EDGE-008       | oversized name handled gracefully                                    |
| MDC-035         | TC-EDGE-009       | oversized display_name handled gracefully                            |
| MDC-036         | TC-EDGE-010       | oversized description handled gracefully                             |
| MDL-014         | TC-EDGE-011       | empty models list shows add CTA                                      |
| MDL-015         | TC-EDGE-012       | no-match search shows empty state                                    |
| MDL-016         | TC-EDGE-013       | sort by name reorders rows                                           |
| MDL-017         | TC-EDGE-014       | kind filter narrows to LLM                                           |
| MDL-010         | TC-NAV-001        | member role cannot add model                                         |
| MDC-010         | TC-NAV-002        | direct create as member surfaces 403 toast                           |
| MDE-010         | TC-NAV-003        | member role cannot edit model                                        |
| MDD-010         | TC-NAV-004        | member cannot delete model                                           |
| MDN-010         | TC-NAV-005        | tab switch updates aria-pressed and URL                              |
| MDN-011         | TC-NAV-006        | back after create does not prompt for unsaved changes                |
| MDC-040         | TC-A11Y-001       | Add model drawer tab order matches visual order                      |
| MDC-041         | TC-A11Y-002       | Enter key submits Add model drawer                                   |
| MDC-042         | TC-A11Y-003       | drawer traps focus and restores on close                             |
| MDE-030         | TC-A11Y-004       | inline errors are announced                                          |
| MDD-030         | TC-A11Y-005       | Delete confirm modal is keyboard-operable                            |
| MDM-FULL        | TC-FULL-001       | create → search → edit display → delete                              |
| MDM-EXT         | TC-FULL-002       | lifecycle: create (all fields) → search → edit → reload → delete     |
