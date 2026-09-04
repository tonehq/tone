"""LLM-backed scenario generator.

Uses the org's configured judge model (``llm_evals.judge_model`` → env →
hardcoded default) to propose ``count`` behavioral test scenarios based on
the agent's published behavior:

- **Prompt-mode agents** — reads the ``system_prompt`` and asks the judge
  to invent utterances that exercise the described persona / rules.
- **Workflow-mode agents** — reads the serialized workflow playbook
  (the SAME markdown the runtime injects; see
  ``core/services/workflow/prompt_serializer.py``) and asks the judge to
  invent utterances that exercise each step and branch.

For agents that also have TOOLS or MCP SERVERS attached (Phase 2), the
generator appends compact "AGENT TOOLS:" / "AGENT MCP SERVERS:" sections
to the user turn and asks the judge to pre-label tool-triggering scenarios
with an ``expected_tools`` array. The deterministic ``tool_selection``
metric then compares those expectations against what the answering LLM
actually emitted (see ``core/services/evals/deepeval/metric_registry.py``).

Persistence is the caller's responsibility
(``AgentLlmScenarioService.generate_scenarios`` calls
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
    behavior — either its ``system_prompt`` (prompt mode) or its serialized
    workflow playbook (workflow mode). Fail-loud on config errors (missing
    published config, missing API key, LLM outage) so the FE surfaces an
    actionable toast; fail-soft on individual malformed rows in the LLM's
    JSON output.
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
            agent_config=agent_config,
            judge_model=judge_model,
            judge_key=judge_key,
            count=capped,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)

        scenarios = self._parse_scenarios(raw, judge_model=judge_model, cap=capped)

        logger.info(
            "[agent-llm-generate] agent={} mode={} judge_model={} requested={} returned={} latency_ms={}",
            agent_id, agent_config.mode, judge_model, capped, len(scenarios), latency_ms,
        )

        if not scenarios:
            raise AgentLlmEvalConfigError(
                "The generator returned no usable scenarios. Try again, or "
                "adjust the agent's system prompt, workflow, or tool "
                "descriptions so it describes concrete behaviors to test."
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
        """Reuses the shared key resolver so a misconfigured provider surfaces
        the same error in the generator flow as in the scoring flow. Uses a
        fresh session (this runs outside a request-scoped session); the agent's
        own key is the same-provider fallback."""
        from core.database.session import SessionLocal
        from core.services.evals.judge_key import resolve_judge_key

        with SessionLocal() as tmp:
            return resolve_judge_key(
                tmp,
                organization_id=agent_config.organization_id,
                judge_model=judge_model,
                fallback_provider=agent_config.llm_provider,
                fallback_key=agent_config.llm_api_key,
                error_cls=AgentLlmEvalConfigError,
            )

    # ── LLM call + parse ───────────────────────────────────────────────

    def _call_generator_llm(
        self,
        *,
        agent_config,
        judge_model: str,
        judge_key: str,
        count: int,
    ) -> str:
        """Invoke the judge model with a fixed meta-prompt. Wraps SDK errors
        in ``AgentLlmEvalConfigError`` (with the full traceback logged) so
        the route maps them to a clean 400 instead of a 500.

        Meta-prompt + user-message wrapper are chosen from ``agent_config.mode``:
        prompt agents get the "read this system prompt" framing; workflow agents
        get the "read this conversation-workflow playbook" framing. The playbook
        text itself is the SAME markdown the runtime injects — resolved once
        in :class:`AgentConfigLoader`."""
        from core.services.llm.chat_complete import chat_complete

        if agent_config.workflow_serialized:
            system = _META_SYSTEM_PROMPT_WORKFLOW.format(count=count)
            user_head = (
                "AGENT WORKFLOW PLAYBOOK:\n\n"
                f"{agent_config.workflow_serialized.strip() or '(empty)'}"
            )
        else:
            system = _META_SYSTEM_PROMPT.format(count=count)
            user_head = (
                "AGENT SYSTEM PROMPT:\n\n"
                f"{(agent_config.system_prompt or '').strip() or '(empty)'}"
            )

        user = _compose_user_message(
            user_head,
            tools=getattr(agent_config, "tools", None) or [],
            mcp_servers=getattr(agent_config, "mcp_server_summaries", None) or [],
            count=count,
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
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


# ── Meta-prompts ────────────────────────────────────────────────────────
# Two variants — same JSON output schema and rules, different framing:
#   ``_META_SYSTEM_PROMPT``          → agent driven by a single system prompt
#   ``_META_SYSTEM_PROMPT_WORKFLOW`` → agent driven by a conversation-workflow
#                                      playbook (graph of steps + branches)
# The picker lives in ``LlmGenerator._call_generator_llm``; downstream
# parsing (``_parse_scenarios``) is variant-agnostic.

_META_SYSTEM_PROMPT = """You are a QA test author for voice/chat AI agents.

