# Agent-LLM Evals Revamp — Requirements

Revamp the agent-LLM evals (test scenarios attached to an agent) to support **versioned generation with human review**, a **single-table folder tree**, and a **dedicated RAG-style page** for managing evals and viewing results. Users can auto-generate evals (optionally with a custom prompt instead of only the agent prompt), review each generated eval, approve or reject (individually or all-at-once), and only approved evals remain. Runs are tied to a version. This mirrors the pattern the KB/RAG evals feature already shipped (`eval_versions`), adapted to the agent-scoped domain. **Existing agent-LLM eval data and flows must keep working** — the change is additive/non-breaking.

## 1. Overview

- **Route(s) / entry points:**
  - Backend: `/api/v1/agents/{agent_id}/llm-evals/*` (existing router `core/api/v1/agent_llm_evals.py`), extended with version + approve/reject routes.
  - Frontend: new per-agent page `/(dashboard)/agents/[agentId]/evaluations` (replaces the in-form `LlmEvalsStep` UI).
- **Goal:** Let users generate/regenerate evals as reviewable **versions**, approve/reject before they count, organize evals in a nested folder **tree**, and view evals + results on a dedicated page with **version filters** — without breaking existing scenarios, runs, folders, or the CLI.
- **Scope:** Backend (models, migration, services, routes, schemas) + Frontend (new page, components, API hooks, types). DB: 1 new table, additive columns on 3 tables. **NOT changing:** the KB/RAG `evals`/`eval_versions` tables and flow; the eval *run/judge* scoring engine; live agent runtime.
- **Shared / affected surfaces:** `agent_llm_eval_scenarios`, `agent_llm_eval_runs`, `agent_llm_eval_results` models; `AgentLlmScenarioService`, `folder_service`, scenario generation strategies; existing FE `LlmEvalsStep/*` (retired/migrated to the new page). Pattern reference (do not modify): `core/models/eval_version.py`, RAG routes in `knowledge_base_routes.py`, FE `components/knowledge-base/Eval*`.

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `core/models/agent_llm_eval_scenario_version.py` | **New** version parent model |
| `core/models/agent_llm_eval_scenario.py` | Add `node_type`, `parent_id`, `name`, `version_id`, `approval_status`; make `prompt` nullable + CHECK |
| `core/models/agent_llm_eval_run.py` / `agent_llm_eval_result.py` | Add `version_id` |
| `core/models/agent_llm_eval_folder.py` | Migrated into the scenarios tree (folder rows); table retired after data move |
| `alembic/versions/<rev>_agent_llm_eval_versioning_and_tree.py` | **New** migration (expand; no version backfill; one-time folder→tree move) |
| `core/services/evals/agent_llm/scenario_service.py` | Version-aware create/generate/approve/reject; tree ops |
| `core/services/evals/agent_llm/folder_service.py` | Fold into tree (node_type='folder', parent_id) or repoint to scenarios table |
| `core/services/evals/agent_llm/service.py` | Runs tied to a version; score only `approved` |
| `core/services/evals/agent_llm/scenario_generation/strategies/llm.py` | Accept custom generation prompt via `options` |
| `core/api/v1/agent_llm_evals.py` | New routes: versions list/generate(new/overwrite), approve/reject (+all), version-filtered results |
| `core/schemas/agent_llm_eval*.py` | Request/response schemas for the above |
| `frontend/src/app/(dashboard)/agents/[agentId]/evaluations/page.tsx` | **New** page (Manage Evals + Results tabs) |
| `frontend/src/components/agents/.../LlmEvalsStep/*` | Version bar, approve/reject rows, folder tree, results tab (mirror `knowledge-base/Eval*`) |
| `frontend/src/lib/api/agentLlmEvals.ts` + `frontend/src/types/agentLlmEval.ts` | New hooks + types |

## 7. Behavior & Functionality

### Data model (locked)
- **New table `agent_llm_eval_scenario_versions`** (`OrgScopedModel`): `agent_id` FK→agents (CASCADE); `version_number` int (unique per agent); `source` (`generated|manual|imported`); `status` (`generating→draft→finalized`); `generation_prompt` (Text, null — the custom prompt); `generated_by_model`, `generation_prompt_hash`; timestamps; UNIQUE `(agent_id, version_number)`.
- **`agent_llm_eval_scenarios` becomes a single-table tree** (folders + evals):
  - `node_type` str(16) NOT NULL default `'scenario'` (`folder|scenario`)
  - `parent_id` UUID self-FK (CASCADE), nullable (NULL = top level)
  - `name` str(120) null (folder label)
  - `version_id` UUID FK→versions (CASCADE), nullable (NULL = manual/no-version)
  - `approval_status` str(16) NOT NULL default `'approved'` (`pending|approved`; evals only)
  - `prompt` becomes nullable; `CHECK (node_type='folder' OR prompt IS NOT NULL)`
  - Partial unique `(agent_id, parent_id, name) WHERE node_type='folder'`
  - Partial unique `(agent_id, version_id, scenario_key) WHERE node_type='scenario'` (NULLS NOT DISTINCT)
