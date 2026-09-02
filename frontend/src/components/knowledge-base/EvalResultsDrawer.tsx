'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomDrawer, SelectInput } from '@/components/shared';
import IngestionRunRecipe from '@/components/knowledge-base/IngestionRunRecipe';
import QuestionRow from '@/components/knowledge-base/QuestionRow';
import SummaryStrip from '@/components/knowledge-base/SummaryStrip';
import { useEvalRunDetail, useEvalRunsForIngestion } from '@/lib/api/evals';
import type { EvalRunSummaryTotals } from '@/types/eval';
import type { IngestionRun } from '@/types/ingestionRun';
import { formatDate } from '@/utils/date';

interface EvalResultsDrawerProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  ingestionRun: IngestionRun | null;
}

export default function EvalResultsDrawer({
  open,
  onClose,
  uploadId,
  ingestionRun,
}: EvalResultsDrawerProps) {
  const ingestionRunId = ingestionRun?.id ?? null;

  const runsQuery = useEvalRunsForIngestion(open ? uploadId : null, open ? ingestionRunId : null);
  const runs = runsQuery.data ?? [];

  // Newest batch is the default selection. Reset when the drawer opens
  // against a different ingestion run.
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  useEffect(() => {
    if (!open) {
      setSelectedRunId(null);
      return;
    }
    if (runs.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !runs.some((r) => r.run_id === selectedRunId)) {
      setSelectedRunId(runs[0].run_id);
    }
  }, [open, runs, selectedRunId]);

  const detailQuery = useEvalRunDetail(open ? uploadId : null, selectedRunId);

  const runOptions = useMemo(
    () =>
      runs.map((r) => ({
        value: r.run_id,
        label: `Run #${r.run_number}${r.started_at ? ` · ${formatDate(r.started_at)}` : ''}${
          r.status === 'failed' ? ' · failed' : ''
        }`,
      })),
    [runs],
  );

  const summaryTotals = detailQuery.data?.summary.summary as
    | EvalRunSummaryTotals
    | Record<string, never>
    | undefined;
  const hasSummary =
    summaryTotals != null && typeof (summaryTotals as EvalRunSummaryTotals).total === 'number';

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={
        ingestionRun ? `Eval results · ingestion run #${ingestionRun.run_number}` : 'Eval results'
      }
      description="Every question scored against this ingestion recipe."
      width="w-[900px] sm:max-w-[95vw]"
    >
      <div className="flex flex-col gap-4">
        {ingestionRun && <IngestionRunRecipe run={ingestionRun} />}

        {runsQuery.isLoading && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            Loading eval batches…
          </div>
        )}

        {!runsQuery.isLoading && runs.length === 0 && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            No eval batches have scored this ingestion run yet.
          </div>
        )}

        {runs.length > 0 && (
          <div className="flex items-center gap-3">
            <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Batch
            </label>
            <div className="min-w-[260px]">
              <SelectInput
                name="eval-batch"
                value={selectedRunId ?? undefined}
                onValueChange={(v) => setSelectedRunId(v || null)}
                options={runOptions}
                placeholder="Select a batch"
              />
            </div>
            <span className="text-[11px] text-muted-foreground">
              {runs.length} batch{runs.length === 1 ? '' : 'es'}
            </span>
          </div>
        )}

        {detailQuery.isLoading && selectedRunId && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            Loading batch…
          </div>
        )}

        {detailQuery.data && hasSummary && (
          <>
            <SummaryStrip
              summary={summaryTotals as EvalRunSummaryTotals}
              batch={detailQuery.data.summary}
            />
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-foreground">
                  Questions ({detailQuery.data.questions.length})
                </h4>
              </div>
              {detailQuery.data.questions.length === 0 ? (
                <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
                  No scored questions in this batch.
                </div>
              ) : (
                <div className="flex flex-col gap-2">
                  {detailQuery.data.questions.map((q) => (
                    <QuestionRow key={q.eval_id} q={q} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </CustomDrawer>
  );
}
