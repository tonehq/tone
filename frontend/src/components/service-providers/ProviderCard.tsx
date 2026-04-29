'use client';

import { ActionMenu } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { ServiceProvider } from '@/types/provider';
import { cn } from '@/utils/cn';
import { Server } from 'lucide-react';

import { STATUS_STYLES, TYPE_BADGE_STYLES, TYPE_ICON_STYLES, TYPE_ICONS } from './constants';

interface ProviderCardProps {
  provider: ServiceProvider;
  selected: boolean;
  onSelect: () => void;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export default function ProviderCard({
  provider,
  selected,
  onSelect,
  onEdit,
  onDelete,
}: ProviderCardProps) {
  const statusKey = (provider.status ?? 'active').toLowerCase();
  const typeKey = provider.provider_type ?? '';

  return (
    <button
      onClick={onSelect}
      className={cn(
        'group relative flex w-full cursor-pointer items-center gap-3 rounded-lg border p-3 text-left transition-all',
        selected
          ? 'border-primary/30 bg-primary/[0.04] shadow-sm shadow-primary/5'
          : 'border-transparent bg-transparent hover:bg-accent/40',
      )}
    >
      {/* Selection indicator */}
      {selected && (
        <div className="absolute left-0 top-1/2 h-6 w-[3px] -translate-y-1/2 rounded-r-full bg-primary" />
      )}

      {/* Type icon */}
      <div
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors',
          TYPE_ICON_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
        )}
      >
        {TYPE_ICONS[typeKey] ?? <Server className="size-4" />}
      </div>

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {provider.display_name}
          </span>
          <Badge
            className={cn(
              'shrink-0 px-1.5 py-0 text-[9px] font-semibold uppercase tracking-wider',
              TYPE_BADGE_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
            )}
          >
            {typeKey}
          </Badge>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span
              className={cn(
                'size-1.5 rounded-full',
                STATUS_STYLES[statusKey] ?? STATUS_STYLES.inactive,
              )}
            />
            <span className="capitalize">{statusKey}</span>
          </span>
          <span className="text-border">&middot;</span>
          <span className="tabular-nums">
            {provider.models?.length ?? 0} model{(provider.models?.length ?? 0) !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Hover actions */}
      <div
        className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
      >
        <ActionMenu
          onEdit={onEdit}
          onDelete={onDelete}
          itemName={provider.display_name}
          deleteDescription={
            provider.is_system
              ? 'System providers cannot be deleted.'
              : `Are you sure you want to delete "${provider.display_name}"? All associated models will also be removed.`
          }
        />
      </div>
    </button>
  );
}
