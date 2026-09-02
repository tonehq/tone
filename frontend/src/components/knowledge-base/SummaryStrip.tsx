import { formatDecimal, formatPercent } from '@/components/knowledge-base/evalResultsHelpers';
import type { EvalRunSummary, EvalRunSummaryTotals } from '@/types/eval';
import { formatDate } from '@/utils/date';

export default function SummaryStrip({
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
