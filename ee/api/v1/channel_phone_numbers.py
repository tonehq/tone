from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from uuid import UUID

from core.database.session import get_db
from core.services.channel_phone_numbers_service import ChannelPhoneNumbersService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_channel_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    if not data.get("provider"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider is required",
        )
    if data.get("channel_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel_id is required",
        )
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).upsert_channel_phone_number(data)


@router.get("/list", status_code=status.HTTP_200_OK)
def get_all_channel_phone_numbers(
    channel_id: Optional[int] = Query(None, description="Filter by channel ID"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).get_all_channel_phone_numbers(channel_id=channel_id)


@router.get("/get_by_channel", status_code=status.HTTP_200_OK)
def get_phone_numbers_by_channel(
    channel_id: int = Query(..., description="The channel ID"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).get_all_channel_phone_numbers(channel_id=channel_id)


@router.get("/get", status_code=status.HTTP_200_OK)
def get_channel_phone_number(
    phone_number_id: int = Query(..., description="The phone number record ID"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).get_channel_phone_number(phone_number_id)


@router.delete("/delete", status_code=status.HTTP_200_OK)
def delete_channel_phone_number(
    phone_number_id: int = Query(..., description="The phone number record ID"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).delete_channel_phone_number(phone_number_id)


@router.get("/get_twilio_phone_numbers", status_code=status.HTTP_200_OK)
def get_twilio_phone_numbers(
    type: str = Query(..., description="The channel type (e.g. twilio)"),
    channel_id: Optional[int] = Query(None, description="The channel ID to use for credentials"),
    agent_id: Optional[int] = Query(None, description="Current agent ID — numbers assigned to other agents are excluded"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    print("into get_twilio_phone_numbers api")
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).get_twilio_phone_numbers(
        channel_type=type,
        channel_id=channel_id,
        agent_id=agent_id,
    )


@router.get("/get_phone_number_list_to_buy", status_code=status.HTTP_200_OK)
def get_phone_number_list_to_buy(
    type: str = Query(..., description="The channel type (e.g. twilio, exotel)"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).get_phone_number_list_to_buy(
        channel_type=type,
        user_id=claims.user_id,
    )


@router.post("/buy_phone_number", status_code=status.HTTP_200_OK)
def buy_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    if not data.get("phone_number"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required",
        )
    if not data.get("channel_name"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="channel_name is required",
        )
    return ChannelPhoneNumbersService(db, org_id=UUID(claims.org_id)).buy_phone_number(
        data=data,
        user_id=claims.user_id,
    )
