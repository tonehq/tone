from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.agent_channel_phone_numbers_service import AgentChannelPhoneNumbersService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.get("/get_channel_phone_numbers", status_code=status.HTTP_200_OK)
def get_channel_phone_numbers(
    channel_id: int = Query(..., description="The channel ID to fetch phone numbers for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return AgentChannelPhoneNumbersService(db).get_channel_phone_numbers(channel_id)


@router.post("/upsert_channel_phone_number", status_code=status.HTTP_200_OK)
def upsert_channel_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    print("data", data)
    if not data.get("phone_number"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required",
        )
    if not data.get("provider"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider is required",
        )
    return AgentChannelPhoneNumbersService(db).upsert_channel_phone_numbers(data)


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
    return AgentChannelPhoneNumbersService(db).detach_channel_phone_number(data)


@router.get("/get_assigned_phone_numbers", status_code=status.HTTP_200_OK)
def get_assigned_phone_numbers(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return AgentChannelPhoneNumbersService(db).get_assigned_phone_numbers()