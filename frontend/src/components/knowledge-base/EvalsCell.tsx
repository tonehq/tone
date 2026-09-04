'use client';

import { Loader2 } from 'lucide-react';

import { CustomButton, CustomTooltip } from '@/components/shared';
import type { EvalRunSummary, EvalRunSummaryTotals } from '@/types/eval';
import { cn } from '@/utils/cn';

interface EvalsCellProps {
  summary: EvalRunSummary | undefined;
  // The eval batch for this run is queued/running — no score exists yet.
  isInFlight: boolean;
  onView: () => void;
}

// Color the "Evals" chip by pass rate — grey when no batch exists yet, red
// on any FAIL, amber on any PARTIAL (no FAIL), green when everything passed.
function evalChipTone(summary: EvalRunSummary | undefined): {
  className: string;
  label: string;
} {
  const neutral = {
    className: 'bg-muted text-muted-foreground ring-1 ring-border/60',
    label: '—',
  };
  if (!summary) return neutral;
  const totals = summary.summary as EvalRunSummaryTotals;
  const total = totals?.total ?? 0;
  if (total === 0) return neutral;
  const label = `${totals.pass}/${total}`;
  if (summary.status === 'failed' || totals.fail > 0) {
    return {
      className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
      label,
    };
  }
  if (totals.partial > 0) {
    return {
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
      label,
    };
  }
  return {
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    label,
  };
}

export default function EvalsCell({ summary, isInFlight, onView }: EvalsCellProps) {
  if (isInFlight) {
    return (
      <CustomTooltip content="Evals are running — the score will appear once the batch finishes.">
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px]',
            'font-medium text-amber-700 ring-1 ring-amber-500/20 dark:text-amber-400',
          )}
        >
          <Loader2 className="size-3 animate-spin" />
          Running
        </span>
      </CustomTooltip>
    );
  }

  const chip = evalChipTone(summary);
  const totals = summary?.summary as EvalRunSummaryTotals | undefined;
  const tooltip = summary
    ? `${totals?.pass ?? 0} pass · ${totals?.partial ?? 0} partial · ${totals?.fail ?? 0} fail (batch #${summary.run_number}) — click to view`
    : 'No eval batch has scored this run yet — click to view';

  return (
    <CustomTooltip content={tooltip}>
      <CustomButton
        type="text"
        size="xs"
        onClick={(e) => {
          e.stopPropagation();
          onView();
        }}
        className={cn(
          'h-auto rounded-full px-2 py-0.5 text-[11px] font-medium tabular-nums transition-colors hover:brightness-110',
          chip.className,
        )}
      >
        {chip.label}
      </CustomButton>
    </CustomTooltip>
  );
}
