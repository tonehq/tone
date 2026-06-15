'use client';

import { motion, type Variants } from 'framer-motion';
import { ChevronRight, KeyRound, Layers, Pencil, Trash2 } from 'lucide-react';
import type React from 'react';

import CustomButton from '@/components/shared/CustomButton';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import type { ProviderUsage } from '@/types/service';
import { cn } from '@/utils/cn';

import ProviderLogo from './ProviderLogo';
import { TYPE_BADGE_STYLES } from './constants';

export const cardVariants: Variants = {
  hidden: { opacity: 0, y: 8, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, scale: 0.96, transition: { duration: 0.15 } },
};

interface ServiceCardProps {
  usage: ProviderUsage;
  onClick: (usage: ProviderUsage) => void;
  onEdit: (usage: ProviderUsage) => void;
  onDelete: (usage: ProviderUsage) => void;
}

export default function ServiceCard({ usage, onClick, onEdit, onDelete }: ServiceCardProps) {
  const handleClick: React.MouseEventHandler<HTMLDivElement> = () => onClick(usage);

  const handleEdit: React.MouseEventHandler<HTMLButtonElement> = (e) => {
    e.stopPropagation();
    onEdit(usage);
  };

  const handleDelete: React.MouseEventHandler<HTMLButtonElement> = (e) => {
    e.stopPropagation();
    onDelete(usage);
  };

  return (
    <motion.div
      layout
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      whileHover={{ y: -2 }}
      transition={{ type: 'spring', stiffness: 260, damping: 24 }}
    >
      <Card
        onClick={handleClick}
        className={cn(
          'group relative flex h-full cursor-pointer flex-col gap-4 overflow-hidden p-5 transition-all',
          'border-border/70 hover:border-border hover:shadow-[0_4px_24px_-12px_rgb(0_0_0/0.12)]',
        )}
      >
        {/* header: logo + title + actions */}
        <div className="flex items-start gap-3">
          <ProviderLogo
            providerName={usage.provider.slug}
            serviceType={usage.service_type}
            className="size-11 shrink-0"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3
                className="truncate text-[15px] font-semibold leading-tight tracking-tight text-foreground"
                title={usage.provider.display_name}
              >
                {usage.provider.display_name}
              </h3>
              <ChevronRight className="size-4 shrink-0 text-muted-foreground/40 transition-all group-hover:translate-x-0.5 group-hover:text-foreground/70" />
            </div>
            {usage.provider.description && (
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {usage.provider.description}
              </p>
            )}
          </div>

          {/* hover actions — anchored top-right, no layout shift */}
          <div className="absolute right-3 top-3 flex items-center gap-0.5 rounded-md bg-card/95 p-0.5 opacity-0 shadow-sm ring-1 ring-border/60 backdrop-blur transition-opacity group-hover:opacity-100">
            <CustomButton
              type="text"
              onClick={handleEdit}
              aria-label="Edit service"
              title="Edit"
              className="!h-auto inline-flex size-7 cursor-pointer items-center justify-center rounded p-0 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              icon={<Pencil className="size-3.5" />}
            />
            <CustomButton
              type="text"
              onClick={handleDelete}
              aria-label="Delete service"
              title="Delete"
              className="!h-auto inline-flex size-7 cursor-pointer items-center justify-center rounded p-0 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              icon={<Trash2 className="size-3.5" />}
            />
          </div>
        </div>

        {/* type pill + default indicator */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            className={cn(
              'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
              TYPE_BADGE_STYLES[usage.service_type] ?? '',
            )}
          >
            {usage.service_type}
          </Badge>
          {usage.default_api_key && (
            <span
              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground"
              title={`Default: ${usage.default_api_key.label ?? '—'}`}
            >
              <span className="size-1.5 rounded-full bg-emerald-500" />
              Default
            </span>
          )}
        </div>

        {/* stats row — slim divider treatment */}
        <div className="mt-auto flex items-center gap-4 border-t border-border/60 pt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <KeyRound className="size-3.5 text-muted-foreground/70" />
            <span className="font-semibold tabular-nums text-foreground">
              {usage.api_key_count}
            </span>
            <span>
              {usage.api_key_count === 1 ? 'key' : 'keys'}
              {usage.active_api_key_count !== usage.api_key_count && (
                <span className="ml-1 text-muted-foreground/70">
                  ({usage.active_api_key_count} active)
                </span>
              )}
            </span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Layers className="size-3.5 text-muted-foreground/70" />
            <span className="font-semibold tabular-nums text-foreground">{usage.model_count}</span>
            <span>{usage.model_count === 1 ? 'model' : 'models'}</span>
          </span>
        </div>
      </Card>
    </motion.div>
  );
}
