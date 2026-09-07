from typing import Optional

from loguru import logger
from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class AgentLlmEvalScenario(OrgScopedModel):
    """A node in an agent's LLM-eval tree — either a ``folder`` or a
    ``scenario`` (Level-2 agent-LLM eval test case), discriminated by
    ``node_type`` and nested via the self-referential ``parent_id``
    (adjacency list). Folders were previously a separate
    ``agent_llm_eval_folders`` table; they now live here as ``node_type='folder'``
    rows so the folder tree and the scenarios it holds share one table.

    ``AgentLlmEvalService.run_eval_for_agent`` loads ``node_type='scenario'``
    rows, converts each into the in-memory ``LLMScenario`` used by the existing
    ``run_eval`` codepath, and never mutates the row — running an eval does NOT
    edit scenarios (scenarios are the input, results are the output).

    Scenarios may belong to a **version** (``version_id`` → ``agent_llm_eval_scenario_versions``):
    auto-generated scenarios are saved as ``approval_status='pending'`` under a
    draft version for review; approve keeps them (``approved``), reject deletes
    the row. Pre-existing / manual scenarios carry ``version_id=NULL`` and are
    always ``approved`` (no backfill).

    Hard-delete, not soft-delete: nodes are user-authored inputs. Deleting a
    folder cascades (``parent_id`` self-FK) to its children; the historical
    ``agent_llm_eval_results`` rows keep their own snapshotted
    ``prompt`` / ``expected_answer`` / ``folder`` so past runs remain
    explainable after their source scenario is gone.
    """

    __tablename__ = "agent_llm_eval_scenarios"
    __table_args__ = (
        # A scenario node must have a prompt; a folder node need not.
        CheckConstraint(
            "node_type = 'folder' OR prompt IS NOT NULL",
            name="ck_agent_llm_eval_scenarios_prompt_required",
        ),
        Index(
            "ix_agent_llm_eval_scenarios_agent_ord",
            "agent_id",
            "scenario_ord",
        ),
        Index("ix_agent_llm_eval_scenarios_parent", "parent_id"),
        Index("ix_agent_llm_eval_scenarios_version_id", "version_id"),
        # PG14-safe uniqueness (no NULLS NOT DISTINCT): split into partial
        # indexes whose predicates keep NULLs out of the indexed columns.
        Index(
            "uq_agent_llm_eval_scenarios_folder_root",
            "agent_id",
            "name",
            unique=True,
            postgresql_where=text("node_type = 'folder' AND parent_id IS NULL"),
        ),
        Index(
            "uq_agent_llm_eval_scenarios_folder_child",
            "agent_id",
            "parent_id",
            "name",
            unique=True,
            postgresql_where=text("node_type = 'folder' AND parent_id IS NOT NULL"),
        ),
        Index(
            "uq_agent_llm_eval_scenarios_versionless",
            "agent_id",
            "scenario_key",
            unique=True,
            postgresql_where=text("node_type = 'scenario' AND version_id IS NULL"),
        ),
        Index(
            "uq_agent_llm_eval_scenarios_versioned",
            "agent_id",
            "version_id",
            "scenario_key",
            unique=True,
            postgresql_where=text("node_type = 'scenario' AND version_id IS NOT NULL"),
        ),
    )

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 'scenario' (an eval test case) | 'folder' (a tree container node).
    node_type = Column(
        String(16), nullable=False, default="scenario", server_default="scenario"
    )

    # Adjacency-list parent. NULL = top level. For a scenario node this is its
    # containing folder node; for a folder node its parent folder (or NULL).
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_llm_eval_scenarios.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Folder display name (folder nodes only). Scenario nodes use scenario_key.
    name = Column(String(120), nullable=True)

    # Version this scenario belongs to (scenario nodes only). NULL = manual /
    # pre-existing (no version). Deleting the version cascades to its scenarios.
    version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_llm_eval_scenario_versions.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Review state for generated scenarios: 'pending' (awaiting approve/reject)
    # | 'approved' (counts for runs). Reject deletes the row, so 'rejected' is
    # never stored. Pre-existing / manual scenarios default to 'approved'.
    approval_status = Column(
        String(16), nullable=False, default="approved", server_default="approved"
    )

    # Stable per-agent slug — the join key that also lands on every
    # ``agent_llm_eval_results.scenario_key`` so a scenario's result history
    # survives an id change (e.g. re-import from CSV). NULL for folder nodes.
    scenario_key = Column(String(120), nullable=True)
    scenario_ord = Column(Integer, nullable=False, default=0)

    # Nullable so folder nodes need no prompt (guarded by the CHECK above).
    prompt = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    # GEval free-text rubrics. Empty → the corresponding metric is skipped
    # for this scenario even if globally enabled.
    persona_criteria = Column(Text, nullable=True)
    instruction_criteria = Column(Text, nullable=True)

    tags = Column(JSONB, nullable=True)

    # Read-only self-referential relationship — surfaces the parent folder
    # NAME to ``to_dict`` and the eval runner without a manual query. List
    # queries in the scenario service pair this with ``joinedload`` to avoid N+1.
    parent_ref = relationship(
        "AgentLlmEvalScenario",
        remote_side="AgentLlmEvalScenario.id",
        foreign_keys=[parent_id],
        lazy="select",
        viewonly=True,
    )

    version_ref = relationship(
        "AgentLlmEvalScenarioVersion",
        foreign_keys=[version_id],
        back_populates="scenarios",
    )

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
        # ``folder``/``folder_id`` are derived from the parent folder node for
        # FE back-compat (the FE still keys off folder_id + folder name). Falls
        # back to None if the parent relationship was never loaded (e.g. a
        # detached instance) rather than firing a lazy query on a closed session.
        folder_name: Optional[str] = None
        try:
            parent_row = self.parent_ref
            if parent_row is not None:
                folder_name = parent_row.name
        except Exception:  # noqa: BLE001 — detached / expired instance
            logger.debug(
                "[agent-llm-eval] scenario parent_ref unavailable (detached instance)"
            )
            folder_name = None
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "agent_id": str(self.agent_id),
            "node_type": self.node_type,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "name": self.name,
            "version_id": str(self.version_id) if self.version_id else None,
            "approval_status": self.approval_status,
            "scenario_key": self.scenario_key,
            "scenario_ord": self.scenario_ord,
            "prompt": self.prompt,
            "expected_answer": self.expected_answer,
            "persona_criteria": self.persona_criteria,
            "instruction_criteria": self.instruction_criteria,
            "tags": self.tags,
            # Back-compat aliases: folder_id == parent folder node id.
            "folder_id": str(self.parent_id) if self.parent_id else None,
            "folder": folder_name,
            "metrics_override": self.metrics_override,
            "threshold_override": self.threshold_override,
            "source": self.source,
            "generation_metadata": self.generation_metadata,
            "expected_tools": self.expected_tools,
            "tool_config": self.tool_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
