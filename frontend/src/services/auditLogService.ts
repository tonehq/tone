import type { ListAuditLogsRequest, ListAuditLogsResponse } from '@/types/settings/auditLog';
import axiosInstance from '@/utils/axios';

export const listAuditLogs = async (
  request: ListAuditLogsRequest,
): Promise<ListAuditLogsResponse> => {
  const { data } = await axiosInstance.post<ListAuditLogsResponse>('/audit-log/list', request);
  return data;
};
