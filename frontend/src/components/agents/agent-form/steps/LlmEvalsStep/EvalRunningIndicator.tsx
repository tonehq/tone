'use client';

import { Loader2 } from 'lucide-react';

import { useAgentLlmEvalRuns } from '@/lib/api/agentLlmEvals';

import { IN_PROGRESS_CHIP_CLASS } from './constants';
import StatusPill from './StatusPill';

// Live "an eval is running" indicator for the agent LLM evals tabs. Reads the
// runs list (which already polls while a run is pending/running) and shows a
// spinner chip until every run is terminal — mirroring the version bar's
// "Generating…" chip so both async actions surface the same way. Renders
// nothing when no run is in flight.
export default function EvalRunningIndicator({ agentId }: { agentId: string }) {
  const runsQuery = useAgentLlmEvalRuns(agentId, { page_size: 100 });
  const active = (runsQuery.data?.items ?? []).filter(
    (r) => r.status === 'pending' || r.status === 'running',
  );
  if (active.length === 0) return null;

  const run = active[0];
  let label: string;
  if (active.length > 1) {
    label = `${active.length} evaluations running…`;
  } else if (run.status === 'pending') {
    label = 'Evaluation queued…';
  } else if (run.total_scenarios > 0) {
    label = `Evaluation running… ${run.scored_count}/${run.total_scenarios} scored`;
  } else {
    label = 'Evaluation running…';
  }

  return (
    <StatusPill
      icon={<Loader2 className="size-3 animate-spin" />}
      label={label}
      className={IN_PROGRESS_CHIP_CLASS}
    />
  );
}