You will be given an AGENT SYSTEM PROMPT. Produce {count} realistic user
utterances that exercise how well an LLM configured with that prompt
follows its instructions and persona.

If an AGENT TOOLS or AGENT MCP SERVERS section is also included, ALSO
generate scenarios that should trigger each tool at least once, and
pre-label those scenarios with an ``expected_tools`` array so the eval
can grade whether the model picked the right tool.

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
      "expected_tools": [
        {{"name": "tool_name", "arguments": {{"arg_name": "value"}}}}
      ],
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
- Only include expected_tools for scenarios that should trigger a tool
  the agent has attached — OMIT the field entirely for text-only scenarios.
  Argument values should be extractable from the user's message.
- Keep prompts natural — one message per scenario, no dialogue turns.
"""


_META_SYSTEM_PROMPT_WORKFLOW = """You are a QA test author for voice/chat AI agents.

You will be given an AGENT WORKFLOW PLAYBOOK: a step-by-step conversation
graph the agent MUST follow. It describes named steps (Talk / Decision /
Tool / API request / End), the exact wording rules per step, the variables
each step collects, and the branch conditions that decide the next step.

If an AGENT TOOLS or AGENT MCP SERVERS section is also included, pre-label
each tool-triggering scenario with an ``expected_tools`` array so the eval
can grade whether the model picked the right tool at the right step.

Produce {count} realistic user utterances that exercise DIFFERENT steps and
branches of that playbook — including edge cases where the user tries to
skip a step, gives partial/invalid input, jumps to a later step early, or
picks a rare branch.

Return STRICTLY a JSON object (no prose, no code fences, no markdown) with
this shape:

{{
  "scenarios": [
    {{
      "scenario_key": "short_snake_case_slug",
      "prompt": "The user's message to the agent",
      "expected_answer": "Optional — the ideal response (or omit if not applicable)",
      "persona_criteria": "Optional — describe how the agent should sound (tone, personality) or omit",
      "instruction_criteria": "Optional — describe which step the agent should be in and what it MUST or MUST NOT do at that step",
      "expected_tools": [
        {{"name": "tool_name", "arguments": {{"arg_name": "value"}}}}
      ],
      "tags": ["short", "kebab_or_snake"]
    }}
  ]
}}

Rules:
- Every scenario_key MUST be unique within this response and lowercase snake_case.
- Cover a mix across the playbook: happy path through each named step, at
  least one utterance per branch condition where feasible, refusals /
  out-of-scope requests, ambiguous input, and adversarial cases testing the
  step-skipping / step-jumping guardrails.
- Prefer scenario_keys and tags that reference the step or branch under test
  (e.g. ``collect_name_typo``, ``skip_confirmation``, tags: ["decision_step"]).
- Only include expected_answer when the correct answer is deterministic
  (a specific line the playbook promises for that step).
- instruction_criteria should quote or paraphrase the specific step's rule
  from the playbook so the judge can verify adherence.
- Only include expected_tools for scenarios that should trigger a tool
  the agent has attached — OMIT the field entirely for text-only scenarios.
  Argument values should be extractable from the user's message.
