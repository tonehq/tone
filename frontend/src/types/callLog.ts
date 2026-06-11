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

export interface CallMetricsTurnMetric {
  turn: number;
  status: string;
  duration: number | null;
  started_at: number | null;
  user_stopped_at: number | null;
  bot_started_at: number | null;
  end_to_end: number | null;
  stt_ttfb: number | null;
  llm_ttfb: number | null;
  tts_ttfb: number | null;
  stt_ttfb_all: number[];
  llm_ttfb_all: number[];
  tts_ttfb_all: number[];
  llm_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
  tts_characters: number | null;
}

export interface CallMetrics {
  ttfb: CallMetricsTTFB[];
  turns: CallMetricsTurn[];
  llm_usage: CallMetricsLLMUsage[];
  tts_usage: CallMetricsTTSUsage[];
  processing: CallMetricsProcessing[];
  user_bot_latency: CallMetricsLatency[];
  /**
   * Per-turn aggregated latency rows produced by the backend
   * `MetricsCollectorProcessor`. Optional — rows persisted before the
   * `turn_metrics` column existed will return `null`/missing.
   */
  turn_metrics?: CallMetricsTurnMetric[] | null;
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
  /**
   * Length of the encoded MP3 recording in seconds. Differs from
   * `duration_seconds` (wall-clock incl. pipeline setup + R2 upload) and
   * matches what the audio player plays. Falls back to `duration_seconds`
   * when no recording exists.
   */
  recording_duration_seconds: number | null;
  from_number: string | null;
  to_number: string | null;
  provider_call_id: string | null;
  trace_id: string | null;
  recording_upload_id: string | null;
  transcript: Array<{ role: string; text: string; timestamp?: string }> | null;
  tool_calls: Array<Record<string, unknown>> | null;
  /**
   * 1:1 join from `call_metrics` — `null` when no metrics record exists for this call.
   * The dedicated `/call-metrics/{call_id}` endpoint is still available for
   * single-call detail fetches; this field just lets the list response carry
   * the full payload without a second round-trip.
   */
  metrics: (CallMetrics & { id: string }) | null;
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

/** A single faceted value + its count, from `POST /call-log/facets`. */
export interface FacetValue {
  value: string;
  count: number;
}

/** Map of facet field → its values with counts (e.g. `{ status: [{value, count}] }`). */
export type CallFacets = Record<string, FacetValue[]>;

export interface CallFacetsParams {
  start_date_time?: string;
  end_date_time?: string;
  filters?: CallLogFilterParam[];
}

export interface CallFacetsState {
  facets: CallFacets;
  loading: boolean;
}
