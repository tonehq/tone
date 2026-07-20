'use client';

import { AlertCircle, CheckCircle2, Clock, Loader2, type LucideIcon } from 'lucide-react';

import type { ContactSyncStatus } from '@/types/contactSync';
import { cn } from '@/utils/cn';

/**
 * A small status pill for a `ContactSync` lifecycle status.
 *
 * WHAT: maps `pending|processing|completed|failed` to a labelled, coloured chip (mirrors
 * the `ScheduledCallStatusChip` visual language). `processing` pulses.
 *
 * WHEN: use anywhere a sync's status is shown — the sync stepper progress line, a sync
 * history row, or the Agent Contacts auto-assign flow.
 */
interface StatusConfig {
  label: string;
  className: string;
  Icon: LucideIcon;
  pulse?: boolean;
}

const STATUS_CONFIG: Record<ContactSyncStatus, StatusConfig> = {
  pending: {
    label: 'Pending',
    className: 'bg-slate-100 text-slate-700 ring-slate-200',
    Icon: Clock,
  },
  processing: {
    label: 'Processing',
    className: 'bg-blue-100 text-blue-700 ring-blue-200',
    Icon: Loader2,
    pulse: true,
  },
  completed: {
    label: 'Completed',
    className: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    Icon: CheckCircle2,
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-700 ring-red-200',
    Icon: AlertCircle,
  },
};

export default function SyncStatusChip({ status }: { status: ContactSyncStatus }) {
  const { label, className, Icon, pulse } = STATUS_CONFIG[status];
  return (
    <span
      aria-label={`Sync status: ${label}`}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        className,
      )}
    >
      <Icon className={cn('size-3.5', pulse && 'motion-safe:animate-spin')} aria-hidden />
      {label}
    </span>
  );
}
