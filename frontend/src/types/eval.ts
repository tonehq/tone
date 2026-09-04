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
  // Ingestion run ids whose eval batch is currently queued or running (no
  // summary row exists yet). Drives the per-row "Evals" loading spinner.
  in_flight_ingestion_run_ids: string[];
}

// One question row in the `evals` table. Mirrors the payload built by
// `_eval_question_to_payload` in core/api/v1/knowledge_base_routes.py.
export interface EvalQuestion {
  id: string;
  upload_id: string;
  knowledge_base_id: string;
  external_id: string;
  question_ord: number;
  question: string;
  expected_answer: string;
  expected_source_snippet: string | null;
  category: string | null;
  // 'manual' for user-authored rows; model name (e.g. 'gpt-4o') for
  // LLM-generated; benchmark source-key (e.g. 'hotpotqa-mini') for imports.
  generated_by_model: string | null;
  generation_prompt_hash: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface EvalQuestionsResponse {
  items: EvalQuestion[];
}

// Payload for POST /evals/manual — the user's typed Q&A. `external_id` is
// optional (the backend mints `manual-<uuid>` when absent).
export interface ManualQuestionInput {
  question: string;
  expected_answer: string;
  expected_source_snippet?: string | null;
  category?: string | null;
  external_id?: string | null;
}

// Payload for PUT /evals/questions/{id} — all optional; explicit null on
// the optional fields clears them.
export interface UpdateQuestionPatch {
  question?: string;
  expected_answer?: string;
  expected_source_snippet?: string | null;
  category?: string | null;
}

export interface EvalSetSummary {
  upload_id: string;
  organization_id: string;
  knowledge_base_id: string | null;
  question_count: number;
  generated_by_model: string | null;
  generation_prompt_hash: string | null;
}

// Per-run overrides (top_k, answer_model, judge_model) are deliberately
// omitted — the backend endpoint does not accept them today. Add them here
// only when the shared Procrastinate task grows the corresponding params.
export interface TriggerEvalRunPayload {
  ingestion_run_id?: string | null;
}

export interface TriggerEvalRunResponse {
  upload_id: string;
  ingestion_run_id: string;
  job_id: number;
  status: 'queued';
}
