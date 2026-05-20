from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.channel_service import ChannelService
from ee.middleware.auth import require_ee_org_member, require_ee_admin_or_owner, EEJWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_channel(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    name = data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return ChannelService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).upsert_channel(
        data, created_by=claims.user_id
    )


@router.get("/list")
def get_all_channels(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_all_channels()


@router.get("/get")
def get_channel(
    channel_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_channel(channel_id)


@router.get("/get_by_type")
def get_channel_by_type(
    type: str = Query(..., description="The channel type (e.g. twilio, web, google_meet, zoom)"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, org_id=UUID(claims.org_id)).get_channel_by_type(type)


@router.get("/list_by_type")
def list_channels_by_type(
    type: str = Query(..., description="The channel type (e.g. twilio, web, google_meet, zoom)"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).get_channels_by_type(type)


@router.delete("/delete")
def delete_channel(
    channel_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_admin_or_owner),
    db: Session = Depends(get_db),
):
    return ChannelService(db, org_id=UUID(claims.org_id), user_id=claims.user_id).delete_channel(channel_id)
