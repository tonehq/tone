'use client';

import type { CallMetricsLLMUsage, CallMetricsTurnMetric } from '@/types/callLog';
import { BrainCircuit } from 'lucide-react';
import { useMemo } from 'react';

import { AxisBarChart } from './AxisBarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { StackedCallsBarChart } from './StackedCallsBarChart';
import { buildPerTurnUsageRows, TurnUsageTable } from './TurnUsageCard';
import { useChartTableView } from './useChartTableView';
import { extractProcessorName } from './utils';

interface LLMUsageSectionProps {
  llmUsage: CallMetricsLLMUsage[];
  totalTokens: number;
  turns: CallMetricsTurnMetric[];
}

const LLM_TABLE_COLUMNS: MetricsTableColumn<CallMetricsLLMUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  {
    key: 'prompt',
    header: 'Prompt',
    align: 'right',
    cell: (row) => row.prompt_tokens.toLocaleString(),
  },
  {
    key: 'completion',
    header: 'Completion',
    align: 'right',
    cell: (row) => row.completion_tokens.toLocaleString(),
  },
  {
    key: 'total',
    header: 'Total',
    align: 'right',
    cell: (row) => row.total_tokens.toLocaleString(),
  },
];

const formatTokens = (v: number) => `${Math.round(v).toLocaleString()} tokens`;

/** Compose a short label like `OpenAILLMService · 800 prompt · 400 completion`
 *  for the cell sub-line. Always returns a non-empty string for valid input. */
function llmCellSubtext(call: CallMetricsLLMUsage): string {
  const proc = call.processor ? extractProcessorName(call.processor) : undefined;
  const breakdown = `${call.prompt_tokens.toLocaleString()} prompt · ${call.completion_tokens.toLocaleString()} completion`;
  return proc ? `${proc} · ${breakdown}` : breakdown;
}

/** Legacy file-local chart of per-call total tokens — rendered for calls
 *  recorded before per-call usage was being persisted into `turn_metrics`. */
function LLMTokensPerCallChart({ llmUsage }: { llmUsage: CallMetricsLLMUsage[] }) {
  const tokenCounts = llmUsage.map((u) => u.total_tokens);
  return (
    <>
      <p className="mb-2 text-xs text-muted-foreground">Tokens per call</p>
      <AxisBarChart
        values={tokenCounts}
        formatValue={(v) => v.toLocaleString()}
        xAxisLabel="Call"
      />
    </>
  );
}

export function LLMUsageSection({ llmUsage, totalTokens, turns }: LLMUsageSectionProps) {
  const totalPrompt = llmUsage.reduce((s, u) => s + u.prompt_tokens, 0);
  const totalCompletion = llmUsage.reduce((s, u) => s + u.completion_tokens, 0);
  const hasMultiple = llmUsage.length > 1;
  const { view, toggle } = useChartTableView('chart', 'LLM usage view');

  // Per-turn rows from `turn_metrics.llm_usage_all`. When present, the
  // chart and table switch to a turn-aligned, stacked-by-call view (one
  // colored segment per LLM call inside the turn, matching the TTFB chart
  // style). When absent (legacy rows), fall back to the flat per-call chart.
  const perTurn = useMemo(() => {
    const { rows, hasAny } = buildPerTurnUsageRows<CallMetricsLLMUsage>(
      turns,
      (t) => t.llm_usage_all,
      (c) => c.total_tokens,
    );
    return {
      rows,
      hasAny,
      // Turns with at least one LLM call vs. total turns rendered — keeps
      // the header label aligned with the `X of Y turns` shown by the
      // Latency cards.
      sampleCount: rows.filter((r) => r.total > 0).length,
      stacks: rows.map((r) => r.values),
      turnLabels: rows.map((r) => r.turnLabel),
    };
  }, [turns]);
  const { rows: perTurnRows, hasAny: hasPerTurnUsage } = perTurn;

  return (
    <div className="space-y-3">
      <SectionHeader icon={BrainCircuit} title="LLM Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-end gap-2">
          <span className="text-xs text-muted-foreground">
            {hasPerTurnUsage
              ? `${perTurn.sampleCount} of ${perTurnRows.length} turn${perTurnRows.length !== 1 ? 's' : ''}`
              : `${llmUsage.length} call${llmUsage.length !== 1 ? 's' : ''}`}
          </span>
          {(hasPerTurnUsage || hasMultiple) && toggle}
        </div>
        <div className="flex gap-4">
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">Prompt</p>
            <p className="text-sm font-semibold text-foreground">{totalPrompt.toLocaleString()}</p>
          </div>
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">Completion</p>
            <p className="text-sm font-semibold text-foreground">
              {totalCompletion.toLocaleString()}
            </p>
          </div>
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-sm font-semibold text-foreground">{totalTokens.toLocaleString()}</p>
          </div>
        </div>
        <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="bg-blue-500 transition-all"
            style={{ width: `${(totalPrompt / totalTokens) * 100}%` }}
          />
          <div
            className="bg-emerald-500 transition-all"
            style={{ width: `${(totalCompletion / totalTokens) * 100}%` }}
          />
        </div>
        <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block size-1.5 rounded-full bg-blue-500" />
            Prompt
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block size-1.5 rounded-full bg-emerald-500" />
            Completion
          </span>
        </div>
        {(hasPerTurnUsage || hasMultiple) && (
          <div className="mt-3 border-t border-border pt-3">
            {hasPerTurnUsage ? (
              view === 'chart' ? (
                <StackedCallsBarChart
                  stacks={perTurn.stacks}
                  formatValue={formatTokens}
                  xAxisLabel="Turn"
                  xLabels={perTurn.turnLabels}
                />
              ) : (
                <TurnUsageTable
                  rows={perTurnRows}
                  columnHeader="LLM Usage"
                  format={formatTokens}
                  cellSubtext={llmCellSubtext}
                />
              )
            ) : view === 'chart' ? (
              <LLMTokensPerCallChart llmUsage={llmUsage} />
            ) : (
              <MetricsDataTable columns={LLM_TABLE_COLUMNS} rows={llmUsage} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
