# versioning-tree-and-page

> feature: agent-llm-evals-revamp · task: versioning-tree-and-page

## Requirements
Implement the full agent-LLM evals revamp (locked design):
1. Versioned generation with human review (new version table; `pending`→`approved`; reject=delete).
2. Custom generation prompt fed to the LLM strategy, stored on the version.
3. Single-table folder **tree** (adjacency: `node_type` + `parent_id`) — fold in the existing folder table.
4. Runs tied to a version; score only approved evals.
5. New per-agent page (Manage Evals + Results tabs) mirroring the RAG UI, with version filters, replacing the in-form `LlmEvalsStep`.

**Non-goal / hard constraint:** must NOT break existing agent-LLM scenarios, runs, folders, CLI, fixtures, or the KB/RAG evals. Additive migration, no version backfill.

## Implementation Details
- See `requirements.md` §7 for the locked schema, migration, flows, endpoints, and FE structure.
- Backend: mirror the shipped RAG pattern (`eval_version.py`, `knowledge_base_routes.py` version/approve/reject routes, `EvalService` version methods) adapted to agent scope.
- Frontend: mirror `components/knowledge-base/Eval*` (VersionBar, QuestionRow, ResultsTab) into the agent-LLM page.
- Standards: `backend-standards` + `frontend-standards`.

## Acceptance Criteria
See `requirements.md` §9 (R-model, R-nonbreaking, R-generate, R-review, R-run, R-customprompt, R-tree, R-page + tests/lint).

## PR Comments — 2026-09-07

Reviewed: uncommitted agent-LLM evals revamp (backend + frontend + migration + tests) vs origin/dev.

- **[should] Migration deploy-safety** `alembic/versions/e2f8a1c4b7d3` — one-shot contract drops `agent_llm_eval_folders` + `scenarios.folder_id` in the same migration new code needs; breaks a rolling deploy (old pods read them). Conflicts with CLAUDE.md expand→migrate→contract. **User-accepted trade-off (chose drop-now in planning); NOT changed.** Safe path if revisited: split into expand (keep old table/column) + follow-up contract, or deploy with a maintenance window.
- **[fixed] Dead FE generate code** — removed `generateAgentLlmEvalScenarios` (services/agentLlmEvalService.ts) + types `GenerateScenariosPayload`/`GenerateScenariosResponse`/`GeneratedScenario` (types/agentLlmEval.ts); superseded by the versioned generate flow.
- **[fixed] Dead BE helper** — removed `_clean_optional_text` from folder_service.py (unused after dropping folder-description persistence).
- **[fixed] DRY** — extracted duplicated `_assert_agent_in_org` into shared `assert_agent_in_org(...)` in folder_service.py; folder_service + version_service now delegate.
- **[fixed] Stale comment** — scenario_service create_scenarios_bulk refresh-loop comment `folder_ref`→`parent_ref`.
- **[kept] Old route** `POST /scenarios/generate` — now UI-dead but left in place (external API consumers); its `generate_scenarios` service method is correctly reused by version_service.
- **[API contract]** Postman MCP not connected + no OpenAPI spec configured. New endpoints to add to the collection: `versions/list`, `versions/generate`, `versions/{id}/approve-all`, `reject-all`, `scenarios/{id}/approve`, `scenarios/{id}/reject`; changed contracts: `ListScenariosRequest` (+version_id, approval_status), `TriggerRunRequest` (+version_id), `GET /runs` (+version_id query).
