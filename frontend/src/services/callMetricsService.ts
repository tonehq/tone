import type { CallMetricsDetail } from '@/types/callMetrics';
import axiosInstance from '@/utils/axios';

export const getCallMetricsByCallId = async (
  callId: string,
  options?: { signal?: AbortSignal },
): Promise<CallMetricsDetail> => {
  const res = await axiosInstance.get(`/call-metrics/${callId}`, {
    signal: options?.signal,
  });
  return res.data;
};
