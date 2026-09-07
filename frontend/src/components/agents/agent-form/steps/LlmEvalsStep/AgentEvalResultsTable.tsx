'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomTable } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type { AgentLlmEvalScoredScenario } from '@/types/agentLlmEval';

import AgentEvalMetricScoreCell from './AgentEvalMetricScoreCell';
import AgentEvalTruncatedCell from './AgentEvalTruncatedCell';
import { metricLabel, orderMetricNames } from './evalMetrics';
import VerdictChip from './VerdictChip';

const PAGE_SIZE_OPTIONS = [10, 20, 50];

// One row per scored scenario. Metric columns are derived dynamically from the
// ``metric_scores`` keys present across the run, so the table always matches
// exactly which metrics were scored. Paginated client-side (the run detail is
// already loaded in full).
export default function AgentEvalResultsTable({
  scenarios,
}: {
  scenarios: AgentLlmEvalScoredScenario[];
}) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(PAGE_SIZE_OPTIONS[0]);

  useEffect(() => {
    setPage(1);
  }, [scenarios]);

  const pageRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return scenarios.slice(start, start + pageSize);
  }, [scenarios, page, pageSize]);

  const metricNames = useMemo(() => {
    const names = new Set<string>();
    for (const s of scenarios) {
      for (const name of Object.keys(s.metric_scores ?? {})) names.add(name);
    }
    return orderMetricNames([...names]);
  }, [scenarios]);

  const columns = useMemo<CustomTableColumn<AgentLlmEvalScoredScenario>[]>(() => {
    const metricColumns: CustomTableColumn<AgentLlmEvalScoredScenario>[] = metricNames.map(
      (name) => ({
        key: `metric:${name}`,
        title: metricLabel(name),
        align: 'center',
        width: 'w-[110px]',
        render: (_v, r) => <AgentEvalMetricScoreCell metric={r.metric_scores?.[name]} />,
      }),
    );

    return [
      {
        key: 'scenario_key',
        title: 'Scenario',
        width: 'w-[180px]',
        render: (_v, r) => (
          <span className="font-medium text-foreground" title={r.scenario_key}>
            {r.scenario_key}
          </span>
        ),
      },
      {
        key: 'verdict',
        title: 'Verdict',
        align: 'center',
        width: 'w-[110px]',
        render: (_v, r) => <VerdictChip verdict={r.verdict} />,
      },
      {
        key: 'prompt',
        title: 'Prompt',
        width: 'w-[240px]',
        render: (_v, r) => <AgentEvalTruncatedCell text={r.prompt} />,
      },
      {
        key: 'expected_answer',
        title: 'Expected answer',
        width: 'w-[240px]',
        render: (_v, r) => <AgentEvalTruncatedCell text={r.expected_answer} />,
      },
      {
        key: 'actual_answer',
        title: 'Actual answer',
        width: 'w-[240px]',
        render: (_v, r) => <AgentEvalTruncatedCell text={r.actual_answer} />,
      },
      ...metricColumns,
    ];
  }, [metricNames]);

  return (
    <CustomTable
      columns={columns}
      dataSource={pageRows}
      rowKey="id"
      pagination={{
        current: page,
        pageSize,
        total: scenarios.length,
        pageSizeOptions: PAGE_SIZE_OPTIONS,
        onChange: (p, size) => {
          setPage(p);
          setPageSize(size);
        },
      }}
      emptyState={
        <div className="py-10 text-center text-sm text-muted-foreground">
          No scored scenarios in this run.
        </div>
      }
    />
  );
}
