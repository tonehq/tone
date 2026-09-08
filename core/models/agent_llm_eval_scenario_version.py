from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class AgentLlmEvalScenarioVersion(OrgScopedModel):
    """One version of an agent's LLM-eval scenario set.

    Each auto-generation (or manual/imported set) is a version — the unit the
    user reviews and approves. Scenario rows (``AgentLlmEvalScenario`` with
    ``node_type='scenario'``) point at a version via ``version_id``; version
    ``version_number`` is numbered per agent (1, 2, 3 …).

    ``status`` lifecycle: ``generating`` (background job producing scenarios)
    → ``draft`` (scenarios generated, saved as ``pending`` and under review)
    → ``finalized`` (reviewed / approved). A failed background generation lands
    on ``failed`` with a user-safe ``generation_error`` so the FE can surface it.

    Runs (``agent_llm_eval_runs``) are tied to a version and score only its
    ``approval_status='approved'`` scenarios; deleting a version nulls the
    version stamp on historical runs/results (``ON DELETE SET NULL``) so run
    history survives.
    """

    __tablename__ = "agent_llm_eval_scenario_versions"
    __table_args__ = (
        UniqueConstraint(
            "agent_id",
            "version_number",
            name="uq_agent_llm_eval_scenario_versions_agent_number",
        ),
        Index("ix_agent_llm_eval_scenario_versions_agent", "agent_id"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    # 'generated' (LLM) | 'manual' | 'imported'
    source = Column(String(16), nullable=False, default="generated")
    # 'generating' (bg job) | 'draft' (under review) | 'finalized' (approved) | 'failed'
    status = Column(String(16), nullable=False, default="draft")
    # The user's custom generation prompt for this version (nullable).
    generation_prompt = Column(Text, nullable=True)
    generated_by_model = Column(String(120), nullable=True)
    generation_prompt_hash = Column(String(64), nullable=True)
    # User-safe reason shown when a background generation fails (status='failed').
    generation_error = Column(Text, nullable=True)

    scenarios = relationship(
        "AgentLlmEvalScenario",
        back_populates="version_ref",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "version_number": self.version_number,
            "source": self.source,
            "status": self.status,
            "generation_prompt": self.generation_prompt,
            "generated_by_model": self.generated_by_model,
            "generation_prompt_hash": self.generation_prompt_hash,
            "generation_error": self.generation_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
