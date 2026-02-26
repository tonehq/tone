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
from core.models.channel import Channel


class ChannelService(BaseService):
    CREATED_ATTRS = ("name", "type", "meta_data")
    UPDATABLE_ATTRS = ("name", "type", "meta_data")

    def upsert_channel(self, data: Dict[str, Any], created_by: int) -> Dict[str, Any]:
        if not data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )

        if not data.get("type"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="type is required",
            )

        meta_data = data.get("meta_data", {})
        if not isinstance(meta_data, dict):
            meta_data = {}
        data["meta_data"] = meta_data

        # Determine UUID
        channel_id = data.get("id")
        if channel_id is not None:
            existing = self.db.query(Channel).filter(Channel.id == int(channel_id)).first()
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
            channel_uuid = existing.uuid
        else:
            channel_uuid = uuid_lib.uuid4()

        now = int(time.time())
        values = {
            "uuid": channel_uuid,
            "name": data["name"],
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        # Add optional fields from allowlist
        for key in self.CREATED_ATTRS:
            if key in data and data[key] is not None:
                values[key] = data[key]

        try:
            self.upsert(
                model=Channel,
                values=values,
                conflict_fields=["uuid"],
                update_fields=[f for f in self.UPDATABLE_ATTRS if f in values],
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A channel with this name already exists",
            ) from e

        record = self.db.query(Channel).filter(Channel.uuid == channel_uuid).first()
        return self._response_item(record)

    def get_channel(self, channel_id: int) -> Dict[str, Any]:
        record = self.db.query(Channel).filter(Channel.id == channel_id).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        return self._response_item(record)

    def get_all_channels(self) -> List[Dict[str, Any]]:
        rows = self.db.query(Channel).order_by(Channel.id).all()
        return [self._response_item(row) for row in rows]

    def get_channel_by_type(self, channel_type: str) -> Dict[str, Any]:
        from core.models.enums import ChannelType

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

        record = self.db.query(Channel).filter(Channel.type == channel_enum).first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No channel found with type: {channel_type}",
            )

        return self._response_item(record)

    def delete_channel(self, channel_id: int) -> Dict[str, str]:
        record = self.db.query(Channel).filter(Channel.id == channel_id).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        self.db.delete(record)
        self.db.commit()

        return {"message": "Channel deleted successfully"}

    def get_or_create_channel_by_type(self, channel_type: str, meta_data: Optional[Dict[str, Any]] = None, created_by: Optional[int] = None) -> Channel:
        """Find an existing channel by type or create one. Returns the ORM object."""
        from core.models.enums import ChannelType

        # Normalize to enum name
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

        existing = self.db.query(Channel).filter(Channel.type == channel_enum).first()
        if existing:
            return existing

        # Create a new channel with type as the default name
        now = int(time.time())
        md = meta_data if isinstance(meta_data, dict) else {}

        channel = Channel(
            uuid=uuid_lib.uuid4(),
            name=channel_enum.value,
            type=channel_enum,
            created_by=created_by,
            meta_data=md,
            created_at=now,
            updated_at=now,
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def _response_item(self, record: Channel) -> Dict[str, Any]:
        return {
            "id": record.id,
            "uuid": str(record.uuid),
            "name": record.name,
            "type": record.type.value if record.type else None,
            "created_by": record.created_by,
            "meta_data": record.meta_data if isinstance(record.meta_data, dict) else {},
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
