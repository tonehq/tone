import type { CallMetricsProcessing } from '@/types/callLog';

export const BAR_CHART_MAX_HEIGHT = 50;

export interface ProcessorGroup {
  model: string;
  entries: number[];
}

export function formatMs(seconds: number): string {
  if (seconds < 0.001) return '< 1ms';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  return `${seconds.toFixed(2)}s`;
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
