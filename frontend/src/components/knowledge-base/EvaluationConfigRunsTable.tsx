'use client';

import { useMemo } from 'react';

import { CheckboxField, CustomTable } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type { EvaluationConfig, EvaluationConfigRunSummary } from '@/types/evaluationConfig';
import { formatMetricScore } from '@/utils/evalFormat';

import { configNameById, verdictSummary } from './evalConfigHelpers';

interface EvaluationConfigRunsTableProps {
  passes: EvaluationConfigRunSummary[];
  configs: EvaluationConfig[];
  selectedIds: string[];
  maxCompare: number;
  loading?: boolean;
  onToggle: (configRunId: string, checked: boolean) => void;
}

// One row per config pass against the current source run. The leading checkbox
// selects up to `maxCompare` passes to compare (disabled once the cap is hit).
export default function EvaluationConfigRunsTable({
  passes,
  configs,
  selectedIds,
  maxCompare,
  loading,
  onToggle,
}: EvaluationConfigRunsTableProps) {
  const columns = useMemo<CustomTableColumn<EvaluationConfigRunSummary>[]>(
    () => [
      {
        key: 'select',
        title: '',
        width: 'w-[44px]',
        render: (_v, r) => (
          <CheckboxField
            id={`pass-${r.config_run_id}`}
            checked={selectedIds.includes(r.config_run_id)}
            disabled={!selectedIds.includes(r.config_run_id) && selectedIds.length >= maxCompare}
            onCheckedChange={(checked) => onToggle(r.config_run_id, checked === true)}
          />
        ),
      },
      {
        key: 'config',
        title: 'Evaluator',
        render: (_v, r) => (
          <span className="font-medium text-foreground">
            {configNameById(configs, r.evaluation_config_id)}
          </span>
        ),
      },
      {
        key: 'run',
        title: 'Run',
        render: (_v, r) => `#${r.config_run_number}`,
      },
      {
        key: 'judge_model',
        title: 'Judge model',
        render: (_v, r) => r.judge_model ?? '—',
      },
      {
        key: 'avg',
        title: 'Avg score',
        align: 'center',
        render: (_v, r) => formatMetricScore(r.average_score),
      },
      {
        key: 'verdicts',
        title: 'Verdicts',
        render: (_v, r) => verdictSummary(r.verdicts),
      },
      {
        key: 'total',
        title: 'Scored',
        align: 'center',
        dataIndex: 'total',
      },
    ],
    [configs, selectedIds, maxCompare, onToggle],
  );

  return (
    <CustomTable
      columns={columns}
      dataSource={passes}
      rowKey="config_run_id"
      loading={loading}
      pagination={false}
      emptyState="No re-grades yet for this run. Run a config above to see scores here."
    />
  );
}
