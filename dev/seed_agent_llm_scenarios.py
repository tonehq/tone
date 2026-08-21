"""Optional one-off seed script — upsert the CLI fixture scenarios into
``agent_llm_eval_scenarios`` for every org whose agent name matches
``LLMScenario.agent_slug``.

Not run by the main ``dev/seed.py`` — new agents start empty by design so
production installs never surprise-inherit dev fixtures. Run this manually
per environment to give existing demo agents starter scenarios:

    python dev/seed_agent_llm_scenarios.py

Idempotent — upserts by ``(agent_id, scenario_key)`` UNIQUE, so re-running
the script is safe (skips rows already present with ``source='fixture'``,
does NOT clobber rows the user has since edited manually — those keep their
current ``source`` and text).
"""

from __future__ import annotations

import os
import sys
from typing import Optional

# Same project-root-on-path bootstrap as dev/seed.py so the script can be
# invoked either as ``python dev/seed_agent_llm_scenarios.py`` or as
# ``python -m dev.seed_agent_llm_scenarios``.
if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

from dotenv import load_dotenv

load_dotenv()

from loguru import logger  # noqa: E402
from sqlalchemy import func  # noqa: E402

from core.database.session import get_db_context  # noqa: E402
from core.models.agent import Agent  # noqa: E402
from core.models.agent_llm_eval_scenario import AgentLlmEvalScenario  # noqa: E402
from evals.fixtures.agent_llm_scenarios import LLMScenario, SCENARIOS  # noqa: E402


_FIXTURE_SOURCE = "fixture"


def _find_agent_by_name(db, slug: str) -> Optional[Agent]:
    """Case-insensitive match on ``agents.name`` — mirrors the CLI resolver
    in ``AgentConfigLoader.resolve_agent_id`` so fixture-linkage semantics
    stay consistent between the CLI and this script."""
    return (
        db.query(Agent)
        .filter(func.lower(Agent.name) == slug.lower())
        .order_by(Agent.created_at.asc())
        .first()
    )


def _upsert_scenario(db, agent: Agent, scenario: LLMScenario) -> str:
    """Return one of ``'inserted' | 'skipped'``. Never overwrites a row the
    user has since edited — the ``source`` column is the audit trail."""
    existing = (
        db.query(AgentLlmEvalScenario)
        .filter(AgentLlmEvalScenario.agent_id == agent.id)
        .filter(AgentLlmEvalScenario.scenario_key == scenario.name)
        .first()
    )
    if existing is not None:
        return "skipped"

    row = AgentLlmEvalScenario(
        organization_id=agent.organization_id,
        agent_id=agent.id,
        scenario_key=scenario.name,
        scenario_ord=0,
        prompt=scenario.prompt,
        expected_answer=scenario.expected_answer,
        persona_criteria=scenario.persona_criteria,
        instruction_criteria=scenario.instruction_criteria,
        tags=list(scenario.tags) if scenario.tags else None,
        metrics_override=list(scenario.metrics) if scenario.metrics else None,
        threshold_override=scenario.threshold,
        source=_FIXTURE_SOURCE,
    )
    db.add(row)
    return "inserted"


def main() -> None:
    inserted = 0
    skipped = 0
    unmatched: list[str] = []

    with get_db_context() as db:
        for scenario in SCENARIOS:
            slug = (scenario.agent_slug or "").strip()
            if not slug:
                # ``agent_slug=None`` fixtures apply to every agent — the CLI
                # runs them ad-hoc, but persisting one row per (agent × scenario)
                # for every agent would double as a silent bulk write during
                # onboarding. Skip here; devs who want the ambient set for a
                # specific agent can copy the fixture and set an agent_slug.
                logger.info(
                    "[seed-agent-llm] fixture {} has agent_slug=None; skipping "
                    "(seed is per-agent — copy the fixture with a slug to include)",
                    scenario.name,
                )
                continue

            agent = _find_agent_by_name(db, slug)
            if agent is None:
                unmatched.append(slug)
                continue

            action = _upsert_scenario(db, agent, scenario)
            if action == "inserted":
                inserted += 1
            else:
                skipped += 1

        db.commit()

    if unmatched:
        logger.warning(
            "[seed-agent-llm] no agent matched {} fixture slug(s): {}",
            len(set(unmatched)), sorted(set(unmatched)),
        )
    logger.info(
        "[seed-agent-llm] done — inserted={} skipped={}",
        inserted, skipped,
    )


if __name__ == "__main__":
    main()
