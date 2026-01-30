from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any
import time
import uuid as uuid_lib
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.agent_phone_numbers import AgentPhoneNumbers
from core.models.agent import Agent


def _agent_phone_number_unique_constraint_detail(exc: IntegrityError) -> str:
    """Return a user-friendly message for AgentPhoneNumbers unique constraint violations."""
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    constraint_name = None
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":
            if hasattr(orig, "diag") and orig.diag is not None:
                constraint_name = getattr(orig.diag, "constraint_name", None)
    if constraint_name is None and "agent_phone_numbers_agent_phone_unique" in msg:
        constraint_name = "agent_phone_numbers_agent_phone_unique"
    if constraint_name is None and "phone_number" in msg and "unique" in msg:
        return "Phone number already in use."
    if constraint_name == "agent_phone_numbers_agent_phone_unique":
        return "This agent already has this phone number."
    if constraint_name and "phone_number" in (constraint_name or "").lower():
        return "Phone number already in use."
    if constraint_name and "uuid" in (constraint_name or "").lower():
        return "Duplicate agent phone number identifier (uuid)."
    if "unique" in msg or (orig and getattr(orig, "pgcode", None) == "23505"):
        return "A record with this value already exists. Please use a unique phone number."
    return "Unique constraint violated."


class AgentPhoneNumbersService(BaseService):
    CREATED_ATTRS = (
        "agent_id", "phone_number", "phone_number_sid", "phone_number_auth_token",
        "provider", "country_code", "number_type", "capabilities", "status",
    )
    UPDATABLE_ATTRS = (
        "phone_number", "phone_number_sid", "phone_number_auth_token", "provider",
        "country_code", "number_type", "capabilities", "status", "updated_at",
    )

    def upsert_agent_phone_number(self, data: Dict[str, Any]):
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
        row_id = data.get("id")
        row_uuid_raw = data.get("uuid")
        agent_id = int(data["agent_id"])
        phone_number = data["phone_number"].strip()
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        if row_id is not None:
            existing = self.db.query(AgentPhoneNumbers).filter(AgentPhoneNumbers.id == int(row_id)).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent phone number not found",
                )
            row_uuid = existing.uuid
        elif row_uuid_raw is not None:
            row_uuid = UUID(str(row_uuid_raw)) if isinstance(row_uuid_raw, str) else row_uuid_raw
        else:
            existing = self.db.query(AgentPhoneNumbers).filter(
                AgentPhoneNumbers.phone_number == phone_number
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number already in use",
                )
            row_uuid = uuid_lib.uuid4()
        now = int(time.time())
        values = {
            "uuid": row_uuid,
            "agent_id": agent_id,
            "phone_number": phone_number,
            "phone_number_sid": data["phone_number_sid"],
            "phone_number_auth_token": data["phone_number_auth_token"],
            "provider": data["provider"],
            "created_at": now,
            "updated_at": now,
        }
        for key in self.CREATED_ATTRS:
            if key in values:
                continue
            if key in data and data[key] is not None and data[key] != "":
                values[key] = data[key]
        try:
            self.upsert(
                model=AgentPhoneNumbers,
                values=values,
                conflict_fields=["uuid"],
                update_fields=list(self.UPDATABLE_ATTRS),
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_phone_number_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        row = self.db.query(AgentPhoneNumbers).filter(AgentPhoneNumbers.uuid == row_uuid).first()
        return row
