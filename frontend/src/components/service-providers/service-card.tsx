'use client';

import { motion, type Variants } from 'framer-motion';
import { ChevronRight, KeyRound, Layers, Pencil, Trash2 } from 'lucide-react';
import type React from 'react';

import { CustomButton } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import type { ProviderUsage } from '@/types/service';
import { cn } from '@/utils/cn';

import ProviderLogo from './ProviderLogo';

// Neutral, editorial type pill — one mono label, no per-type rainbow accent.
const TYPE_PILL =
  'rounded-full border border-border bg-background px-2 py-0 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground';

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
          'group relative flex h-full cursor-pointer flex-col gap-4 overflow-hidden rounded-xl p-5 transition-all duration-200',
          'border-border hover:-translate-y-0.5 hover:border-foreground/20',
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
              size="icon-xs"
              onClick={handleEdit}
              aria-label="Edit service"
              title="Edit"
              className="text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Pencil className="size-3.5" />
            </CustomButton>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={handleDelete}
              aria-label="Delete service"
              title="Delete"
              className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              <Trash2 className="size-3.5" />
            </CustomButton>
          </div>
        </div>

        {/* type pill + default indicator */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={TYPE_PILL}>{usage.service_type}</Badge>
          {usage.default_api_key && (
            <span
              className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-amber-500"
              title={`Default: ${usage.default_api_key.label ?? '—'}`}
            >
              <span className="size-1.5 rounded-full bg-amber-400" />
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

        {/* hairline accent that wipes in on hover */}
        <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
      </Card>
    </motion.div>
  );
}
