# Organizations (E2E scenarios)

> Companion to `frontend/e2e/dashboard/organizations.spec.ts`. Each scenario
> ID below maps to a Playwright `test(...)` name so a failing run can be
> triaged directly back to a scenario.

## User stories

- As a logged-in user, I can see every organization I belong to as a card
  grid at `/organizations`, with role badges + a search box.
- As a user, I can create a new organization from a modal with a Name field.
- As an admin / owner of a card, I can edit its Name, Description, Website,
  and Logo URL.
- As an owner of a card, I can delete it after typing the org name into a
  confirm-name guard input.
- As a multi-org user, I can switch the active org from the sidebar
  switcher; the page reloads and every subsequent request uses the new
  tenant header.

## Routes

| Route | Component |
|---|---|
| `/organizations` | `frontend/src/components/organizations/OrganizationListPage.tsx` |

## Key files

- `OrganizationListPage.tsx` — list page with stats, search, card grid.
- `OrganizationCard.tsx` — single card; clicking the card opens Edit for admin/owner.
- `OrganizationCardMenu.tsx` — per-card "…" menu with Edit + Delete (Delete owner-only).
- `OrganizationUpsertModal.tsx` — Create / Edit modal with Name, Description, Website URL, Logo URL.
- `OrganizationDeleteModal.tsx` — Delete confirm with typed-name guard.
- `frontend/src/atoms/OrganizationAtom.tsx` — write atoms for list/create/update/delete.
- `frontend/src/services/organizationService.ts` — axios calls.
- `frontend/src/components/layout/sidebar.tsx:244–339` — the sidebar switcher (aria-label `Switch organization`); switch is a localStorage write + `window.location.reload()`, not an API call.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| POST | `/organization/get_associated_tenants` | list load |
| POST | `/organization/create_tenants?name=` | create modal Submit |
| GET | `/organization/details?org_id=` | Edit modal open |
| PUT | `/organization/details?org_id=` | Edit modal Save |
| DELETE | `/organization/delete?org_id=` | Delete confirm |
| _none_ | n/a | Sidebar switch — client-only localStorage + reload |

## Scenarios — Organizations (OL-/OC-/OE-/OS-/OD-/OG-)

### List + rendering

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OL-001 | Visit `/organizations` | Header + "New Organization" CTA visible | `renders the header + "New Organization" CTA` |
| OL-002 | Card grid populated | At least the fixture `__e2e__org` is visible | `the card grid lists at least the fixture org` |
| OL-003 | Search filters | Typing a unique name hides everything except that card | `search filters cards by name` |
| OL-004 | No-matches state | Searching gibberish surfaces a "No matches" empty state | `empty search shows the No matches state with a Clear button` |

### Create modal

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OC-001 | Click New Organization | Modal opens with empty Name | `clicking New Organization opens the upsert modal with empty Name` |
| OC-002 | Empty Name | Create button is disabled | `Create button is disabled while Name is blank` |
| OC-003 | Valid create | Toast + new card appears | `valid Create posts the form and the new card appears` |

### Edit modal

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OE-001 | Open Edit on the fixture org | Modal hydrates with the existing Name | `Edit modal hydrates with the existing values` |
| OE-002 | Edit Name + Save | Card re-renders; reload still shows the new name; restore at end | `editing Name persists across a refetch` |
| OE-003 | Edit Description + Website + Save | Both round-trip on reload | `description + website round-trip on reload` |

### Delete modal

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OD-002 | Owner Delete | Modal opens; Delete stays disabled until the name is typed exactly | `owner Delete opens the modal; Delete button is disabled until the name is typed exactly` |
| OD-003 | Typed-name confirm | Card disappears from the grid | `typed-name confirm deletes the org and removes the card` |

### Comprehensive flow

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OG-FULL | Create → edit name+desc+website → delete | Every persisted value round-trips through a reload | `create → edit name+desc+website → delete` |

OG-FULL fills every writable Upsert-modal field:

| Section | Field | Selector | Helper | Asserted on reload |
|---|---|---|---|---|
| Upsert modal | Name | `input[name="name"]` (in dialog) | `createOrganizationViaUI({ name })` then inline fill | yes |
| Upsert modal | Description | `textarea[name="description"]` (in dialog) | inline fill | yes |
| Upsert modal | Website URL | `input[name="website_url"]` (in dialog) | inline fill | yes |
| Upsert modal | Logo URL | `input[name="logo_url"]` (in dialog) | not covered here — modal accepts URLs but the test focuses on the round-trippable trio above | — |

### Sidebar switch (runs last in the file)

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OS-001 | Open switcher | Popover lists every org the user belongs to | `the switcher opens a popover listing every org the user belongs to` |
| OS-002 | Pick fixture org → switch back | After the picked-org reload, the new name is active; the test then switches back to "My Space" so the worker ends in a clean state | `picking the fixture org reloads with the new tenant` (currently `test.fixme` — see "OS-002 deferred" below) |

