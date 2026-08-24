# Plan — Auto-generate LLM Eval Scenarios (v1)

## Goal

Wire a working `llm` scenario-generation strategy so clicking **Auto-generate** in the LLM Evals tab actually produces scenarios (instead of the current `noop` placeholder). Uses the org's configured judge model as the generator. **Persist directly** (no dry-run), `source='generated'`. Zero change to any other flow.

## What's already scaffolded (reuse — don't rebuild)

- `ScenarioGenerator` ABC + `GeneratedScenario` dataclass (`scenario_generation/base.py`)
- Factory registry `get_scenario_generator(strategy)` (`scenario_generation/__init__.py`)
- `NoopGenerator` (`scenario_generation/strategies/noop.py`) — kept as-is for tests & compat
- `AgentLlmScenarioService.generate_scenarios(...)` — already dispatches to the strategy, handles persistence via `create_scenarios_bulk(source='generated')`, returns `GeneratedBatch`
- `AgentLlmEvalService._resolve_judge_key(...)` — already handles agent-key-reuse-when-same-provider and org key lookup + missing-key errors
- `load_agent_llm_eval_settings_for_org(...)` — resolves `llm_evals.judge_model` (DB → env → default)
- `AgentConfigLoader.load_for_eval(...)` — walks agent → published_config → returns the system prompt
- `chat_complete(model, api_key, messages, json_mode=True, ...)` — provider-agnostic LLM call
- Route: `POST /agents/{id}/llm-evals/scenarios/generate` — takes `{strategy, count, dry_run, options}` and calls `generate_scenarios`

Everything above stays untouched. This plan adds ONE new strategy + registers it + updates the FE dropdown.

---

## Phase 1 — New strategy: `LlmGenerator`

**File:** `core/services/evals/agent_llm/scenario_generation/strategies/llm.py` (new)

### Responsibilities (single class, one method)

```python
class LlmGenerator(ScenarioGenerator):
    strategy_key = "llm"

    def generate(self, db, agent_id, *, count=10, options=None) -> list[GeneratedScenario]:
        # 1. Load agent's published config → system prompt (raises AgentLlmEvalConfigError
        #    if unpublished / no prompt — surface it verbatim, same error class the
        #    Run Eval flow already uses).
        # 2. Resolve judge model + engine via load_agent_llm_eval_settings_for_org(db, org_id).
        # 3. Resolve judge API key via AgentLlmEvalService._resolve_judge_key(...) — the
        #    exact same helper the eval runner uses (agent-key reuse when providers match,
        #    else ProviderKeyService.get_key, else AgentLlmEvalConfigError).
        # 4. Build the meta-prompt (see below).
        # 5. Call chat_complete(json_mode=True) with the judge model + resolved key.
        # 6. Parse the JSON response → list[GeneratedScenario], clamped to `count`.
        # 7. Return.
```

### Meta-prompt shape

System message: fixed one-shot instructions describing the JSON schema the generator must emit — `scenario_key` (kebab-case slug, unique within batch), `prompt` (user utterance), optional `expected_answer`, `persona_criteria`, `instruction_criteria`, `tags` (array of short strings). Explicitly says "return ONLY a JSON object with a top-level `scenarios` array — no prose, no code fences."

User message: the agent's system prompt verbatim, wrapped as `"AGENT SYSTEM PROMPT:\n\n<prompt>\n\nGenerate <count> scenarios to test whether an LLM configured with this prompt behaves correctly."`

### JSON parse (fail-soft per row, fail-loud for whole batch)

- Use `json.loads(text)`; if that fails, try `_extract_first_json_object(text)` (a small regex-scan helper local to the file — code fences / trailing chatter tolerated).
- For each dict in `scenarios[]`:
  - Skip rows missing `scenario_key` or `prompt` (log at debug).
  - Coerce `tags` to `list[str]` (drop non-strings).
  - Stamp `generation_metadata = {"strategy": "llm", "judge_model": <model>, "raw_index": i}` for audit.
- Clamp to `count` even if the LLM returned more.
- If parse yields ZERO valid rows, raise `AgentLlmEvalConfigError("LLM returned no usable scenarios")` — the route already maps that to a 400 with the message.

### Error handling (per backend standards)

- Import the same typed exception the rest of the eval flow uses: `AgentLlmEvalConfigError` (no HTTP-specific classes).
- Wrap `chat_complete` failures with `logger.exception(...)` + re-raise as `AgentLlmEvalConfigError("LLM generation failed: …")` — the route maps to `AGENT_EVAL_CONFIG_INVALID`.
- Never leak provider stack traces or API responses to the user; log the full trace via loguru.

### Reuse checklist (mandatory — CLAUDE.md rule)

- ✅ Do NOT re-implement key resolution — call `AgentLlmEvalService._resolve_judge_key`.
  - Alternative: extract `_resolve_judge_key` to a module-level helper in `agent_llm/judge_key.py` if reusing a private method feels wrong (see "Optional refactor" below).
- ✅ Do NOT re-implement config loading — call `AgentConfigLoader().load_for_eval`.
- ✅ Do NOT re-implement judge settings resolution — call `load_agent_llm_eval_settings_for_org`.
- ✅ Do NOT re-implement chat completion — call `chat_complete`.

### Optional refactor (only if `_resolve_judge_key` reuse feels dirty)

Extract `_resolve_judge_key` from `AgentLlmEvalService` to a module-level function in a new file `core/services/evals/agent_llm/judge_key.py`. Change the existing method to a one-line delegator. Zero behavior change. Skip if the code review would prefer minimal diff — the private-method reuse pattern is well-established in this codebase.

---

