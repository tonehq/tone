from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List
import time
import uuid as uuid_lib
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers
from core.models.channel import Channel


def _channel_phone_number_unique_constraint_detail(exc: IntegrityError) -> str:
    """Return a user-friendly message for AgentChannelPhoneNumbers unique constraint violations."""
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    constraint_name = None
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":
            if hasattr(orig, "diag") and orig.diag is not None:
                constraint_name = getattr(orig.diag, "constraint_name", None)
    if constraint_name is None and "agent_channel_phone_numbers_channel_phone_unique" in msg:
        constraint_name = "agent_channel_phone_numbers_channel_phone_unique"
    if constraint_name is None and "phone_number" in msg and "unique" in msg:
        return "Phone number already in use."
    if constraint_name == "agent_channel_phone_numbers_channel_phone_unique":
        return "This channel already has this phone number."
    if constraint_name and "phone_number" in (constraint_name or "").lower():
        return "Phone number already in use."
    if constraint_name and "uuid" in (constraint_name or "").lower():
        return "Duplicate channel phone number identifier (uuid)."
    if "unique" in msg or (orig and getattr(orig, "pgcode", None) == "23505"):
        return "A record with this value already exists. Please use a unique phone number."
    return "Unique constraint violated."


class AgentChannelPhoneNumbersService(BaseService):
    CREATED_ATTRS = (
        "channel_id", "agent_id", "phone_number", "phone_number_sid", "phone_number_auth_token",
        "provider", "country_code", "number_type", "capabilities", "status",
    )
    UPDATABLE_ATTRS = (
        "channel_id", "agent_id", "phone_number", "phone_number_sid", "phone_number_auth_token", "provider",
        "country_code", "number_type", "capabilities", "status", "updated_at",
    )

    def get_channel_phone_numbers(self, channel_id: int):
        channel = self.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )
        return (
            self.query(AgentChannelPhoneNumbers)
            .filter(
                AgentChannelPhoneNumbers.channel_id == channel_id,
                AgentChannelPhoneNumbers.status == "active",
            )
            .all()
        )

    def get_assigned_phone_numbers(self) -> List[Dict[str, Any]]:
        """Return all phone numbers that are assigned to an agent."""
        from core.models.agent import Agent

        try:
            rows = (
                self.query(AgentChannelPhoneNumbers)
                .join(Agent, AgentChannelPhoneNumbers.agent_id == Agent.id)
                .filter(AgentChannelPhoneNumbers.agent_id.isnot(None))
                .add_columns(Agent.name)
                .all()
            )
            return [
                {
                    "phone_number": cpn.phone_number,
                    "agent_id": cpn.agent_id,
                    "agent_name": agent_name,
                    "provider": cpn.provider,
                }
                for cpn, agent_name in rows
            ]
        except Exception:
            self.db.rollback()
            return []

    def detach_channel_phone_number(self, data: Dict[str, Any]):
        channel_id = int(data["channel_id"])
        phone_number = data["phone_number"].strip()
        agent_id = data.get("agent_id")

        channel = self.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        q = self.query(AgentChannelPhoneNumbers).filter(
            AgentChannelPhoneNumbers.channel_id == channel_id,
            AgentChannelPhoneNumbers.phone_number == phone_number,
        )
        if agent_id is not None:
            q = q.filter(AgentChannelPhoneNumbers.agent_id == int(agent_id))

        record = q.first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phone number not found for this channel",
            )

        self.db.delete(record)
        self.db.commit()
        return {"message": "Phone number detached from channel successfully"}

    def upsert_channel_phone_numbers(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Accepts phone_number as either:
          - a list of objects: [{"type": "twilio", "no": "+1..."}, ...]
          - a plain string: "+1..." (legacy, single entry)

        Shared fields (phone_number_sid, phone_number_auth_token, provider,
        country_code, number_type, capabilities, status, channel_id) apply to
        every entry in the list.
        """
        phone_number_raw = data.get("phone_number")

        # Normalise to list of {"no": str, "type": str} entries
        if isinstance(phone_number_raw, list):
            entries = phone_number_raw
        else:
            # Legacy string path
            provider_fallback = data.get("provider", "")
            entries = [{"no": str(phone_number_raw), "type": provider_fallback}]

        if not entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="phone_number is required",
            )

        results = []
        for entry in entries:
            number_str = entry.get("no", "").strip()
            if not number_str:
                continue
            # Per-entry provider falls back to the top-level provider field
            provider = entry.get("type") or data.get("provider", "")
            row_data = {
                **data,
                "phone_number": number_str,
                "provider": provider,
            }
            row = self._upsert_single(row_data)
            results.append({
                "id": row.id,
                "uuid": str(row.uuid),
                "phone_number": row.phone_number,
                "provider": row.provider,
                "channel_id": row.channel_id,
                "status": row.status,
            })

        return results

    # Keep old name as alias so any other callers don't break
    def upsert_channel_phone_number(self, data: Dict[str, Any]):
        return self.upsert_channel_phone_numbers(data)

    def _upsert_single(self, data: Dict[str, Any]) -> AgentChannelPhoneNumbers:
        """Upsert a single phone number row. phone_number must be a plain string here."""
        phone_number = data["phone_number"].strip()
        channel_id = data.get("channel_id")
        agent_id = data.get("agent_id")

        if channel_id is not None:
            channel = self.query(Channel).filter(Channel.id == int(channel_id)).first()
            if not channel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Channel not found",
                )

        if agent_id is not None:
            try:
                existing_assignment = (
                    self.query(AgentChannelPhoneNumbers)
                    .filter(
                        AgentChannelPhoneNumbers.phone_number == phone_number,
                        AgentChannelPhoneNumbers.agent_id.isnot(None),
                        AgentChannelPhoneNumbers.agent_id != int(agent_id),
                    )
                    .first()
                )
                if existing_assignment:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Phone number {phone_number} is already assigned to another agent.",
                    )
            except HTTPException:
                raise
            except Exception:
                self.db.rollback()

        row_id = data.get("id")
        row_uuid_raw = data.get("uuid")

        created_by = data.get("created_by")
        provider = data.get("provider")
        if created_by is not None and provider and row_id is None and row_uuid_raw is None:
            existing_by_creator = (
                self.query(AgentChannelPhoneNumbers)
                .join(Channel, AgentChannelPhoneNumbers.channel_id == Channel.id)
                .filter(
                    Channel.created_by == int(created_by),
                    AgentChannelPhoneNumbers.provider == provider,
                    AgentChannelPhoneNumbers.phone_number == phone_number,
                )
                .first()
            )
            if existing_by_creator:
                row_id = existing_by_creator.id

        if row_id is not None:
            existing = self.query(AgentChannelPhoneNumbers).filter(
                AgentChannelPhoneNumbers.id == int(row_id)
            ).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Channel phone number not found",
                )
            row_uuid = existing.uuid
        elif row_uuid_raw is not None:
            row_uuid = UUID(str(row_uuid_raw)) if isinstance(row_uuid_raw, str) else row_uuid_raw
        else:
            existing = self.query(AgentChannelPhoneNumbers).filter(
                AgentChannelPhoneNumbers.phone_number == phone_number
            ).first()
            if existing:
                row_uuid = existing.uuid
            else:
                row_uuid = uuid_lib.uuid4()

        now = int(time.time())
        values = {
            "uuid": row_uuid,
            "channel_id": int(channel_id) if channel_id is not None else None,
            "agent_id": int(agent_id) if agent_id is not None else None,
            "phone_number": phone_number,
            "phone_number_sid": data.get("phone_number_sid", ""),
            "phone_number_auth_token": data.get("phone_number_auth_token", ""),
            "provider": data.get("provider", ""),
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
                model=AgentChannelPhoneNumbers,
                values=values,
                conflict_fields=["uuid"],
                update_fields=list(self.UPDATABLE_ATTRS),
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            detail = _channel_phone_number_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e

        result = self.db.query(AgentChannelPhoneNumbers).filter(
            AgentChannelPhoneNumbers.uuid == row_uuid
        ).first()

        # Invalidate phone→agent cache when phone numbers are assigned/changed
        from core.services.redis_service import cache_delete_pattern
        cache_delete_pattern("phone_to_agent:*")

        return result