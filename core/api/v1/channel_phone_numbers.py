from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from core.database.session import get_db
from core.services.channel_phone_numbers_service import ChannelPhoneNumbersService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.get("/get_channel_phone_numbers", status_code=status.HTTP_200_OK)
def get_channel_phone_numbers(
    channel_id: int = Query(..., description="The channel ID to fetch phone numbers for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db).get_channel_phone_numbers(channel_id)


@router.post("/upsert_channel_phone_number", status_code=status.HTTP_200_OK)
def upsert_channel_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if not data.get("phone_number"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required",
        )
    if not data.get("phone_number_sid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number_sid is required",
        )
    if not data.get("phone_number_auth_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number_auth_token is required",
        )
    if not data.get("provider"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider is required",
        )
    return ChannelPhoneNumbersService(db).upsert_channel_phone_numbers(data)


@router.post("/detach_channel_phone_number", status_code=status.HTTP_200_OK)
def detach_channel_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if data.get("channel_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel_id is required",
        )
    if not data.get("phone_number"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required",
        )
    return ChannelPhoneNumbersService(db).detach_channel_phone_number(data)


@router.get("/get_twilio_phone_numbers", status_code=status.HTTP_200_OK)
def get_twilio_phone_numbers(
    type: str = Query(..., description="The channel type (e.g. twilio)"),
    channel_id: Optional[int] = Query(None, description="The channel ID to use for credentials"),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db).get_twilio_phone_numbers(
        channel_type=type,
        channel_id=channel_id,
    )
