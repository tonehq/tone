from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi import Body
from core.models.voice import Voice
from core.middleware.auth import JWTClaims
from core.middleware.auth import require_org_member
from typing import Dict, Any

from core.database.session import get_db
from core.services.voice_service import VoiceService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()

@router.get("/get_voices")
def get_voices(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_voices()


@router.get("/get_voice_by_provider")
def get_voice(
    service_provider_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_voices_by_provider_id(service_provider_id)


@router.get("/get_languages_by_provider")
def get_languages_by_provider(
    service_provider_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_languages_by_provider_id(service_provider_id)


@router.get("/get_voices_by_language")
def get_voices_by_language(
    service_provider_id: int = Query(...),
    language: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_voices_by_language(service_provider_id, language)


@router.get("/get_voice_by_model_provider")
def get_voice_by_model_provider(
    model_provider_menu_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_voices_by_model_provider_menu_id(model_provider_menu_id)


@router.get("/get_languages_by_model_provider")
def get_languages_by_model_provider(
    model_provider_menu_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_languages_by_model_provider_menu_id(model_provider_menu_id)


@router.get("/get_voices_by_language_and_model_provider")
def get_voices_by_language_and_model_provider(
    model_provider_menu_id: int = Query(...),
    language: str = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).get_voices_by_language_and_model_provider(model_provider_menu_id, language)


@router.post("/upsert_voice")
def upsert_voice(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).upsert_voice(data)


@router.delete("/delete_voice")
def delete_voice(
    voice_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db)
):
    return VoiceService(db).delete_voice(voice_id)