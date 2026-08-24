from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.models.base import OrgScopedModel


class CallTranscriptEvalResult(OrgScopedModel):
    """One DeepEval-scored transcript for a real (completed) call — the
    post-call analogue of :class:`AgentLlmEvalResult`.

    v1 is full-call only: one row per call, ``mode='full_call'``. The
    per-turn mode is reserved (see ``turn_number``) so the same table
    covers both when the per-turn runner ships.

    Snapshot columns (``llm_model``, ``llm_provider``, ``system_prompt``,
    ``chatbot_role``) are stamped at scoring time so a config edit AFTER the
    call cannot retroactively rewrite what was scored. ``chatbot_role`` is
    the first 200 chars of the system prompt — the ``RoleAdherenceMetric``
    consumes it, so we snapshot it explicitly instead of re-clipping on read.
    """

    __tablename__ = "call_transcript_eval_results"
    __table_args__ = (
        Index("ix_call_transcript_eval_results_call_id", "call_id"),
        Index(
            "ix_call_transcript_eval_results_agent_verdict",
            "agent_id",
            "verdict",
        ),
        Index(
            "ix_call_transcript_eval_results_call_mode",
            "call_id",
            "mode",
        ),
    )

    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
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
    # 'full_call' (v1) | 'per_turn' (v2 reserved)
    mode = Column(String(16), nullable=False, default="full_call")
    turn_number = Column(Integer, nullable=True)

    # Snapshot — see class docstring.
    llm_model = Column(String(120), nullable=True)
    llm_provider = Column(String(60), nullable=True)
    system_prompt = Column(Text, nullable=True)
    chatbot_role = Column(String(400), nullable=True)

    judge_model = Column(String(120), nullable=True)
    judge_engine = Column(String(32), nullable=True)  # 'deepeval'

    # 'completed' | 'failed' — 'completed' also covers skip rows (see
    # ``skip_reason``); a skip is a completed no-op, not a failure.
    status = Column(String(16), nullable=False, default="completed")
    verdict = Column(String(16), nullable=True)  # PASS | PARTIAL | FAIL
    metric_scores = Column(JSONB, nullable=True)
    judge_reasoning = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    judge_error = Column(Text, nullable=True)
    # 'no_transcript' | 'auto_run_off' | 'already_scored' | …
    skip_reason = Column(String(120), nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # v2 forward-compat — reserved for tool / RAG / MCP-aware scoring. All
    # three stay NULL for every v1 row so existing writers/readers are
    # unchanged; wired up when the tool / RAG / MCP metrics ship.
    tool_trace = Column(JSONB, nullable=True)
    rag_context = Column(JSONB, nullable=True)
    mcp_context = Column(JSONB, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "call_id": str(self.call_id),
            "agent_id": str(self.agent_id),
            "agent_config_id": (
                str(self.agent_config_id) if self.agent_config_id else None
            ),
            "mode": self.mode,
            "turn_number": self.turn_number,
            "llm_model": self.llm_model,
            "llm_provider": self.llm_provider,
            "system_prompt": self.system_prompt,
            "chatbot_role": self.chatbot_role,
            "judge_model": self.judge_model,
            "judge_engine": self.judge_engine,
            "status": self.status,
            "verdict": self.verdict,
            "metric_scores": self.metric_scores or {},
            "judge_reasoning": self.judge_reasoning,
            "latency_ms": self.latency_ms,
            "judge_error": self.judge_error,
            "skip_reason": self.skip_reason,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "reserved": {
                "tool_trace": self.tool_trace,
                "rag_context": self.rag_context,
                "mcp_context": self.mcp_context,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
