'use client';

import { CustomButton } from '@/components/shared';
import { cn } from '@/utils/cn';
import { useMemo, useState } from 'react';

import { type ReferenceLine } from './AxisBarChart';
import { computeMedian, computePercentile } from './utils';

/**
 * Single source of truth for the latency-chart stat chips (Avg, Median, Min,
 * Max, P99). Both `TurnLatencySection` and `LatencyAxisChart` consume the
 * `useLatencyStats` hook + `<LatencyStatChips />` component below — adding a
 * new stat (or recoloring one) is a one-line change here that lights up
 * everywhere.
 */

export type StatKey = 'avg' | 'median' | 'min' | 'max' | 'p99';

interface StatMeta {
  label: string;
  color: NonNullable<ReferenceLine['color']>;
  dot: string;
}

// Display order = render order of the chip row.
export const STAT_META: Record<StatKey, StatMeta> = {
  avg: { label: 'Avg', color: 'violet', dot: 'bg-violet-500' },
  median: { label: 'Median', color: 'sky', dot: 'bg-sky-500' },
  min: { label: 'Min', color: 'emerald', dot: 'bg-emerald-500' },
  max: { label: 'Max', color: 'red', dot: 'bg-red-500' },
  p99: { label: 'P99', color: 'amber', dot: 'bg-amber-500' },
};

const STAT_KEYS = Object.keys(STAT_META) as StatKey[];

export type LatencyStats = Record<StatKey, number>;

export function computeStats(values: number[]): LatencyStats {
  if (values.length === 0) {
    return { avg: 0, median: 0, min: 0, max: 0, p99: 0 };
  }
  const sum = values.reduce((s, v) => s + v, 0);
  return {
    avg: sum / values.length,
    median: computeMedian(values),
    min: Math.min(...values),
    max: Math.max(...values),
    p99: computePercentile(values, 0.99),
  };
}

interface UseLatencyStatsOptions {
  /** Stats whose reference line should be visible on first render. */
  defaultVisible?: readonly StatKey[];
}

interface UseLatencyStatsResult {
  stats: LatencyStats;
  sampleCount: number;
  visible: Set<StatKey>;
  toggle: (key: StatKey) => void;
  /** Pre-built reference lines for the chart, using `format` for labels. */
  buildReferenceLines: (format: (v: number) => string) => ReferenceLine[];
}

/**
 * Owns the computed stats + the visible-set toggle state for one chart.
 * Format is intentionally NOT taken here so the same hook can drive callers
 * that display stats with different precision than their chart axis.
 */
export function useLatencyStats(
  values: number[],
  { defaultVisible }: UseLatencyStatsOptions = {},
): UseLatencyStatsResult {
  const stats = useMemo(() => computeStats(values), [values]);
  const sampleCount = values.length;

  const [visible, setVisible] = useState<Set<StatKey>>(() => new Set(defaultVisible ?? []));

  const toggle = (key: StatKey) =>
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const buildReferenceLines = (format: (v: number) => string): ReferenceLine[] =>
    STAT_KEYS.filter((k) => visible.has(k)).map((k) => ({
      value: stats[k],
      label: `${STAT_META[k].label} ${format(stats[k])}`,
      color: STAT_META[k].color,
    }));

  return { stats, sampleCount, visible, toggle, buildReferenceLines };
}

interface LatencyStatChipsProps {
  stats: LatencyStats;
  visible: Set<StatKey>;
  onToggle: (key: StatKey) => void;
  /** How to render each chip's numeric value (and reference-line labels). */
  format: (value: number) => string;
  /** Greys out all chips when there are no samples to summarize. */
  disabled?: boolean;
  /** Aria-label for the chip group. */
  ariaLabel: string;
}

/**
 * Renders the row of stat chips (Avg / Median / Min / Max / P99). Click a
 * chip to toggle its reference line on the adjacent chart. Pure
 * presentational — state lives in `useLatencyStats`.
 */
export function LatencyStatChips({
  stats,
  visible,
  onToggle,
  format,
  disabled = false,
  ariaLabel,
}: LatencyStatChipsProps) {
  return (
    <div role="group" aria-label={ariaLabel} className="mb-3 flex flex-wrap gap-1.5">
      {STAT_KEYS.map((key) => {
        const meta = STAT_META[key];
        const isOn = visible.has(key);
        return (
          <CustomButton
            key={key}
            type="text"
            size="sm"
            onClick={() => onToggle(key)}
            aria-pressed={isOn}
            disabled={disabled}
            className={cn(
              'h-auto items-start gap-1.5 rounded-md border border-transparent px-2 py-1 transition',
              isOn
                ? 'bg-muted/40 hover:bg-muted/60'
                : 'opacity-50 hover:opacity-100 hover:bg-muted/40',
            )}
          >
            <span className="flex flex-col items-start gap-0.5">
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <span
                  className={cn(
                    'inline-block size-1.5 rounded-full',
                    meta.dot,
                    !isOn && 'opacity-40',
                  )}
                />
                {meta.label}
              </span>
              <span className="text-sm font-semibold text-foreground">
                {disabled ? '—' : format(stats[key])}
              </span>
            </span>
          </CustomButton>
        );
      })}
    </div>
  );
}
