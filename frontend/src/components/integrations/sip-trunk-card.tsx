'use client';

import { ActionMenu, CustomButton } from '@/components/shared';
import type { SipTrunk } from '@/types/sipTrunk';
import { cn } from '@/utils/cn';
import { formatRelative } from '@/utils/date';
import { motion, type Variants } from 'framer-motion';
import { Clock, Network, Phone, RefreshCw } from 'lucide-react';

export const sipCardVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.14 } },
};

const STATUS_STYLES: Record<SipTrunk['status'], string> = {
  draft: 'bg-muted text-muted-foreground',
  provisioned: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  error: 'bg-red-500/10 text-red-600 dark:text-red-400',
};

interface SipTrunkCardProps {
  trunk: SipTrunk;
  provisioning: boolean;
  onEdit: (trunk: SipTrunk) => void;
  onDelete: (trunk: SipTrunk) => Promise<void>;
  onProvision: (trunk: SipTrunk) => void;
  onManageNumbers: (trunk: SipTrunk) => void;
}

export default function SipTrunkCard({
  trunk,
  provisioning,
  onEdit,
  onDelete,
  onProvision,
  onManageNumbers,
}: SipTrunkCardProps) {
  const gatewaySummary =
    trunk.gateways.length === 0
      ? 'No gateways'
      : trunk.gateways
          .slice(0, 2)
          .map((gateway) => `${gateway.host}:${gateway.port}/${gateway.transport}`)
          .join(', ') + (trunk.gateways.length > 2 ? ` +${trunk.gateways.length - 2}` : '');

  return (
    <motion.div
      layout
      variants={sipCardVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      onClick={() => onEdit(trunk)}
      className={cn(
        'group relative cursor-pointer overflow-hidden rounded-2xl border border-border/80 bg-card transition-all duration-200',
        'hover:border-foreground/20 hover:shadow-[0_8px_24px_-12px_rgba(0,0,0,0.12)]',
      )}
    >
      <span className="absolute inset-y-0 left-0 w-1 bg-indigo-500" aria-hidden />

      <div className="flex items-center gap-4 py-4 pl-5 pr-4">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-indigo-200/50 bg-indigo-50 shadow-sm dark:border-indigo-500/20 dark:bg-indigo-500/10">
          <Network className="size-4 text-indigo-500" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="truncate text-sm font-semibold tracking-tight text-foreground">
              {trunk.name}
            </h3>
            <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {trunk.carrier}
            </span>
            <span
              className={cn(
                'rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                STATUS_STYLES[trunk.status],
              )}
            >
              {trunk.status}
            </span>
            <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {trunk.auth_mode === 'digest' ? 'digest' : 'ip acl'}
            </span>
          </div>

          <p className="mt-1 truncate text-xs text-muted-foreground">{gatewaySummary}</p>

          {trunk.termination_host && (
            <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">
              {trunk.inbound_uri_template}
            </p>
          )}

          {trunk.status === 'error' && trunk.status_detail && (
            <p className="mt-1 line-clamp-2 text-xs text-red-500">{trunk.status_detail}</p>
          )}

          <p className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="size-3 shrink-0" />
            Updated {formatRelative(trunk.updated_at)}
          </p>
        </div>

        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <CustomButton type="text" onClick={() => onManageNumbers(trunk)} className="gap-1.5">
            <Phone className="size-3.5" />
            Numbers
          </CustomButton>

          <CustomButton
            type="text"
            onClick={() => onProvision(trunk)}
            disabled={provisioning}
            className="gap-1.5"
          >
            <RefreshCw className={cn('size-3.5', provisioning && 'animate-spin')} />
            {trunk.status === 'provisioned' ? 'Resync' : 'Provision'}
          </CustomButton>

          <ActionMenu
            onEdit={() => onEdit(trunk)}
            onDelete={() => onDelete(trunk)}
            itemName={trunk.name}
          />
        </div>
      </div>
    </motion.div>
  );
}
