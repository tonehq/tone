// Mirrors backend `_eval_run_summary_to_dict` + `_result_row_to_dict`
// (core/services/evals/eval_service.py, core/api/v1/knowledge_base_routes.py).
//
// One "eval batch" (`run_id`) scores every question of an upload against a
// specific ingestion pipeline recipe (`ingestion_run_id`). A batch of 50
// questions → 50 rows in `eval_results` all sharing the same `run_id`.

export type EvalVerdict = 'PASS' | 'PARTIAL' | 'FAIL';
export type EvalBatchStatus = 'completed' | 'failed';

export interface EvalRunSummaryTotals {
  total: number;
  pass: number;
  partial: number;
  fail: number;
  pass_rate: number;
  partial_rate: number;
  fail_rate: number;
  retrieval_hit_rate: number;
  avg_correctness: number;
  avg_groundedness: number;
  avg_relevance: number;
  total_questions: number;
  duration_ms: number;
}

export interface EvalRunSummary {
  run_id: string;
  upload_id: string;
  ingestion_run_id: string | null;
  run_number: number;
  triggered_by: string;
  top_k: number;
  answer_model: string | null;
  judge_model: string | null;
  status: EvalBatchStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  summary: EvalRunSummaryTotals | Record<string, never>;
}

export interface EvalRetrievedChunk {
  text?: string;
  score?: number;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface EvalJudgeResult {
  verdict: EvalVerdict;
  correctness: number;
  groundedness: number;
  relevance: number;
  reasoning: string | null;
}

// One scored question inside a batch.
export interface EvalScoredQuestion {
  id: string;
  eval_id: string;
  category: string;
  question: string;
  expected_answer: string;
  expected_source_snippet: string;
  retrieval_hit: boolean;
  retrieved_chunks: EvalRetrievedChunk[];
  actual_answer: string;
  judge: EvalJudgeResult;
  latency_ms: number | null;
  retrieval_error: string | null;
  answer_error: string | null;
  status: string;
}

export interface EvalRunDetail {
  summary: EvalRunSummary;
  questions: EvalScoredQuestion[];
}

export interface EvalSummaryByIngestionResponse {
  // Keyed by ingestion_run_id. Missing key ⇒ no eval batch has scored that
  // ingestion run.
  items: Record<string, EvalRunSummary>;
}
