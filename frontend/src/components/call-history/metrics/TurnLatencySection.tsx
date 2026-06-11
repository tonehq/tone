'use client';

import { CustomButton } from '@/components/shared';
import type { CallMetricsTurnMetric } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { LineChart } from 'lucide-react';
import { useState } from 'react';

import { AxisBarChart, type ReferenceLine } from './AxisBarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { computeMedian, formatMs } from './utils';

interface TurnLatencySectionProps {
  turns: CallMetricsTurnMetric[];
}

type StatKey = 'avg' | 'median' | 'min' | 'max';

const STAT_META: Record<
  StatKey,
  { label: string; color: NonNullable<ReferenceLine['color']>; dot: string }
> = {
  avg: { label: 'Avg', color: 'violet', dot: 'bg-violet-500' },
  median: { label: 'Median', color: 'sky', dot: 'bg-sky-500' },
  min: { label: 'Min', color: 'emerald', dot: 'bg-emerald-500' },
  max: { label: 'Max', color: 'red', dot: 'bg-red-500' },
};

const formatSeconds = (v: number) => `${v.toFixed(2)}s`;

/**
 * Treat 0.0 the same as null. Pipecat emits 0.0 only for placeholder cases
 * (e.g. the auto-greeting turn where TTFB wasn't actually measured); a real
 * measurement is always > 0. Skipping 0s keeps the stats honest.
 */
const sanitize = (v: number | null): number | null => (v == null || v <= 0 ? null : v);

/** Per-turn metric series: aligned with `turns` 1:1 (nulls preserved). */
interface MetricSeries {
  key: string;
  title: string;
  subtitle: string;
  format: (v: number) => string;
  values: (number | null)[];
}

/**
 * Turn-aligned latency breakdown.
 *
 * Renders one card per metric (STT TTFB, LLM TTFB, TTS TTFB, end-to-end).
 * All four cards share the same x-axis — the turn number — so they can be
 * read side-by-side without the "55 samples vs 31 samples" mismatch the
 * per-sample TTFB chart suffers from.
 */
export function TurnLatencySection({ turns }: TurnLatencySectionProps) {
  if (turns.length === 0) return null;

  // Keep only real conversation turns — those with a user→bot transition.
  // `end_to_end` is the canonical signal: it's only set when both
  // `user_stopped_at` and `bot_started_at` were captured. This drops:
  //   • the pre/inter-turn bucket (turn 0) — system events between turns
  //   • the agent's first greeting — bot spoke first, no preceding user input
  //   • abandoned turns where the bot never started speaking
  // The result is exactly "N user→bot exchanges" matching the user's mental
  // model. STT TTFB inside this window may still be null for individual turns
  // (when turn-stop fired before STT finalized) — those render as empty bars,
  // but the turn itself remains on the x-axis so every chart stays aligned.
  const sorted = [...turns].sort((a, b) => a.turn - b.turn).filter((t) => t.end_to_end != null);

  if (sorted.length === 0) return null;

  const turnLabels = sorted.map((t) => String(t.turn));

  const series: MetricSeries[] = [
    {
      key: 'stt',
      title: 'STT TTFB per Turn',
      subtitle: 'Speech-to-text first-text time',
      format: formatMs,
      values: sorted.map((t) => sanitize(t.stt_ttfb)),
    },
    {
      key: 'llm',
      title: 'LLM TTFB per Turn',
      subtitle: 'First token from the model',
      format: formatMs,
      values: sorted.map((t) => sanitize(t.llm_ttfb)),
    },
    {
      key: 'tts',
      title: 'TTS TTFB per Turn',
      subtitle: 'First audio chunk from TTS',
      format: formatMs,
      values: sorted.map((t) => sanitize(t.tts_ttfb)),
    },
    {
      key: 'end_to_end',
      title: 'End-to-End Latency per Turn',
      subtitle: 'User stopped → bot started speaking',
      format: formatSeconds,
      values: sorted.map((t) => sanitize(t.end_to_end)),
    },
  ];

  return (
    <div className="space-y-3">
      <SectionHeader icon={LineChart} title="Latency per Turn" />
      <div className="space-y-2">
        {series.map((s) => (
          <TurnMetricCard
            key={s.key}
            seriesKey={s.key}
            title={s.title}
            subtitle={s.subtitle}
            format={s.format}
            values={s.values}
            turnLabels={turnLabels}
          />
        ))}
      </div>
    </div>
  );
}

