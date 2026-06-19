# Feature Doc: Organizations

Feature documentation for the Organizations page at `/organizations`.
Companion to `frontend/e2e/dashboard/organizations.spec.ts`. Each TC ID below
maps to a Playwright `test(...)` name; the legacy scenario IDs
(OL-/OC-/OE-/OD-/OS-/OG-/OR-/ON-) remain in the mapping table for traceability.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/organizations`
- **Main component**: `frontend/src/components/organizations/OrganizationListPage.tsx`
- **Sub-components**:
  - `OrganizationCard.tsx` — single card; clicking opens Edit for admin/owner
  - `OrganizationCardMenu.tsx` — per-card "…" menu with Edit + Delete (Delete owner-only)
  - `OrganizationUpsertModal.tsx` — Create / Edit modal with Name, Description, Website URL, Logo URL
  - `OrganizationDeleteModal.tsx` — Delete confirm with typed-name guard
- **State**: `frontend/src/atoms/OrganizationAtom.tsx` — write atoms for list/create/update/delete
- **API service**: `frontend/src/services/organizationService.ts`
- **Sidebar switcher**: `frontend/src/components/layout/sidebar.tsx:244–339` — aria-label `Switch organization`; switch is a localStorage write + `window.location.reload()`, not an API call
- **Auth required**: yes

---

## User Stories

### US-1: View all my organizations

**As a** logged-in user, **I want to** see every organization I belong to as a card grid at `/organizations`, with role badges + a search box.

### US-2: Create a new organization

**As a** user, **I want to** create a new organization from a modal with a Name field.

### US-3: Edit an organization

**As an** admin / owner of a card, **I want to** edit its Name, Description, Website, and Logo URL.

### US-4: Delete an organization

**As an** owner of a card, **I want to** delete it after typing the org name into a confirm-name guard input.

### US-5: Switch active organization

**As a** multi-org user, **I want to** switch the active org from the sidebar switcher; the page reloads and every subsequent request uses the new tenant header.

---

## UI Elements

| Element                     | Type     | Content / Label                                       | Behavior                                          |
| --------------------------- | -------- | ----------------------------------------------------- | ------------------------------------------------- |
| Page header                 | h1       | Organizations                                         | Static                                            |
| New Organization CTA        | button   | "New Organization"                                    | Opens `OrganizationUpsertModal` (create mode)     |
| Search box                  | input    | Search by name                                        | Filters card grid                                 |
| No-matches state            | div      | "No matches" + Clear button                           | Shows when search returns 0 cards                 |
| Organization card           | card     | Logo + Name + role badge                              | Click opens Edit for admin/owner                  |
| Card menu trigger           | button   | "…" icon                                              | Opens Edit + Delete menu                          |
| Edit menu item              | menu     | "Edit"                                                | Opens Upsert modal in edit mode                   |
| Delete menu item            | menu     | "Delete"                                              | Owner-only; opens Delete modal                    |
| Upsert — Name               | input    | `input[name="name"]` (in dialog)                      | Required                                          |
| Upsert — Description        | textarea | `textarea[name="description"]` (in dialog)            | Optional                                          |
| Upsert — Website URL        | input    | `input[name="website_url"]` (in dialog)               | Optional, URL-validated                           |
| Upsert — Logo URL           | input    | `input[name="logo_url"]` (in dialog)                  | Optional, URL-validated                           |
| Create / Save button        | button   | "Create" / "Save"                                     | Disabled until form valid                         |
| Delete confirm — name guard | input    | type the org name                                     | Delete button disabled until exact match          |
| Delete confirm button       | button   | "Delete"                                              | Disabled until name matches                       |
| Sidebar org switcher        | button   | aria-label "Switch organization"                      | Opens popover with all orgs                       |

---

## Input Specifications

| Field        | Type     | Required | Validation                                  | Exact Error Message              |
| ------------ | -------- | -------- | ------------------------------------------- | -------------------------------- |
| Name         | text     | yes      | non-empty after trim                        | (Create / Save disabled)         |
| Description  | textarea | no       | up to N chars (⚠ unverified)                | n/a                              |
| Website URL  | url      | no       | valid URL when non-empty                    | (⚠ Zod schema in flux)           |
| Logo URL     | url      | no       | valid URL when non-empty                    | n/a                              |

---

## Navigation

| Trigger                                | Destination                                  | Condition                  |
| -------------------------------------- | -------------------------------------------- | -------------------------- |
| Visit `/organizations` (auth'd)        | Renders Organizations page                   | `tone_access_token` set    |
| Visit `/organizations` (no auth)       | `/auth/login?redirect=%2Forganizations`      | Middleware redirect        |
| Sidebar org switch                     | Same URL; `window.location.reload()`         | Client-only                |
| Click `Members` link on card           | `/settings/members`                          | (⚠ unverified, see ON-010) |

---

## API Contracts

| Method | Path                                          | Triggered by               |
| ------ | --------------------------------------------- | -------------------------- |
| POST   | `/organization/get_associated_tenants`        | list load                  |
| POST   | `/organization/create_tenants?name=`          | create modal Submit        |
| GET    | `/organization/details?org_id=`               | Edit modal open            |
| PUT    | `/organization/details?org_id=`               | Edit modal Save            |
| DELETE | `/organization/delete?org_id=`                | Delete confirm             |
| _none_ | n/a                                           | Sidebar switch (localStorage + reload) |

### Error payload shape (all endpoints)

```json
{ "detail": "<string>" }
```

400 example: `{ "detail": "Invalid website URL" }` / `{ "detail": "Invalid name" }`
401 example: `{ "detail": "Could not validate credentials" }`
403 example: `{ "detail": "Forbidden" }` / `{ "detail": "Only owner can delete" }`
404 example: `{ "detail": "Organization not found" }`
409 example: `{ "detail": "Organization name already exists" }`
500 example: `{ "detail": "Internal server error" }`

> Backend contract caveat: the upsert modal posts `website_url` but the backend stores it as `Organization.website` and the GET response key doesn't always match. Asserting `website_url` after a reload fails today; OE-003 / OG-FULL therefore only round-trip the `description` field.

---

## Scenario ID Mapping (old → new)

| Old scenario ID | New TC ID         | Spec test name                                                            |
| --------------- | ----------------- | ------------------------------------------------------------------------- |
| OL-001          | TC-HAPPY-001      | renders the header + "New Organization" CTA                               |
| OL-002          | TC-HAPPY-002      | the card grid lists at least the fixture org                              |
| OL-003          | TC-HAPPY-003      | search filters cards by name                                              |
| OL-004          | TC-HAPPY-004      | empty search shows the No matches state with a Clear button               |
| OC-001          | TC-HAPPY-005      | clicking New Organization opens the upsert modal with empty Name          |
| OC-002          | TC-VALIDATE-001   | Create button is disabled while Name is blank                             |
| OC-003          | TC-HAPPY-006      | valid Create posts the form and the new card appears                     |
| OE-001          | TC-HAPPY-007      | Edit modal hydrates with the existing values                              |
| OE-002          | TC-HAPPY-008      | editing Name persists across a refetch                                    |
| OE-003          | TC-HAPPY-009      | description + website round-trip on reload                                |
| OD-002          | TC-VALIDATE-002   | owner Delete opens the modal; Delete button is disabled until name typed exactly |
| OD-003          | TC-HAPPY-010      | typed-name confirm deletes the org and removes the card                   |
| OG-FULL         | TC-FULL-001       | create → edit name+desc+website → delete                                  |
| OS-001          | TC-HAPPY-011      | the switcher opens a popover listing every org the user belongs to        |
| OS-002          | TC-HAPPY-012      | picking the fixture org reloads with the new tenant (currently `test.fixme`) |
| OL-010          | TC-NAV-001        | unauthenticated visit redirects to login                                  |
| OL-011          | TC-NAV-002        | expired token redirects to login                                          |
| OL-012          | TC-HAPPY-013      | member sees read-only edit modal for fixture org                          |
| OD-010          | TC-HAPPY-014      | member does not see Delete on a card they do not own                      |
| OD-011          | TC-HAPPY-015      | admin cannot delete an org they do not own                                |
| OC-010          | TC-ERROR-001      | create with 400 surfaces error and keeps modal open                       |
| OC-011          | TC-ERROR-002      | duplicate org name surfaces 409 toast                                     |
| OC-012          | TC-ERROR-003      | create 500 surfaces toast and keeps form intact                           |
| OE-010          | TC-ERROR-004      | 400 on save shows toast and keeps modal open                              |
| OE-011          | TC-ERROR-005      | 401 on save shows toast and triggers login redirect                       |
| OE-012          | TC-ERROR-006      | non-admin save shows 403 toast                                            |
| OE-013          | TC-ERROR-007      | 404 on save closes modal and refetches list                               |
| OE-014          | TC-ERROR-008      | 500 on save shows toast and preserves edits                               |
| OD-012          | TC-ERROR-009      | non-owner delete shows 403 toast                                          |
| OD-013          | TC-ERROR-010      | delete on already-deleted org closes modal and refetches                  |
| OD-014          | TC-ERROR-011      | delete 500 shows toast and preserves card                                 |
| OL-013          | TC-ERROR-012      | list 500 surfaces toast and offers retry                                  |
| OC-020          | TC-EDGE-001       | network failure on create preserves form                                  |
| OE-020          | TC-EDGE-002       | network failure on edit preserves edits                                   |
| OE-021          | TC-LOADING-001    | slow save disables button with loading state                              |
| OD-020          | TC-EDGE-003       | network failure on delete preserves card                                  |
| OE-022          | TC-EDGE-004       | concurrent edit last-write-wins refreshes list                            |
| OC-030          | TC-VALIDATE-003   | whitespace-only name disables Create                                      |
| OC-031          | TC-EDGE-005       | whitespace in name is trimmed before submit                               |
| OC-032          | TC-EDGE-006       | unicode + emoji name round-trips                                          |
| OC-033          | TC-EDGE-007       | script tag in name is escaped on render                                   |
| OC-034          | TC-EDGE-008       | name over 500 chars handled gracefully                                    |
| OE-030          | TC-EDGE-009       | description over 2000 chars handled gracefully                            |
| OE-031          | TC-EDGE-010       | javascript: URL rejected safely                                           |
| OE-032          | TC-EDGE-011       | website URL whitespace trimmed before submit                              |
| OE-033          | TC-EDGE-012       | oversized logo URL handled gracefully                                     |
| OC-040          | TC-A11Y-001       | Create modal tab order matches visual order                               |
| OC-041          | TC-A11Y-002       | Enter key submits Create modal                                            |
| OC-042          | TC-A11Y-003       | inline errors are announced by screen readers                             |
| OE-040          | TC-A11Y-004       | Upsert modal traps focus and restores on close                            |
| OD-030          | TC-A11Y-005       | Delete modal is keyboard-operable end to end                              |
| OL-014          | TC-HAPPY-016      | empty list shows create CTA                                               |
| OL-015          | TC-HAPPY-017      | clearing no-match search restores grid                                    |
| OL-016          | TC-HAPPY-018      | sort by name reorders cards                                               |
| OL-017          | TC-HAPPY-019      | sort by created_at reorders cards                                         |
| OR-010          | TC-HAPPY-020      | owner has full edit + delete on own org                                   |
| OR-011          | TC-HAPPY-021      | admin can edit but cannot delete                                          |
| OR-012          | TC-HAPPY-022      | member is restricted to read-only view                                    |
| OR-013          | TC-HAPPY-023      | sole owner cannot leave own org                                           |
| ON-010          | TC-NAV-003        | card members link navigates to /settings/members                          |
| ON-011          | TC-NAV-004        | back after org switch preserves new tenant                                |
| ON-012          | TC-NAV-005        | closing Create modal restores focus to trigger                            |

---

## Test Cases

---

### TC-HAPPY-001: Organizations page renders header + New Organization CTA

**Preconditions**: Signed in.

**Action**:
1. Visit `/organizations`

**Observation 1 — Network call**:
1. Exactly one `POST /organization/get_associated_tenants` is recorded

**Observation 2 — Header + CTA**:
1. The page `h1` reads `Organizations`
2. The `New Organization` button is visible and enabled

---

### TC-HAPPY-002: Card grid lists at least the fixture org

**Preconditions**: `__e2e__org` fixture exists (seeded in `beforeAll`).

**Action**:
1. Visit `/organizations`

**Observation 1 — Card rendered**:
1. A card whose name contains `__e2e__org` is in the DOM

---

### TC-HAPPY-003: Search filters cards by name

**Action**:
1. Visit `/organizations`
2. Type a unique org name into the search box

**Observation 1 — Filtered grid**:
1. Only the card matching that name is visible
2. All other cards are hidden

---

### TC-HAPPY-004: Empty search shows No matches with Clear button

**Action**:
1. Visit `/organizations`
2. Type gibberish (no match) into the search box

**Observation 1 — Empty state**:
1. Text `No matches` is visible
2. A `Clear` button is visible inside the empty state

---

### TC-HAPPY-005: Clicking New Organization opens the upsert modal with empty Name

**Action**:
1. Visit `/organizations`
2. Click `New Organization`

**Observation 1 — Modal opens**:
1. A dialog appears
2. The Name input is in the DOM and its value is empty

---

### TC-HAPPY-006: Valid Create posts the form and the new card appears

**Action**:
1. Open Create modal
2. Type `__e2e__ Org <uuid>` into Name
3. Click `Create`

**Observation 1 — Network**:
1. Exactly one `POST /organization/create_tenants?name=...` is recorded

**Observation 2 — Toast + grid update**:
1. A success toast appears
2. A new card with the entered name is visible in the grid

**Cleanup**: delete the org in `finally`.

---

### TC-HAPPY-007: Edit modal hydrates with existing values

**Preconditions**: Fixture org exists.

**Action**:
1. Visit `/organizations`
2. Click the fixture card menu `…` → `Edit`

**Observation 1 — Hydration**:
1. `GET /organization/details?org_id=...` is recorded
2. The Name input value equals the fixture's current name

---

### TC-HAPPY-008: Editing Name persists across a refetch

**Action**:
1. Open Edit on the fixture org
2. Change Name to `__e2e__ renamed <uuid>`
3. Click Save
4. Reload the page

**Observation 1 — Save fires**:
1. `PUT /organization/details?org_id=...` is recorded
2. Request body contains the new name

**Observation 2 — Card reflects new name**:
1. After save, the card on the grid shows the new name
2. After reload the new name is still present

**Cleanup**: restore the original name in `finally`.

---

### TC-HAPPY-009: Description + Website round-trip on reload

> ⚠ Website round-trip is currently broken at the backend (see "Out of scope"). This case only round-trips `description` reliably; `website` is asserted via the PUT request body only.

**Action**:
1. Open Edit on the fixture org
2. Change Description to `e2e desc <uuid>` and Website URL to `https://e2e.example.com`
3. Click Save
4. Reload

