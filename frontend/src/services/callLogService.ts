import type { CallLogQueryParams } from '@/types/callLog';
import axiosInstance from '@/utils/axios';

export const getCallLogs = async (params: CallLogQueryParams) => {
  const res = await axiosInstance.get('/call-log/list', { params });
  return res.data;
};
