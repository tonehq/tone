# auto-generate-background-job

> feature: agent-llm-evals-revamp · task: auto-generate-background-job

## Requirements

Move the agent-LLM-eval **"Auto-generate scenarios"** flow from a synchronous HTTP request to a
**Procrastinate background job**, mirroring the existing "Run Eval" background pattern.

- **Context / correction:** "Run Eval" (`POST /agents/{id}/llm-evals/runs`) is **already** backgrounded
  (Procrastinate `agent_eval` queue, `pending → running → completed/failed`, FE polls). **No change is
  needed for Run Eval.** Only **auto-generate** (`POST /agents/{id}/llm-evals/versions/generate`) is
  synchronous today and is the sole target of this task.
- **Why:** LLM scenario generation makes a multi-second `chat_complete` call inline on the request
  thread, risking gateway/proxy timeouts and blocking a threadpool worker.
- **Progress indication:** once generation is triggered, the UI must show a **"Generating…" indication**
  on the version until the job completes (success → drafts appear; failure → visible failure state).
- **Non-goal / safety:** must **not break existing functionality** — the synchronous `generate()` code
  path stays usable for CLI/tests; scenario approve/reject, runs, results, versions bar all keep working.

## Implementation Details

Mirror the Run-Eval two-phase pattern (`begin_pending_run` → enqueue sync → worker flips lifecycle).

**Backend**
- Version model `agent_llm_eval_scenario_versions.status` (free-text String16, today `draft`/`finalized`)
  gains lifecycle states **`generating`** and **`failed`**; add nullable **`generation_error`** (Text)
  column for the user-safe failure reason (mirrors `agent_llm_eval_runs.error`). Alembic migration =
  additive-nullable + guarded + real `downgrade` (expand-only, deploy-safe).
- `AgentLlmEvalVersionService`: split `generate()` into `begin_generation()` (SYNC: pre-flight validate +
  create/resolve version row as `generating`, commit) and `run_generation()` (worker: atomic
  `mark_generating→running` idempotency guard, call `generate_scenarios(dry_run=False)`, stamp
  hash/model, flip to `draft`, or on failure flip to `failed` + `generation_error`). Keep `generate()` as
  a thin sync wrapper that calls both in sequence so CLI/tests are unchanged (entry-point-agnostic reuse).
- `ingestion_queue.py`: add `@app.task(name="generate_agent_llm_eval_version", queue="agent_eval",
  pass_context=True)` (mirror `run_agent_llm_eval`: own session, swallow+log scoring-phase failures after
  flipping the version to `failed`, retry transient pre-generation failures) and
  `enqueue_generate_agent_llm_eval_version_sync(...)` via `_defer_via_ephemeral_app`.
- Route `generate_llm_eval_version`: same path; pre-flight + `begin_generation` (version→`generating`) →
  `enqueue_..._sync` → on enqueue failure flip version to `failed` + 503 → return **202** with
  `{version_id, status: "generating"}` (was 201 `{version, scenarios}`). Org-scoped throughout;
  `org_id` forwarded to the worker.

**Frontend** (feature already partly pre-wired)
- `useAgentLlmEvalVersions` already polls (`refetchInterval` 4s) while any version `status === 'generating'`
  and the generate mutation already invalidates the versions key — reuse as-is.
- Version status type adds `'failed'` (and a `generation_error?` field); a `VersionStatusChip`
  (`Loader2 animate-spin` for generating, error chip for failed) mirrors `RunStatusChip`, rendered in
  `AgentEvalVersionBar`.
- `GenerateScenariosModal`: on 202 success, close and show a "Generation started" toast (not "review the
  drafts below"); disable approve-all/reject-all/run on a `generating` version.

## Acceptance Criteria

- [ ] Clicking Auto-generate returns immediately (202); the version appears in `generating` and the UI
      shows a live "Generating…" indicator that clears when the job finishes.
- [ ] On worker success the version flips to `draft` with its pending scenarios; the drafts appear via the
      existing versions/scenarios poll+invalidation (no manual refresh).
- [ ] On worker failure the version shows a visible failed state with a user-safe reason; no phantom
      stuck-`generating` version.
- [ ] Procrastinate replay/retry is idempotent (no duplicate scenarios, terminal states are no-ops).
- [ ] Overwrite mode does not destroy the previous drafts if generation fails.
- [ ] Existing Run-Eval, approve/reject, results, and the synchronous `generate()` path are unaffected.
- [ ] Backend tests (route 202, worker success/failure/replay, overwrite-safety, sync-generate regression)
      and FE typecheck/lint/build are green.
