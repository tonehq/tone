import type {
  CallFacets,
  CallFacetsParams,
  CallLogQueryParams,
  CallLogRow,
  ToolExecution,
  ToolExecutionStatus,
  ToolExecutionType,
} from '@/types/callLog';
import axiosInstance from '@/utils/axios';

export interface ToolExecutionsQuery {
  status?: ToolExecutionStatus;
  type?: ToolExecutionType;
}

export const getCallLogs = async (params: CallLogQueryParams) => {
  const res = await axiosInstance.post('/call-log/list', params);
  return res.data;
};

export const getCallFacets = async (params: CallFacetsParams): Promise<CallFacets> => {
  const res = await axiosInstance.post('/call-log/facets', params);
  return res.data;
};

export const getFilterValues = async (
  columnName: string,
): Promise<{ column: string; values: string[] }> => {
  const res = await axiosInstance.get('/call-log/filter-values', {
    params: { column_name: columnName },
  });
  return res.data;
};

export const getCallLogById = async (callId: string): Promise<CallLogRow> => {
  const res = await axiosInstance.get(`/call-log/${callId}`);
  return res.data;
};

export const getCallLogAudioUrl = async (callId: string): Promise<string> => {
  const res = await axiosInstance.get(`/call-log/${callId}/audio-url`);
  return res.data.url;
};

export const getCallToolExecutions = async (
  callId: string,
  query?: ToolExecutionsQuery,
): Promise<ToolExecution[]> => {
  const res = await axiosInstance.get(`/call-log/${callId}/tool-executions`, { params: query });
  return res.data;
};
