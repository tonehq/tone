'use client';

import type { CallMetricsTTSUsage } from '@/types/callLog';
import { Mic } from 'lucide-react';

import { BarChart } from './BarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { BAR_CHART_MAX_HEIGHT } from './utils';

interface TTSUsageSectionProps {
  ttsUsage: CallMetricsTTSUsage[];
  totalChars: number;
}

const TTS_TABLE_COLUMNS: MetricsTableColumn<CallMetricsTTSUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  { key: 'model', header: 'Model', align: 'left', cell: (row) => row.model },
  {
    key: 'chars',
    header: 'Characters',
    align: 'right',
    cell: (row) => row.characters.toLocaleString(),
  },
];

export function TTSUsageSection({ ttsUsage, totalChars }: TTSUsageSectionProps) {
  const displayChunks = ttsUsage.length > 20 ? ttsUsage.slice(0, 20) : ttsUsage;
  const displayChars = displayChunks.map((u) => u.characters);
  const maxChars = Math.max(...displayChars);
  const { view, toggle } = useChartTableView('chart', 'TTS usage view');

  return (
    <div className="space-y-3">
      <SectionHeader icon={Mic} title="TTS Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-foreground">{ttsUsage[0].model}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {ttsUsage.length} chunk{ttsUsage.length !== 1 ? 's' : ''}
            </span>
            {toggle}
          </div>
        </div>
        {view === 'chart' ? (
          <>
            <BarChart
              values={displayChars}
              maxValue={maxChars}
              maxHeight={BAR_CHART_MAX_HEIGHT}
              color="bg-amber-500/70 hover:bg-amber-500"
              getTooltip={(v) => `${v} chars`}
            />
            {ttsUsage.length > 20 && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                Showing first 20 of {ttsUsage.length} chunks
              </p>
            )}
          </>
        ) : (
          <MetricsDataTable columns={TTS_TABLE_COLUMNS} rows={ttsUsage} />
        )}
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
              {Math.round(totalChars / ttsUsage.length)} chars
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
