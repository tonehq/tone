export interface CreateOutboundCallPayload {
  agent_id: string;
  /** Optional caller-id. Omit to let the backend auto-select the org's configured number. */
  from_number?: string;
  /** One or many destinations (bulk / CSV). */
  to_numbers: string[];
  scheduled_at?: string | null;
  /** Directory the created contacts land in (default the org's "Global" directory). */
  directory_id?: string;
  /** How many of this batch's calls dial at once. Omit → the backend applies the env default. */
  max_concurrency?: number;
  /** Trigger engine: 'twilio'/'telnyx' place a real PSTN call; 'websocket' bridges to a remote
   * /ws/test. Omit to let the from-number's channel pick the telephony engine. */
  provider?: OutboundTriggerProvider;
}

/** How an outbound call is triggered. */
export type OutboundTriggerProvider = 'twilio' | 'telnyx' | 'websocket';

/** Response from POST /outbound-call/create. `mode` says whether it dialed now or queued.
 * `parallel_websocket` is an immediate WebSocket (test-bridge) fan-out — it dials right away. */
export interface CreateOutboundCallResponse {
  mode: 'immediate' | 'scheduled' | 'bulk' | 'parallel_websocket';
  status?: string | null;
  count?: number;
  invalid?: { to_number: string; error: string }[];
}

export type ScheduledCallStatus =
  | 'scheduled'
  | 'processing'
  | 'dispatched'
  | 'in_progress'
  | 'completed'
  | 'busy'
  | 'no_answer'
  | 'failed'
  | 'canceled';

export interface ScheduledCallRow {
  id: string;
  agent_id: string;
  agent_name: string | null;
  contact_id: string | null;
  contact_name: string | null;
  contact_phone_number: string | null;
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
