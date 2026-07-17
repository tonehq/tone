import type { DurationTone } from '@/components/call-history/tools-mcp/helpers';

/**
 * End-to-end latency thresholds for a turn (ms). The Consolidated tab uses a
 * three-band chip: green ≤ 800 (target), amber ≤ 1500 (acceptable), rose above
 * (regression). These bands are UX thresholds and intentionally differ from
 * the tool-execution `formatDuration` bands, which measure a single tool round-
 * trip rather than an entire turn.
 */
export const LATENCY_GOOD_MAX_MS = 800;
export const LATENCY_WARN_MAX_MS = 1500;

/** Bucket a turn's latency into a tone that maps to `durationToneClass`. */
export function turnLatencyTone(ms: number | null | undefined): DurationTone {
  if (ms == null) return 'neutral';
  if (ms <= LATENCY_GOOD_MAX_MS) return 'good';
  if (ms <= LATENCY_WARN_MAX_MS) return 'warn';
  return 'bad';
}

/** Display string for a latency chip — always uses ms below 10s to keep the
 *  chip visually stable, then switches to seconds for very long turns. */
export function formatTurnLatency(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 10_000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}
