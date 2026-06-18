# Members + Invitations (E2E scenarios)

> Companion to `frontend/e2e/dashboard/members.spec.ts`. Each scenario ID
> below maps to a Playwright `test(...)` name so a failing run can be triaged
> directly back to a scenario.

## User stories

- As an org owner / admin, I can invite a new member by name + email + role.
- As a member, I can see the list of active members and pending invitations
  in two separate tabs on `/members`.
- As an owner / admin, I can cancel a pending invitation or resend it.
- I cannot demote or remove the last owner — the role dropdown and Delete
  button on that row are locked.

## Routes

| Route | Component |
|---|---|
| `/members` | `frontend/src/components/settings/Members.tsx` |

## Key files

- `frontend/src/components/settings/Members.tsx` — top-level container with two tabs + invite button + error toasts.
- `frontend/src/components/settings/MembersTable.tsx` — active-member rows with role dropdown + Delete icon + last-owner lock.
- `frontend/src/components/settings/InvitationsTable.tsx` — pending invite rows with Cancel + Resend icons.
- `frontend/src/components/settings/InviteMemberModal.tsx` — modal with Name, Email, Role (Admin / Member / Viewer; no Owner).
- `frontend/src/atoms/SettingsAtom.tsx` — `membersAtom`, `invitationsAtom`, write atoms.
- `frontend/src/services/userService.ts` — axios calls.

## API endpoints exercised

| Method | Path | Triggered by |
|---|---|---|
| POST | `/user/get_all_users_for_organization` | Members tab load |
| POST | `/user/get_all_invited_users_for_organization` | Invitations tab load |
| POST | `/organization/invite_user_to_organization` | Invite modal Send |
| POST | `/organization/update_member_role?member_id=&role=` | per-row role change |
| DELETE | `/organization/remove_user_from_organization?user_id=` | per-row Delete |
| DELETE | `/organization/cancel_invitation?invite_id=` | Cancel invitation icon |
| POST | `/organization/resend_invitation?invite_id=` | Resend invitation icon |

## Scenarios — Members (ML-/MI-/MR-/MD-/INV-/MM-)

### List + rendering

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| ML-001 | Visit `/members` | Header, both tabs, and Invite Member CTA are visible | `renders the header, both tabs, and Invite Member CTA` |
| ML-002 | Members tab columns | Name, Role, Status headers visible | `Members tab shows the expected columns` |
| ML-003 | Members tab rows | At least one row (the signed-in user) renders | `Members tab lists at least one row (the logged-in user)` |
| ML-004 | Search interactive | Typing then clearing does not throw | `search input is interactive` |
| ML-005 | Role filter | Dropdown opens with All / Owner / Admin / Member / Viewer | `role filter dropdown opens with the documented options` |
| ML-006 | Invitations tab columns | Email, Role, Status headers visible | `Invitations tab renders its own column headers` |

### Invite modal — validation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-001 | Click Invite Member | Modal opens with Name, Email, Role | `clicking Invite Member opens the modal with all three fields` |
| MI-002 | Empty form | Send Invite button is disabled | `Send Invite is disabled while the form is invalid` |
| MI-003 | Invalid email | Send Invite stays disabled after blur | `invalid email keeps Send Invite disabled` |

### Invite — happy path + duplicates

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-004 | Valid invite | Success toast + row appears in Invitations tab | `valid invite creates a new row + success toast` |
| MI-005 | Same email twice | Error toast on second invite | `inviting the same email twice surfaces an error toast` |

### Invitation row actions

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| INV-001 | Cancel pending invitation | Row disappears | `cancelling a pending invitation removes the row` |
| INV-002 | Resend pending invitation | Toast appears; row stays | `resending a pending invitation surfaces a toast` |

### Last-owner protection

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MR-001 | Role dropdown on the signed-in owner | Disabled (or omitted) | `the signed-in owner role dropdown is locked or read-only` |
| MD-001 | Delete button on the signed-in owner | Disabled (or omitted) | `the signed-in owner Delete button is locked or omitted` |

### Comprehensive flow

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MM-FULL | Invite → assert row → resend → cancel → assert gone | Every step asserts a toast or row mutation; the invite is cancelled in the same test | `invite → assert row → resend → cancel → assert gone` |

MM-FULL exercises every writable control on the Invite modal + every Invitation row action:

| Section | Field | Selector | Helper | Asserted |
|---|---|---|---|---|
| Invite modal | Name | `input[name="name"]` (inside dialog) | `inviteMemberViaUI({ name })` | yes (row contains the email) |
| Invite modal | Email | `input[name="email"]` (inside dialog) | `inviteMemberViaUI({ email })` | yes |
| Invite modal | Role | `button[id="invite-role"]` (inside dialog) | `pickSelectOptionByLabel(role)` | role label is asserted indirectly via the row's Role cell |
| Invitations tab | Resend icon | `getByRole('button', { name: 'Resend invitation' })` | inline click | success toast |
| Invitations tab | Cancel icon | `getByRole('button', { name: 'Cancel invitation' })` | `cancelInvitationViaUI` | row count 0 after confirm |

