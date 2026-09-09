# RAG Evaluation Config — Requirements

<!-- Populated from the brainstorm session (manual mode — no ClickUp task). Source of truth for the plan.
Section order/numbering preserved. UI sections kept (this feature has a KB tab + compare view). -->

This feature lets users **re-grade an existing RAG eval result** with different **judge configurations** — a different judge model, a custom judge prompt, and different metric parameters — and **compare the resulting scores** side by side. Today the judge setup is a single per-org global setting (`Settings → Evaluations`) and judge prompts are fixed on-disk files, so a user cannot vary the judge per-run or compare configs. This feature introduces reusable, org-wide **evaluation configs** and a **config-results** store so the same frozen answers can be scored by many configs and compared. It is a LangSmith-style *Evaluator → Feedback* model: the answered dataset is the fixed source, the config is the controlled variable, and each run produces a comparable result. Target users are power users tuning/calibrating their RAG judge.

## 1. Overview

- **Route(s) / entry points:**
  - New KB tab: `frontend/src/app/(dashboard)/knowledge-base/[id]/` → **"Evaluation Config"** tab (sits next to Documents / Ingestion Runs / Manage Evals / Results).
  - New backend endpoints under `/api/v1` for config CRUD, running a config against a source eval run, and listing/comparing config results.
- **Goal:** Let users test the judge with different models + prompts + metric params against a fixed eval result set, find the judge setup they trust, and set it as the default used everywhere.
- **Scope:** Backend (2 new tables + service + routes + background job) and frontend (new tab + compare view). Reuses the existing judge stack (DeepEval engine, metric registry), the existing `eval_results` runs as the frozen source, and `evals` questions. **Not changing:** the existing single-run eval flow, `eval_results` schema, ingestion/retrieval pipeline, or the existing per-org `eval_settings` (it remains the global default).
- **Shared / affected surfaces:** existing KB detail page tab bar; existing DeepEval judge services (`core/services/evals/deepeval/`), `judge_factory`, `metric_registry`; org `eval_settings` (read as fallback defaults when creating a config).

## 2. Involved Files

| File | Responsibility |
|------|----------------|
| `core/models/evaluation_config.py` | NEW — `EvaluationConfig` model (org-wide reusable judge recipe) |
| `core/models/evaluation_config_result.py` | NEW — `EvaluationConfigResult` model (scores per config per source run) |
| `core/services/evals/evaluation_config_service.py` | NEW — CRUD + orchestration (run a config against a source run, reusing DeepEval judge) |
| `core/api/v1/…` (eval config routes) | NEW — config CRUD, run, list/compare endpoints (thin handlers) |
| `core/services/ingestion_queue.py` | EXTEND — new Procrastinate task on the `eval` queue to run a config-grading pass in the background |
| `core/services/evals/deepeval/*`, `judge_factory.py`, `metric_registry.py` | REUSE — judge engine, metrics, scorecard (custom prompt threaded through) |
| `core/services/evals/prompt_loader.py` | REUSE/EXTEND — default prompt fallback when a config has no custom prompt |
| Alembic migration | NEW — create the two tables + indexes |
| `frontend/src/app/(dashboard)/knowledge-base/[id]/…` | EXTEND — add "Evaluation Config" tab |
| `frontend/src/components/knowledge-base/EvaluationConfig*.tsx` | NEW — config list/editor, run trigger, 3-up compare view + prompt modal |
| `frontend/src/services/…`, `frontend/src/types/…` | NEW — API hooks + types for configs and config results |

## 3. Layout & Structure   *(UI)*

- **New KB tab "Evaluation Config"** inside the KB detail page, alongside the existing eval tabs.
- **Config list/editor:** create/edit an org-wide config (name, judge model, judge engine, custom prompt, metrics enabled, per-metric thresholds, default threshold, `is_default`).
- **Run panel:** pick a **source eval run** (an existing `eval_results` run) + a config → trigger a background grading pass.
- **Compare view:** up to **3 configs side by side** for the same source run, each column showing judge model + metrics + verdict/score summary; **the prompt is hidden**, click → **modal** shows the full prompt.
- **Responsive:** compare columns stack / horizontally scroll on narrow screens.

## 4. Content & Copy   *(UI)*

- Tab label: **"Evaluation Config"**.
- Config editor labels: Name, Description, Judge Model, Judge Engine, Judge Prompt (with "leave blank to use default"), Metrics, Thresholds, Default threshold, "Set as default".
- Prompt-missing-placeholder validation error: e.g. *"Prompt must include the {{question}}, {{answer}} and {{context}} placeholders."* (exact tokens confirmed against the existing prompt files during planning.)
- Empty states: "No evaluation configs yet — create one to start comparing judges." / "No results yet — run a config against a source eval run."

