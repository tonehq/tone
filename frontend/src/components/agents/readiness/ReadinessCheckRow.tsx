'use client';

import {
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  MinusCircle,
  ShieldAlert,
} from 'lucide-react';

import { CustomButton } from '@/components/shared';
import type { ReadinessCheckResult } from '@/types/readiness';
import { cn } from '@/utils/cn';

import { SEVERITY_TEXT_CLASS } from './readinessConstants';

interface ReadinessCheckRowProps {
  check: ReadinessCheckResult;
  onFix?: (check: ReadinessCheckResult) => void;
}

/**
 * One row in the check list. Icon on the left encodes both severity and
 * status; the message + remediation stack vertically. A "Fix it" affordance
 * appears only when the backend supplied a `deep_link`.
 */
export default function ReadinessCheckRow({ check, onFix }: ReadinessCheckRowProps) {
  const { Icon, tone } = iconFor(check);
  const isFail = check.status === 'fail';

  return (
    <div
      className={cn(
        'flex items-start gap-2.5 rounded-md border px-3 py-2.5',
        isFail ? 'border-border/60 bg-muted/20' : 'border-border/40 bg-transparent',
      )}
    >
      <Icon className={cn('mt-0.5 size-4 shrink-0', tone)} aria-hidden />

      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-[13px] leading-snug text-foreground">{check.message}</p>

        {check.status === 'fail' && check.remediation && (
          <p className="text-[12px] leading-snug text-muted-foreground">{check.remediation}</p>
        )}

        {check.status === 'skipped' && check.skip_reason && (
          <p className="text-[11px] leading-snug text-muted-foreground/80 italic">
            {check.skip_reason}
          </p>
        )}
      </div>

      {isFail && check.deep_link && onFix && (
        <CustomButton
          type="text"
          size="xs"
          onClick={() => onFix(check)}
          className="h-6 shrink-0 gap-1 px-2 text-[11px]"
          icon={<ExternalLink className="size-3" />}
        >
          Fix it
        </CustomButton>
      )}
    </div>
  );
}

// ── icon selection ───────────────────────────────────────────────────────────

function iconFor(check: ReadinessCheckResult): {
  Icon: React.ComponentType<{ className?: string }>;
  tone: string;
} {
  if (check.status === 'pass') {
    return { Icon: CheckCircle2, tone: 'text-emerald-600 dark:text-emerald-400' };
  }
  if (check.status === 'skipped') {
    return { Icon: MinusCircle, tone: 'text-muted-foreground' };
  }
  // status === 'fail': icon depends on severity.
  if (check.severity === 'blocker') {
    return { Icon: ShieldAlert, tone: SEVERITY_TEXT_CLASS.blocker };
  }
  if (check.severity === 'warning') {
    return { Icon: AlertTriangle, tone: SEVERITY_TEXT_CLASS.warning };
  }
  return { Icon: CircleAlert, tone: SEVERITY_TEXT_CLASS.info };
}
