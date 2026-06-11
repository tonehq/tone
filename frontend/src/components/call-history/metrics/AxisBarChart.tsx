import { cn } from '@/utils/cn';

export interface ReferenceLine {
  value: number;
  label: string;
  color?: 'red' | 'emerald' | 'amber' | 'sky' | 'violet';
}

interface AxisBarChartProps {
  values: number[];
  formatValue: (value: number) => string;
  xAxisLabel?: string;
  referenceLines?: ReferenceLine[];
  /**
   * Optional per-bar labels for the x-axis. When omitted, bars are
   * labelled 1..N (the historical behaviour). Used by the per-turn
   * latency charts so every chart shares the same turn-number axis.
   */
  xLabels?: string[];
}

const CHART_HEIGHT = 140;
const Y_TICKS = 4;
const MIN_BAR_WIDTH = 18;
const BAR_GAP = 4;

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

export function AxisBarChart({
  values,
  formatValue,
  xAxisLabel = 'Sample',
  referenceLines,
  xLabels,
}: AxisBarChartProps) {
  const labelFor = (i: number) => xLabels?.[i] ?? String(i + 1);
  const max = Math.max(...values, 0);
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
        <div style={{ minWidth: values.length * (MIN_BAR_WIDTH + BAR_GAP) }}>
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
              {values.map((v, i) => {
                const heightPct = scaleMax > 0 ? Math.max((v / scaleMax) * 100, 1.5) : 1.5;
                return (
                  <div
                    key={i}
                    className="group relative flex-1 rounded-t bg-primary/60 transition-colors hover:bg-primary"
                    style={{ height: `${heightPct}%`, minWidth: MIN_BAR_WIDTH }}
                    title={`${xAxisLabel} ${labelFor(i)}: ${formatValue(v)}`}
                  />
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
            {values.map((_, i) => (
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
