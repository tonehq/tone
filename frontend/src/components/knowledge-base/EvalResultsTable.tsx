'use client';

import { useMemo } from 'react';

import MetricScoreCell from '@/components/knowledge-base/MetricScoreCell';
import TruncatedCell from '@/components/knowledge-base/TruncatedCell';
import VerdictChip from '@/components/knowledge-base/VerdictChip';
import { metricLabel, orderMetricNames } from '@/components/knowledge-base/evalMetricsConstants';
import { CustomTable } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type { EvalScoredQuestion } from '@/types/eval';

// One row per scored question. Metric columns are derived dynamically from the
// `metric_scores` keys present across the batch, so the table always matches
// exactly which DeepEval metrics were run.
export default function EvalResultsTable({ questions }: { questions: EvalScoredQuestion[] }) {
  const metricNames = useMemo(() => {
    const names = new Set<string>();
    for (const q of questions) {
      for (const name of Object.keys(q.judge.metric_scores ?? {})) names.add(name);
    }
    return orderMetricNames([...names]);
  }, [questions]);

  const columns = useMemo<CustomTableColumn<EvalScoredQuestion>[]>(() => {
    const metricColumns: CustomTableColumn<EvalScoredQuestion>[] = metricNames.map((name) => ({
      key: `metric:${name}`,
      title: metricLabel(name),
      align: 'center',
      width: 'w-[110px]',
      render: (_v, r) => <MetricScoreCell metric={r.judge.metric_scores?.[name]} />,
    }));

    return [
      {
        key: 'verdict',
        title: 'Verdict',
        align: 'center',
        width: 'w-[110px]',
        render: (_v, r) => <VerdictChip verdict={r.judge.verdict} />,
      },
      {
        key: 'question',
        title: 'Question',
        width: 'w-[260px]',
        render: (_v, r) => <TruncatedCell text={r.question} maxWidthClassName="max-w-[250px]" />,
      },
      {
        key: 'expected_answer',
        title: 'Expected answer',
        width: 'w-[260px]',
        render: (_v, r) => (
          <TruncatedCell text={r.expected_answer} maxWidthClassName="max-w-[250px]" />
        ),
      },
      {
        key: 'actual_answer',
        title: 'Actual answer',
        width: 'w-[260px]',
        render: (_v, r) => (
          <TruncatedCell text={r.actual_answer} maxWidthClassName="max-w-[250px]" />
        ),
      },
      ...metricColumns,
      {
        key: 'latency_ms',
        title: 'Latency',
        align: 'right',
        width: 'w-[90px]',
        render: (_v, r) => (
          <span className="text-sm tabular-nums text-muted-foreground">
            {r.latency_ms != null ? `${r.latency_ms}ms` : '—'}
          </span>
        ),
      },
    ];
  }, [metricNames]);

  return (
    <CustomTable
      columns={columns}
      dataSource={questions}
      rowKey="eval_id"
      pagination={false}
      emptyState={
        <div className="py-10 text-center text-sm text-muted-foreground">
          No scored questions in this batch.
        </div>
      }
    />
  );
}
