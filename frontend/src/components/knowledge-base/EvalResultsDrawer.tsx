'use client';

import { useEffect, useId, useMemo, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronRight, MinusCircle, XCircle } from 'lucide-react';

import { CustomDrawer, SelectInput } from '@/components/shared';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import { useEvalRunDetail, useEvalRunsForIngestion } from '@/lib/api/evals';
import type {
  EvalRunSummary,
  EvalRunSummaryTotals,
  EvalScoredQuestion,
  EvalVerdict,
} from '@/types/eval';
import type { IngestionRun } from '@/types/ingestionRun';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';

interface EvalResultsDrawerProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  ingestionRun: IngestionRun | null;
}

const verdictStyle: Record<
  EvalVerdict,
  { label: string; className: string; icon: React.ReactNode }
> = {
  PASS: {
    label: 'Pass',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  PARTIAL: {
    label: 'Partial',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <MinusCircle className="size-3" />,
  },
  FAIL: {
    label: 'Fail',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

const formatPercent = (v: number) => `${Math.round(v * 100)}%`;
const formatDecimal = (v: number) => (Number.isFinite(v) ? v.toFixed(2) : '—');

function VerdictChip({ verdict }: { verdict: EvalVerdict }) {
  const s = verdictStyle[verdict] ?? verdictStyle.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {s.label}
    </span>
  );
}

function IngestionRunRecipe({ run }: { run: IngestionRun }) {
  return (
    <section className="rounded-lg border border-border/60 bg-muted/30 p-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Ingestion recipe (run #{run.run_number})
      </h4>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12.5px]">
        <div>
          <dt className="text-[11px] text-muted-foreground">Parser</dt>
          <dd className="mt-0.5 text-foreground">{run.parser}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Tokeniser</dt>
          <dd className="mt-0.5 text-foreground">{run.tokeniser}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-[11px] text-muted-foreground">Embedder</dt>
          <dd className="mt-0.5 text-foreground">
            {run.embedding_model}
            <span className="ml-1 text-muted-foreground">
              · {run.embedding_provider} · {run.embedding_dimensions}D
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Store</dt>
          <dd className="mt-0.5 text-foreground">{run.vector_store}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-muted-foreground">Chunks</dt>
          <dd className="mt-0.5 tabular-nums text-foreground">
            {run.chunk_count == null ? '—' : run.chunk_count.toLocaleString()}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function SummaryStrip({
  summary,
  batch,
}: {
  summary: EvalRunSummaryTotals;
  batch: EvalRunSummary;
}) {
  const cells: { label: string; value: React.ReactNode }[] = [
    {
      label: 'Score',
      value: (
        <span className="tabular-nums">
          <span className="text-emerald-600">{summary.pass}</span>
          {' / '}
          {summary.total}
        </span>
      ),
    },
    {
      label: 'Pass rate',
      value: <span className="tabular-nums">{formatPercent(summary.pass_rate)}</span>,
    },
    {
      label: 'Retrieval hit',
      value: <span className="tabular-nums">{formatPercent(summary.retrieval_hit_rate)}</span>,
    },
    {
      label: 'Avg correctness',
      value: <span className="tabular-nums">{formatDecimal(summary.avg_correctness)}</span>,
    },
    {
      label: 'Avg groundedness',
      value: <span className="tabular-nums">{formatDecimal(summary.avg_groundedness)}</span>,
    },
    {
      label: 'Avg relevance',
      value: <span className="tabular-nums">{formatDecimal(summary.avg_relevance)}</span>,
    },
  ];
  return (
    <section className="rounded-lg border border-border/60 bg-card p-3">
      <div className="grid grid-cols-3 gap-3 text-[12.5px] sm:grid-cols-6">
        {cells.map((c) => (
          <div key={c.label}>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
              {c.label}
            </div>
            <div className="mt-0.5 font-medium text-foreground">{c.value}</div>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border/60 pt-2 text-[11px] text-muted-foreground">
        <span>
          Answer model: <span className="text-foreground">{batch.answer_model ?? '—'}</span>
        </span>
        <span>
          Judge: <span className="text-foreground">{batch.judge_model ?? '—'}</span>
        </span>
        <span>
          Top-K: <span className="text-foreground tabular-nums">{batch.top_k}</span>
        </span>
        <span>
          Triggered: <span className="text-foreground">{batch.triggered_by}</span>
        </span>
        {batch.completed_at && (
          <span>
            Completed: <span className="text-foreground">{formatDate(batch.completed_at)}</span>
          </span>
        )}
      </div>
    </section>
  );
}

function ChunkRow({
  index,
  score,
  text,
}: {
  index: number;
  score: number | null | undefined;
  text: string | null | undefined;
}) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();
  return (
    <div className="rounded bg-muted/40">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-2 py-1.5 text-left font-sans text-[11px] text-muted-foreground"
        aria-expanded={expanded}
        aria-controls={panelId}
      >
        {expanded ? (
          <ChevronDown className="size-3.5 shrink-0" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0" />
        )}
        <span>chunk {index + 1}</span>
        {typeof score === 'number' && (
          <span className="tabular-nums">score {score.toFixed(3)}</span>
        )}
      </button>
      {expanded && (
        <div
          id={panelId}
          className="whitespace-pre-wrap border-t border-border/60 px-2 py-2 font-mono text-[12px] text-foreground"
        >
          {text ?? '—'}
        </div>
      )}
    </div>
  );
}

function QuestionRow({ q }: { q: EvalScoredQuestion }) {
  const [expanded, setExpanded] = useState(false);
  const chunks = q.retrieved_chunks ?? [];
  return (
    <div className="rounded-md border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
      >
        {expanded ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictChip verdict={q.judge.verdict} />
            <span className="text-[11px] text-muted-foreground">
              {q.category} · #{q.id}
            </span>
            {!q.retrieval_hit && (
              <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-amber-500/20 dark:text-amber-400">
                no retrieval hit
              </span>
            )}
            <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
              c {formatDecimal(q.judge.correctness)} · g {formatDecimal(q.judge.groundedness)} · r{' '}
              {formatDecimal(q.judge.relevance)}
              {q.latency_ms != null && ` · ${q.latency_ms}ms`}
            </span>
          </div>
          <div className="mt-1 text-[13px] font-medium text-foreground">{q.question}</div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border/60 px-3 py-3">
          <div className="grid grid-cols-1 gap-3 text-[12.5px] md:grid-cols-2">
            <div>
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Expected answer
              </div>
              <div className="mt-1 whitespace-pre-wrap text-foreground">
                {q.expected_answer || '—'}
              </div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Actual answer
              </div>
              <div className="mt-1 whitespace-pre-wrap text-foreground">
                {q.actual_answer || '—'}
              </div>
            </div>
            {q.expected_source_snippet && (
              <div className="md:col-span-2">
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  Expected source snippet
                </div>
                <div className="mt-1 rounded bg-muted/40 p-2 font-mono text-[12px] text-foreground">
                  {q.expected_source_snippet}
                </div>
              </div>
            )}
            {q.judge.reasoning && (
              <div className="md:col-span-2">
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  Judge reasoning
                </div>
                <div className="mt-1 whitespace-pre-wrap text-foreground">
                  {formatIngestionError(q.judge.reasoning) ?? q.judge.reasoning}
                </div>
              </div>
            )}
            {(q.retrieval_error || q.answer_error) && (
              <div className="md:col-span-2">
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                  Errors
                </div>
                {q.retrieval_error && (
                  <div className="mt-1 text-destructive">
                    Retrieval: {formatIngestionError(q.retrieval_error) ?? q.retrieval_error}
                  </div>
                )}
                {q.answer_error && (
                  <div className="mt-1 text-destructive">
                    Answer: {formatIngestionError(q.answer_error) ?? q.answer_error}
                  </div>
                )}
              </div>
            )}
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Retrieved chunks ({chunks.length})
              </div>
              <div className="mt-1 space-y-2">
                {chunks.length === 0 && <div className="text-muted-foreground">None</div>}
                {chunks.map((c, i) => (
                  <ChunkRow
                    key={i}
                    index={i}
                    score={c.score}
                    text={c.text as string | null | undefined}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
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
