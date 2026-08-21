"""LLM-backed scenario generator.

Uses the org's configured judge model (``llm_evals.judge_model`` → env →
hardcoded default) to propose ``count`` behavioral test scenarios based on
the agent's published system prompt. Persistence is the caller's
responsibility (``AgentLlmScenarioService.generate_scenarios`` calls
``create_scenarios_bulk`` on our return value) — this strategy never writes
to the DB, matching the ``ScenarioGenerator`` contract.

Reuse-first — nothing in this file re-implements what already exists:

- Agent config resolution → ``AgentConfigLoader.load_for_eval``
- Judge settings resolution → ``load_agent_llm_eval_settings_for_org``
- API key resolution (agent-key reuse + org fallback) →
  ``AgentLlmEvalService._resolve_judge_key``
- Provider-agnostic LLM call → ``chat_complete(json_mode=True)``
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Mapping, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.services.evals.agent_llm.scenario_generation.base import (
    GeneratedScenario,
    ScenarioGenerator,
)
from core.services.evals.errors import AgentLlmEvalConfigError

# Hard cap on how many scenarios one call can request — bounds cost + latency
# regardless of what the FE sends. Matches the FE's own max on the count input.
_MAX_COUNT = 50

# Deterministic-ish generation: low temperature keeps the output on-schema
# while leaving some room for variety across repeated runs.
_GENERATION_TEMPERATURE = 0.4
_GENERATION_MAX_TOKENS = 4096

_STRATEGY_KEY = "llm"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class LlmGenerator(ScenarioGenerator):
    """Produce scenarios by asking the judge LLM to reason over the agent's
    system prompt. Fail-loud on config errors (missing published config,
    missing API key, LLM outage) so the FE surfaces an actionable toast;
    fail-soft on individual malformed rows in the LLM's JSON output.
    """

    strategy_key = _STRATEGY_KEY

    def generate(
        self,
        db: Session,
        agent_id: UUID,
        *,
        count: int = 10,
        options: Optional[Mapping[str, Any]] = None,
    ) -> list[GeneratedScenario]:
        # Clamp BEFORE any DB / LLM work so a bad ``count`` can't burn tokens.
        # ``max(1, ...)`` guards against callers passing 0 / negative values —
        # the strategy contract lets us return fewer, never more.
        capped = max(1, min(int(count or 0), _MAX_COUNT))

        agent_config = self._load_agent_config(db, agent_id)
        judge_model = self._resolve_judge_model(db, agent_config.organization_id)
        judge_key = self._resolve_judge_key(agent_config, judge_model)

        t0 = time.monotonic()
        raw = self._call_generator_llm(
            system_prompt=agent_config.system_prompt or "",
            judge_model=judge_model,
            judge_key=judge_key,
            count=capped,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        scenarios = self._parse_scenarios(raw, judge_model=judge_model, cap=capped)

        logger.info(
            "[agent-llm-generate] agent={} judge_model={} requested={} returned={} latency_ms={}",
            agent_id, judge_model, capped, len(scenarios), latency_ms,
        )

        if not scenarios:
            raise AgentLlmEvalConfigError(
                "The generator returned no usable scenarios. Try again, or "
                "adjust the agent's system prompt so it describes concrete "
                "behaviors to test."
            )
        return scenarios

    # ── Reused primitives ──────────────────────────────────────────────

    def _load_agent_config(self, db: Session, agent_id: UUID):
        """Snapshot the agent's published config — same call the eval runner
        uses. Raises ``AgentLlmEvalConfigError`` when the agent is missing,
        unpublished, or lacks an LLM setup."""
        # Local import — the generator is loaded eagerly at registry build
        # time, keeping the heavy ``sqlalchemy.orm`` graph out of hot paths
        # that never invoke us.
        from core.services.evals.agent_llm.agent_config_loader import (
            AgentConfigLoader,
        )

        return AgentConfigLoader().load_for_eval(db, agent_id)

    def _resolve_judge_model(self, db: Session, organization_id: UUID) -> str:
        """``llm_evals.judge_model`` (DB) → ``AGENT_LLM_EVAL_JUDGE_MODEL`` (env)
        → hardcoded default. One resolver, shared with the run-eval path."""
        from core.services.org_settings import (
            load_agent_llm_eval_settings_for_org,
        )

        return load_agent_llm_eval_settings_for_org(db, organization_id).judge_model

    def _resolve_judge_key(self, agent_config, judge_model: str) -> str:
        """Reuses the exact key-resolution helper the eval runner uses so a
        misconfigured provider surfaces the same error in the generator flow
        as in the scoring flow."""
        # Local import breaks a possible import cycle (service imports
        # scenario_service → scenario_service imports us via
        # generate_scenarios lazy path).
        from core.services.evals.agent_llm.service import AgentLlmEvalService

        return AgentLlmEvalService()._resolve_judge_key(
            organization_id=agent_config.organization_id,
            judge_model=judge_model,
            fallback_provider=agent_config.llm_provider,
            fallback_key=agent_config.llm_api_key,
        )

    # ── LLM call + parse ───────────────────────────────────────────────

    def _call_generator_llm(
        self,
        *,
        system_prompt: str,
        judge_model: str,
        judge_key: str,
        count: int,
    ) -> str:
        """Invoke the judge model with a fixed meta-prompt. Wraps SDK errors
        in ``AgentLlmEvalConfigError`` (with the full traceback logged) so
        the route maps them to a clean 400 instead of a 500."""
        from core.services.llm.chat_complete import chat_complete

        messages = [
            {"role": "system", "content": _META_SYSTEM_PROMPT.format(count=count)},
            {
                "role": "user",
                "content": (
                    "AGENT SYSTEM PROMPT:\n\n"
                    f"{(system_prompt or '').strip() or '(empty)'}\n\n"
                    f"Generate up to {count} scenarios."
                ),
            },
        ]
        try:
            return chat_complete(
                model=judge_model,
                api_key=judge_key,
                messages=messages,
                temperature=_GENERATION_TEMPERATURE,
                max_tokens=_GENERATION_MAX_TOKENS,
                json_mode=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "[agent-llm-generate] LLM call failed judge_model={}", judge_model,
            )
            raise AgentLlmEvalConfigError(
                f"Scenario generator LLM call failed ({type(exc).__name__}). "
                "Check the judge model + provider key on Settings → Evaluations."
            ) from exc

    def _parse_scenarios(
        self,
        raw: str,
        *,
        judge_model: str,
        cap: int,
    ) -> list[GeneratedScenario]:
        """Extract a list of scenario dicts from the LLM response. Tolerates
        stray prose / code fences by falling back to a JSON-object extractor.
        Silently drops rows missing required fields — the batch fails-loud
        only when EVERY row is unusable (handled by ``generate``)."""
        data = _try_parse_json(raw)
        if not isinstance(data, Mapping):
            logger.debug(
                "[agent-llm-generate] LLM response was not a JSON object: {!r}", raw[:200],
            )
            return []

        rows = data.get("scenarios")
        if not isinstance(rows, list):
            logger.debug(
                "[agent-llm-generate] JSON missing 'scenarios' array; keys={}",
                list(data.keys()),
            )
            return []

        seen_keys: set[str] = set()
        out: list[GeneratedScenario] = []
        for index, row in enumerate(rows):
            if len(out) >= cap:
                break
            scenario = _row_to_scenario(
                row,
                index=index,
                seen_keys=seen_keys,
                judge_model=judge_model,
            )
            if scenario is None:
                continue
            seen_keys.add(scenario.scenario_key)
            out.append(scenario)
        return out


# ── Meta-prompt ─────────────────────────────────────────────────────────

_META_SYSTEM_PROMPT = """You are a QA test author for voice/chat AI agents.

