# evaluation-config-e2e

> feature: rag-evaluation-config · task: evaluation-config-e2e

## Requirements

Build the RAG Evaluation Config feature end-to-end (backend + frontend), per
`../requirements.md`. In short: let users define reusable, org-wide **evaluation
configs** (judge model + engine + custom prompt + metrics + thresholds), **run** a
config against an existing frozen `eval_results` run in the background (re-judge
only — no re-retrieval/re-answer), persist the scores in a new
`evaluation_config_results` table tagged with the config + source run, and **compare
up to 3 configs side by side** in a new KB "Evaluation Config" tab (prompt behind a
modal). One config can be marked default.

- **In scope:** 2 new models + Alembic migration; `EvaluationConfigService` (CRUD +
  run orchestration reusing the DeepEval judge stack); Procrastinate background task
  on the `eval` queue; thin org-scoped/RBAC routes; frontend tab, config editor, run
  panel, 3-up compare view + prompt modal, API hooks + types.
- **Non-goals:** re-running retrieval/answer; auto-wiring default config into the
  post-ingestion auto-run (possible follow-up); few-shot human-correction calibration;
  moving the existing per-org `eval_settings` UI. See §10 of requirements.md.

## Implementation Details

- **Reuse (do not duplicate):** DeepEval judge (`core/services/evals/deepeval/*`),
  `judge_factory`, `metric_registry.SUPPORTED_METRICS`, `prompt_loader` (default
  prompt fallback), the eval error→HTTP mapping, org `eval_settings` resolver (as
  create-time defaults), shared FE components (`CustomButton`, `CustomModal`,
  `CustomTable`, `SelectInput`, `TextInput`).
- **Source of answers:** an `eval_results` run identified by its `run_id`
  (`actual_answer`, `retrieved_chunks`).
- **Data model / tables / edge cases / API shapes:** to be finalized in the plan
  (§7 of requirements.md is the reference). Re-confirm the standalone-table vs.
  reuse-`EvalResult` decision against the repo DRY doctrine during planning.
- **Background:** grading N questions is minutes-long → Procrastinate `eval` queue,
  202 on trigger; correlate logs by `config_run_id`.

## Acceptance Criteria

- [ ] Maps to requirements.md §9 acceptance criteria (config CRUD, custom-prompt
      validation + default fallback, background run reusing frozen answers, 3-up
      compare, set-default), plus tests + lint/typecheck passing.
