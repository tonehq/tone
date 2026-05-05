'use client';

import { ActionMenu } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { Service } from '@/types/provider';
import { cn } from '@/utils/cn';
import { Box, Key, Server } from 'lucide-react';

import { STATUS_STYLES, TYPE_BADGE_STYLES, TYPE_ICON_STYLES, TYPE_ICONS } from './constants';

interface ServiceCardProps {
  service: Service;
  onNavigate: () => void;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export default function ServiceCard({ service, onNavigate, onEdit, onDelete }: ServiceCardProps) {
  const statusKey = (service.status ?? 'active').toLowerCase();
  const typeKey = service.service_type ?? '';

  return (
    <div
      className="group relative flex cursor-pointer flex-col rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/20 hover:shadow-md hover:shadow-primary/5"
      onClick={onNavigate}
    >
      {/* Top row: icon + name + badges + actions */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-lg',
            TYPE_ICON_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
          )}
        >
          {TYPE_ICONS[typeKey] ?? <Server className="size-4.5" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-foreground">{service.name}</h3>
            <Badge
              className={cn(
                'shrink-0 px-1.5 py-0 text-[9px] font-semibold uppercase tracking-wider',
                TYPE_BADGE_STYLES[typeKey] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {typeKey}
            </Badge>
            {service.is_default && (
              <Badge className="shrink-0 bg-primary/10 px-1.5 py-0 text-[9px] font-medium text-primary hover:bg-primary/10">
                Default
              </Badge>
            )}
          </div>
          {service.description && (
            <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
              {service.description}
            </p>
          )}
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
            itemName={service.name}
            deleteDescription={`Delete "${service.name}"? Agents using this service will need to be reconfigured.`}
          />
        </div>
      </div>

      {/* Divider */}
      <div className="my-3 border-t border-border/60" />

      {/* Bottom row: metadata chips */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-muted-foreground">
        {/* Status */}
        <span className="flex items-center gap-1">
          <span
            className={cn(
              'size-1.5 rounded-full',
              STATUS_STYLES[statusKey] ?? STATUS_STYLES.inactive,
            )}
          />
          <span className="capitalize">{statusKey}</span>
        </span>

        {/* Provider name */}
        {service.service_provider_name && (
          <span className="flex items-center gap-1">
            <Server className="size-3 text-muted-foreground/60" />
            {service.service_provider_name}
          </span>
        )}

        {/* Models count */}
        <span className="flex items-center gap-1">
          <Box className="size-3 text-muted-foreground/60" />
          <span className="tabular-nums">
            {service.models?.length ?? 0} model{(service.models?.length ?? 0) !== 1 ? 's' : ''}
          </span>
        </span>

        {/* API Key hint */}
        {service.api_key_hint && (
          <span className="flex items-center gap-1">
            <Key className="size-3 text-muted-foreground/60" />
            <span className="font-mono">{service.api_key_hint}</span>
          </span>
        )}
      </div>
    </div>
  );
}
