'use client';

import { CustomButton } from '@/components/shared';
import type { ProviderCardConfig } from '@/constants/integrations';
import { cn } from '@/utils/cn';

interface IntegrationCardProps {
  config: ProviderCardConfig;
  hasItems: boolean;
  children?: React.ReactNode;
  actionLabel: string;
  actionIcon: React.ReactNode;
  actionLoading: boolean;
  onAction: () => void;
}

export default function IntegrationCard({
  config,
  hasItems,
  children,
  actionLabel,
  actionIcon,
  actionLoading,
  onAction,
}: IntegrationCardProps) {
  return (
    <div
      className={cn(
        'group relative flex flex-col overflow-hidden rounded-2xl border bg-background shadow-sm transition-all duration-300',
        hasItems ? 'border-border' : 'border-border/60 hover:border-border hover:shadow-md',
      )}
    >
      {hasItems && <div className={cn('h-[3px] w-full', config.accentColor)} />}

      <div className="flex flex-1 flex-col p-5">
        <div
          className={cn(
            'mb-3 flex size-10 items-center justify-center rounded-xl border',
            config.iconBg,
            config.iconBorder,
          )}
        >
          {config.icon}
        </div>

        <div className="mb-1 flex items-center gap-2">
          <h3 className="text-[13px] font-semibold text-foreground">{config.name}</h3>
          {hasItems && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400">
              <span className="size-1 rounded-full bg-emerald-500" />
              Active
            </span>
          )}
        </div>

        <p className="mb-4 text-[12px] leading-relaxed text-muted-foreground">
          {config.description}
        </p>

        <div className="mt-auto">
          {children && <div className="mb-3 space-y-1.5">{children}</div>}
          <CustomButton
            type={hasItems ? 'default' : 'primary'}
            size="sm"
            fullWidth
            icon={actionIcon}
            onClick={onAction}
            loading={actionLoading}
          >
            {actionLabel}
          </CustomButton>
        </div>
      </div>
    </div>
  );
}