**Observation 1 — Save body**:
1. PUT body contains the new `description` and `website_url`

**Observation 2 — Persistence on reload**:
1. After reload the Edit modal shows the updated `description`
2. ⚠ Website URL persistence is NOT asserted today (backend key mismatch)

---

### TC-HAPPY-010: Typed-name confirm deletes the org and removes the card

**Preconditions**: Throw-away `__e2e__ delete <uuid>` org exists; signed-in user is its owner.

**Action**:
1. Open the card menu → `Delete`
2. Type the exact org name into the guard input
3. Click `Delete`

**Observation 1 — Network**:
1. `DELETE /organization/delete?org_id=...` is recorded

**Observation 2 — Card disappears**:
1. The card is no longer in the grid

---

### TC-HAPPY-011: Switcher popover lists every org the user belongs to

**Action**:
1. Visit `/home` (any authed page)
2. Click the sidebar org switcher trigger

**Observation 1 — Popover content**:
1. A popover opens
2. Every org returned by `POST /organization/get_associated_tenants` is listed inside it

---

### TC-HAPPY-012: Picking fixture org reloads with the new tenant (test.fixme)

> Currently `test.fixme` — see Deferred section for details on the JWT race.

**Action**:
1. Open the switcher and click the fixture org

**Observation 1 — Reload + new tenant**:
1. `window.location.reload()` is invoked
2. After reload, subsequent requests carry the new `tenant_id` header

