'use client';

import { useEffect, useMemo, useState } from 'react';

import EvalResultsTable from '@/components/knowledge-base/EvalResultsTable';
import SummaryStrip from '@/components/knowledge-base/SummaryStrip';
import { versionLabel } from '@/components/knowledge-base/evalsConstants';
import { SelectInput } from '@/components/shared';
import {
  useEvalRunDetail,
  useEvalRunsFiltered,
  useInFlightEvalRunIds,
  useEvalVersions,
} from '@/lib/api/evals';
import { useIngestionRuns } from '@/lib/api/ingestion-runs';
import type { EvalRunSummaryTotals } from '@/types/eval';
import { formatDate } from '@/utils/date';

interface EvalResultsTabProps {
  uploadId: string;
}

const HINT_CLASS =
  'rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground';

const ALL = '__all__';

// Eval-batch results as a table, filterable by eval version and ingestion run.
export default function EvalResultsTab({ uploadId }: EvalResultsTabProps) {
  const { data: versions = [] } = useEvalVersions(uploadId);
  const { data: runsResp } = useIngestionRuns(uploadId, {
    status_filter: ['ready'],
    page_size: 100,
    sort_by: 'run_number',
    sort_order: 'desc',
  });
  const readyRuns = useMemo(() => runsResp?.data ?? [], [runsResp]);

  const [versionFilter, setVersionFilter] = useState<string>(ALL);
  const [ingestionFilter, setIngestionFilter] = useState<string>(ALL);

  const filters = useMemo(
    () => ({
      eval_version_id: versionFilter === ALL ? null : versionFilter,
      ingestion_run_id: ingestionFilter === ALL ? null : ingestionFilter,
    }),
    [versionFilter, ingestionFilter],
  );

  // While any visible ingestion run has a queued/running eval batch, poll the
  // batches list so a just-finished run appears without a manual refresh.
  const readyRunIds = useMemo(() => readyRuns.map((r) => r.id), [readyRuns]);
  const inFlightRunIds = useInFlightEvalRunIds(uploadId, readyRunIds);

  const batchesQuery = useEvalRunsFiltered(uploadId, filters, inFlightRunIds.size > 0);
  const batches = useMemo(() => batchesQuery.data ?? [], [batchesQuery.data]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  useEffect(() => {
    if (batches.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !batches.some((b) => b.run_id === selectedRunId)) {
      setSelectedRunId(batches[0].run_id);
    }
  }, [batches, selectedRunId]);

  const versionOptions = useMemo(
    () => [
      { value: ALL, label: 'All versions' },
      ...versions.map((v) => ({ value: v.id, label: versionLabel(v) })),
    ],
    [versions],
  );

  const ingestionOptions = useMemo(
    () => [
      { value: ALL, label: 'All ingestion runs' },
      ...readyRuns.map((r) => ({
        value: r.id,
        label: `Run #${r.run_number}${r.is_active ? ' (active)' : ''}`,
      })),
    ],
    [readyRuns],
  );

  const batchOptions = useMemo(
    () =>
      batches.map((b) => ({
        value: b.run_id,
        label: `Batch #${b.run_number}${b.started_at ? ` · ${formatDate(b.started_at)}` : ''}${
          b.status === 'failed' ? ' · failed' : ''
        }`,
      })),
    [batches],
  );

  const detailQuery = useEvalRunDetail(uploadId, selectedRunId);
  const summaryTotals = detailQuery.data?.summary.summary as
    | EvalRunSummaryTotals
    | Record<string, never>
    | undefined;
  const hasSummary =
    summaryTotals != null && typeof (summaryTotals as EvalRunSummaryTotals).total === 'number';

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 py-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Eval results</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Every question scored in a batch — expected vs. actual answer and each DeepEval metric.
          Filter by version and ingestion run.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Version
          </label>
          <div className="min-w-[240px]">
            <SelectInput
              name="results-version-filter"
              value={versionFilter}
              onValueChange={(v) => setVersionFilter(v || ALL)}
              options={versionOptions}
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Ingest recipe
          </label>
          <div className="min-w-[220px]">
            <SelectInput
              name="results-ingestion-filter"
              value={ingestionFilter}
              onValueChange={(v) => setIngestionFilter(v || ALL)}
              options={ingestionOptions}
            />
          </div>
        </div>
        {batches.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Batch
            </label>
            <div className="min-w-[260px]">
              <SelectInput
                name="results-batch"
                value={selectedRunId ?? undefined}
                onValueChange={(v) => setSelectedRunId(v || null)}
                options={batchOptions}
                placeholder="Select a batch"
              />
            </div>
          </div>
        )}
      </div>

      {batchesQuery.isLoading && <div className={HINT_CLASS}>Loading eval batches…</div>}

      {!batchesQuery.isLoading && batches.length === 0 && (
        <div className={HINT_CLASS}>
          No eval batches match these filters — run an eval from the Manage evals tab.
        </div>
      )}

      {detailQuery.isLoading && selectedRunId && <div className={HINT_CLASS}>Loading batch…</div>}

      {detailQuery.data && hasSummary && (
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <SummaryStrip
            summary={summaryTotals as EvalRunSummaryTotals}
            batch={detailQuery.data.summary}
          />
          <EvalResultsTable questions={detailQuery.data.questions} />
        </div>
      )}
    </div>
  );
}
