"""EE routes for the ``app_integrations`` catalog.

Mirrors :mod:`core.api.v1.app_integrations` but swaps the auth guards for the
EE multi-tenant equivalents. The Pydantic schemas, service, and response
formatter are imported from core — there is no schema duplication.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from core.api.v1.app_integrations import (
    CreateAppIntegrationRequest,
    UpdateAppIntegrationRequest,
    parse_list_args,
)
from core.database.session import get_db
from core.services.app_integration_service import AppIntegrationService
from ee.middleware.auth import require_ee_org_member


router = APIRouter()


def _get_service(claims, db: Session) -> AppIntegrationService:
    """Build a service bound to the EE caller's org + user."""
    user_id = UUID(str(claims.user_id)) if claims.user_id else None
    return AppIntegrationService(db, user_id=user_id, org_id=UUID(claims.org_id))


@router.post("/create_app_integration", status_code=status.HTTP_201_CREATED)
def create_app_integration(
    body: CreateAppIntegrationRequest,
    claims=Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Add a new integration to the global catalog. Any org member may create."""
    svc = _get_service(claims, db)
    integration = svc.create_app_integration(body.model_dump(exclude_unset=True))
    return svc.app_integration_response(integration)


@router.put("/update_app_integration", status_code=status.HTTP_200_OK)
def update_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    body: UpdateAppIntegrationRequest = Body(...),
    claims=Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Patch an existing integration. Any org member may update."""
    svc = _get_service(claims, db)
    integration = svc.update_app_integration(id, body.model_dump(exclude_unset=True))
    return svc.app_integration_response(integration)


@router.get("/get_app_integration")
def get_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    claims=Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Fetch a single integration by id. Any org member may read."""
    svc = _get_service(claims, db)
    integration = svc.get_app_integration(id)
    return svc.app_integration_response(integration)


@router.post("/list")
def list_app_integrations(
    data: Dict[str, Any] = Body(default={}),
    claims=Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """List integrations with optional search, filters, sort, and pagination.

    Same body contract as the core route. See
    :func:`core.api.v1.app_integrations.list_app_integrations` for details.
    """
    svc = _get_service(claims, db)
    return svc.list_app_integrations(**parse_list_args(data))


@router.delete("/delete_app_integration", status_code=status.HTTP_200_OK)
def delete_app_integration(
    id: UUID = Query(..., description="App integration UUID"),
    claims=Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Hard-delete a non-default integration. Any org member may delete."""
    svc = _get_service(claims, db)
    return svc.delete_app_integration(id)
