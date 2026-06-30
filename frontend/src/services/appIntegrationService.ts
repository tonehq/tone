/**
 * API client for the ``app_integrations`` catalog.
 *
 * Endpoints live under ``/app-integration`` and mirror the backend router in
 * :mod:`core.api.v1.app_integrations` / :mod:`ee.api.v1.app_integrations`.
 */

import { pagedListRequest } from '@/services/listHelpers';
import type {
  AppIntegration,
  AppIntegrationCreatePayload,
  AppIntegrationUpdatePayload,
} from '@/types/appIntegration';
import type { ListRequest, ListResponse } from '@/types/list';
import axiosInstance from '@/utils/axios';

export const listAppIntegrations = (
  request: ListRequest = {},
): Promise<ListResponse<AppIntegration>> =>
  pagedListRequest<AppIntegration>('/app-integration/list', request);

export const getAppIntegration = async (id: string): Promise<AppIntegration> => {
  const { data } = await axiosInstance.get<AppIntegration>('/app-integration/get_app_integration', {
    params: { id },
  });
  return data;
};

export const createAppIntegration = async (
  payload: AppIntegrationCreatePayload,
): Promise<AppIntegration> => {
  const { data } = await axiosInstance.post<AppIntegration>(
    '/app-integration/create_app_integration',
    payload,
  );
  return data;
};

export const updateAppIntegration = async (
  id: string,
  payload: AppIntegrationUpdatePayload,
): Promise<AppIntegration> => {
  const { data } = await axiosInstance.put<AppIntegration>(
    '/app-integration/update_app_integration',
    payload,
    { params: { id } },
  );
  return data;
};

export const deleteAppIntegration = async (id: string): Promise<void> => {
  await axiosInstance.delete('/app-integration/delete_app_integration', { params: { id } });
};
