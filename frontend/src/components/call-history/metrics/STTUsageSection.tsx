'use client';

import type { CallMetricsSTTUsage } from '@/types/callLog';
import { AudioLines } from 'lucide-react';

import { BarChart } from './BarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { BAR_CHART_MAX_HEIGHT, formatAudioMs } from './utils';

interface STTUsageSectionProps {
  sttUsage: CallMetricsSTTUsage[];
  totalAudioMs: number;
}

const STT_TABLE_COLUMNS: MetricsTableColumn<CallMetricsSTTUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  { key: 'model', header: 'Model', align: 'left', cell: (row) => row.model ?? '-' },
  {
    key: 'audio',
    header: 'Audio',
    align: 'right',
    cell: (row) => formatAudioMs(row.audio_ms),
  },
];

export function STTUsageSection({ sttUsage, totalAudioMs }: STTUsageSectionProps) {
  // Long calls can produce many short utterances; cap the chart at 20 to match
  // the TTS section's behavior. The table view still shows everything.
  const displayChunks = sttUsage.length > 20 ? sttUsage.slice(0, 20) : sttUsage;
  const displayMs = displayChunks.map((u) => u.audio_ms);
  const maxMs = Math.max(...displayMs);
  const avgMs = sttUsage.length > 0 ? totalAudioMs / sttUsage.length : 0;
  const { view, toggle } = useChartTableView('chart', 'STT usage view');

  return (
    <div className="space-y-3">
      <SectionHeader icon={AudioLines} title="STT Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-foreground">{sttUsage[0].model ?? '-'}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {sttUsage.length} utterance{sttUsage.length !== 1 ? 's' : ''}
            </span>
            {toggle}
          </div>
        </div>
        {view === 'chart' ? (
          <>
            <BarChart
              values={displayMs}
              maxValue={maxMs}
              maxHeight={BAR_CHART_MAX_HEIGHT}
              color="bg-cyan-500/70 hover:bg-cyan-500"
              getTooltip={(v) => formatAudioMs(v)}
            />
            {sttUsage.length > 20 && (
              <p className="mt-1 text-[10px] text-muted-foreground">
                Showing first 20 of {sttUsage.length} utterances
              </p>
            )}
          </>
        ) : (
          <MetricsDataTable columns={STT_TABLE_COLUMNS} rows={sttUsage} />
        )}
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
      </div>
    </div>
  );
}