- Keep prompts natural — one message per scenario, no dialogue turns.
"""


# ── Helpers (module-level, pure) ────────────────────────────────────────


def _compose_user_message(
    head: str,
    *,
    tools: list,
    mcp_servers: list,
    count: int,
) -> str:
    """Assemble the user turn: agent-description head → optional tools →
    optional MCP servers → generate-count directive.

    Sections are OMITTED entirely (no header, no ``(none)`` placeholder)
    when the corresponding list is empty. That keeps the meta-prompt for
    a no-tool prompt agent byte-identical to the Phase 1 shape so the
    generator's judge-side reasoning doesn't change on a regression path.
    """
    parts: list[str] = [head]

    if tools:
        tool_lines = []
        for t in tools:
            fn = t.get("function") if isinstance(t, dict) else None
            if not isinstance(fn, dict):
                continue
            name = fn.get("name") or ""
            if not name:
                continue
            desc = (fn.get("description") or "").strip()
            args = _summarize_tool_args(fn.get("parameters"))
            tool_lines.append(
                f"- {name}({args}) — {desc}" if desc else f"- {name}({args})"
            )
        if tool_lines:
            parts.append("AGENT TOOLS:\n" + "\n".join(tool_lines))

    if mcp_servers:
        mcp_lines = []
        for s in mcp_servers:
            if not isinstance(s, dict):
                continue
            name = s.get("name") or ""
            if not name:
                continue
            desc = (s.get("description") or "").strip()
            mcp_lines.append(f"- {name} — {desc}" if desc else f"- {name}")
        if mcp_lines:
            parts.append("AGENT MCP SERVERS:\n" + "\n".join(mcp_lines))

    parts.append(
        f"Generate up to {count} scenarios. "
        "For any scenario that should trigger a tool, populate "
        "`expected_tools` with the tool name and expected arguments."
    )
    return "\n\n".join(parts)


def _summarize_tool_args(parameters) -> str:
    """Compact one-line arg summary for the tool listing (``arg1, arg2, ...``).
    Returns the required args first (in DECLARED order), then optional args
    (in property-dict insertion order), so the judge sees the shape at a
    glance without dumping the full JSON schema. Empty when no
    ``properties`` are declared.

    Declared-list order matters for reproducibility: iterating a Python
    ``set`` yields hash-randomized order (PYTHONHASHSEED) which would flip
    the arg listing between process starts — making the generator's user
    prompt non-deterministic and breaking replay / fixture / cache-key
    workflows.
    """
    if not isinstance(parameters, dict):
        return ""
    props = parameters.get("properties")
    if not isinstance(props, dict) or not props:
        return ""
    required = parameters.get("required")
    required_list = [r for r in required if isinstance(r, str)] if isinstance(required, list) else []
    required_set = set(required_list)
    # Preserve declared list order in ``required`` (deterministic across
    # process starts), then append the remaining property keys in dict
    # insertion order (which Python 3.7+ guarantees).
    ordered = required_list + [k for k in props.keys() if k not in required_set]
    return ", ".join(ordered)



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
        # Tool-aware fields (Phase 2). Malformed rows silently degrade to
        # None — the scenario is still valid as a text-only test, and the
        # deterministic ``tool_selection`` metric skips when expected_tools
        # is None.
        expected_tools=_clean_expected_tools(row.get("expected_tools")),
        generation_metadata={
            "strategy": _STRATEGY_KEY,
            "judge_model": judge_model,
            "raw_index": index,
        },
    )


# Hard cap on how many tool expectations one scenario can carry — bounds
# JSONB row size and prevents a runaway generator from asking the judge to
# grade dozens of tool calls per scenario. Realistic scenarios expect 1-2
# tools; anything past 5 is almost certainly noise.
_MAX_EXPECTED_TOOLS = 5


def _clean_expected_tools(value: Any) -> Optional[list]:
    """Coerce the judge's ``expected_tools`` output into a list of
    ``{"name": str, "arguments": dict}`` entries.

    Returns ``None`` (not ``[]``) when the input is absent / empty so
    downstream code can cheaply distinguish "text-only scenario" from
    "tool-triggering scenario with no args". Silently drops entries with
    no ``name`` — the generator shouldn't fail a whole scenario over one
    malformed tool ref.

    Filtering happens BEFORE the ``_MAX_EXPECTED_TOOLS`` cap so a batch
    where the first N entries are malformed doesn't lose the valid
    entries that follow them — the cap counts VALID tools, not raw items.
    """
    if not isinstance(value, list) or not value:
        return None
    cleaned: list[dict] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = _clean_str(item.get("name"))
        if not name:
            continue
        args = item.get("arguments")
        if not isinstance(args, Mapping):
            args = {}
        cleaned.append({"name": name, "arguments": dict(args)})
        if len(cleaned) >= _MAX_EXPECTED_TOOLS:
            break
    return cleaned or None


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
