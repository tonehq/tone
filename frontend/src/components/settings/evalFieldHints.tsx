'use client';

import { Info } from 'lucide-react';

import CustomTooltip from '@/components/shared/CustomTooltip';

// Plain-English copy shown in the ⓘ tooltip next to each eval-settings field.
// Mirrors ``frontend/src/components/knowledge-base/ingestionFieldHints.tsx`` —
// single source of truth for evaluation UX copy.

export const EVAL_FIELD_HINTS = {
  auto_run_enabled:
    'When on, evals run automatically after every ingestion. Turn off to control cost.',
  generation_model: 'The LLM that writes the question set the first time evals run for a document.',
  answer_model: 'The LLM that answers each question (the "student" being tested).',
  judge_model: 'The LLM that scores each answer (the "teacher"). Also used by agent LLM evals.',
  judge_engine: 'Framework that structures the scoring. "deepeval" is the production default.',
  top_k:
    'How many chunks to retrieve per question. Lower = tighter context, higher contextual_relevancy.',
  max_context_chars:
    'Cap on the total chunk text passed to the answer model per question. Prevents runaway prompt sizes.',
  metric_threshold: 'Score at or above which one metric passes. 0.7 is DeepEval’s default.',
  metrics_enabled: 'Which DeepEval metrics run per question. Uncheck a metric to skip it entirely.',
} as const;

export type EvalFieldKey = keyof typeof EVAL_FIELD_HINTS;

export function HintIcon({ text }: { text: string }) {
  return (
    <CustomTooltip content={text}>
      <Info className="size-3.5 cursor-help text-muted-foreground" />
    </CustomTooltip>
  );
}
