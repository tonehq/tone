'use client';

import { AxisBarChart } from './AxisBarChart';
import { LatencyStatChips, type StatKey, useLatencyStats } from './LatencyStatChips';

interface LatencyAxisChartProps {
  latencies: number[];
}

const DEFAULT_VISIBLE_STATS: readonly StatKey[] = ['avg', 'min'];

const formatChipSeconds = (v: number) => `${v.toFixed(3)}s`;
const formatAxisSeconds = (v: number) => `${v.toFixed(2)}s`;

export function LatencyAxisChart({ latencies }: LatencyAxisChartProps) {
  const { stats, sampleCount, visible, toggle, buildReferenceLines } = useLatencyStats(latencies, {
    defaultVisible: DEFAULT_VISIBLE_STATS,
  });

  const referenceLines = buildReferenceLines(formatChipSeconds);

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">Latency by measurement</span>
        <span className="text-xs text-muted-foreground">
          {latencies.length} measurement{latencies.length !== 1 ? 's' : ''}
        </span>
      </div>

      <LatencyStatChips
        stats={stats}
        visible={visible}
        onToggle={toggle}
        format={formatChipSeconds}
        disabled={sampleCount === 0}
        ariaLabel="Toggle reference lines"
      />

      <AxisBarChart
        values={latencies}
        formatValue={formatAxisSeconds}
        xAxisLabel="Measurement"
        referenceLines={referenceLines}
      />
    </div>
  );
}
