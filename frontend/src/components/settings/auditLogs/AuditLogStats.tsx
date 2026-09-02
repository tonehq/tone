'use client';

import { Activity, Link2, PenLine, PlusCircle, Trash2, type LucideIcon } from 'lucide-react';

import { cn } from '@/utils/cn';

import type { AuditStats } from './useAuditStats';

interface StatDef {
  key: keyof Omit<AuditStats, 'loading'>;
  label: string;
  icon: LucideIcon;
  tone: string;
}

// Ordered left-to-right to match the reference screenshot.
const STATS: StatDef[] = [
  { key: 'total', label: 'Total Events', icon: Activity, tone: 'bg-primary/10 text-primary' },
  {
    key: 'created',
    label: 'Created',
    icon: PlusCircle,
    tone: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  },
  {
    key: 'updated',
    label: 'Updated',
    icon: PenLine,
    tone: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  },
  {
    key: 'deleted',
    label: 'Deleted',
    icon: Trash2,
    tone: 'bg-rose-500/10 text-rose-600 dark:text-rose-400',
  },
  {
    key: 'attachments',
    label: 'Attachments',
    icon: Link2,
    tone: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
  },
];

interface AuditLogStatsProps {
  stats: AuditStats;
  // When null the whole strip is muted — signals "pick an agent to see stats".
  agentSelected: boolean;
}

export default function AuditLogStats({ stats, agentSelected }: AuditLogStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {STATS.map(({ key, label, icon: Icon, tone }) => (
        <div
          key={key}
          className={cn(
            'rounded-xl border border-border bg-card p-4 transition-opacity',
            !agentSelected && 'opacity-60',
          )}
        >
          <div className="mb-2 flex items-center gap-2">
            <div className={cn('flex size-7 items-center justify-center rounded-lg', tone)}>
              <Icon className="size-4" strokeWidth={2} />
            </div>
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
              {label}
            </span>
          </div>
          <p className="text-2xl font-semibold tracking-tight text-foreground">
            {stats.loading ? '—' : stats[key].toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}
