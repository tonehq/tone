// Display order, labels, and formatting for the agent-LLM eval metric keys
// stored in ``agent_llm_eval_results.metric_scores``. The results table derives
// its metric columns dynamically from the keys present in a run; this module
// only fixes their ORDER, header LABELS, and score formatting.
//
// Agent-LLM metric scores are ``{ score, reason }`` (no per-metric verdict, unlike
// the RAG side), so the score pill is colored by score band rather than a verdict.

export const METRIC_DISPLAY_ORDER: readonly string[] = [
  'correctness',
  'answer_relevancy',
  'faithfulness',
  'persona_adherence',
  'instruction_following',
  'hallucination',
  'bias',
  'toxicity',
  'tool_selection',
];

const METRIC_LABELS: Record<string, string> = {
  correctness: 'Correctness',
  answer_relevancy: 'Answer relevancy',
  faithfulness: 'Faithfulness',
  persona_adherence: 'Persona adherence',
  instruction_following: 'Instruction following',
  hallucination: 'Hallucination',
  bias: 'Bias',
  toxicity: 'Toxicity',
  tool_selection: 'Tool selection',
};

// Human label for a metric key; falls back to a title-cased version of the raw
// key so an unmapped metric still reads sensibly.
export function metricLabel(name: string): string {
  if (METRIC_LABELS[name]) return METRIC_LABELS[name];
  return name
    .split('_')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');
}

// Order a set of metric names by METRIC_DISPLAY_ORDER, appending any unknown
// names alphabetically so the columns are stable across renders/runs.
export function orderMetricNames(names: string[]): string[] {
  const known = METRIC_DISPLAY_ORDER.filter((m) => names.includes(m));
  const unknown = names.filter((m) => !METRIC_DISPLAY_ORDER.includes(m)).sort();
  return [...known, ...unknown];
}

export const formatPercent = (v: number): string =>
  Number.isFinite(v) ? `${Math.round(v * 100)}%` : '—';

export const formatDecimal = (v: number | undefined): string =>
  typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : '—';

// Tailwind classes for a metric-score pill, colored by score band (agent-LLM
// metric scores carry no per-metric verdict). Mirrors the VerdictChip palette.
export const metricScoreClasses = (score: number | undefined): string => {
  if (typeof score !== 'number' || !Number.isFinite(score)) {
    return 'bg-muted text-muted-foreground ring-1 ring-border/60';
  }
  if (score >= 0.8) {
    return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20';
  }
  if (score >= 0.5) {
    return 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20';
  }
  return 'bg-destructive/10 text-destructive ring-1 ring-destructive/20';
};
