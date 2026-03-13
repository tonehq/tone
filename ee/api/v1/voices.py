from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.voice_service import VoiceService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.get("/get_voices")
def get_voices(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db, org_id=UUID(claims.org_id)).get_voices()


@router.get("/get_voice_by_provider")
def get_voice(
    service_provider_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db, org_id=UUID(claims.org_id)).get_voices_by_provider_id(service_provider_id)


@router.post("/upsert_voice")
def upsert_voice(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db, org_id=UUID(claims.org_id)).upsert_voice(data)


@router.delete("/delete_voice")
def delete_voice(
    voice_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db, org_id=UUID(claims.org_id)).delete_voice(voice_id)
