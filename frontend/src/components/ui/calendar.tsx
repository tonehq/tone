'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import * as React from 'react';
import { DayPicker } from 'react-day-picker';

import { cn } from '@/utils/cn';

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

/**
 * Thin shadcn-style wrapper around react-day-picker v9, themed with the
 * project's design tokens (no external stylesheet — every class is supplied
 * via `classNames` so light/dark parity comes from CSS variables).
 *
 * Range styling: `range_start`/`range_end` paint the inner day button primary,
 * `range_middle` tints the cell with `accent`. `selected` intentionally adds no
 * button colour so it never fights the range modifiers on the same cell.
 */
function Calendar({ className, classNames, showOutsideDays = true, ...props }: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn('p-0', className)}
      classNames={{
        months: 'flex flex-col gap-4',
        month: 'flex flex-col gap-3',
        month_caption: 'relative flex h-8 items-center pt-1',
        caption_label: 'text-sm font-semibold text-foreground',
        nav: 'absolute right-0 top-0 flex items-center gap-1',
        button_previous:
          'inline-flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40',
        button_next:
          'inline-flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40',
        month_grid: 'border-collapse',
        weekdays: 'flex',
        weekday: 'w-11 text-[0.68rem] font-medium uppercase tracking-wide text-muted-foreground/70',
        week: 'mt-1 flex',
        // Cell width must match the weekday width (w-11) so the header and dates
        // stay column-aligned; the day button is centered inside the cell.
        day: 'relative flex w-11 items-center justify-center p-0 text-center text-sm focus-within:relative focus-within:z-20',
        day_button:
          'inline-flex size-10 cursor-pointer items-center justify-center rounded-full p-0 font-normal tabular-nums text-foreground transition-colors hover:bg-accent hover:text-foreground',
        // Continuous brand band: endpoints are solid-primary circles, the days
        // between get a soft primary tint with rounded outer ends.
        range_start:
          'rounded-l-full bg-primary/10 [&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:shadow-sm [&>button]:hover:bg-primary',
        range_end:
          'rounded-r-full bg-primary/10 [&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:shadow-sm [&>button]:hover:bg-primary',
        range_middle:
          'bg-primary/10 [&>button]:bg-transparent [&>button]:text-foreground [&>button]:hover:bg-primary/20',
        today:
          '[&>button]:font-semibold [&>button]:ring-1 [&>button]:ring-inset [&>button]:ring-ring/50',
        outside: 'text-muted-foreground/40',
        disabled: 'text-muted-foreground opacity-40',
        hidden: 'invisible',
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation, className: chevronClass, ...chevronProps }) =>
          orientation === 'left' ? (
            <ChevronLeft className={cn('size-4', chevronClass)} {...chevronProps} />
          ) : (
            <ChevronRight className={cn('size-4', chevronClass)} {...chevronProps} />
          ),
      }}
      {...props}
    />
  );
}

Calendar.displayName = 'Calendar';

export { Calendar };