You will be given an AGENT SYSTEM PROMPT. Produce {count} realistic user
utterances that exercise how well an LLM configured with that prompt
follows its instructions and persona.

Return STRICTLY a JSON object (no prose, no code fences, no markdown) with
this shape:

{{
  "scenarios": [
    {{
      "scenario_key": "short_snake_case_slug",
      "prompt": "The user's message to the agent",
      "expected_answer": "Optional — the ideal response (or omit if not applicable)",
      "persona_criteria": "Optional — describe how the agent should sound (tone, personality) or omit",
      "instruction_criteria": "Optional — describe what the agent MUST or MUST NOT do based on the system prompt",
      "tags": ["short", "kebab_or_snake"]
    }}
  ]
}}

Rules:
- Every scenario_key MUST be unique within this response and lowercase snake_case.
- Cover a mix of: happy path, edge cases, corrections mid-conversation,
  refusals, out-of-scope requests, ambiguous input, and adversarial cases
  that test the agent's guardrails.
- Only include expected_answer when the correct answer is deterministic
  (e.g. a factual response the system prompt promises).
- instruction_criteria should quote or paraphrase specific rules from the
  system prompt so the judge can verify them.
- Keep prompts natural — one message per scenario, no dialogue turns.
"""


# ── Helpers (module-level, pure) ────────────────────────────────────────


def _try_parse_json(raw: str) -> Any:
    """Parse ``raw`` as JSON. Falls back to extracting the first top-level
    object if the model wrapped the JSON in prose / code fences (a common
    failure mode even with ``json_mode=True`` on some providers)."""
    if not raw:
        return None
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip code fences (```json ... ```).
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    if stripped != text:
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    # Last resort: find the first {...} balanced object.
    obj = _extract_first_json_object(text)
    if obj is not None:
        try:
            return json.loads(obj)
        except json.JSONDecodeError:
            return None
    return None


def _extract_first_json_object(text: str) -> Optional[str]:
    """Return the substring of the first balanced ``{...}`` block, or ``None``
    if no balanced block is present. Ignores braces inside strings."""
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    return text[start : i + 1]
    return None


def _row_to_scenario(
    row: Any,
    *,
    index: int,
    seen_keys: set[str],
    judge_model: str,
) -> Optional[GeneratedScenario]:
    """Coerce one dict from the LLM response into a ``GeneratedScenario``.
    Returns ``None`` for rows missing required fields or with a duplicate
    key within this batch (dedup is per-response; DB-level dedup lives in
    ``AgentLlmScenarioService.create_scenarios_bulk``)."""
    if not isinstance(row, Mapping):
        return None

    prompt = _clean_str(row.get("prompt"))
    if not prompt:
        return None

    key = _clean_str(row.get("scenario_key")) or f"generated_{index + 1}"
    slug = _slugify(key)
    if not slug or slug in seen_keys:
        # Duplicate within this batch — append the ordinal so it stays unique.
        slug = f"{slug or 'generated'}_{index + 1}"
        if slug in seen_keys:
            return None

    return GeneratedScenario(
        scenario_key=slug,
        prompt=prompt,
        expected_answer=_clean_str(row.get("expected_answer")),
        persona_criteria=_clean_str(row.get("persona_criteria")),
        instruction_criteria=_clean_str(row.get("instruction_criteria")),
        tags=_clean_tags(row.get("tags")),
        generation_metadata={
            "strategy": _STRATEGY_KEY,
            "judge_model": judge_model,
            "raw_index": index,
        },
    )


def _clean_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _clean_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        _slugify(v) for v in value if isinstance(v, str) and v.strip()
    ][:8]


def _slugify(text: str) -> str:
    """Lowercase snake_case slug — the format the scenario_key column
    expects. Non-alphanumerics collapse to a single underscore."""
    lowered = text.strip().lower()
    slug = _SLUG_RE.sub("_", lowered).strip("_")
    return slug[:120]


__all__ = ["LlmGenerator"]
