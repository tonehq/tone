import type { CallLogQueryParams, CallLogRow } from '@/types/callLog';
import axiosInstance from '@/utils/axios';

export const getCallLogs = async (params: CallLogQueryParams) => {
  const res = await axiosInstance.post('/call-log/list', params);
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

export const getCallLogById = async (callId: number): Promise<CallLogRow> => {
  const res = await axiosInstance.get(`/call-log/${callId}`);
  return res.data;
};

export const getCallLogAudioUrl = async (callId: number): Promise<string> => {
  const res = await axiosInstance.get(`/call-log/${callId}/audio-url`);
  return res.data.url;
};