interface TurnMetricCardProps {
  seriesKey: string;
  title: string;
  subtitle: string;
  format: (v: number) => string;
  values: (number | null)[];
  turnLabels: string[];
}

/** Single per-metric card: chart/table toggle + stat reference lines. */
function TurnMetricCard({
  seriesKey,
  title,
  subtitle,
  format,
  values,
  turnLabels,
}: TurnMetricCardProps) {
  const present = values.filter((v): v is number => v != null);
  const sampleCount = present.length;

  const max = sampleCount > 0 ? Math.max(...present) : 0;
  const min = sampleCount > 0 ? Math.min(...present) : 0;
  const median = computeMedian(present);
  const avg = sampleCount > 0 ? present.reduce((s, v) => s + v, 0) / sampleCount : 0;

  const stats: Record<StatKey, number> = { avg, median, min, max };

  const [visible, setVisible] = useState<Set<StatKey>>(() => new Set());
  const { view, toggle: viewToggle } = useChartTableView('chart', `${title} view`);

  const toggle = (key: StatKey) =>
    setVisible((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const referenceLines: ReferenceLine[] = (Object.keys(STAT_META) as StatKey[])
    .filter((key) => visible.has(key))
    .map((key) => ({
      value: stats[key],
      label: `${STAT_META[key].label} ${format(stats[key])}`,
      color: STAT_META[key].color,
    }));

  // Chart needs a number per bar — null turns become 0 (no bar visible) but
  // the x-axis slot is preserved so all four charts stay turn-aligned.
  const chartValues = values.map((v) => (v == null ? 0 : v));

  const rows = values.map((v, i) => ({
    turn: turnLabels[i],
    value: v,
  }));

  const columns: MetricsTableColumn<{ turn: string; value: number | null }>[] = [
    { key: 'turn', header: 'Turn', align: 'left', width: 'w-16', cell: (row) => row.turn },
    {
      key: 'value',
      header: title.replace(' per Turn', ''),
      align: 'right',
      cell: (row) =>
        row.value == null ? <span className="text-muted-foreground">—</span> : format(row.value),
    },
  ];

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <span className="text-sm font-medium text-foreground">{title}</span>
          <span className="ml-2 text-xs text-muted-foreground">{subtitle}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {sampleCount} of {values.length} turn{values.length !== 1 ? 's' : ''}
          </span>
          {viewToggle}
        </div>
      </div>

      {view === 'chart' ? (
        <>
          <div
            role="group"
            aria-label={`Toggle reference lines for ${seriesKey}`}
            className="mb-3 flex flex-wrap gap-1.5"
          >
            {(Object.keys(STAT_META) as StatKey[]).map((key) => {
              const meta = STAT_META[key];
              const isOn = visible.has(key);
              return (
                <CustomButton
                  key={key}
                  type="text"
                  size="sm"
                  onClick={() => toggle(key)}
                  aria-pressed={isOn}
                  disabled={sampleCount === 0}
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
                      {sampleCount === 0 ? '—' : format(stats[key])}
                    </span>
                  </span>
                </CustomButton>
              );
            })}
          </div>
          <AxisBarChart
            values={chartValues}
            formatValue={format}
            xAxisLabel="Turn"
            xLabels={turnLabels}
            referenceLines={referenceLines}
          />
        </>
      ) : (
        <MetricsDataTable columns={columns} rows={rows} />
      )}
    </div>
  );
}
