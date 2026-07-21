'use client';

import { CalendarDays, ChevronDown, Clock } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import CustomButton from '@/components/shared/CustomButton';
import CustomPopover from '@/components/shared/CustomPopover';
import TimezoneSelect from '@/components/shared/TimezoneSelect';
import { Calendar } from '@/components/ui/calendar';
import type { DateTimePickerProps } from '@/types/components';
import { cn } from '@/utils/cn';
import { combineToIso, formatTzDateTime, getBrowserTimeZone, splitFromIso } from '@/utils/date';

export type { DateTimePickerProps, DateTimeValue } from '@/types/components';

const BROWSER_TZ = getBrowserTimeZone();

/** `Jun 5, 2026` for the summary row. */
function formatDayLabel(day?: Date): string {
  if (!day) return 'Select a day';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(day);
}

/**
 * Shared, timezone-aware **single-instant** picker (calendar + `HH:mm` time + IANA
 * timezone), styled to match {@link DateRangePicker}. Emits `{ value, timeZone }` where
 * `value` is a UTC ISO instant — the form the backend's `scheduled_at` expects. No range,
 * no relative presets. Drafts live inside the popover until Apply.
 */
const DateTimePicker: React.FC<DateTimePickerProps> = ({
  value,
  onChange,
  placeholder = 'Select date & time',
  align = 'start',
  className,
  triggerClassName,
  disabled,
}) => {
  const [open, setOpen] = useState(false);
  const [day, setDay] = useState<Date | undefined>(undefined);
  const [time, setTime] = useState('09:00');
  const [timeZone, setTimeZone] = useState(value?.timeZone || BROWSER_TZ);

  // Seed the draft from the applied value every time the popover opens.
  useEffect(() => {
    if (!open) return;
    const tz = value?.timeZone || BROWSER_TZ;
    setTimeZone(tz);
    if (value?.value) {
      const s = splitFromIso(value.value, tz);
      setDay(s.day);
      setTime(s.time);
    } else {
      setDay(undefined);
      setTime('09:00');
    }
  }, [open, value?.value, value?.timeZone]);

  const handleApply = () => {
    if (!day) {
      onChange?.({ value: null, timeZone });
      setOpen(false);
      return;
    }
    onChange?.({ value: combineToIso(day, time, timeZone), timeZone });
    setOpen(false);
  };

  const handleClear = () => {
    setDay(undefined);
    onChange?.({ value: null, timeZone });
    setOpen(false);
  };

  const hasValue = !!value?.value;
  const triggerLabel = hasValue ? formatTzDateTime(value!.value!, value!.timeZone) : placeholder;

  return (
    <CustomPopover
      open={open}
      onOpenChange={setOpen}
      modal
      align={align}
      width="w-[320px]"
      className={cn(
        'flex max-h-[min(85vh,var(--radix-popover-content-available-height))] flex-col overflow-hidden',
        className,
      )}
      contentClassName="min-h-0 max-h-none flex-1 space-y-2.5 px-2 py-2.5"
      trigger={
        <CustomButton
          type="default"
          size="sm"
          disabled={disabled}
          aria-label="Select date and time"
          className={cn(
            'justify-start gap-2 font-normal',
            hasValue
              ? 'border-solid border-primary/40 bg-primary/5 text-foreground hover:bg-primary/10'
              : 'border-dashed text-muted-foreground',
            triggerClassName,
          )}
        >
          <CalendarDays
            className={cn('size-4 shrink-0', hasValue ? 'text-primary' : 'text-muted-foreground')}
          />
          <span className="truncate">{triggerLabel}</span>
          <ChevronDown className="ml-auto size-4 shrink-0 opacity-60" />
        </CustomButton>
      }
      footer={
        <>
          <CustomButton type="text" size="sm" onClick={handleClear} disabled={!day}>
            Clear
          </CustomButton>
          <CustomButton type="primary" size="sm" onClick={handleApply}>
            Apply
          </CustomButton>
        </>
      }
    >
      <div className="flex justify-center">
        <Calendar
          mode="single"
          selected={day}
          onSelect={setDay}
          numberOfMonths={1}
          defaultMonth={day}
          // The shared Calendar leaves `selected` unstyled (so it never fights the range
          // modifiers in DateRangePicker). This is single-select, so give the chosen day a
          // clear filled highlight here.
          classNames={{
            selected:
              '[&>button]:bg-primary [&>button]:font-medium [&>button]:text-primary-foreground [&>button]:hover:bg-primary [&>button]:hover:text-primary-foreground',
          }}
        />
      </div>

      <div className="overflow-hidden rounded-lg border border-border">
        <div className="flex items-center gap-2 px-2.5 py-2">
          <span className="w-10 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            When
          </span>
          <div className="flex min-w-0 flex-1 items-center gap-1.5 text-sm">
            <CalendarDays className="size-3.5 shrink-0 text-muted-foreground" />
            <span className={cn('truncate tabular-nums', !day && 'text-muted-foreground')}>
              {formatDayLabel(day)}
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 rounded-md border border-input bg-background pl-2 transition-colors focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/30">
            <Clock className="size-3.5 shrink-0 text-muted-foreground" />
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              aria-label="time"
              className="h-8 w-[104px] bg-transparent pr-2 text-sm tabular-nums outline-none"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Timezone
        </span>
        <div className="min-w-0 flex-1">
          <TimezoneSelect name="dtp-timezone" value={timeZone} onValueChange={setTimeZone} />
        </div>
      </div>
    </CustomPopover>
  );
};

export default React.memo(DateTimePicker);
