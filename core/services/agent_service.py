from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, Iterable, List, Optional, Tuple
import secrets
import time
import uuid as uuid_lib
from uuid import UUID
import traceback

from fastapi import HTTPException, status

from core.services.audit_actions import AgentAuditAction, AuditResourceType
from core.services.base import BaseService
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.model import Model
# Note: legacy methods that referenced removed models (ServiceProvider,
# Account, ModelInstance, AgentChannel, AgentChannelPhoneNumbers, the
# AgentType enum) — `upsert_agent`, `_agent_response_item`, `duplicate_agent`,
# the old `get_all_agents`, and several helpers — remain in this file as
# dead code and will NameError if called. They are no longer wired into any
# HTTP route and should be removed in a follow-up cleanup.
from core.services.agent_config_service import AgentConfigService
from core.services.channel_service import ChannelService
from core.services.meta_data_schema_validator import MetaDataSchemaValidator
from core.services.webrtc import supported_providers
from core.models.agent_tool import AgentTool
from core.models.agent_mcp_server import AgentMcpServer
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.agent_channel import AgentChannel
from core.models.channel import Channel
from core.models.knowledge_base import KnowledgeBase
from core.models.phone_number import PhoneNumber
from core.models.tool import Tool
from core.models.mcp_server import McpServer
from core.models.upload import Upload

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
    """Return a user-friendly message for Agent integrity-error violations.

    Distinguishes unique-violation (23505) from foreign-key-violation (23503)
    and not-null (23502). FK violations used to be reported as
    "Unique constraint violated." which made e.g. an unknown model id look
    like a duplicate-name issue.
    """
    msg = str(exc).lower()
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) if orig is not None else None
    constraint_name = None
    if orig is not None and hasattr(orig, "diag") and orig.diag is not None:
        constraint_name = getattr(orig.diag, "constraint_name", None)

    # Foreign-key violation: a referenced row doesn't exist.
    if pgcode == "23503" or "foreign key" in msg:
        if constraint_name and "knowledge_model" in constraint_name:
            return "Selected knowledge embedding model does not exist."
        if constraint_name and "language" in constraint_name:
            return "Selected language does not exist."
        return "A referenced record could not be found. Check your selections and try again."

    # Not-null violation.
    if pgcode == "23502":
        return "A required field is missing."

    # Unique violation: the legacy path.
    if constraint_name is None and "agent_name_unique" in msg:
        constraint_name = "agent_name_unique"
    if constraint_name == "agent_name_unique":
        return "An agent with this name already exists."
    if constraint_name and "uuid" in constraint_name.lower():
        return "Duplicate agent identifier (uuid)."
    if pgcode == "23505" or "unique" in msg:
        return "A record with this value already exists. Please use a unique name or identifier."

    return "Database constraint violated."


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

    # Note: the AgentType return annotation is a string forward-reference
    # because the underlying enum was removed in the dev-branch refactor.
    # This method is only called by `_normalize_agent_value` from the legacy
    # `upsert_agent` flow, which is no longer reachable via any HTTP route.
    def _normalize_agent_type(self, value: Any) -> "AgentType | None":  # noqa: F821
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
            existing = self.query(Agent).filter(Agent.id == int(agent_id)).first()
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
            "organization_id": self.org_id,
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
            print("into agent try")
            # Use auto_commit=False for all operations so we can commit
            # everything atomically — if any step fails, nothing is persisted.
            self.upsert(
                model=Agent,
                values=values,
                conflict_fields=["uuid"],
                update_fields=update_fields,
                extra_update={"updated_at": now},
                auto_commit=False,
            )
            # Flush so the agent row gets an id we can reference below
            self.db.flush()
            agent = self.query(Agent).filter(Agent.uuid == agent_uuid).first()

            channel_data = agent_data.get("channel")
            if channel_data:
                channel_svc = ChannelService(self.db, user_id=self.user_id, org_id=self.org_id)
                channel = None
                if channel_data.get("id"):
                    from core.models.channel import Channel as ChannelModel
                    channel = self.query(ChannelModel).filter(ChannelModel.id == int(channel_data["id"])).first()
                    if not channel:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
                elif channel_data.get("type"):
                    channel = channel_svc.get_or_create_channel_by_type(
                        channel_type=channel_data["type"],
                        meta_data=channel_data.get("meta_data"),
                        created_by=created_by,
                        auto_commit=False,
                    )
                if channel:
                    existing_link = (
                        self.query(AgentChannel)
                        .filter(AgentChannel.agent_id == agent.id, AgentChannel.channel_id == channel.id)
                        .first()
                    )
                    if not existing_link:
                        now_link = int(time.time())
                        self.upsert(
                            model=AgentChannel,
                            values={
                                "uuid": uuid_lib.uuid4(),
                                "agent_id": agent.id,
                                "channel_id": channel.id,
                                "created_at": now_link,
                                "updated_at": now_link,
                            },
                            conflict_fields=["uuid"],
                            update_fields=["updated_at"],
                            auto_commit=False,
                        )

            # When id present: edit both agent and agent_config. When id absent: create agent then create agent_config.
            # Create/update config whenever any config-related field is present.
            CONFIG_TRIGGER_KEYS = (
                "system_prompt", "html_prompt", "first_message", "end_call_message",
                "voicemail_message", "llm_account_id", "tts_account_id", "stt_account_id",
                "llm_model_id", "tts_model_id", "stt_model_id",
                "llm_metadata", "tts_metadata", "stt_metadata",
                "llm_meta_data", "tts_meta_data", "stt_meta_data",
                "llm_model_provider_menu_id", "llm_model_menu_id",
                "tts_model_provider_menu_id", "tts_model_menu_id",
                "stt_model_provider_menu_id", "stt_model_menu_id",
                *AGENT_METADATA_KEYS,
            )
            existing_config = self.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).first()
            has_config_field = any(k in agent_data for k in CONFIG_TRIGGER_KEYS)
            if has_config_field or existing_config:
                config_data = self._build_agent_config_data(agent.id, agent_data, existing_config=existing_config)
                if existing_config:
                    config_data["id"] = existing_config.id
                    config_data["uuid"] = str(existing_config.uuid)
                AgentConfigService(self.db, org_id=self.org_id).upsert_agent_config(config_data, auto_commit=False)

            # All steps succeeded — commit the entire transaction atomically
            self.db.commit()
        except IntegrityError as e:
            print(traceback.format_exc())
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        except HTTPException:
            print(traceback.format_exc())
            self.db.rollback()
            raise
        except Exception:
            print(traceback.format_exc())
            self.db.rollback()
            raise

        agent = self.query(Agent).filter(Agent.uuid == agent_uuid).first()
        config = self.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).first()
        return self._agent_response_item(agent, config)

    def _agent_response_item(self, agent: Agent, config: Any) -> Dict[str, Any]:
        """Build response dict: agent + config as single flat object (no agent_config key)."""
        from core.models.channel import Channel

        channel_rows = (
            self.query(Channel)
            .join(AgentChannel, AgentChannel.channel_id == Channel.id)
            .filter(AgentChannel.agent_id == agent.id)
            .all()
        )

        channel_ids = [c.id for c in channel_rows]
        try:
            phone_rows = (
                self.query(AgentChannelPhoneNumbers)
                .filter(AgentChannelPhoneNumbers.agent_id == agent.id)
                .all()
            )
        except Exception:
            self.db.rollback()
            phone_rows = (
                self.query(AgentChannelPhoneNumbers)
                .filter(AgentChannelPhoneNumbers.channel_id.in_(channel_ids))
                .all()
            ) if channel_ids else []

        # Group phone numbers by channel_id
        phones_by_channel: Dict[int, list] = {}
        for p in phone_rows:
            phones_by_channel.setdefault(p.channel_id, []).append({
                "id": p.id,
                "uuid": str(p.uuid),
                "phone_number": p.phone_number,
                "phone_number_sid": p.phone_number_sid,
                "provider": p.provider,
                "country_code": p.country_code,
                "number_type": p.number_type,
                "capabilities": p.capabilities,
                "status": p.status,
            })

        # Build channels list with nested phone_numbers
        channels_list = []
        for ch in channel_rows:
            channels_list.append({
                "id": ch.id,
                "uuid": str(ch.uuid),
                "name": ch.name,
                "type": ch.type.value if ch.type else None,
                "created_by": ch.created_by,
                "meta_data": ch.meta_data if isinstance(ch.meta_data, dict) else {},
                "phone_numbers": phones_by_channel.get(ch.id, []),
            })

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
            "phone_number": [{"type": p.provider, "no": p.phone_number} for p in phone_rows],
            "channels": channels_list,
        }
        if config:
            agent_meta = config.agent_metadata if isinstance(config.agent_metadata, dict) else {}
            llm_meta = config.llm_metadata if isinstance(config.llm_metadata, dict) else {}
            tts_meta = config.tts_metadata if isinstance(config.tts_metadata, dict) else {}
            stt_meta = config.stt_metadata if isinstance(config.stt_metadata, dict) else {}

            # Resolve model_provider_menu_id and model_menu_id from model_instance FKs
            mi_ids = [
                mid for mid in [config.llm_model_instance_id, config.tts_model_instance_id, config.stt_model_instance_id]
                if mid is not None
            ]
            mi_lookup = {}
            if mi_ids:
                mis = self.db.query(ModelInstance).filter(ModelInstance.id.in_(mi_ids)).all()
                acct_ids_for_mi = [mi.account_id for mi in mis if mi.account_id]
                acct_for_mi = {}
                if acct_ids_for_mi:
                    accts = self.db.query(Account).filter(Account.id.in_(acct_ids_for_mi)).all()
                    acct_for_mi = {a.id: a for a in accts}
                for mi in mis:
                    acct = acct_for_mi.get(mi.account_id)
                    mi_lookup[mi.id] = {
                        "model_provider_menu_id": acct.model_provider_menu_id if acct else None,
                        "model_menu_id": mi.model_menu_id,
                    }

            def _mi_field(mi_id, field):
                if mi_id and mi_id in mi_lookup:
                    return mi_lookup[mi_id].get(field)
                return None

            item.update({
                "llm_account_id": config.llm_account_id,
                "tts_account_id": config.tts_account_id,
                "stt_account_id": config.stt_account_id,
                "llm_model_instance_id": config.llm_model_instance_id,
                "tts_model_instance_id": config.tts_model_instance_id,
                "stt_model_instance_id": config.stt_model_instance_id,
                "llm_model_provider_menu_id": _mi_field(config.llm_model_instance_id, "model_provider_menu_id"),
                "tts_model_provider_menu_id": _mi_field(config.tts_model_instance_id, "model_provider_menu_id"),
                "stt_model_provider_menu_id": _mi_field(config.stt_model_instance_id, "model_provider_menu_id"),
                "llm_model_menu_id": _mi_field(config.llm_model_instance_id, "model_menu_id"),
                "tts_model_menu_id": _mi_field(config.tts_model_instance_id, "model_menu_id"),
                "stt_model_menu_id": _mi_field(config.stt_model_instance_id, "model_menu_id"),
                "llm_model_id": llm_meta.get("model_id"),
                "tts_model_id": tts_meta.get("model_id"),
                "stt_model_id": stt_meta.get("model_id"),
                "llm_metadata": llm_meta,
                "tts_metadata": tts_meta,
                "stt_metadata": stt_meta,
                "llm_meta_data": llm_meta,
                "tts_meta_data": tts_meta,
                "stt_meta_data": stt_meta,
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
        # Build metadata dicts from request, falling back to existing config when key is absent.
        # Accept both "llm_metadata" and "llm_meta_data" naming conventions.
        def _build_metadata(meta_key: str, model_id_key: str) -> dict:
            alt_key = meta_key.replace("metadata", "meta_data")
            # Check if the request explicitly provides this metadata key
            meta_key_present = meta_key in data or alt_key in data
            if meta_key_present:
                # Request explicitly sent this key — use it as-is (replaces existing)
                req_meta = data.get(meta_key) if meta_key in data else data.get(alt_key)
                base = dict(req_meta) if isinstance(req_meta, dict) else {}
            else:
                # Key absent from request — preserve existing config values
                base = {}
                if existing_config and isinstance(getattr(existing_config, meta_key, None), dict):
                    base = dict(getattr(existing_config, meta_key) or {})
            # model_id shorthand overrides metadata's model_id
            model_id_val = data.get(model_id_key)
            if model_id_val is not None:
                base["model_id"] = model_id_val
            return base

        llm_metadata = _build_metadata("llm_metadata", "llm_model_id")
        tts_metadata = _build_metadata("tts_metadata", "tts_model_id")
        stt_model_id_val = data.get("stt_model_id") or data.get("stt_model_it")
        stt_metadata = _build_metadata("stt_metadata", "stt_model_id")
        if stt_model_id_val is not None and "model_id" not in stt_metadata:
            stt_metadata["model_id"] = stt_model_id_val
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
            "llm_account_id": _get("llm_account_id"),
            "tts_account_id": _get("tts_account_id"),
            "stt_account_id": _get("stt_account_id"),
            "first_message": _get("first_message"),
            "system_prompt": system_prompt,
            "end_call_message": _get("end_call_message"),
            "voicemail_message": voicemail,
            "html_prompt": html_prompt,
            "llm_metadata": llm_metadata,
            "tts_metadata": tts_metadata,
            "stt_metadata": stt_metadata,
            "agent_metadata": agent_metadata,
        }

        # Resolve model_instance for each service type via ModelInstance chain:
        # model_menu_id → ModelInstance (active) → Account (active, org-scoped)
        # If model_menu_id is not sent but model_provider_menu_id is, find the first
        # active model instance for that provider (used for TTS voice-based and STT auto selection).
        from core.models.model_menu import ModelMenu

        for stype in ("llm", "tts", "stt"):
            mm_id = data.get(f"{stype}_model_menu_id")
            mpm_id = data.get(f"{stype}_model_provider_menu_id")

            if mm_id is None and mpm_id is not None:
                # No specific model selected — find the first active model instance for this provider
                mi = (
                    self.db.query(ModelInstance)
                    .join(Account, Account.id == ModelInstance.account_id)
                    .join(ModelMenu, ModelMenu.id == ModelInstance.model_menu_id)
                    .filter(
                        ModelMenu.model_provider_menu_id == int(mpm_id),
                        ModelInstance.status == 'active',
                        Account.status == 'active',
                        Account.organization_id == self.org_id,
                    )
                    .order_by(Account.id.asc(), ModelInstance.id.asc())
                    .first()
                )
                if mi:
                    mm_id = mi.model_menu_id
                    config_data[f"{stype}_model_instance_id"] = mi.id
                    config_data[f"{stype}_account_id"] = mi.account_id
                    meta_key = f"{stype}_metadata"
                    meta = dict(config_data.get(meta_key) or {})
                    meta["model_menu_id"] = mi.model_menu_id
                    config_data[meta_key] = meta

            elif mm_id is not None:
                # Specific model selected — find matching instance
                mi = (
                    self.db.query(ModelInstance)
                    .join(Account, Account.id == ModelInstance.account_id)
                    .filter(
                        ModelInstance.model_menu_id == int(mm_id),
                        ModelInstance.status == 'active',
                        Account.status == 'active',
                        Account.organization_id == self.org_id,
                    )
                    .order_by(Account.id.asc())
                    .first()
                )
                if mi:
                    config_data[f"{stype}_model_instance_id"] = mi.id
                    config_data[f"{stype}_account_id"] = mi.account_id
                    meta_key = f"{stype}_metadata"
                    meta = dict(config_data.get(meta_key) or {})
                    meta["model_menu_id"] = int(mm_id)
                    config_data[meta_key] = meta

        return config_data

    def duplicate_agent(self, agent_id: int, new_name: str, created_by: int):
        """Duplicate an existing agent with its config and channel links.

        Creates a new agent with the given name, copies the full AgentConfig
        (prompts, service IDs, all metadata), and links to the same channels.
        Phone numbers, documents, call logs, and uploads are NOT copied.
        """
        source_agent = self.query(Agent).filter(Agent.id == agent_id).first()
        if not source_agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source agent not found",
            )

        now = int(time.time())
        new_agent_uuid = uuid_lib.uuid4()

        # 1. Create new Agent
        agent_values = {
            "uuid": new_agent_uuid,
            "name": new_name,
            "description": source_agent.description,
            "is_public": source_agent.is_public,
            "tags": source_agent.tags,
            "meta_data": source_agent.meta_data,
            "status": "active",
            "agent_type": source_agent.agent_type,
            "total_calls": 0,
            "total_minutes": Decimal("0"),
            "average_rating": Decimal("0"),
            "created_by": created_by,
            "organization_id": self.org_id,
            "created_at": now,
            "updated_at": now,
        }

        try:
            self.upsert(
                model=Agent,
                values=agent_values,
                conflict_fields=["uuid"],
                update_fields=["updated_at"],
                auto_commit=False,
            )
            self.db.flush()
            new_agent = self.query(Agent).filter(Agent.uuid == new_agent_uuid).first()

            # 2. Copy AgentConfig
            source_config = self.query(AgentConfig).filter(AgentConfig.agent_id == source_agent.id).first()
            if source_config:
                import copy
                config_values = {
                    "uuid": uuid_lib.uuid4(),
                    "agent_id": new_agent.id,
                    "organization_id": self.org_id,
                    "llm_account_id": source_config.llm_account_id,
                    "tts_account_id": source_config.tts_account_id,
                    "stt_account_id": source_config.stt_account_id,
                    "llm_model_instance_id": source_config.llm_model_instance_id,
                    "tts_model_instance_id": source_config.tts_model_instance_id,
                    "stt_model_instance_id": source_config.stt_model_instance_id,
                    "first_message": source_config.first_message,
                    "system_prompt": source_config.system_prompt or "",
                    "end_call_message": source_config.end_call_message,
                    "voicemail_message": source_config.voicemail_message,
                    "html_prompt": source_config.html_prompt,
                    "status": "active",
                    "llm_metadata": copy.deepcopy(source_config.llm_metadata) if source_config.llm_metadata else {},
                    "tts_metadata": copy.deepcopy(source_config.tts_metadata) if source_config.tts_metadata else {},
                    "stt_metadata": copy.deepcopy(source_config.stt_metadata) if source_config.stt_metadata else {},
                    "agent_metadata": copy.deepcopy(source_config.agent_metadata) if source_config.agent_metadata else {},
                    "created_at": now,
                    "updated_at": now,
                }
                self.upsert(
                    model=AgentConfig,
                    values=config_values,
                    conflict_fields=["agent_id", "organization_id"],
                    update_fields=["updated_at"],
                    auto_commit=False,
                )

            # 3. Link to same channels
            source_channels = self.query(AgentChannel).filter(AgentChannel.agent_id == source_agent.id).all()
            for link in source_channels:
                self.upsert(
                    model=AgentChannel,
                    values={
                        "uuid": uuid_lib.uuid4(),
                        "agent_id": new_agent.id,
                        "channel_id": link.channel_id,
                        "organization_id": self.org_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                    conflict_fields=["uuid"],
                    update_fields=["updated_at"],
                    auto_commit=False,
                )

            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from e
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        new_agent = self.query(Agent).filter(Agent.uuid == new_agent_uuid).first()
        new_config = self.query(AgentConfig).filter(AgentConfig.agent_id == new_agent.id).first()
        return self._agent_response_item(new_agent, new_config)


    # ------------------------------------------------------------------
    # New create/edit API (aligned to Agent + AgentConfig UUID models)
    # ------------------------------------------------------------------

    def create_agent(self, data: Dict[str, Any], user_id: Optional[UUID]) -> Agent:
        """Create a new agent with optional config and attachments."""
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")

        try:
            agent = Agent(
                name=data["name"],
                description=data.get("description"),
                agent_type=data["agent_type"],
                is_active=data.get("is_active", True),
                created_by_user_id=user_id,
                organization_id=self.org_id,
            )
            self.db.add(agent)
            self.db.flush()

            self.audit.log(
                AgentAuditAction.CREATED,
                agent_id=agent.id,
                after=self._snapshot(agent, self._AGENT_ROOT_FIELDS),
            )

            self._apply_attachments(agent, data, user_id)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from e
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        return agent

    def update_agent(self, agent_id: str, data: Dict[str, Any], user_id: Optional[UUID]) -> Agent:
        """Update an existing agent in place. Only provided fields are changed.

        Mutates the live config (resolved via ``published_config_id``) rather
        than the latest version, so editing while viewing v2 with v3 live
        cannot silently flip the live pointer.
        """
        aid = UUID(str(agent_id))
        agent = self.query(Agent).filter(Agent.id == aid, Agent.deleted_at.is_(None)).first()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

        try:
            root_before = self._snapshot(agent, self._AGENT_ROOT_FIELDS)
            for field in self._AGENT_ROOT_FIELDS:
                if field in data:
                    setattr(agent, field, data[field])

            self.audit.log_field_diff(
                AgentAuditAction.UPDATED,
                agent_id=agent.id,
                agent_config_id=agent.published_config_id,
                before=root_before,
                after=self._snapshot(agent, self._AGENT_ROOT_FIELDS),
                fields=self._AGENT_ROOT_FIELDS,
            )

            self._apply_attachments(agent, data, user_id)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from e
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        self._invalidate_pipeline_cache(agent.id)
        return agent

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    def list_versions(self, agent_id: str) -> List[Dict[str, Any]]:
        """All non-deleted versions for an agent, newest first. Each row is
        flagged with ``is_live`` against ``Agent.published_config_id``."""
        agent = self.get_agent(agent_id)
        rows = (
            self.query(AgentConfig)
            .filter(AgentConfig.agent_id == agent.id, AgentConfig.deleted_at.is_(None))
            .order_by(AgentConfig.version.desc())
            .all()
        )
        live_id = agent.published_config_id
        return [self.version_response(r, is_live=(r.id == live_id)) for r in rows]

    def get_version(self, agent_id: str, config_id: str) -> AgentConfig:
        """Fetch one version, scoped to the agent. Raises 404 if missing."""
        agent = self.get_agent(agent_id)
        cfg = (
            self.query(AgentConfig)
            .filter(
                AgentConfig.id == UUID(str(config_id)),
                AgentConfig.agent_id == agent.id,
                AgentConfig.deleted_at.is_(None),
            )
            .first()
        )
        if not cfg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Version not found for this agent",
            )
        return cfg

    def save_as_new_version(
        self,
        agent_id: str,
        data: Dict[str, Any],
        user_id: Optional[UUID],
        *,
        source_config_id: Optional[UUID] = None,
        from_scratch: bool = False,
    ) -> Tuple[Agent, Optional[AgentConfig]]:
        """Persist a new **draft** version of the agent's config.

        Two modes:

        * **Clone** (default) — copy fields and tool / MCP / KB attachments
          from ``source_config_id`` (or the live version when omitted), apply
          any edits in ``data``, and write as version N+1.
        * **From scratch** (``from_scratch=True``) — skip source resolution
          entirely. The new row starts with whatever ``config`` the request
          carries (or null fields if none) and no attachments. Used by the
          "Start fresh" path in the create-version dialog.

        The new version is never auto-promoted to live; callers must invoke
        ``switch_active_version`` (Publish) to make it serve traffic.

        Returns the agent along with the newly-created config so the router can
        render ``agent_response`` against the draft — otherwise the response
        would still reflect the live version and the UI would lose the edits
        the user just saved.
        """
        agent = self.get_agent(agent_id)
        try:
            new_config = self._apply_attachments(
                agent,
                data,
                user_id,
                create_new_version=True,
                make_live=False,
                source_config_id=source_config_id,
                from_scratch=from_scratch,
            )
            if new_config is not None:
                self.audit.log(
                    AgentAuditAction.VERSION_CREATED,
                    agent_id=agent.id,
                    agent_config_id=new_config.id,
                    target_resource_type=AuditResourceType.AGENT_CONFIG,
                    target_resource_id=str(new_config.id),
                    extra={
                        "version": new_config.version,
                        "from_scratch": bool(from_scratch),
                        "source_config_id": (
                            str(source_config_id) if source_config_id else None
                        ),
                    },
                )
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from e
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        self._invalidate_pipeline_cache(agent.id)
        return agent, new_config

    def update_version(
        self,
        agent_id: str,
        data: Dict[str, Any],
        *,
        source_config_id: Optional[UUID] = None,
    ) -> Tuple[Agent, Optional[AgentConfig]]:
        """Update an existing version in place — no new version row is created.

        Target is ``source_config_id`` (the version the editor was previewing).
        When omitted, falls back to the live config — i.e. same behaviour as
        ``update_agent`` minus the top-level agent fields.

        This is the Save endpoint's backend. Versioning lives behind its own
        "Create version" button (see ``save_as_new_version``), so editing
        never spawns drafts. ``published_config_id`` is not touched; if the
        edited row happens to be live, callers serving traffic see the new
        fields on the next pipeline cache miss.
        """
        agent = self.get_agent(agent_id)
        if source_config_id is not None:
            target = self.get_version(agent_id, str(source_config_id))
        else:
            target = self._resolve_current_config(agent)
            if target is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent has no config to update",
                )

        try:
            config_data = data.get("config")
            if config_data is not None:
                self._validate_meta_data_schema(config_data)
                self._apply_config_fields_audited(agent, target, config_data)
            self._sync_config_attachments(agent, target, data)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            detail = _agent_unique_constraint_detail(e)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from e
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        self._invalidate_pipeline_cache(agent.id)
        return agent, target

    def switch_active_version(self, agent_id: str, config_id: str) -> Agent:
        """Promote an existing version to live.

        Points ``Agent.published_config_id`` at the target config and stamps
        ``published_at`` on it — drafts created via ``save_as_new_version`` have
        a null ``published_at`` until they are promoted here.
        """
        agent = self.get_agent(agent_id)
        cfg = self.get_version(agent_id, config_id)
        if agent.published_config_id == cfg.id:
            return agent
        try:
            from datetime import datetime, timezone
            previous_published_id = agent.published_config_id
            agent.published_config_id = cfg.id
            cfg.published_at = datetime.now(timezone.utc)
            self.audit.log(
                AgentAuditAction.VERSION_SWITCHED,
                agent_id=agent.id,
                agent_config_id=cfg.id,
                target_resource_type=AuditResourceType.AGENT_CONFIG,
                target_resource_id=str(cfg.id),
                before={"published_config_id": (
                    str(previous_published_id) if previous_published_id else None
                )},
                after={"published_config_id": str(cfg.id)},
                extra={"version": cfg.version},
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self._invalidate_pipeline_cache(agent.id)
        return agent

    def delete_version(self, agent_id: str, config_id: str) -> Dict[str, str]:
        """Soft-delete a version. The live version cannot be deleted."""
        agent = self.get_agent(agent_id)
        cfg = self.get_version(agent_id, config_id)
        if agent.published_config_id == cfg.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the live version. Switch to another version first.",
            )
        from datetime import datetime, timezone
        cfg.deleted_at = datetime.now(timezone.utc)
        # Retire the version's owned workflow copy alongside it — unless another
        # live version still references it. Legacy unowned workflows are kept.
        if cfg.workflow_id is not None:
            from core.models.workflow import Workflow

            wf = (
                self.query(Workflow)
                .filter(Workflow.id == cfg.workflow_id, Workflow.deleted_at.is_(None))
                .first()
            )
            if wf and wf.agent_id == agent.id:
                others = (
                    self.query(AgentConfig)
                    .filter(
                        AgentConfig.workflow_id == wf.id,
                        AgentConfig.deleted_at.is_(None),
                        AgentConfig.id != cfg.id,
                    )
                    .count()
                )
                if others == 0:
                    wf.deleted_at = datetime.now(timezone.utc)
        self.audit.log(
            AgentAuditAction.VERSION_DELETED,
            agent_id=agent.id,
            agent_config_id=cfg.id,
            target_resource_type=AuditResourceType.AGENT_CONFIG,
            target_resource_id=str(cfg.id),
            extra={"version": cfg.version},
        )
        self.db.commit()
        self._invalidate_pipeline_cache(agent.id)
        return {"message": "Version deleted successfully"}

    def version_response(self, config: AgentConfig, is_live: bool) -> Dict[str, Any]:
        """Lightweight summary used in version-list responses."""
        return {
            "id": str(config.id),
            "version": config.version,
            "is_live": is_live,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
            "published_at": config.published_at.isoformat() if config.published_at else None,
            "created_by_user_id": (
                str(config.created_by_user_id) if config.created_by_user_id else None
            ),
        }

    def _apply_attachments(
        self,
        agent: Agent,
        data: Dict[str, Any],
        user_id: Optional[UUID],
        *,
        create_new_version: bool = False,
        make_live: bool = False,
        source_config_id: Optional[UUID] = None,
        from_scratch: bool = False,
    ) -> Optional[AgentConfig]:
        """Shared logic for syncing config and attachments.

        ``create_new_version=False`` (default): the live config is mutated in
        place — the behaviour used by both ``create_agent`` and ``update_agent``.

        ``create_new_version=True``: the live config is cloned into a fresh row
        with the next version number and attachments are wired against it.
        ``make_live`` controls whether that new row is promoted to live:

        * ``make_live=False`` (default) — the new row is a draft;
          ``published_config_id`` is untouched. Used by ``save_as_new_version``.
        * ``make_live=True`` — the new row becomes live immediately. Reserved
          for internal callers; the editor flow goes through
          ``switch_active_version`` instead.

        Returns the affected config (the new draft when versioning, otherwise
        the in-place row) so callers can render a response against it.
        """
        config_data = data.get("config")
        tool_ids = data.get("tool_ids")
        mcp_server_ids = data.get("mcp_server_ids")
        upload_ids = data.get("upload_ids")

        config: Optional[AgentConfig] = None
        if config_data is not None:
            if create_new_version:
                config = self._create_new_version_config(
                    agent,
                    config_data,
                    user_id,
                    make_live=make_live,
                    source_config_id=source_config_id,
                    from_scratch=from_scratch,
                )
            else:
                config = self._upsert_new_config(agent, config_data, user_id)
        elif create_new_version:
            # Versioning a save with no config edits = clone source config as-is.
            config = self._create_new_version_config(
                agent,
                {},
                user_id,
                make_live=make_live,
                source_config_id=source_config_id,
                from_scratch=from_scratch,
            )

        if config is None and (
            tool_ids is not None or mcp_server_ids is not None or upload_ids is not None
        ):
            config = self._resolve_current_config(agent)

        self._sync_config_attachments(agent, config, data)
        return config

    def _sync_config_attachments(
        self,
        agent: Agent,
        config: Optional[AgentConfig],
        data: Dict[str, Any],
    ) -> None:
        """Fan out the optional ``*_ids`` keys in ``data`` to their dedicated
        ``_sync_*`` helpers.

        Each input is independently optional: ``None`` means "leave that
        attachment list alone", an empty list means "clear it". Phone numbers
        and web channels are agent-scoped; the rest are config-scoped.

        Used by both the in-place update path and the new-version path so the
        attachment-sync fan-out lives in exactly one place.
        """
        tool_ids = data.get("tool_ids")
        if tool_ids is not None:
            self._sync_tools(agent, config, tool_ids)
        mcp_server_ids = data.get("mcp_server_ids")
        if mcp_server_ids is not None:
            self._sync_mcp_servers(agent, config, mcp_server_ids)
        upload_ids = data.get("upload_ids")
        if upload_ids is not None:
            self._sync_knowledge_base(agent, config, upload_ids)
        phone_numbers = data.get("phone_numbers")
        if phone_numbers is not None:
            self._sync_phone_numbers(agent, phone_numbers)
        web_channel_ids = data.get("web_channel_ids")
        if web_channel_ids is not None:
            self._sync_agent_channels(agent, web_channel_ids)

    def get_agent(self, agent_id: str) -> Agent:
        """Fetch a single agent by UUID. Raises 404 if not found."""
        aid = UUID(str(agent_id))
        agent = self.query(Agent).filter(Agent.id == aid, Agent.deleted_at.is_(None)).first()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    def delete_agent(self, agent_id: str) -> Dict[str, str]:
        """Delete an agent and all related records (UUID-based)."""
        agent = self.get_agent(agent_id)

        # Capture the audit row BEFORE the delete fan-out so the snapshot
        # holds the agent's identifying fields. The audit row survives the
        # delete because audit_logs has no FK on agent_id.
        self.audit.log(
            AgentAuditAction.DELETED,
            agent_id=agent.id,
            before=self._snapshot(agent, self._AGENT_ROOT_FIELDS),
        )

        # Delete phone numbers assigned to this agent (unassigned numbers live on provider only)
        self.db.query(PhoneNumber).filter(
            PhoneNumber.agent_id == agent.id, PhoneNumber.organization_id == self.org_id
        ).delete(synchronize_session=False)

        # Delete junction rows
        self.db.query(AgentTool).filter(AgentTool.agent_id == agent.id).delete(synchronize_session=False)
        self.db.query(AgentMcpServer).filter(AgentMcpServer.agent_id == agent.id).delete(synchronize_session=False)
        self.db.query(AgentKnowledgeBase).filter(AgentKnowledgeBase.agent_id == agent.id).delete(synchronize_session=False)

        # Delete config
        self.db.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).delete(synchronize_session=False)

        # Soft-delete the agent's owned workflow copies before the hard delete —
        # the FK is SET NULL, so without this they would linger as live orphans.
        from datetime import datetime, timezone
        from core.models.workflow import Workflow
        self.db.query(Workflow).filter(
            Workflow.agent_id == agent.id, Workflow.deleted_at.is_(None)
        ).update({"deleted_at": datetime.now(timezone.utc)}, synchronize_session=False)

        self.db.delete(agent)
        self.db.commit()
        return {"message": "Agent deleted successfully"}

    def _validate_meta_data_schema(self, config_data: Dict[str, Any]) -> None:
        """Validate meta_data_schema fields in llm_settings, stt_settings, voice_settings.

        Prefers model-level meta_data_schema (per-model param support).
        Falls back to provider-level meta_data_schema[kind] for models that
        don't have their own schema yet.
        Raises HTTPException(400) with structured errors if validation fails.
        """
        from core.models.model_provider import ModelProvider

        SETTINGS_KIND_MAP = {
            "llm_settings": "llm",
            "stt_settings": "stt",
            "voice_settings": "tts",
        }

        validator = MetaDataSchemaValidator()
        all_errors: Dict[str, Dict[str, list]] = {}

        for settings_key, kind in SETTINGS_KIND_MAP.items():
            settings = config_data.get(settings_key)
            if not settings or not isinstance(settings, dict):
                continue

            provider_id = settings.get("provider_id")
            if not provider_id:
                continue

            # Try model-level schema first
            schema = None
            model_meta_data = None
            model_id = settings.get("model_id")
            if model_id:
                model_record = (
                    self.db.query(Model)
                    .filter(Model.id == UUID(str(model_id)))
                    .first()
                )
                if model_record:
                    if model_record.meta_data_schema:
                        schema = model_record.meta_data_schema
                    if model_record.meta_data:
                        model_meta_data = model_record.meta_data

            # Fall back to provider-level schema
            if not schema:
                provider = (
                    self.db.query(ModelProvider)
                    .filter(ModelProvider.id == UUID(str(provider_id)))
                    .first()
                )
                if provider and provider.meta_data_schema:
                    schema = provider.meta_data_schema.get(kind)

            if not schema:
                continue

            field_errors = validator.validate_settings(schema, settings, model_meta_data)
            if field_errors:
                all_errors[settings_key] = field_errors

        if all_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Validation failed", "errors": all_errors},
            )

    # ── Config field metadata (shared by in-place updates and version cloning) ──
    _CONFIG_FIELDS = (
        "first_message", "end_call_message", "system_prompt_template",
        "conversation_history_token_limit", "language_id", "knowledge_model_id",
        "llm_settings", "voice_settings", "stt_settings", "conversation_settings",
        # Workflow assignment lives on the live config (per-agent toggle + assigned workflow).
        "mode", "workflow_id",
    )
    _CONFIG_UUID_FIELDS = frozenset({"language_id", "knowledge_model_id", "workflow_id"})

    # Root agent fields that callers can patch via ``update_agent``.
    _AGENT_ROOT_FIELDS = ("name", "description", "agent_type", "is_active")

    @staticmethod
    def _snapshot(obj: Any, fields: Iterable[str]) -> Dict[str, Any]:
        """Capture a shallow ``{field: value}`` snapshot for diffing.

        UUID-typed fields are normalised to strings so the JSON payload
        stored in ``audit_logs.changes`` is comparable across runs.
        """
        snap: Dict[str, Any] = {}
        for field in fields:
            val = getattr(obj, field, None)
            if isinstance(val, UUID):
                val = str(val)
            snap[field] = val
        return snap

    def _apply_config_fields(self, target: AgentConfig, data: Dict[str, Any]) -> None:
        """Copy provided config field values onto an AgentConfig row.

        Only keys present in `data` are written, so partial updates don't wipe
        unsent fields. UUID-typed columns are normalised from strings.
        """
        for field in self._CONFIG_FIELDS:
            if field not in data:
                continue
            val = data[field]
            if val is not None and field in self._CONFIG_UUID_FIELDS:
                try:
                    val = UUID(str(val))
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid {field}",
                    )
            if field == "workflow_id" and val is not None:
                self._assert_assignable_workflow(val, target.agent_id)
            setattr(target, field, val)

    def _assert_assignable_workflow(self, workflow_id: UUID, agent_id: Optional[UUID]) -> None:
        """Guard workflow assignment: the workflow must exist, belong to the caller's org
        (``self.query`` is org-scoped), be owned by this agent (or be a legacy unowned
        row), and be valid (its graph passes validation). Prevents assigning another
        org's workflow (IDOR), another agent's per-version copy, or a broken graph."""
        from core.models.workflow import Workflow, WorkflowVersion

        wf = (
            self.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.deleted_at.is_(None))
            .first()
        )
        if not wf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
            )
        if wf.agent_id is not None and agent_id is not None and wf.agent_id != agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow belongs to a different agent",
            )
        version = (
            self.query(WorkflowVersion)
            .filter(
                WorkflowVersion.id == wf.draft_version_id,
                WorkflowVersion.deleted_at.is_(None),
            )
            .first()
        )
        if not version or not version.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow has validation issues — fix them before assigning it to an agent",
            )

    def _apply_config_fields_audited(
        self,
        agent: Agent,
        target: AgentConfig,
        config_data: Dict[str, Any],
    ) -> None:
        """Apply ``config_data`` to ``target`` and emit one config-update audit row.

        Centralises the snapshot → mutate → diff sequence used by both the
        in-place update (``_upsert_new_config``) and the version update
        (``update_version``). ``log_field_diff`` short-circuits when nothing
        actually changed, so calling this on a no-op write is free.

        Schema validation (``_validate_meta_data_schema``) is the caller's
        responsibility because both call sites already invoke it at the
        right point in their own flow.
        """
        before_snap = self._snapshot(target, self._CONFIG_FIELDS)
        self._apply_config_fields(target, config_data)
        self.audit.log_field_diff(
            AgentAuditAction.CONFIG_UPDATED,
            agent_id=agent.id,
            agent_config_id=target.id,
            before=before_snap,
            after=self._snapshot(target, self._CONFIG_FIELDS),
            fields=self._CONFIG_FIELDS,
        )

    def _resolve_current_config(self, agent: Agent) -> Optional[AgentConfig]:
        """Return the live AgentConfig: published_config_id first, then latest version."""
        if agent.published_config_id:
            cfg = (
                self.query(AgentConfig)
                .filter(
                    AgentConfig.id == agent.published_config_id,
                    AgentConfig.deleted_at.is_(None),
                )
                .first()
            )
            if cfg:
                return cfg
        return (
            self.query(AgentConfig)
            .filter(AgentConfig.agent_id == agent.id, AgentConfig.deleted_at.is_(None))
            .order_by(AgentConfig.version.desc())
            .first()
        )

    def _next_version_number(self, agent_id: UUID) -> int:
        """Return ``max(version)+1`` across **all** rows for this agent —
        including soft-deleted ones.

        The unique constraint ``uq_agent_configs_agent_version`` on
        ``(agent_id, version)`` does not exclude soft-deleted rows. If we
        computed the next version from non-deleted rows only, a sequence of
        *switch-live → delete-the-highest → save-as-new-version* would attempt
        to reuse a version number that still occupies the unique index and
        fail with an ``IntegrityError``. Version numbers stay monotonically
        increasing for the lifetime of the agent.
        """
        row = (
            self.query(AgentConfig)
            .filter(AgentConfig.agent_id == agent_id)
            .with_entities(AgentConfig.version)
            .order_by(AgentConfig.version.desc())
            .first()
        )
        return (row[0] + 1) if row else 1

    @staticmethod
    def _invalidate_pipeline_cache(agent_id) -> None:
        """Drop the resolver's cached pipeline so the next call re-reads the DB."""
        from core.services.redis_service import cache_delete
        cache_delete(f"agent_pipeline_config:{agent_id}")

    def _upsert_new_config(self, agent: Agent, config_data: Dict[str, Any], user_id: Optional[UUID]) -> AgentConfig:
        """Update the live config in place, or create v1 if the agent has none yet."""
        self._validate_meta_data_schema(config_data)
        existing = self._resolve_current_config(agent)

        if existing:
            self._apply_config_fields_audited(agent, existing, config_data)
            if agent.published_config_id != existing.id:
                agent.published_config_id = existing.id
            return existing

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required to create config",
            )
        from datetime import datetime, timezone
        config = AgentConfig(
            agent_id=agent.id,
            version=1,
            created_by_user_id=user_id,
            organization_id=self.org_id,
            published_at=datetime.now(timezone.utc),
        )
        self._apply_config_fields(config, config_data)
        self.db.add(config)
        self.db.flush()
        agent.published_config_id = config.id
        return config

    def _create_new_version_config(
        self,
        agent: Agent,
        config_data: Dict[str, Any],
        user_id: Optional[UUID],
        *,
        make_live: bool = False,
        source_config_id: Optional[UUID] = None,
        from_scratch: bool = False,
    ) -> AgentConfig:
        """Persist a new version row (version N+1).

        Two modes:

        * **Clone** (default) — fields and tool / MCP / knowledge-base
          attachments are copied from the resolved source (explicit
          ``source_config_id`` wins, otherwise the live config). Saving while
          previewing v9 produces a new row mirroring v9 before any edits in
          ``config_data`` are applied. This is the "Copy from version" path
          in the create-version dialog.
        * **Fresh** (``from_scratch=True``) — no source is read. The new row
          starts with whatever ``config_data`` carries (or null fields if
          empty) and zero attachments. This is the "Start fresh" path.
          ``source_config_id`` is ignored.

        ``make_live`` controls promotion:

        * ``False`` (default) — the new row is a draft. ``published_at`` stays
          null and ``agent.published_config_id`` is not touched; the currently
          live version keeps serving calls.
        * ``True`` — the new row becomes live: ``published_config_id`` is
          repointed and ``published_at`` is stamped to now.
        """
        self._validate_meta_data_schema(config_data)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required to create a version",
            )

        from datetime import datetime, timezone
        source = None if from_scratch else self._resolve_clone_source(agent, source_config_id)
        now = datetime.now(timezone.utc) if make_live else None
        new_config = AgentConfig(
            agent_id=agent.id,
            version=self._next_version_number(agent.id),
            created_by_user_id=user_id,
            organization_id=self.org_id,
            published_at=now,
        )
        # Seed from the source so fields the request didn't touch are preserved.
        if source is not None:
            for field in self._CONFIG_FIELDS:
                setattr(new_config, field, getattr(source, field, None))
        self._apply_config_fields(new_config, config_data)
        self.db.add(new_config)
        self.db.flush()
        # Each agent version owns an independent workflow copy — deep-copy the
        # referenced workflow's single working graph so editing one version's
        # workflow never changes another's. Flush-only inside this transaction,
        # so a failure later rolls the copy back too.
        if not from_scratch and new_config.workflow_id is not None:
            from core.services.workflow.service import WorkflowService

            wf_copy = WorkflowService(
                self.db, user_id=user_id, org_id=self.org_id
            ).duplicate_for_agent_version(new_config.workflow_id, agent.id, user_id)
            new_config.workflow_id = wf_copy.id
        # Clone attachment rows so the new version owns its own snapshot.
        # _sync_* may overwrite specific lists later in the same transaction
        # if the caller explicitly sent tool_ids / mcp_server_ids / upload_ids.
        if source is not None:
            self._clone_attachments(
                agent, source_config_id=source.id, target_config_id=new_config.id
            )
            # The session is configured `autoflush=False`, so the cloned
            # `db.add(...)` calls above stay PENDING in memory. Without an
            # explicit flush, the subsequent `_sync_*` queries (which run a
            # SELECT for "existing rows scoped to this config") would not see
            # the clones, conclude that the config has no attachments, and
            # re-INSERT every tool/MCP/KB — colliding with the flushed clones
            # at commit on `uq_agent_tools_config_tool` and friends. Flushing
            # here makes the clones visible to those follow-up queries in the
            # same transaction.
            self.db.flush()
        if make_live:
            agent.published_config_id = new_config.id
        return new_config

    def _resolve_clone_source(
        self, agent: Agent, source_config_id: Optional[UUID]
    ) -> Optional[AgentConfig]:
        """Pick the config to clone from when versioning.

        Explicit ``source_config_id`` wins (validated to belong to the agent);
        otherwise we fall back to whatever ``_resolve_current_config`` returns
        (published version → latest version → None).
        """
        if source_config_id is not None:
            cfg = (
                self.query(AgentConfig)
                .filter(
                    AgentConfig.id == source_config_id,
                    AgentConfig.agent_id == agent.id,
                    AgentConfig.deleted_at.is_(None),
                )
                .first()
            )
            if not cfg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_config_id does not belong to this agent",
                )
            return cfg
        return self._resolve_current_config(agent)

    def _clone_attachments(
        self,
        agent: Agent,
        *,
        source_config_id: UUID,
        target_config_id: UUID,
    ) -> None:
        """Duplicate tool / MCP / KB rows from one config to another.

        Each row keeps its foreign-id (tool_id / mcp_server_id /
        knowledge_base_id) but is rewritten under ``target_config_id`` so the
        per-config unique constraint stays valid.
        """
        base = {
            "agent_id": agent.id,
            "agent_config_id": target_config_id,
            "organization_id": self.org_id,
        }

        for row in (
            self.query(AgentTool)
            .filter(
                AgentTool.agent_id == agent.id,
                AgentTool.organization_id == self.org_id,
                AgentTool.agent_config_id == source_config_id,
            )
            .all()
        ):
            self.db.add(AgentTool(**base, tool_id=row.tool_id))

        for row in (
            self.query(AgentMcpServer)
            .filter(
                AgentMcpServer.agent_id == agent.id,
                AgentMcpServer.organization_id == self.org_id,
                AgentMcpServer.agent_config_id == source_config_id,
            )
            .all()
        ):
            self.db.add(
                AgentMcpServer(
                    **base,
                    mcp_server_id=row.mcp_server_id,
                    oauth_connection_id=row.oauth_connection_id,
                )
            )

        for row in (
            self.query(AgentKnowledgeBase)
            .filter(
                AgentKnowledgeBase.agent_id == agent.id,
                AgentKnowledgeBase.organization_id == self.org_id,
                AgentKnowledgeBase.agent_config_id == source_config_id,
            )
            .all()
        ):
            self.db.add(
                AgentKnowledgeBase(**base, knowledge_base_id=row.knowledge_base_id)
            )

    def _sync_tools(self, agent: Agent, config: Optional[AgentConfig], tool_ids: List[str]) -> None:
        uuids = [UUID(str(tid)) for tid in tool_ids]
        if uuids:
            existing_tools = self.query(Tool).filter(Tool.id.in_(uuids)).all()
            found = {t.id for t in existing_tools}
            missing = [str(u) for u in uuids if u not in found]
            if missing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tools not found: {', '.join(missing)}")

        # All writes are scoped to this config — editing v11's tools must not
        # touch v10's rows, and v10's rows must keep their `agent_config_id`.
        config_id = config.id if config else None
        scope = [
            AgentTool.agent_id == agent.id,
            AgentTool.organization_id == self.org_id,
            AgentTool.agent_config_id == config_id,
        ]

        # Snapshot before the diff so the audit-log sees attach/detach events
        # against the same scope the writes below operate on.
        before_ids = {
            r[0] for r in self.db.query(AgentTool.tool_id).filter(*scope).all()
        }

        # Delete tools not in the new set
        if uuids:
            self.db.query(AgentTool).filter(
                *scope, AgentTool.tool_id.notin_(uuids),
            ).delete(synchronize_session=False)
        else:
            self.db.query(AgentTool).filter(*scope).delete(synchronize_session=False)

        # Insert missing
        if uuids:
            existing_rows = self.db.query(AgentTool.tool_id).filter(*scope).all()
            existing_set = {r[0] for r in existing_rows}
            for tid in uuids:
                if tid not in existing_set:
                    self.db.add(AgentTool(
                        agent_id=agent.id,
                        tool_id=tid,
                        agent_config_id=config_id,
                        organization_id=self.org_id,
                    ))

        self.audit.log_attachment_diff(
            agent_id=agent.id,
            agent_config_id=config_id,
            before_ids=before_ids,
            after_ids=set(uuids),
            attached_action=AgentAuditAction.TOOL_ATTACHED,
            detached_action=AgentAuditAction.TOOL_DETACHED,
            resource_type=AuditResourceType.TOOL,
        )

    def _sync_mcp_servers(self, agent: Agent, config: Optional[AgentConfig], mcp_server_ids: List[str]) -> None:
        uuids = {UUID(str(sid)) for sid in mcp_server_ids}

        if uuids:
            existing = self.query(McpServer).filter(McpServer.id.in_(uuids)).all()
            found = {s.id for s in existing}
            missing = [str(u) for u in uuids if u not in found]
            if missing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"MCP servers not found: {', '.join(missing)}")

        config_id = config.id if config else None
        scope = [
            AgentMcpServer.agent_id == agent.id,
            AgentMcpServer.organization_id == self.org_id,
            AgentMcpServer.agent_config_id == config_id,
        ]

        before_ids = {
            r[0]
            for r in self.db.query(AgentMcpServer.mcp_server_id).filter(*scope).all()
        }

        # Delete rows not in the new set
        if uuids:
            self.db.query(AgentMcpServer).filter(
                *scope, AgentMcpServer.mcp_server_id.notin_(uuids),
            ).delete(synchronize_session=False)
        else:
            self.db.query(AgentMcpServer).filter(*scope).delete(synchronize_session=False)

        # Insert any missing links
        if uuids:
            existing_ids = {
                r[0]
                for r in self.db.query(AgentMcpServer.mcp_server_id).filter(*scope).all()
            }
            for sid in uuids:
                if sid in existing_ids:
                    continue
                if config_id is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent config required to attach MCP servers")
                self.db.add(AgentMcpServer(
                    agent_id=agent.id,
                    agent_config_id=config_id,
                    mcp_server_id=sid,
                    organization_id=self.org_id,
                ))

        self.audit.log_attachment_diff(
            agent_id=agent.id,
            agent_config_id=config_id,
            before_ids=before_ids,
            after_ids=uuids,
            attached_action=AgentAuditAction.MCP_ATTACHED,
            detached_action=AgentAuditAction.MCP_DETACHED,
            resource_type=AuditResourceType.MCP_SERVER,
        )

    def _sync_knowledge_base(self, agent: Agent, config: Optional[AgentConfig], upload_ids: List[str]) -> None:
        uuids = [UUID(str(uid)) for uid in upload_ids]
        existing_uploads: List[Upload] = []
        if uuids:
            existing_uploads = self.query(Upload).filter(Upload.id.in_(uuids)).all()
            found = {u.id for u in existing_uploads}
            missing = [str(u) for u in uuids if u not in found]
            if missing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Uploads not found: {', '.join(missing)}")

        kb_ids: List[UUID] = []
        if uuids:
            config_id = config.id if config else None
            if config_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent config required to attach knowledge base documents")
            kb_by_upload = {
                kb.upload_id: kb
                for kb in self.db.query(KnowledgeBase).filter(
                    KnowledgeBase.upload_id.in_(uuids),
                    KnowledgeBase.organization_id == self.org_id,
                ).all()
            }
            upload_by_id = {u.id: u for u in existing_uploads}
            for uid in uuids:
                kb = kb_by_upload.get(uid)
                if kb is None:
                    up = upload_by_id.get(uid)
                    kb = KnowledgeBase(
                        organization_id=self.org_id,
                        name=(up.file_name if up and up.file_name else str(uid)),
                        status=(up.status if up else "ready"),
                        upload_id=uid,
                        meta_data={},
                    )
                    self.db.add(kb)
                    self.db.flush()
                kb_ids.append(kb.id)

        config_id = config.id if config else None
        scope = [
            AgentKnowledgeBase.agent_id == agent.id,
            AgentKnowledgeBase.organization_id == self.org_id,
            AgentKnowledgeBase.agent_config_id == config_id,
        ]

        # Snapshot before/after as ``upload_id`` (the id the caller passes and
        # the UI shows) rather than the internal ``knowledge_base_id`` — the
        # audit row should read meaningfully without joining KB rows.
        before_upload_ids = {
            r[0]
            for r in self.db.query(KnowledgeBase.upload_id)
            .join(
                AgentKnowledgeBase,
                AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id,
            )
            .filter(*scope)
            .all()
            if r[0] is not None
        }

        if kb_ids:
            self.db.query(AgentKnowledgeBase).filter(
                *scope, AgentKnowledgeBase.knowledge_base_id.notin_(kb_ids),
            ).delete(synchronize_session=False)
        else:
            self.db.query(AgentKnowledgeBase).filter(*scope).delete(synchronize_session=False)

        if kb_ids:
            existing_rows = (
                self.db.query(AgentKnowledgeBase.knowledge_base_id).filter(*scope).all()
            )
            existing_set = {r[0] for r in existing_rows}
            for kid in kb_ids:
                if kid not in existing_set:
                    self.db.add(AgentKnowledgeBase(
                        agent_id=agent.id,
                        knowledge_base_id=kid,
                        agent_config_id=config_id,
                        organization_id=self.org_id,
                    ))

        self.audit.log_attachment_diff(
            agent_id=agent.id,
            agent_config_id=config_id,
            before_ids=before_upload_ids,
            after_ids=uuids,
            attached_action=AgentAuditAction.KB_ATTACHED,
            detached_action=AgentAuditAction.KB_DETACHED,
            resource_type=AuditResourceType.KNOWLEDGE_BASE,
        )

    def _sync_phone_numbers(self, agent: Agent, phone_numbers: List[Dict[str, Any]]) -> None:
        """Sync phone numbers for an agent.

        Each entry is {number, channel_id, label?}. Numbers in the list are
        created (if new) or kept. Numbers currently assigned to this agent
        but NOT in the list are deleted from DB.
        """
        incoming_numbers = {entry["number"] for entry in phone_numbers}

        # Numbers currently mapped to this agent — captured before the sync so we can
        # invalidate the phone_to_agent cache for every number that gains/loses a mapping.
        prior_numbers = {
            n for (n,) in self.db.query(PhoneNumber.number).filter(
                PhoneNumber.agent_id == agent.id, PhoneNumber.organization_id == self.org_id
            ).all()
        }

        # Delete phone numbers removed from this agent
        if incoming_numbers:
            self.db.query(PhoneNumber).filter(
                PhoneNumber.agent_id == agent.id, PhoneNumber.organization_id == self.org_id,
                PhoneNumber.number.notin_(incoming_numbers),
            ).delete(synchronize_session=False)
        else:
            self.db.query(PhoneNumber).filter(
                PhoneNumber.agent_id == agent.id, PhoneNumber.organization_id == self.org_id,
            ).delete(synchronize_session=False)

        # Create or update each number
        for entry in phone_numbers:
            number = entry["number"]
            channel_id = UUID(str(entry["channel_id"]))
            label = entry.get("label")

            existing = (
                self.db.query(PhoneNumber)
                .filter(PhoneNumber.number == number, PhoneNumber.organization_id == self.org_id)
                .first()
            )
            if existing:
                # Number already in DB — reassign to this agent
                if existing.agent_id and existing.agent_id != agent.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Phone number {number} is already assigned to another agent",
                    )
                existing.agent_id = agent.id
                existing.channel_id = channel_id
                if label is not None:
                    existing.label = label
            else:
                # New number — insert into DB
                self.db.add(PhoneNumber(
                    number=number,
                    channel_id=channel_id,
                    agent_id=agent.id,
                    label=label,
                    organization_id=self.org_id,
                ))

        # Invalidate the phone→agent routing cache for every number that changed mapping
        # (added or removed) so the next call routes to the correct agent immediately.
        from core.services.redis_service import cache_delete
        for num in prior_numbers | incoming_numbers:
            if num:
                cache_delete(f"phone_to_agent:{num.strip()}")

        self.audit.log_attachment_diff(
            agent_id=agent.id,
            agent_config_id=None,
            before_ids=prior_numbers,
            after_ids=incoming_numbers,
            attached_action=AgentAuditAction.PHONE_ATTACHED,
            detached_action=AgentAuditAction.PHONE_DETACHED,
            resource_type=AuditResourceType.PHONE_NUMBER,
        )

    def _sync_agent_channels(self, agent: Agent, channel_ids: List[str]) -> None:
        web_types = set(supported_providers())
        incoming = set()
        for raw in channel_ids:
            cid = UUID(str(raw))
            channel = (
                self.db.query(Channel)
                .filter(Channel.id == cid, Channel.organization_id == self.org_id)
                .first()
            )
            if not channel:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found"
                )
            if (channel.channel_type or "").lower() not in web_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Channel {channel.name} is not a web-call channel",
                )
            incoming.add(cid)

        before_channel_ids = {
            cid for (cid,) in self.db.query(AgentChannel.channel_id).filter(
                AgentChannel.agent_id == agent.id, AgentChannel.organization_id == self.org_id
            ).all()
        }

        existing = self.db.query(AgentChannel).filter(
            AgentChannel.agent_id == agent.id, AgentChannel.organization_id == self.org_id
        )
        if incoming:
            existing.filter(AgentChannel.channel_id.notin_(incoming)).delete(synchronize_session=False)
        else:
            existing.delete(synchronize_session=False)

        bound = {
            cid for (cid,) in self.db.query(AgentChannel.channel_id).filter(
                AgentChannel.agent_id == agent.id, AgentChannel.organization_id == self.org_id
            ).all()
        }
        for cid in incoming:
            if cid in bound:
                continue
            self.db.add(AgentChannel(
                agent_id=agent.id,
                channel_id=cid,
                slug=secrets.token_urlsafe(12),
                organization_id=self.org_id,
            ))

        self.audit.log_attachment_diff(
            agent_id=agent.id,
            agent_config_id=None,
            before_ids=before_channel_ids,
            after_ids=incoming,
            attached_action=AgentAuditAction.WEB_CHANNEL_ATTACHED,
            detached_action=AgentAuditAction.WEB_CHANNEL_DETACHED,
            resource_type=AuditResourceType.WEB_CHANNEL,
        )

    def agent_response(
        self, agent: Agent, config: Optional[AgentConfig] = None
    ) -> Dict[str, Any]:
        """Serialise an agent + a chosen config version.

        ``config`` is optional: when omitted the live config (resolved via
        ``published_config_id``, falling back to the latest version) is used.
        Pass an explicit ``AgentConfig`` to render the agent at a non-live
        version for the version-preview endpoint.
        """
        # Refresh to get latest state
        self.db.refresh(agent)

        if config is None:
            config = self._resolve_current_config(agent)

        # The model picker persists the selected LLM into config.llm_settings.model_id
        # (a models.id), so resolve a human-readable name for the detail/overview.
        # Fall back to the denormalised agent.llm_model column for older agents.
        llm_model_name = agent.llm_model
        if config and isinstance(config.llm_settings, dict):
            model_id = config.llm_settings.get("model_id")
            if model_id:
                from core.models.model import Model

                model = self.db.query(Model).filter(Model.id == model_id).first()
                if model:
                    llm_model_name = model.display_name or model.name or llm_model_name

        result: Dict[str, Any] = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "agent_type": agent.agent_type,
            "llm_model": llm_model_name,
            "is_active": agent.is_active,
            "created_by_user_id": str(agent.created_by_user_id) if agent.created_by_user_id else None,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }

        if config:
            result["config"] = {
                "id": str(config.id),
                "version": config.version,
                "first_message": config.first_message,
                "end_call_message": config.end_call_message,
                "system_prompt_template": config.system_prompt_template,
                "conversation_history_token_limit": config.conversation_history_token_limit,
                "language_id": str(config.language_id) if config.language_id else None,
                "knowledge_model_id": str(config.knowledge_model_id) if config.knowledge_model_id else None,
                "llm_settings": config.llm_settings,
                "voice_settings": config.voice_settings,
                "stt_settings": config.stt_settings,
                "conversation_settings": config.conversation_settings,
                "mode": getattr(config, "mode", "prompt") or "prompt",
                "workflow_id": str(config.workflow_id) if getattr(config, "workflow_id", None) else None,
            }
        else:
            result["config"] = None

        # Attachments are per-version: filter the join tables by the resolved
        # config's id so previewing v9 shows v9's tools / MCP / KB. When the
        # agent has no config yet (impossible in practice but defensive), the
        # filter on `IS NULL` correctly returns an empty list.
        config_id_for_attachments = config.id if config else None

        # Tools
        tool_rows = (
            self.db.query(Tool)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(
                AgentTool.agent_id == agent.id,
                AgentTool.organization_id == self.org_id,
                AgentTool.agent_config_id == config_id_for_attachments,
            )
            .all()
        )
        result["tools"] = [{"id": str(t.id), "name": t.name} for t in tool_rows]

        # MCP Servers
        mcp_rows = (
            self.db.query(McpServer)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent.id,
                AgentMcpServer.organization_id == self.org_id,
                AgentMcpServer.agent_config_id == config_id_for_attachments,
            )
            .all()
        )
        result["mcp_servers"] = [{"id": str(ms.id), "name": ms.name} for ms in mcp_rows]

        # Documents (knowledge base uploads)
        kb_rows = (
            self.db.query(Upload)
            .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
            .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
            .filter(
                AgentKnowledgeBase.agent_id == agent.id,
                AgentKnowledgeBase.organization_id == self.org_id,
                AgentKnowledgeBase.agent_config_id == config_id_for_attachments,
            )
            .all()
        )
        result["documents"] = [
            {"id": str(u.id), "file_path": u.file_path, "file_name": u.file_name}
            for u in kb_rows
        ]

        # Phone numbers
        phone_rows = (
            self.db.query(PhoneNumber)
            .filter(PhoneNumber.agent_id == agent.id, PhoneNumber.organization_id == self.org_id)
            .all()
        )
        result["phone_numbers"] = [
            {
                "id": str(p.id),
                "number": p.number,
                "channel_id": str(p.channel_id) if p.channel_id else None,
                "label": p.label,
            }
            for p in phone_rows
        ]

        channel_rows = (
            self.db.query(AgentChannel, Channel)
            .join(Channel, Channel.id == AgentChannel.channel_id)
            .filter(AgentChannel.agent_id == agent.id, AgentChannel.organization_id == self.org_id)
            .all()
        )
        result["web_channels"] = [
            {
                "id": str(ac.id),
                "channel_id": str(ac.channel_id),
                "channel_type": ch.channel_type,
                "name": ch.name,
                "slug": ac.slug,
            }
            for ac, ch in channel_rows
        ]

        # Version history (single query — driving the editor's version selector)
        version_rows = (
            self.query(AgentConfig)
            .filter(AgentConfig.agent_id == agent.id, AgentConfig.deleted_at.is_(None))
            .order_by(AgentConfig.version.desc())
            .all()
        )
        live_id = agent.published_config_id
        result["versions"] = [
            self.version_response(v, is_live=(v.id == live_id)) for v in version_rows
        ]

        return result