## Phase 2 — Register the strategy

**File:** `core/services/evals/agent_llm/scenario_generation/strategies/__init__.py` (modify)

Add one import line so the side-effect module load registers the class:

```python
from core.services.evals.agent_llm.scenario_generation.strategies.llm import (  # noqa: F401
    LlmGenerator,
)
```

**File:** `core/services/evals/agent_llm/scenario_generation/__init__.py` (modify)

Extend the `_build_registry` dict with the new strategy:

```python
from core.services.evals.agent_llm.scenario_generation.strategies.llm import (
    LlmGenerator,
)
registry = {
    NoopGenerator.strategy_key: NoopGenerator,
    LlmGenerator.strategy_key: LlmGenerator,
}
```

No route change needed — `POST /agents/{id}/llm-evals/scenarios/generate` already accepts any registered `strategy` string.

---

## Phase 3 — Frontend: default the strategy to `llm`, hide the dropdown

**File:** `frontend/src/components/agents/agent-form/steps/LlmEvalsStep.tsx` (modify — `GenerateScenariosModal`)

Two targeted edits:

1. **Default `strategy = 'llm'`** and remove the dropdown (only one live strategy for now — `noop` stays registered for tests but never surfaces in the UI).
2. **Drop `dry_run: true` → `dry_run: false`** so the generated scenarios persist directly. The response's `persisted` list is what gets used — surface a success toast `"{N} scenarios added"` and rely on the shared invalidator (already wired into `useGenerateAgentLlmEvalScenarios`) to refresh the scenarios table.
3. **Add a clear error path**: on failure (missing published config, missing judge key, LLM returned nothing) rely on `handleApiError` — it already surfaces `detail.message` from the router's typed errors.

The modal stays: label "Auto-generate scenarios", count input (default 10, max 50 to bound cost), Cancel + Generate buttons. Loading state uses `generate.isPending`.

Do NOT remove the `noop` strategy from the backend — it's the safety net when the FE ever passes an unknown/omitted strategy.

---

## Phase 4 — Small safety additions

### 4.1 Cost/latency ceiling

Add a hardcoded `_MAX_COUNT = 50` in `LlmGenerator.generate` — clamp `count` to that value before calling the LLM. Prevents a caller from asking for 10,000 scenarios and burning tokens. Matches the FE's new max.

### 4.2 Duplicate-key handling

`create_scenarios_bulk` already raises `AgentLlmScenarioKeyConflictError` when a `scenario_key` collides. `LlmGenerator` may accidentally re-emit a slug that already exists on the agent (e.g. `booking_happy_path`). Two options:

- **A (chosen)**: catch the conflict at the route layer (already mapped to `SCENARIO_KEY_CONFLICT` 409) — user re-clicks Auto-generate and the LLM produces different slugs on retry (temperature > 0).
- **B**: retry once inside `LlmGenerator` with an appended "avoid these existing keys: [...]" hint. Skip — over-engineered for v1.

### 4.3 Logging

Every log line prefixed `[agent-llm-generate]` (matches existing `[agent-llm-eval]` convention). Log: agent_id, judge_model, requested/returned/persisted counts, judge latency. Never log the API key, the raw LLM response body, or the parsed scenarios (PII risk if the agent's prompt contains customer data).

---

## Files touched

**New**:
- `core/services/evals/agent_llm/scenario_generation/strategies/llm.py`

**Modified (additive only)**:
- `core/services/evals/agent_llm/scenario_generation/__init__.py` — one line in `_build_registry`
- `core/services/evals/agent_llm/scenario_generation/strategies/__init__.py` — one import
- `frontend/src/components/agents/agent-form/steps/LlmEvalsStep.tsx` — default strategy to `llm`, drop `dry_run`, drop strategy dropdown

**NOT touched** (functionality-preserved):
- `AgentLlmScenarioService.generate_scenarios` — unchanged
- `POST /scenarios/generate` route — unchanged
- `NoopGenerator` — unchanged (still callable via `strategy: 'noop'`)
- `AgentLlmEvalService.run_eval*` — unchanged
- Any RAG-eval file, any settings-page file, any migration

---

## Test plan (manual — no test scaffolding here)

1. In the UI, ensure `llm_evals.judge_model` is set (or `AGENT_LLM_EVAL_JUDGE_MODEL` env, or the hardcoded default `"gpt-4o"`).
2. Open an agent → LLM Evals tab → click **Auto-generate**.
3. Modal → keep count = 10 → click Generate.
4. Expect a "10 scenarios added" toast + table refresh with 10 new rows all badged `generated`.
5. Click a row → verify the prompt + criteria fields are populated + non-empty.
6. Repeat with a fresh agent that has no published config → expect the toast `"Agent 'X' has no published config — publish the agent before running an LLM eval."`.
7. Repeat with an agent whose LLM provider has no API key → expect the toast `"No '<provider>' API key configured for organization <id>."`.
8. Verify `POST /agents/{id}/llm-evals/scenarios/generate` still accepts `strategy: 'noop'` for regression (returns empty list, 200).

## Rollback

Revert the 3 modified files. The new `llm.py` file is inert without the registry entry. All rollback-safe; no DB or shared-state changes.

## Out of scope (v2 candidates)

- Diversity / coverage — v1 emits whatever the LLM proposes; no dedup against existing scenarios beyond the DB unique constraint.
- Preview-then-save UX — v1 persists directly. If users report "too many junk scenarios", flip `dry_run` on and add a Save-all button.
- Per-agent generator config (temperature, seed, model override) — v1 uses the org's `llm_evals.judge_model` only.
- Auto-run of the generator on agent create — deliberately not wired; user-triggered only.
