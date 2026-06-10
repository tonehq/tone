import { cn } from '@/utils/cn';
import React from 'react';

interface MetricsCategoryProps {
  /** Top-level grouping label (e.g. `Latency`, `Usage`). */
  title: string;
  /** Optional helper line under the title. */
  description?: string;
  /** Section blocks rendered inside the group, one below the other. */
  children: React.ReactNode;
  className?: string;
}

/**
 * Top-level grouping for the call metrics page. Renders a styled header
 * over a vertically stacked list of section blocks (TTFB, LLM Usage, …).
 *
 * Used to split the metrics view into `Latency` and `Usage` categories so
 * sections related to each other sit together visually.
 */
export function MetricsCategory({ title, description, children, className }: MetricsCategoryProps) {
  return (
    <section className={cn('flex flex-col gap-4', className)}>
      <header className="flex items-baseline gap-2 border-b border-border pb-2">
        <h3 className="text-base font-semibold uppercase tracking-wide text-foreground">{title}</h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </header>
      <div className="flex flex-col gap-6">{children}</div>
    </section>
  );
}
