from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any
import time
import uuid as uuid_lib
from uuid import UUID
import traceback

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers
from core.models.service_provider import ServiceProvider
from core.models.account import Account
from core.models.model_instance import ModelInstance
from core.models.enums import AgentType
from core.services.agent_config_service import AgentConfigService
from core.services.channel_service import ChannelService
from core.models.agent_channel import AgentChannel

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
            if channel_data and channel_data.get("type"):
                channel_svc = ChannelService(self.db, user_id=self.user_id, org_id=self.org_id)
                channel = channel_svc.get_or_create_channel_by_type(
                    channel_type=channel_data["type"],
                    meta_data=channel_data.get("meta_data"),
                    created_by=created_by,
                    auto_commit=False,
                )
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

    def delete_agent(self, agent_id: int):
        agent = self.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )
        self.query(AgentChannelPhoneNumbers).filter(AgentChannelPhoneNumbers.agent_id == agent.id).delete()
        self.query(AgentConfig).filter(AgentConfig.agent_id == agent.id).delete()
        self.query(AgentChannel).filter(AgentChannel.agent_id == agent.id).delete()
        self.db.delete(agent)
        self.db.commit()
        return {"message": "Agent deleted successfully"}

    def get_all_agents(self, agent_id=None, created_by=None):
        """Return all agents with joined agent_config. If agent_id is given, return only that agent."""

        q = (
            self.query(Agent)
            .outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
            .add_entity(AgentConfig)
        )
        if agent_id is not None:
            q = q.filter(Agent.id == agent_id)
        if created_by is not None:
            q = q.filter(Agent.created_by == created_by)
        rows = q.order_by(Agent.id).all()

        result = []
        for agent, config in rows:
            result.append(self._agent_response_item(agent, config))
        return result
