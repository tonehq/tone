'use client';

import type { ReactNode } from 'react';

import type { AgentLlmEvalRunSummaryTotals } from '@/types/agentLlmEval';

import { formatPercent } from './evalMetrics';

// Aggregate scorecard for the selected run — pass/total, pass rate, and the
// partial/fail breakdown. Mirrors the RAG SummaryStrip layout.
export default function AgentEvalSummaryStrip({
  summary,
}: {
  summary: AgentLlmEvalRunSummaryTotals;
}) {
  const cells: { label: string; value: ReactNode }[] = [
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
      label: 'Partial / Fail',
      value: (
        <span className="tabular-nums">
          <span className="text-amber-600">{summary.partial}</span>
          {' / '}
          <span className="text-destructive">{summary.fail}</span>
        </span>
      ),
    },
  ];

  return (
    <section className="rounded-lg border border-border/60 bg-card p-3">
      <div className="grid grid-cols-3 gap-3 text-[12.5px]">
        {cells.map((c) => (
          <div key={c.label}>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
              {c.label}
            </div>
            <div className="mt-0.5 font-medium text-foreground">{c.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
