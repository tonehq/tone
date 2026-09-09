// Reusable, org-wide judge configs (Evaluator) + the scores from re-grading a
// frozen eval run with one (Feedback). Mirrors the backend
// EvaluationConfig / EvaluationConfigResult models.

import type { EvalMetricScore, HumanVerdict } from '@/types/eval';

export interface EvaluationConfig {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  judge_model: string;
  judge_engine: string;
  judge_prompt: string | null;
  metrics_enabled: string[];
  metric_threshold: number;
  metric_thresholds: Record<string, number>;
  is_default: boolean;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface EvaluationConfigResult {
  id: string;
  organization_id: string;
  evaluation_config_id: string | null;
  source_run_id: string;
  eval_id: string;
  config_run_id: string;
  config_run_number: number;
  triggered_by: string;
  status: string;
  verdict: string | null;
  judge_reasoning: string | null;
  metric_scores: Record<string, EvalMetricScore>;
  latency_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// The list_results read shape: a config-result row joined to its source
// question (the persisted model has no question column — the join adds it).
export interface EvaluationConfigResultRow extends EvaluationConfigResult {
  question: string;
  question_ord: number;
  // The human Accept/Reject mark on the source answer (ground truth). null =
  // unlabeled. Lets the per-question compare table show "Your call".
  human_verdict: HumanVerdict | null;
}

// One config pass against a source run — the compare/run picker unit.
export interface EvaluationConfigRunSummary {
  config_run_id: string;
  evaluation_config_id: string | null;
  config_run_number: number;
  source_run_id: string;
  judge_model: string | null;
  total: number;
  verdicts: Record<string, number>;
  average_score: number | null;
  // How often this judge's accept/reject matched the human labels on the source
  // run (0..1), or null when no answers are labeled. `labeled_count` = how many
  // of the run's answers carry a human mark.
  human_agreement: number | null;
  labeled_count: number;
  created_at: string | null;
}

export interface EvaluationConfigResultsResponse {
  runs: EvaluationConfigRunSummary[];
  results: EvaluationConfigResultRow[];
}

export interface EvaluationConfigCreatePayload {
  name: string;
  judge_model: string;
  judge_engine?: string;
  judge_prompt?: string | null;
  description?: string | null;
  metrics_enabled?: string[];
  metric_threshold?: number;
  metric_thresholds?: Record<string, number>;
  is_default?: boolean;
}

export type EvaluationConfigUpdatePayload = Partial<EvaluationConfigCreatePayload>;

export interface EvaluationConfigListResponse {
  items: EvaluationConfig[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunEvaluationConfigPayload {
  source_run_id: string;
  evaluation_config_id: string;
}
