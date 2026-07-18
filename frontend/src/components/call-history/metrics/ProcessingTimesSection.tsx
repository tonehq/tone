'use client';

import type { CallMetricsProcessing } from '@/types/callLog';
import { Clock } from 'lucide-react';
import { useMemo, useState } from 'react';

import { CollapsibleCard } from './CollapsibleCard';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { SortToggle, type SortDirection } from './SortToggle';
import { useChartTableView } from './useChartTableView';
import { formatMs, groupByProcessor } from './utils';

interface ProcessingTimesSectionProps {
  processing: CallMetricsProcessing[];
}

interface ProcessorRow {
  processor: string;
  model: string;
  avg: number;
  total: number;
  calls: number;
}

const TABLE_COLUMNS: MetricsTableColumn<ProcessorRow>[] = [
  { key: 'processor', header: 'Processor', align: 'left', cell: (row) => row.processor },
  {
    key: 'model',
    header: 'Model',
    align: 'left',
    cell: (row) => <span className="text-muted-foreground">{row.model}</span>,
  },
  { key: 'avg', header: 'Avg', align: 'right', cell: (row) => formatMs(row.avg) },
  { key: 'total', header: 'Total', align: 'right', cell: (row) => formatMs(row.total) },
  { key: 'calls', header: 'Calls', align: 'right', cell: (row) => row.calls },
];

interface ProcessingChartProps {
  rows: ProcessorRow[];
}

/**
 * Horizontal bar chart of avg processing time per processor. Rendered as the
 * chart view of ProcessingTimesSection — table view stays in the shared
 * MetricsDataTable. File-local because it has only one consumer.
 */
function ProcessingChart({ rows }: ProcessingChartProps) {
  const max = Math.max(...rows.map((r) => r.avg), 0);
  const scale = max > 0 ? max : 1;
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const widthPct = Math.max((row.avg / scale) * 100, 2);
        return (
          <div key={row.processor} className="space-y-1">
            <div className="flex items-baseline justify-between gap-2 text-xs">
              <span className="truncate font-medium text-foreground">{row.processor}</span>
              <span className="tabular-nums text-muted-foreground">{formatMs(row.avg)} avg</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
              <div
                className="h-full rounded-full bg-primary/60 transition-all"
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ProcessingTimesSection({ processing }: ProcessingTimesSectionProps) {
  const significant = processing.filter((p) => p.model && p.value > 0);
  const { view, toggle } = useChartTableView('table', 'Processing times view');
  const [sort, setSort] = useState<SortDirection>('natural');

  const rows = useMemo<ProcessorRow[]>(() => {
    const grouped = groupByProcessor(significant);
    const base: ProcessorRow[] = Object.entries(grouped).map(([processor, data]) => {
      const total = data.entries.reduce((s, v) => s + v, 0);
      return {
        processor,
        model: data.model,
        avg: total / data.entries.length,
        total,
        calls: data.entries.length,
      };
    });
    if (sort === 'natural') return base;
    return [...base].sort((a, b) => (sort === 'asc' ? a.avg - b.avg : b.avg - a.avg));
  }, [significant, sort]);

  if (significant.length === 0) return null;

  return (
    <CollapsibleCard
      title={<SectionHeader icon={Clock} title="Processing Times" />}
      actions={
        <>
          <SortToggle value={sort} onChange={setSort} label="Sort processors by avg" />
          {toggle}
        </>
      }
    >
      {view === 'chart' ? (
        <ProcessingChart rows={rows} />
      ) : (
        <MetricsDataTable columns={TABLE_COLUMNS} rows={rows} getRowKey={(row) => row.processor} />
      )}
    </CollapsibleCard>
  );
}
