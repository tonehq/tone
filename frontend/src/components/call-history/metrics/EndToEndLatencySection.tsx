'use client';

import type { CallMetricsLatency } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { Activity } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import { LatencyAxisChart } from './LatencyAxisChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { latencyTone } from './utils';

interface EndToEndLatencySectionProps {
  latencies: CallMetricsLatency[];
}

interface LatencyRow {
  index: number;
  latency: number;
  isMin: boolean;
  isMax: boolean;
}

const TABLE_COLUMNS: MetricsTableColumn<LatencyRow>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (row) => row.index + 1 },
  {
    key: 'measurement',
    header: 'Measurement',
    align: 'left',
    cell: (row) => (
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="font-medium text-foreground">Measurement {row.index + 1}</span>
        {row.isMin && (
          <Badge
            variant="secondary"
            className="border-emerald-500/30 bg-emerald-500/15 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-300"
          >
            Min
          </Badge>
        )}
        {row.isMax && (
          <Badge
            variant="secondary"
            className="border-red-500/30 bg-red-500/15 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wide text-red-700 dark:text-red-300"
          >
            Max
          </Badge>
        )}
      </div>
    ),
  },
  {
    key: 'latency',
    header: 'Latency',
    align: 'right',
    cell: (row) => (
      <span className={cn('font-semibold', latencyTone(row.latency).text)}>
        {row.latency.toFixed(3)}s
      </span>
    ),
  },
];

export function EndToEndLatencySection({ latencies }: EndToEndLatencySectionProps) {
  const values = latencies.map((l) => l.latency);
  const max = Math.max(...values, 0);
  const min = Math.min(...values);
  const hasMultiple = values.length > 1;
  const { view, toggle } = useChartTableView('chart', 'End-to-end latency view');

  const rows: LatencyRow[] = latencies.map((l, i) => ({
    index: i,
    latency: l.latency,
    isMin: hasMultiple && l.latency === min,
    isMax: hasMultiple && l.latency === max,
  }));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <SectionHeader icon={Activity} title="End-to-End Latency" />
        {hasMultiple && toggle}
      </div>
      {!hasMultiple || view === 'table' ? (
        <MetricsDataTable columns={TABLE_COLUMNS} rows={rows} />
      ) : (
        <LatencyAxisChart latencies={values} />
      )}
    </div>
  );
}
