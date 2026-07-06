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
  /** Optional — present on rows persisted with cache-aware providers. */
  cache_read_input_tokens?: number | null;
  cache_creation_input_tokens?: number | null;
  reasoning_tokens?: number | null;
}

export interface CallMetricsTTSUsage {
  model: string;
  processor: string;
  characters: number;
}

export interface CallMetricsSTTUsage {
  model: string | null;
  processor: string;
  audio_ms: number;
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
  stt_audio_ms: number | null;
  /**
   * Per-call usage breakdown within the turn — mirrors the `*_ttfb_all`
   * pattern. Optional: missing on rows persisted before per-call usage was
   * being collected. Each array has one entry per individual service call
   * inside the turn.
   */
  llm_usage_all?: CallMetricsLLMUsage[] | null;
  tts_usage_all?: CallMetricsTTSUsage[] | null;
  stt_usage_all?: CallMetricsSTTUsage[] | null;
}

export interface CallMetrics {
  ttfb: CallMetricsTTFB[];
  turns: CallMetricsTurn[];
  llm_usage: CallMetricsLLMUsage[];
  tts_usage: CallMetricsTTSUsage[];
  /**
   * Per-utterance STT audio duration (ms). Optional — rows persisted
   * before the `stt_usage` column existed will return `null`/missing.
   */
  stt_usage?: CallMetricsSTTUsage[] | null;
  processing: CallMetricsProcessing[];
  user_bot_latency: CallMetricsLatency[];
  /**
   * Per-turn aggregated latency rows produced by the backend
   * `MetricsCollectorProcessor`. Optional — rows persisted before the
   * `turn_metrics` column existed will return `null`/missing.
   */
  turn_metrics?: CallMetricsTurnMetric[] | null;
}

export interface ServedBy {
  deployment?: string;
  pod?: string;
  node?: string;
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
  served_by: ServedBy | null;
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

export type ToolExecutionStatus = 'success' | 'error';

export type ToolExecutionType =
  | 'custom'
  | 'send_sms'
  | 'google_calendar'
  | 'read_document'
  | 'built_in'
  | 'mcp';

/** One row from `tool_executions` — one tool/MCP invocation during a call.
 *  The `tool_*` and `mcp_server_*` fields are joined in at read time from the
 *  source `tools` / `mcp_servers` tables (LEFT JOIN on FK id). They are
 *  optional: NULL for code-defined built-ins, pre-FK rows, and rows whose
 *  source has since been deleted (ON DELETE SET NULL). */
export interface ToolExecution {
  id: string;
  call_id: string | null;
  agent_id: string | null;
  tool_name: string;
  tool_type: ToolExecutionType | string | null;
  mcp_server_name: string | null;
  tool_id: string | null;
  mcp_server_id: string | null;
  arguments: unknown;
  result: unknown;
  status: ToolExecutionStatus | string | null;
  error_message: string | null;
  status_code: number | null;
  duration_ms: number | null;
  turn_number: number | null;
  started_at: string | null;
  meta_data: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
  // Joined from `tools`
  tool_description?: string | null;
  tool_url?: string | null;
  tool_method?: string | null;
  tool_auth_type?: string | null;
  tool_is_active?: boolean | null;
  // Joined from `mcp_servers`
  mcp_server_description?: string | null;
  mcp_server_url?: string | null;
  mcp_server_transport?: string | null;
  mcp_server_is_active?: boolean | null;
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
