"""Extension seam for scenario auto-generation strategies.

Every real generator (LLM-based, template-based, coverage-driven, …) subclasses
``ScenarioGenerator`` and registers itself in
``core/services/evals/agent_llm/scenario_generation/__init__.py``. The
``AgentLlmScenarioService.generate_scenarios`` entry point calls the factory
and never touches strategy-specific code, so adding a new strategy in the
future is one file + one line in the registry — no changes to the route,
service, or UI.

Kept ABC-first (not Protocol) so linters and IDEs flag missing ``generate``
implementations at import time rather than silently at first call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, Optional
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass
class GeneratedScenario:
    """One proposed scenario the strategy wants to add — pre-persistence.

    The FE preview step renders these read-only so the user can accept /
    reject before ``AgentLlmScenarioService.create_scenarios_bulk`` turns
    them into real ``agent_llm_eval_scenarios`` rows. Field names match
    ``ScenarioInput`` so no adapter is needed at the persist call site.
    """

    scenario_key: str
    prompt: str
    expected_answer: Optional[str] = None
    persona_criteria: Optional[str] = None
    instruction_criteria: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    # 0..1 self-reported "how confident is the generator that this scenario
    # is worth running?" — the FE uses it to rank / de-select low-quality
    # picks in the preview step. Optional because deterministic template
    # strategies have no meaningful score.
    confidence: Optional[float] = None
    # Provenance blob persisted verbatim to ``generation_metadata`` — how it
    # was made (strategy, model, prompt hash, coverage bucket, …). The UI
    # never renders this; it's audit-only.
    generation_metadata: Optional[dict] = None


class ScenarioGenerator(ABC):
    """Strategy for producing new eval scenarios for one agent.

    Subclasses must set ``strategy_key`` to the value the factory registers
    them under (matches the ``strategy`` string the FE and route layers pass
    around). Everything else — DB access, LLM calls, coverage analysis —
    lives inside ``generate``.
    """

    strategy_key: ClassVar[str] = ""

    @abstractmethod
    def generate(
        self,
        db: Session,
        agent_id: UUID,
        *,
        count: int = 10,
        options: Optional[Mapping[str, Any]] = None,
    ) -> list[GeneratedScenario]:
        """Return up to ``count`` proposed scenarios for ``agent_id``.

        Implementations MAY return fewer (an LLM strategy might dedupe or
        fail-soft) but MUST NOT return more — the FE and route layers rely
        on the caller-supplied bound. Implementations MUST NOT persist to
        the DB; that responsibility lives on
        ``AgentLlmScenarioService.create_scenarios_bulk`` (single-writer
        rule — see the DRY reuse doctrine).

        ``options`` is a strategy-specific dict (temperature, coverage
        bucket, seed corpus id, …). Kept as an open mapping so new
        strategies don't force a signature change here.
        """


__all__ = ["GeneratedScenario", "ScenarioGenerator"]
