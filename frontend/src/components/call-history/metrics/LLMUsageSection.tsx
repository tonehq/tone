import type { CallMetricsLLMUsage } from '@/types/callLog';
import { BrainCircuit } from 'lucide-react';

import { BarChart } from './BarChart';
import { SectionHeader } from './SectionHeader';
import { BAR_CHART_MAX_HEIGHT } from './utils';

interface LLMUsageSectionProps {
  llmUsage: CallMetricsLLMUsage[];
  totalTokens: number;
}

export function LLMUsageSection({ llmUsage, totalTokens }: LLMUsageSectionProps) {
  const totalPrompt = llmUsage.reduce((s, u) => s + u.prompt_tokens, 0);
  const totalCompletion = llmUsage.reduce((s, u) => s + u.completion_tokens, 0);
  const model = [...new Set(llmUsage.map((u) => u.model))].join(', ');

  return (
    <div className="space-y-3">
      <SectionHeader icon={BrainCircuit} title="LLM Usage" />
      <div className="rounded-lg border border-border p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-foreground">{model}</span>
          <span className="text-xs text-muted-foreground">
            {llmUsage.length} call{llmUsage.length !== 1 ? 's' : ''}
          </span>
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
        {llmUsage.length > 1 && (
          <div className="mt-3 border-t border-border pt-3">
            <p className="mb-2 text-xs text-muted-foreground">Tokens per call</p>
            <BarChart
              values={llmUsage.map((u) => u.total_tokens)}
              maxValue={Math.max(...llmUsage.map((u) => u.total_tokens))}
              maxHeight={BAR_CHART_MAX_HEIGHT}
              color="bg-emerald-500/60 hover:bg-emerald-500"
              getTooltip={(v, i) => `Call ${i + 1}: ${v.toLocaleString()} tokens`}
            />
          </div>
        )}
      </div>
    </div>
  );
}
