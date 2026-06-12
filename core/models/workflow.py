import uuid

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
    """Org-level, reusable node-based conversation workflow (a "pathway").

    Not owned by any single agent — an agent's live AgentConfig references it via
    ``workflow_id``. Holds pointers to its current editable draft version and the
    published version that goes live when assigned.
    """

    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_workflows_org_name"),
        Index("ix_workflows_organization_id", "organization_id"),
    )

    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(16), nullable=False, default="draft")  # draft | published

    published_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    draft_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    latest_version = Column(Integer, nullable=False, default=0)

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    versions = relationship(
        "WorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
        foreign_keys="WorkflowVersion.workflow_id",
    )
    published_version = relationship(
        "WorkflowVersion", foreign_keys=[published_version_id], post_update=True
    )
    draft_version = relationship(
        "WorkflowVersion", foreign_keys=[draft_version_id], post_update=True
    )


class WorkflowVersion(OrgScopedModel):
    """A snapshot of a workflow's graph. The single ``is_draft=True`` row is the
    editable working copy; ``is_draft=False`` rows are immutable published snapshots.

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
    version = Column(Integer, nullable=False)
    is_draft = Column(Boolean, nullable=False, default=True)

    graph = Column(
        JSONB,
        nullable=False,
        server_default=text("'{\"schemaVersion\": 1, \"nodes\": [], \"edges\": [], \"globalPrompt\": \"\"}'::jsonb"),
    )
    start_node_name = Column(String(120), nullable=True)
    graph_checksum = Column(String(64), nullable=True)
    is_valid = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONB, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", back_populates="versions", foreign_keys=[workflow_id])