---

### TC-HAPPY-013: Member sees read-only edit modal for fixture org

**Preconditions**: Logged in as `member` of the fixture org.

**Action**:
1. Open the card menu → `Edit` (or click the card)

**Observation 1 — Read-only**:
1. The Name input is disabled or read-only
2. The Save button is not present or is disabled

---

### TC-HAPPY-014: Member does not see Delete on a card they do not own

**Preconditions**: Logged in as member of the card's org.

**Action**:
1. Open the card menu `…`

**Observation 1 — Delete absent**:
1. The Delete item is not in the menu
2. Only Edit / View is present

---

### TC-HAPPY-015: Admin cannot delete an org they do not own

**Preconditions**: Logged in as admin (non-owner).

**Action**:
1. Open the card menu on a non-owned org

**Observation 1 — Delete absent / disabled**:
1. Delete is either hidden or disabled (per `OrganizationCardMenu` role gate)

---

### TC-HAPPY-016: Empty org list shows Create CTA

**Action**:
1. Mock `POST /organization/get_associated_tenants` to return `[]`
2. Visit `/organizations`

**Observation 1 — Empty state**:
1. An empty-state message is visible
2. A `Create Organization` CTA is visible

---

### TC-HAPPY-017: Clearing no-match search restores grid

**Action**:
1. Visit `/organizations`
2. Type gibberish into search
3. Click the `Clear` button in the empty state

