'use client';

import { CalendarDays, ChevronDown, Clock } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import type { DateRange } from 'react-day-picker';

import CustomButton from '@/components/shared/CustomButton';
import CustomPopover from '@/components/shared/CustomPopover';
import TimezoneSelect from '@/components/shared/TimezoneSelect';
import { Calendar } from '@/components/ui/calendar';
import type { DateRangePickerProps } from '@/types/components';
import { cn } from '@/utils/cn';
import { combineToIso, formatTzDateTime, getBrowserTimeZone, splitFromIso } from '@/utils/date';

export type { DateRangePickerProps, DateRangeValue } from '@/types/components';

const BROWSER_TZ = getBrowserTimeZone();

const PRESETS: Array<{ key: string; label: string; title: string; ms: number }> = [
  { key: '15m', label: '15m', title: 'Last 15 minutes', ms: 15 * 60_000 },
  { key: '30m', label: '30m', title: 'Last 30 minutes', ms: 30 * 60_000 },
  { key: '1h', label: '1h', title: 'Last 1 hour', ms: 60 * 60_000 },
  { key: '24h', label: '24h', title: 'Last 24 hours', ms: 24 * 60 * 60_000 },
  { key: '7d', label: '7d', title: 'Last 7 days', ms: 7 * 24 * 60 * 60_000 },
];

/** `Jun 5, 2026` for the Start/End summary rows. */
function formatDayLabel(day?: Date): string {
  if (!day) return 'Select a day';
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(day);
}

/**
 * Shared, timezone-aware date-range picker (calendar + start/end date & time +
 * relative presets + IANA timezone). Emits `{ start, end, timeZone }` where
 * start/end are UTC ISO instants. Drafts live inside the popover until Apply.
 */
const DateRangePicker: React.FC<DateRangePickerProps> = ({
  value,
  onChange,
  placeholder = 'Select date range',
  presets = true,
  align = 'start',
  className,
  triggerClassName,
  disabled,
}) => {
  const [open, setOpen] = useState(false);
  const [range, setRange] = useState<DateRange | undefined>(undefined);
  const [startTime, setStartTime] = useState('00:00');
  const [endTime, setEndTime] = useState('23:59');
  const [timeZone, setTimeZone] = useState(value?.timeZone || BROWSER_TZ);
  const [activePreset, setActivePreset] = useState<string | null>(null);

  // Seed the draft from the applied value every time the popover opens.
  useEffect(() => {
    if (!open) return;
    const tz = value?.timeZone || BROWSER_TZ;
    setTimeZone(tz);
    setActivePreset(null);
    if (value?.start && value?.end) {
      const s = splitFromIso(value.start, tz);
      const e = splitFromIso(value.end, tz);
      setRange({ from: s.day, to: e.day });
      setStartTime(s.time);
      setEndTime(e.time);
    } else {
      setRange(undefined);
      setStartTime('00:00');
      setEndTime('23:59');
    }
  }, [open, value?.start, value?.end, value?.timeZone]);

  // Manual edits to the calendar/time clear the highlighted preset.
  const handleSelectRange = (next: DateRange | undefined) => {
    setRange(next);
    setActivePreset(null);
  };

  const applyPreset = (key: string, ms: number) => {
    const now = new Date();
    const from = new Date(now.getTime() - ms);
    const s = splitFromIso(from.toISOString(), timeZone);
    const e = splitFromIso(now.toISOString(), timeZone);
    setRange({ from: s.day, to: e.day });
    setStartTime(s.time);
    setEndTime(e.time);
    setActivePreset(key);
  };

  const handleApply = () => {
    if (!range?.from) {
      onChange?.({ start: null, end: null, timeZone });
      setOpen(false);
      return;
    }
    const to = range.to ?? range.from;
    onChange?.({
      start: combineToIso(range.from, startTime, timeZone),
      end: combineToIso(to, endTime, timeZone),
      timeZone,
    });
    setOpen(false);
  };

  const handleClear = () => {
    setRange(undefined);
    onChange?.({ start: null, end: null, timeZone });
    setOpen(false);
  };

  const hasValue = !!(value?.start && value?.end);
  const triggerLabel = hasValue
    ? `${formatTzDateTime(value!.start!, value!.timeZone)} – ${formatTzDateTime(
        value!.end!,
        value!.timeZone,
      )}`
    : placeholder;

  return (
    <CustomPopover
      open={open}
      onOpenChange={setOpen}
      modal
      align={align}
      width="w-[360px]"
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
          aria-label="Select date range"
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
          <CustomButton type="text" size="sm" onClick={handleClear} disabled={!range?.from}>
            Clear
          </CustomButton>
          <CustomButton type="primary" size="sm" onClick={handleApply}>
            Apply
          </CustomButton>
        </>
      }
    >
      {presets && (
        <div className="flex flex-wrap gap-1.5 border-b border-border pb-2.5">
          {PRESETS.map((p) => (
            <CustomButton
              key={p.key}
              type="default"
              size="xs"
              title={p.title}
              onClick={() => applyPreset(p.key, p.ms)}
              className={cn(
                'rounded-full px-2.5 font-medium transition-colors',
                activePreset === p.key
                  ? 'border-primary/40 bg-primary/10 text-primary hover:bg-primary/15'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {p.label}
            </CustomButton>
          ))}
        </div>
      )}

      <div className="flex justify-center">
        <Calendar
          mode="range"
          selected={range}
          onSelect={handleSelectRange}
          numberOfMonths={1}
          defaultMonth={range?.from}
        />
      </div>

      <div className="divide-y divide-border overflow-hidden rounded-lg border border-border">
        {(['start', 'end'] as const).map((which) => {
          const day = which === 'start' ? range?.from : (range?.to ?? range?.from);
          const time = which === 'start' ? startTime : endTime;
          const setTime = which === 'start' ? setStartTime : setEndTime;
          return (
            <div key={which} className="flex items-center gap-2 px-2.5 py-2">
              <span className="w-10 shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {which}
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
                  onChange={(e) => {
                    setTime(e.target.value);
                    setActivePreset(null);
                  }}
                  aria-label={`${which} time`}
                  className="h-8 w-[104px] bg-transparent pr-2 text-sm tabular-nums outline-none"
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-3">
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Timezone
        </span>
        <div className="min-w-0 flex-1">
          <TimezoneSelect name="drp-timezone" value={timeZone} onValueChange={setTimeZone} />
        </div>
      </div>
    </CustomPopover>
  );
};

export default React.memo(DateRangePicker);
