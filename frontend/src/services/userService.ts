import type { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import axios from '@/utils/axios';

export const getAllUsersForOrganization = async (): Promise<OrganizationMemberApi[]> => {
  const { data } = await axios.get<OrganizationMemberApi[]>('/user/get_all_users_for_organization');
  return data ?? [];
};

export const getAllInvitedUsersForOrganization = async (): Promise<OrganizationInviteApi[]> => {
  const { data } = await axios.get<OrganizationInviteApi[]>(
    '/user/get_all_invited_users_for_organization',
  );
  return data ?? [];
};

export const inviteUserToOrganization = async (payload: {
  name: string;
  email: string;
  role: string;
}): Promise<void> => {
  await axios.post('/organization/invite_user_to_organization', payload);
};

export const updateOrganizationMemberRole = async (
  memberId: number,
  role: string,
): Promise<void> => {
  await axios.post(`/organization/update_member_role?member_id=${memberId}&role=${role}`);
};

export const removeOrganizationMember = async (userId: number): Promise<void> => {
  await axios.delete(`/organization/remove_user_from_organization?user_id=${userId}`);
};

export const cancelInvitation = async (inviteId: number): Promise<void> => {
  await axios.delete(`/organization/cancel_invitation?invite_id=${inviteId}`);
};

export const validateInvitation = async (
  email: string,
  code: string,
): Promise<{
  valid: boolean;
  email: string;
  name: string;
  role: string;
  user_exists: boolean;
  has_password: boolean;
}> => {
  const { data } = await axios.get(
    `/organization/validate_invitation?email=${encodeURIComponent(email)}&code=${encodeURIComponent(code)}`,
  );
  return data;
};

export const acceptInvitationWithPassword = async (payload: {
  email: string;
  code: string;
  password: string;
  user_tenant_id?: string;
}): Promise<void> => {
  await axios.post('/organization/accept_invitation_with_password', payload);
};
