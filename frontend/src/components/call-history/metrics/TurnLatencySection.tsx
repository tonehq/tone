'use client';

import type { CallMetricsTurnMetric } from '@/types/callLog';
import { LineChart } from 'lucide-react';

import { LatencyStatChips, useLatencyStats } from './LatencyStatChips';
import { SectionHeader } from './SectionHeader';
import { StackedCallsBarChart } from './StackedCallsBarChart';
import { type PerTurnUsageRow, TurnUsageTable } from './TurnUsageCard';
import { useChartTableView } from './useChartTableView';
import { formatMs, turnHasAnyMeasurement } from './utils';

interface TurnLatencySectionProps {
  turns: CallMetricsTurnMetric[];
}

const formatSeconds = (v: number) => `${v.toFixed(2)}s`;

/**
 * Drop placeholder zeros and nulls. Pipecat emits 0.0 only for cases where
 * TTFB wasn't actually measured (e.g. the auto-greeting turn); a real
 * measurement is always > 0. Skipping 0s keeps the stats honest.
 */
const cleanSamples = (raw: readonly (number | null)[] | null | undefined): number[] =>
  (raw ?? []).filter((v): v is number => v != null && v > 0);

/** Per-turn metric series: one stack of per-call values per turn. */
interface MetricSeries {
  key: string;
  title: string;
  subtitle: string;
  format: (v: number) => string;
  /** Per turn → per call values. Empty array = no measurement for that turn. */
  stacks: number[][];
}

/**
 * Turn-aligned latency breakdown.
 *
 * Renders one card per metric (STT TTFB, LLM TTFB, TTS TTFB, end-to-end).
 * The STT / LLM / TTS bars stack one segment per individual service call
 * inside the turn, so a turn with multiple LLM completions (e.g. a tool-call
 * follow-up) shows multiple segments instead of just the first. End-to-end
 * is one value per turn (the wall-clock user→bot gap), so its "stack" is a
 * single segment per turn.
 */
export function TurnLatencySection({ turns }: TurnLatencySectionProps) {
  if (turns.length === 0) return null;

  // Keep any real conversational turn (pipecat numbers them starting at 1)
  // with at least one measurement (LLM / STT / TTS or end_to_end). This
  // includes the greeting and any final partial turn. Turn 0 is an internal
  // pre/inter-turn bucket — not a conversational turn — and is always hidden.
  const sorted = [...turns]
    .sort((a, b) => a.turn - b.turn)
    .filter((t) => t.turn >= 1 && turnHasAnyMeasurement(t));

  if (sorted.length === 0) return null;

  // Display labels use the raw pipecat turn number so they line up with the
  // Tools & MCP Executions table (which also shows the raw turn number). A
  // gap in the sequence (e.g. 2, 3, 5, 6) is real — it means a filtered turn
  // sat in between (greeting / abandoned / pre-turn bucket).
  const turnLabels = sorted.map((t) => String(t.turn));

  const series: MetricSeries[] = [
    {
      key: 'stt',
      title: 'STT TTFB per Turn',
      subtitle: 'Speech-to-text first-text time',
      format: formatMs,
      stacks: sorted.map((t) => cleanSamples(t.stt_ttfb_all)),
    },
    {
      key: 'llm',
      title: 'LLM TTFB per Turn',
      subtitle: 'First token from the model',
      format: formatMs,
      stacks: sorted.map((t) => cleanSamples(t.llm_ttfb_all)),
    },
    {
      key: 'tts',
      title: 'TTS TTFB per Turn',
      subtitle: 'First audio chunk from TTS',
      format: formatMs,
      stacks: sorted.map((t) => cleanSamples(t.tts_ttfb_all)),
    },
    {
      key: 'end_to_end',
      title: 'End-to-End Latency per Turn',
      subtitle: 'User stopped → bot started speaking',
      format: formatSeconds,
      stacks: sorted.map((t) => cleanSamples([t.end_to_end])),
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
            stacks={s.stacks}
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
  stacks: number[][];
  turnLabels: string[];
}

/** Single per-metric card: chart/table toggle + stat reference lines. */
function TurnMetricCard({
  seriesKey,
  title,
  subtitle,
  format,
  stacks,
  turnLabels,
}: TurnMetricCardProps) {
  // Stats reflect what the bar visually represents: the per-turn TOTAL
  // (sum of all per-call values inside the turn). Turns with no measurement
  // are excluded so a placeholder zero doesn't drag the avg / min down.
  const turnTotals = stacks.map((s) => s.reduce((acc, v) => acc + v, 0)).filter((v) => v > 0);
  const { stats, sampleCount, visible, toggle, buildReferenceLines } = useLatencyStats(turnTotals);
  const { view, toggle: viewToggle } = useChartTableView('chart', `${title} view`);

  const referenceLines = buildReferenceLines(format);

  // Reshape into the same per-turn / per-call grouped table the Usage cards
  // use — Turn (rowSpan) | <metric> | Total (rowSpan), with one row per
  // call inside the turn. `calls` and `values` both carry the raw number;
  // there's no per-call metadata for TTFB so no cell subtext.
  const tableRows: PerTurnUsageRow<number>[] = stacks.map((segments, i) => ({
    turnLabel: turnLabels[i],
    calls: segments,
    values: segments,
    total: segments.reduce((acc, v) => acc + v, 0),
  }));
  const tableColumnHeader = title.replace(' per Turn', '');

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <span className="text-sm font-medium text-foreground">{title}</span>
          <span className="ml-2 text-xs text-muted-foreground">{subtitle}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {sampleCount} of {stacks.length} turn{stacks.length !== 1 ? 's' : ''}
          </span>
          {viewToggle}
        </div>
      </div>

      {view === 'chart' ? (
        <>
          <LatencyStatChips
            stats={stats}
            visible={visible}
            onToggle={toggle}
            format={format}
            disabled={sampleCount === 0}
            ariaLabel={`Toggle reference lines for ${seriesKey}`}
          />
          <StackedCallsBarChart
            stacks={stacks}
            formatValue={format}
            xAxisLabel="Turn"
            xLabels={turnLabels}
            referenceLines={referenceLines}
          />
        </>
      ) : (
        <TurnUsageTable rows={tableRows} columnHeader={tableColumnHeader} format={format} />
      )}
    </div>
  );
}
