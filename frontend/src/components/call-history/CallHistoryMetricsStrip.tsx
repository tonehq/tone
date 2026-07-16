'use client';

import { CustomButton } from '@/components/shared';
import type { MetricsSummary, MetricsSummarySeries } from '@/types/callLog';
import { Gauge, X } from 'lucide-react';
import React from 'react';

interface CallHistoryMetricsStripProps {
  data: MetricsSummary | null;
  loading: boolean;
  onDismiss: () => void;
}

// The four values we surface, in render order. Each slot maps directly to a
// coordinate in ``series.per_call`` — the frontend just navigates the grid,
// so adding/reordering values is a one-line change.
//
// Row = the per-call stat computed over that call's turns.
// Col = the across-call aggregate applied to the list of per-call stats.
// Example: ``{ row: 'p99', col: 'p50' }`` reads as "median of the per-call
// p99s" — the *typical* call's *worst* turn.
type StatKey = 'p50' | 'p99';
interface SummarySlot {
  label: string;
  row: StatKey;
  col: StatKey;
}

const SLOTS: SummarySlot[] = [
  { label: 'p50 of p50s', row: 'p50', col: 'p50' },
  { label: 'p99 of p50s', row: 'p50', col: 'p99' },
  { label: 'p50 of p99s', row: 'p99', col: 'p50' },
  { label: 'p99 of p99s', row: 'p99', col: 'p99' },
];

function formatValue(value: number | null, unit: 'ms' | 's'): string {
  if (typeof value !== 'number') return '-';
  if (unit === 'ms') return `${Math.round(value).toLocaleString()} ms`;
  return `${value.toFixed(2)} s`;
}

const Slot: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex flex-col">
    <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
    <span className="text-sm font-semibold tabular-nums text-foreground">{value}</span>
  </div>
);

/**
 * Compact strip under the Call History search bar showing four nested
 * end-to-end latency aggregates for the current filter scope. Pure component —
 * fetching + visibility live in the parent so this stays trivially reusable.
 */
const CallHistoryMetricsStrip: React.FC<CallHistoryMetricsStripProps> = ({
  data,
  loading,
  onDismiss,
}) => {
  const series: MetricsSummarySeries | null = data?.series.end_to_end_latency ?? null;

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-border bg-muted/30 px-4 py-3">
      <div className="flex items-center gap-2">
        <Gauge className="size-4 text-violet-500" />
        <span className="text-sm font-medium text-foreground">End-to-end latency</span>
      </div>

      <div className="hidden h-6 w-px bg-border sm:block" />

      {loading && !series ? (
        <span className="text-xs text-muted-foreground">Loading…</span>
      ) : series ? (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {SLOTS.map(({ label, row, col }) => (
            <Slot
              key={label}
              label={label}
              value={formatValue(series.per_call[row][col], series.unit)}
            />
          ))}
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">No metrics for this filter scope.</span>
      )}

      <CustomButton
        type="text"
        size="sm"
        className="ml-auto"
        icon={<X className="size-4" />}
        aria-label="Hide metrics"
        onClick={onDismiss}
      />
    </div>
  );
};

export default CallHistoryMetricsStrip;
