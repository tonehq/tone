import type { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import axios from '@/utils/axios';

export const getAllUsersForOrganization = async (): Promise<OrganizationMemberApi[]> => {
  const { data } = await axios.get<OrganizationMemberApi[]>('/organizations/members');
  return data ?? [];
};

export const getAllInvitedUsersForOrganization = async (): Promise<OrganizationInviteApi[]> => {
  const { data } = await axios.get<OrganizationInviteApi[]>('/organizations/invitations');
  return data ?? [];
};

export const inviteUserToOrganization = async (payload: {
  name: string;
  email: string;
  role: string;
}): Promise<void> => {
  await axios.post('/organizations/invite', payload);
};

export const updateOrganizationMemberRole = async (
  memberId: number,
  role: string
): Promise<void> => {
  await axios.patch(`/organizations/members/${memberId}`, { role });
};
