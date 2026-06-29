"""WorkflowService — org-level CRUD + draft/publish/validate for visual workflows."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from core.models.agent_config import AgentConfig
from core.models.enums import WorkflowStatus
from core.models.workflow import Workflow, WorkflowVersion
from core.services.base import BaseService
from core.services.workflow import schema as wf_schema
from core.services.workflow import vapi_adapter

# Draft rows always use version 0; published snapshots use 1, 2, 3, …
_DRAFT_VERSION = 0


def _checksum(graph: Dict[str, Any]) -> str:
    canonical = json.dumps(graph, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class WorkflowService(BaseService):
    # ── lookups ────────────────────────────────────────────────────────────
    def _get(self, workflow_id: str) -> Workflow:
        try:
            wid = UUID(str(workflow_id))
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        wf = (
            self.query(Workflow)
            .filter(Workflow.id == wid, Workflow.deleted_at.is_(None))
            .first()
        )
        if not wf:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        return wf

    def _version(self, version_id) -> Optional[WorkflowVersion]:
        if not version_id:
            return None
        return (
            self.query(WorkflowVersion)
            .filter(WorkflowVersion.id == version_id, WorkflowVersion.deleted_at.is_(None))
            .first()
        )

    def _agents_using(self, workflow_id: UUID) -> int:
        # Count DISTINCT agents — agent_configs are versioned, so a single agent can have
        # several config rows referencing the same workflow; without distinct this over-counts
        # (and could wrongly block delete for a workflow only referenced by a stale version).
        return (
            self.query(AgentConfig)
            .with_entities(AgentConfig.agent_id)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .distinct()
            .count()
        )

    # ── list / get ─────────────────────────────────────────────────────────
    def list(self) -> List[Dict[str, Any]]:
        rows = (
            self.query(Workflow)
            .filter(Workflow.deleted_at.is_(None))
            .order_by(Workflow.updated_at.desc())
            .all()
        )
        return [self.summary(wf) for wf in rows]

    def summary(self, wf: Workflow) -> Dict[str, Any]:
        draft = self._version(wf.draft_version_id)
        return {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "status": wf.status,
            "is_valid": bool(draft.is_valid) if draft else False,
            "agents_using": self._agents_using(wf.id),
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        }

    def detail(self, wf: Workflow) -> Dict[str, Any]:
        draft = self._version(wf.draft_version_id)
        published = self._version(wf.published_version_id)
        return {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "status": wf.status,
            "agents_using": self._agents_using(wf.id),
            "draft_version_id": str(wf.draft_version_id) if wf.draft_version_id else None,
            "published_version_id": str(wf.published_version_id) if wf.published_version_id else None,
            "latest_version": wf.latest_version,
            "graph": (draft.graph if draft else wf_schema.empty_graph()),
            "graph_checksum": draft.graph_checksum if draft else None,
            "is_valid": bool(draft.is_valid) if draft else False,
            "validation_errors": (draft.validation_errors or []) if draft else [],
            "has_published": published is not None,
            # True when the editable draft has diverged from the live published snapshot —
            # i.e. there are saved edits that are not live yet (compared by graph checksum).
            "has_unpublished_changes": bool(
                published and draft and draft.graph_checksum != published.graph_checksum
            ),
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        }

    def get(self, workflow_id: str) -> Dict[str, Any]:
        return self.detail(self._get(workflow_id))

    # ── create ─────────────────────────────────────────────────────────────
    def create(
        self,
        name: str,
        description: Optional[str],
        user_id: Optional[UUID],
        graph: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
        name = name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow name is required")

        # Friendly duplicate-name check (the DB unique constraint is the backstop below).
        existing = (
            self.query(Workflow)
            .filter(Workflow.name == name, Workflow.deleted_at.is_(None))
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'A workflow named "{name}" already exists. Choose a different name.',
            )

        graph = graph or wf_schema.empty_graph()
        size_err = wf_schema.graph_size_error(graph)
        if size_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=size_err)
        errors = wf_schema.validate_graph(graph)

        wf = Workflow(
            organization_id=self.org_id,
            name=name,
            description=description,
            status=WorkflowStatus.DRAFT.value,
            latest_version=0,
            created_by_user_id=user_id,
        )
        self.db.add(wf)

        draft = WorkflowVersion(
            organization_id=self.org_id,
            workflow_id=wf.id,
            version=_DRAFT_VERSION,
            is_draft=True,
            graph=graph,
            start_node_name=wf_schema.find_start_node_name(graph),
            graph_checksum=_checksum(graph),
            is_valid=(len(errors) == 0),
            validation_errors=errors,
            created_by_user_id=user_id,
        )

        try:
            self.db.flush()  # assign wf.id
            draft.workflow_id = wf.id
            self.db.add(draft)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'A workflow named "{name}" already exists. Choose a different name.',
            )
        wf.draft_version_id = draft.id
        self.db.commit()
        return self.detail(wf)

    # ── save draft ─────────────────────────────────────────────────────────
    def save_draft(
        self,
        workflow_id: str,
        graph: Dict[str, Any],
        expected_checksum: Optional[str],
        user_id: Optional[UUID],
    ) -> Dict[str, Any]:
        size_err = wf_schema.graph_size_error(graph)
        if size_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=size_err)
        wf = self._get(workflow_id)
        draft = self._version(wf.draft_version_id)
        if not draft:
            # Recover: create a draft if somehow missing.
            draft = WorkflowVersion(
                organization_id=self.org_id,
                workflow_id=wf.id,
                version=_DRAFT_VERSION,
                is_draft=True,
                graph=graph,
                created_by_user_id=user_id,
            )
            self.db.add(draft)
            self.db.flush()
            wf.draft_version_id = draft.id

        if expected_checksum and draft.graph_checksum and expected_checksum != draft.graph_checksum:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This workflow was changed elsewhere. Reload before saving.",
            )

        errors = wf_schema.validate_graph(graph)
        draft.graph = graph
        draft.start_node_name = wf_schema.find_start_node_name(graph)
        draft.graph_checksum = _checksum(graph)
        draft.is_valid = len(errors) == 0
        draft.validation_errors = errors
        self.db.commit()
        return self.detail(wf)

    # ── validate (no persistence) ──────────────────────────────────────────
    def validate(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        return wf_schema.validate_graph(graph)

    # ── publish ────────────────────────────────────────────────────────────
    def publish(self, workflow_id: str, user_id: Optional[UUID]) -> Dict[str, Any]:
        wf = self._get(workflow_id)
        draft = self._version(wf.draft_version_id)
        if not draft:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to publish")

        errors = wf_schema.validate_graph(draft.graph)
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Workflow has validation errors", "errors": errors},
            )

        wf.latest_version = (wf.latest_version or 0) + 1
        snapshot = WorkflowVersion(
            organization_id=self.org_id,
            workflow_id=wf.id,
            version=wf.latest_version,
            is_draft=False,
            graph=draft.graph,
            start_node_name=draft.start_node_name,
            graph_checksum=draft.graph_checksum,
            is_valid=True,
            validation_errors=[],
            published_at=datetime.now(timezone.utc),
            created_by_user_id=user_id,
        )
        self.db.add(snapshot)
        self.db.flush()
        wf.published_version_id = snapshot.id
        wf.status = WorkflowStatus.PUBLISHED.value
        self.db.commit()

        self._invalidate_assigned_agents(wf.id)
        return self.detail(wf)

    # ── versions / delete ──────────────────────────────────────────────────
    def list_versions(self, workflow_id: str) -> List[Dict[str, Any]]:
        wf = self._get(workflow_id)
        rows = (
            self.query(WorkflowVersion)
            .filter(
                WorkflowVersion.workflow_id == wf.id,
                WorkflowVersion.is_draft.is_(False),
                WorkflowVersion.deleted_at.is_(None),
            )
            .order_by(WorkflowVersion.version.desc())
            .all()
        )
        return [
            {
                "id": str(v.id),
                "version": v.version,
                "is_live": v.id == wf.published_version_id,
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v in rows
        ]

    def delete(self, workflow_id: str) -> Dict[str, Any]:
        wf = self._get(workflow_id)
        if self._agents_using(wf.id) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is assigned to one or more agents. Unassign it first.",
            )
        wf.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"success": True, "id": str(wf.id)}

    # ── Vapi import / export ───────────────────────────────────────────────
    def import_vapi(
        self,
        name: str,
        description: Optional[str],
        vapi_graph: Dict[str, Any],
        user_id: Optional[UUID],
    ) -> Dict[str, Any]:
        canonical = vapi_adapter.from_vapi(vapi_graph or {})
        return self.create(name=name, description=description, user_id=user_id, graph=canonical)

    def export_vapi(self, workflow_id: str) -> Dict[str, Any]:
        wf = self._get(workflow_id)
        published = self._version(wf.published_version_id)
        draft = self._version(wf.draft_version_id)
        graph = (published or draft).graph if (published or draft) else wf_schema.empty_graph()
        return vapi_adapter.to_vapi(graph)

    # ── helpers ────────────────────────────────────────────────────────────
    def _invalidate_assigned_agents(self, workflow_id: UUID) -> None:
        """Drop the pipeline cache for every agent assigned to this workflow."""
        try:
            from core.services.redis_service import cache_delete
        except Exception:
            return
        rows = (
            self.query(AgentConfig)
            .with_entities(AgentConfig.agent_id)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .distinct()
            .all()
        )
        for (agent_id,) in rows:
            try:
                cache_delete(f"agent_pipeline_config:{agent_id}")
            except Exception:
                pass
