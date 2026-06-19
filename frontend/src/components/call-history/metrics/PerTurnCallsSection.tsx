'use client';

import type { CallMetricsTurnMetric } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { BarChart3 } from 'lucide-react';

import { SectionHeader } from './SectionHeader';
import {
  StackedTurnLatencyChart,
  type StackedSeriesDatum,
  type StackedSeriesMeta,
} from './StackedTurnLatencyChart';
import { useChartTableView } from './useChartTableView';
import { formatMs } from './utils';

interface PerTurnCallsSectionProps {
  turns: CallMetricsTurnMetric[];
}

interface PerCallRow {
  /** Display label for the merged Turn cell. */
  turnLabel: string;
  /** Set only on the first row of a turn group — drives `<td rowSpan>`. */
  rowSpan?: number;
  /** Set only on the first row of a turn group — drives the merged Total cell. */
  totalLatency?: number;
  /** True on the final row of a turn group (drives the divider). */
  lastInTurn: boolean;
  llm: number | null;
  stt: number | null;
  tts: number | null;
}

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

const SERVICE_COLUMNS: { key: 'llm' | 'stt' | 'tts'; header: string }[] = [
  { key: 'llm', header: 'LLM Latency' },
  { key: 'stt', header: 'STT Latency' },
  { key: 'tts', header: 'TTS Latency' },
];

/** Drop placeholder zeros and nulls from a per-call array. */
const clean = (raw: readonly (number | null)[] | null | undefined): number[] =>
  (raw ?? []).filter((v): v is number => v != null && v > 0);

/**
 * Flatten `turn_metrics` into one row per individual service call. Each turn
 * contributes `max(n_llm, n_stt, n_tts)` rows; the Turn and Total Latency
 * cells carry `rowSpan` on the first row so they merge across the turn.
 */
function buildRows(turns: CallMetricsTurnMetric[]): PerCallRow[] {
  const out: PerCallRow[] = [];
  let displayIndex = 0;
  for (const t of turns) {
    const llm = clean(t.llm_ttfb_all);
    const stt = clean(t.stt_ttfb_all);
    const tts = clean(t.tts_ttfb_all);
    const rowCount = Math.max(llm.length, stt.length, tts.length);
    if (rowCount === 0) continue;
    displayIndex += 1;
    const turnLabel = String(displayIndex);
    const totalLatency =
      llm.reduce((s, v) => s + v, 0) +
      stt.reduce((s, v) => s + v, 0) +
      tts.reduce((s, v) => s + v, 0);
    for (let i = 0; i < rowCount; i++) {
      out.push({
        turnLabel,
        rowSpan: i === 0 ? rowCount : undefined,
        totalLatency: i === 0 ? totalLatency : undefined,
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
  const sanitize = (v: number | null): number | null => (v == null || v <= 0 ? null : v);
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
 * - **Chart view**: one stacked bar per turn (LLM emerald, STT sky, TTS
 *   amber). Bar height = sum of the first TTFB for each service.
 * - **Table view**: per-call rows grouped under a merged Turn cell. Each
 *   service column shows the individual call's TTFB; the Total Latency cell
 *   merges across the turn and sums every per-call TTFB for that turn —
 *   matching the height of the corresponding stacked bar.
 */
export function PerTurnCallsSection({ turns }: PerTurnCallsSectionProps) {
  const { view, toggle } = useChartTableView('chart', 'Service latency view');

  if (turns.length === 0) return null;

  // Same filter as TurnLatencySection's cards above — only real user→bot
  // exchanges. Drops the auto-greeting, pre/inter-turn bucket, and abandoned
  // turns so every Latency view on the page shows the same turn set.
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
          : 'Per-call rows grouped under each turn. Service columns show the individual call’s TTFB; Total Latency sums all per-call TTFBs for that turn.'}
      </p>

      {view === 'chart' ? (
        <div className="rounded-lg border border-border p-3">
          <StackedTurnLatencyChart data={chartData} series={SERIES} formatValue={formatMs} />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full table-fixed text-sm">
            <colgroup>
              <col className="w-20" />
              <col className="w-1/4" />
              <col className="w-1/4" />
              <col className="w-1/4" />
              <col className="w-1/4" />
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
                <th
                  scope="col"
                  className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
                >
                  Total Latency
                </th>
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
                  {row.rowSpan != null && row.totalLatency != null && (
                    <td
                      rowSpan={row.rowSpan}
                      className="border-l border-border bg-muted/30 px-3 py-2 text-center align-middle text-base font-semibold tabular-nums text-foreground"
                    >
                      {formatMs(row.totalLatency)}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
