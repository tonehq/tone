import { getAllInvitedUsersForOrganization, getAllUsersForOrganization, inviteUserToOrganization } from '@/services/auth/userService';
import { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

interface MemberData {
  key: string;
  name: string;
  email: string;
  joinedDate: string;
  role: string;
  avatar: string | null;
}

interface InvitationData {
  key: string;
  name: string;
  email: string;
  invitedDate: string;
  status: string;
  role: string;
}

interface SettingsState {
  organizationList: any[];
  membersList: MemberData[];
  invitationsList: InvitationData[];
  membersLoading: boolean;
  invitationsLoading: boolean;
}

const settingsAtom = atom<SettingsState>({
  organizationList: [],
  membersList: [],
  invitationsList: [],
  membersLoading: false,
  invitationsLoading: false,
});

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

export {
  inviteUserToOrganizationAtom,
  loadableInvitationsRowsAtom,
  loadableMembersRowsAtom,
  refetchInvitationsAtom,
  refetchMembersAtom,
  settingsAtom
};

