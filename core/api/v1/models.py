from fastapi import APIRouter, Depends, Body, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.model_service import ModelService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.post("/upsert_model", status_code=status.HTTP_200_OK)
def upsert_model(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create or update a model. Send id to update; send service_provider_id and name to create."""
    return ModelService(db).upsert_model(data)
