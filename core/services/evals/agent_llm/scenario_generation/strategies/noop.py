"""``NoopGenerator`` — the v1 placeholder strategy.

The FE surfaces a working "Auto-generate scenarios" button in v1 so the UX
lands whole, but no real algorithm exists yet. This strategy returns an
empty list and lets the service / route respond "0 generated — coming
soon" without special-casing the flow.

When a real strategy is implemented, it lands alongside this one and gets
one line in ``strategies/__init__.py`` — no route, service, or FE change.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.services.evals.agent_llm.scenario_generation.base import (
    GeneratedScenario,
    ScenarioGenerator,
)


class NoopGenerator(ScenarioGenerator):
    strategy_key = "noop"

    def generate(
        self,
        db: Session,
        agent_id: UUID,
        *,
        count: int = 10,
        options: Optional[Mapping[str, Any]] = None,
    ) -> list[GeneratedScenario]:
        return []


__all__ = ["NoopGenerator"]
