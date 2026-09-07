from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.ingestion_pipeline_run import IngestionPipelineRun
from core.models.knowledge_base import KnowledgeBase
from core.models.upload import Upload
from core.utils.agent_scope import published_config_subquery


def resolve_active_run_id(
    db: Session,
    *,
    org_id: Any,
    upload_id: Any,
    agent_id: Optional[Any] = None,
) -> Optional[UUID]:
    if agent_id is not None:
        pinned = (
            db.query(AgentKnowledgeBase.active_ingestion_pipeline_run_id)
            .join(KnowledgeBase, KnowledgeBase.id == AgentKnowledgeBase.knowledge_base_id)
            .join(Agent, Agent.id == AgentKnowledgeBase.agent_id)
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.organization_id == org_id,
                AgentKnowledgeBase.agent_config_id == Agent.published_config_id,
                KnowledgeBase.upload_id == upload_id,
                AgentKnowledgeBase.active_ingestion_pipeline_run_id.isnot(None),
            )
            .scalar()
        )
        if pinned is not None:
            return pinned

    kb_default = (
        db.query(KnowledgeBase.active_ingestion_pipeline_run_id)
        .filter(
            KnowledgeBase.upload_id == upload_id,
            KnowledgeBase.organization_id == org_id,
            KnowledgeBase.active_ingestion_pipeline_run_id.isnot(None),
        )
        .scalar()
    )
    if kb_default is not None:
        return kb_default

    return (
        db.query(IngestionPipelineRun.id)
        .filter(
            IngestionPipelineRun.upload_id == upload_id,
            IngestionPipelineRun.organization_id == org_id,
            IngestionPipelineRun.is_active.is_(True),
        )
        .scalar()
    )


def _run_columns(db: Session):
    return db.query(
        IngestionPipelineRun.id,
        IngestionPipelineRun.organization_id,
        IngestionPipelineRun.embedding_dimensions,
    )


def runs_for_filters(db: Session, filters: dict) -> List[Any]:
    q = _run_columns(db)
    if filters.get("organization_id") is not None:
        q = q.filter(IngestionPipelineRun.organization_id == filters["organization_id"])
    if filters.get("ingestion_run_id") is not None:
        q = q.filter(IngestionPipelineRun.id == filters["ingestion_run_id"])
    if filters.get("upload_id") is not None:
        q = q.filter(IngestionPipelineRun.upload_id == filters["upload_id"])
    return q.all()


def scoped_runs(db: Session, filters: dict) -> List[Any]:
    org_id = filters.get("organization_id")
    upload_id = filters.get("upload_id")
    agent_id = filters.get("agent_id")
    run_id = filters.get("ingestion_run_id")
    q = _run_columns(db)
    if org_id is not None:
        q = q.filter(IngestionPipelineRun.organization_id == org_id)
    if filters.get("embedding_provider") is not None:
        q = q.filter(IngestionPipelineRun.embedding_provider == filters["embedding_provider"])
    if filters.get("embedding_model") is not None:
        q = q.filter(IngestionPipelineRun.embedding_model == filters["embedding_model"])
    if filters.get("embedding_dimensions") is not None:
        q = q.filter(IngestionPipelineRun.embedding_dimensions == int(filters["embedding_dimensions"]))
    if run_id is None and upload_id is not None and org_id is not None:
        run_id = resolve_active_run_id(db, org_id=org_id, upload_id=upload_id, agent_id=agent_id)
    if run_id is not None:
        q = q.filter(IngestionPipelineRun.id == run_id)
    else:
        q = q.filter(IngestionPipelineRun.is_active.is_(True))
        if upload_id is not None:
            q = q.filter(IngestionPipelineRun.upload_id == upload_id)
    if agent_id is not None:
        q = (
            q.join(Upload, Upload.id == IngestionPipelineRun.upload_id)
            .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .filter(
                AgentKnowledgeBase.agent_id == str(agent_id),
                AgentKnowledgeBase.agent_config_id == published_config_subquery(str(agent_id)),
                Upload.status == filters.get("status", "ready"),
            )
        )
    return q.all()
