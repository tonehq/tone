import type { CallMetricsTTSUsage } from '@/types/callLog';
import { Mic } from 'lucide-react';

import { BarChart } from './BarChart';
import { SectionHeader } from './SectionHeader';

interface TTSUsageSectionProps {
  ttsUsage: CallMetricsTTSUsage[];
  totalChars: number;
}

export function TTSUsageSection({ ttsUsage, totalChars }: TTSUsageSectionProps) {
  const displayChunks = ttsUsage.length > 20 ? ttsUsage.slice(0, 20) : ttsUsage;
  const maxChars = Math.max(...displayChunks.map((x) => x.characters));

  return (
    <div className="space-y-3">
      <SectionHeader icon={Mic} title="TTS Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">{ttsUsage[0].model}</span>
          <span className="text-xs text-muted-foreground">
            {ttsUsage.length} chunk{ttsUsage.length !== 1 ? 's' : ''}
          </span>
        </div>
        <BarChart
          values={displayChunks.map((u) => u.characters)}
          maxValue={maxChars}
          maxHeight={40}
          color="bg-amber-500/70 hover:bg-amber-500"
          getTooltip={(v) => `${v} chars`}
        />
        {ttsUsage.length > 20 && (
          <p className="mt-1 text-[10px] text-muted-foreground">
            Showing first 20 of {ttsUsage.length} chunks
          </p>
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