**Observation 1 — Restored**:
1. The search input is empty
2. The full card grid is visible

---

### TC-HAPPY-018: Sort by Name reorders cards

**Preconditions**: Cards sortable.

**Action**:
1. Visit `/organizations`
2. Sort by Name ascending, then descending

**Observation 1 — Ascending**:
1. The first card name is alphabetically smallest

**Observation 2 — Descending**:
1. The first card name is alphabetically largest

---

### TC-HAPPY-019: Sort by created_at reorders cards

**Action**:
1. Visit `/organizations`
2. Sort by `Created at` ascending, then descending

**Observation 1 — Ascending**:
1. Cards are ordered oldest-first

**Observation 2 — Descending**:
1. Cards are ordered newest-first

---

### TC-HAPPY-020: Owner has full edit + delete on own org

**Preconditions**: Owner of the org.

**Action**:
1. Open the card menu and edit a field; save
2. Open the card menu and delete the org

**Observation 1 — Edit completes**:
1. PUT request fires; toast confirms

**Observation 2 — Delete completes**:
1. DELETE request fires; card disappears

---

### TC-HAPPY-021: Admin can edit but cannot delete

**Preconditions**: Logged in as admin (non-owner).

**Action**:
1. Open the card menu

**Observation 1 — Edit available**:
1. Edit opens the upsert modal in edit mode

