from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class AgentLlmEvalRun(OrgScopedModel):
    """One agent-LLM eval batch — one row per Run Eval click. Owns the run
    lifecycle (``pending → running → completed / failed``) so the UI can show
    the run the moment it's triggered instead of only after every scenario
    has been scored.

    Companion table: ``agent_llm_eval_results`` stores the per-scenario
    scored rows and still uses ``run_id`` as its grouping key. This row's
    ``id`` IS that ``run_id`` — the two are kept in sync at the app layer
    (no hard FK on the results table to keep the migration additive; the
    ``UniqueConstraint(run_id, scenario_key)`` on the results table plus the
    unique ``id`` here is enough to prevent divergence in practice).

    Snapshotted fields (``judge_model``, ``llm_model``, ``llm_provider``,
    ``triggered_by``, ``filter_snapshot``) mirror what the results table
    already stamps per-row so history stays readable after a mid-run agent
    config change.
    """

    __tablename__ = "agent_llm_eval_runs"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "run_number", name="uq_agent_llm_eval_runs_agent_run_number"
        ),
        Index("ix_agent_llm_eval_runs_agent_status", "agent_id", "status"),
        Index(
            "ix_agent_llm_eval_runs_agent_started_desc",
            "agent_id",
            "started_at",
        ),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_number = Column(Integer, nullable=False)
    triggered_by = Column(String(32), nullable=False)  # 'ui' | 'cli' | 'api'

    # Lifecycle state. Terminal states are ``completed`` and ``failed``.
    # ``pending`` = row inserted by the router before enqueue.
    # ``running`` = worker has picked up the job and started scoring.
    status = Column(String(20), nullable=False, default="pending")

    judge_model = Column(String(120), nullable=True)
    judge_engine = Column(String(32), nullable=True)
    # Snapshotted at ``mark_running`` (once the worker has loaded the live
    # agent config), so the UI can show which answer model produced the
    # scored answers even after the agent's live config changes.
    llm_model = Column(String(120), nullable=True)
    llm_provider = Column(String(60), nullable=True)

    # Known at trigger time — lets the UI render "Scoring N of M" progress
    # while status is non-terminal without waiting for the results table to
    # catch up.
    total_scenarios = Column(Integer, nullable=False, default=0)
    # Snapshot of the trigger filter for reproducibility (``scenario_ids``,
    # ``tags``, ``folder``, ``folders``). Loose JSONB — the UI won't unpack
    # it in v1; keeps the door open for a "re-run this exact selection"
    # affordance without a schema change.
    filter_snapshot = Column(JSONB, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Safe, user-visible short string for ``status='failed'`` rows. Full
    # traceback goes to logs (``logger.exception`` in the worker), NOT here.
    error = Column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "run_number": self.run_number,
            "triggered_by": self.triggered_by,
            "status": self.status,
            "judge_model": self.judge_model,
            "judge_engine": self.judge_engine,
            "llm_model": self.llm_model,
            "llm_provider": self.llm_provider,
            "total_scenarios": self.total_scenarios,
            "filter_snapshot": self.filter_snapshot,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
