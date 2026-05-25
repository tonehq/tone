'use client';

import { cn } from '@/utils/cn';
import type { ReactNode } from 'react';

interface SectionShellProps {
  eyebrow?: string;
  title: string;
  description?: string;
  count?: number | null;
  toolbar?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Unified section wrapper used on the Integrations page. Combines the section
 * title, count chip and (optional) toolbar into one compact header row so the
 * page reads as a clear vertical sequence instead of three competing blocks.
 */
export default function SectionShell({
  eyebrow,
  title,
  description,
  count,
  toolbar,
  children,
  className,
}: SectionShellProps) {
  return (
    <section className={cn('mb-10 last:mb-0', className)}>
      <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-1 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground/80">
              {eyebrow}
            </p>
          )}
          <div className="flex items-baseline gap-2">
            <h2 className="text-base font-semibold tracking-tight text-foreground">{title}</h2>
            {typeof count === 'number' && (
              <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-semibold text-muted-foreground tabular-nums">
                {count}
              </span>
            )}
          </div>
          {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
        </div>
        {toolbar && (
          <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">{toolbar}</div>
        )}
      </header>
      {children}
    </section>
  );
}
