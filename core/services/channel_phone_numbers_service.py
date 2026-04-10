# Standard library
import time
import uuid as uuid_lib
from typing import Dict, Any, List, Optional

# SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# FastAPI
from fastapi import HTTPException, status

# Logging
from loguru import logger

# Local
from core.services.base import BaseService
from core.models.channel_phone_numbers import ChannelPhoneNumber
from core.models.channel import Channel
import requests


class ChannelPhoneNumbersService(BaseService):
    CREATED_ATTRS = (
        "channel_id", "phone_number", "phone_number_sid", "provider",
        "country_code", "number_type", "capabilities", "friendly_name", "status",
    )
    UPDATABLE_ATTRS = (
        "channel_id", "phone_number", "phone_number_sid", "provider",
        "country_code", "number_type", "capabilities", "friendly_name", "status",
    )

    def upsert_channel_phone_number(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

        channel_id = int(data["channel_id"])
        channel = self.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        model_id = data.get("id")
        model_uuid_raw = data.get("uuid")
        if model_id is not None:
            existing = self.query(ChannelPhoneNumber).filter(ChannelPhoneNumber.id == int(model_id)).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Channel phone number not found",
                )
            model_uuid = existing.uuid
        elif model_uuid_raw is not None:
            from uuid import UUID
            model_uuid = UUID(str(model_uuid_raw)) if isinstance(model_uuid_raw, str) else model_uuid_raw
        else:
            existing = self.query(ChannelPhoneNumber).filter(
                ChannelPhoneNumber.phone_number == data["phone_number"].strip(),
                ChannelPhoneNumber.channel_id == channel_id,
            ).first()
            model_uuid = existing.uuid if existing else uuid_lib.uuid4()

        now = int(time.time())
        values = {
            "uuid": model_uuid,
            "channel_id": channel_id,
            "phone_number": data["phone_number"].strip(),
            "phone_number_sid": data["phone_number_sid"],
            "provider": data["provider"],
            "created_at": now,
            "updated_at": now,
        }

        for key in self.CREATED_ATTRS:
            if key in values:
                continue
            if key in data and data[key] is not None:
                values[key] = data[key]

        if "status" not in values:
            values["status"] = "active"

        try:
            self.upsert(
                model=ChannelPhoneNumber,
                values=values,
                conflict_fields=["uuid"],
                update_fields=[f for f in self.UPDATABLE_ATTRS if f in values],
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A phone number with this value already exists for this channel.",
            ) from e

        record = self.db.query(ChannelPhoneNumber).filter(ChannelPhoneNumber.uuid == model_uuid).first()
        return self._response_item(record)

    def get_channel_phone_number(self, phone_number_id: int) -> Dict[str, Any]:
        record = self.query(ChannelPhoneNumber).filter(ChannelPhoneNumber.id == phone_number_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel phone number not found",
            )
        return self._response_item(record)

    def get_all_channel_phone_numbers(self, channel_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self.query(ChannelPhoneNumber).filter(ChannelPhoneNumber.status == "active")

        if channel_id is not None:
            query = query.filter(ChannelPhoneNumber.channel_id == channel_id)

        rows = query.order_by(ChannelPhoneNumber.id).all()
        return [self._response_item(row) for row in rows]

    def delete_channel_phone_number(self, phone_number_id: int) -> Dict[str, str]:
        record = self.query(ChannelPhoneNumber).filter(ChannelPhoneNumber.id == phone_number_id).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel phone number not found",
            )

        self.db.delete(record)
        self.db.commit()
        return {"message": "Channel phone number deleted successfully"}

    def get_twilio_phone_numbers(self, channel_type: str, channel_id: Optional[int] = None, agent_id: Optional[int] = None):
        print("into get_twilio_phone_numbers")
        from twilio.rest import Client
        from core.models.enums import ChannelType
        from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers

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

            print(f"channel_enum: {channel_enum}")
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
            q = self.query(AgentChannelPhoneNumbers).with_entities(AgentChannelPhoneNumbers.phone_number).filter(
                AgentChannelPhoneNumbers.agent_id.isnot(None),
            )
            if agent_id is not None:
                q = q.filter(AgentChannelPhoneNumbers.agent_id != agent_id)
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

    def _response_item(self, record: ChannelPhoneNumber) -> Dict[str, Any]:
        return {
            "id": record.id,
            "uuid": str(record.uuid),
            "channel_id": record.channel_id,
            "phone_number": record.phone_number,
            "phone_number_sid": record.phone_number_sid,
            "provider": record.provider,
            "country_code": record.country_code,
            "number_type": record.number_type,
            "capabilities": record.capabilities if isinstance(record.capabilities, dict) else {},
            "friendly_name": record.friendly_name,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
