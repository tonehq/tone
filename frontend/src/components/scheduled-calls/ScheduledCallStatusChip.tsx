'use client';

import { cn } from '@/lib/utils';
import type { ScheduledCallStatus } from '@/types/outboundCall';
import {
  AlertCircle,
  Ban,
  CalendarClock,
  CheckCircle2,
  Loader2,
  type LucideIcon,
  PhoneMissed,
  PhoneOutgoing,
} from 'lucide-react';

interface StatusConfig {
  label: string;
  className: string;
  Icon: LucideIcon;
  pulse?: boolean;
}

const STATUS_CONFIG: Record<ScheduledCallStatus, StatusConfig> = {
  scheduled: {
    label: 'Scheduled',
    className: 'bg-slate-100 text-slate-700 ring-slate-200',
    Icon: CalendarClock,
  },
  processing: {
    label: 'Processing',
    className: 'bg-blue-100 text-blue-700 ring-blue-200',
    Icon: Loader2,
    pulse: true,
  },
  dispatched: {
    label: 'Dispatched',
    className: 'bg-blue-100 text-blue-700 ring-blue-200',
    Icon: PhoneOutgoing,
    pulse: true,
  },
  completed: {
    label: 'Completed',
    className: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    Icon: CheckCircle2,
  },
  busy: {
    label: 'Busy',
    className: 'bg-orange-100 text-orange-700 ring-orange-200',
    Icon: PhoneMissed,
  },
  no_answer: {
    label: 'No answer',
    className: 'bg-orange-100 text-orange-700 ring-orange-200',
    Icon: PhoneMissed,
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-100 text-red-700 ring-red-200',
    Icon: AlertCircle,
  },
  canceled: {
    label: 'Canceled',
    className: 'bg-slate-100 text-slate-500 ring-slate-200',
    Icon: Ban,
  },
};

const FALLBACK: StatusConfig = {
  label: 'Unknown',
  className: 'bg-slate-100 text-slate-500 ring-slate-200',
  Icon: AlertCircle,
};

export default function ScheduledCallStatusChip({
  status,
}: {
  status: ScheduledCallStatus | null;
}) {
  const { label, className, Icon, pulse } = (status && STATUS_CONFIG[status]) || FALLBACK;
  return (
    <span
      aria-label={`Status: ${label}`}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        className,
      )}
    >
      <Icon className={cn('size-3.5', pulse && 'motion-safe:animate-pulse')} aria-hidden />
      {label}
    </span>
  );
}