## Coverage map (what `MM-FULL` transitively exercises)

| Scenario | Covered by MM-FULL? | Notes |
|---|---|---|
| MI-001 | yes | invite modal opened + filled |
| MI-004 | yes | toast + row assertion |
| INV-001 | yes | cancel + row gone |
| INV-002 | yes | resend toast |

## Deferred (`test.skip` / `test.fixme`)

- `MR-002` (role-change persistence on an accepted member) — skipped. The invitation token is NOT exposed via `/user/get_all_invited_users_for_organization` (`Invite.to_dict` at `core/models/invite.py:31` omits it), so there is no way to programmatically accept an invitation in CI. File a follow-up to either expose the token in a dev/test endpoint or seed an accepted-member fixture.
- `MD-002` (delete-confirm modal on a non-last-owner member) — skipped for the same reason.
- `MI-006` (Core member-cap of 3 → 403 on next invite) — `test.fixme`. The cap counts both members and pending invites, so running this for real in a shared test env risks leaving the org near the cap and breaking later runs. Run manually in a dedicated test env.

## Out of scope

- Multi-user invite-accept-handoff flows (need a second authenticated context).
- Transfer-ownership flow (no UI today; only the backend supports it).

## Cleanup

Every test that creates an invitation cancels it in `try/finally`. The `__e2e__` prefix on invite emails ensures any leftovers from aborted runs are easy to identify and sweep.

---

## Gap-filling scenarios

> Appended rows. New IDs start after the highest existing number per family
> (ML-006 → ML-010+, MI-005 → MI-010+, INV-002 → INV-010+, MR-001 → MR-010+,
> MD-001 → MD-010+). MM-FULL is unchanged; new lifecycle test is MM-EXT.

### Auth & access control

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| ML-010 | Visit `/members` without auth | Redirects to `/auth/login?redirect=%2Fmembers` | `unauthenticated visit redirects to login` |
| ML-011 | Visit `/members` with expired token | Same redirect; cookie cleanup verified | `expired token redirects to login` |
| MI-010 | Member (non-admin/owner) opens page | `Invite Member` CTA hidden / disabled | `member role cannot see Invite CTA` |
| MR-010 | Member tries to change another member's role | Role dropdown is disabled / read-only | `member cannot mutate other roles` |
| MD-010 | Member tries to delete another member | Delete button is hidden / disabled | `member cannot delete others` |
| MI-011 | Member calls `POST /organization/invite_user_to_organization` directly | Backend returns 403; UI surfaces toast `Forbidden` | `direct invite call as member surfaces 403 toast` |

### Backend error states

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-020 | `POST /organization/invite_user_to_organization` returns 400 invalid email | Inline error or toast; modal stays open with form intact | `400 invalid email keeps modal open with toast` |
| MI-021 | Invite returns 401 mid-flow | Toast `Could not validate credentials`; next nav hits login redirect | `401 on invite triggers login redirect on next nav` |
| MI-022 | Invite returns 403 (downgraded mid-session) | Access denied toast; modal stays open | `403 on invite shows toast` |
| MI-023 | Invite returns 409 duplicate (already a member or pending invite) | Toast with backend `detail`; modal stays open | `409 duplicate email surfaces toast` |
| MI-024 | Invite returns 500 | Generic error toast; modal intact | `500 on invite shows toast and preserves form` |
| MR-020 | `POST /organization/update_member_role` returns 403 (last owner demotion) | Toast `Cannot demote the last owner`; dropdown reverts to previous role | `last-owner demotion 403 reverts dropdown` |
| MR-021 | Role change returns 500 | Toast; dropdown reverts to previous role | `500 on role change reverts dropdown` |
| MD-020 | `DELETE /organization/remove_user_from_organization` returns 403 (last owner) | Toast `Cannot remove the last owner`; row stays | `last-owner delete 403 shows toast` |
| MD-021 | Delete member returns 404 (already gone) | Row disappears after refetch | `404 on delete refetches list` |
| MD-022 | Delete returns 500 | Toast; row remains | `500 on delete shows toast and preserves row` |
| INV-010 | Cancel invitation returns 404 | Row disappears after refetch | `404 on cancel refetches invitations` |
| INV-011 | Cancel invitation returns 500 | Toast; row remains | `500 on cancel shows toast` |
| INV-012 | Resend invitation returns 429 (rate limited) | Toast `Too many resend attempts`; row stays | `429 on resend surfaces rate-limit toast` |
| INV-013 | Resend invitation returns 500 | Generic error toast; row stays | `500 on resend shows toast` |
| ML-020 | `POST /user/get_all_users_for_organization` returns 500 | Error toast; empty table with retry affordance | `members list 500 surfaces toast` |
| ML-021 | `POST /user/get_all_invited_users_for_organization` returns 500 | Same on Invitations tab | `invitations list 500 surfaces toast` |

