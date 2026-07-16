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
  pod?: string;
  ordinal?: number;
  node?: string;
  environment?: string;
}

/**
 * One service (LLM / STT / TTS) inside the call's pipeline snapshot. Each field
 * that has a raw id and a human-readable form carries both: `provider_name` is
 * the provider slug (call filters key off it) with `provider_display_name` for
 * the UI; the TTS spec adds `voice_id` + `voice_name` and `language` (code) +
 * `language_display`. The display fields are present only for calls placed after
 * the snapshot started capturing them, so the UI falls back to the raw value.
 */
export interface PipelineSpecSnapshot {
  provider_name: string | null;
  provider_display_name?: string | null;
  model_name: string | null;
  model_id: string | null;
  voice_id?: string | null;
  voice_name?: string | null;
  language?: string | null;
  language_display?: string | null;
}

/**
 * Immutable snapshot of the pipeline used for a single call, captured at call
 * start and stored on the call row. This — NOT the live agent config — is the
 * source of truth for the Call Configurations tab, so editing the agent later
 * never rewrites what a past call shows.
 */
export interface PipelineConfigSnapshot {
  llm: PipelineSpecSnapshot | null;
  stt: PipelineSpecSnapshot | null;
  tts: PipelineSpecSnapshot | null;
  is_s2s?: boolean;
  custom_tools?: Array<{ id: string | null; name: string | null }>;
  mcp_servers?: unknown[];
  knowledge_bases?: unknown[];
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
  /**
   * Immutable snapshot of the pipeline used for THIS call (provider/model, plus
   * voice/language on newer calls), captured at call start. Null for very old
   * calls persisted before snapshots existed. Drives the Configurations tab so
   * it reflects what the call actually used — not the agent's current config.
   */
  pipeline_config: PipelineConfigSnapshot | null;
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

// -----------------------------------------------------------------------------
// Metrics summary (POST /call-log/metrics-summary) — 2-step nested aggregation
// over the same filter scope the table is showing. See backend
// ``CallMetricsAnalyticsService`` for the math.
// -----------------------------------------------------------------------------

/** Aggregate stats over a list of per-call values (rowKey => this block). */
export interface MetricsSummaryStatBlock {
  avg: number | null;
  p50: number | null;
  p99: number | null;
}

export interface MetricsSummarySeries {
  unit: 'ms' | 's';
  /** Number of calls that contributed at least one positive sample to this series. */
  call_sample_count: number;
  /**
   * 3×3 grid keyed as ``per_call[rowStat][colStat]``.
   *   row = the per-call stat computed first (over that call's turn samples)
   *   col = the across-call aggregate then applied to the list of per-call stats
   * e.g. ``per_call.p99.p50`` = median of the per-call p99s ("typical call's worst turn").
   */
  per_call: {
    avg: MetricsSummaryStatBlock;
    p50: MetricsSummaryStatBlock;
    p99: MetricsSummaryStatBlock;
  };
}

export type MetricsSummarySeriesKey = 'llm_ttfb' | 'stt_ttfb' | 'tts_ttfb' | 'end_to_end_latency';

export interface MetricsSummary {
  call_count: number;
  calls_with_metrics: number;
  series: Record<MetricsSummarySeriesKey, MetricsSummarySeries>;
}

export interface MetricsSummaryParams {
  start_date_time?: string;
  end_date_time?: string;
  filters?: CallLogFilterParam[];
}

export interface MetricsSummaryState {
  data: MetricsSummary | null;
  loading: boolean;
}
