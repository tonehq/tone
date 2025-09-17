import axios from '@/utils/axios';

// Get all users for organization
export const getAllUsersForOrganization = async () => {
  try {
    const response = await axios.get('/api/v1/user/get_all_users_for_organization');
    return response.data;
  } catch (error) {
    console.error('Error fetching users for organization:', error);
    throw error;
  }
};

// Get all invited users for organization
export const getAllInvitedUsersForOrganization = async () => {
  try {
    const response = await axios.get('/api/v1/user/get_all_invited_users_for_organization');
    return response.data;
  } catch (error) {
    console.error('Error fetching invited users for organization:', error);
    throw error;
  }
};

// Invite user to organization
export const inviteUserToOrganization = async (payload: {
  name: string;
  email: string;
  role: string;
}) => {
  try {
    const response = await axios.post('/api/v1/organization/invite_user_to_organization', payload);
    return response.data;
  } catch (error) {
    console.error('Error inviting user to organization:', error);
    throw error;
  }
};