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
