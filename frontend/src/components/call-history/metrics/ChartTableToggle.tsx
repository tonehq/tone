'use client';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';
import { BarChart3, Table as TableIcon, type LucideIcon } from 'lucide-react';

export type MetricView = 'chart' | 'table';

interface ChartTableToggleProps {
  view: MetricView;
  onChange: (next: MetricView) => void;
  /** Accessible label describing what the toggle controls (e.g. "TTFB samples"). */
  label?: string;
  className?: string;
}

interface OptionMeta {
  value: MetricView;
  label: string;
  Icon: LucideIcon;
}

const OPTIONS: OptionMeta[] = [
  { value: 'chart', label: 'Chart view', Icon: BarChart3 },
  { value: 'table', label: 'Table view', Icon: TableIcon },
];

/**
 * Segmented two-option toggle used across metric sections to flip between
 * a chart and a tabular view of the same data. Controlled — the parent owns
 * the view state. For most sections prefer the [[useChartTableView]] hook
 * which bundles the state + this toggle.
 */
export function ChartTableToggle({ view, onChange, label, className }: ChartTableToggleProps) {
  return (
    <div
      role="group"
      aria-label={label ?? 'Chart or table view'}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-md border border-border bg-muted/40 p-0.5',
        className,
      )}
    >
      {OPTIONS.map(({ value, label: optionLabel, Icon }) => {
        const isActive = view === value;
        return (
          <CustomButton
            key={value}
            type="text"
            size="sm"
            onClick={() => onChange(value)}
            aria-pressed={isActive}
            aria-label={optionLabel}
            className={cn(
              'h-7 w-7 items-center justify-center rounded p-0 transition',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon className="size-3.5" />
          </CustomButton>
        );
      })}
    </div>
  );
}
