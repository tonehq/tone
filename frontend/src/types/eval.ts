// Mirrors backend `_eval_run_summary_to_dict` + `_result_row_to_dict`
// (core/services/evals/eval_service.py, core/api/v1/knowledge_base_routes.py).
//
// One "eval batch" (`run_id`) scores every question of an upload against a
// specific ingestion pipeline recipe (`ingestion_run_id`). A batch of 50
// questions → 50 rows in `eval_results` all sharing the same `run_id`.

export type EvalVerdict = 'PASS' | 'PARTIAL' | 'FAIL';
export type EvalBatchStatus = 'completed' | 'failed';

// Human acceptance mark on a frozen answer (ground truth). Single source for the
// literal union — mirrors the backend HUMAN_ACCEPT / HUMAN_REJECT constants.
// Nullable (`HumanVerdict | null`) at each use site, where null = unlabeled.
export type HumanVerdict = 'accept' | 'reject';

// A question is 'pending' (generated, awaiting review) or 'approved' (kept —
// scored on run). Rejected questions are deleted, so there is no 'rejected'.
export type EvalApprovalStatus = 'pending' | 'approved';
export type EvalVersionStatus = 'generating' | 'draft' | 'finalized';
export type EvalVersionSource = 'generated' | 'manual' | 'imported';

// One version of an upload's eval question set. Mirrors backend
// EvalVersion.to_dict + the counts/has_results added by EvalService.list_versions.
export interface EvalVersion {
  id: string;
  organization_id: string;
  upload_id: string;
  knowledge_base_id: string;
  version_number: number;
  source: EvalVersionSource;
  status: EvalVersionStatus;
  generation_instructions: string | null;
  generated_by_model: string | null;
  generation_prompt_hash: string | null;
  counts: { total: number; approved: number; pending: number };
  // True once a batch has scored this version — overwrite is then blocked.
  has_results: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface EvalVersionsResponse {
  items: EvalVersion[];
}

export interface EvalRunSummaryTotals {
  total: number;
  pass: number;
  partial: number;
  fail: number;
  pass_rate: number;
  partial_rate: number;
  fail_rate: number;
  retrieval_hit_rate: number;
  total_questions: number;
  duration_ms: number;
}

export interface EvalRunSummary {
  run_id: string;
  upload_id: string;
  ingestion_run_id: string | null;
  eval_version_id: string | null;
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

// One DeepEval metric's score inside `metric_scores`. Keyed by the metric's
// stable snake_case name (e.g. 'faithfulness'). `verdict` is lowercase
// (pass/partial/fail), distinct from the uppercase batch-level EvalVerdict.
export interface EvalMetricScore {
  score: number;
  verdict: string;
  reason: string | null;
}

export interface EvalJudgeResult {
  verdict: EvalVerdict;
  reasoning: string | null;
  // Full DeepEval scorecard — one entry per enabled metric. Empty for
  // legacy-judge rows. Keys drive the per-metric columns in the results table.
  metric_scores: Record<string, EvalMetricScore>;
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
  // Human acceptance label on this frozen answer (ground truth). null = unlabeled.
  human_verdict: HumanVerdict | null;
}

// Payload for POST /eval-runs/{runId}/label — set/clear the human mark on one
// scored answer. verdict=null clears it.
export interface SetHumanVerdictPayload {
  eval_id: string;
  verdict: HumanVerdict | null;
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
  eval_version_id: string | null;
  external_id: string;
  question_ord: number;
  question: string;
  expected_answer: string;
  expected_source_snippet: string | null;
  category: string | null;
  approval_status: EvalApprovalStatus;
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
  // Which version to score; omit to let the backend pick the latest approved.
  eval_version_id?: string | null;
}

// Payload for POST /eval-versions/generate — generate into a new version or
// overwrite an existing (un-run) one, with an optional custom prompt. Questions
// are drafted from the uploaded document (not any ingestion run's chunks).
export interface GenerateEvalVersionPayload {
  mode: 'new' | 'overwrite';
  version_id?: string | null;
  instructions?: string | null;
}

export interface GenerateEvalVersionResponse {
  upload_id: string;
  job_id: number;
  status: 'queued';
}

export interface TriggerEvalRunResponse {
  upload_id: string;
  ingestion_run_id: string;
  job_id: number;
  status: 'queued';
}
