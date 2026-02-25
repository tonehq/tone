from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.channel_service import ChannelService
from core.middleware.auth import require_org_member, require_admin_or_owner, JWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_channel(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    name = data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return ChannelService(db, user_id=claims.user_id).upsert_channel(
        data, created_by=claims.user_id
    )


@router.get("/list")
def get_all_channels(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, user_id=claims.user_id).get_all_channels()


@router.get("/get")
def get_channel(
    channel_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return ChannelService(db, user_id=claims.user_id).get_channel(channel_id)


@router.delete("/delete")
def delete_channel(
    channel_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return ChannelService(db, user_id=claims.user_id).delete_channel(channel_id)
