'use client';

import { CustomButton } from '@/components/shared';
import type { CallMetricsTTFB } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { Zap } from 'lucide-react';
import { useState } from 'react';

import { AxisBarChart, type ReferenceLine } from './AxisBarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { computeMedian, formatMs } from './utils';

interface TTFBSectionProps {
  ttfbByProcessor: Record<string, CallMetricsTTFB[]>;
}

type StatKey = 'avg' | 'median' | 'min' | 'max';

const STAT_META: Record<
  StatKey,
  { label: string; color: NonNullable<ReferenceLine['color']>; dot: string }
> = {
  avg: { label: 'Avg', color: 'violet', dot: 'bg-violet-500' },
  median: { label: 'Median', color: 'sky', dot: 'bg-sky-500' },
  min: { label: 'Min', color: 'emerald', dot: 'bg-emerald-500' },
  max: { label: 'Max', color: 'red', dot: 'bg-red-500' },
};

interface TTFBProcessorCardProps {
  processor: string;
  entries: CallMetricsTTFB[];
}

const TTFB_TABLE_COLUMNS: MetricsTableColumn<CallMetricsTTFB>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  {
    key: 'model',
    header: 'Model',
    align: 'left',
    cell: (row) => row.model ?? <span className="text-muted-foreground">—</span>,
  },
  { key: 'value', header: 'TTFB', align: 'right', cell: (row) => formatMs(row.value) },
];

function TTFBProcessorCard({ processor, entries }: TTFBProcessorCardProps) {
  const values = entries.map((e) => e.value);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const median = computeMedian(values);
  const avg = values.reduce((s, v) => s + v, 0) / values.length;
  const model = entries.find((e) => e.model)?.model;

  const stats: Record<StatKey, number> = { avg, median, min, max };
  // Each processor card holds its own visible-stats set; default is empty
  // (no reference lines) so the chart starts uncluttered.
  const [visible, setVisible] = useState<Set<StatKey>>(() => new Set());
  const { view, toggle: viewToggle } = useChartTableView('chart', `${processor} view`);

  const toggle = (key: StatKey) =>
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const referenceLines: ReferenceLine[] = (Object.keys(STAT_META) as StatKey[])
    .filter((key) => visible.has(key))
    .map((key) => ({
      value: stats[key],
      label: `${STAT_META[key].label} ${formatMs(stats[key])}`,
      color: STAT_META[key].color,
    }));

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <span className="text-sm font-medium text-foreground">{processor}</span>
          {model && <span className="ml-2 text-xs text-muted-foreground">{model}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {entries.length} sample{entries.length !== 1 ? 's' : ''}
          </span>
          {viewToggle}
        </div>
      </div>
      {view === 'chart' ? (
        <>
          <div
            role="group"
            aria-label="Toggle reference lines"
            className="mb-3 flex flex-wrap gap-1.5"
          >
            {(Object.keys(STAT_META) as StatKey[]).map((key) => {
              const meta = STAT_META[key];
              const isOn = visible.has(key);
              return (
                <CustomButton
                  key={key}
                  type="text"
                  size="sm"
                  onClick={() => toggle(key)}
                  aria-pressed={isOn}
                  className={cn(
                    'h-auto items-start gap-1.5 rounded-md border border-transparent px-2 py-1 transition',
                    isOn
                      ? 'bg-muted/40 hover:bg-muted/60'
                      : 'opacity-50 hover:opacity-100 hover:bg-muted/40',
                  )}
                >
                  <span className="flex flex-col items-start gap-0.5">
                    <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                      <span
                        className={cn(
                          'inline-block size-1.5 rounded-full',
                          meta.dot,
                          !isOn && 'opacity-40',
                        )}
                      />
                      {meta.label}
                    </span>
                    <span className="text-sm font-semibold text-foreground">
                      {formatMs(stats[key])}
                    </span>
                  </span>
                </CustomButton>
              );
            })}
          </div>
          <AxisBarChart
            values={values}
            formatValue={formatMs}
            xAxisLabel="Sample"
            referenceLines={referenceLines}
          />
        </>
      ) : (
        <MetricsDataTable columns={TTFB_TABLE_COLUMNS} rows={entries} />
      )}
    </div>
  );
}

export function TTFBSection({ ttfbByProcessor }: TTFBSectionProps) {
  return (
    <div className="space-y-3">
      <SectionHeader icon={Zap} title="Time to First Byte (TTFB)" />
      <div className="space-y-2">
        {Object.entries(ttfbByProcessor).map(([processor, entries]) => (
          <TTFBProcessorCard key={processor} processor={processor} entries={entries} />
        ))}
      </div>
    </div>
  );
}
