from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any
import time
import uuid as uuid_lib
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.agent_config import AgentConfig
from core.models.agent import Agent


def _agent_config_unique_constraint_detail(exc: IntegrityError) -> str:
    """Return a user-friendly message for AgentConfig unique constraint violations."""
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    constraint_name = None
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":
            if hasattr(orig, "diag") and orig.diag is not None:
                constraint_name = getattr(orig.diag, "constraint_name", None)
    if constraint_name is None and "agent_config_agent_id_unique" in msg:
        constraint_name = "agent_config_agent_id_unique"
    if constraint_name == "agent_config_agent_id_unique":
        return "Agent config already exists for this agent."
    if constraint_name and "uuid" in (constraint_name or "").lower():
        return "Duplicate agent config identifier (uuid)."
    if "unique" in msg or (orig and getattr(orig, "pgcode", None) == "23505"):
        return "A record with this value already exists."
    return "Unique constraint violated."


class AgentConfigService(BaseService):
    CREATED_ATTRS = (
        "agent_id", "llm_service_id", "tts_service_id", "stt_service_id",
        "first_message", "system_prompt", "end_call_message", "voicemail_message",
        "html_prompt", "status", "llm_metadata", "tts_metadata", "stt_metadata", "agent_metadata",
        "description",
    )
    UPDATABLE_ATTRS = (
        "llm_service_id", "tts_service_id", "stt_service_id",
        "first_message", "system_prompt", "end_call_message", "voicemail_message",
        "html_prompt", "status", "llm_metadata", "tts_metadata", "stt_metadata", "agent_metadata",
        "description", "updated_at",
    )

    def upsert_agent_config(self, config_data: Dict[str, Any]):
        if config_data.get("agent_id") is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agent_id is required",
            )
        if not config_data.get("system_prompt"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="system_prompt is required",
            )
        config_id = config_data.get("id")
        config_uuid_raw = config_data.get("uuid")
        agent_id = int(config_data["agent_id"])
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        if config_id is not None:
            existing = self.db.query(AgentConfig).filter(AgentConfig.id == int(config_id)).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent config not found",
                )
            config_uuid = existing.uuid
        elif config_uuid_raw is not None:
            config_uuid = UUID(str(config_uuid_raw)) if isinstance(config_uuid_raw, str) else config_uuid_raw
        else:
            config_uuid = uuid_lib.uuid4()
        now = int(time.time())
        values = {
            "uuid": config_uuid,
            "agent_id": agent_id,
            "system_prompt": config_data["system_prompt"],
            "created_at": now,
            "updated_at": now,
        }
        for key in self.CREATED_ATTRS:
            if key in ("agent_id", "system_prompt"):
                continue
            if key in config_data and config_data[key] is not None:
                values[key] = config_data[key]
        try:
            self.upsert(
                model=AgentConfig,
                values=values,
                conflict_fields=["uuid"],
                update_fields=list(self.UPDATABLE_ATTRS),
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_config_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        config = self.db.query(AgentConfig).filter(AgentConfig.uuid == config_uuid).first()
        return config
