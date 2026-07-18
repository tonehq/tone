'use client';

import type { CallMetricsTurnMetric, ToolExecution } from '@/types/callLog';
import { LineChart } from 'lucide-react';
import { type ReactNode, useMemo, useState } from 'react';

import { CollapsibleCard } from './CollapsibleCard';
import { LatencyStatChips, useLatencyStats } from './LatencyStatChips';
import { SectionHeader } from './SectionHeader';
import { SortToggle, type SortDirection } from './SortToggle';
import { StackedCallsBarChart } from './StackedCallsBarChart';
import { type PerTurnUsageRow, TurnUsageTable } from './TurnUsageCard';
import { useChartTableView } from './useChartTableView';
import { formatMs, turnHasAnyMeasurement } from './utils';

interface TurnLatencySectionProps {
  turns: CallMetricsTurnMetric[];
  /** Full tool_executions list for this call. Used only by the end-to-end card
   *  to render an "Executed Tool Calls" column per turn. */
  toolExecutions?: ToolExecution[];
}

/**
 * Count executed tool calls per turn — "executed" = the pipeline actually
 * dispatched and ran the handler, i.e. status ∈ {`success`, `error`}. Excludes
 * `proposed` (LLM emitted but never dispatched) and `cancelled` (killed
 * mid-execution, neither pass nor fail).
 */
function buildExecutedToolCallsByTurn(
  toolExecutions: ToolExecution[] | undefined,
): Map<number, number> {
  const byTurn = new Map<number, number>();
  for (const tc of toolExecutions ?? []) {
    if (tc.turn_number == null) continue;
    if (tc.status !== 'success' && tc.status !== 'error') continue;
    byTurn.set(tc.turn_number, (byTurn.get(tc.turn_number) ?? 0) + 1);
  }
  return byTurn;
}

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
export function TurnLatencySection({ turns, toolExecutions }: TurnLatencySectionProps) {
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
      format: formatMs,
      stacks: sorted.map((t) => cleanSamples([t.end_to_end])),
    },
  ];

  // Precompute per-turn executed tool-call counts once — only the end-to-end
  // card uses them (its "Total" column duplicates the latency value, so we
  // repurpose it to surface tool activity per turn).
  const executedByTurn = buildExecutedToolCallsByTurn(toolExecutions);
  const executedForTurnLabel = (label: string): number => {
    const turnNum = Number(label);
    if (!Number.isFinite(turnNum)) return 0;
    return executedByTurn.get(turnNum) ?? 0;
  };

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
            totalColumnOverride={
              s.key === 'end_to_end'
                ? {
                    header: 'Tool Calls',
                    render: (row) => {
                      const count = executedForTurnLabel(row.turnLabel);
                      return count > 0 ? count : <span className="text-muted-foreground">0</span>;
                    },
                  }
                : undefined
            }
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
  /** Optional trailing-column override for this card's table view. When
   *  omitted the shared `Total` column is rendered. */
  totalColumnOverride?: {
    header: string;
    render: (row: PerTurnUsageRow<number>) => ReactNode;
  };
}

/** Single per-metric card: chart/table toggle + stat reference lines + sort. */
function TurnMetricCard({
  seriesKey,
  title,
  subtitle,
  format,
  stacks,
  turnLabels,
  totalColumnOverride,
}: TurnMetricCardProps) {
  const { view, toggle: viewToggle } = useChartTableView('chart', `${title} view`);
  const [sort, setSort] = useState<SortDirection>('natural');

  // Reorder stacks / labels together by per-turn total. Natural order is the
  // upstream-sorted (turn-number) sequence — no work needed.
  const { stacks: displayStacks, turnLabels: displayLabels } = useMemo(() => {
    if (sort === 'natural') return { stacks, turnLabels };
    const totals = stacks.map((s) => s.reduce((acc, v) => acc + v, 0));
    const order = totals
      .map((total, i) => ({ total, i }))
      .sort((a, b) => (sort === 'asc' ? a.total - b.total : b.total - a.total));
    return {
      stacks: order.map((o) => stacks[o.i]),
      turnLabels: order.map((o) => turnLabels[o.i]),
    };
  }, [stacks, turnLabels, sort]);

  // Stats reflect what the bar visually represents: the per-turn TOTAL
  // (sum of all per-call values inside the turn). Turns with no measurement
  // are excluded so a placeholder zero doesn't drag the avg / min down.
  const turnTotals = displayStacks
    .map((s) => s.reduce((acc, v) => acc + v, 0))
    .filter((v) => v > 0);
  const { stats, sampleCount, visible, toggle, buildReferenceLines } = useLatencyStats(turnTotals);

  const referenceLines = buildReferenceLines(format);

  // Reshape into the same per-turn / per-call grouped table the Usage cards
  // use — Turn (rowSpan) | <metric> | Total (rowSpan), with one row per
  // call inside the turn. `calls` and `values` both carry the raw number;
  // there's no per-call metadata for TTFB so no cell subtext.
  const tableRows: PerTurnUsageRow<number>[] = displayStacks.map((segments, i) => ({
    turnLabel: displayLabels[i],
    calls: segments,
    values: segments,
    total: segments.reduce((acc, v) => acc + v, 0),
  }));
  const tableColumnHeader = title.replace(' per Turn', '');

  return (
    <CollapsibleCard
      title={title}
      subtitle={subtitle}
      actions={
        <>
          <span className="text-xs text-muted-foreground">
            {sampleCount} of {stacks.length} turn{stacks.length !== 1 ? 's' : ''}
          </span>
          <SortToggle
            value={sort}
            onChange={setSort}
            label={`Sort order for ${tableColumnHeader}`}
          />
          {viewToggle}
        </>
      }
    >
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
            stacks={displayStacks}
            formatValue={format}
            xAxisLabel="Turn"
            xLabels={displayLabels}
            referenceLines={referenceLines}
          />
        </>
      ) : (
        <TurnUsageTable
          rows={tableRows}
          columnHeader={tableColumnHeader}
          format={format}
          totalColumn={totalColumnOverride}
        />
      )}
    </CollapsibleCard>
  );
}