**Observation 2 — Delete blocked**:
1. Delete option is hidden or disabled

---

### TC-HAPPY-022: Member is restricted to read-only view

**Preconditions**: Logged in as member.

**Action**:
1. Open the card menu

**Observation 1 — Read-only**:
1. The menu shows neither Edit nor Delete
2. Card click opens a read-only modal

---

### TC-HAPPY-023: Sole owner cannot leave own org

**Preconditions**: Sole owner of an org.

**Action**:
1. Open the card menu and look for a Leave control

**Observation 1 — Leave disabled**:
1. The Leave control (if present) is disabled
2. A tooltip explains why (⚠ exact copy unverified)

---

### TC-VALIDATE-001: Create button is disabled while Name is blank

**Action**:
1. Open Create modal
2. Leave Name empty

**Observation 1 — Disabled**:
1. `Create` is disabled
2. Clicking it fires zero `POST /organization/create_tenants` requests

---

### TC-VALIDATE-002: Owner Delete button disabled until name typed exactly

**Preconditions**: Owner of fixture org; throw-away org exists.

**Action**:
1. Open Delete modal on the throw-away org
2. Type a mismatched name into the guard input

**Observation 1 — Delete disabled**:
1. Delete button has `disabled` while the typed name differs from the org name

**Observation 2 — Enables on exact match**:
1. Typing the exact org name enables the Delete button

---

### TC-VALIDATE-003: Whitespace-only Name disables Create

**Action**:
1. Open Create modal
2. Type `   ` (whitespace only) into Name

**Observation 1 — Disabled**:
1. `Create` is disabled

---

### TC-ERROR-001: Create with 400 surfaces error and keeps modal open

**Action**:
1. Open Create modal and submit a valid-looking name

**Observation 1 — Toast**:
1. An error toast appears with text matching the `detail`

**Observation 2 — Modal preserved**:
1. The Create modal is still open with form values intact

**API mock**: `POST /organization/create_tenants` → `400 { "detail": "Invalid name" }`.

---

### TC-ERROR-002: Duplicate org name surfaces 409 toast

**Action**:
1. Submit Create with a name already in use

**Observation 1 — Toast + modal**:
1. Toast text equals `Organization name already exists`
2. Modal stays open

**API mock**: create endpoint → `409 { "detail": "Organization name already exists" }`.

---

### TC-ERROR-003: Create 500 surfaces toast and keeps form intact

**Action**:
1. Submit Create with valid values

**Observation 1 — Toast + modal preserved**:
1. Generic error toast appears
2. Modal still open with form values

**API mock**: create endpoint → `500`.

---

### TC-ERROR-004: 400 on save shows toast and keeps modal open

**Action**:
1. Open Edit modal; change a field; click Save

**Observation 1 — Toast + modal**:
1. Error toast appears
2. Edit modal still open

**API mock**: `PUT /organization/details` → `400 { "detail": "Invalid website URL" }`.

---

### TC-ERROR-005: 401 on save shows toast and triggers login redirect

**Action**:
1. Open Edit modal; click Save

**Observation 1 — Toast**:
1. Toast text equals `Could not validate credentials`

