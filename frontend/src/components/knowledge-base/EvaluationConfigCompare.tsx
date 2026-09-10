'use client';

import { useMemo, useState } from 'react';

import { CustomTable } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type {
  EvaluationConfig,
  EvaluationConfigResult,
  EvaluationConfigRunSummary,
} from '@/types/evaluationConfig';
import { formatMetricScore } from '@/utils/evalFormat';

import CompareColumnHeader from './CompareColumnHeader';
import { metricLabel } from './evalMetricsConstants';
import {
  bestInRow,
  buildCompareMatrix,
  configById,
  configNameById,
  type CompareMatrixRow,
} from './evalConfigHelpers';
import JudgePromptModal from './JudgePromptModal';

interface EvaluationConfigCompareProps {
  passes: EvaluationConfigRunSummary[]; // up to 3, already selected (col order)
  results: EvaluationConfigResult[];
  configs: EvaluationConfig[];
}

interface PromptView {
  name: string;
  prompt: string | null;
}

const OVERALL_ROW = '__overall__';

// Signed delta vs the baseline column, e.g. "+0.12" / "−0.08".
function formatDelta(value: number, baseline: number): string {
  const d = value - baseline;
  const sign = d >= 0 ? '+' : '−';
  return `${sign}${Math.abs(d).toFixed(2)}`;
}

// Aligned side-by-side comparison: metrics as rows, config passes as columns
// (only the judge changed across them). The best score per row is highlighted;
// non-baseline columns show a delta vs the left-most (baseline) pass.
export default function EvaluationConfigCompare({
  passes,
  results,
  configs,
}: EvaluationConfigCompareProps) {
  const [promptView, setPromptView] = useState<PromptView | null>(null);

  const baselineId = passes[0]?.config_run_id ?? null;

  const rows = useMemo<CompareMatrixRow[]>(() => {
    const overall: CompareMatrixRow = {
      metric: OVERALL_ROW,
      byPass: Object.fromEntries(passes.map((p) => [p.config_run_id, p.average_score])),
    };
    return [overall, ...buildCompareMatrix(passes, results)];
  }, [passes, results]);

  const columns = useMemo<CustomTableColumn<CompareMatrixRow>[]>(() => {
    const passColumns: CustomTableColumn<CompareMatrixRow>[] = passes.map((pass) => {
      const config = configById(configs, pass.evaluation_config_id);
      const name = configNameById(configs, pass.evaluation_config_id);
      const isBaseline = pass.config_run_id === baselineId;
      return {
        key: pass.config_run_id,
        align: 'center',
        title: (
          <CompareColumnHeader
            name={name}
            runNumber={pass.config_run_number}
            judgeModel={pass.judge_model}
            verdicts={pass.verdicts}
            isBaseline={isBaseline}
            humanAgreement={pass.human_agreement}
            labeledCount={pass.labeled_count}
            onViewPrompt={() => setPromptView({ name, prompt: config?.judge_prompt ?? null })}
          />
        ),
        render: (_v, r) => {
          const value = r.byPass[pass.config_run_id];
          if (typeof value !== 'number') return <span className="text-muted-foreground">—</span>;
          const best = bestInRow(r.byPass);
          const isWinner = best !== null && value >= best && passes.length > 1;
          const baseline = baselineId ? r.byPass[baselineId] : null;
          const showDelta = !isBaseline && typeof baseline === 'number';
          return (
            <div className="flex flex-col items-center">
              <span className={isWinner ? 'font-semibold text-primary' : 'text-foreground'}>
                {formatMetricScore(value)}
              </span>
              {showDelta && (
                <span className="text-xs text-muted-foreground">
                  {formatDelta(value, baseline as number)}
                </span>
              )}
            </div>
          );
        },
      };
    });

    return [
      {
        key: 'metric',
        title: 'Metric',
        render: (_v, r) =>
          r.metric === OVERALL_ROW ? (
            <span className="font-semibold text-foreground">Overall</span>
          ) : (
            <span className="text-foreground">{metricLabel(r.metric)}</span>
          ),
      },
      ...passColumns,
    ];
  }, [passes, configs, baselineId]);

  if (passes.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Select up to three config runs above to compare their scores.
      </div>
    );
  }

  return (
    <>
      <CustomTable columns={columns} dataSource={rows} rowKey="metric" pagination={false} />
      <JudgePromptModal
        open={promptView !== null}
        onClose={() => setPromptView(null)}
        configName={promptView?.name ?? ''}
        prompt={promptView?.prompt ?? null}
      />
    </>
  );
}
