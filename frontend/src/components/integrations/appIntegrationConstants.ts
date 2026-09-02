/** Shared constants for the app-integration list view. */

export type BadgeTone = 'success' | 'warning' | 'default' | 'muted';

export const BADGE_TONES: Record<BadgeTone, string> = {
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
  default: 'bg-muted text-muted-foreground',
  muted: 'bg-muted/60 text-muted-foreground',
};
