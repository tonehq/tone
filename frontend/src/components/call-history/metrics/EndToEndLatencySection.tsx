import type { CallMetricsLatency } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { Activity } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import { LatencyAxisChart } from './LatencyAxisChart';
import { SectionHeader } from './SectionHeader';
import { latencyTone } from './utils';

interface EndToEndLatencySectionProps {
  latencies: CallMetricsLatency[];
}

const ROW_GRID = 'grid-cols-[3rem_minmax(7rem,1fr)_minmax(8rem,2fr)_5.5rem]';

export function EndToEndLatencySection({ latencies }: EndToEndLatencySectionProps) {
  const values = latencies.map((l) => l.latency);
  const max = Math.max(...values, 0);
  const min = Math.min(...values);
  const scale = max > 0 ? max : 1;
  const hasMultiple = values.length > 1;

  return (
    <div className="space-y-3">
      <SectionHeader icon={Activity} title="End-to-End Latency" />
      {hasMultiple && <LatencyAxisChart latencies={values} />}

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div
          className={cn(
            'grid items-center gap-3 border-b border-border bg-muted/40 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground',
            ROW_GRID,
          )}
        >
          <span>#</span>
          <span>Measurement</span>
          <span>Distribution</span>
          <span className="text-right">Latency</span>
        </div>
        <ul className="divide-y divide-border">
          {latencies.map((l, i) => {
            const tone = latencyTone(l.latency);
            const fillPct = Math.max((l.latency / scale) * 100, 2);
            const isMin = hasMultiple && l.latency === min;
            const isMax = hasMultiple && l.latency === max;
            return (
              <li
                key={i}
                className={cn(
                  'grid items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/30',
                  ROW_GRID,
                )}
              >
                <span className="text-sm tabular-nums text-muted-foreground">{i + 1}</span>
                <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                  <span className="truncate text-sm font-medium text-foreground">
                    {hasMultiple ? `Measurement ${i + 1}` : 'Latency'}
                  </span>
                  {isMin && (
                    <Badge
                      variant="secondary"
                      className="border-emerald-500/30 bg-emerald-500/15 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wide text-emerald-700 dark:text-emerald-300"
                    >
                      Min
                    </Badge>
                  )}
                  {isMax && (
                    <Badge
                      variant="secondary"
                      className="border-red-500/30 bg-red-500/15 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wide text-red-700 dark:text-red-300"
                    >
                      Max
                    </Badge>
                  )}
                </div>
                <div className="relative h-2 overflow-hidden rounded-full bg-muted" aria-hidden>
                  <div
                    className={cn('h-full rounded-full opacity-80 transition-all', tone.bar)}
                    style={{ width: `${fillPct}%` }}
                  />
                </div>
                <span className={cn('text-right text-sm font-semibold tabular-nums', tone.text)}>
                  {l.latency.toFixed(3)}s
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