## 5. Theming & Colors   *(UI)*

- Token-driven via existing MUI theme + shared components (`CustomButton`, `CustomModal`, `CustomTable`, `SelectInput`, `TextInput`). Light & dark parity, AA contrast — inherit from existing eval tabs.

## 6. Motion & Animation   *(UI)*

- Match existing KB eval tabs (no bespoke motion required). Modal open/close uses shared `CustomModal` defaults.

## 7. Behavior & Functionality

- **Validation:**
  - Config name required, unique per org. Judge model required. Metrics-enabled must be a subset of the metric registry's `SUPPORTED_METRICS`. Thresholds in (0, 1]. Custom prompt (when provided) must contain the required placeholders so the judge always receives question/answer/context.
  - Run requires: a valid source eval run with scored answers, and a config.
- **Primary action(s):**
  - **Create/edit/delete config** (org-scoped, admin/owner guard).
  - **Run config → source run:** enqueues a background Procrastinate job on the `eval` queue; the job loads the source run's frozen answers (`actual_answer`, `retrieved_chunks`) from `eval_results`, re-judges each question via the DeepEval engine using the config's model + prompt + metrics, and writes `evaluation_config_result` rows (all sharing a `config_run_id`). Returns 202.
  - **Compare:** fetch up to 3 config-result sets for the same source run.
  - **Set default:** mark one config `is_default` (the "use everywhere" winner).
- **State & data:** results are read via list endpoints; each result row is tagged with `evaluation_config_id`, `source_run_id`, `config_run_id`.
- **APIs & data model:**
  - **Table `evaluation_configs`** (`OrgScopedModel`): `name`, `description?`, `judge_model`, `judge_engine`, `judge_prompt?` (null = default), `metrics_enabled` JSONB, `metric_thresholds` JSONB, `metric_threshold` float, `is_default` bool.
  - **Table `evaluation_config_results`** (`OrgScopedModel`): `evaluation_config_id` FK, `source_run_id` UUID (the `eval_results.run_id`), `eval_id` FK, `config_run_id` UUID, `config_run_number` int, `verdict`, `metric_scores` JSONB, `judge_reasoning?`, `latency_ms?`, `status`, `started_at`, `completed_at`. **NOTE:** this is ~90% identical to `EvalResult` — the reuse-vs-new-table decision (add config columns to `eval_results` vs. a standalone table) was decided as **standalone table** during brainstorm; re-confirm in planning against the repo DRY doctrine.
  - Multi-tenancy: every query org-scoped; routes use `require_admin_or_owner` for writes.
- **Error handling:** typed service errors mapped to HTTP (reuse the eval error → HTTP mapping pattern). Judge failures are fail-soft per metric (existing DeepEval `runner` behavior). Every `except` logs a full traceback.

## 8. Non-Functional Requirements

- **Standards compliance:** logic in a `BaseService`, thin routers, reuse existing judge/metric/prompt building blocks (no duplicated judge loop). Lint/typecheck/tests pass.
- **Performance:** grading N questions is minutes-long → always background (Procrastinate `eval` queue), never inline in the request.
- **Security:** AES-encrypted provider keys used via the existing `ToneDeepEvalLLM` adapter; no keys logged; org-scoping + RBAC on every route.
- **Observability:** `[eval-config]`-tagged logs; correlate by `config_run_id`; `logger.exception` on failures.

## 9. Acceptance Criteria

- [ ] R(config-crud): User can create/edit/delete an org-wide evaluation config (name, judge model, engine, custom prompt, metrics, thresholds, default). Writes are admin/owner + org-scoped.
- [ ] R(custom-prompt): A custom judge prompt can be saved; prompts missing the required placeholders are rejected with a clear error; blank prompt falls back to the default on-disk prompt.
- [ ] R(run): Running a config against a source eval run enqueues a background job, reuses the frozen answers (no re-retrieval/re-answer), re-judges via DeepEval, and writes `evaluation_config_result` rows tagged with config + source + `config_run_id`.
- [ ] R(compare): The KB "Evaluation Config" tab compares up to 3 configs for the same source run, showing model + metrics + scores; prompt hidden behind a modal.
- [ ] R(default): A config can be marked default and is surfaced as the recommended judge.
- [ ] Tests added (service + route + regression for the placeholder validation); lint + typecheck pass.

## 10. Out of Scope

- Re-running the RAG retrieval/answer pipeline (only re-judging frozen answers).
- Wiring `is_default` config into the *automatic* post-ingestion eval run (may be a follow-up task).
- Human-correction few-shot calibration (LangSmith feature) — future.
- Cross-KB/global dataset management beyond the existing per-upload eval versions.
- Migrating the existing per-org `eval_settings` UI out of Settings (it stays as the global default).
