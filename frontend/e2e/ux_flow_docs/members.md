# Feature Doc: Members + Invitations

Feature documentation for the Members + Invitations area at `/members`.
Companion to `frontend/e2e/dashboard/members.spec.ts`. Each test case ID below
maps to a Playwright `test(...)` name; the legacy scenario IDs (ML-/MI-/MR-/MD-/INV-/MM-)
remain in the mapping table for traceability.

> **Format rule (mandatory):** every test case below is one **Action** (steps the
> user performs) followed by multiple **Observations** (each a set of verification
> steps). See [`_template.md`](_template.md) for the canonical shape and ID prefixes.

---

## Page

- **Route**: `/members`
- **Main component**: `frontend/src/components/settings/Members.tsx`
- **Sub-components**:
  - `frontend/src/components/settings/MembersTable.tsx` — active-member rows with role dropdown + Delete icon + last-owner lock
  - `frontend/src/components/settings/InvitationsTable.tsx` — pending invite rows with Cancel + Resend icons
  - `frontend/src/components/settings/InviteMemberModal.tsx` — modal with Name, Email, Role (Admin / Member / Viewer; no Owner)
- **State**: `frontend/src/atoms/SettingsAtom.tsx` — `membersAtom`, `invitationsAtom`, write atoms
- **API service**: `frontend/src/services/userService.ts`
- **Auth required**: yes

---

## User Stories

### US-1: Invite a new member by name + email + role

**As an** org owner / admin, **I want to** invite a new member by name + email + role.

### US-2: See active members and pending invitations

**As a** member, **I want to** see the list of active members and pending invitations in two separate tabs on `/members`.

### US-3: Cancel or resend pending invitations

**As an** owner / admin, **I want to** cancel a pending invitation or resend it.

### US-4: Last-owner protection

**As a** user, **I want** the system to prevent demoting or removing the last owner — the role dropdown and Delete button on that row are locked.

---

## UI Elements

| Element              | Type    | Content / Label                                    | Behavior                                 |
| -------------------- | ------- | -------------------------------------------------- | ---------------------------------------- |
| Page header          | h1      | Members                                            | Static                                   |
| Members tab          | tab     | "Members"                                          | Switches to active-members table         |
| Invitations tab      | tab     | "Invitations"                                      | Switches to pending-invitations table    |
| Invite Member CTA    | button  | "Invite Member"                                    | Opens `InviteMemberModal`                |
| Search input         | input   | Search by name / email                             | Filters table                            |
| Role filter          | select  | All / Owner / Admin / Member / Viewer              | Filters Members tab                      |
| Members table        | table   | Cols: Name, Role, Status                           | Row count ≥ 1 (signed-in user always)    |
| Invitations table    | table   | Cols: Email, Role, Status                          | Empty state: "No pending invitations"    |
| Role dropdown (row)  | select  | per-member role                                    | Disabled on last-owner row               |
| Delete icon (row)    | button  | Trash icon                                         | Disabled / hidden on last-owner row      |
| Cancel invite icon   | button  | aria-label "Cancel invitation"                     | Removes invitation                       |
| Resend invite icon   | button  | aria-label "Resend invitation"                     | Re-sends invitation email                |
| Invite modal — Name  | input   | `input[name="name"]` (inside dialog)               | Required                                 |
| Invite modal — Email | input   | `input[name="email"]` (inside dialog)              | Required, email-validated                |
| Invite modal — Role  | select  | `button[id="invite-role"]` (Admin / Member / Viewer; no Owner) | Required                       |
| Send Invite button   | button  | "Send Invite"                                      | Disabled until form valid                |

---

## Input Specifications

| Field                  | Type   | Required | Validation                                    | Exact Error Message              |
| ---------------------- | ------ | -------- | --------------------------------------------- | -------------------------------- |
| Invite — Name          | text   | yes      | non-empty after trim                          | (Send Invite disabled)           |
| Invite — Email         | email  | yes      | non-empty, valid email shape                  | (Send Invite disabled)           |
| Invite — Role          | enum   | yes      | one of `admin` / `member` / `viewer`          | n/a                              |

---

## Navigation

