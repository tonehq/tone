from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List, Optional
import time
import uuid as uuid_lib
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.channel_phone_numbers import ChannelPhoneNumbers
from core.models.channel import Channel
import requests


def _channel_phone_number_unique_constraint_detail(exc: IntegrityError) -> str:
    """Return a user-friendly message for ChannelPhoneNumbers unique constraint violations."""
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    constraint_name = None
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":
            if hasattr(orig, "diag") and orig.diag is not None:
                constraint_name = getattr(orig.diag, "constraint_name", None)
    if constraint_name is None and "channel_phone_numbers_channel_phone_unique" in msg:
        constraint_name = "channel_phone_numbers_channel_phone_unique"
    if constraint_name is None and "phone_number" in msg and "unique" in msg:
        return "Phone number already in use."
    if constraint_name == "channel_phone_numbers_channel_phone_unique":
        return "This channel already has this phone number."
    if constraint_name and "phone_number" in (constraint_name or "").lower():
        return "Phone number already in use."
    if constraint_name and "uuid" in (constraint_name or "").lower():
        return "Duplicate channel phone number identifier (uuid)."
    if "unique" in msg or (orig and getattr(orig, "pgcode", None) == "23505"):
        return "A record with this value already exists. Please use a unique phone number."
    return "Unique constraint violated."


