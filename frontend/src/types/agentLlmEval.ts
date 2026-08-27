// Mirrors backend `AgentLlmEvalScenario.to_dict()` +
// `_run_summary_to_dict` in core/api/v1/agent_llm_evals.py.

export type AgentLlmEvalVerdict = 'PASS' | 'PARTIAL' | 'FAIL';
// ``pending`` = router inserted the runs-table row but the worker hasn't
// picked up the Procrastinate job yet. ``running`` = worker started
// scoring. Terminal states are ``completed`` / ``failed``. The UI polls
// while any row is non-terminal (see ``useAgentLlmEvalRuns``).
export type AgentLlmEvalBatchStatus = 'pending' | 'running' | 'completed' | 'failed';
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
  // FK to first-class folder row. Every scenario always belongs to a real
  // folder; the backend seeds a "Default" folder on agent-create so
  // ``folder_id`` is never null.
  folder_id: string;
  // Convenience display name (JOINed from the folder row) — read-only. The
  // backend populates it so the table / drawer don't need a second query.
  folder: string | null;
  metrics_override: string[] | null;
  threshold_override: number | null;
  source: AgentLlmEvalScenarioSource;
  generation_metadata: Record<string, unknown> | null;
  expected_tools: ExpectedToolCall[] | null;
  tool_config: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

// First-class folder row + its scenario count.
export interface AgentLlmEvalFolder {
  id: string;
  agent_id: string;
  name: string;
  description: string | null;
  count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ListFoldersResponse {
  items: AgentLlmEvalFolder[];
}

export interface CreateFolderPayload {
  name: string;
  description?: string | null;
}

// Backend echoes the created folder row on ``POST /folders``. Uses a
// type alias (not an empty ``extends`` interface) because
// ``@typescript-eslint/no-empty-object-type`` correctly flags the
// no-op subtype as equivalent to its supertype.
export type CreateFolderResponse = AgentLlmEvalFolder;

export interface RenameFolderPayload {
  folder_id: string;
  new_name: string;
}

// Backend echoes the renamed folder row on ``POST /folders/rename``.
// Type alias for the same reason as ``CreateFolderResponse``.
export type RenameFolderResponse = AgentLlmEvalFolder;

export interface DeleteFolderPayload {
  folder_id: string;
}

// ``scenarios_deleted`` is the number of scenarios removed by the CASCADE.
// ``results_preserved`` is the count of past-run rows still tagged with
// this folder's name — kept intact so run history stays readable. The FE
// uses both in the confirmation impact + success toast.
export interface DeleteFolderResponse {
  folder_id: string;
  scenarios_deleted: number;
  results_preserved: number;
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
  // Exact folder filter by FK; null/undefined skips.
  folder_id?: string | null;
  // Exact-match filter on ``AgentLlmEvalScenario.source``. Whitelisted at
  // the router (Pydantic regex); non-whitelisted values are rejected.
  source?: AgentLlmEvalScenarioSource | null;
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
  // FK to first-class folder row. When omitted, the backend resolves the
  // agent's Default folder.
  folder_id?: string | null;
  metrics_override?: string[] | null;
  threshold_override?: number | null;
  scenario_ord?: number | null;
}

// Bulk-create body. ``source`` is optional client attribution — defaults
// to ``'manual'`` at the backend. The Auto-generate preview flow sends
// ``'generated'`` so the scenarios-table source badge reflects reality.
// Whitelisted server-side to ``manual`` | ``generated`` — ``csv`` /
// ``fixture`` stay owned by their respective server-side flows.
export interface BulkCreateScenariosPayload {
  scenarios: ScenarioInput[];
  source?: 'manual' | 'generated';
}

// Bulk-delete body. Ids not belonging to the caller's (agent, org) are
// silently skipped server-side; the response's ``deleted`` count is the
// number of rows actually removed (may be less than ``scenario_ids.length``
// if the UI cache was stale).
export interface BulkDeleteScenariosPayload {
  scenario_ids: string[];
}

export interface BulkDeleteScenariosResponse {
  deleted: number;
  requested: number;
}

export interface ScenarioPatch {
  scenario_key?: string | null;
  prompt?: string | null;
  expected_answer?: string | null;
  persona_criteria?: string | null;
  instruction_criteria?: string | null;
  tags?: string[] | null;
  // Move to a different folder. Every scenario must belong to a real
  // folder — there is no way to clear it.
  folder_id?: string | null;
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
  // Known at trigger time — the FE uses it to render "Scoring N of M"
  // progress while ``status`` is non-terminal. ``0`` for historical
  // backfilled runs where the original selection size wasn't recorded.
  total_scenarios: number;
  // Number of ``agent_llm_eval_results`` rows already written for this run.
  // Derived by the backend's LEFT JOIN so it stays fresh without a write
  // from the worker per scored scenario.
  scored_count: number;
  // Snapshot of the trigger filter ({scenario_ids, tags, folder_id, folder_ids}).
  // Loose typing — the FE doesn't unpack it in v1; kept for a future
  // "re-run this exact selection" affordance.
  filter_snapshot: Record<string, unknown> | null;
}

export interface AgentLlmEvalScoredScenario {
  id: string;
  scenario_key: string;
  scenario_tags: string[] | null;
  // Snapshot of the scenario's folder NAME at run time (null when the
  // scenario had no folder at scoring time — legacy history rows only;
  // new scenarios always belong to a folder).
  folder: string | null;
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

export interface ListRunsRequest {
  page_no?: number;
  page_size?: number;
}

export interface ListRunsResponse {
  items: AgentLlmEvalRunSummary[];
  total: number;
  // Echo-back of the requested paging so a client can trust the response
  // without tracking it separately. ``null`` means "no paging requested"
  // (backend returned every run — preserved for backward-compat callers).
  page_no: number | null;
  page_size: number | null;
}

export interface TriggerRunPayload {
  scenario_ids?: string[];
  tags?: string[];
  // Restrict the run to one folder (FK id).
  folder_id?: string | null;
  // Multi-select variant of `folder_id` — matches ANY of the folder ids
  // in the list. When both `folder_id` and `folder_ids` are provided the
  // backend uses `folder_ids` and ignores `folder_id`.
  folder_ids?: string[];
  judge_model?: string | null;
}

export interface TriggerRunResponse {
  job_id: number;
  // Router now inserts a pending row in ``agent_llm_eval_runs`` before
  // enqueue and returns its id + status alongside the Procrastinate job
  // id. The FE uses ``run_id`` to reconcile the just-triggered row on
  // the next runs-list fetch; ``status`` is always ``'pending'`` on the
  // synchronous response.
  run_id: string;
  status: AgentLlmEvalBatchStatus;
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
  // When set, every persisted (non-dry-run) scenario lands in this folder.
  folder_id?: string | null;
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
