from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class AgentLlmEvalScenario(OrgScopedModel):
    """One reusable Level-2 (agent-LLM) eval test case attached to an agent.

    Persists what today lives only in the ``evals/fixtures/agent_llm_scenarios.py``
    dataclass list. ``AgentLlmEvalService.run_eval_for_agent`` loads rows here,
    converts each into the in-memory ``LLMScenario`` used by the existing
    ``run_eval`` codepath, and never mutates the row — running an eval does
    NOT edit scenarios (scenarios are the input, results are the output).

    Hard-delete, not soft-delete: scenarios are user-authored inputs, not
    audit-critical historical rows. Removing one just means "stop scoring
    this case"; the historical ``agent_llm_eval_results`` rows keep their
    own snapshotted ``prompt`` / ``expected_answer`` so past runs remain
    fully explainable even after their source scenario is gone.

    The v2 forward-compat columns (``expected_tools`` / ``tool_config``) sit
    here alongside the mirror columns on ``agent_llm_eval_results`` so a
    future tool-scoring runner can persist expected vs. actual traces without
    needing another migration.
    """

    __tablename__ = "agent_llm_eval_scenarios"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "scenario_key",
            name="uq_agent_llm_eval_scenarios_agent_key",
        ),
        Index(
            "ix_agent_llm_eval_scenarios_agent_ord",
            "agent_id",
            "scenario_ord",
        ),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Stable per-agent slug — the join key that also lands on every
    # ``agent_llm_eval_results.scenario_key`` so a scenario's result history
    # survives an id change (e.g. re-import from CSV).
    scenario_key = Column(String(120), nullable=False)
    scenario_ord = Column(Integer, nullable=False, default=0)

    prompt = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    # GEval free-text rubrics. Empty → the corresponding metric is skipped
    # for this scenario even if globally enabled.
    persona_criteria = Column(Text, nullable=True)
    instruction_criteria = Column(Text, nullable=True)

    tags = Column(JSONB, nullable=True)

    # Single-value grouping (e.g. "Refund flow"). NULL = "Uncategorized" in the
    # UI. Snapshotted onto ``agent_llm_eval_results.folder`` at run time so
    # historical grouping survives edits/deletes. Rename is a bulk UPDATE on
    # BOTH tables in one transaction — see ``rename_folder`` in the service.
    folder = Column(String(120), nullable=True)

    # Per-scenario overrides — NULL means "use the org's ``agent_llm.*``
    # eval settings from ``organizations.eval_settings``".
    metrics_override = Column(JSONB, nullable=True)
    threshold_override = Column(Float, nullable=True)

    # Provenance: 'manual' | 'csv' | 'generated' | 'fixture'. Used by the UI
    # to badge the row and by the CLI seed script to skip re-upserting
    # rows the user has since edited manually.
    source = Column(String(32), nullable=False, default="manual")
    generation_metadata = Column(JSONB, nullable=True)

    # v2 forward-compat — read only by the (not yet built) tool/MCP eval
    # runner. Nullable so v1 flows never touch them.
    expected_tools = Column(JSONB, nullable=True)
    tool_config = Column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "scenario_key": self.scenario_key,
            "scenario_ord": self.scenario_ord,
            "prompt": self.prompt,
            "expected_answer": self.expected_answer,
            "persona_criteria": self.persona_criteria,
            "instruction_criteria": self.instruction_criteria,
            "tags": self.tags,
            "folder": self.folder,
            "metrics_override": self.metrics_override,
            "threshold_override": self.threshold_override,
            "source": self.source,
            "generation_metadata": self.generation_metadata,
            "expected_tools": self.expected_tools,
            "tool_config": self.tool_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
