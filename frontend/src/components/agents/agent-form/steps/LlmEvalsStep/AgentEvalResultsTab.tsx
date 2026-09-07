'use client';

import { Loader2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { SelectInput } from '@/components/shared';
import {
  useAgentLlmEvalRunDetail,
  useAgentLlmEvalRuns,
  useAgentLlmEvalVersions,
} from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalRunSummaryTotals } from '@/types/agentLlmEval';
import { formatDate } from '@/utils/date';

import AgentEvalResultsTable from './AgentEvalResultsTable';
import AgentEvalSummaryStrip from './AgentEvalSummaryStrip';
import { versionLabel } from './constants';

const ALL = '__all__';

const HINT_CLASS =
  'rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground';

// Eval-run results as a metrics table, filterable by version and run. Mirrors
// the RAG ``EvalResultsTab``. Reads existing endpoints (runs filtered by
// version + run detail) — no backend change.
export default function AgentEvalResultsTab({ agentId }: { agentId: string }) {
  const versionsQuery = useAgentLlmEvalVersions(agentId);
  const versions = useMemo(() => versionsQuery.data?.items ?? [], [versionsQuery.data]);

  const [versionFilter, setVersionFilter] = useState<string>(ALL);

  const runsQuery = useAgentLlmEvalRuns(agentId, {
    page_size: 100,
    version_id: versionFilter === ALL ? undefined : versionFilter,
  });
  // Only terminal runs have scored rows to show.
  const runs = useMemo(
    () =>
      (runsQuery.data?.items ?? []).filter(
        (r) => r.status === 'completed' || r.status === 'failed',
      ),
    [runsQuery.data],
  );

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  useEffect(() => {
    if (runs.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !runs.some((r) => r.run_id === selectedRunId)) {
      setSelectedRunId(runs[0].run_id);
    }
  }, [runs, selectedRunId]);

  const detailQuery = useAgentLlmEvalRunDetail(agentId, selectedRunId);
  const scenarios = detailQuery.data?.scenarios ?? [];
  const totals = detailQuery.data?.summary?.summary as
    | AgentLlmEvalRunSummaryTotals
    | Record<string, never>
    | undefined;
  const hasTotals = !!totals && typeof (totals as AgentLlmEvalRunSummaryTotals).total === 'number';

  const versionOptions = useMemo(
    () => [
      { value: ALL, label: 'All versions' },
      ...versions.map((v) => ({ value: v.id, label: versionLabel(v) })),
    ],
    [versions],
  );

  const runOptions = useMemo(
    () =>
      runs.map((r) => ({
        value: r.run_id,
        label: `Run #${r.run_number}${r.started_at ? ` · ${formatDate(r.started_at)}` : ''}`,
      })),
    [runs],
  );

  return (
    <div className="flex flex-col gap-4">
      {/* Filters: version + run. */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-[220px] sm:min-w-[260px]">
          <SelectInput
            name="results-version-filter"
            label="Version"
            value={versionFilter}
            onValueChange={(v) => v && setVersionFilter(v)}
            options={versionOptions}
          />
        </div>
        <div className="min-w-[220px] sm:min-w-[260px]">
          <SelectInput
            name="results-run"
            label="Run"
            value={selectedRunId ?? undefined}
            onValueChange={(v) => setSelectedRunId(v || null)}
            options={runOptions}
            placeholder={runOptions.length ? 'Select a run' : 'No completed runs'}
            disabled={runOptions.length === 0}
          />
        </div>
      </div>

      {runsQuery.isLoading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading runs…
        </div>
      ) : runs.length === 0 ? (
        <div className={HINT_CLASS}>
          No completed eval runs yet. Run an eval from the Manage Evals tab to see scored results here.
        </div>
      ) : detailQuery.isLoading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading results…
        </div>
      ) : (
        <>
          {hasTotals && (
            <AgentEvalSummaryStrip summary={totals as AgentLlmEvalRunSummaryTotals} />
          )}
          <AgentEvalResultsTable scenarios={scenarios} />
        </>
      )}
    </div>
  );
}
