'use client';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';
import { ArrowDown, ArrowUp, ArrowUpDown, type LucideIcon } from 'lucide-react';

export type SortDirection = 'natural' | 'asc' | 'desc';

interface SortToggleProps {
  value: SortDirection;
  onChange: (next: SortDirection) => void;
  /** Accessible label describing what the toggle sorts. */
  label?: string;
  className?: string;
}

interface OptionMeta {
  value: SortDirection;
  label: string;
  Icon: LucideIcon;
}

const OPTIONS: OptionMeta[] = [
  { value: 'natural', label: 'Original order', Icon: ArrowUpDown },
  { value: 'asc', label: 'Sort ascending', Icon: ArrowUp },
  { value: 'desc', label: 'Sort descending', Icon: ArrowDown },
];

/**
 * Three-option sort control (turn order / asc / desc) styled to match
 * [[ChartTableToggle]]. Controlled — the parent owns the sort state.
 */
export function SortToggle({ value, onChange, label, className }: SortToggleProps) {
  return (
    <div
      role="group"
      aria-label={label ?? 'Sort order'}
      className={cn(
        'inline-flex items-center gap-0.5 rounded-md border border-border bg-muted/40 p-0.5',
        className,
      )}
    >
      {OPTIONS.map(({ value: optionValue, label: optionLabel, Icon }) => {
        const isActive = value === optionValue;
        return (
          <CustomButton
            key={optionValue}
            type="text"
            size="sm"
            onClick={() => onChange(optionValue)}
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
