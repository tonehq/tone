import type { EvalVerdict } from '@/types/eval';

// Single source for the verdict colour language (pass = emerald, partial =
// amber, fail = destructive), shared by VerdictChip and VerdictTally so the
// palette is defined once. `base` = background + text; `ring` = the matching
// ring VerdictChip layers on top.
export const VERDICT_COLOR: Record<EvalVerdict, string> = {
  PASS: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  PARTIAL: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  FAIL: 'bg-destructive/10 text-destructive',
};

export const VERDICT_RING: Record<EvalVerdict, string> = {
  PASS: 'ring-1 ring-emerald-500/20',
  PARTIAL: 'ring-1 ring-amber-500/20',
  FAIL: 'ring-1 ring-destructive/20',
};