class ChannelPhoneNumbersService(BaseService):
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
            self.query(ChannelPhoneNumbers)
            .filter(
                ChannelPhoneNumbers.channel_id == channel_id,
                ChannelPhoneNumbers.status == "active",
            )
            .all()
        )

    def get_assigned_phone_numbers(self) -> List[Dict[str, Any]]:
        """Return all phone numbers that are assigned to an agent."""
        from core.models.agent import Agent

        try:
            rows = (
                self.query(ChannelPhoneNumbers)
                .join(Agent, ChannelPhoneNumbers.agent_id == Agent.id)
                .filter(ChannelPhoneNumbers.agent_id.isnot(None))
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

        q = self.query(ChannelPhoneNumbers).filter(
            ChannelPhoneNumbers.channel_id == channel_id,
            ChannelPhoneNumbers.phone_number == phone_number,
        )
        if agent_id is not None:
            q = q.filter(ChannelPhoneNumbers.agent_id == int(agent_id))

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

    def _upsert_single(self, data: Dict[str, Any]) -> ChannelPhoneNumbers:
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
                    self.query(ChannelPhoneNumbers)
                    .filter(
                        ChannelPhoneNumbers.phone_number == phone_number,
                        ChannelPhoneNumbers.agent_id.isnot(None),
                        ChannelPhoneNumbers.agent_id != int(agent_id),
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
                self.query(ChannelPhoneNumbers)
                .join(Channel, ChannelPhoneNumbers.channel_id == Channel.id)
                .filter(
                    Channel.created_by == int(created_by),
                    ChannelPhoneNumbers.provider == provider,
                    ChannelPhoneNumbers.phone_number == phone_number,
                )
                .first()
            )
            if existing_by_creator:
                row_id = existing_by_creator.id

        if row_id is not None:
            existing = self.query(ChannelPhoneNumbers).filter(
                ChannelPhoneNumbers.id == int(row_id)
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
            existing = self.query(ChannelPhoneNumbers).filter(
                ChannelPhoneNumbers.phone_number == phone_number
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
                model=ChannelPhoneNumbers,
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

        return self.db.query(ChannelPhoneNumbers).filter(
            ChannelPhoneNumbers.uuid == row_uuid
        ).first()

    def get_twilio_phone_numbers(self, channel_type: str, channel_id: Optional[int] = None, agent_id: Optional[int] = None):
        from twilio.rest import Client
        from core.models.enums import ChannelType

        if channel_id is not None:
            channel = self.query(Channel).filter(Channel.id == channel_id).first()
            if not channel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No channel found with id: {channel_id}",
                )
        else:
            type_name = channel_type.strip().upper()
            channel_enum = None
            for ct in ChannelType:
                if ct.name == type_name:
                    channel_enum = ct
                    break
            if channel_enum is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid channel type: {channel_type}",
                )

            channel = (
                self.query(Channel)
                .filter(Channel.type == channel_enum)
                .first()
            )
            if not channel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No channel found with type: {channel_type}",
                )

        meta_data = channel.meta_data if isinstance(channel.meta_data, dict) else {}
        account_sid = meta_data.get("account_sid")
        auth_token = meta_data.get("auth_token")
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel meta_data is missing account_sid or auth_token",
            )

        try:
            client = Client(account_sid, auth_token)
            phone_numbers = client.incoming_phone_numbers.list()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch phone numbers from Twilio: {str(e)}",
            )

        try:
            q = self.query(ChannelPhoneNumbers).with_entities(ChannelPhoneNumbers.phone_number).filter(
                ChannelPhoneNumbers.agent_id.isnot(None),
            )
            if agent_id is not None:
                q = q.filter(ChannelPhoneNumbers.agent_id != agent_id)
            taken_numbers = {row[0] for row in q.all()}
        except Exception:
            self.db.rollback()
            taken_numbers = set()

        return [
            {
                "sid": number.sid,
                "phone_number": number.phone_number,
                "friendly_name": number.friendly_name,
                "voice": number.capabilities.get("voice"),
                "sms": number.capabilities.get("sms"),
                "status": number.status,
            }
            for number in phone_numbers
            if number.phone_number not in taken_numbers
        ]


    def get_phone_number_list_to_buy(self, channel_type: str, user_id: int):
        from core.models.enums import ChannelType
        from requests.auth import HTTPBasicAuth

        type_name = channel_type.strip().upper()
        channel_enum = None
        for ct in ChannelType:
            if ct.name == type_name:
                channel_enum = ct
                break
        if channel_enum is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channel type: {channel_type}",
            )

        channel = (
            self.query(Channel)
            .filter(Channel.type == channel_enum, Channel.created_by == user_id)
            .first()
        )
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No channel found with type: {channel_type} for the current user",
            )

        meta_data = channel.meta_data if isinstance(channel.meta_data, dict) else {}

        if channel_enum == ChannelType.TWILIO:
            account_sid = meta_data.get("account_sid")
            auth_token = meta_data.get("auth_token")
            if not account_sid or not auth_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Channel meta_data is missing account_sid or auth_token",
                )
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/AvailablePhoneNumbers/US/Local.json"
            auth = HTTPBasicAuth(account_sid, auth_token)

        elif channel_enum == ChannelType.EXOTEL:
            account_sid = meta_data.get("account_sid")
            api_key = meta_data.get("api_key")
            api_token = meta_data.get("api_token")
            if not account_sid or not api_key or not api_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Channel meta_data is missing account_sid, api_key, or api_token",
                )
            url = f"https://api.exotel.com/v2_beta/Accounts/{account_sid}/AvailablePhoneNumbers/SG/Landline"
            auth = HTTPBasicAuth(api_key, api_token)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone number purchase is not supported for channel type: {channel_type}",
            )

        try:
            response = requests.get(url, auth=auth)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch available phone numbers from {channel_type}: {str(e)}",
            )

        return response.json()


    def buy_phone_number(self, data: Dict[str, Any], user_id: int):
        from core.models.enums import ChannelType
        from requests.auth import HTTPBasicAuth

        phone_number = data["phone_number"].strip()
        channel_name = data["channel_name"].strip()

        # Find channel by name for the current user
        channel = (
            self.query(Channel)
            .filter(Channel.name == channel_name, Channel.created_by == user_id)
            .first()
        )
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No channel found with name: {channel_name} for the current user",
            )

        meta_data = channel.meta_data if isinstance(channel.meta_data, dict) else {}
        account_sid = meta_data.get("account_sid")

        if not account_sid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel meta_data is missing account_sid",
            )

        if channel.type == ChannelType.TWILIO:
            auth_token = meta_data.get("auth_token")
            if not auth_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Channel meta_data is missing auth_token",
                )
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json"
            auth = HTTPBasicAuth(account_sid, auth_token)

        elif channel.type == ChannelType.EXOTEL:
            api_key = meta_data.get("api_key")
            api_token = meta_data.get("api_token")
            if not api_key or not api_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Channel meta_data is missing api_key or api_token",
                )
            url = f"https://api.exotel.com/v1/Accounts/{account_sid}/IncomingPhoneNumbers"
            auth = HTTPBasicAuth(api_key, api_token)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone number purchase is not supported for channel type: {channel.type.value}",
            )

        try:
            response = requests.post(
                url,
                auth=auth,
                data={"PhoneNumber": phone_number},
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to buy phone number from {channel.type.value}: {str(e)}",
            )

        return response.json()