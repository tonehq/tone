from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any
import time
import uuid as uuid_lib
from uuid import UUID

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.agent_phone_numbers import AgentPhoneNumbers
from core.models.service_provider import ServiceProvider
from core.models.enums import AgentType
from core.services.agent_config_service import AgentConfigService

# Keys from request JSON to store in agent_config.agent_metadata
AGENT_METADATA_KEYS = (
    "custom_vocabulary",
    "filter_words",
    "realistic_filler_words",
    "language",
    "voice_speed",
    "patience_level",
    "speech_recognition",
    "call_recording",
    "call_transcription",
)


def _agent_unique_constraint_detail(exc: IntegrityError) -> str:
    """Return a user-friendly message for Agent unique constraint violations."""
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    constraint_name = None
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":  # unique_violation
            if hasattr(orig, "diag") and orig.diag is not None:
                constraint_name = getattr(orig.diag, "constraint_name", None)
    if constraint_name is None and "agent_name_unique" in msg:
        constraint_name = "agent_name_unique"
    if constraint_name == "agent_name_unique":
        return "An agent with this name already exists."
    if constraint_name and "uuid" in (constraint_name or "").lower():
        return "Duplicate agent identifier (uuid)."
    if "unique" in msg or (orig and getattr(orig, "pgcode", None) == "23505"):
        return "A record with this value already exists. Please use a unique name or identifier."
    return "Unique constraint violated."


