'use client';

import { useMemo } from 'react';

import TruncatedCell from '@/components/knowledge-base/TruncatedCell';
import VerdictChip from '@/components/knowledge-base/VerdictChip';
import { CustomTable } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type { EvalVerdict, HumanVerdict } from '@/types/eval';
import type {
  EvaluationConfig,
  EvaluationConfigResultRow,
  EvaluationConfigRunSummary,
} from '@/types/evaluationConfig';
import { formatMetricScore } from '@/utils/evalFormat';

import {
  buildQuestionMatrix,
  configNameById,
  meanRowScore,
  type QuestionMatrixRow,
} from './evalConfigHelpers';
import { HUMAN_VERDICT_COLOR, HUMAN_VERDICT_LABEL } from './verdictColors';

interface EvaluationConfigScoresTableProps {
  passes: EvaluationConfigRunSummary[]; // selected passes (columns)
  results: EvaluationConfigResultRow[];
  configs: EvaluationConfig[];
}

const KNOWN_VERDICTS = new Set(['PASS', 'PARTIAL', 'FAIL']);

// Per-question score matrix: one row per question, one column per selected
// config pass, each cell showing that pass's verdict + mean score for the
// question. Reuses the eval-results VerdictChip / TruncatedCell.
export default function EvaluationConfigScoresTable({
  passes,
  results,
  configs,
}: EvaluationConfigScoresTableProps) {
  const rows = useMemo(() => buildQuestionMatrix(results), [results]);

  // Human mark is config-independent (lives on the source answer), so it's the
  // same across every pass for a given question — take it from any row.
  const humanByEval = useMemo(() => {
    const map = new Map<string, HumanVerdict | null>();
    for (const r of results) map.set(r.eval_id, r.human_verdict);
    return map;
  }, [results]);

  const columns = useMemo<CustomTableColumn<QuestionMatrixRow>[]>(() => {
    const passColumns: CustomTableColumn<QuestionMatrixRow>[] = passes.map((pass) => ({
      key: `pass:${pass.config_run_id}`,
      title: `${configNameById(configs, pass.evaluation_config_id)} #${pass.config_run_number}`,
      align: 'center',
      render: (_v, r) => {
        const cell = r.byPass[pass.config_run_id];
        if (!cell) return <span className="text-muted-foreground">—</span>;
        const verdict = (cell.verdict ?? '').toUpperCase();
        const score = meanRowScore(cell);
        return (
          <div className="flex flex-col items-center gap-0.5">
            {KNOWN_VERDICTS.has(verdict) && <VerdictChip verdict={verdict as EvalVerdict} />}
            <span className="text-xs text-muted-foreground">{formatMetricScore(score)}</span>
          </div>
        );
      },
    }));

    return [
      {
        key: 'question',
        title: 'Question',
        render: (_v, r) => <TruncatedCell text={r.question} maxWidthClassName="max-w-[320px]" />,
      },
      {
        key: 'human_verdict',
        title: 'Your call',
        align: 'center',
        render: (_v, r) => {
          const human = humanByEval.get(r.evalId) ?? null;
          if (!human) return <span className="text-muted-foreground">—</span>;
          return (
            <span
              className={`rounded px-2 py-0.5 text-xs font-medium ${HUMAN_VERDICT_COLOR[human]}`}
            >
              {HUMAN_VERDICT_LABEL[human]}
            </span>
          );
        },
      },
      ...passColumns,
    ];
  }, [passes, configs, humanByEval]);

  if (passes.length === 0) return null;

  return (
    <CustomTable
      columns={columns}
      dataSource={rows}
      rowKey="evalId"
      pagination={false}
      emptyState="No per-question scores for the selected runs."
    />
  );
}
