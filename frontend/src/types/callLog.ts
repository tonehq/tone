export interface CallLogRow {
  id: number;
  uuid: string;
  agent_id: number;
  agent_name: string;
  agent_type: string;
  started_at: number;
  ended_at: number | null;
  duration_seconds: number | null;
  transcript: Array<{ role: string; text: string; timestamp?: string }> | null;
  from_number: string | null;
  to_number: string | null;
  transport_type: string | null;
  status: string;
}

export interface CallLogsState {
  callLogs: CallLogRow[];
  total: number;
  loading: boolean;
}

export interface CallLogFilterParam {
  field: string;
  operator: string;
  value: string | number | (string | number)[];
}

export interface CallLogQueryParams {
  page_no: number;
  page_size: number;
  start_date_time?: number;
  end_date_time?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: string;
}
