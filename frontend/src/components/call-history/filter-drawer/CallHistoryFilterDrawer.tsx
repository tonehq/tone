'use client';

import { CustomButton, CustomDrawer, DateRangePicker } from '@/components/shared';
import { Slider } from '@/components/ui/slider';
import type { CallFilterState, CallHistoryFilterDrawerProps } from '@/types/callHistoryFilters';
import React, { useEffect, useState } from 'react';

import {
  countDrawerFilters,
  createEmptyFilterState,
  DRAWER_FACET_SECTIONS,
  isLatencyActive,
  LATENCY_STEP,
  MAX_LATENCY_SECONDS,
  MIN_LATENCY_SECONDS,
} from './constants';
import FacetSection from './FacetSection';
import FilterSection from './FilterSection';

const CallHistoryFilterDrawer: React.FC<CallHistoryFilterDrawerProps> = ({
  open,
  onClose,
  value,
  facets,
  facetsLoading,
  onApply,
}) => {
  const [draft, setDraft] = useState<CallFilterState>(value);

  // Re-seed the draft from the applied value every time the drawer opens.
  useEffect(() => {
    if (open) setDraft(value);
  }, [open, value]);

  const toggleFacet = (field: string, val: string) => {
    setDraft((prev) => {
      const current = prev.facets[field] ?? [];
      const next = current.includes(val) ? current.filter((v) => v !== val) : [...current, val];
      const facetsNext = { ...prev.facets };
      if (next.length) facetsNext[field] = next;
      else delete facetsNext[field];
      return { ...prev, facets: facetsNext };
    });
  };

  // Reset all drawer filters (date, facets, turns, latency).
  const handleReset = () => setDraft((prev) => createEmptyFilterState(prev.dateRange.timeZone));

  const handleApply = () => {
    onApply(draft);
    onClose();
  };

  const drawerActiveCount = countDrawerFilters(draft);

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title="Filters"
      description="Narrow call history by time, status, agent, pipeline and metrics."
      side="right"
      width="w-full sm:max-w-[420px]"
      contentClassName="px-6 pb-6"
      footer={
        <div className="flex items-center justify-between gap-2">
          <CustomButton
            type="text"
            size="sm"
            onClick={handleReset}
            disabled={drawerActiveCount === 0}
          >
            Reset
          </CustomButton>
          <CustomButton type="primary" size="sm" onClick={handleApply}>
            Apply
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col">
        <FilterSection
          title="Timeline"
          count={draft.dateRange.start && draft.dateRange.end ? 1 : 0}
          defaultOpen={false}
        >
          <DateRangePicker
            value={draft.dateRange}
            onChange={(dateRange) => setDraft((p) => ({ ...p, dateRange }))}
            triggerClassName="w-full"
          />
        </FilterSection>

        {DRAWER_FACET_SECTIONS.map((s) => (
          <FacetSection
            key={s.field}
            field={s.field}
            label={s.label}
            titleCase={s.titleCase}
            values={facets[s.field] ?? []}
            selected={draft.facets[s.field] ?? []}
            loading={facetsLoading}
            onToggle={toggleFacet}
          />
        ))}

        <FilterSection
          title="Turns"
          count={draft.minTurns.trim() !== '' || draft.maxTurns.trim() !== '' ? 1 : 0}
          defaultOpen={false}
        >
          <div className="flex items-center gap-2">
            <input
              type="number"
              inputMode="numeric"
              min={0}
              value={draft.minTurns}
              onChange={(e) => setDraft((p) => ({ ...p, minTurns: e.target.value }))}
              placeholder="From"
              aria-label="Minimum turns"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm tabular-nums shadow-xs outline-none transition-colors focus:border-ring focus:ring-[3px] focus:ring-ring/30"
            />
            <span className="text-sm text-muted-foreground">to</span>
            <input
              type="number"
              inputMode="numeric"
              min={0}
              value={draft.maxTurns}
              onChange={(e) => setDraft((p) => ({ ...p, maxTurns: e.target.value }))}
              placeholder="To"
              aria-label="Maximum turns"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm tabular-nums shadow-xs outline-none transition-colors focus:border-ring focus:ring-[3px] focus:ring-ring/30"
            />
          </div>
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            Calls with no metrics record are excluded when this range is set.
          </p>
        </FilterSection>

        <FilterSection
          title="Avg latency"
          count={isLatencyActive(draft.latency) ? 1 : 0}
          defaultOpen={false}
        >
          <div className="flex items-center justify-between pb-2">
            <span className="text-xs text-muted-foreground">Seconds</span>
            <span className="text-xs font-medium tabular-nums text-foreground">
              {draft.latency[0].toFixed(1)}s — {draft.latency[1].toFixed(1)}s
            </span>
          </div>
          <Slider
            min={MIN_LATENCY_SECONDS}
            max={MAX_LATENCY_SECONDS}
            step={LATENCY_STEP}
            value={draft.latency}
            onValueChange={(values) => {
              const [a = MIN_LATENCY_SECONDS, b = MAX_LATENCY_SECONDS] = values;
              setDraft((p) => ({ ...p, latency: a <= b ? [a, b] : [b, a] }));
            }}
            aria-label="Average latency range"
          />
          <div className="flex items-center justify-between pt-1 text-[10px] text-muted-foreground">
            <span>{MIN_LATENCY_SECONDS}s</span>
            <span>{MAX_LATENCY_SECONDS}s</span>
          </div>
        </FilterSection>
      </div>
    </CustomDrawer>
  );
};

export default CallHistoryFilterDrawer;
