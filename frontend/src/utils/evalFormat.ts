import type { EvalModelOption } from '@/types/evalSettings';

// Shared eval score formatters used by BOTH eval features (KB/RAG evals and
// agent-LLM evals). These operate on 0..1 ratios (pass rate, metric score),
// which is why they can't reuse ``@/lib/utils`` ``formatPercent`` (that one
// expects an already-scaled 0..100 value).

export interface EvalModelSelectOption {
  value: string;
  label: string;
}

// Map the eval model catalog to `{value,label}` dropdown options, surfacing a
// persisted value that's no longer in the catalog as an "(unavailable)" row so
// an admin-disabled model is never silently dropped from the list. The single
// source for BOTH the eval-settings model pickers and the evaluation-config
// judge-model picker.
export function buildEvalModelOptions(
  models: EvalModelOption[] | undefined,
  currentValue?: string | null,
): EvalModelSelectOption[] {
  const opts = (models ?? []).map((m) => ({
    value: m.name,
    label: `${m.display_name} — ${m.provider_display_name}`,
  }));
  if (currentValue && !opts.some((o) => o.value === currentValue)) {
    opts.unshift({ value: currentValue, label: `${currentValue} (unavailable)` });
  }
  return opts;
}

// 0..1 ratio → whole-number percent, e.g. 0.4 → "40%". Non-finite → "—".
export const formatRatioPercent = (v: number | null | undefined): string =>
  typeof v === 'number' && Number.isFinite(v) ? `${Math.round(v * 100)}%` : '—';

// A metric score → 2-decimal string, e.g. 0.9166 → "0.92". Non-finite → "—".
export const formatMetricScore = (v: number | null | undefined): string =>
  typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : '—';
