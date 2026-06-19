import { cn } from '@/utils/cn';

export interface StackedSeriesDatum {
  /** X-axis label for the turn group (e.g. `"1"`, `"2"`). */
  label: string;
  /** Values per series in the same order as `series` prop. Null = no segment. */
  values: (number | null)[];
}

export interface StackedSeriesMeta {
  key: string;
  label: string;
  /** Tailwind classes for the segment fill and its hover state. */
  barClass: string;
  /** Tailwind class for the legend swatch / tooltip dot. */
  dotClass: string;
}

interface StackedTurnLatencyChartProps {
  /** One entry per turn; `values` length must equal `series` length. */
  data: StackedSeriesDatum[];
  series: StackedSeriesMeta[];
  formatValue: (value: number) => string;
  xAxisLabel?: string;
}

const CHART_HEIGHT = 160;
const Y_TICKS = 4;
const BAR_WIDTH = 28;
const BAR_GAP = 14;

/**
 * Stacked bar chart: one bar per x-tick, divided into colored segments — one
 * per series.
 *
 * Used by the per-turn latency overview where each turn has a single bar with
 * three segments (LLM / STT / TTS) stacked bottom-to-top. The bar's total
 * height is the sum of the three TTFBs for that turn; each segment's height
 * within the bar shows that service's share.
 *
 * Null/zero values render nothing (the segment is omitted). The y-axis scale
 * is the max stacked total across all turns.
 */
export function StackedTurnLatencyChart({
  data,
  series,
  formatValue,
  xAxisLabel = 'Turn',
}: StackedTurnLatencyChartProps) {
  const totals = data.map((d) => d.values.reduce<number>((acc, v) => acc + (v ?? 0), 0));
  const max = totals.length > 0 ? Math.max(...totals) : 0;
  const scaleMax = max > 0 ? max : 1;

  const ticks = Array.from({ length: Y_TICKS + 1 }, (_, i) => (scaleMax * i) / Y_TICKS).reverse();

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        {series.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span className={cn('inline-block size-2.5 rounded-sm', s.dotClass)} />
            <span>{s.label}</span>
          </span>
        ))}
      </div>

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
          <div style={{ minWidth: data.length * (BAR_WIDTH + BAR_GAP) }}>
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
                className="absolute inset-y-0 left-2 right-2 flex items-end"
                style={{ gap: BAR_GAP }}
              >
                {data.map((group, gi) => {
                  const total = totals[gi];
                  const barHeightPct = total > 0 ? (total / scaleMax) * 100 : 0;
                  return (
                    <div
                      key={gi}
                      className="flex flex-col-reverse overflow-hidden rounded-t"
                      style={{ width: BAR_WIDTH, height: `${barHeightPct}%` }}
                      title={`${xAxisLabel} ${group.label}: total ${formatValue(total)}`}
                    >
                      {group.values.map((v, si) => {
                        if (v == null || v <= 0) return null;
                        const meta = series[si];
                        const segmentPct = total > 0 ? (v / total) * 100 : 0;
                        return (
                          <div
                            key={meta.key}
                            className={cn('transition-colors', meta.barClass)}
                            style={{ height: `${segmentPct}%` }}
                            title={`${meta.label} · ${xAxisLabel} ${group.label}: ${formatValue(v)}`}
                          />
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>

            <div
              className="mt-1 flex px-2 text-[10px] text-muted-foreground"
              style={{ gap: BAR_GAP }}
            >
              {data.map((group, gi) => (
                <span key={gi} className="text-center" style={{ width: BAR_WIDTH }}>
                  {group.label}
                </span>
              ))}
            </div>
            <p className="mt-1 text-center text-xs text-muted-foreground">{xAxisLabel}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
