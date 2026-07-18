'use client';

import type { CallMetricsSTTUsage, CallMetricsTurnMetric } from '@/types/callLog';
import { AudioLines } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AxisBarChart } from './AxisBarChart';
import { CollapsibleCard } from './CollapsibleCard';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { SortToggle, type SortDirection } from './SortToggle';
import { StackedCallsBarChart } from './StackedCallsBarChart';
import { buildPerTurnUsageRows, TurnUsageTable } from './TurnUsageCard';
import { useChartTableView } from './useChartTableView';
import { formatAudioMs } from './utils';

interface STTUsageSectionProps {
  sttUsage: CallMetricsSTTUsage[];
  totalAudioMs: number;
  turns: CallMetricsTurnMetric[];
}

const STT_TABLE_COLUMNS: MetricsTableColumn<CallMetricsSTTUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  {
    key: 'audio',
    header: 'Audio',
    align: 'right',
    cell: (row) => formatAudioMs(row.audio_ms),
  },
];

export function STTUsageSection({ sttUsage, totalAudioMs, turns }: STTUsageSectionProps) {
  const avgMs = sttUsage.length > 0 ? totalAudioMs / sttUsage.length : 0;
  const { view, toggle } = useChartTableView('chart', 'STT usage view');
  const [sort, setSort] = useState<SortDirection>('natural');

  // Per-turn rows from `turn_metrics.stt_usage_all`. When present, the chart
  // becomes a per-turn stacked bar (one segment per STT call inside the
  // turn, matching the TTFB chart style). When absent, fall back to flat.
  const perTurn = useMemo(() => {
    const { rows, hasAny } = buildPerTurnUsageRows<CallMetricsSTTUsage>(
      turns,
      (t) => t.stt_usage_all,
      (c) => c.audio_ms,
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

  // Long calls can produce many short utterances; cap the legacy chart at 20
  // to match the TTS section. Table view still shows everything.
  const legacyUtteranceValues = useMemo(() => {
    const values = sttUsage.slice(0, 20).map((u) => u.audio_ms);
    if (sort === 'natural') return values;
    return [...values].sort((a, b) => (sort === 'asc' ? a - b : b - a));
  }, [sttUsage, sort]);

  const renderBody = () => {
    if (hasPerTurnUsage) {
      return view === 'chart' ? (
        <StackedCallsBarChart
          stacks={perTurn.stacks}
          formatValue={formatAudioMs}
          xAxisLabel="Turn"
          xLabels={perTurn.turnLabels}
        />
      ) : (
        <TurnUsageTable rows={perTurnRows} columnHeader="STT Usage" format={formatAudioMs} />
      );
    }
    if (view === 'chart') {
      return (
        <>
          <AxisBarChart
            values={legacyUtteranceValues}
            formatValue={formatAudioMs}
            xAxisLabel="Utterance"
          />
          {sttUsage.length > 20 && (
            <p className="mt-1 text-[10px] text-muted-foreground">
              Showing first 20 of {sttUsage.length} utterances
            </p>
          )}
        </>
      );
    }
    return <MetricsDataTable columns={STT_TABLE_COLUMNS} rows={sttUsage} />;
  };

  return (
    <CollapsibleCard
      title={<SectionHeader icon={AudioLines} title="STT Usage" />}
      actions={
        <>
          <span className="text-xs text-muted-foreground">
            {hasPerTurnUsage
              ? `${perTurn.sampleCount} of ${perTurnRows.length} turn${perTurnRows.length !== 1 ? 's' : ''}`
              : `${sttUsage.length} utterance${sttUsage.length !== 1 ? 's' : ''}`}
          </span>
          <SortToggle value={sort} onChange={setSort} label="Sort STT usage by total" />
          {toggle}
        </>
      }
    >
      {renderBody()}
      <div className="mt-2 flex gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Total</p>
          <p className="text-sm font-semibold text-foreground">{formatAudioMs(totalAudioMs)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Avg / utterance</p>
          <p className="text-sm font-semibold text-foreground">{formatAudioMs(avgMs)}</p>
        </div>
      </div>
    </CollapsibleCard>
  );
}
