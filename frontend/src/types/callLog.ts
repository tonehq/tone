export interface CallMetricsTTFB {
  model: string | null;
  value: number;
  processor: string;
}

export interface CallMetricsTurn {
  turn: number;
  status: string;
  duration: number;
}

export interface CallMetricsLLMUsage {
  model: string;
  processor: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface CallMetricsTTSUsage {
  model: string;
  processor: string;
  characters: number;
}

export interface CallMetricsProcessing {
  model: string | null;
  value: number;
  processor: string;
}

export interface CallMetricsLatency {
  latency: number;
}

export interface CallMetrics {
  ttfb: CallMetricsTTFB[];
  turns: CallMetricsTurn[];
  llm_usage: CallMetricsLLMUsage[];
  tts_usage: CallMetricsTTSUsage[];
  processing: CallMetricsProcessing[];
  user_bot_latency: CallMetricsLatency[];
}

export interface CallLogRow {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_type: string;
  direction: string;
  channel_type: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  from_number: string | null;
  to_number: string | null;
  provider_call_id: string | null;
  trace_id: string | null;
  recording_upload_id: string | null;
  transcript: Array<{ role: string; text: string; timestamp?: string }> | null;
  metrics: CallMetrics | null;
  tool_calls: Array<Record<string, unknown>> | null;
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
  start_date_time?: string;
  end_date_time?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: CallLogFilterParam[];
}
