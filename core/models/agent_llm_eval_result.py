from datetime import datetime, timezone

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


class AgentLlmEvalResult(OrgScopedModel):
    """One scored scenario for one agent-LLM eval run — a run over N scenarios
    writes N rows here. All rows of the same run share ``run_id`` (a UUID
    stamped by ``AgentLlmEvalService``) plus the per-agent monotonic
    ``run_number`` so a batch is addressable as a unit for compare / summary.

    Namespaced ``agent_llm_eval_results`` so future ``agent_call_eval_results``
    / ``agent_tool_eval_results`` fit alongside without renaming.

    The typed snapshot columns (``llm_model``, ``llm_provider``,
    ``system_prompt``) + JSONB ``llm_settings_snapshot`` stamp the agent's
    config at run time so scores are attributable to a specific agent
    version even after the agent's live config changes.
    """

    __tablename__ = "agent_llm_eval_results"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "scenario_key", name="uq_agent_llm_eval_results_run_scenario"
        ),
        Index(
            "ix_agent_llm_eval_results_agent_run_desc",
            "agent_id",
            "run_number",
        ),
        Index("ix_agent_llm_eval_results_run_id", "run_id"),
        Index("ix_agent_llm_eval_results_agent_verdict", "agent_id", "verdict"),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_config_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_id = Column(UUID(as_uuid=True), nullable=False)
    run_number = Column(Integer, nullable=False)
    triggered_by = Column(String(32), nullable=False)  # 'cli' for MVP

    scenario_key = Column(String(120), nullable=False)
    scenario_tags = Column(JSONB, nullable=True)
    # Snapshot of ``AgentLlmEvalScenario.folder`` at run time. Preserved across
    # scenario edits/deletes. Bulk-renamed alongside the scenarios table when
    # a folder is renamed so the UI can group past runs under the current name.
    folder = Column(String(120), nullable=True)
    prompt = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)

    # Typed snapshot columns — pulled from agent_configs at run time so
    # a mid-run agent edit can't retroactively rewrite what was scored.
    llm_model = Column(String(120), nullable=True)
    llm_provider = Column(String(60), nullable=True)
    system_prompt = Column(Text, nullable=True)
    # Everything else the agent had configured (temperature, top_p, top_k,
    # max_tokens, …) — JSONB so new keys land here without a migration.
    llm_settings_snapshot = Column(JSONB, nullable=True)

    judge_model = Column(String(120), nullable=True)
    judge_engine = Column(String(32), nullable=True)  # 'deepeval' for MVP

    status = Column(String(16), nullable=False, default="completed")
    actual_answer = Column(Text, nullable=True)
    verdict = Column(String(16), nullable=True)  # PASS | PARTIAL | FAIL
    metric_scores = Column(JSONB, nullable=True)
    judge_reasoning = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    answer_error = Column(Text, nullable=True)
    judge_error = Column(Text, nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # v2 forward-compat — reserved for the (not yet built) tool/MCP-scoring
    # runner. ``execution_trace`` will store the ordered step-by-step trace
    # of what the agent actually did (tool calls, arguments, results);
    # ``tools_called`` will store the flat list for cheap ``expected vs
    # actual`` diffs against ``AgentLlmEvalScenario.expected_tools``. Both
    # stay ``NULL`` for every v1 row so existing writers/readers are
    # unchanged; wired up when the tool-scoring metric ships.
    execution_trace = Column(JSONB, nullable=True)
    tools_called = Column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "agent_config_id": str(self.agent_config_id) if self.agent_config_id else None,
            "run_id": str(self.run_id),
            "run_number": self.run_number,
            "triggered_by": self.triggered_by,
            "scenario_key": self.scenario_key,
            "scenario_tags": self.scenario_tags,
            "folder": self.folder,
            "prompt": self.prompt,
            "expected_answer": self.expected_answer,
            "llm_model": self.llm_model,
            "llm_provider": self.llm_provider,
            "system_prompt": self.system_prompt,
            "llm_settings_snapshot": self.llm_settings_snapshot,
            "judge_model": self.judge_model,
            "judge_engine": self.judge_engine,
            "status": self.status,
            "actual_answer": self.actual_answer,
            "verdict": self.verdict,
            "metric_scores": self.metric_scores or {},
            "judge_reasoning": self.judge_reasoning,
            "latency_ms": self.latency_ms,
            "answer_error": self.answer_error,
            "judge_error": self.judge_error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_trace": self.execution_trace,
            "tools_called": self.tools_called,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
