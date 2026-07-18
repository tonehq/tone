import type { CallMetricsProcessing, CallMetricsTurnMetric } from '@/types/callLog';

export const BAR_CHART_MAX_HEIGHT = 50;

export interface ProcessorGroup {
  model: string;
  entries: number[];
}

export function formatMs(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0ms';
  return `${Math.round(seconds * 1000).toLocaleString()}ms`;
}

/**
 * Format an audio duration (ms) for display. Voice-agent durations span
 * ~100ms (single utterance) to several minutes (full call), so unit pick:
 *   - `Xms` for sub-second values (rare; very short utterances)
 *   - `X.Xs` for sub-minute values (typical per-utterance + short totals)
 *   - `Xm Ys` for >= 60s (whole-call totals).
 */
export function formatAudioMs(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '0s';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  // Round to whole seconds first, then split into m/s. Splitting before
  // rounding can land on remSec=60 (e.g. 119.5s → floor()→1m + round(59.5)→60s
  // → "1m 60s") which is malformed.
  const totalSec = Math.round(seconds);
  const minutes = Math.floor(totalSec / 60);
  const remSec = totalSec - minutes * 60;
  return `${minutes}m ${remSec}s`;
}

export function extractProcessorName(processor: string): string {
  return processor.replace(/#\d+$/, '');
}

export function groupByProcessor(entries: CallMetricsProcessing[]): Record<string, ProcessorGroup> {
  return entries.reduce(
    (acc, p) => {
      const key = extractProcessorName(p.processor);
      if (!acc[key]) acc[key] = { model: p.model!, entries: [] };
      acc[key].entries.push(p.value);
      return acc;
    },
    {} as Record<string, ProcessorGroup>,
  );
}

export function computeMedian(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

// Linear-interpolation percentile (matches numpy's default + the backend
// _percentile helper). With small N — typical for a single call — p99
// collapses to max.
export function computePercentile(values: number[], q: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  if (sorted.length === 1) return sorted[0];
  const rank = q * (sorted.length - 1);
  const lo = Math.floor(rank);
  const hi = Math.min(lo + 1, sorted.length - 1);
  const frac = rank - lo;
  return sorted[lo] + (sorted[hi] - sorted[lo]) * frac;
}

export interface LatencyTone {
  text: string;
  bar: string;
}

/**
 * True if a turn has at least one real measurement in any pipeline stage.
 *
 * The pipecat `turn_metrics` array can include "shell" entries with no useful
 * data — typically the pre/inter-turn bucket (turn 0) which only carries
 * system events. Those should be hidden from every per-turn view.
 *
 * Everything else is kept, including:
 *   • the agent's first greeting — has LLM + TTS but no STT, no end_to_end
 *     (the bot spoke first, so there is no user→bot gap to measure)
 *   • a final partial / abandoned turn — may only have STT or only end_to_end
 *
 * Per-metric cards then show "X of Y turns" where Y is the count below and X
 * is the number of those turns that actually had a value for that metric.
 */
export function turnHasAnyMeasurement(t: CallMetricsTurnMetric): boolean {
  const hasSample = (arr: readonly (number | null)[] | null | undefined): boolean =>
    (arr ?? []).some((v) => v != null && v > 0);
  return (
    t.end_to_end != null ||
    hasSample(t.llm_ttfb_all) ||
    hasSample(t.stt_ttfb_all) ||
    hasSample(t.tts_ttfb_all)
  );
}

// Semantic thresholds for end-to-end user→bot latency (in seconds).
// Used by every latency view (chart, table, cards) to keep the bands aligned.
export function latencyTone(seconds: number): LatencyTone {
  if (seconds < 3) {
    return {
      text: 'text-emerald-600 dark:text-emerald-400',
      bar: 'bg-emerald-500',
    };
  }
  if (seconds < 7) {
    return {
      text: 'text-amber-600 dark:text-amber-400',
      bar: 'bg-amber-500',
    };
  }
  return {
    text: 'text-red-600 dark:text-red-400',
    bar: 'bg-red-500',
  };
}
