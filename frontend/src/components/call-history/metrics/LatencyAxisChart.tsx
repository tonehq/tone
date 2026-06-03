interface LatencyAxisChartProps {
  latencies: number[];
}

const CHART_HEIGHT = 140;
const Y_TICKS = 4;
const MIN_BAR_WIDTH = 18;
const BAR_GAP = 4;

export function LatencyAxisChart({ latencies }: LatencyAxisChartProps) {
  const max = Math.max(...latencies, 0);
  const avg = latencies.reduce((s, v) => s + v, 0) / latencies.length;
  const scaleMax = max > 0 ? max : 1;

  const ticks = Array.from({ length: Y_TICKS + 1 }, (_, i) => (scaleMax * i) / Y_TICKS).reverse();

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">Latency by measurement</span>
        <span className="text-xs text-muted-foreground">
          {latencies.length} measurement{latencies.length !== 1 ? 's' : ''}
        </span>
      </div>
      <div className="mb-3 flex gap-4">
        <div>
          <p className="text-xs text-muted-foreground">Avg</p>
          <p className="text-sm font-semibold text-foreground">{avg.toFixed(3)}s</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Max</p>
          <p className="text-sm font-semibold text-foreground">{max.toFixed(3)}s</p>
        </div>
      </div>

      <div className="flex min-w-0">
        <div
          className="mr-2 flex flex-col justify-between text-right text-[10px] text-muted-foreground"
          style={{ height: CHART_HEIGHT }}
          aria-hidden
        >
          {ticks.map((t, i) => (
            <span key={i}>{t.toFixed(2)}s</span>
          ))}
        </div>

        <div className="min-w-0 flex-1 overflow-x-auto">
          <div
            style={{
              minWidth: latencies.length * (MIN_BAR_WIDTH + BAR_GAP),
            }}
          >
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
                {latencies.map((v, i) => {
                  const heightPct = scaleMax > 0 ? Math.max((v / scaleMax) * 100, 1.5) : 1.5;
                  return (
                    <div
                      key={i}
                      className="group relative flex-1 rounded-t bg-primary/60 transition-colors hover:bg-primary"
                      style={{ height: `${heightPct}%`, minWidth: MIN_BAR_WIDTH }}
                      title={`Measurement ${i + 1}: ${v.toFixed(3)}s`}
                    />
                  );
                })}
              </div>
            </div>

            <div
              className="mt-1 flex px-1 text-[10px] text-muted-foreground"
              style={{ gap: BAR_GAP }}
            >
              {latencies.map((_, i) => (
                <span key={i} className="flex-1 text-center" style={{ minWidth: MIN_BAR_WIDTH }}>
                  {i + 1}
                </span>
              ))}
            </div>
            <p className="mt-1 text-center text-xs text-muted-foreground">Measurement</p>
          </div>
        </div>
      </div>
    </div>
  );
}
