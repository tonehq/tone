'use client';

import type { CallMetricsTurnMetric } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { BarChart3 } from 'lucide-react';

import {
  StackedTurnLatencyChart,
  type StackedSeriesDatum,
  type StackedSeriesMeta,
} from './StackedTurnLatencyChart';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { formatMs } from './utils';

interface PerTurnCallsSectionProps {
  turns: CallMetricsTurnMetric[];
}

interface PerCallRow {
  /** Display label for the merged Turn cell (raw pipecat turn number). */
  turnLabel: string;
  /** Set only on the first row of a turn group — drives `<td rowSpan>`. */
  rowSpan?: number;
  /** True on the final row of a turn group (drives the divider). */
  lastInTurn: boolean;
  llm: number | null;
  stt: number | null;
  tts: number | null;
}

const SERVICE_COLUMNS: { key: 'llm' | 'stt' | 'tts'; header: string }[] = [
  { key: 'llm', header: 'LLM' },
  { key: 'stt', header: 'STT' },
  { key: 'tts', header: 'TTS' },
];

const SERIES: StackedSeriesMeta[] = [
  {
    key: 'llm',
    label: 'LLM',
    barClass: 'bg-emerald-500/70 hover:bg-emerald-500',
    dotClass: 'bg-emerald-500',
  },
  {
    key: 'stt',
    label: 'STT',
    barClass: 'bg-sky-500/70 hover:bg-sky-500',
    dotClass: 'bg-sky-500',
  },
  {
    key: 'tts',
    label: 'TTS',
    barClass: 'bg-amber-500/70 hover:bg-amber-500',
    dotClass: 'bg-amber-500',
  },
];

/**
 * Treat 0.0 as "no measurement" — same convention as TurnLatencySection.
 * Pipecat emits 0.0 only for placeholder cases (e.g. the auto-greeting turn
 * where TTFB wasn't actually measured); a real measurement is always > 0.
 */
const sanitize = (v: number | null): number | null => (v == null || v <= 0 ? null : v);

/**
 * Flatten `turn_metrics` into one table row per individual service call.
 *
 * Each turn contributes `max(n_llm, n_stt, n_tts)` rows; gaps are nulled so
 * the columns stay aligned by call index. The first row of every turn carries
 * `rowSpan` so the Turn cell merges vertically (the Excel-style layout).
 */
function buildRows(turns: CallMetricsTurnMetric[]): PerCallRow[] {
  const out: PerCallRow[] = [];
  // Display index re-numbers turns 1..N so the table's labels align with
  // the chart view and the per-metric cards above (which also re-number).
  let displayIndex = 0;
  for (const t of turns) {
    const llm = t.llm_ttfb_all ?? [];
    const stt = t.stt_ttfb_all ?? [];
    const tts = t.tts_ttfb_all ?? [];
    const rowCount = Math.max(llm.length, stt.length, tts.length);
    if (rowCount === 0) continue;
    displayIndex += 1;
    const turnLabel = String(displayIndex);
    for (let i = 0; i < rowCount; i++) {
      out.push({
        turnLabel,
        rowSpan: i === 0 ? rowCount : undefined,
        lastInTurn: i === rowCount - 1,
        llm: i < llm.length ? llm[i] : null,
        stt: i < stt.length ? stt[i] : null,
        tts: i < tts.length ? tts[i] : null,
      });
    }
  }
  return out;
}

/** Per-turn first-TTFB series for the stacked bar chart. */
function buildChartData(turns: CallMetricsTurnMetric[]): StackedSeriesDatum[] {
  return turns.map((t, i) => ({
    label: String(i + 1),
    values: [sanitize(t.llm_ttfb), sanitize(t.stt_ttfb), sanitize(t.tts_ttfb)],
  }));
}

const formatCell = (v: number | null) =>
  v == null ? <span className="text-muted-foreground">—</span> : formatMs(v);

/**
 * Per-turn LLM / STT / TTS latency with a chart ↔ table toggle.
 *
 * - **Chart view**: grouped bar chart, 3 colored bars per turn (first TTFB
 *   per service). Quick side-by-side comparison.
 * - **Table view**: merged-cell layout — one row per individual service call,
 *   grouped under a vertically-merged Turn cell. Keeps per-call granularity.
 */
export function PerTurnCallsSection({ turns }: PerTurnCallsSectionProps) {
  const { view, toggle } = useChartTableView('chart', 'Service latency view');

  if (turns.length === 0) return null;

  // Same filter as TurnLatencySection's cards above — only real user→bot
  // exchanges. Drops the auto-greeting (no preceding user speech), the pre/
  // inter-turn bucket, and abandoned turns, so every Latency view on the
  // page shows the exact same turn set.
  const sorted = [...turns].sort((a, b) => a.turn - b.turn).filter((t) => t.end_to_end != null);
  const rows = buildRows(sorted);
  const chartData = buildChartData(sorted);
  if (rows.length === 0 && chartData.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <SectionHeader icon={BarChart3} title="LLM / STT / TTS per Turn" />
        {toggle}
      </div>
      <p className="text-xs text-muted-foreground">
        {view === 'chart'
          ? 'One bar per turn. Each bar stacks the first TTFB for LLM, STT, and TTS — the colored segments show each service’s share of the bar.'
          : 'Every individual service call grouped under its turn. Rows = calls, columns = services.'}
      </p>

      {view === 'chart' ? (
        <div className="rounded-lg border border-border p-3">
          <StackedTurnLatencyChart data={chartData} series={SERIES} formatValue={formatMs} />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full table-fixed text-sm">
            <colgroup>
              <col className="w-24" />
              <col className="w-1/3" />
              <col className="w-1/3" />
              <col className="w-1/3" />
            </colgroup>
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th
                  scope="col"
                  className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
                >
                  Turn
                </th>
                {SERVICE_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    scope="col"
                    className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  className={cn('border-border', row.lastInTurn && 'border-b last:border-0')}
                >
                  {row.rowSpan != null && (
                    <td
                      rowSpan={row.rowSpan}
                      className="border-r border-border bg-muted/30 px-3 py-2 text-center align-middle text-base font-semibold tabular-nums text-foreground"
                    >
                      {row.turnLabel}
                    </td>
                  )}
                  {SERVICE_COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className="px-3 py-2 text-center tabular-nums text-foreground"
                    >
                      {formatCell(row[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