### OS- ordering constraint

`OS-002` triggers `window.location.reload()`. The spec runs every OS- test at the very end of the file and finishes by switching back to **My Space**, so the worker session is in a known state for any subsequent file (and the `afterAll` deletion of the fixture org runs against the right tenant).

## Coverage map (what `OG-FULL` transitively exercises)

| Scenario | Covered by OG-FULL? | Notes |
|---|---|---|
| OC-003 | yes | new org is created |
| OE-001 | yes | edit modal is opened |
| OE-002 | yes | Name change asserted on reload |
| OE-003 | yes | Description + Website asserted on reload |
| OD-003 | yes | the org is deleted in `try/finally` |

## Deferred (`test.skip` / `test.fixme`)

- `OE-004` (invalid Website URL → inline error) — `test.fixme`; the modal's validation surface depends on Zod schema finalisation and changes too often to lock in here.
- `OD-001` (Delete option hidden on cards where role is not Owner) — skipped. Needs a non-owner membership seed which CI does not provide today.
- `OS-002` (org switch round-trip) — `test.fixme`. The sidebar switch is currently a localStorage swap + `window.location.reload()` (`components/layout/sidebar.tsx:288–297`), but the JWT in cookies still encodes the old `org_id`. The backend middleware reconciles this only on subsequent requests, which races with Playwright's reload wait and leaves the worker session unhealthy. Re-enable once the switch flow calls `/auth/switch_organization` so the test gets a refreshed JWT in the same step.
- **Website URL round-trip** — the upsert modal posts `website_url` but the backend stores it as `Organization.website` and the GET response key doesn't always match. Asserting `website_url` after a reload fails. OE-003 / OG-FULL therefore only round-trip the `description` field. Track a backend follow-up to align the contract before adding a website assertion back.

## Out of scope

- Billing tier / quota assertions — depend on subscription data that varies per env.
- Logo-upload via file picker (modal accepts a URL today; in-modal upload is a separate feature).
- Multi-user invite-accept-handoff flows (need a second authenticated context).

## Cleanup

`beforeAll` creates an `__e2e__org` throw-away org via the UI. `afterAll`
deletes it. Every mutation test either:
- reverts the throw-away org back to its baseline name/description/etc., OR
- uses a freshly-created throw-away org inside `try/finally` so it self-cleans.

---

## Gap-filling scenarios

