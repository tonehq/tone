'use client';

import type { CallMetricsTurnMetric } from '@/types/callLog';
import { cn } from '@/utils/cn';
import type React from 'react';

import { turnHasAnyMeasurement } from './utils';

export interface PerTurnUsageRow<T> {
  /** Display label — raw pipecat turn number (matches TTFB charts). */
  turnLabel: string;
  /** Per-call entries inside this turn (filtered to value > 0). */
  calls: T[];
  /** Per-call values aligned 1:1 with `calls` — drives chart segments. */
  values: number[];
  /** Sum of `values` — drives the merged Total cell in the table. */
  total: number;
}

/**
 * Filter + reshape `turn_metrics` into one `PerTurnUsageRow<T>` per turn.
 *
 * Skips turn 0 (pipecat's internal pre/inter-turn bucket) and any turn with
 * no measurement, mirroring the filter used by `TurnLatencySection` so the
 * Usage and Latency cards line up on the same set of turns.
 *
 * `getCalls` and `getValue` are the only stage-specific bits — pass them in
 * to reuse this across LLM tokens, TTS characters, and STT audio.
 */
export function buildPerTurnUsageRows<T>(
  turns: CallMetricsTurnMetric[],
  getCalls: (t: CallMetricsTurnMetric) => T[] | null | undefined,
  getValue: (call: T) => number | null | undefined,
): { rows: PerTurnUsageRow<T>[]; hasAny: boolean } {
  const sorted = [...turns]
    .sort((a, b) => a.turn - b.turn)
    .filter((t) => t.turn >= 1 && turnHasAnyMeasurement(t));

  let hasAny = false;
  const rows = sorted.map((t) => {
    const raw = getCalls(t) ?? [];
    const pairs = raw
      .map((c) => ({ call: c, value: Number(getValue(c) ?? 0) }))
      .filter((p) => p.value > 0);
    const total = pairs.reduce((acc, p) => acc + p.value, 0);
    if (total > 0) hasAny = true;
    return {
      turnLabel: String(t.turn),
      calls: pairs.map((p) => p.call),
      values: pairs.map((p) => p.value),
      total,
    };
  });

  return { rows, hasAny };
}

interface TurnUsageTableProps<T> {
  rows: PerTurnUsageRow<T>[];
  /** Header for the per-call value column, e.g. `LLM Usage`. */
  columnHeader: string;
  /** Format the per-call and per-turn-total numeric values. */
  format: (value: number) => string;
  /**
   * Optional secondary line on each per-call row — e.g. processor / model.
   * Returning `undefined` renders just the value with no sub-line.
   */
  cellSubtext?: (call: T) => string | undefined;
  /**
   * Optional override for the trailing rowSpan column. Defaults to a `Total`
   * column that sums the row's per-call values. Provide `{ header, render }` to
   * replace both the header label and the cell contents — e.g. for the
   * end-to-end latency table where "Total" duplicates the single per-turn
   * value, this is used to swap in an executed tool-call count instead.
   */
  totalColumn?: {
    header: string;
    render: (row: PerTurnUsageRow<T>) => React.ReactNode;
  };
}

/**
 * Per-call rows grouped under each turn — Turn cell and Total cell merge
 * across the turn's calls via `rowSpan`. Single usage column (per design
 * spec), mirroring the rowSpan layout used by `PerTurnCallsSection`.
 *
 * Reused by every usage card (LLM / STT / TTS) so the only stage-specific
 * bits are the column header, the formatter, and the optional subtext.
 */
export function TurnUsageTable<T>({
  rows,
  columnHeader,
  format,
  cellSubtext,
  totalColumn,
}: TurnUsageTableProps<T>) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No data</p>;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full table-fixed text-sm">
        <colgroup>
          <col className="w-20" />
          <col className="w-auto" />
          <col className="w-32" />
        </colgroup>
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th
              scope="col"
              className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
            >
              Turn
            </th>
            <th
              scope="col"
              className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
            >
              {columnHeader}
            </th>
            <th
              scope="col"
              className="px-3 py-2 text-center text-xs font-medium uppercase tracking-wide text-muted-foreground"
            >
              {totalColumn?.header ?? 'Total'}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            // A turn with no calls still gets one placeholder row so the
            // chart's reserved slot for that turn has a matching table row.
            const callCount = Math.max(row.calls.length, 1);
            return Array.from({ length: callCount }, (_, i) => {
              const isFirst = i === 0;
              const isLast = i === callCount - 1;
              const call = row.calls[i];
              const value = row.values[i];
              const subtext = call != null && cellSubtext ? cellSubtext(call) : undefined;
              return (
                <tr
                  key={`${row.turnLabel}-${i}`}
                  className={cn('border-border', isLast && 'border-b last:border-0')}
                >
                  {isFirst && (
                    <td
                      rowSpan={callCount}
                      className="border-r border-border bg-muted/30 px-3 py-2 text-center align-middle text-base font-semibold tabular-nums text-foreground"
                    >
                      {row.turnLabel}
                    </td>
                  )}
                  <td className="px-3 py-2 text-center tabular-nums text-foreground">
                    {call == null ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <div className="flex flex-col">
                        <span>{format(value)}</span>
                        {subtext && (
                          <span className="text-xs text-muted-foreground">{subtext}</span>
                        )}
                      </div>
                    )}
                  </td>
                  {isFirst && (
                    <td
                      rowSpan={callCount}
                      className="border-l border-border bg-muted/30 px-3 py-2 text-center align-middle text-base font-semibold tabular-nums text-foreground"
                    >
                      {totalColumn ? (
                        totalColumn.render(row)
                      ) : row.total > 0 ? (
                        format(row.total)
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  )}
                </tr>
              );
            });
          })}
        </tbody>
      </table>
    </div>
  );
}
