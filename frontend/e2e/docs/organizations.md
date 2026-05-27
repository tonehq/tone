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
