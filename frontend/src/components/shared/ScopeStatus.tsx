'use client';

import CustomButton from '@/components/shared/CustomButton';
import { Badge } from '@/components/ui/badge';
import CustomTooltip from '@/components/shared/CustomTooltip';
import { cn } from '@/utils/cn';
import { evaluateScopes, shortScopeLabel } from '@/utils/scopes';
import { AlertTriangle, CheckCircle2, RotateCw, ShieldX } from 'lucide-react';

type ScopeVariant = 'ok' | 'missing' | 'expired';

interface ScopeStatusProps {
  /** Scopes the connection was granted (list, space/comma string, or null). */
  granted?: string[] | string | null;
  /** Scopes the provider/tool requires. */
  required?: string[] | string | null;
  /** Force the `expired` state regardless of scope comparison. */
  expired?: boolean;
  /** Re-run the OAuth authorize flow to grant missing scopes / refresh tokens. */
  onReconnect?: () => void;
  reconnecting?: boolean;
  className?: string;
}

const VARIANT_STYLES: Record<ScopeVariant, string> = {
  ok: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20',
  missing: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/25',
  expired: 'bg-destructive/10 text-destructive border-destructive/25',
};

/**
 * Inline, accessible scope-status affordance shared across the connection card, the MCP form, and
 * the agent tool step. Status is conveyed with an icon + label (never colour alone) and announced
 * via an aria-live region. Offers an optional Reconnect action when scopes are missing/expired.
 */
export default function ScopeStatus({
  granted,
  required,
  expired = false,
  onReconnect,
  reconnecting = false,
  className,
}: ScopeStatusProps) {
  const evaluation = evaluateScopes(granted, required);
  const variant: ScopeVariant = expired ? 'expired' : evaluation.ok ? 'ok' : 'missing';

  const Icon = variant === 'ok' ? CheckCircle2 : variant === 'expired' ? ShieldX : AlertTriangle;
  const label =
    variant === 'ok'
      ? evaluation.required.length > 0
        ? 'All scopes granted'
        : 'Connected'
      : variant === 'expired'
        ? 'Token expired'
        : `Missing: ${evaluation.missing.map(shortScopeLabel).join(', ')}`;

  const tooltip =
    evaluation.required.length > 0 ? (
      <div className="max-w-[260px] space-y-1.5 py-0.5 text-left">
        <p className="text-[11px] font-semibold">Required scopes</p>
        <ul className="space-y-0.5">
          {evaluation.required.map((scope) => {
            const isGranted = !evaluation.missing.includes(scope);
            return (
              <li key={scope} className="flex items-center gap-1.5 text-[11px]">
                {isGranted ? (
                  <CheckCircle2 className="size-3 shrink-0 text-emerald-400" />
                ) : (
                  <AlertTriangle className="size-3 shrink-0 text-amber-400" />
                )}
                <span className="truncate">{shortScopeLabel(scope)}</span>
              </li>
            );
          })}
        </ul>
      </div>
    ) : (
      'This provider grants access without configurable scopes.'
    );

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <CustomTooltip content={tooltip}>
        <Badge
          variant="outline"
          aria-live="polite"
          className={cn('cursor-default gap-1 font-medium', VARIANT_STYLES[variant])}
        >
          <Icon className="size-3" strokeWidth={2.25} aria-hidden />
          {label}
        </Badge>
      </CustomTooltip>

      {variant !== 'ok' && onReconnect && (
        <CustomButton
          type="text"
          size="sm"
          onClick={onReconnect}
          loading={reconnecting}
          className="h-6 gap-1 px-2 text-xs"
        >
          <RotateCw className="size-3" aria-hidden />
          Reconnect
        </CustomButton>
      )}
    </div>
  );
}
