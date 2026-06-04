import type {
  CallMetrics,
  CallMetricsLatency,
  CallMetricsLLMUsage,
  CallMetricsProcessing,
  CallMetricsTTFB,
  CallMetricsTTSUsage,
  CallMetricsTurn,
} from '@/types/callLog';

export type {
  CallMetrics,
  CallMetricsLatency,
  CallMetricsLLMUsage,
  CallMetricsProcessing,
  CallMetricsTTFB,
  CallMetricsTTSUsage,
  CallMetricsTurn,
};

/**
 * Lightweight summary shape returned by `POST /call-metrics/list`.
 * The per-sample arrays are intentionally absent — they're only fetched
 * on row-click via `GET /call-metrics/{call_id}` (see CallMetricsDetail).
 */
export interface CallMetricsRow {
  id: string;
  call_id: string;
  agent_id: string | null;
  agent_name: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;

  avg_ttfb_ms: number | null;
  avg_latency_s: number | null;
  total_tokens: number | null;
  total_tts_chars: number | null;
  turn_count: number | null;
}

/**
 * Full per-call payload returned by `GET /call-metrics/{call_id}`.
 * Extends the list row with the six per-sample arrays — fed to MetricsModal.
 */
export interface CallMetricsDetail extends CallMetricsRow {
  ttfb: CallMetricsTTFB[];
  processing: CallMetricsProcessing[];
  llm_usage: CallMetricsLLMUsage[];
  tts_usage: CallMetricsTTSUsage[];
  user_bot_latency: CallMetricsLatency[];
  turns: CallMetricsTurn[];
}

export interface CallMetricsState {
  rows: CallMetricsRow[];
  total: number;
  loading: boolean;
}

export interface CallMetricsFilterParam {
  field: string;
  operator: string;
  value: string | number | (string | number)[];
}

export interface CallMetricsQueryParams {
  page_no: number;
  page_size: number;
  start_date_time?: string;
  end_date_time?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: CallMetricsFilterParam[];
}
