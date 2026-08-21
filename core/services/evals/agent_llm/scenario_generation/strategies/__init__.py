"""Side-effect imports — pulling each strategy module in registers its class
with the factory registry defined in the parent package's ``__init__``.

Add a new strategy: create ``strategies/<name>.py`` implementing
``ScenarioGenerator``, then add one import line here. The parent package's
``get_scenario_generator`` factory automatically picks it up.
"""

from __future__ import annotations

from core.services.evals.agent_llm.scenario_generation.strategies.noop import (
    NoopGenerator,
)

__all__ = ["NoopGenerator"]
