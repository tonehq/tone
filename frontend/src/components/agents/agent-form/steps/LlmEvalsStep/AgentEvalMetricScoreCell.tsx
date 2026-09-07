'use client';

import { CustomTooltip } from '@/components/shared';
import { cn } from '@/utils/cn';

import { formatDecimal, metricScoreClasses } from './evalMetrics';

interface MetricScore {
  score?: number;
  reason?: string | null;
}

// One metric's score for a scored scenario: a compact score pill colored by the
// score band, revealing the judge's reason on hover. ``metric`` is undefined
// when this run did not score that metric for this row.
export default function AgentEvalMetricScoreCell({ metric }: { metric: MetricScore | undefined }) {
  if (!metric) return <span className="text-muted-foreground">—</span>;

  const pill = (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums',
        metricScoreClasses(metric.score),
      )}
    >
      {formatDecimal(metric.score)}
    </span>
  );

  if (!metric.reason) return pill;

  return (
    <CustomTooltip
      content={
        <div className="max-h-60 max-w-sm overflow-auto whitespace-pre-wrap break-words text-xs leading-snug">
          {metric.reason}
        </div>
      }
    >
      {pill}
    </CustomTooltip>
  );
}
