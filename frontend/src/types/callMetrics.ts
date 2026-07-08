import type {
  CallMetrics,
  CallMetricsLatency,
  CallMetricsLLMUsage,
  CallMetricsProcessing,
  CallMetricsSTTUsage,
  CallMetricsTTFB,
  CallMetricsTTSUsage,
  CallMetricsTurn,
} from '@/types/callLog';

export type {
  CallMetrics,
  CallMetricsLatency,
  CallMetricsLLMUsage,
  CallMetricsProcessing,
  CallMetricsSTTUsage,
  CallMetricsTTFB,
  CallMetricsTTSUsage,
  CallMetricsTurn,
};

/**
 * Lightweight per-call summary fields. Reused as the base for
 * `CallMetricsDetail`, which adds the per-sample arrays.
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
  p50_ttfb_ms: number | null;
  p99_ttfb_ms: number | null;
  avg_latency_s: number | null;
  p50_latency_s: number | null;
  p99_latency_s: number | null;
  total_tokens: number | null;
  total_tts_chars: number | null;
  total_stt_audio_ms: number | null;
  turn_count: number | null;
}

/**
 * Full per-call payload returned by `GET /call-metrics/{call_id}`.
 * Extends the list row with the six per-sample arrays — fed to the call-metrics detail page.
 */
export interface CallMetricsDetail extends CallMetricsRow {
  ttfb: CallMetricsTTFB[];
  processing: CallMetricsProcessing[];
  llm_usage: CallMetricsLLMUsage[];
  tts_usage: CallMetricsTTSUsage[];
  stt_usage: CallMetricsSTTUsage[];
  user_bot_latency: CallMetricsLatency[];
  turns: CallMetricsTurn[];
}
