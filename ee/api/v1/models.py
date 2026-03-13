from fastapi import APIRouter, Depends, Body, Query, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.model_service import ModelService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/get_models_by_provider", status_code=status.HTTP_200_OK)
def get_models_by_provider(
    service_provider_id: int = Query(..., description="The service provider ID to fetch models for"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ModelService(db, org_id=UUID(claims.org_id)).get_models_by_provider(service_provider_id)


@router.post("/upsert_model", status_code=status.HTTP_200_OK)
def upsert_model(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ModelService(db, org_id=UUID(claims.org_id)).upsert_model(data)


@router.delete("/delete_model", status_code=status.HTTP_200_OK)
def delete_model(
    model_id: int = Query(..., description="The model ID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ModelService(db, org_id=UUID(claims.org_id)).delete_model(model_id)
