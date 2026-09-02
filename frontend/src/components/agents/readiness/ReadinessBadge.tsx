'use client';

import { AlertTriangle, CheckCircle2, HelpCircle, Loader2, ShieldAlert } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { ReadinessOverallStatus } from '@/types/readiness';
import { cn } from '@/utils/cn';

/**
 * Shared readiness pill. One component, three surfaces:
 *   - editor header
 *   - agent list column
 *   - version selector dropdown
 *
 * Follows the same colour+icon language as `ScopeStatus.tsx` so the two badges
 * feel like family. Status is conveyed with an icon AND a label (never colour
 * alone) so it stays accessible.
 */

type BadgeState = ReadinessOverallStatus | 'loading' | 'error';

interface ReadinessBadgeProps {
  status: BadgeState;
  blockerCount?: number;
  warningCount?: number;
  /** `sm` → compact for tables/dropdowns; `md` → editor header. */
  size?: 'sm' | 'md';
  /** When set, the pill becomes a button-flavoured control (cursor + focus ring). */
  onClick?: (e: React.MouseEvent<HTMLElement>) => void;
  /** Hide the text label and render icon-only (used inside the version dropdown). */
  iconOnly?: boolean;
  className?: string;
  'aria-label'?: string;
}

const VARIANT_STYLES: Record<BadgeState, string> = {
  ready:
    'border-transparent bg-transparent text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-400',
  ready_with_warnings:
    'border-transparent bg-transparent text-amber-700 hover:bg-amber-500/10 dark:text-amber-400',
  not_ready: 'border-transparent bg-transparent text-destructive hover:bg-destructive/10',
  loading: 'border-transparent bg-transparent text-muted-foreground',
  error: 'border-transparent bg-transparent text-muted-foreground hover:bg-accent',
};

const ICONS: Record<BadgeState, React.ComponentType<{ className?: string }>> = {
  ready: CheckCircle2,
  ready_with_warnings: AlertTriangle,
  not_ready: ShieldAlert,
  loading: Loader2,
  error: HelpCircle,
};

function labelFor(state: BadgeState, blockers: number, warnings: number): string {
  switch (state) {
    case 'loading':
      return 'Checking…';
    case 'error':
      return 'Readiness unavailable';
    case 'ready':
      return 'Ready';
    case 'ready_with_warnings':
      return warnings === 1 ? '1 warning' : `${warnings} warnings`;
    case 'not_ready':
      return blockers === 1 ? '1 blocker' : `${blockers} blockers`;
    default:
      return '';
  }
}

export default function ReadinessBadge({
  status,
  blockerCount = 0,
  warningCount = 0,
  size = 'md',
  onClick,
  iconOnly = false,
  className,
  'aria-label': ariaLabel,
}: ReadinessBadgeProps) {
  const Icon = ICONS[status];
  const label = labelFor(status, blockerCount, warningCount);
  const isInteractive = typeof onClick === 'function';

  const badgeInner = (
    <Badge
      variant="outline"
      aria-live="polite"
      aria-label={ariaLabel ?? label}
      className={cn(
        'gap-1 font-medium',
        VARIANT_STYLES[status],
        size === 'sm' ? 'px-1.5 py-0 text-[10px]' : 'px-2 py-0.5 text-[11px]',
        isInteractive ? 'cursor-pointer hover:brightness-105' : 'cursor-default',
        className,
      )}
    >
      <Icon
        className={cn(
          size === 'sm' ? 'size-3' : 'size-3.5',
          status === 'loading' && 'animate-spin',
        )}
        aria-hidden
      />
      {!iconOnly && <span>{label}</span>}
    </Badge>
  );

  // Interactive badges use CustomButton so keyboard + AT semantics come for
  // free and we stay compliant with the shared-components rule.
  if (isInteractive) {
    return (
      <CustomButton
        type="text"
        size="xs"
        onClick={onClick}
        aria-label={ariaLabel ?? label}
        className="h-auto rounded-md p-0 hover:bg-transparent"
      >
        {badgeInner}
      </CustomButton>
    );
  }
  return badgeInner;
}
