import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import {
  cancelInvitation,
  inviteUserToOrganization,
  pagedGetAllInvitedUsersForOrganization,
  pagedGetAllUsersForOrganization,
  removeOrganizationMember,
  resendInvitation,
  updateOrganizationMemberRole,
} from '@/services/userService';
import type { ListRequest, ListResponse } from '@/types/list';
import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';

const DEFAULT_PARAMS: ListRequest = {
  page: 1,
  page_size: 10,
  sort_order: 'desc',
};

// ────────────────────────────────────────────────────────────────────────────
// Members
// ────────────────────────────────────────────────────────────────────────────

const membersRefreshAtom = atom(0);
const membersParamsAtom = atom<ListRequest>({ ...DEFAULT_PARAMS });

const membersPagedAtom = atom<Promise<ListResponse<OrganizationMemberApi>>>(async (get) => {
  get(membersRefreshAtom);
  return pagedGetAllUsersForOrganization(get(membersParamsAtom));
});

const loadableMembersPagedAtom = loadable(membersPagedAtom);

const setMembersParamsAtom = atom(null, (get, set, patch: Partial<ListRequest>) => {
  const current = get(membersParamsAtom);
  // Reset to page 1 whenever filters/search/sort change, so users don't see
  // an empty page when their result set shrinks.
  const resetsPage =
    'search' in patch ||
    'sort_by' in patch ||
    'sort_order' in patch ||
    'filters' in patch ||
    'page_size' in patch;
  set(membersParamsAtom, {
    ...current,
    ...patch,
    page: resetsPage ? 1 : (patch.page ?? current.page),
  });
});

const refetchMembersAtom = atom(null, (_get, set) => {
  set(membersRefreshAtom, (c) => c + 1);
});

// ────────────────────────────────────────────────────────────────────────────
// Invitations
// ────────────────────────────────────────────────────────────────────────────

const invitationsRefreshAtom = atom(0);
const invitationsParamsAtom = atom<ListRequest>({ ...DEFAULT_PARAMS });

const invitationsPagedAtom = atom<Promise<ListResponse<OrganizationInviteApi>>>(async (get) => {
  get(invitationsRefreshAtom);
  return pagedGetAllInvitedUsersForOrganization(get(invitationsParamsAtom));
});

const loadableInvitationsPagedAtom = loadable(invitationsPagedAtom);

const setInvitationsParamsAtom = atom(null, (get, set, patch: Partial<ListRequest>) => {
  const current = get(invitationsParamsAtom);
  const resetsPage =
    'search' in patch ||
    'sort_by' in patch ||
    'sort_order' in patch ||
    'filters' in patch ||
    'page_size' in patch;
  set(invitationsParamsAtom, {
    ...current,
    ...patch,
    page: resetsPage ? 1 : (patch.page ?? current.page),
  });
});

const refetchInvitationsAtom = atom(null, (_get, set) => {
  set(invitationsRefreshAtom, (c) => c + 1);
});

// ────────────────────────────────────────────────────────────────────────────
// Mutations
// ────────────────────────────────────────────────────────────────────────────

const inviteUserToOrganizationAtom = atom(
  null,
  async (_get, set, payload: { name: string; email: string; role: string }) => {
    await inviteUserToOrganization(payload);
    set(invitationsRefreshAtom, (c) => c + 1);
  },
);

const updateMemberRoleAtom = atom(
  null,
  async (_get, set, payload: { memberId: number; role: string }) => {
    await updateOrganizationMemberRole(payload.memberId, payload.role);
    set(membersRefreshAtom, (c) => c + 1);
  },
);

const removeMemberAtom = atom(null, async (_get, set, userId: number) => {
  await removeOrganizationMember(userId);
  set(membersRefreshAtom, (c) => c + 1);
});

const cancelInvitationAtom = atom(null, async (_get, set, inviteId: number) => {
  await cancelInvitation(inviteId);
  set(invitationsRefreshAtom, (c) => c + 1);
});

const resendInvitationAtom = atom(null, async (_get, set, inviteId: number) => {
  await resendInvitation(inviteId);
  set(invitationsRefreshAtom, (c) => c + 1);
});

export {
  cancelInvitationAtom,
  invitationsParamsAtom,
  inviteUserToOrganizationAtom,
  loadableInvitationsPagedAtom,
  loadableMembersPagedAtom,
  membersParamsAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
  removeMemberAtom,
  resendInvitationAtom,
  setInvitationsParamsAtom,
  setMembersParamsAtom,
  updateMemberRoleAtom,
};
