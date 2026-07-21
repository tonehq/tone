import { listRequest, pagedListRequest } from '@/services/listHelpers';
import type { ListRequest } from '@/types/list';
import type {
  OrganizationCreateResponse,
  OrganizationDetails,
  OrganizationListItem,
  OrganizationUpdatePayload,
  OrganizationUpdateResponse,
} from '@/types/organization';
import axios from '@/utils/axios';

export const getAssociatedTenants = (request: ListRequest = {}) =>
  listRequest<OrganizationListItem>('/organization/get_associated_tenants', request);

export const pagedGetAssociatedTenants = (request: ListRequest = {}) =>
  pagedListRequest<OrganizationListItem>('/organization/get_associated_tenants', request);

export const getOrganizationDetails = async (orgId: string): Promise<OrganizationDetails> => {
  const { data } = await axios.get<OrganizationDetails>('/organization/details', {
    params: { org_id: orgId },
  });
  return data;
};

export const createOrganization = async (
  name: string,
  schedulingTimezone?: string,
): Promise<OrganizationCreateResponse> => {
  const { data } = await axios.post<OrganizationCreateResponse>(
    '/organization/create_tenants',
    null,
    { params: { name, scheduling_timezone: schedulingTimezone || undefined } },
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

/** Read the active org's `settings` JSONB bag (default scheduling timezone, etc.). */
export const getOrganizationSettings = async (): Promise<Record<string, unknown>> => {
  const { data } = await axios.get<Record<string, unknown>>('/organization/settings');
  return data ?? {};
};

export const deleteOrganization = async (orgId: string): Promise<void> => {
  await axios.delete('/organization/delete', { params: { org_id: orgId } });
};

export const switchOrganization = async (orgId: string) => {
  const { data } = await axios.post('/auth/switch_organization', { organization_id: orgId });
  return data;
};
