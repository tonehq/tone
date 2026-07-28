from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.models.base import OrgScopedModel


class AgentKnowledgeBase(OrgScopedModel):
    __tablename__ = "agent_knowledge_bases"
    __table_args__ = (
        UniqueConstraint("agent_config_id", "knowledge_base_id", name="uq_agent_kb_config_kb"),
    )

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    knowledge_base_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    agent_config_id = Column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False)
    # Per-agent pin: overrides ``knowledge_bases.active_ingestion_pipeline_run_id``
    # for this specific agent. NULL means "follow the KB default".
    # Resolution order lives in ``IngestionRunService.resolve_active_run_id``.
    active_ingestion_pipeline_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    active_run = relationship(
        "IngestionPipelineRun",
        foreign_keys=[active_ingestion_pipeline_run_id],
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "knowledge_base_id": str(self.knowledge_base_id),
            "agent_config_id": str(self.agent_config_id) if self.agent_config_id else None,
            "active_ingestion_pipeline_run_id": (
                str(self.active_ingestion_pipeline_run_id)
                if self.active_ingestion_pipeline_run_id
                else None
            ),
        }
