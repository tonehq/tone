'use client';

import { ActionMenu } from '@/components/shared';
import { formatRelative } from '@/utils/date';
import { cn } from '@/utils/cn';
import { motion, type Variants } from 'framer-motion';
import { Clock, Phone } from 'lucide-react';

import { getChannelProviderVisual, humanizeSlug } from './providerVisuals';
import type { Channel } from '@/types/integration';

export const cardVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.14 } },
};

interface ChannelCardProps {
  channel: Channel;
  onEdit: (channel: Channel) => void;
  onDelete: (channel: Channel) => Promise<void>;
}

export default function ChannelCard({ channel, onEdit, onDelete }: ChannelCardProps) {
  const visual = getChannelProviderVisual(channel.channel_type);
  const typeLabel = visual?.name ?? humanizeSlug(channel.channel_type);
  const updated = formatRelative(channel.updated_at);

  return (
    <motion.div
      layout
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      onClick={() => onEdit(channel)}
      className={cn(
        'group relative cursor-pointer overflow-hidden rounded-2xl border border-border/80 bg-card transition-all duration-200',
        'hover:border-foreground/20',
      )}
    >
      {/* Brand accent stripe down the left edge */}
      <span
        className={cn('absolute inset-y-0 left-0 w-1', visual?.accentColor ?? 'bg-blue-500')}
        aria-hidden
      />

      <div className="flex items-center gap-4 py-4 pl-5 pr-4">
        <div
          className={cn(
            'flex size-11 shrink-0 items-center justify-center rounded-xl border shadow-sm',
            visual?.iconBg ?? 'bg-muted',
            visual?.iconBorder ?? 'border-border/50',
          )}
        >
          {visual?.icon ?? <Phone className="size-4 text-muted-foreground" />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="truncate text-sm font-semibold tracking-tight text-foreground">
              {channel.name}
            </h3>
            <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {typeLabel}
            </span>
          </div>
          <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3 shrink-0" />
            Updated {updated}
          </p>
        </div>

        <div onClick={(e) => e.stopPropagation()}>
          <ActionMenu
            onEdit={() => onEdit(channel)}
            onDelete={() => onDelete(channel)}
            itemName={channel.name}
          />
        </div>
      </div>
    </motion.div>
  );
}
