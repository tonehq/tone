'use client';

import { useEffect, useMemo, useState } from 'react';

import HumanVerdictControl from '@/components/knowledge-base/HumanVerdictControl';
import MetricScoreCell from '@/components/knowledge-base/MetricScoreCell';
import TruncatedCell from '@/components/knowledge-base/TruncatedCell';
import VerdictChip from '@/components/knowledge-base/VerdictChip';
import { metricLabel, orderMetricNames } from '@/components/knowledge-base/evalMetricsConstants';
import { CustomTable } from '@/components/shared';
import { useSetHumanVerdict } from '@/lib/api/evals';
import type { CustomTableColumn } from '@/types/components';
import type { EvalScoredQuestion, HumanVerdict } from '@/types/eval';
import { handleApiError } from '@/utils/helpers';

const PAGE_SIZE_OPTIONS = [10, 20, 50];

interface EvalResultsTableProps {
  uploadId: string;
  runId: string;
  questions: EvalScoredQuestion[];
}

// One row per scored question. Metric columns are derived dynamically from the
// `metric_scores` keys present across the batch, so the table always matches
// exactly which DeepEval metrics were run. Paginated client-side (the batch
// detail is already loaded in full). The leading "Your call" column captures the
// human Accept/Reject ground-truth mark used for judge-agreement %.
export default function EvalResultsTable({ uploadId, runId, questions }: EvalResultsTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0]);

  const labelMutation = useSetHumanVerdict(uploadId, runId);
  const setLabel = (evalId: string, verdict: HumanVerdict | null) =>
    labelMutation.mutate({ eval_id: evalId, verdict }, { onError: handleApiError });

  // Reset to the first page when the batch changes.
  useEffect(() => {
    setPage(1);
  }, [questions]);

  const pageRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return questions.slice(start, start + pageSize);
  }, [questions, page, pageSize]);

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
        key: 'human_verdict',
        title: 'Your call',
        align: 'center',
        width: 'w-[96px]',
        render: (_v, r) => (
          <HumanVerdictControl
            value={r.human_verdict}
            disabled={labelMutation.isPending}
            onSet={(verdict) => setLabel(r.eval_id, verdict)}
          />
        ),
      },
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
    ];
  }, [metricNames, labelMutation.isPending, setLabel]);

  return (
    <CustomTable
      columns={columns}
      dataSource={pageRows}
      rowKey="eval_id"
      pagination={{
        current: page,
        pageSize,
        total: questions.length,
        pageSizeOptions: PAGE_SIZE_OPTIONS,
        onChange: (p, size) => {
          setPage(p);
          setPageSize(size);
        },
      }}
      emptyState={
        <div className="py-10 text-center text-sm text-muted-foreground">
          No scored questions in this batch.
        </div>
      }
    />
  );
}
