import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import {
  cancelInvitation,
  getAllInvitedUsersForOrganization,
  getAllUsersForOrganization,
  inviteUserToOrganization,
  removeOrganizationMember,
  updateOrganizationMemberRole,
} from '@/services/userService';

import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';

// Trigger to force refetch in loadable atoms
const membersRefreshAtom = atom(0);
const invitationsRefreshAtom = atom(0);

const membersRowsAtom = atom<Promise<OrganizationMemberApi[]>>(async (get) => {
  get(membersRefreshAtom);
  const apiData = (await getAllUsersForOrganization()) as OrganizationMemberApi[];
  return apiData;
});

const invitationsRowsAtom = atom<Promise<OrganizationInviteApi[]>>(async (get) => {
  get(invitationsRefreshAtom);
  const apiData = (await getAllInvitedUsersForOrganization()) as OrganizationInviteApi[];
  return apiData;
});

const loadableMembersRowsAtom = loadable(membersRowsAtom);
const loadableInvitationsRowsAtom = loadable(invitationsRowsAtom);

const refetchMembersAtom = atom(null, (_get, set) => {
  set(membersRefreshAtom, (c) => c + 1);
});

const refetchInvitationsAtom = atom(null, (_get, set) => {
  set(invitationsRefreshAtom, (c) => c + 1);
});

const inviteUserToOrganizationAtom = atom(
  null,
  async (_get, set, payload: { name: string; email: string; role: string }) => {
    await inviteUserToOrganization(payload);
    set(invitationsRefreshAtom, (c) => c + 1);
  },
);

// Action: update member role and refresh members
const updateMemberRoleAtom = atom(
  null,
  async (_get, set, payload: { memberId: number; role: string }) => {
    await updateOrganizationMemberRole(payload.memberId, payload.role);
    set(membersRefreshAtom, (c) => c + 1);
  },
);

// Action: remove member and refresh members
const removeMemberAtom = atom(null, async (_get, set, userId: number) => {
  await removeOrganizationMember(userId);
  set(membersRefreshAtom, (c) => c + 1);
});

// Action: cancel invitation and refresh invitations
const cancelInvitationAtom = atom(null, async (_get, set, inviteId: number) => {
  await cancelInvitation(inviteId);
  set(invitationsRefreshAtom, (c) => c + 1);
});

export {
  cancelInvitationAtom,
  inviteUserToOrganizationAtom,
  loadableInvitationsRowsAtom,
  loadableMembersRowsAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
  removeMemberAtom,
  updateMemberRoleAtom,
};
