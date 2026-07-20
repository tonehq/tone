'use client';

import { BarChart3 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AxisBarChart } from './AxisBarChart';
import { CollapsibleCard } from './CollapsibleCard';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SortToggle, type SortDirection } from './SortToggle';
import { useChartTableView } from './useChartTableView';
import { computePercentile, formatMs } from './utils';

interface EndToEndLatencyPercentileSectionProps {
  /** User-to-bot latencies in seconds, one per turn. */
  latencies: number[];
}

interface PercentileRow {
  bucket: string;
  latency: number;
}

const PERCENTILES: readonly { key: string; q: number }[] = [
  { key: 'p50', q: 0.5 },
  { key: 'p75', q: 0.75 },
  { key: 'p90', q: 0.9 },
  { key: 'p95', q: 0.95 },
  { key: 'p99', q: 0.99 },
];

const TABLE_COLUMNS: MetricsTableColumn<PercentileRow>[] = [
  {
    key: 'bucket',
    header: 'Percentile',
    align: 'left',
    cell: (row) => <span className="font-medium text-foreground">{row.bucket}</span>,
  },
  {
    key: 'latency',
    header: 'Latency',
    align: 'right',
    cell: (row) => <span className="font-semibold">{formatMs(row.latency)}</span>,
  },
];

export function EndToEndLatencyPercentileSection({
  latencies,
}: EndToEndLatencyPercentileSectionProps) {
  const { view, toggle: viewToggle } = useChartTableView('chart', 'Percentile distribution view');
  const [sort, setSort] = useState<SortDirection>('natural');

  const naturalRows: PercentileRow[] = useMemo(
    () =>
      PERCENTILES.map(({ key, q }) => ({
        bucket: key,
        latency: computePercentile(latencies, q),
      })),
    [latencies],
  );

  const rows = useMemo(() => {
    if (sort === 'natural') return naturalRows;
    return [...naturalRows].sort((a, b) =>
      sort === 'asc' ? a.latency - b.latency : b.latency - a.latency,
    );
  }, [naturalRows, sort]);

  if (latencies.length === 0) return null;

  return (
    <CollapsibleCard
      title={
        <div className="flex items-center gap-2">
          <BarChart3 className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            End-to-End Latency Distribution
          </span>
        </div>
      }
      subtitle={`${latencies.length} sample${latencies.length !== 1 ? 's' : ''}`}
      actions={
        <>
          <SortToggle
            value={sort}
            onChange={setSort}
            label="Sort order for percentile distribution"
          />
          {viewToggle}
        </>
      }
    >
      {view === 'chart' ? (
        <AxisBarChart
          values={rows.map((r) => r.latency)}
          xLabels={rows.map((r) => r.bucket)}
          xAxisLabel="Percentile"
          formatValue={formatMs}
        />
      ) : (
        <MetricsDataTable columns={TABLE_COLUMNS} rows={rows} getRowKey={(row) => row.bucket} />
      )}
    </CollapsibleCard>
  );
}
