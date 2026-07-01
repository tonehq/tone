"""Workflow CRUD API — org-level visual conversation workflows ("pathways").

Assignment of a workflow to an agent lives on the agent router (``AgentConfigRequest``
``mode`` + ``workflow_id``); this router owns the workflow lifecycle itself.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.workflow.service import WorkflowService
from shared.config import settings

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class SaveDraftRequest(BaseModel):
    workflow_id: str
    graph: Dict[str, Any]
    expected_checksum: Optional[str] = None


class ValidateRequest(BaseModel):
    graph: Dict[str, Any]


class PublishRequest(BaseModel):
    workflow_id: str


class CloneWorkflowRequest(BaseModel):
    workflow_id: str
    name: Optional[str] = Field(None, min_length=1, max_length=200)


class ImportVapiRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    graph: Dict[str, Any]


def _get_service(claims: JWTClaims, db: Session) -> WorkflowService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return WorkflowService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/list")
def list_workflows(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    return _get_service(claims, db).list()


@router.post("/create", status_code=status.HTTP_201_CREATED)
def create_workflow(
    body: CreateWorkflowRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return svc.create(body.name, body.description, user_id)


@router.get("/get")
def get_workflow(
    workflow_id: str = Query(..., description="The workflow id to fetch"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get(workflow_id)


@router.post("/save_draft")
def save_draft(
    body: SaveDraftRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return svc.save_draft(body.workflow_id, body.graph, body.expected_checksum, user_id)


@router.post("/validate")
def validate_workflow(
    body: ValidateRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    issues = _get_service(claims, db).validate(body.graph)
    return {"is_valid": len(issues) == 0, "errors": issues}


@router.post("/publish")
def publish_workflow(
    body: PublishRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return svc.publish(body.workflow_id, user_id)


@router.post("/clone", status_code=status.HTTP_201_CREATED)
def clone_workflow(
    body: CloneWorkflowRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return svc.clone(body.workflow_id, user_id, body.name)


@router.get("/list_versions")
def list_versions(
    workflow_id: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_versions(workflow_id)


@router.delete("/delete", status_code=status.HTTP_200_OK)
def delete_workflow(
    workflow_id: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete(workflow_id)


@router.post("/import_vapi", status_code=status.HTTP_201_CREATED)
def import_vapi(
    body: ImportVapiRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    user_id = UUID(claims.user_id) if claims.user_id else None
    return svc.import_vapi(body.name, body.description, body.graph, user_id)


@router.get("/export_vapi")
def export_vapi(
    workflow_id: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).export_vapi(workflow_id)
