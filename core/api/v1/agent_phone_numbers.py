from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.agent_phone_numbers_service import AgentPhoneNumbersService
from core.middleware.auth import require_org_member, JWTClaims

router = APIRouter()


@router.get("/get_agent_phone_numbers", status_code=status.HTTP_200_OK)
def get_agent_phone_numbers(
    agent_id: int = Query(..., description="The agent ID to fetch phone numbers for"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return AgentPhoneNumbersService(db).get_agent_phone_numbers(agent_id)


@router.post("/upsert_agent_phone_number", status_code=status.HTTP_200_OK)
def upsert_agent_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if data.get("agent_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required",
        )
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
    return AgentPhoneNumbersService(db).upsert_agent_phone_number(data)


@router.post("/detach_agent_phone_number", status_code=status.HTTP_200_OK)
def detach_agent_phone_number(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if data.get("agent_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required",
        )
    if not data.get("phone_number"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone_number is required",
        )
    return AgentPhoneNumbersService(db).detach_agent_phone_number(data)


@router.post("/get_twilio_phone_numbers", status_code=status.HTTP_200_OK)
def get_twilio_phone_numbers(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    if not data.get("account_sid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="account_sid is required",
        )
    if not data.get("auth_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth_token is required",
        )
    return AgentPhoneNumbersService(db).get_twilio_phone_numbers(
        account_sid=data["account_sid"],
        auth_token=data["auth_token"],
    )
