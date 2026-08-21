"""Scenario-generation registry — the ONE place strategy classes are looked up.

Callers (``AgentLlmScenarioService.generate_scenarios``, the API route, a
future cron job) never import a specific strategy — they call
:func:`get_scenario_generator` with a string key. Adding a new strategy is a
one-line change in ``strategies/__init__.py`` plus a new file under
``strategies/``. Nothing at the call site changes.

Registry construction is import-driven — importing
``.strategies`` runs each module which lands its class in ``_REGISTRY`` at
class-body time. Keeping the registry building explicit (not a metaclass
side-effect) means the strategy list is greppable and stable.
"""

from __future__ import annotations

from core.services.evals.agent_llm.scenario_generation.base import (
    GeneratedScenario,
    ScenarioGenerator,
)


def _build_registry() -> dict[str, type[ScenarioGenerator]]:
    # Import the strategies package for its side-effect (class definitions).
    # Local import keeps the module cheap to load when only the ABC is needed.
    from core.services.evals.agent_llm.scenario_generation import strategies  # noqa: F401

    from core.services.evals.agent_llm.scenario_generation.strategies.llm import (
        LlmGenerator,
    )
    from core.services.evals.agent_llm.scenario_generation.strategies.noop import (
        NoopGenerator,
    )

    registry: dict[str, type[ScenarioGenerator]] = {
        # ``noop`` stays registered as a safety net + regression target — it
        # returns an empty list and never touches the LLM. The FE surfaces
        # only ``llm`` in the dropdown.
        NoopGenerator.strategy_key: NoopGenerator,
        LlmGenerator.strategy_key: LlmGenerator,
    }
    return registry


_REGISTRY: dict[str, type[ScenarioGenerator]] = _build_registry()


def get_scenario_generator(strategy: str) -> ScenarioGenerator:
    """Return an instantiated generator for ``strategy``.

    Raises ``ValueError`` (mapped to HTTP 400 at the route layer) for an
    unknown strategy so a typo in the FE never silently uses the wrong
    algorithm. Returned instances are cheap — instantiated fresh each call
    so any per-run mutable state (options, RNG, cache) stays isolated.
    """
    key = (strategy or "").strip().lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        raise ValueError(
            f"Unknown scenario generator strategy: {strategy!r}. "
            f"Registered: {sorted(_REGISTRY.keys())}"
        )
    return cls()


def registered_strategies() -> list[str]:
    """Public read of the registry — used by the route layer to advertise
    available strategies to the FE (dropdown options)."""
    return sorted(_REGISTRY.keys())


__all__ = [
    "GeneratedScenario",
    "ScenarioGenerator",
    "get_scenario_generator",
    "registered_strategies",
]
