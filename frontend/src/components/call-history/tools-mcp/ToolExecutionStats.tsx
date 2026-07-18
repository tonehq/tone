'use client';

import { StatCard } from '@/components/call-history/metrics/StatCard';
import { AlertCircle, CheckCircle2, Wrench, XCircle } from 'lucide-react';
import React from 'react';

import type { ToolExecutionSummary } from './helpers';

interface ToolExecutionStatsProps {
  summary: ToolExecutionSummary;
}

/**
 * Four KPI tiles above the executions table. Reuses the same `StatCard` used
 * by the Metrics section so call-detail tabs stay visually consistent.
 *
 * The `Total tool calls` tile counts every tool the LLM proposed, including
 * ones that never actually ran (`proposed`, `cancelled`) — the split is
 * spelled out in the `Not executed` tile. Success / error rates are computed
 * over the *executed* subset so the percentages stay meaningful even when a
 * call has a lot of interrupted proposals.
 */
const ToolExecutionStats: React.FC<ToolExecutionStatsProps> = ({ summary }) => {
  const successRate =
    summary.executed > 0 ? `${Math.round((summary.success / summary.executed) * 100)}%` : '—';
  const errorRate =
    summary.executed > 0 ? `${Math.round((summary.errors / summary.executed) * 100)}%` : '—';
  const notExecutedSub =
    summary.notExecuted > 0
      ? `${summary.proposed} proposed · ${summary.cancelled} cancelled`
      : 'all proposed calls ran';

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        icon={Wrench}
        label="Total tool calls"
        value={String(summary.total)}
        sub={`${summary.executed} executed of ${summary.total} proposed`}
        color="bg-slate-500"
      />
      <StatCard
        icon={CheckCircle2}
        label="Successful"
        value={String(summary.success)}
        sub={`${successRate} of executed`}
        color="bg-emerald-500"
      />
      <StatCard
        icon={XCircle}
        label="Errors"
        value={String(summary.errors)}
        sub={`${errorRate} of executed`}
        color="bg-rose-500"
      />
      <StatCard
        icon={AlertCircle}
        label="Not executed"
        value={String(summary.notExecuted)}
        sub={notExecutedSub}
        color="bg-amber-500"
      />
    </div>
  );
};

export default ToolExecutionStats;