**Observation 2 — Login redirect**:
1. Next navigation to a protected route lands on `/auth/login`

**API mock**: save endpoint → `401`.

---

### TC-ERROR-006: Non-admin save shows 403 toast

**Preconditions**: Logged in as member.

**Action**:
1. Programmatically open the Edit modal; try Save

**Observation 1 — Toast + modal**:
1. Access-denied toast appears
2. Modal stays open

**API mock**: save endpoint → `403 { "detail": "Forbidden" }`.

---

### TC-ERROR-007: 404 on save closes modal and refetches list

**Action**:
1. Open Edit; click Save

**Observation 1 — Toast + refetch**:
1. An empty-state toast appears OR list refetches
2. The Edit modal closes

**Observation 2 — List refetch**:
1. `POST /organization/get_associated_tenants` is fired after the 404

**API mock**: save endpoint → `404`.

---

### TC-ERROR-008: 500 on save shows toast and preserves edits

**Action**:
1. Open Edit; change values; click Save

**Observation 1 — Toast + edits preserved**:
1. Generic error toast appears
2. Modal stays open with edits intact

**API mock**: save endpoint → `500`.

---

### TC-ERROR-009: Non-owner delete shows 403 toast

**Preconditions**: Logged in as non-owner.

**Action**:
1. Attempt delete via direct API call (or open Delete modal if present)

**Observation 1 — Toast + card persists**:
1. Access-denied toast appears
2. The card remains in the grid

**API mock**: delete endpoint → `403`.

---

### TC-ERROR-010: Delete on already-deleted org closes modal and refetches

**Action**:
1. Open Delete modal and confirm

**Observation 1 — Refetch + modal closes**:
1. `POST /organization/get_associated_tenants` is recorded after the 404
2. The Delete modal is closed
3. The card disappears from the grid

**API mock**: delete endpoint → `404 { "detail": "Organization not found" }`.

---

### TC-ERROR-011: Delete 500 shows toast and preserves card

**Action**:
1. Open Delete modal and confirm

**Observation 1 — Toast + card persists**:
1. Toast text equals `Internal server error`
2. Card stays in grid
3. Modal stays open

**API mock**: delete endpoint → `500`.

---

### TC-ERROR-012: List 500 surfaces toast and offers retry

**Action**:
1. Visit `/organizations`

**Observation 1 — Toast + retry**:
1. An error toast appears
2. The grid is empty with a retry affordance

**API mock**: list endpoint → `500`.

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/organizations`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Forganizations`

---

### TC-NAV-002: Expired token redirects to login

**Preconditions**: expired `tone_access_token` cookie.

**Action**:
1. Visit `/organizations`

**Observation 1 — Redirect + cookie cleanup**:
1. URL becomes `/auth/login?redirect=%2Forganizations`
2. The expired cookie is cleared

---

### TC-NAV-003: Card members link navigates to /settings/members

**Action**:
1. Visit `/organizations`
2. Click the Members link on a card (or via menu)

**Observation 1 — Navigation**:
1. URL becomes `/settings/members`
2. The members page is scoped to the clicked org

---

### TC-NAV-004: Back after org switch preserves new tenant

**Preconditions**: User just switched org via sidebar.

**Action**:
1. Navigate to a route
2. Press browser Back

**Observation 1 — Tenant preserved**:
1. Subsequent requests still carry the new tenant header

---

### TC-NAV-005: Closing Create modal restores focus to trigger

**Action**:
1. Click `New Organization`
2. Close the modal via `X`

**Observation 1 — URL + focus**:
1. URL is unchanged
2. Focus returns to the `New Organization` trigger button

---

### TC-LOADING-001: Slow save disables button with loading state

**Action**:
1. Open Edit modal; change a field
2. Click Save against a delayed (3500 ms) backend

**Observation 1 — Loading state**:
1. The Save button shows a loading label / spinner within 100 ms
2. The button has `disabled` throughout the in-flight period

**Observation 2 — Double-submit blocked**:
1. Clicking Save multiple times fires exactly one `PUT /organization/details`

**API mock**: save endpoint → 200 delayed by 3500 ms.

---

### TC-EDGE-001: Network failure on create preserves form

**Action**:
1. Open Create modal; submit valid values

**Observation 1 — Toast + modal preserved**:
1. Error toast appears
2. Modal still open with form values

**API mock**: create endpoint → `route.abort('failed')`.

---

### TC-EDGE-002: Network failure on edit preserves edits

**Action**:
1. Open Edit; change a field; click Save

