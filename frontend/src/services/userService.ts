import { listRequest, pagedListRequest } from '@/services/listHelpers';
import type { ListRequest } from '@/types/list';
import type { OrganizationInviteApi, OrganizationMemberApi } from '@/types/settings/members';
import axios from '@/utils/axios';

export const getAllUsersForOrganization = (request: ListRequest = {}) =>
  listRequest<OrganizationMemberApi>('/user/get_all_users_for_organization', request);

export const pagedGetAllUsersForOrganization = (request: ListRequest = {}) =>
  pagedListRequest<OrganizationMemberApi>('/user/get_all_users_for_organization', request);

export const getAllInvitedUsersForOrganization = (request: ListRequest = {}) =>
  listRequest<OrganizationInviteApi>('/user/get_all_invited_users_for_organization', request);

export const pagedGetAllInvitedUsersForOrganization = (request: ListRequest = {}) =>
  pagedListRequest<OrganizationInviteApi>('/user/get_all_invited_users_for_organization', request);

export const inviteUserToOrganization = async (payload: {
  name: string;
  email: string;
  role: string;
}): Promise<void> => {
  await axios.post('/organization/invite_user_to_organization', payload);
};

export const updateOrganizationMemberRole = async (
  memberId: string,
  role: string,
): Promise<void> => {
  await axios.post(
    `/organization/update_member_role?member_id=${encodeURIComponent(memberId)}&role=${encodeURIComponent(role)}`,
  );
};

export const removeOrganizationMember = async (userId: string): Promise<void> => {
  await axios.delete(
    `/organization/remove_user_from_organization?user_id=${encodeURIComponent(userId)}`,
  );
};

export const cancelInvitation = async (inviteId: string): Promise<void> => {
  await axios.delete(`/organization/cancel_invitation?invite_id=${encodeURIComponent(inviteId)}`);
};

export const resendInvitation = async (inviteId: string): Promise<void> => {
  await axios.post(`/organization/resend_invitation?invite_id=${encodeURIComponent(inviteId)}`);
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
