// Mirror of the backend storage shape (``core/services/org_settings.py``).
// The org's ``eval_settings`` JSONB carries two sibling sub-objects:
//   { rag_evals: {...}, llm_evals: {...} }
// Each is independent — a change to one never affects the other, including
// its own ``auto_run_enabled`` toggle. Every field is OPTIONAL in the raw
// stored payload; a key that isn't set means "fall through to env → default"
// on the backend. The UI renders unset fields as placeholders.

export interface EvalSettings {
  rag_evals?: RagEvalOrgSettings;
  llm_evals?: LlmEvalOrgSettings;
}

export interface RagEvalOrgSettings {
  auto_run_enabled?: boolean;
  generation_model?: string;
  answer_model?: string;
  judge_model?: string;
  judge_engine?: string;
  top_k?: number;
  max_context_chars?: number;
  metric_threshold?: number;
  metrics_enabled?: string[];
  metric_thresholds?: Record<string, number>;
}

export interface LlmEvalOrgSettings {
  auto_run_enabled?: boolean;
  judge_model?: string;
  judge_engine?: string;
  metric_threshold?: number;
  metrics_enabled?: string[];
  metric_thresholds?: Record<string, number>;
}

// Back-compat alias — some callers imported the old name; keeping this
// re-export means the rename is a fully additive change on the FE side.
export type AgentLlmEvalOrgSettings = LlmEvalOrgSettings;

// DeepEval metrics meaningful for agent-LLM (Level-2) evaluation — mirrors the
// backend `_DEFAULT_AGENT_LLM_METRICS_ENABLED` tuple in `org_settings.py`.
// `bias` / `toxicity` are OK to enable here (they score the answer LLM's own
// output — no retrieval context needed).
export const AGENT_LLM_EVAL_METRIC_NAMES = [
  'correctness',
  'instruction_following',
  'persona_adherence',
  'bias',
  'toxicity',
] as const;

export type AgentLlmEvalMetricName = (typeof AGENT_LLM_EVAL_METRIC_NAMES)[number];

// DeepEval metrics that are meaningful for RAG evaluation. Kept in sync with
// the backend ``SUPPORTED_METRICS`` registry in
// ``core/services/evals/deepeval/metric_registry.py``. Intentionally excluded:
//   - persona_adherence / instruction_following — the RAG judge rejects
//     these (``AGENT_CONTEXT_METRICS`` filter in ``judge_service.py``).
//   - bias / toxicity — content-safety metrics for the answer LLM, not RAG
//     quality signals. Belong on the future Agent LLM evals settings page.
export const EVAL_METRIC_NAMES = [
  'faithfulness',
  'answer_relevancy',
  'contextual_precision',
  'contextual_recall',
  'contextual_relevancy',
  'hallucination',
  'correctness',
] as const;

export type EvalMetricName = (typeof EVAL_METRIC_NAMES)[number];

export const EVAL_JUDGE_ENGINES = ['deepeval', 'legacy'] as const;
export type EvalJudgeEngine = (typeof EVAL_JUDGE_ENGINES)[number];

// Backend catalog powering the generation / answer model dropdowns on the
// Evaluations settings page. Filtered to OpenAI + Google (Gemini) providers
// by ``core/services/evals/eval_models_service.py``.
export interface EvalModelOption {
  provider_id: string;
  provider_display_name: string;
  name: string;
  display_name: string;
}

export interface EvalModelCatalog {
  providers: { provider_id: string; display_name: string }[];
  models: EvalModelOption[];
}
