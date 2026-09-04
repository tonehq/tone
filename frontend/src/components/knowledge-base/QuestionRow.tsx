'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

import ChunkRow from '@/components/knowledge-base/ChunkRow';
import VerdictChip from '@/components/knowledge-base/VerdictChip';
import { formatDecimal } from '@/components/knowledge-base/evalResultsHelpers';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import { CustomButton } from '@/components/shared';
import type { EvalScoredQuestion } from '@/types/eval';

export default function QuestionRow({ q }: { q: EvalScoredQuestion }) {
  const [expanded, setExpanded] = useState(false);
  const chunks = q.retrieved_chunks ?? [];
  return (
    <div className="rounded-md border border-border/60 bg-card">
      <CustomButton
        type="text"
        fullWidth
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="h-auto items-start justify-start gap-2 whitespace-normal rounded-none bg-transparent px-3 py-2 text-left font-normal hover:bg-transparent"
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
      </CustomButton>

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
