// Pure helpers for the Evaluation Config tab — aggregation over config-result
// rows for the compare view. Kept out of components per the repo's
// "no logic inline in a component" rule.

import type {
  EvaluationConfig,
  EvaluationConfigResult,
  EvaluationConfigResultRow,
  EvaluationConfigRunSummary,
} from '@/types/evaluationConfig';

import { orderMetricNames } from './evalMetricsConstants';

interface MetricAverage {
  metric: string;
  average: number;
  count: number;
}

// Mean per-metric score across a pass's rows. Rows missing a metric simply
// don't contribute to that metric's average. Internal — consumed only by
// buildCompareMatrix below.
function averageMetricScores(rows: EvaluationConfigResult[]): MetricAverage[] {
  const sums = new Map<string, { total: number; count: number }>();
  for (const row of rows) {
    for (const [metric, entry] of Object.entries(row.metric_scores ?? {})) {
      const score = typeof entry?.score === 'number' ? entry.score : null;
      if (score === null) continue;
      const acc = sums.get(metric) ?? { total: 0, count: 0 };
      acc.total += score;
      acc.count += 1;
      sums.set(metric, acc);
    }
  }
  return Array.from(sums.entries())
    .map(([metric, { total, count }]) => ({
      metric,
      average: count ? total / count : 0,
      count,
    }))
    .sort((a, b) => a.metric.localeCompare(b.metric));
}

// verdict tally → a compact "P / Pt / F" style summary for a pass.
export function verdictSummary(verdicts: Record<string, number>): string {
  const pass = verdicts.PASS ?? 0;
  const partial = verdicts.PARTIAL ?? 0;
  const fail = verdicts.FAIL ?? 0;
  return `${pass} pass · ${partial} partial · ${fail} fail`;
}

export function configNameById(configs: EvaluationConfig[], id: string | null): string {
  if (!id) return 'Deleted config';
  return configs.find((c) => c.id === id)?.name ?? 'Unknown config';
}

export function configById(
  configs: EvaluationConfig[],
  id: string | null,
): EvaluationConfig | null {
  if (!id) return null;
  return configs.find((c) => c.id === id) ?? null;
}

// Mean of a single row's metric scores (0..1), or null when it has none.
export function meanRowScore(row: EvaluationConfigResult): number | null {
  const scores = Object.values(row.metric_scores ?? {})
    .map((e) => e?.score)
    .filter((s): s is number => typeof s === 'number' && Number.isFinite(s));
  if (!scores.length) return null;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
}

export interface QuestionMatrixRow {
  evalId: string;
  question: string;
  byPass: Record<string, EvaluationConfigResult>;
}

// Pivot config-result rows into one row per question, keyed by config_run_id,
// so the per-question compare table can render a column per selected pass.
// Ordered by the question's original position in the source run.
export function buildQuestionMatrix(results: EvaluationConfigResultRow[]): QuestionMatrixRow[] {
  const byEval = new Map<string, QuestionMatrixRow & { ord: number }>();
  for (const row of results) {
    const existing = byEval.get(row.eval_id);
    if (existing) {
      existing.byPass[row.config_run_id] = row;
    } else {
      byEval.set(row.eval_id, {
        evalId: row.eval_id,
        question: row.question ?? '',
        ord: row.question_ord ?? 0,
        byPass: { [row.config_run_id]: row },
      });
    }
  }
  return Array.from(byEval.values())
    .sort((a, b) => a.ord - b.ord)
    .map(({ ord: _ord, ...rest }) => rest);
}

export interface CompareMatrixRow {
  metric: string;
  // config_run_id → mean score for that metric (null = the pass didn't run it).
  byPass: Record<string, number | null>;
}

// Build the aligned compare matrix: one row per metric (union across the
// selected passes, in the canonical metric order), each with the per-pass mean
// score. Lets the compare view render metrics as rows and configs as columns so
// scores line up for a direct read.
export function buildCompareMatrix(
  passes: EvaluationConfigRunSummary[],
  results: EvaluationConfigResult[],
): CompareMatrixRow[] {
  const rowsByPass = new Map<string, EvaluationConfigResult[]>();
  for (const row of results) {
    const list = rowsByPass.get(row.config_run_id) ?? [];
    list.push(row);
    rowsByPass.set(row.config_run_id, list);
  }

  const metricSet = new Set<string>();
  const avgByPass = new Map<string, Map<string, number>>();
  for (const pass of passes) {
    const map = new Map<string, number>();
    for (const m of averageMetricScores(rowsByPass.get(pass.config_run_id) ?? [])) {
      map.set(m.metric, m.average);
      metricSet.add(m.metric);
    }
    avgByPass.set(pass.config_run_id, map);
  }

  return orderMetricNames([...metricSet]).map((metric) => ({
    metric,
    byPass: Object.fromEntries(
      passes.map((p) => [p.config_run_id, avgByPass.get(p.config_run_id)?.get(metric) ?? null]),
    ),
  }));
}

// The max score across a compare row's passes (ignoring nulls), or null when
// no pass has a score — used to highlight the winning cell per metric.
export function bestInRow(byPass: Record<string, number | null>): number | null {
  const values = Object.values(byPass).filter((v): v is number => typeof v === 'number');
  return values.length ? Math.max(...values) : null;
}
