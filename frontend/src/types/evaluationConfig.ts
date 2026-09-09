// Reusable, org-wide judge configs (Evaluator) + the scores from re-grading a
// frozen eval run with one (Feedback). Mirrors the backend
// EvaluationConfig / EvaluationConfigResult models.

import type { EvalMetricScore } from '@/types/eval';

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

// One config pass against a source run — the compare/run picker unit.
export interface EvaluationConfigRunSummary {
  config_run_id: string;
  evaluation_config_id: string | null;
  config_run_number: number;
  source_run_id: string;
  total: number;
  verdicts: Record<string, number>;
  created_at: string | null;
}

export interface EvaluationConfigResultsResponse {
  runs: EvaluationConfigRunSummary[];
  results: EvaluationConfigResult[];
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