| Trigger                          | Destination                                       | Condition                  |
| -------------------------------- | ------------------------------------------------- | -------------------------- |
| Visit `/members` (auth'd)        | Renders Members page                              | `tone_access_token` set    |
| Visit `/members` (no auth)       | `/auth/login?redirect=%2Fmembers`                 | Middleware redirect        |
| Click tab `Members` / `Invitations` | Same URL with `?tab=` updated                  | Always                     |

---

## API Contracts

| Method | Path                                                   | Triggered by                  |
| ------ | ------------------------------------------------------ | ----------------------------- |
| POST   | `/user/get_all_users_for_organization`                 | Members tab load              |
| POST   | `/user/get_all_invited_users_for_organization`         | Invitations tab load          |
| POST   | `/organization/invite_user_to_organization`            | Invite modal Send             |
| POST   | `/organization/update_member_role?member_id=&role=`    | per-row role change           |
| DELETE | `/organization/remove_user_from_organization?user_id=` | per-row Delete                |
| DELETE | `/organization/cancel_invitation?invite_id=`           | Cancel invitation icon        |
| POST   | `/organization/resend_invitation?invite_id=`           | Resend invitation icon        |

### Error payload shape (all endpoints)

```json
{ "detail": "<string>" }
```

400 example: `{ "detail": "Invalid email" }`
401 example: `{ "detail": "Could not validate credentials" }`
403 example: `{ "detail": "Forbidden" }` / `{ "detail": "Cannot demote the last owner" }` / `{ "detail": "Cannot remove the last owner" }`
404 example: `{ "detail": "Not found" }`
409 example: `{ "detail": "Email already invited" }` / `{ "detail": "Already a member" }`
429 example: `{ "detail": "Too many resend attempts" }`
500 example: `{ "detail": "Internal server error" }`

---

## Scenario ID Mapping (old → new)

| Old scenario ID | New TC ID           | Spec test name                                                                |
| --------------- | ------------------- | ----------------------------------------------------------------------------- |
| ML-001          | TC-HAPPY-001        | renders the header, both tabs, and Invite Member CTA                          |
| ML-002          | TC-HAPPY-002        | Members tab shows the expected columns                                        |
| ML-003          | TC-HAPPY-003        | Members tab lists at least one row (the logged-in user)                       |
| ML-004          | TC-HAPPY-004        | search input is interactive                                                   |
| ML-005          | TC-HAPPY-005        | role filter dropdown opens with the documented options                        |
| ML-006          | TC-HAPPY-006        | Invitations tab renders its own column headers                                |
| MI-001          | TC-HAPPY-007        | clicking Invite Member opens the modal with all three fields                  |
| MI-002          | TC-VALIDATE-001     | Send Invite is disabled while the form is invalid                             |
| MI-003          | TC-VALIDATE-002     | invalid email keeps Send Invite disabled                                      |
| MI-004          | TC-HAPPY-008        | valid invite creates a new row + success toast                                |
| MI-005          | TC-ERROR-001        | inviting the same email twice surfaces an error toast                         |
| INV-001         | TC-HAPPY-009        | cancelling a pending invitation removes the row                               |
| INV-002         | TC-HAPPY-010        | resending a pending invitation surfaces a toast                               |
| MR-001          | TC-HAPPY-011        | the signed-in owner role dropdown is locked or read-only                      |
| MD-001          | TC-HAPPY-012        | the signed-in owner Delete button is locked or omitted                        |
| MM-FULL         | TC-FULL-001         | invite → assert row → resend → cancel → assert gone                           |
| ML-010          | TC-NAV-001          | unauthenticated visit redirects to login                                      |
| ML-011          | TC-NAV-002          | expired token redirects to login                                              |
| MI-010          | TC-HAPPY-013        | member role cannot see Invite CTA                                             |
| MR-010          | TC-HAPPY-014        | member cannot mutate other roles                                              |
| MD-010          | TC-HAPPY-015        | member cannot delete others                                                   |
| MI-011          | TC-ERROR-002        | direct invite call as member surfaces 403 toast                               |
| MI-020          | TC-ERROR-003        | 400 invalid email keeps modal open with toast                                 |
| MI-021          | TC-ERROR-004        | 401 on invite triggers login redirect on next nav                             |
| MI-022          | TC-ERROR-005        | 403 on invite shows toast                                                     |
| MI-023          | TC-ERROR-006        | 409 duplicate email surfaces toast                                            |
| MI-024          | TC-ERROR-007        | 500 on invite shows toast and preserves form                                  |
| MR-020          | TC-ERROR-008        | last-owner demotion 403 reverts dropdown                                      |
| MR-021          | TC-ERROR-009        | 500 on role change reverts dropdown                                           |
| MD-020          | TC-ERROR-010        | last-owner delete 403 shows toast                                             |
| MD-021          | TC-ERROR-011        | 404 on delete refetches list                                                  |
| MD-022          | TC-ERROR-012        | 500 on delete shows toast and preserves row                                   |
| INV-010         | TC-ERROR-013        | 404 on cancel refetches invitations                                           |
| INV-011         | TC-ERROR-014        | 500 on cancel shows toast                                                     |
| INV-012         | TC-ERROR-015        | 429 on resend surfaces rate-limit toast                                       |
| INV-013         | TC-ERROR-016        | 500 on resend shows toast                                                     |
| ML-020          | TC-ERROR-017        | members list 500 surfaces toast                                               |
| ML-021          | TC-ERROR-018        | invitations list 500 surfaces toast                                           |
| MI-030          | TC-EDGE-001         | network failure on invite preserves form                                      |
| MI-031          | TC-LOADING-001      | slow invite disables button with loading state                                |
| MR-030          | TC-EDGE-002         | network failure on role change reverts dropdown                               |
| MD-030          | TC-EDGE-003         | network failure on delete preserves row                                       |
| INV-020         | TC-EDGE-004         | concurrent cancel handled gracefully                                          |
| MI-040          | TC-EDGE-005         | email whitespace trimmed before invite                                        |
| MI-041          | TC-EDGE-006         | email casing handled consistently                                             |
| MI-042          | TC-VALIDATE-003     | whitespace-only name disables Send Invite                                     |
| MI-043          | TC-EDGE-007         | unicode + emoji name round-trips                                              |
| MI-044          | TC-EDGE-008         | script tag in name is escaped on render                                       |
| MI-045          | TC-EDGE-009         | oversized name handled gracefully                                             |
| MI-046          | TC-VALIDATE-004     | invalid email formats fail validation                                         |
| MI-047          | TC-EDGE-010         | max-length email accepted                                                     |
| MI-050          | TC-A11Y-001         | Invite modal tab order matches visual order                                   |
| MI-051          | TC-A11Y-002         | Enter key submits Invite modal                                                |
| MI-052          | TC-A11Y-003         | Invite modal traps focus and restores on close                                |
| MI-053          | TC-A11Y-004         | inline errors are announced                                                   |
| MR-040          | TC-A11Y-005         | role dropdown is keyboard-operable                                            |
| MD-040          | TC-A11Y-006         | Delete confirm modal is keyboard-operable                                     |
| ML-022          | TC-HAPPY-016        | empty members list shows invite CTA                                           |
| ML-023          | TC-HAPPY-017        | empty invitations tab shows empty state                                       |
| ML-024          | TC-HAPPY-018        | no-match search shows empty state                                             |
| ML-025          | TC-EDGE-011         | members pagination boundary disables prev/next                                |
| ML-026          | TC-HAPPY-019        | sort by name reorders rows                                                    |
| ML-027          | TC-HAPPY-020        | sort by role reorders rows                                                    |
| ML-028          | TC-HAPPY-021        | role filter narrows table to admins                                           |
| MR-011          | TC-HAPPY-022        | owner has full member CRUD                                                    |
| MR-012          | TC-HAPPY-023        | admin cannot change owner roles                                               |
| MR-013          | TC-HAPPY-024        | last-owner row is locked                                                      |
| MD-011          | TC-HAPPY-025        | owner self-delete with other owners redirects to /organizations               |
| MD-012          | TC-HAPPY-026        | sole owner self-delete is blocked                                             |
| MN-010          | TC-NAV-003          | invitation email link has mailto attribute                                    |
| MN-011          | TC-NAV-004          | back after closing modal is a no-op for URL                                   |
| MN-012          | TC-NAV-005          | tab switch updates query param and preserves counts                           |
| MM-EXT          | TC-FULL-002         | lifecycle: invite (admin) → resend → role change → cancel                     |

---

## Test Cases

> Every test case is **one Action + multiple Observations**. Each Action is a numbered
> list of steps. Each Observation is a numbered list of verification steps.

---

### TC-HAPPY-001: Members page renders header, tabs, and Invite CTA

**Preconditions**:
- Signed in as owner; `tone_access_token` cookie set

**Action**:
1. Visit `/members`

**Observation 1 — Header + chrome**:
1. The page `h1` "Members" is visible
2. Both `Members` and `Invitations` tabs are in the DOM

**Observation 2 — Invite affordance**:
1. The `Invite Member` button is visible
2. The Invite button is enabled

---

### TC-HAPPY-002: Members tab shows expected columns

**Action**:
1. Visit `/members`
2. Click the `Members` tab (if not active by default)

**Observation 1 — Column headers**:
1. Column header `Name` is visible
2. Column header `Role` is visible
3. Column header `Status` is visible

---

### TC-HAPPY-003: Members tab lists at least the logged-in user

**Action**:
1. Visit `/members`

**Observation 1 — Network call**:
1. Exactly one `POST /user/get_all_users_for_organization` is recorded

**Observation 2 — Row presence**:
1. At least one row is rendered in the Members table
2. The signed-in user's email appears in that row

---

### TC-HAPPY-004: Search input is interactive

**Action**:
1. Visit `/members`
2. Type `foo` into the search input
3. Clear the search input

**Observation 1 — No crash**:
1. The page does not throw a React error
2. The search input value is empty after clearing

---

### TC-HAPPY-005: Role filter dropdown opens with documented options

**Action**:
1. Visit `/members`
2. Click the Role filter dropdown trigger

**Observation 1 — Options list**:
1. The dropdown contains options `All`, `Owner`, `Admin`, `Member`, `Viewer`
2. No additional options are shown

---

### TC-HAPPY-006: Invitations tab renders its own column headers

**Action**:
1. Visit `/members`
2. Click the `Invitations` tab

**Observation 1 — Network call**:
1. Exactly one `POST /user/get_all_invited_users_for_organization` is recorded

**Observation 2 — Column headers**:
1. Column header `Email` is visible
2. Column header `Role` is visible
3. Column header `Status` is visible

---

### TC-HAPPY-007: Clicking Invite Member opens the modal with all three fields

**Action**:
1. Visit `/members`
2. Click `Invite Member`

**Observation 1 — Modal opens**:
1. A dialog appears containing the heading or aria-label for invitation
2. Modal contains an input named `name`
3. Modal contains an input named `email`
4. Modal contains a Role select trigger with id `invite-role`

---

### TC-HAPPY-008: Valid invite creates a new row + success toast

**Action**:
1. Open the Invite modal
2. Fill `name = __e2e__ Invite`, `email = __e2e__user+<uuid>@example.com`, role = `Member`
3. Click `Send Invite`

**Observation 1 — Network**:
1. Exactly one `POST /organization/invite_user_to_organization` is recorded
2. Body contains `name`, `email`, and `role`

**Observation 2 — Toast**:
1. A success Sonner toast is visible in `[data-sonner-toast]`

**Observation 3 — Invitations tab**:
1. Switching to the Invitations tab shows a new row containing the invited email

**Cleanup**: cancel the invitation in `finally`.

---

### TC-HAPPY-009: Cancelling a pending invitation removes the row

**Preconditions**: An invitation row already exists for `__e2e__cancel+<uuid>@example.com`.

**Action**:
1. Switch to the Invitations tab
2. Click the `Cancel invitation` icon on the target row
3. Confirm the cancel dialog (if any)

**Observation 1 — Network**:
1. Exactly one `DELETE /organization/cancel_invitation?invite_id=...` is recorded

**Observation 2 — Row disappears**:
1. The row containing the cancelled email is no longer in the DOM

---

### TC-HAPPY-010: Resending a pending invitation surfaces a toast

**Preconditions**: An invitation row exists.

**Action**:
1. Switch to the Invitations tab
2. Click the `Resend invitation` icon

**Observation 1 — Network**:
1. Exactly one `POST /organization/resend_invitation?invite_id=...` is recorded

**Observation 2 — Toast + row persistence**:
1. A Sonner toast appears
2. The invitation row is still in the DOM

---

### TC-HAPPY-011: Signed-in owner role dropdown is locked

**Preconditions**: Logged-in user is the only owner (last-owner protection).

**Action**:
1. Visit `/members`
2. Locate the row for the signed-in user

**Observation 1 — Dropdown locked**:
1. The role dropdown for that row is disabled OR is not rendered
2. No tooltip-driven click changes the role

---

### TC-HAPPY-012: Signed-in owner Delete button is locked

**Preconditions**: Logged-in user is the only owner.

**Action**:
1. Visit `/members`
2. Locate the row for the signed-in user

**Observation 1 — Delete locked**:
1. The Delete icon on that row is disabled OR is not rendered

---

### TC-HAPPY-013: Member role cannot see Invite CTA

**Preconditions**: Logged in as a `member` (non-admin / non-owner).

**Action**:
1. Visit `/members`

**Observation 1 — CTA hidden / disabled**:
1. The `Invite Member` button is either not in the DOM or has the `disabled` attribute

---

### TC-HAPPY-014: Member cannot mutate other roles

**Preconditions**: Logged in as a `member`.

**Action**:
1. Visit `/members`
2. Locate a non-self row

**Observation 1 — Role dropdown locked**:
1. The role dropdown for that row is disabled or non-interactive

---

### TC-HAPPY-015: Member cannot delete others

**Preconditions**: Logged in as a `member`.

**Action**:
1. Visit `/members`
2. Locate a non-self row

**Observation 1 — Delete locked**:
1. The Delete icon for that row is not in the DOM or is disabled

---

### TC-HAPPY-016: Empty members list shows invite CTA

**Action**:
1. Mock `POST /user/get_all_users_for_organization` to return `[]`
2. Visit `/members`

**Observation 1 — Empty state**:
1. An empty-state message is visible
2. The `Invite Member` CTA is still visible

---

### TC-HAPPY-017: Empty invitations tab shows empty state

**Action**:
1. Mock `POST /user/get_all_invited_users_for_organization` to return `[]`
2. Visit `/members` and switch to Invitations tab

**Observation 1 — Empty state text**:
1. The text `No pending invitations` (or equivalent) is visible

---

### TC-HAPPY-018: No-match search shows empty state

**Action**:
1. Visit `/members`
2. Type a string that matches no row into search

**Observation 1 — Empty state**:
1. A `No matches` message is visible
2. The table body has zero rows

---

### TC-HAPPY-019: Sort by Name reorders rows

**Action**:
1. Visit `/members`
2. Click the `Name` column header

**Observation 1 — Rows reorder ascending**:
1. The first row's Name is alphabetically smallest

**Observation 2 — Second click reverses**:
1. Clicking the header again reorders descending
2. The first row's Name is alphabetically largest

---

### TC-HAPPY-020: Sort by Role reorders rows

**Action**:
1. Visit `/members`
2. Click the `Role` column header

**Observation 1 — Rows reorder by role enum order**:
1. Owners group together, then Admins, then Members, then Viewers (or reverse on second click)

---

### TC-HAPPY-021: Role filter narrows table to admins

**Action**:
1. Visit `/members`
2. Open the Role filter
3. Pick `Admin`

**Observation 1 — Filtered rows**:
1. Every visible row has Role `Admin`
2. No `Owner` / `Member` / `Viewer` rows are visible

---

### TC-HAPPY-022: Owner has full member CRUD

**Preconditions**: Logged in as owner; at least one non-owner member exists.

**Action**:
1. Visit `/members`
2. On a non-last-owner row, change role via the dropdown
3. Delete a non-last-owner row

**Observation 1 — Role change**:
1. `POST /organization/update_member_role` is recorded
2. The row's role cell reflects the new value

**Observation 2 — Delete**:
1. `DELETE /organization/remove_user_from_organization` is recorded
2. The row disappears

---

### TC-HAPPY-023: Admin cannot change owner roles

**Preconditions**: Logged in as admin; an owner row is present.

**Action**:
1. Visit `/members`
2. Locate the owner row

**Observation 1 — Dropdown disabled**:
1. The role dropdown on the owner row is disabled for the admin viewer

---

### TC-HAPPY-024: Last-owner row is locked with tooltip

**Preconditions**: Only one owner in the org.

**Action**:
1. Visit `/members`
2. Hover the locked role dropdown

**Observation 1 — Locked controls**:
1. The role dropdown for the last owner is disabled
2. The Delete icon for the last owner is disabled or hidden

**Observation 2 — Tooltip explains the lock**:
1. A tooltip appears with text explaining the last-owner restriction (⚠ exact copy unverified)

---

### TC-HAPPY-025: Owner self-delete with other owners redirects to /organizations

**Preconditions**: Logged in as owner; at least one other owner exists.

**Action**:
1. Visit `/members`
2. Click Delete on the signed-in user's row
3. Confirm the modal

**Observation 1 — Delete fires**:
1. `DELETE /organization/remove_user_from_organization?user_id=<self>` is recorded

**Observation 2 — Redirect**:
1. URL becomes `/organizations` within 2s

---

### TC-HAPPY-026: Sole owner self-delete is blocked

**Preconditions**: Logged in as sole owner.

**Action**:
1. Visit `/members`
2. Attempt to delete self

**Observation 1 — Delete blocked**:
1. The Delete icon is disabled
2. A tooltip explains why (⚠ exact copy unverified)

---

### TC-VALIDATE-001: Send Invite is disabled while form is invalid

**Action**:
1. Open the Invite modal
2. Leave Name and Email blank

**Observation 1 — Submit blocked**:
1. The `Send Invite` button has the `disabled` attribute
2. Clicking it fires zero `POST /organization/invite_user_to_organization` requests

---

### TC-VALIDATE-002: Invalid email keeps Send Invite disabled

**Action**:
1. Open the Invite modal
2. Type `John` into Name
3. Type `not-an-email` into Email
4. Blur the Email input

**Observation 1 — Inline / disabled state**:
1. `Send Invite` is still disabled
2. (If inline error supported) helper text under Email reads a validation message

---

### TC-VALIDATE-003: Whitespace-only name disables Send Invite

**Action**:
1. Open the Invite modal
2. Type `   ` (whitespace only) into Name
3. Type a valid Email

**Observation 1 — Disabled**:
1. `Send Invite` is disabled

---

### TC-VALIDATE-004: Invalid email formats fail validation

**Action**:
1. Open the Invite modal
2. For each of `noat.com`, `foo@`, `foo@@bar.com`, `foo@bar`:
   1. Type the value into Email and blur

**Observation 1 — Disabled for every value**:
1. `Send Invite` remains disabled for each input
2. Zero `POST /organization/invite_user_to_organization` requests are recorded

---

### TC-ERROR-001: Inviting the same email twice surfaces an error toast

**Preconditions**: An invitation for `dup+<uuid>@example.com` already exists.

**Action**:
1. Open the Invite modal
2. Submit a new invitation for the same email

**Observation 1 — Error toast**:
1. A Sonner error toast appears with the backend `detail` (e.g. `Email already invited`)

**Observation 2 — Modal remains**:
1. The Invite modal is still open with the entered values intact

---

### TC-ERROR-002: Direct invite call as member surfaces 403 toast

**Preconditions**: Logged in as `member`.

**Action**:
1. Visit `/members`
2. Programmatically trigger `POST /organization/invite_user_to_organization` (via dev tools / fixture)

**Observation 1 — 403 surfaces**:
1. A toast appears with text matching `Forbidden`

**API mock**: route returns `403 { "detail": "Forbidden" }`.

---

### TC-ERROR-003: 400 invalid email keeps modal open with toast

**Action**:
1. Open Invite modal and submit a valid-looking email

**Observation 1 — Toast**:
1. A toast with text equal to the 400 `detail` is visible

**Observation 2 — Modal stays open**:
1. The Invite modal is still visible with form values intact

**API mock**: `POST /organization/invite_user_to_organization` → `400 { "detail": "Invalid email" }`.

---

### TC-ERROR-004: 401 on invite triggers login redirect on next nav

**Action**:
1. Open Invite modal and submit valid values

**Observation 1 — Toast**:
1. Toast title equals `Could not validate credentials`

**Observation 2 — Next nav redirects to login**:
1. Navigating to any protected route afterward lands on `/auth/login`

**API mock**: invite endpoint → `401 { "detail": "Could not validate credentials" }`.

---

### TC-ERROR-005: 403 on invite shows toast

**Action**:
1. Submit a valid invite

**Observation 1 — Toast + modal**:
1. Toast surfaces the `detail`
2. Modal stays open

**API mock**: invite endpoint → `403 { "detail": "Forbidden" }`.

---

### TC-ERROR-006: 409 duplicate email surfaces toast

**Action**:
1. Submit a valid invite for an email already in the org

**Observation 1 — Toast**:
1. Toast text equals the `detail` (e.g. `Email already invited`)

**Observation 2 — Modal stays open**:
1. Invite modal still rendered

**API mock**: invite endpoint → `409 { "detail": "Email already invited" }`.

---

### TC-ERROR-007: 500 on invite shows toast and preserves form

**Action**:
1. Submit a valid invite

**Observation 1 — Toast**:
1. A generic error toast appears

**Observation 2 — Modal preserved**:
1. The Invite modal is still open with form values intact

**API mock**: invite endpoint → `500 { "detail": "Internal server error" }`.

---

### TC-ERROR-008: Last-owner demotion 403 reverts dropdown

**Preconditions**: Demotion attempted on the last owner.

**Action**:
1. Change the role of the last-owner row from Owner → Admin

**Observation 1 — Toast**:
1. Toast text equals `Cannot demote the last owner`

**Observation 2 — Dropdown reverts**:
1. Within 1s of the response the dropdown shows `Owner` again

**API mock**: `POST /organization/update_member_role` → `403 { "detail": "Cannot demote the last owner" }`.

---

### TC-ERROR-009: 500 on role change reverts dropdown

**Action**:
1. Change a member's role

**Observation 1 — Toast + revert**:
1. Toast surfaces a generic error
2. Dropdown reverts to the previous role

**API mock**: role-change endpoint → `500`.

---

### TC-ERROR-010: Last-owner delete 403 shows toast

**Action**:
1. Click Delete on the last-owner row (via direct API call if UI blocks it)

**Observation 1 — Toast + row persists**:
1. Toast text equals `Cannot remove the last owner`
2. The row is still visible after the response

**API mock**: delete endpoint → `403 { "detail": "Cannot remove the last owner" }`.

---

### TC-ERROR-011: 404 on delete refetches list

**Action**:
1. Click Delete on a member row

**Observation 1 — Refetch**:
1. After the 404, `POST /user/get_all_users_for_organization` is fired
2. The row disappears from the table

**API mock**: delete endpoint → `404 { "detail": "Not found" }`.

---

### TC-ERROR-012: 500 on delete shows toast and preserves row

**Action**:
1. Click Delete on a member row

**Observation 1 — Toast + row persists**:
1. Generic error toast appears
2. The row is still in the DOM

**API mock**: delete endpoint → `500`.

---

### TC-ERROR-013: 404 on cancel refetches invitations

**Action**:
1. Cancel an invitation

**Observation 1 — Refetch + row gone**:
1. `POST /user/get_all_invited_users_for_organization` is recorded
2. The row is no longer in the DOM

**API mock**: cancel endpoint → `404`.

---

### TC-ERROR-014: 500 on cancel shows toast and preserves row

**Action**:
1. Cancel an invitation

**Observation 1 — Toast + row persists**:
1. Error toast appears
2. The invitation row is still rendered

**API mock**: cancel endpoint → `500`.

---

### TC-ERROR-015: 429 on resend surfaces rate-limit toast

**Action**:
1. Click Resend on an invitation row

**Observation 1 — Toast**:
1. Toast text equals `Too many resend attempts`

**Observation 2 — Row persists**:
1. The invitation row is still in the DOM

**API mock**: resend endpoint → `429 { "detail": "Too many resend attempts" }`.

---

### TC-ERROR-016: 500 on resend shows toast

**Action**:
1. Click Resend on an invitation row

**Observation 1 — Toast**:
1. A generic error toast appears

**API mock**: resend endpoint → `500`.

---

### TC-ERROR-017: Members list 500 surfaces toast

**Action**:
1. Visit `/members`

**Observation 1 — Toast + empty table**:
1. An error toast appears
2. The Members table is empty with a retry affordance

**API mock**: members-list endpoint → `500`.

---

### TC-ERROR-018: Invitations list 500 surfaces toast

**Action**:
1. Visit `/members` and switch to Invitations tab

**Observation 1 — Toast + empty table**:
1. An error toast appears
2. The Invitations table is empty

**API mock**: invitations-list endpoint → `500`.

---

### TC-NAV-001: Unauthenticated visit redirects to login

**Preconditions**: no `tone_access_token` cookie.

**Action**:
1. Visit `/members`

**Observation 1 — Redirect**:
1. URL becomes `/auth/login?redirect=%2Fmembers`
2. No Members content is rendered

---

### TC-NAV-002: Expired token redirects to login

**Preconditions**: `tone_access_token` cookie present but expired.

**Action**:
1. Visit `/members`

**Observation 1 — Redirect + cleanup**:
1. URL becomes `/auth/login?redirect=%2Fmembers`
2. The expired cookie is cleared (verified after redirect)

---

### TC-NAV-003: Invitation email link has mailto attribute

**Action**:
1. Visit `/members` and open the Invitations tab
2. Inspect the email link in an invitation row

**Observation 1 — Attribute**:
1. The link's `href` starts with `mailto:`

---

### TC-NAV-004: Back after closing modal is a no-op for URL

**Action**:
1. Visit `/members`
2. Open the Invite modal
3. Close it via the `X` button
4. Press the browser Back button

**Observation 1 — URL unchanged**:
1. The URL is still `/members`

**Observation 2 — Focus restored**:
1. Focus returns to the `Invite Member` trigger button

---

### TC-NAV-005: Tab switch updates query param and preserves counts

**Action**:
1. Visit `/members`
2. Click the `Invitations` tab

**Observation 1 — URL updated**:
1. The URL contains `?tab=invitations` (or equivalent)

**Observation 2 — Counts persist**:
1. Switching back to `Members` shows the same row count seen on first load

---

### TC-LOADING-001: Slow invite disables button with loading state

**Action**:
1. Open Invite modal
2. Fill valid values
3. Click Send Invite (backend delayed ~3500 ms)

**Observation 1 — Loading state**:
1. The Send Invite button shows a loading label / spinner within 100 ms
2. The button has `disabled` while in flight

**Observation 2 — Double-submit blocked**:
1. Clicking the button several more times records exactly one `POST /organization/invite_user_to_organization`

**API mock**: invite endpoint → 200 delayed by 3500 ms.

---

### TC-EDGE-001: Network failure on invite preserves form

**Action**:
1. Open Invite modal and submit valid values

**Observation 1 — Toast + modal preserved**:
1. Error toast appears
2. Modal stays open with form values intact

**API mock**: invite endpoint → `route.abort('failed')`.

---

### TC-EDGE-002: Network failure on role change reverts dropdown

**Action**:
1. Change a member's role

**Observation 1 — Toast + revert**:
1. Error toast appears
2. Dropdown reverts to the previous role

**API mock**: role-change endpoint → `route.abort('failed')`.

---

### TC-EDGE-003: Network failure on delete preserves row

**Action**:
1. Click Delete on a row

**Observation 1 — Toast + row persists**:
1. Error toast appears
2. Row is still in the DOM

**API mock**: delete endpoint → `route.abort('failed')`.

---

### TC-EDGE-004: Concurrent cancel handled gracefully

**Action**:
1. Two admins cancel the same invitation
2. The second admin's cancel returns 404

**Observation 1 — Toast + row gone**:
1. A toast appears for the second admin
2. The row is already absent (refetch ran)

---

### TC-EDGE-005: Email whitespace trimmed before invite

**Action**:
1. Submit invite with email `  john@acme.com  `

**Observation 1 — Trimmed payload**:
1. The request body's `email` equals `john@acme.com` (no leading/trailing whitespace)

**Observation 2 — Row shows clean email**:
1. The new invitation row shows `john@acme.com` without spaces

> ⚠ unverified whether the frontend or backend trims — document current behaviour.

---

### TC-EDGE-006: Email casing handled consistently

**Action**:
1. Submit invite with email `Foo@BAR.com`

**Observation 1 — Persistence**:
1. After reload the email appears either fully lower-cased or as entered (consistent with backend behaviour)

> ⚠ unverified — confirm casing rule.

---

### TC-EDGE-007: Unicode + emoji name round-trips

**Action**:
1. Submit invite with `name = "Adä 🚀"`

**Observation 1 — Persistence**:
1. Invitation row renders the unicode + emoji correctly

---

### TC-EDGE-008: Script tag in name is escaped on render

**Action**:
1. Submit invite with `name = "<script>alert(1)</script>"`

**Observation 1 — Escaped render**:
1. The row renders the literal `<script>` text
2. `window.alert` is not invoked

---

### TC-EDGE-009: Oversized name handled gracefully

**Action**:
1. Submit invite with a 600-char `name`

**Observation 1 — Outcome**:
1. The request is either accepted or inline-error rejected; no crash either way

---

### TC-EDGE-010: Max-length email accepted

**Action**:
1. Submit invite with a 254-char valid email

**Observation 1 — Accepted**:
1. Request succeeds (200/201) and a row appears

---

### TC-EDGE-011: Members pagination boundary disables prev/next

**Preconditions**: Members list is paginated.

**Action**:
1. Navigate to page 1, then to the last page

**Observation 1 — Boundaries**:
1. On page 1 the `Prev` control is disabled
2. On the last page the `Next` control is disabled

---

### TC-A11Y-001: Invite modal tab order matches visual order

**Action**:
1. Open Invite modal
2. Focus the Name input and press Tab repeatedly

**Observation 1 — Order**:
1. Focus moves Name → Email → Role → Send Invite
2. No focusable element is skipped

---

### TC-A11Y-002: Enter key submits Invite modal

**Action**:
1. Open Invite modal
2. Fill valid values
3. Press Enter while focused inside the modal

**Observation 1 — Submit fires**:
1. Exactly one `POST /organization/invite_user_to_organization` is recorded

---

### TC-A11Y-003: Invite modal traps focus and restores on close

**Action**:
1. Open Invite modal
2. Tab past the last focusable element

**Observation 1 — Focus wraps**:
1. Focus wraps back to the first focusable element in the modal

**Observation 2 — Escape closes + restores focus**:
1. Pressing Escape closes the modal
2. Focus returns to the `Invite Member` CTA button

---

### TC-A11Y-004: Inline errors are announced

**Action**:
1. Open Invite modal
2. Trigger an inline validation error

**Observation 1 — ARIA**:
1. The inline error element has `role="alert"` or `aria-live="polite"`

---

### TC-A11Y-005: Role dropdown is keyboard-operable

**Action**:
1. Visit `/members`
2. Focus a member's role dropdown
3. Use arrow keys to change the role and press Enter

**Observation 1 — Change applied**:
1. The role-change network call fires once
2. The row reflects the new role

---

### TC-A11Y-006: Delete confirm modal is keyboard-operable

**Action**:
1. Visit `/members`
2. Tab to a Delete icon and press Enter
3. Tab to the confirm button in the dialog and press Enter

**Observation 1 — Delete completes**:
1. `DELETE /organization/remove_user_from_organization` is recorded
2. The row disappears

---

### TC-FULL-001: Invite → assert row → resend → cancel → assert gone

**Preconditions**: Signed in as owner.

**Action**:
1. Click `Invite Member`; fill Name = `__e2e__ MM`, Email = `__e2e__mm+<uuid>@example.com`, Role = `Member`; click `Send Invite`
2. Switch to Invitations tab; locate the row
3. Click `Resend invitation` on that row
4. Click `Cancel invitation` on that row and confirm

**Observation 1 — Invite succeeds**:
1. `POST /organization/invite_user_to_organization` is recorded
2. Success toast appears

**Observation 2 — Row appears**:
1. Invitations tab contains a row with the new email

**Observation 3 — Resend succeeds**:
1. `POST /organization/resend_invitation?invite_id=...` is recorded
2. A toast confirms the resend

**Observation 4 — Cancel succeeds**:
1. `DELETE /organization/cancel_invitation?invite_id=...` is recorded
2. The row is no longer in the DOM

**Cleanup**: `try/finally` ensures the invitation is cancelled.

---

### TC-FULL-002: Lifecycle invite (Admin) → resend → role change → cancel

**Preconditions**: Signed in as owner.

**Action**:
1. Open Invite modal; submit with Role = `Admin`
2. Switch to Invitations tab; verify row
3. Click Resend; verify toast
4. Mock role-change call to succeed; change the (mocked) accepted member's role to `Member`
5. Cancel the invitation

**Observation 1 — All steps fire expected requests**:
1. `POST /organization/invite_user_to_organization` recorded with role `admin`
2. `POST /organization/resend_invitation` recorded
3. `POST /organization/update_member_role?member_id=...&role=member` recorded (mocked)
4. `DELETE /organization/cancel_invitation` recorded

**Observation 2 — Toast + UI**:
1. Every step's success surfaces a toast OR row mutation per the spec
2. `try/finally` ensures the invitation is cancelled even on assertion failure

---

## Coverage map (what `TC-FULL-001` transitively exercises)

| Scenario          | Covered by TC-FULL-001? | Notes                              |
| ----------------- | ----------------------- | ---------------------------------- |
| TC-HAPPY-007 (MI-001) | yes                 | invite modal opened + filled       |
| TC-HAPPY-008 (MI-004) | yes                 | toast + row assertion              |
| TC-HAPPY-009 (INV-001) | yes                | cancel + row gone                  |
| TC-HAPPY-010 (INV-002) | yes                | resend toast                       |

---

## Deferred (`test.skip` / `test.fixme`)

- **MR-002** (role-change persistence on an accepted member) — skipped. The invitation token is NOT exposed via `/user/get_all_invited_users_for_organization` (`Invite.to_dict` at `core/models/invite.py:31` omits it), so there is no way to programmatically accept an invitation in CI.
- **MD-002** (delete-confirm modal on a non-last-owner member) — skipped for the same reason.
- **MI-006** (Core member-cap of 3 → 403 on next invite) — `test.fixme`. The cap counts both members and pending invites and risks leaving the org near the cap. Run manually in a dedicated test env.

## Out of scope

- Multi-user invite-accept-handoff flows (need a second authenticated context).
- Transfer-ownership flow (no UI today; only the backend supports it).

## Cleanup

Every test that creates an invitation cancels it in `try/finally`. The `__e2e__` prefix on invite emails ensures any leftovers from aborted runs are easy to identify and sweep.

---

## Edge Cases (each appears as a `TC-EDGE-*` or `TC-VALIDATE-*` test case above)

- [x] Network failure on invite — see TC-EDGE-001
- [x] Network failure on role change — see TC-EDGE-002
- [x] Network failure on delete — see TC-EDGE-003
- [x] Concurrent cancel — see TC-EDGE-004
- [x] Email whitespace — see TC-EDGE-005
- [x] Email casing — see TC-EDGE-006
- [x] Unicode + emoji name — see TC-EDGE-007
- [x] Script tag in name — see TC-EDGE-008
- [x] Oversized name (>500 chars) — see TC-EDGE-009
- [x] Max-length email — see TC-EDGE-010
- [x] Pagination boundary — see TC-EDGE-011

---

## Business Rules

- Invite modal Role choices are `Admin`, `Member`, `Viewer`; `Owner` is never an invite role.
- Last-owner protection: the role dropdown and Delete control are both locked on the last-remaining owner row.
- Member-cap (Core edition) counts both active members and pending invites.

---

## Accessibility Requirements (each appears as a `TC-A11Y-*` test case above)

- [x] Invite modal tab order matches visual order — see TC-A11Y-001
- [x] Enter submits the Invite modal — see TC-A11Y-002
- [x] Invite modal traps focus and restores on close — see TC-A11Y-003
- [x] Inline errors announced via `role="alert"` / `aria-live` — see TC-A11Y-004
- [x] Role dropdown keyboard-operable — see TC-A11Y-005
- [x] Delete confirm modal keyboard-operable — see TC-A11Y-006
