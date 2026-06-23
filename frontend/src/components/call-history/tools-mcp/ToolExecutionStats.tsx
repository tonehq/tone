'use client';

import { StatCard } from '@/components/call-history/metrics/StatCard';
import { CheckCircle2, Gauge, Wrench, XCircle } from 'lucide-react';
import React from 'react';

import type { ToolExecutionSummary } from './helpers';

interface ToolExecutionStatsProps {
  summary: ToolExecutionSummary;
}

/**
 * Four KPI tiles above the executions table. Reuses the same `StatCard` used
 * by the Metrics section so call-detail tabs stay visually consistent.
 */
const ToolExecutionStats: React.FC<ToolExecutionStatsProps> = ({ summary }) => {
  const successRate =
    summary.total > 0 ? `${Math.round((summary.success / summary.total) * 100)}%` : '—';
  const errorRate =
    summary.total > 0 ? `${Math.round((summary.errors / summary.total) * 100)}%` : '—';
  const avgDuration = summary.avgDurationMs == null ? '—' : `${summary.avgDurationMs} ms`;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        icon={Wrench}
        label="Total invocations"
        value={String(summary.total)}
        color="bg-slate-500"
      />
      <StatCard
        icon={CheckCircle2}
        label="Successful"
        value={String(summary.success)}
        sub={`${successRate} success rate`}
        color="bg-emerald-500"
      />
      <StatCard
        icon={XCircle}
        label="Errors"
        value={String(summary.errors)}
        sub={`${errorRate} error rate`}
        color="bg-rose-500"
      />
      <StatCard icon={Gauge} label="Avg duration" value={avgDuration} color="bg-indigo-500" />
    </div>
  );
};

export default ToolExecutionStats;
