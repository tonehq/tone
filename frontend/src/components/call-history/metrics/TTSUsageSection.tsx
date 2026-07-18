'use client';

import type { CallMetricsTTSUsage, CallMetricsTurnMetric } from '@/types/callLog';
import { Mic } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AxisBarChart } from './AxisBarChart';
import { CollapsibleCard } from './CollapsibleCard';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { SortToggle, type SortDirection } from './SortToggle';
import { StackedCallsBarChart } from './StackedCallsBarChart';
import { buildPerTurnUsageRows, TurnUsageTable } from './TurnUsageCard';
import { useChartTableView } from './useChartTableView';

interface TTSUsageSectionProps {
  ttsUsage: CallMetricsTTSUsage[];
  totalChars: number;
  turns: CallMetricsTurnMetric[];
}

const TTS_TABLE_COLUMNS: MetricsTableColumn<CallMetricsTTSUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  {
    key: 'chars',
    header: 'Characters',
    align: 'right',
    cell: (row) => row.characters.toLocaleString(),
  },
];

const formatChars = (v: number) => `${Math.round(v).toLocaleString()} chars`;

export function TTSUsageSection({ ttsUsage, totalChars, turns }: TTSUsageSectionProps) {
  const { view, toggle } = useChartTableView('chart', 'TTS usage view');
  const [sort, setSort] = useState<SortDirection>('natural');

  // Per-turn rows from `turn_metrics.tts_usage_all`. When present, the chart
  // becomes a per-turn stacked bar (one segment per TTS call inside the
  // turn — typically multiple per turn because TTS splits by sentence).
  const perTurn = useMemo(() => {
    const { rows, hasAny } = buildPerTurnUsageRows<CallMetricsTTSUsage>(
      turns,
      (t) => t.tts_usage_all,
      (c) => c.characters,
    );
    const displayRows =
      sort === 'natural'
        ? rows
        : [...rows].sort((a, b) => (sort === 'asc' ? a.total - b.total : b.total - a.total));
    return {
      rows: displayRows,
      hasAny,
      sampleCount: displayRows.filter((r) => r.total > 0).length,
      stacks: displayRows.map((r) => r.values),
      turnLabels: displayRows.map((r) => r.turnLabel),
    };
  }, [turns, sort]);
  const { rows: perTurnRows, hasAny: hasPerTurnUsage } = perTurn;

  // Legacy per-chunk chart values — first 20 chunks. Sort when requested.
  const legacyChunkValues = useMemo(() => {
    const values = ttsUsage.slice(0, 20).map((u) => u.characters);
    if (sort === 'natural') return values;
    return [...values].sort((a, b) => (sort === 'asc' ? a - b : b - a));
  }, [ttsUsage, sort]);

  const renderBody = () => {
    if (hasPerTurnUsage) {
      return view === 'chart' ? (
        <StackedCallsBarChart
          stacks={perTurn.stacks}
          formatValue={formatChars}
          xAxisLabel="Turn"
          xLabels={perTurn.turnLabels}
        />
      ) : (
        <TurnUsageTable rows={perTurnRows} columnHeader="TTS Usage" format={formatChars} />
      );
    }
    if (view === 'chart') {
      return (
        <>
          <AxisBarChart
            values={legacyChunkValues}
            formatValue={(v) => `${v.toLocaleString()}`}
            xAxisLabel="Chunk"
          />
          {ttsUsage.length > 20 && (
            <p className="mt-1 text-[10px] text-muted-foreground">
              Showing first 20 of {ttsUsage.length} chunks
            </p>
          )}
        </>
      );
    }
    return <MetricsDataTable columns={TTS_TABLE_COLUMNS} rows={ttsUsage} />;
  };

  return (
    <CollapsibleCard
      title={<SectionHeader icon={Mic} title="TTS Usage" />}
      actions={
        <>
          <span className="text-xs text-muted-foreground">
            {hasPerTurnUsage
              ? `${perTurn.sampleCount} of ${perTurnRows.length} turn${perTurnRows.length !== 1 ? 's' : ''}`
              : `${ttsUsage.length} chunk${ttsUsage.length !== 1 ? 's' : ''}`}
          </span>
          <SortToggle value={sort} onChange={setSort} label="Sort TTS usage by total" />
          {toggle}
        </>
      }
    >
      {renderBody()}
      <div className="mt-2 flex gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Total</p>
          <p className="text-sm font-semibold text-foreground">
            {totalChars.toLocaleString()} chars
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg / chunk</p>
          <p className="text-sm font-semibold text-foreground">
            {ttsUsage.length > 0
              ? `${Math.round(totalChars / ttsUsage.length).toLocaleString()} chars`
              : '—'}
          </p>
        </div>
      </div>
    </CollapsibleCard>
  );
}
