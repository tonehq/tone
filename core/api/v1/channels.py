from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.channel_service import ChannelService
from core.utils.auth_helpers import require_org_id

router = APIRouter()


def _svc(claims: JWTClaims, db: Session) -> ChannelService:
    return ChannelService(db, org_id=require_org_id(claims.org_id), user_id=claims.user_id)


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_channel(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if not data.get("name"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return _svc(claims, db).upsert_channel(data, created_by=claims.user_id)


@router.post("/list")
def list_channels(
    body: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).list_channels(
        channel_type=body.get("channel_type") or body.get("type"),
    )


@router.get("/all")
def get_all_channels(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Legacy unpaginated list. Prefer ``POST /list`` for new code."""
    return _svc(claims, db).get_all_channels()


@router.get("/get")
def get_channel(
    channel_id: str = Query(...),
    include_config: bool = Query(False),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).get_channel(channel_id, include_config=include_config)


@router.get("/get_by_type")
def get_channel_by_type(
    type: str = Query(..., description="Channel type slug (e.g. twilio, telnyx, exotel)"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).get_channel_by_type(type)


@router.get("/list_by_type")
def list_channels_by_type(
    type: str = Query(..., description="Channel type slug (e.g. twilio, telnyx, exotel)"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).get_channels_by_type(type)


@router.delete("/delete")
def delete_channel(
    channel_id: str = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _svc(claims, db).delete_channel(channel_id)