**Observation 1 — Toast + edits intact**:
1. Error toast appears
2. Modal still open with edits

**API mock**: save endpoint → `route.abort('failed')`.

---

### TC-EDGE-003: Network failure on delete preserves card

**Action**:
1. Open Delete modal; confirm

**Observation 1 — Toast + card persists**:
1. Error toast appears
2. Card remains
3. Modal stays open

**API mock**: delete endpoint → `route.abort('failed')`.

---

### TC-EDGE-004: Concurrent edit last-write-wins refreshes list

**Action**:
1. Open Edit modal on the fixture org
2. Have another tab update the same org
3. Save in the first tab

**Observation 1 — Last write wins**:
1. The first tab's PUT is accepted; backend returns the latest record
2. The list refetches and shows the merged state

---

### TC-EDGE-005: Whitespace in name is trimmed before submit

**Action**:
1. Open Create modal; type `  Acme  ` into Name; submit

**Observation 1 — Trimmed payload**:
1. The `?name=` query param equals `Acme` (no leading/trailing whitespace)

**Observation 2 — Persisted clean**:
1. After reload the card name is `Acme`

---

### TC-EDGE-006: Unicode + emoji name round-trips

**Action**:
1. Open Create modal; type `Acme 🌟 Inc.` into Name; submit

**Observation 1 — Persisted**:
1. The new card renders the unicode + emoji correctly
2. After reload the unicode is still present

---

### TC-EDGE-007: Script tag in name is escaped on render

**Action**:
1. Open Create modal; type `<script>alert(1)</script>` into Name; submit

**Observation 1 — Escaped render**:
1. The card renders the literal `<script>` text
2. `window.alert` is not invoked

---

### TC-EDGE-008: Name over 500 chars handled gracefully

**Action**:
1. Open Create modal; type a 600-char name; submit

**Observation 1 — Outcome**:
1. Request is either accepted or rejected with an inline error; no crash

---

### TC-EDGE-009: Description over 2000 chars handled gracefully

**Action**:
1. Open Edit modal; paste a 2500-char description; Save

**Observation 1 — Outcome**:
1. Save is either accepted or rejected with an inline error; no crash

---

### TC-EDGE-010: javascript: URL rejected safely

**Action**:
1. Open Edit modal; type `javascript:alert(1)` into Website URL; Save

**Observation 1 — Rejection**:
1. Either Zod rejects with an inline error, OR backend returns 400
2. No script executes

---

### TC-EDGE-011: Website URL whitespace trimmed before submit

**Action**:
1. Open Edit modal; type `  https://e2e.example.com  ` into Website URL; Save

**Observation 1 — Trimmed payload**:
1. PUT body `website_url` equals `https://e2e.example.com`

---

### TC-EDGE-012: Oversized logo URL handled gracefully

**Action**:
1. Open Edit modal; paste a very long logo URL; Save

**Observation 1 — Outcome**:
1. Inline error appears OR backend returns 400
2. Modal stays open

---

### TC-A11Y-001: Create modal tab order matches visual order

**Action**:
1. Open Create modal
2. Focus the first input and Tab repeatedly

**Observation 1 — Order**:
1. Focus moves Name → Description → Website → Logo → Create button

---

### TC-A11Y-002: Enter key submits Create modal

**Action**:
1. Open Create modal; fill valid values; press Enter

**Observation 1 — Submit fires**:
1. Exactly one `POST /organization/create_tenants` is recorded

---

### TC-A11Y-003: Inline errors are announced by screen readers

**Action**:
1. Trigger an inline validation error in the Create or Edit modal

**Observation 1 — ARIA**:
1. The inline error element has `role="alert"` or `aria-live="polite"`

---

### TC-A11Y-004: Upsert modal traps focus and restores on close

**Action**:
1. Open the Upsert modal
2. Tab past the last focusable element
3. Press Escape

**Observation 1 — Focus wraps**:
1. Focus wraps back to the first focusable element

**Observation 2 — Escape restores focus**:
1. Modal closes
2. Focus returns to the triggering element

---

### TC-A11Y-005: Delete modal is keyboard-operable end to end

**Action**:
1. Tab to the card menu and open Delete
2. Type the org name into the guard input
3. Tab to the Delete button and press Enter

**Observation 1 — Delete completes via keyboard**:
1. `DELETE /organization/delete?org_id=...` is recorded
2. The card disappears

---

### TC-FULL-001: Create → edit name+desc+website → delete

**Preconditions**: Signed in as owner.

