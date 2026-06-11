'use client';

import type { CallMetricsLLMUsage } from '@/types/callLog';
import { BrainCircuit } from 'lucide-react';

import { BarChart } from './BarChart';
import { MetricsDataTable, type MetricsTableColumn } from './MetricsDataTable';
import { SectionHeader } from './SectionHeader';
import { useChartTableView } from './useChartTableView';
import { BAR_CHART_MAX_HEIGHT } from './utils';

interface LLMUsageSectionProps {
  llmUsage: CallMetricsLLMUsage[];
  totalTokens: number;
}

const LLM_TABLE_COLUMNS: MetricsTableColumn<CallMetricsLLMUsage>[] = [
  { key: 'idx', header: '#', align: 'left', width: 'w-12', cell: (_row, i) => i + 1 },
  { key: 'model', header: 'Model', align: 'left', cell: (row) => row.model },
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

/** File-local chart of per-call total tokens. Extracted so the values array
 *  is computed once instead of remapping inline for both `values` and `maxValue`. */
function LLMTokensPerCallChart({ llmUsage }: { llmUsage: CallMetricsLLMUsage[] }) {
  const tokenCounts = llmUsage.map((u) => u.total_tokens);
  return (
    <>
      <p className="mb-2 text-xs text-muted-foreground">Tokens per call</p>
      <BarChart
        values={tokenCounts}
        maxValue={Math.max(...tokenCounts)}
        maxHeight={BAR_CHART_MAX_HEIGHT}
        color="bg-emerald-500/60 hover:bg-emerald-500"
        getTooltip={(v, i) => `Call ${i + 1}: ${v.toLocaleString()} tokens`}
      />
    </>
  );
}

export function LLMUsageSection({ llmUsage, totalTokens }: LLMUsageSectionProps) {
  const totalPrompt = llmUsage.reduce((s, u) => s + u.prompt_tokens, 0);
  const totalCompletion = llmUsage.reduce((s, u) => s + u.completion_tokens, 0);
  const model = [...new Set(llmUsage.map((u) => u.model))].join(', ');
  const hasMultiple = llmUsage.length > 1;
  const { view, toggle } = useChartTableView('chart', 'LLM usage view');

  return (
    <div className="space-y-3">
      <SectionHeader icon={BrainCircuit} title="LLM Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-foreground">{model}</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              {llmUsage.length} call{llmUsage.length !== 1 ? 's' : ''}
            </span>
            {hasMultiple && toggle}
          </div>
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
        {hasMultiple && (
          <div className="mt-3 border-t border-border pt-3">
            {view === 'chart' ? (
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
