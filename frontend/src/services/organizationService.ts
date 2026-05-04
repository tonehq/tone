import type {
  OrganizationCreateResponse,
  OrganizationDetails,
  OrganizationListItem,
  OrganizationUpdatePayload,
  OrganizationUpdateResponse,
} from '@/types/organization';
import axios from '@/utils/axios';

export const getAssociatedTenants = async (): Promise<OrganizationListItem[]> => {
  const { data } = await axios.get<OrganizationListItem[]>('/organization/get_associated_tenants');
  return data ?? [];
};

export const getOrganizationDetails = async (orgId: string): Promise<OrganizationDetails> => {
  const { data } = await axios.get<OrganizationDetails>('/organization/details', {
    params: { org_id: orgId },
  });
  return data;
};

export const createOrganization = async (name: string): Promise<OrganizationCreateResponse> => {
  const { data } = await axios.post<OrganizationCreateResponse>(
    '/organization/create_tenants',
    null,
    { params: { name } },
  );
  return data;
};

export const updateOrganization = async (
  orgId: string,
  payload: OrganizationUpdatePayload,
): Promise<OrganizationUpdateResponse> => {
  const { data } = await axios.put<OrganizationUpdateResponse>('/organization/details', payload, {
    params: { org_id: orgId },
  });
  return data;
};

export const deleteOrganization = async (orgId: string): Promise<void> => {
  await axios.delete('/organization/delete', { params: { org_id: orgId } });
};
