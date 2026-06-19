import { cn } from '@/utils/cn';

import { type ReferenceLine } from './AxisBarChart';

interface StackedCallsBarChartProps {
  /**
   * One entry per x-tick = the per-call values for that turn (already
   * sanitized — drop nulls/zeros before passing). An empty array renders
   * no bar for that turn (the slot stays reserved so the axis keeps its
   * shape).
   */
  stacks: number[][];
  formatValue: (value: number) => string;
  xAxisLabel?: string;
  xLabels?: string[];
  referenceLines?: ReferenceLine[];
}

const CHART_HEIGHT = 140;
const Y_TICKS = 4;
const MIN_BAR_WIDTH = 22;
const BAR_GAP = 4;

/**
 * Rotated per-call palette. Each segment within a turn gets a distinct hue so
 * a turn with multiple calls is visually obvious (call 1 emerald, call 2
 * sky, call 3 amber, call 4 violet, …). A turn with one call just shows the
 * first color — same visual feel as a single-color bar.
 */
const CALL_PALETTE = [
  'bg-emerald-500/70 hover:bg-emerald-500',
  'bg-sky-500/70 hover:bg-sky-500',
  'bg-amber-500/70 hover:bg-amber-500',
  'bg-violet-500/70 hover:bg-violet-500',
  'bg-rose-500/70 hover:bg-rose-500',
];

const REF_LINE_STYLES: Record<
  NonNullable<ReferenceLine['color']>,
  { line: string; label: string }
> = {
  red: { line: 'border-red-500/70', label: 'text-red-600 dark:text-red-400' },
  emerald: { line: 'border-emerald-500/70', label: 'text-emerald-600 dark:text-emerald-400' },
  amber: { line: 'border-amber-500/70', label: 'text-amber-600 dark:text-amber-400' },
  sky: { line: 'border-sky-500/70', label: 'text-sky-600 dark:text-sky-400' },
  violet: { line: 'border-violet-500/70', label: 'text-violet-600 dark:text-violet-400' },
};

/**
 * Per-turn bar chart where each turn's bar is split into one segment per
 * individual service call within that turn. Single bar color throughout;
 * thin dividers mark the call boundaries.
 *
 * Bar height = sum of the turn's per-call values. Y-axis scale = max total
 * across turns (or the largest reference line, whichever is higher).
 *
 * Stacks with a single element render as one solid bar (no internal divider),
 * so this can also stand in for a normal bar chart of one value per turn.
 */
export function StackedCallsBarChart({
  stacks,
  formatValue,
  xAxisLabel = 'Sample',
  referenceLines,
  xLabels,
}: StackedCallsBarChartProps) {
  const labelFor = (i: number) => xLabels?.[i] ?? String(i + 1);
  const totals = stacks.map((s) => s.reduce((acc, v) => acc + v, 0));
  const max = totals.length > 0 ? Math.max(...totals, 0) : 0;
  const refMax = referenceLines?.reduce((m, r) => Math.max(m, r.value), 0) ?? 0;
  const scaleMax = Math.max(max, refMax) > 0 ? Math.max(max, refMax) : 1;

  const ticks = Array.from({ length: Y_TICKS + 1 }, (_, i) => (scaleMax * i) / Y_TICKS).reverse();

  return (
    <div className="flex min-w-0">
      <div
        className="mr-2 flex flex-col justify-between text-right text-[10px] text-muted-foreground"
        style={{ height: CHART_HEIGHT }}
        aria-hidden
      >
        {ticks.map((t, i) => (
          <span key={i}>{formatValue(t)}</span>
        ))}
      </div>

      <div className="min-w-0 flex-1 overflow-x-auto">
        <div style={{ minWidth: stacks.length * (MIN_BAR_WIDTH + BAR_GAP) }}>
          <div
            className="relative border-b border-l border-border"
            style={{ height: CHART_HEIGHT }}
          >
            {ticks.map((_, i) =>
              i === ticks.length - 1 ? null : (
                <div
                  key={i}
                  className="absolute left-0 right-0 border-t border-dashed border-border/60"
                  style={{ top: `${(i / Y_TICKS) * 100}%` }}
                />
              ),
            )}

            <div
              className="absolute inset-y-0 left-1 right-1 flex items-end"
              style={{ gap: BAR_GAP }}
            >
              {stacks.map((segments, gi) => {
                const total = totals[gi];
                const barHeightPct = total > 0 ? Math.max((total / scaleMax) * 100, 1.5) : 0;
                return (
                  <div
                    key={gi}
                    className="flex flex-1 flex-col-reverse overflow-hidden rounded-t"
                    style={{ height: `${barHeightPct}%`, minWidth: MIN_BAR_WIDTH }}
                    title={
                      segments.length > 1
                        ? `${xAxisLabel} ${labelFor(gi)}: ${segments.length} calls, total ${formatValue(total)}`
                        : `${xAxisLabel} ${labelFor(gi)}: ${formatValue(total)}`
                    }
                  >
                    {segments.map((v, si) => {
                      const segmentPct = total > 0 ? (v / total) * 100 : 0;
                      return (
                        <div
                          key={si}
                          className={cn(
                            'transition-colors',
                            CALL_PALETTE[si % CALL_PALETTE.length],
                          )}
                          style={{ height: `${segmentPct}%` }}
                          title={`${xAxisLabel} ${labelFor(gi)} · call ${si + 1}: ${formatValue(v)}`}
                        />
                      );
                    })}
                  </div>
                );
              })}
            </div>

            {referenceLines?.map((line, i) => {
              const topPct = (1 - line.value / scaleMax) * 100;
              if (topPct < 0 || topPct > 100) return null;
              const styles = REF_LINE_STYLES[line.color ?? 'violet'];
              return (
                <div
                  key={`ref-${i}`}
                  className={cn(
                    'pointer-events-none absolute left-0 right-0 border-t-2 border-dashed',
                    styles.line,
                  )}
                  style={{ top: `${topPct}%` }}
                >
                  <span
                    className={cn(
                      'absolute -top-2 right-1 rounded bg-background px-1 text-[10px] font-medium',
                      styles.label,
                    )}
                  >
                    {line.label}
                  </span>
                </div>
              );
            })}
          </div>

          <div
            className="mt-1 flex px-1 text-[10px] text-muted-foreground"
            style={{ gap: BAR_GAP }}
          >
            {stacks.map((_, i) => (
              <span key={i} className="flex-1 text-center" style={{ minWidth: MIN_BAR_WIDTH }}>
                {labelFor(i)}
              </span>
            ))}
          </div>
          <p className="mt-1 text-center text-xs text-muted-foreground">{xAxisLabel}</p>
        </div>
      </div>
    </div>
  );
}
