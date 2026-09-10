'use client';

import { useEffect, useMemo, useState } from 'react';

import EvalResultsTable from '@/components/knowledge-base/EvalResultsTable';
import SummaryStrip from '@/components/knowledge-base/SummaryStrip';
import { ingestionRunLabel } from '@/components/knowledge-base/ingestionRunLabel';
import { versionNumberMap } from '@/components/knowledge-base/evalsConstants';
import { SelectInput } from '@/components/shared';
import {
  useEvalRunDetail,
  useEvalRunsFiltered,
  useEvalVersions,
  useInFlightEvalRunIds,
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

// Eval-batch results as a table. Two-step picker: choose an ingestion run, then
// a batch (each labelled with its version + date) — the version is shown on the
// batch itself, so no separate version filter is needed.
export default function EvalResultsTab({ uploadId }: EvalResultsTabProps) {
  const { data: versions = [] } = useEvalVersions(uploadId);
  const { data: runsResp } = useIngestionRuns(uploadId, {
    status_filter: ['ready'],
    page_size: 100,
    sort_by: 'run_number',
    sort_order: 'desc',
  });
  const readyRuns = useMemo(() => runsResp?.data ?? [], [runsResp]);

  const [ingestionFilter, setIngestionFilter] = useState<string>(ALL);

  const filters = useMemo(
    () => ({
      eval_version_id: null,
      ingestion_run_id: ingestionFilter === ALL ? null : ingestionFilter,
    }),
    [ingestionFilter],
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

  const ingestionOptions = useMemo(
    () => [
      { value: ALL, label: 'All ingestion runs' },
      ...readyRuns.map((r) => ({
        value: r.id,
        label: `${ingestionRunLabel(r)}${r.is_active ? ' (active)' : ''}`,
      })),
    ],
    [readyRuns],
  );

  // version id → "v<N>" so a batch can carry its version in the label.
  const versionNumberById = useMemo(() => versionNumberMap(versions), [versions]);

  const batchOptions = useMemo(
    () =>
      batches.map((b) => {
        const versionNo = b.eval_version_id ? versionNumberById.get(b.eval_version_id) : undefined;
        const versionPart = versionNo ? `v${versionNo}` : 'Unversioned';
        const datePart = b.started_at ? ` · ${formatDate(b.started_at)}` : '';
        const failedPart = b.status === 'failed' ? ' · failed' : '';
        return { value: b.run_id, label: `${versionPart}${datePart}${failedPart}` };
      }),
    [batches, versionNumberById],
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
          Pick an ingestion run, then a batch.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Ingestion run
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
          No eval batches for this ingestion run — run an eval from the Manage evals tab.
        </div>
      )}

      {detailQuery.isLoading && selectedRunId && <div className={HINT_CLASS}>Loading batch…</div>}

      {detailQuery.data && hasSummary && selectedRunId && (
        <div className="flex min-h-0 flex-1 flex-col gap-4">
          <SummaryStrip
            summary={summaryTotals as EvalRunSummaryTotals}
            batch={detailQuery.data.summary}
          />
          <EvalResultsTable
            uploadId={uploadId}
            runId={selectedRunId}
            questions={detailQuery.data.questions}
          />
        </div>
      )}
    </div>
  );
}