- **`agent_llm_eval_runs` + `agent_llm_eval_results`:** add `version_id` (results snapshot `ON DELETE SET NULL`).
- **Delete rules:** delete folder → cascade children (folders + evals); delete version → cascade its eval rows (folders/manual evals untouched).

### Migration (locked)
- **Expand only, NO version backfill** — existing scenarios keep `version_id=NULL`, `node_type='scenario'`, `approval_status='approved'`.
- **One-time folder move** (unavoidable for single-table tree): existing `agent_llm_eval_folders` rows → folder nodes in `agent_llm_eval_scenarios`; repoint each scenario's `folder_id`→`parent_id`. Then retire the folder table (kept until FE cutover if safer).
- Additive/nullable columns + server defaults so old code keeps working during rollout.

### Flows (locked)
1. **Generate** (with `mode: new | overwrite`, optional `parent_id` target folder default top-level, optional `generation_prompt`): create version (`status=generating`) → generate synchronously → **insert all evals saved as `approval_status='pending'`** (`version_id`, `parent_id`) → version `→ draft`. Overwrite of an already-**run** version is refused.
2. **Review:** approve one (`pending→approved`); reject one (**DELETE row**); approve-all; reject-all (**DELETE all pending**). "Ignored ⇒ not stored" ⇒ rejected rows are deleted; final DB holds only approved.
3. **Approve-all** → version `→ finalized`.
4. **Run:** pick a version → scores only its `approval_status='approved'` evals → stamps `version_id` on run + results.
5. **Custom prompt** feeds the `llm.py` strategy via `options` (supplements/replaces the agent system prompt for generation only; stored on the version, not per-eval).

### Frontend (locked)
- **New dedicated per-agent page**, replacing the in-form `LlmEvalsStep` UI (retire the second UI — DRY). Two tabs like RAG: **Manage Evals** + **Results**.
- **Version bar** (mirror `EvalVersionBar`): version dropdown + Generate + approve-all/reject-all with icons (`CheckCheck`/`Sparkles`/`XCircle`).
- **Folder tree** navigation coexists with the version filter dropdown (folders = tree nav; version = filter).
- **Results tab** has a **version filter** (like RAG).
- Per-eval approve/reject icons on rows (mirror `EvalQuestionRow`).

- **APIs & data model:** all routes org-scoped via `require_org_member` + `_ensure_agent_in_org` (existing pattern); logic in `AgentLlmScenarioService`/services, thin routers. Endpoints (new): `POST …/llm-evals/versions/list`, `POST …/versions/generate` (`mode`,`version_id?`,`parent_id?`,`generation_prompt?`,`count`), `POST …/versions/{id}/approve-all`, `…/reject-all`, `POST …/scenarios/{id}/approve`, `…/reject`, version-filtered runs/results list.
- **Error handling:** reuse existing `_handle_scenario_error` / `_handle_folder_error` mapping; overwrite-of-run-version → 409; unknown strategy → 400.

## 8. Non-Functional Requirements

- **Standards compliance:** follow `backend-standards` (thin routers, service layer, org-scoping, safe additive Alembic migration, `logger.exception` on except) and `frontend-standards` (shared components — `CustomButton`, `SelectInput`, `CustomTab`, `CustomTable`; TanStack Query hooks in `@/lib/api`; one component per file; no `any`).
- **Non-breaking:** existing scenarios/runs/folders/CLI/fixtures must keep working; version-less scenarios still listable and runnable; no change to KB/RAG evals.
- **Security:** every query org-scoped (no IDOR); overwrite refused on run versions.
- **Observability:** context-tagged logs on generate/approve/reject; full tracebacks on except.

## 9. Acceptance Criteria

- [ ] R-model: new version table + additive columns exist; migration applies cleanly and is reversible; existing rows valid with `version_id=NULL`.
- [ ] R-nonbreaking: existing agent-LLM scenarios, runs, folders, and CLI seed continue to work unchanged; KB/RAG evals untouched.
- [ ] R-generate: generate creates a draft version and saves all evals as `pending`; overwrite of a run version is refused.
- [ ] R-review: approve keeps (→approved); reject deletes; approve-all finalizes; reject-all deletes all pending; DB never retains rejected evals.
- [ ] R-run: a run is tied to a chosen version and scores only its approved evals; run + results carry `version_id`.
- [ ] R-customprompt: a user-supplied generation prompt is used by the LLM strategy and stored on the version.
- [ ] R-tree: folders + evals live in one table as an adjacency tree; nesting works; folder delete cascades.
- [ ] R-page: new per-agent page shows Manage Evals + Results tabs with version filter + approve/reject icons; old in-form step retired with no data loss.
- [ ] Tests added (service + route); lint + typecheck pass.

## 10. Out of Scope

- KB/RAG `evals` / `eval_versions` tables and UI (only the *rename* of `generation_instructions`→`generation_prompt` there is a **separate**, later cleanup — not in this feature).
- Changing the judge/scoring engine or live agent runtime.
- Async/background generation (agent-LLM generation stays synchronous).
- Tool/MCP eval scoring (existing v2 forward-compat columns untouched).
