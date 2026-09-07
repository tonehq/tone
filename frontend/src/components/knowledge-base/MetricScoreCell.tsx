'use client';

import { CustomTooltip } from '@/components/shared';
import {
  formatDecimal,
  metricVerdictClasses,
} from '@/components/knowledge-base/evalResultsHelpers';
import type { EvalMetricScore } from '@/types/eval';
import { cn } from '@/utils/cn';

// One metric's score for a scored question: a compact score pill colored by
// the metric's verdict, revealing the judge's reason on hover. `metric` is
// undefined when this batch did not score that metric for this row.
export default function MetricScoreCell({ metric }: { metric: EvalMetricScore | undefined }) {
  if (!metric) return <span className="text-muted-foreground">—</span>;

  const pill = (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums',
        metricVerdictClasses(metric.verdict),
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
