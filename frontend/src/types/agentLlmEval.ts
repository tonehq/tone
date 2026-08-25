// Mirrors backend `AgentLlmEvalScenario.to_dict()` +
// `_run_summary_to_dict` in core/api/v1/agent_llm_evals.py.

export type AgentLlmEvalVerdict = 'PASS' | 'PARTIAL' | 'FAIL';
export type AgentLlmEvalBatchStatus = 'completed' | 'failed' | 'running';
export type AgentLlmEvalScenarioSource = 'manual' | 'csv' | 'generated' | 'fixture';

// Tool-aware eval (Phase 2). Both shapes match the backend
// ``core.services.evals.agent_llm.tool_selection_metric`` contract 1:1 so the
// deterministic scorecard flows through without a client-side reshape.
export interface ExpectedToolCall {
  name: string;
  arguments?: Record<string, unknown>;
}

export interface ToolCallIntent {
  name: string;
  arguments: Record<string, unknown>;
}

// Execution-trace shape emitted by the executor. Single-turn today
// (``{turns: [{role: 'assistant', tool_calls: [...]}]}``); kept as an
// opaque record so a future multi-turn extension doesn't require a
// type-level breaking change on the FE.
export type AgentLlmEvalExecutionTrace = Record<string, unknown>;

export interface AgentLlmEvalScenario {
  id: string;
  organization_id: string;
  agent_id: string;
  scenario_key: string;
  scenario_ord: number;
  prompt: string;
  expected_answer: string | null;
  persona_criteria: string | null;
  instruction_criteria: string | null;
  tags: string[] | null;
  metrics_override: string[] | null;
  threshold_override: number | null;
  source: AgentLlmEvalScenarioSource;
  generation_metadata: Record<string, unknown> | null;
  expected_tools: ExpectedToolCall[] | null;
  tool_config: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ListScenariosResponse {
  items: AgentLlmEvalScenario[];
  total: number;
  page_no: number;
  page_size: number;
}

export interface ListScenariosRequest {
  page_no?: number;
  page_size?: number;
  search?: string | null;
  tags?: string[] | null;
  sort_by?: string | null;
  sort_order?: 'asc' | 'desc';
}

export interface ScenarioInput {
  scenario_key: string;
  prompt: string;
  expected_answer?: string | null;
  persona_criteria?: string | null;
  instruction_criteria?: string | null;
  tags?: string[] | null;
  metrics_override?: string[] | null;
  threshold_override?: number | null;
  scenario_ord?: number | null;
}

export interface ScenarioPatch {
  scenario_key?: string | null;
  prompt?: string | null;
  expected_answer?: string | null;
  persona_criteria?: string | null;
  instruction_criteria?: string | null;
  tags?: string[] | null;
  metrics_override?: string[] | null;
  // Sentinel: -1 clears the override so the resolver falls back to the org default.
  threshold_override?: number | null;
  scenario_ord?: number | null;
}

export interface AgentLlmEvalRunSummaryTotals {
  total: number;
  pass: number;
  partial: number;
  fail: number;
  pass_rate: number;
  partial_rate: number;
  fail_rate: number;
  duration_ms: number;
  [avgKey: string]: number | undefined;
}

export interface AgentLlmEvalRunSummary {
  run_id: string;
  agent_id: string;
  run_number: number;
  triggered_by: string;
  judge_model: string | null;
  // Answer model — the agent's LLM at the time of the run (snapshotted).
  // All rows in a run share the same value, so it collapses cleanly in the
  // grouped summary query.
  llm_model: string | null;
  llm_provider: string | null;
  status: AgentLlmEvalBatchStatus;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  summary: AgentLlmEvalRunSummaryTotals | Record<string, never>;
}

export interface AgentLlmEvalScoredScenario {
  id: string;
  scenario_key: string;
  scenario_tags: string[] | null;
  prompt: string;
  expected_answer: string | null;
  actual_answer: string | null;
  verdict: AgentLlmEvalVerdict | null;
  metric_scores: Record<string, { score?: number; reason?: string | null }> | null;
  judge_reasoning: string | null;
  judge_model: string | null;
  judge_engine: string | null;
  llm_model: string | null;
  llm_provider: string | null;
  system_prompt: string | null;
  llm_settings_snapshot: Record<string, unknown> | null;
  latency_ms: number | null;
  status: string;
  answer_error: string | null;
  judge_error: string | null;
  started_at: string | null;
  completed_at: string | null;
  // Tool-aware fields (Phase 2). ``null`` (not ``[]``) when the LLM emitted
  // no tool calls — distinguishes "no tools attempted" from an empty array.
  tools_called: ToolCallIntent[] | null;
  execution_trace: AgentLlmEvalExecutionTrace | null;
}

export interface AgentLlmEvalRunDetail {
  summary: AgentLlmEvalRunSummary;
  scenarios: AgentLlmEvalScoredScenario[];
}

export interface TriggerRunPayload {
  scenario_ids?: string[];
  tags?: string[];
  judge_model?: string | null;
}

export interface TriggerRunResponse {
  job_id: number;
  status: 'queued';
  triggered_by: string;
}

export interface GeneratedScenario {
  scenario_key: string;
  prompt: string;
  expected_answer: string | null;
  persona_criteria: string | null;
  instruction_criteria: string | null;
  tags: string[];
  confidence: number | null;
  generation_metadata: Record<string, unknown> | null;
  // Tool-aware eval (Phase 2). ``null`` for text-only scenarios so the
  // "tool" chip only shows on scenarios the generator actually pre-labeled.
  expected_tools: ExpectedToolCall[] | null;
}

export interface GenerateScenariosPayload {
  strategy?: string;
  count?: number;
  dry_run?: boolean;
  options?: Record<string, unknown> | null;
}

export interface GenerateScenariosResponse {
  strategy: string;
  dry_run: boolean;
  generated: GeneratedScenario[];
  persisted: AgentLlmEvalScenario[];
  note: string | null;
}

export interface CompareRunsPayload {
  baseline_run_id: string;
  candidate_run_id: string;
  score_drop?: number;
}

export interface CompareRunsResponse {
  baseline: { id: string; run_number: number; started_at: string | null; summary: unknown };
  candidate: { id: string; run_number: number; started_at: string | null; summary: unknown };
  score_drop_threshold: number;
  regressions: Array<Record<string, unknown>>;
  regression_count: number;
  per_scenario: Array<Record<string, unknown>>;
}
