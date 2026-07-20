'use client';

import { Gauge } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AxisBarChart } from './AxisBarChart';
import { CollapsibleCard } from './CollapsibleCard';
import { LatencyStatChips, useLatencyStats } from './LatencyStatChips';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SortToggle, type SortDirection } from './SortToggle';
import { useChartTableView } from './useChartTableView';
import { formatMs } from './utils';

interface UserBotLatencySectionProps {
  /** Per-turn user→bot wall-clock latencies in seconds. */
  latencies: number[];
}

interface UserBotLatencyRow {
  turn: string;
  latency: number;
}

const TABLE_COLUMNS: MetricsTableColumn<UserBotLatencyRow>[] = [
  {
    key: 'turn',
    header: 'Turn',
    align: 'left',
    cell: (row) => <span className="font-medium text-foreground">{row.turn}</span>,
  },
  {
    key: 'latency',
    header: 'Latency',
    align: 'right',
    cell: (row) => <span className="font-semibold">{formatMs(row.latency)}</span>,
  },
];

export function UserBotLatencySection({ latencies }: UserBotLatencySectionProps) {
  const { view, toggle: viewToggle } = useChartTableView('chart', 'User bot latency view');
  const [sort, setSort] = useState<SortDirection>('natural');

  // Drop non-positive values — a 0/null means the observer didn't get a real
  // measurement for that turn (matches TurnLatencySection.cleanSamples).
  const cleaned = useMemo(() => latencies.filter((v) => v > 0), [latencies]);

  const naturalRows = useMemo<UserBotLatencyRow[]>(
    () => cleaned.map((latency, i) => ({ turn: String(i + 1), latency })),
    [cleaned],
  );

  const rows = useMemo(() => {
    if (sort === 'natural') return naturalRows;
    return [...naturalRows].sort((a, b) =>
      sort === 'asc' ? a.latency - b.latency : b.latency - a.latency,
    );
  }, [naturalRows, sort]);

  const { stats, sampleCount, visible, toggle, buildReferenceLines } = useLatencyStats(
    rows.map((r) => r.latency),
  );

  if (cleaned.length === 0) return null;

  return (
    <CollapsibleCard
      title={
        <div className="flex items-center gap-2">
          <Gauge className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">User Bot Latency</span>
        </div>
      }
      subtitle="User stopped speaking → bot started speaking, per turn"
      actions={
        <>
          <span className="text-xs text-muted-foreground">
            {sampleCount} turn{sampleCount !== 1 ? 's' : ''}
          </span>
          <SortToggle value={sort} onChange={setSort} label="Sort order for user bot latency" />
          {viewToggle}
        </>
      }
    >
      {view === 'chart' ? (
        <>
          <LatencyStatChips
            stats={stats}
            visible={visible}
            onToggle={toggle}
            format={formatMs}
            disabled={sampleCount === 0}
            ariaLabel="Toggle reference lines for user bot latency"
          />
          <AxisBarChart
            values={rows.map((r) => r.latency)}
            xLabels={rows.map((r) => r.turn)}
            xAxisLabel="Turn"
            formatValue={formatMs}
            referenceLines={buildReferenceLines(formatMs)}
          />
        </>
      ) : (
        <MetricsDataTable columns={TABLE_COLUMNS} rows={rows} getRowKey={(row) => row.turn} />
      )}
    </CollapsibleCard>
  );
}
