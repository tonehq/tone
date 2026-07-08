"""Channel service — v2 schema.

A ``Channel`` row is a telephony or transport provider configuration
(``twilio``, ``telnyx``, ``exotel``, ``daily``, ``websocket``). The credential
payload lives encrypted in ``encrypted_config`` (JSONB).
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import requests
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import IntegrityError

from core.models.agent import Agent
from core.models.channel import Channel
from core.models.phone_number import PhoneNumber
from core.services.base import BaseService
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt_json, encrypt_json


def _extract_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pull a credential dict out of a request payload.

    Accepts the new shape (``config``) and the legacy shape (``meta_data``)
    so the controllers and the rest of the codebase can migrate gradually.
    """
    config = data.get("config")
    if isinstance(config, dict):
        return {k: v for k, v in config.items() if v not in (None, "")}
    meta_data = data.get("meta_data")
    if isinstance(meta_data, dict):
        return {k: v for k, v in meta_data.items() if v not in (None, "")}
    return {}


class ChannelService(BaseService):
    UPDATABLE_ATTRS = ("name", "channel_type", "encrypted_config")

    # ──────────────────────────────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────────────────────────────

    def upsert_channel(
        self,
        data: Dict[str, Any],
        created_by: Optional[Union[str, UUID]] = None,
    ) -> Dict[str, Any]:
        name = data.get("name")
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )

        channel_type = (data.get("channel_type") or data.get("type") or "").strip().lower()
        if not channel_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="channel_type is required",
            )

        config_payload = _extract_config(data)
        encrypted_config = encrypt_json(config_payload) if config_payload else None

        channel_id = coerce_uuid(data.get("id"))
        try:
            if channel_id:
                record = (
                    self.query(Channel).filter(Channel.id == channel_id).first()
                )
                if not record:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
                    )
                record.name = name
                record.channel_type = channel_type
                if encrypted_config is not None:
                    record.encrypted_config = encrypted_config
                self.db.commit()
                self.db.refresh(record)
            else:
                record = Channel(
                    organization_id=self.org_id,
                    name=name,
                    channel_type=channel_type,
                    encrypted_config=encrypted_config,
                )
                self.db.add(record)
                self.db.commit()
                self.db.refresh(record)
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A channel with this name already exists",
            ) from e

        return record.to_dict()

    def list_channels(
        self,
        channel_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return every channel in the org (no pagination)."""
        q = self.query(Channel)
        if channel_type:
            q = q.filter(Channel.channel_type == channel_type.strip().lower())
        items = q.order_by(Channel.updated_at.desc()).all()
        return [i.to_dict() for i in items]

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Legacy compatibility — returns every channel for this org."""
        rows = self.query(Channel).order_by(Channel.updated_at.desc()).all()
        return [row.to_dict() for row in rows]

    def get_channel(
        self,
        channel_id: Union[str, UUID],
        include_config: bool = False,
    ) -> Dict[str, Any]:
        record = self._get_record(channel_id)
        return record.to_dict(include_config=include_config)

    def get_channel_by_type(self, channel_type: str) -> Dict[str, Any]:
        slug = channel_type.strip().lower()
        record = (
            self.query(Channel)
            .filter(Channel.channel_type == slug)
            .order_by(Channel.updated_at.desc())
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No channel found with type: {channel_type}",
            )
        return record.to_dict()

    def get_channels_by_type(self, channel_type: str) -> List[Dict[str, Any]]:
        slug = channel_type.strip().lower()
        rows = (
            self.query(Channel)
            .filter(Channel.channel_type == slug)
            .order_by(Channel.updated_at.desc())
            .all()
        )
        return [row.to_dict() for row in rows]

    def delete_channel(self, channel_id: Union[str, UUID]) -> Dict[str, str]:
        record = self._get_record(channel_id)
        self.db.delete(record)
        self.db.commit()
        return {"message": "Channel deleted successfully"}

    def get_or_create_channel_by_type(
        self,
        channel_type: str,
        meta_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        created_by: Optional[Union[str, UUID]] = None,
        auto_commit: bool = True,
    ) -> Channel:
        """Find an existing channel of this type or create one with the supplied
        config. Returns the ORM record. Used by the bot runner."""
        slug = channel_type.strip().lower()
        existing = (
            self.query(Channel)
            .filter(Channel.channel_type == slug)
            .order_by(Channel.updated_at.desc())
            .first()
        )
        if existing:
            return existing

        payload = config or meta_data or {}
        encrypted_config = encrypt_json(payload) if payload else None

        record = Channel(
            organization_id=self.org_id,
            name=slug,
            channel_type=slug,
            encrypted_config=encrypted_config,
        )
        self.db.add(record)
        if auto_commit:
            self.db.commit()
            self.db.refresh(record)
        else:
            self.db.flush()
        return record

    def get_decrypted_config(self, channel: Channel) -> Dict[str, Any]:
        return decrypt_json(channel.encrypted_config)

    # ──────────────────────────────────────────────────────────────────────
    # Twilio: live IncomingPhoneNumber listing
    # ──────────────────────────────────────────────────────────────────────

    def list_twilio_phone_numbers(self, channel_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Fetch IncomingPhoneNumbers from Twilio for a Twilio channel, merged
        with local PhoneNumber rows so the UI can mark numbers already
        assigned to an agent in this org."""
        record = self._get_record(channel_id)
        if (record.channel_type or "").lower() != "twilio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel is not a Twilio channel",
            )

        config = decrypt_json(record.encrypted_config)
        account_sid = config.get("account_sid")
        auth_token = config.get("auth_token")
        if not account_sid or not auth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Twilio credentials are not configured for this channel",
            )

        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
        except ImportError as e:
            logger.exception("twilio SDK not installed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Twilio integration is unavailable on this server",
            ) from e

        try:
            client = Client(account_sid, auth_token)
            twilio_numbers = client.incoming_phone_numbers.list()
        except TwilioRestException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Twilio API error: {e.msg or str(e)}",
            ) from e
        except Exception as e:
            logger.exception("Unexpected error fetching Twilio phone numbers")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch phone numbers from Twilio",
            ) from e

        local_rows = (
            self.db.query(PhoneNumber, Agent.name.label("agent_name"))
            .outerjoin(Agent, Agent.id == PhoneNumber.agent_id)
            .filter(
                PhoneNumber.channel_id == record.id,
                PhoneNumber.organization_id == self.org_id,
            )
            .all()
        )
        assignments_by_number: Dict[str, Dict[str, Any]] = {}
        for pn, agent_name in local_rows:
            if pn.agent_id:
                assignments_by_number[pn.number] = {
                    "agent_id": str(pn.agent_id),
                    "agent_name": agent_name,
                }

        results: List[Dict[str, Any]] = []
        for n in twilio_numbers:
            number = getattr(n, "phone_number", None)
            if not number:
                continue
            results.append(
                {
                    "id": getattr(n, "sid", number),
                    "number": number,
                    "label": getattr(n, "friendly_name", None),
                    "channel_id": str(record.id),
                    "assigned_to": assignments_by_number.get(number),
                }
            )
        return results

    def list_telnyx_phone_numbers(self, channel_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Fetch phone numbers from Telnyx for a Telnyx channel, merged with
        local PhoneNumber rows so the UI can mark numbers already assigned to an
        agent in this org."""
        record = self._get_record(channel_id)
        if (record.channel_type or "").lower() != "telnyx":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel is not a Telnyx channel",
            )

        config = decrypt_json(record.encrypted_config)
        api_key = config.get("api_key")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telnyx credentials are not configured for this channel",
            )

        try:
            response = requests.get(
                "https://api.telnyx.com/v2/phone_numbers",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"page[size]": 250},
                timeout=15,
            )
            response.raise_for_status()
            telnyx_numbers = response.json().get("data", [])
        except requests.HTTPError as e:
            detail = "Telnyx API error"
            try:
                errors = response.json().get("errors") or []
                if errors:
                    detail = f"Telnyx API error: {errors[0].get('detail') or errors[0].get('title')}"
            except Exception:
                pass
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from e
        except Exception as e:
            logger.exception("Unexpected error fetching Telnyx phone numbers")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch phone numbers from Telnyx",
            ) from e

        local_rows = (
            self.db.query(PhoneNumber, Agent.name.label("agent_name"))
            .outerjoin(Agent, Agent.id == PhoneNumber.agent_id)
            .filter(
                PhoneNumber.channel_id == record.id,
                PhoneNumber.organization_id == self.org_id,
            )
            .all()
        )
        assignments_by_number: Dict[str, Dict[str, Any]] = {}
        for pn, agent_name in local_rows:
            if pn.agent_id:
                assignments_by_number[pn.number] = {
                    "agent_id": str(pn.agent_id),
                    "agent_name": agent_name,
                }

        results: List[Dict[str, Any]] = []
        for n in telnyx_numbers:
            number = n.get("phone_number")
            if not number:
                continue
            results.append(
                {
                    "id": n.get("id", number),
                    "number": number,
                    "label": n.get("customer_reference") or n.get("connection_name"),
                    "channel_id": str(record.id),
                    "assigned_to": assignments_by_number.get(number),
                }
            )
        return results

    # ──────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────

    def _get_record(self, channel_id: Union[str, UUID]) -> Channel:
        uid = coerce_uuid(channel_id)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="channel_id must be a valid UUID",
            )
        record = self.query(Channel).filter(Channel.id == uid).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )
        return record