**Action**:
1. Click `New Organization`; type `__e2e__ full <uuid>`; click Create
2. Open the new card's Edit menu; change Name to `__e2e__ renamed`, Description to `e2e desc`, Website URL to `https://e2e.example.com`; click Save
3. Reload
4. Open the new card's Delete; type the exact name; click Delete

**Observation 1 — Create**:
1. `POST /organization/create_tenants?name=...` is recorded
2. The new card appears in the grid

**Observation 2 — Edit**:
1. `PUT /organization/details?org_id=...` is recorded
2. PUT body contains the new name, description, and website_url

**Observation 3 — Reload persistence**:
1. The new name persists after reload
2. The new description persists after reload
3. ⚠ Website URL persistence is NOT asserted today (backend key mismatch)

**Observation 4 — Delete**:
1. `DELETE /organization/delete?org_id=...` is recorded
2. The card disappears from the grid

**Cleanup**: `try/finally` ensures the throw-away org is deleted.

---

## Coverage map (what `TC-FULL-001` transitively exercises)

| Scenario          | Covered by TC-FULL-001? | Notes                                  |
| ----------------- | ----------------------- | -------------------------------------- |
| TC-HAPPY-006 (OC-003) | yes                 | new org is created                     |
| TC-HAPPY-007 (OE-001) | yes                 | edit modal is opened                   |
| TC-HAPPY-008 (OE-002) | yes                 | Name change asserted on reload         |
| TC-HAPPY-009 (OE-003) | yes                 | Description asserted on reload         |
| TC-HAPPY-010 (OD-003) | yes                 | org is deleted in `try/finally`        |

---

## Deferred (`test.skip` / `test.fixme`)

- **OE-004** (invalid Website URL → inline error) — `test.fixme`; modal's validation surface depends on Zod schema finalisation and changes often.
- **OD-001** (Delete option hidden on cards where role is not Owner) — skipped. Needs a non-owner membership seed which CI does not provide today.
- **OS-002** (org switch round-trip) — `test.fixme`. Sidebar switch is a localStorage swap + `window.location.reload()` (`components/layout/sidebar.tsx:288–297`), but the JWT in cookies still encodes the old `org_id`. Backend middleware reconciles this only on subsequent requests, racing with Playwright's reload wait. Re-enable once the switch flow calls `/auth/switch_organization` so the test gets a refreshed JWT in the same step.
- **Website URL round-trip** — the upsert modal posts `website_url` but the backend stores it as `Organization.website` and the GET response key doesn't always match. OE-003 / TC-FULL-001 therefore only round-trip the `description` field. Track a backend follow-up to align the contract before adding a website assertion back.

## Out of scope

- Billing tier / quota assertions — depend on subscription data that varies per env.
- Logo-upload via file picker (modal accepts a URL today; in-modal upload is a separate feature).
- Multi-user invite-accept-handoff flows (need a second authenticated context).

## Cleanup

`beforeAll` creates an `__e2e__org` throw-away org via the UI. `afterAll`
deletes it. Every mutation test either reverts the throw-away org back to its
baseline name/description/etc., OR uses a freshly-created throw-away org inside
`try/finally` so it self-cleans.

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-VALIDATE-*` test case above)

- [x] Network failure on create — see TC-EDGE-001
- [x] Network failure on edit — see TC-EDGE-002
- [x] Network failure on delete — see TC-EDGE-003
- [x] Concurrent edit — see TC-EDGE-004
- [x] Whitespace in name — see TC-EDGE-005
- [x] Unicode + emoji name — see TC-EDGE-006
- [x] Script tag in name — see TC-EDGE-007
- [x] Oversized name — see TC-EDGE-008
- [x] Oversized description — see TC-EDGE-009
- [x] javascript: URL — see TC-EDGE-010
- [x] Website URL whitespace — see TC-EDGE-011
- [x] Oversized logo URL — see TC-EDGE-012

---

## Business Rules

- Only owners see the Delete option in the card menu.
- Delete requires typing the org name verbatim into the guard input before the Delete button enables.
- Sidebar org switch is a client-only localStorage write + `window.location.reload()`; no `/auth/switch_organization` API call today.
- Last-owner protection: sole owner cannot leave the org.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Create modal tab order matches visual order — see TC-A11Y-001
- [x] Enter submits Create modal — see TC-A11Y-002
- [x] Inline errors are announced — see TC-A11Y-003
- [x] Upsert modal traps focus and restores on close — see TC-A11Y-004
- [x] Delete modal is keyboard-operable end to end — see TC-A11Y-005