> These rows extend the tables above. They follow the existing prefix
> convention; new IDs are appended after the highest pre-existing number per
> family (OL-004 → OL-010+, OC-003 → OC-010+, OE-003 → OE-010+, OD-003 → OD-010+,
> OS-002 → OS-010+, OG-FULL retained). No existing rows are renumbered.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OL-010 | Visit `/organizations` without auth | Redirects to `/auth/login?redirect=%2Forganizations` | `unauthenticated visit redirects to login` |
| OL-011 | Visit `/organizations` with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| OL-012 | Member (non-owner) opens fixture org card | Edit modal opens read-only / write controls limited per role | `member sees read-only edit modal for fixture org` |
| OD-010 | Member clicks card menu `…` on a card they don't own | Delete option hidden (owner-only); only Edit/View visible | `member does not see Delete on a card they do not own` |
| OD-011 | Admin (non-owner) clicks Delete | Action denied or hidden per `OrganizationCardMenu` role gate | `admin cannot delete an org they do not own` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OC-010 | `POST /organization/create_tenants` returns 400 invalid name | Inline error or toast; modal stays open with form intact | `create with 400 surfaces error and keeps modal open` |
| OC-011 | `POST /organization/create_tenants` returns 409 duplicate name | Error toast; modal stays open; user can edit Name | `duplicate org name surfaces 409 toast` |
| OC-012 | `POST /organization/create_tenants` returns 500 | Generic error toast; modal stays open with form intact | `create 500 surfaces toast and keeps form intact` |
| OE-010 | `PUT /organization/details` returns 400 invalid website URL | Inline error or toast; modal stays open | `400 on save shows toast and keeps modal open` |
| OE-011 | `PUT /organization/details` returns 401 mid-flow | Toast `Could not validate credentials`; next navigation hits login redirect | `401 on save shows toast and triggers login redirect` |
| OE-012 | `PUT /organization/details` returns 403 (member, not admin/owner) | Access denied toast; modal stays open | `non-admin save shows 403 toast` |
| OE-013 | `PUT /organization/details` returns 404 (org deleted by another session) | Empty state toast or redirect to list; the modal closes | `404 on save closes modal and refetches list` |
| OE-014 | `PUT /organization/details` returns 500 | Generic error toast; modal stays open with edits intact | `500 on save shows toast and preserves edits` |
| OD-012 | `DELETE /organization/delete` returns 403 (non-owner) | Access denied toast; card stays in grid | `non-owner delete shows 403 toast` |
| OD-013 | `DELETE /organization/delete` returns 404 (already gone) | Toast + card disappears from grid after refetch | `delete on already-deleted org closes modal and refetches` |
| OD-014 | `DELETE /organization/delete` returns 500 | Toast `Internal server error`; card remains; modal stays open | `delete 500 shows toast and preserves card` |
| OL-013 | `POST /organization/get_associated_tenants` returns 500 | Error toast; empty grid with retry affordance | `list 500 surfaces toast and offers retry` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OC-020 | Network failure on create (`route.abort('failed')`) | Error toast; modal stays open with entered values preserved | `network failure on create preserves form` |
| OE-020 | Network failure mid-save | Error toast; modal stays open with edits intact | `network failure on edit preserves edits` |
| OE-021 | Slow `PUT /organization/details` (>3s) | Save button shows loading + `disabled`; no double-submit | `slow save disables button with loading state` |
| OD-020 | Network failure on delete | Error toast; card remains; modal stays open | `network failure on delete preserves card` |
| OE-022 | Concurrent edit: another tab updates the org while modal is open | On Save, backend returns latest record (last-write-wins); list refetches | `concurrent edit last-write-wins refreshes list` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OC-030 | Name is whitespace only | Submit disabled (trim treats as empty) | `whitespace-only name disables Create` |
| OC-031 | Leading/trailing whitespace in Name | Trimmed before submit; reload shows trimmed name | `whitespace in name is trimmed before submit` |
| OC-032 | Name with emoji + unicode (e.g. `Acme 🌟 Inc.`) | Accepted; card renders unicode; reload persists | `unicode + emoji name round-trips` |
| OC-033 | Name containing `<script>alert(1)</script>` | Stored verbatim; rendered as text (no XSS) | `script tag in name is escaped on render` |
| OC-034 | Name >500 chars | Either accepted or truncated with inline error | `name over 500 chars handled gracefully` |
| OE-030 | Description >2000 chars | Accepted or truncated with inline error | `description over 2000 chars handled gracefully` |
| OE-031 | Website URL with `javascript:` scheme | Either Zod rejects, OR backend rejects with 400 — never executed | `javascript: URL rejected safely` |
| OE-032 | Website URL with leading/trailing whitespace | Trimmed before submit | `website URL whitespace trimmed before submit` |
| OE-033 | Logo URL exceeding allowed length | Inline error or backend 400; modal stays open | `oversized logo URL handled gracefully` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OC-040 | Tab through Create modal | Order: Name → Description → Website → Logo → Create button | `Create modal tab order matches visual order` |
| OC-041 | Submit Create modal via Enter | Triggers Create if valid | `Enter key submits Create modal` |
| OC-042 | Inline form errors have `role="alert"` | Screen reader announces validation | `inline errors are announced by screen readers` |
| OE-040 | Upsert modal traps focus | Tab from last field wraps to first; Escape closes and restores focus to triggering element | `Upsert modal traps focus and restores on close` |
| OD-030 | Delete modal traps focus and confirms keyboard-only | Type org name → Tab → press Enter to confirm | `Delete modal is keyboard-operable end to end` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OL-014 | Empty org list (user belongs to no orgs) | Empty state with `Create Organization` CTA | `empty list shows create CTA` |
| OL-015 | Search with no matches → click `Clear` | Resets search; full grid restored | `clearing no-match search restores grid` |
| OL-016 | Sort cards by Name asc/desc (if sortable) | Cards reorder; first card name matches expected | `sort by name reorders cards` |
| OL-017 | Sort cards by `Created at` | Cards reorder oldest-first / newest-first | `sort by created_at reorders cards` |

### Role-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| OR-010 | Owner can Edit + Delete own org | All actions enabled and complete successfully | `owner has full edit + delete on own org` |
| OR-011 | Admin can Edit but NOT Delete | Edit succeeds; Delete option hidden/disabled | `admin can edit but cannot delete` |
| OR-012 | Member can view; cannot Edit nor Delete | Card opens in read-only mode; menu shows neither Edit nor Delete | `member is restricted to read-only view` |
| OR-013 | Sole owner cannot leave the org | Leave control disabled with explanatory tooltip | `sole owner cannot leave own org` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| ON-010 | Click `Members` link on a card (or via menu) | Navigates to `/settings/members` scoped to that org | `card members link navigates to /settings/members` |
| ON-011 | Browser Back after switching org via sidebar | Returns to previous route under the new tenant | `back after org switch preserves new tenant` |
| ON-012 | Open Create modal, close via X | Modal closes, URL unchanged, focus restored | `closing Create modal restores focus to trigger` |
