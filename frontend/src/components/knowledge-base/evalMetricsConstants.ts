// Display order + human labels for the DeepEval metric keys stored in
// `eval_results.metric_scores` (mirrors core/services/evals/deepeval/
// metric_registry.py `SUPPORTED_METRICS`). The results table derives its
// metric columns dynamically from the scorecard keys present in a batch;
// this constant only fixes their ORDER and the header LABELS.

// Metrics render in this order when present. Unknown metric names (e.g. a
// newly added registry entry) are appended after these, alphabetically.
export const METRIC_DISPLAY_ORDER: readonly string[] = [
  'correctness',
  'faithfulness',
  'answer_relevancy',
  'contextual_precision',
  'contextual_recall',
  'contextual_relevancy',
  'hallucination',
  'bias',
  'toxicity',
  'persona_adherence',
  'instruction_following',
];

const METRIC_LABELS: Record<string, string> = {
  correctness: 'Correctness',
  faithfulness: 'Faithfulness',
  answer_relevancy: 'Answer relevancy',
  contextual_precision: 'Contextual precision',
  contextual_recall: 'Contextual recall',
  contextual_relevancy: 'Contextual relevancy',
  hallucination: 'Hallucination',
  bias: 'Bias',
  toxicity: 'Toxicity',
  persona_adherence: 'Persona adherence',
  instruction_following: 'Instruction following',
};

// Human label for a metric key; falls back to a title-cased version of the
// raw key so an unmapped metric still reads sensibly.
export function metricLabel(name: string): string {
  if (METRIC_LABELS[name]) return METRIC_LABELS[name];
  return name
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
}

// Order a set of metric names by METRIC_DISPLAY_ORDER, appending any unknown
// names alphabetically so the columns are stable across renders/batches.
export function orderMetricNames(names: string[]): string[] {
  const known = METRIC_DISPLAY_ORDER.filter((m) => names.includes(m));
  const unknown = names.filter((m) => !METRIC_DISPLAY_ORDER.includes(m)).sort();
  return [...known, ...unknown];
}
