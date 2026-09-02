// Single source of truth for call-status presentation. Used by the call
// history table (row badge) and the call configurations tab (header badge).
// The `hover:` variants are inert outside hover-capable contexts (e.g. the
// detail tab) but harmless — keeping one map avoids palette drift.

export const CALL_STATUS_TONES: Record<string, string> = {
  completed: 'bg-emerald-500/10 text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-400',
  in_progress: 'bg-amber-500/10 text-amber-700 hover:bg-amber-500/10 dark:text-amber-400',
  failed: 'bg-destructive/10 text-destructive hover:bg-destructive/10',
};

export const CALL_STATUS_LABELS: Record<string, string> = {
  completed: 'Completed',
  in_progress: 'In Progress',
  failed: 'Failed',
};

const FALLBACK_TONE = 'bg-muted text-muted-foreground';

export function getCallStatusTone(status: string | null | undefined): string {
  return (status && CALL_STATUS_TONES[status]) || FALLBACK_TONE;
}

/** Falls back to a naively title-cased version of the raw status. */
export function getCallStatusLabel(status: string | null | undefined): string {
  if (!status) return 'Unknown';
  return (
    CALL_STATUS_LABELS[status] ?? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );
}