class AgentService(BaseService):
    CREATED_ATTRS = (
        "name", "description", "is_public", "tags",
        "total_calls", "total_minutes", "average_rating",
        "meta_data", "status", "agent_type",
    )
    UPDATABLE_ATTRS = (
        "name", "description", "is_public", "tags",
        "total_calls", "total_minutes", "average_rating",
        "meta_data", "status", "agent_type",
    )

    def _normalize_agent_value(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        if key == "total_minutes" or key == "average_rating":
            try:
                return Decimal(str(value)) if value != "" else None
            except Exception:
                return None
        if key == "total_calls":
            try:
                return int(value) if value != "" else None
            except (TypeError, ValueError):
                return None
        if key == "agent_type":
            return self._normalize_agent_type(value)
        if key == "meta_data":
            return value if isinstance(value, dict) else None
        return value

    def _normalize_agent_type(self, value: Any) -> AgentType | None:
        """Accept int (0,1,2) or string (inbound, outbound, chatbot) and return AgentType."""
        if value is None:
            return None
        if isinstance(value, AgentType):
            return value
        if isinstance(value, int) and 0 <= value <= 2:
            return list(AgentType)[value]
        if isinstance(value, str) and value:
            name = value.strip().upper()
            for at in AgentType:
                if at.name == name or (getattr(at, "value", None) == value):
                    return at
        return None

    def upsert_agent(self, agent_data: Dict[str, Any], created_by: int):
        if not agent_data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )
        # description (if present) is for the agent only, not agent_config
        agent_id = agent_data.get("id")
        agent_uuid_raw = agent_data.get("uuid")
        if agent_id is not None:
            existing = self.db.query(Agent).filter(Agent.id == int(agent_id)).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found",
                )
            agent_uuid = existing.uuid
        elif agent_uuid_raw is not None:
            agent_uuid = UUID(str(agent_uuid_raw)) if isinstance(agent_uuid_raw, str) else agent_uuid_raw
        else:
            agent_uuid = uuid_lib.uuid4()
        now = int(time.time())
        values = {
            "uuid": agent_uuid,
            "name": agent_data["name"],
            "description": agent_data.get("description"),
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }
        for key in self.CREATED_ATTRS:
            if key == "name":
                continue
            if key in agent_data and agent_data[key] is not None and agent_data[key] != "":
                normalized = self._normalize_agent_value(key, agent_data[key])
                if normalized is not None:
                    values[key] = normalized
        if agent_id is None and "status" not in values:
            values["status"] = "active"
        update_fields = ["name", "description", "is_public", "tags", "updated_at"]
        for key in ("total_calls", "total_minutes", "average_rating", "meta_data", "status", "agent_type"):
            if key in values:
                update_fields.append(key)
        try:
            self.upsert(
                model=Agent,
                values=values,
                conflict_fields=["uuid"],
                update_fields=update_fields,
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        agent = self.db.query(Agent).filter(Agent.uuid == agent_uuid).first()

        # When id present: edit both agent and agent_config. When id absent: create agent then create agent_config.
        # Run config upsert when system_prompt is provided (create/update) or when html_prompt is provided (update).
        existing_config = self.db.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).first()
        if agent_data.get("system_prompt") or agent_data.get("html_prompt") is not None:
            config_data = self._build_agent_config_data(agent.id, agent_data, existing_config=existing_config)
            if existing_config:
                config_data["id"] = existing_config.id
                config_data["uuid"] = str(existing_config.uuid)
            AgentConfigService(self.db).upsert_agent_config(config_data)

        config = self.db.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).first()
        return self._agent_response_item(agent, config)

    def _agent_response_item(self, agent: Agent, config: Any) -> Dict[str, Any]:
        """Build response dict: agent + config as single flat object (no agent_config key)."""
        phone_rows = (
            self.db.query(AgentPhoneNumbers)
            .filter(AgentPhoneNumbers.agent_id == agent.id)
            .all()
        )

        item = {
            "id": agent.id,
            "uuid": str(agent.uuid),
            "name": agent.name,
            "description": agent.description,
            "is_public": agent.is_public,
            "tags": agent.tags,
            "total_calls": agent.total_calls,
            "total_minutes": float(agent.total_minutes) if agent.total_minutes is not None else None,
            "average_rating": float(agent.average_rating) if agent.average_rating is not None else None,
            "created_by": agent.created_by,
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "meta_data": agent.meta_data,
            "status": agent.status,
            "agent_type": agent.agent_type.value if agent.agent_type is not None else None,
            "phone_number": phone_rows[0].phone_number if phone_rows else None,
            "country_code": phone_rows[0].country_code if phone_rows else None,
            
        }
        # Phone numbers for this agent (phone_number and country_code only)

        # item["phone_numbers"] = [
        #     {"phone_number": p.phone_number, "country_code": p.country_code}
        #     for p in phone_rows
        # ]
        if config:
            agent_meta = config.agent_metadata if isinstance(config.agent_metadata, dict) else {}
            llm_meta = config.llm_metadata if isinstance(config.llm_metadata, dict) else {}
            tts_meta = config.tts_metadata if isinstance(config.tts_metadata, dict) else {}
            stt_meta = config.stt_metadata if isinstance(config.stt_metadata, dict) else {}
            item.update({
                "llm_service_id": config.llm_service_id,
                "tts_service_id": config.tts_service_id,
                "stt_service_id": config.stt_service_id,
                "llm_model_id": llm_meta.get("model_id"),
                "tts_model_id": tts_meta.get("model_id"),
                "stt_model_id": stt_meta.get("model_id"),
                "first_message": config.first_message,
                "system_prompt": config.system_prompt,
                "end_call_message": config.end_call_message,
                "voicemail_message": config.voicemail_message,
                "html_prompt": config.html_prompt,
                "config_status": config.status,
                **{k: agent_meta.get(k) for k in AGENT_METADATA_KEYS},
            })
        else:
            item["html_prompt"] = None
        return item

    def _build_agent_config_data(
        self, agent_id: int, data: Dict[str, Any], existing_config: AgentConfig | None = None
    ) -> Dict[str, Any]:
        """Build agent_config payload from combined request; agent_metadata from AGENT_METADATA_KEYS.
        When existing_config is set, use its values for any field not provided in data (so partial updates don't wipe fields).
        """
        def _get(key: str, default: Any = None) -> Any:
            if key in data and data[key] is not None:
                return data[key]
            if existing_config is not None:
                return getattr(existing_config, key, default)
            return default

        voicemail = data.get("voice_mail_message") or data.get("voicemail_message") or (existing_config.voicemail_message if existing_config else None)
        llm_model_id = data.get("llm_model_id")
        if llm_model_id is None and existing_config and isinstance(getattr(existing_config, "llm_metadata"), dict):
            llm_model_id = (existing_config.llm_metadata or {}).get("model_id")
        tts_model_id = data.get("tts_model_id")
        if tts_model_id is None and existing_config and isinstance(getattr(existing_config, "tts_metadata"), dict):
            tts_model_id = (existing_config.tts_metadata or {}).get("model_id")
        stt_model_id = data.get("stt_model_id") or data.get("stt_model_it")
        if stt_model_id is None and existing_config and isinstance(getattr(existing_config, "stt_metadata"), dict):
            stt_model_id = (existing_config.stt_metadata or {}).get("model_id")
        system_prompt = data.get("system_prompt")
        if system_prompt is None or system_prompt == "":
            system_prompt = (existing_config.system_prompt or "") if existing_config else ""
        html_prompt = data.get("html_prompt") if "html_prompt" in data else (existing_config.html_prompt if existing_config else None)
        agent_metadata = {k: data[k] for k in AGENT_METADATA_KEYS if k in data}
        if existing_config and isinstance(existing_config.agent_metadata, dict) and not agent_metadata:
            agent_metadata = existing_config.agent_metadata
        elif existing_config and isinstance(existing_config.agent_metadata, dict):
            merged = dict(existing_config.agent_metadata)
            merged.update(agent_metadata)
            agent_metadata = merged
        config_data = {
            "agent_id": agent_id,
            "llm_service_id": _get("llm_service_id"),
            "tts_service_id": _get("tts_service_id"),
            "stt_service_id": _get("stt_service_id"),
            "first_message": _get("first_message"),
            "system_prompt": system_prompt,
            "end_call_message": _get("end_call_message"),
            "voicemail_message": voicemail,
            "html_prompt": html_prompt,
            "llm_metadata": {"model_id": llm_model_id} if llm_model_id is not None else (existing_config.llm_metadata if existing_config else {}),
            "tts_metadata": {"model_id": tts_model_id} if tts_model_id is not None else (existing_config.tts_metadata if existing_config else {}),
            "stt_metadata": {"model_id": stt_model_id} if stt_model_id is not None else (existing_config.stt_metadata if existing_config else {}),
            "agent_metadata": agent_metadata,
        }
        return config_data

    def get_all_agents(self, agent_id=None, created_by=None):
        """Return all agents with joined agent_config and service_providers (llm, tts, stt). If agent_id is given, return only that agent."""
        from sqlalchemy.orm import aliased

        llm_provider = aliased(ServiceProvider)
        tts_provider = aliased(ServiceProvider)
        stt_provider = aliased(ServiceProvider)

        q = (
            self.db.query(Agent, AgentConfig, llm_provider, tts_provider, stt_provider)
            .outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
            .outerjoin(llm_provider, AgentConfig.llm_service_id == llm_provider.id)
            .outerjoin(tts_provider, AgentConfig.tts_service_id == tts_provider.id)
            .outerjoin(stt_provider, AgentConfig.stt_service_id == stt_provider.id)
        )
        if agent_id is not None:
            q = q.filter(Agent.id == agent_id)
        if created_by is not None:
            q = q.filter(Agent.created_by == created_by)
        rows = q.order_by(Agent.id).all()

        result = []
        for agent, config, llm_sp, tts_sp, stt_sp in rows:
            result.append(self._agent_response_item(agent, config))
        return result
