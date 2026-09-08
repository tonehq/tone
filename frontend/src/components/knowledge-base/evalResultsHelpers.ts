// Score formatters are shared with the agent-LLM eval feature — single source
// of truth in ``@/utils/evalFormat`` (re-exported here so existing imports of
// ``formatPercent`` / ``formatDecimal`` from this module keep working).
export {
  formatRatioPercent as formatPercent,
  formatMetricScore as formatDecimal,
} from '@/utils/evalFormat';

// Tailwind classes for a per-metric verdict pill/score. `metric_scores`
// verdicts are lowercase ('pass' | 'partial' | 'fail'); anything else falls
// back to a neutral tone. Mirrors the color scheme used by VerdictChip.
export const metricVerdictClasses = (verdict: string | null | undefined): string => {
  switch ((verdict ?? '').toLowerCase()) {
    case 'pass':
      return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20';
    case 'partial':
      return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20';
    case 'fail':
      return 'bg-destructive/10 text-destructive ring-1 ring-destructive/20';
    default:
      return 'bg-muted text-muted-foreground ring-1 ring-border/60';
  }
};
