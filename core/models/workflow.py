from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class Workflow(OrgScopedModel):
    """Agent-owned node-based conversation workflow (a "pathway").

    Owned by the agent in ``agent_id``; each agent version (AgentConfig) references
    its own independent copy via ``workflow_id`` — creating a new agent version
    deep-copies the workflow so edits on one version never leak into another.
    ``agent_id IS NULL`` marks legacy org-level rows from before agent scoping.

    Workflows have no publish step of their own: ``version_id`` points at the single
    working graph, which is what a call uses. The agent version's own publish is the
    real "go live" gate.
    """

    __tablename__ = "workflows"
    __table_args__ = (
        # Partial unique index: name uniqueness only applies to legacy org-level
        # rows — per-agent-version copies intentionally share names.
        Index(
            "uq_workflows_org_name",
            "organization_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND agent_id IS NULL"),
        ),
        Index("ix_workflows_organization_id", "organization_id"),
        Index("ix_workflows_agent_id", "agent_id"),
    )

    name = Column(String(200), nullable=False)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    description = Column(String(500), nullable=True)

    # Pointer to the single working graph (the column is still named
    # ``draft_version_id`` for migration stability; there is no separate published
    # version anymore).
    draft_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    versions = relationship(
        "WorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
        foreign_keys="WorkflowVersion.workflow_id",
    )
    draft_version = relationship(
        "WorkflowVersion", foreign_keys=[draft_version_id], post_update=True
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "name": self.name,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "description": self.description,
            "draft_version_id": str(self.draft_version_id) if self.draft_version_id else None,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowVersion(OrgScopedModel):
    """The single working graph for a workflow (one row per workflow).

    The ``graph`` JSONB is the canonical React-Flow-native graph
    (``{schemaVersion, nodes, edges, globalPrompt, artifactPlan}``) with the Vapi
    field set nested inside each ``node.data`` and ``edge.data.condition``.
    """

    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "version", name="uq_workflow_versions_workflow_version"),
        Index("ix_workflow_versions_workflow_id", "workflow_id"),
        Index("ix_workflow_versions_graph_gin", "graph", postgresql_using="gin"),
    )

    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False, default=0)

    graph = Column(
        JSONB,
        nullable=False,
        server_default=text("'{\"schemaVersion\": 1, \"nodes\": [], \"edges\": [], \"globalPrompt\": \"\"}'::jsonb"),
    )
    start_node_name = Column(String(120), nullable=True)
    graph_checksum = Column(String(64), nullable=True)
    is_valid = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONB, nullable=True)

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", back_populates="versions", foreign_keys=[workflow_id])

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "version": self.version,
            "graph": self.graph,
            "start_node_name": self.start_node_name,
            "graph_checksum": self.graph_checksum,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
            "created_by_user_id": str(self.created_by_user_id) if self.created_by_user_id else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
