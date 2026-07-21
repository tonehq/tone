import type {
  CreateOutboundCallPayload,
  CreateOutboundCallResponse,
  ScheduledCallRow,
  ScheduledCallsQueryParams,
} from '@/types/outboundCall';
import axiosInstance from '@/utils/axios';

export const createOutboundCall = async (
  payload: CreateOutboundCallPayload,
): Promise<CreateOutboundCallResponse> => {
  const res = await axiosInstance.post('/outbound-call/create', payload);
  return res.data;
};

/**
 * Place/queue outbound calls from an uploaded CSV/Excel of numbers. The file is parsed
 * SERVER-SIDE (the browser never reads it); `formData` carries `agent_id`, optional
 * `from_number` / `scheduled_at`, and `file`.
 */
export const createOutboundCallFromFile = async (
  formData: FormData,
): Promise<CreateOutboundCallResponse> => {
  // Override the instance's default `application/json` Content-Type so axios sends real
  // multipart/form-data (with the boundary) — otherwise the File is JSON-serialized to `{}`.
  const res = await axiosInstance.post('/outbound-call/create-from-file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export interface OutboundConcurrencyMax {
  /** Env ceiling the per-batch selector is capped to and defaults to; null = no upper bound. */
  max: number | null;
}

export const getOutboundConcurrencyMax = async (): Promise<OutboundConcurrencyMax> => {
  const res = await axiosInstance.get('/outbound-call/concurrency-max');
  return res.data;
};

export const getScheduledCalls = async (
  params: ScheduledCallsQueryParams,
): Promise<{ data: ScheduledCallRow[]; total: number }> => {
  const res = await axiosInstance.post('/outbound-call/scheduled/list', params);
  return res.data;
};

export const cancelScheduledCall = async (id: string): Promise<ScheduledCallRow> => {
  const res = await axiosInstance.post(`/outbound-call/scheduled/${id}/cancel`);
  return res.data;
};

export const cancelScheduledCalls = async (
  ids: string[],
): Promise<{
  canceled: number;
  canceled_ids: string[];
  skipped: { id: string; error: string }[];
}> => {
  const res = await axiosInstance.post('/outbound-call/scheduled/bulk-cancel', { ids });
  return res.data;
};
