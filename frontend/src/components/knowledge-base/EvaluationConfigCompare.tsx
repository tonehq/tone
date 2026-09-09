'use client';

import { useMemo, useState } from 'react';

import { CustomButton } from '@/components/shared';
import type {
  EvaluationConfig,
  EvaluationConfigResult,
  EvaluationConfigRunSummary,
} from '@/types/evaluationConfig';

import {
  averageMetricScores,
  configById,
  configNameById,
  verdictSummary,
} from './evalConfigHelpers';
import JudgePromptModal from './JudgePromptModal';

interface EvaluationConfigCompareProps {
  passes: EvaluationConfigRunSummary[]; // up to 3, already selected
  results: EvaluationConfigResult[];
  configs: EvaluationConfig[];
}

interface PromptView {
  name: string;
  prompt: string | null;
}

// Side-by-side columns (up to 3) — only the judge changed across them, so
// scores are directly comparable. The prompt is hidden behind a modal.
export default function EvaluationConfigCompare({
  passes,
  results,
  configs,
}: EvaluationConfigCompareProps) {
  const [promptView, setPromptView] = useState<PromptView | null>(null);

  const resultsByPass = useMemo(() => {
    const map = new Map<string, EvaluationConfigResult[]>();
    for (const row of results) {
      const list = map.get(row.config_run_id) ?? [];
      list.push(row);
      map.set(row.config_run_id, list);
    }
    return map;
  }, [results]);

  if (passes.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Select up to three config runs above to compare their scores.
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {passes.map((pass) => {
          const config = configById(configs, pass.evaluation_config_id);
          const name = configNameById(configs, pass.evaluation_config_id);
          const rows = resultsByPass.get(pass.config_run_id) ?? [];
          const averages = averageMetricScores(rows);
          return (
            <div
              key={pass.config_run_id}
              className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
            >
              <div>
                <div className="text-sm font-semibold text-foreground">{name}</div>
                <div className="text-xs text-muted-foreground">
                  Run #{pass.config_run_number} · {config?.judge_model ?? '—'}
                </div>
              </div>
              <div className="text-xs text-muted-foreground">{verdictSummary(pass.verdicts)}</div>
              <div className="flex flex-col gap-1">
                {averages.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No metric scores.</div>
                ) : (
                  averages.map((m) => (
                    <div
                      key={m.metric}
                      className="flex items-center justify-between text-xs text-foreground"
                    >
                      <span className="text-muted-foreground">{m.metric}</span>
                      <span className="font-medium">{m.average.toFixed(2)}</span>
                    </div>
                  ))
                )}
              </div>
              <CustomButton
                type="default"
                size="sm"
                onClick={() => setPromptView({ name, prompt: config?.judge_prompt ?? null })}
              >
                View prompt
              </CustomButton>
            </div>
          );
        })}
      </div>

      <JudgePromptModal
        open={promptView !== null}
        onClose={() => setPromptView(null)}
        configName={promptView?.name ?? ''}
        prompt={promptView?.prompt ?? null}
      />
    </>
  );
}
