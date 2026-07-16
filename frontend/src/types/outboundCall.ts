export interface CreateOutboundCallPayload {
  agent_id: string;
  from_number: string;
  /** One or many destinations (bulk / CSV). */
  to_numbers: string[];
  scheduled_at?: string | null;
}

/** Response from POST /outbound-call/create. `mode` says whether it dialed now or queued. */
export interface CreateOutboundCallResponse {
  mode: 'immediate' | 'scheduled' | 'bulk';
  status?: string | null;
  count?: number;
  invalid?: { to_number: string; error: string }[];
}

export type ScheduledCallStatus =
  | 'scheduled'
  | 'processing'
  | 'dispatched'
  | 'completed'
  | 'busy'
  | 'no_answer'
  | 'failed'
  | 'canceled';

export interface ScheduledCallRow {
  id: string;
  agent_id: string;
  agent_name: string | null;
  status: ScheduledCallStatus | null;
  from_number: string | null;
  to_number: string | null;
  scheduled_at: string | null;
  provider_call_sid: string | null;
  call_id: string | null;
  error: string | null;
  created_at: string | null;
}

export interface ScheduledCallFilter {
  field: string;
  operator?: string;
  value: unknown;
}

export interface ScheduledCallsQueryParams {
  page_no?: number;
  page_size?: number;
  filters?: ScheduledCallFilter[];
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  start_date_time?: string;
  end_date_time?: string;
}

export interface ScheduledCallsState {
  rows: ScheduledCallRow[];
  total: number;
  loading: boolean;
}
