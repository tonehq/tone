import type { CallMetricsDetail, CallMetricsQueryParams } from '@/types/callMetrics';
import axiosInstance from '@/utils/axios';

export const getCallMetrics = async (params: CallMetricsQueryParams) => {
  const res = await axiosInstance.post('/call-metrics/list', params);
  return res.data;
};

export const getCallMetricsByCallId = async (callId: string): Promise<CallMetricsDetail> => {
  const res = await axiosInstance.get(`/call-metrics/${callId}`);
  return res.data;
};
