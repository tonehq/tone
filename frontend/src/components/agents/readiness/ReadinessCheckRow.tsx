'use client';

import { AlertTriangle, CheckCircle2, CircleAlert, MinusCircle, ShieldAlert } from 'lucide-react';

import type { ReadinessCheckResult } from '@/types/readiness';
import { cn } from '@/utils/cn';

import { SEVERITY_TEXT_CLASS } from './readinessConstants';

interface ReadinessCheckRowProps {
  check: ReadinessCheckResult;
}

/**
 * One row in the check list. Icon on the left encodes both severity and
 * status; the message + remediation stack vertically.
 *
 * OAuth expiry checks intentionally have NO per-row refresh button — the
 * check's own message points to "Run Deep Test" which triggers a real
 * refresh via ``tools.reachable`` / ``mcp_servers.reachable``. Manual
 * refresh is an implementation detail we don't expose to end users; the
 * Tools / MCP pages surface a "Reconnect" button when the token is
 * genuinely broken and user action is required.
 */
export default function ReadinessCheckRow({ check }: ReadinessCheckRowProps) {
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
