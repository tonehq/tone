// Shared eval score formatters used by BOTH eval features (KB/RAG evals and
// agent-LLM evals). These operate on 0..1 ratios (pass rate, metric score),
// which is why they can't reuse ``@/lib/utils`` ``formatPercent`` (that one
// expects an already-scaled 0..100 value).

// 0..1 ratio → whole-number percent, e.g. 0.4 → "40%". Non-finite → "—".
export const formatRatioPercent = (v: number | null | undefined): string =>
  typeof v === 'number' && Number.isFinite(v) ? `${Math.round(v * 100)}%` : '—';

// A metric score → 2-decimal string, e.g. 0.9166 → "0.92". Non-finite → "—".
export const formatMetricScore = (v: number | null | undefined): string =>
  typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : '—';
