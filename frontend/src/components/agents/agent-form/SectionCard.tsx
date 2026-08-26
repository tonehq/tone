'use client';

import type React from 'react';

import { IconChip } from '@/components/shared';
import type { IconChipTone } from '@/components/shared';
import { cn } from '@/utils/cn';

export interface SectionCardProps {
  icon: React.ReactNode;
  tone?: IconChipTone;
  /** Tailwind classes for the leading icon chip (bg, text colour, ring).
   * Examples in the steps: indigo/amber/emerald/violet/sky/muted. */
  iconClassName?: string;
  title: string;
  description?: string;
  /** Right-aligned slot for a control like a Switch, count badge, or button. */
  action?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  /** Override the body wrapper class (defaults to flex column with gap-4). */
  bodyClassName?: string;
}

/**
 * Shared "section" card used across every tab of the agent edit page so the
 * visual rhythm is consistent: icon chip + title + subtitle in the header,
 * optional right-aligned action, then the body content.
 */
export default function SectionCard({
  icon,
  tone,
  iconClassName,
  title,
  description,
  action,
  children,
  className,
  bodyClassName,
}: SectionCardProps) {
  return (
    <section
      className={cn(
        'flex flex-col gap-4 rounded-2xl border border-border/70 bg-card p-4',
        className,
      )}
    >
      <header className="group/section flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {tone ? (
            <IconChip icon={icon} tone={tone} size="md" interactive />
          ) : (
            <span
              className={cn(
                'flex size-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset',
                iconClassName ?? 'bg-muted text-muted-foreground ring-border',
              )}
            >
              {icon}
            </span>
          )}
          <div className="min-w-0">
            <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">
              {title}
            </h3>
            {description ? (
              <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
            ) : null}
          </div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </header>
      {children ? <div className={cn('flex flex-col gap-4', bodyClassName)}>{children}</div> : null}
    </section>
  );
}

// Re-usable colour tokens for the icon chip so every step picks from the same
// palette and the "what category am I in?" cue stays consistent.
export const ACCENTS = {
  indigo: 'bg-indigo-500/10 text-indigo-700 ring-indigo-500/30 dark:text-indigo-300',
  amber: 'bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-300',
  emerald: 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/30 dark:text-emerald-300',
  violet: 'bg-violet-500/10 text-violet-700 ring-violet-500/30 dark:text-violet-300',
  sky: 'bg-sky-500/10 text-sky-700 ring-sky-500/30 dark:text-sky-300',
  rose: 'bg-rose-500/10 text-rose-700 ring-rose-500/30 dark:text-rose-300',
  slate: 'bg-slate-500/10 text-slate-700 ring-slate-500/30 dark:text-slate-300',
  muted: 'bg-muted text-muted-foreground ring-border',
} as const;