### Network resilience

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-030 | Network failure on Send Invite (`route.abort('failed')`) | Toast; modal stays open with form intact | `network failure on invite preserves form` |
| MI-031 | Slow invite (>3s) | Send button shows loading + `disabled`; double-submit blocked | `slow invite disables button with loading state` |
| MR-030 | Network failure on role change | Toast; dropdown reverts to previous role | `network failure on role change reverts dropdown` |
| MD-030 | Network failure on delete | Toast; row remains | `network failure on delete preserves row` |
| INV-020 | Concurrent: another admin cancels the same invitation | First action succeeds, second returns 404 → toast + row already gone | `concurrent cancel handled gracefully` |

### Input edge cases

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-040 | Email with leading/trailing whitespace | Trimmed before submit; row shows clean email | `email whitespace trimmed before invite` |
| MI-041 | Email with uppercase letters (e.g. `Foo@BAR.com`) | Lower-cased server-side or accepted as-is; reload shows persisted form | `email casing handled consistently` |
| MI-042 | Name whitespace only | Send Invite disabled | `whitespace-only name disables Send Invite` |
| MI-043 | Name with emoji / unicode | Accepted; row renders unicode in greeting on accept | `unicode + emoji name round-trips` |
| MI-044 | Name with `<script>` tag content | Stored verbatim; rendered as text in toast email body / table | `script tag in name is escaped on render` |
| MI-045 | Name >500 chars | Either accepted or inline error | `oversized name handled gracefully` |
| MI-046 | Invalid email formats (missing `@`, missing TLD, multiple `@`) | Inline error; Send Invite disabled | `invalid email formats fail validation` |
| MI-047 | Email exactly at max length (e.g. 254 chars) | Accepted | `max-length email accepted` |

### Accessibility & keyboard

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MI-050 | Tab through Invite modal | Order: Name → Email → Role → Send Invite | `Invite modal tab order matches visual order` |
| MI-051 | Submit Invite modal via Enter | Triggers Send Invite if valid | `Enter key submits Invite modal` |
| MI-052 | Invite modal traps focus | Tab wraps; Escape closes; focus restored to `Invite Member` CTA | `Invite modal traps focus and restores on close` |
| MI-053 | Inline form errors have `role="alert"` | Screen reader announces | `inline errors are announced` |
| MR-040 | Role dropdown reachable via keyboard | Arrow keys change role; Enter confirms | `role dropdown is keyboard-operable` |
| MD-040 | Delete confirm modal is keyboard-operable | Tab to confirm; Enter confirms | `Delete confirm modal is keyboard-operable` |

### List-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| ML-022 | Empty members list (impossible in practice but mock it) | Empty state with `Invite Member` CTA | `empty members list shows invite CTA` |
| ML-023 | Empty invitations list | `No pending invitations` empty state | `empty invitations tab shows empty state` |
| ML-024 | Search with no matches | `No matches` state | `no-match search shows empty state` |
| ML-025 | Pagination boundary on Members tab (if paginated) | Prev disabled on page 1, Next disabled on last page | `members pagination boundary disables prev/next` |
| ML-026 | Sort by Name on Members tab | Rows reorder asc / desc | `sort by name reorders rows` |
| ML-027 | Sort by Role on Members tab | Rows reorder by role enum order | `sort by role reorders rows` |
| ML-028 | Role filter `Admin` | Only admin rows visible | `role filter narrows table to admins` |

### Role-specific scenarios

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MR-011 | Owner can Invite + change any role + delete any non-last-owner | All actions succeed | `owner has full member CRUD` |
| MR-012 | Admin can Invite + change Member/Admin roles but NOT change Owner | Owner row's role dropdown disabled for admin | `admin cannot change owner roles` |
| MR-013 | Last owner row: role dropdown disabled + Delete locked | Tooltips explain the lock | `last-owner row is locked` |
| MD-011 | Owner deletes self (when other owners exist) | Confirmation modal; on confirm, redirected to org list | `owner self-delete with other owners redirects to /organizations` |
| MD-012 | Sole owner cannot self-delete | Delete disabled with tooltip | `sole owner self-delete is blocked` |

### Cross-feature navigation

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MN-010 | Click invited user's email link (mailto) | Default mail client opens (test asserts attribute, not OS behavior) | `invitation email link has mailto attribute` |
| MN-011 | Browser Back after closing Invite modal | URL unchanged (modal is overlay); focus restored to trigger | `back after closing modal is a no-op for URL` |
| MN-012 | Tab switch (Members ↔ Invitations) | `?tab=` query updates; counts persist | `tab switch updates query param and preserves counts` |

### Full lifecycle test

| ID | Scenario | Expected | Spec test name |
|---|---|---|---|
| MM-EXT | Invite Admin role → assert row → resend → change role to Member (mock backend OK if accept impossible) → cancel → assert gone | All toasts + row mutations asserted; `try/finally` ensures invitation is cancelled even on assertion failure | `lifecycle: invite (admin) → resend → role change → cancel` |
