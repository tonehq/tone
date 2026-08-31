"""Build a ``CheckContext`` from an agent + config, in a few batched queries.

Keeping this separate from ``runner.py`` isolates the "how do I gather all the
data one check might need" concern from "how do I run the checks and aggregate
results". Individual checks never see this module — they only see the finished
``CheckContext``.

Two module-level helpers in ``core/services/pipeline/service_resolver.py`` are
imported directly to avoid duplicating their logic:

- ``get_active_agent_config`` — resolves the "check this config" fallback chain
  when the caller didn't pass an explicit ``config_id``.
- ``_config_service_ids`` — normalises UUID extraction from the ``llm_settings``
  / ``stt_settings`` / ``voice_settings`` JSONB blobs. It's underscored (module-
  private by convention) but the shape is stable — it feeds the same fields the
  runtime resolver reads at call time, which is exactly what we want here.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_channel import AgentChannel
from core.models.agent_config import AgentConfig
from core.models.agent_knowledge_base import AgentKnowledgeBase
from core.models.agent_mcp_server import AgentMcpServer
from core.models.agent_tool import AgentTool
from core.models.api_key import ApiKey
from core.models.channel import Channel
from core.models.knowledge_base import KnowledgeBase
from core.models.mcp_server import McpServer
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.models.phone_number import PhoneNumber
from core.models.tool import Tool
from core.services.pipeline.service_resolver import (
    _config_service_ids,
    get_active_agent_config,
)
from core.services.readiness.base import CheckContext, ServiceSpec
from core.services.readiness.schemas import Depth
from core.utils.encryption import decrypt
from core.utils.oauth_resolution import stamp_effective


class ContextBuilder:
    """Assembles a ``CheckContext`` for a given agent + config version.

    One instance per readiness run — cheap to construct and discard. Each
    ``build_for_config`` call issues a small, bounded number of queries and
    then hands the fully-populated context to the runner.
    """

    def __init__(self, db: Session, org_id: UUID):
        self.db = db
        self.org_id = org_id

    def resolve_config(
        self, agent: Agent, config_id: Optional[str] = None
    ) -> Optional[AgentConfig]:
        """Return the ``AgentConfig`` to check.

        Priority: explicit ``config_id`` (must belong to this agent and org) →
        the agent's published version → the agent's default/latest non-template
        version (via the shared resolver helper).
        """
        if config_id:
            row = (
                self.db.query(AgentConfig)
                .filter(
                    AgentConfig.id == config_id,
                    AgentConfig.agent_id == agent.id,
                    AgentConfig.organization_id == self.org_id,
                    AgentConfig.deleted_at.is_(None),
                )
                .first()
            )
            return row
        return get_active_agent_config(self.db, agent)

    def build(
        self, agent: Agent, config: Optional[AgentConfig], depth: Depth
    ) -> CheckContext:
        """Build a fully-populated context. Handles the "config is None" edge
        case by returning a bare context whose checks all trip on the
        Agent/Config category rather than crashing lower down."""
        if config is None:
            return CheckContext(
                agent=agent,
                config=None,
                org_id=self.org_id,
                db=self.db,
                depth=depth,
            )

        ids = _config_service_ids(config)
        provider_by_id, model_by_id = self._fetch_providers_models(
            ids["provider_ids"], ids["model_ids"]
        )
        keys_by_svc = self._fetch_api_keys(ids["provider_ids"])
        voice_row = self._fetch_voice(ids["voice_uuid"])

        llm = self._build_spec(
            settings=config.llm_settings,
            provider_id=ids["llm_pid"],
            model_id=ids["llm_mid"],
            service_type="llm",
            providers=provider_by_id,
            models=model_by_id,
            keys=keys_by_svc,
        )
        stt = self._build_spec(
            settings=config.stt_settings,
            provider_id=ids["stt_pid"],
            model_id=ids["stt_mid"],
            service_type="stt",
            providers=provider_by_id,
            models=model_by_id,
            keys=keys_by_svc,
        )
        tts = self._build_spec(
            settings=config.voice_settings,
            provider_id=ids["tts_pid"],
            model_id=ids["tts_mid"],
            service_type="tts",
            providers=provider_by_id,
            models=model_by_id,
            keys=keys_by_svc,
        )

        return CheckContext(
            agent=agent,
            config=config,
            org_id=self.org_id,
            db=self.db,
            depth=depth,
            is_s2s=bool((config.llm_settings or {}).get("is_s2s")),
            llm=llm,
            stt=stt,
            tts=tts,
            voice=voice_row,
            phone_numbers=self._fetch_phone_numbers(agent.id),
            tools=self._fetch_linked_tools(agent.id, config.id),
            knowledge_bases=self._fetch_linked_knowledge_bases(agent.id, config.id),
            mcp_servers=self._fetch_linked_mcp_servers(agent.id, config.id),
            channels=self._fetch_linked_channels(agent.id),
        )

    # ── batched loaders ────────────────────────────────────────────────────

    def _fetch_providers_models(
        self, provider_ids: set, model_ids: set
    ) -> Tuple[Dict[UUID, ModelProvider], Dict[UUID, Model]]:
        providers: Dict[UUID, ModelProvider] = {}
        models: Dict[UUID, Model] = {}
        if provider_ids:
            for row in self.db.query(ModelProvider).filter(
                ModelProvider.id.in_(provider_ids)
            ):
                providers[row.id] = row
        if model_ids:
            for row in self.db.query(Model).filter(Model.id.in_(model_ids)):
                models[row.id] = row
        return providers, models

    def _fetch_api_keys(
        self, provider_ids: set
    ) -> Dict[Tuple[UUID, Optional[str]], ApiKey]:
        """Return ``{(provider_id, service_type): ApiKey}``, is_default first.

        Matches the runtime resolver's key-lookup semantics — including the
        "``NULL`` ``service_type`` covers any service for the provider"
        fallback — so a green readiness check means the resolver will find the
        same key at call time.
        """
        if not provider_ids or not self.org_id:
            return {}
        keys = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.provider_id.in_(provider_ids),
                ApiKey.organization_id == self.org_id,
                ApiKey.is_active.is_(True),
            )
            .order_by(ApiKey.is_default.desc())
            .all()
        )
        indexed: Dict[Tuple[UUID, Optional[str]], ApiKey] = {}
        for k in keys:
            indexed.setdefault((k.provider_id, k.service_type), k)
        return indexed

    def _fetch_voice(self, voice_uuid: Optional[UUID]) -> Optional[ModelVoice]:
        if not voice_uuid:
            return None
        return (
            self.db.query(ModelVoice)
            .filter(ModelVoice.id == voice_uuid)
            .first()
        )

    def _fetch_phone_numbers(self, agent_id: UUID) -> List[PhoneNumber]:
        return (
            self.db.query(PhoneNumber)
            .filter(
                PhoneNumber.agent_id == agent_id,
                PhoneNumber.organization_id == self.org_id,
            )
            .all()
        )

    def _fetch_linked_channels(self, agent_id: UUID) -> List[Channel]:
        """Return telephony ``Channel`` rows linked to the agent.

        Two linkage paths in the schema, both authoritative:

        * ``AgentChannel(agent_id, channel_id)`` — direct link, used by
          outbound-only agents that own a channel but no assigned number.
        * ``PhoneNumber(agent_id, channel_id)`` — the number-owns-channel
          path, which is how every inbound agent in prod currently links.

        Union both and dedupe by ``channel.id`` so the transport-credit
        probe fires regardless of which shape the agent uses. Non-telephony
        types (``daily``, ``websocket``, ``livekit``) are excluded — they
        have no provider-side balance / credit surface to probe.
        """
        telephony_types = ("twilio", "telnyx", "plivo", "exotel")

        via_agent_channel = (
            self.db.query(Channel)
            .join(AgentChannel, AgentChannel.channel_id == Channel.id)
            .filter(
                AgentChannel.agent_id == agent_id,
                AgentChannel.organization_id == self.org_id,
                Channel.organization_id == self.org_id,
                Channel.channel_type.in_(telephony_types),
            )
        )
        via_phone_number = (
            self.db.query(Channel)
            .join(PhoneNumber, PhoneNumber.channel_id == Channel.id)
            .filter(
                PhoneNumber.agent_id == agent_id,
                PhoneNumber.organization_id == self.org_id,
                Channel.organization_id == self.org_id,
                Channel.channel_type.in_(telephony_types),
            )
        )
        seen: Dict[UUID, Channel] = {}
        for row in via_agent_channel.all() + via_phone_number.all():
            seen.setdefault(row.id, row)
        return list(seen.values())

    def _fetch_linked_tools(self, agent_id: UUID, config_id: UUID) -> List[Tool]:
        # Selects the per-version override alongside the Tool row and stamps the
        # winner on `.effective_oauth_connection_id` — same shape the runtime
        # loader (`custom_tool_service.get_custom_tools_for_agent`) produces, so
        # the OAuth resolver in deep checks reads the same connection the
        # pipeline would at call time.
        rows = (
            self.db.query(Tool, AgentTool.oauth_connection_id)
            .join(AgentTool, AgentTool.tool_id == Tool.id)
            .filter(
                AgentTool.agent_id == agent_id,
                AgentTool.agent_config_id == config_id,
                # Defensive: never probe a soft-deleted tool even if a stale
                # link lingers. Tools are hard-deleted today (delete_tool also
                # removes AgentTool rows), so this is future-proofing that
                # changes nothing now — mirrors the AgentConfig.deleted_at guard
                # in resolve_config.
                Tool.deleted_at.is_(None),
            )
            .all()
        )
        tools: List[Tool] = []
        for tool, link_oauth in rows:
            stamp_effective(tool, link_oauth)
            tools.append(tool)
        return tools

    def _fetch_linked_knowledge_bases(
        self, agent_id: UUID, config_id: UUID
    ) -> List[KnowledgeBase]:
        return (
            self.db.query(KnowledgeBase)
            .join(
                AgentKnowledgeBase,
                AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id,
            )
            .filter(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.agent_config_id == config_id,
                # Defensive soft-delete guard (see _fetch_linked_tools). KB
                # entities aren't deleted today, so this is a no-op now.
                KnowledgeBase.deleted_at.is_(None),
            )
            .all()
        )

    def _fetch_linked_mcp_servers(
        self, agent_id: UUID, config_id: UUID
    ) -> List[McpServer]:
        # Select the per-version OAuth override alongside the McpServer row and
        # stamp the winner onto ``server.effective_oauth_connection_id`` — same
        # shape ``mcp_tool_service._fetch_agent_mcp_servers`` produces at runtime,
        # so the OAuth resolver in deep checks reads the same connection the
        # pipeline would at call time (agent-link override → entity default).
        rows = (
            self.db.query(McpServer, AgentMcpServer.oauth_connection_id)
            .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
            .filter(
                AgentMcpServer.agent_id == agent_id,
                AgentMcpServer.agent_config_id == config_id,
                # Defensive soft-delete guard (see _fetch_linked_tools). MCP
                # servers are hard-deleted today, so this is a no-op now.
                McpServer.deleted_at.is_(None),
            )
            .all()
        )
        servers: List[McpServer] = []
        for server, link_oauth in rows:
            stamp_effective(server, link_oauth)
            servers.append(server)
        return servers

    # ── per-service spec builder ───────────────────────────────────────────

    def _build_spec(
        self,
        settings: Optional[Dict[str, Any]],
        provider_id: Optional[UUID],
        model_id: Optional[UUID],
        service_type: str,
        providers: Dict[UUID, ModelProvider],
        models: Dict[UUID, Model],
        keys: Dict[Tuple[UUID, Optional[str]], ApiKey],
    ) -> ServiceSpec:
        spec = ServiceSpec(
            settings=dict(settings or {}),
            provider_id=provider_id,
            model_id=model_id,
            provider=providers.get(provider_id) if provider_id else None,
            model=models.get(model_id) if model_id else None,
        )
        if provider_id:
            spec.api_key = keys.get((provider_id, service_type)) or keys.get(
                (provider_id, None)
            )
        if spec.api_key is not None:
            spec.decrypted_key = _safe_decrypt(spec.api_key)
        return spec


def _safe_decrypt(api_key: ApiKey) -> Optional[str]:
    """Decrypt an API key without raising — a decrypt failure is a first-class
    result the checks want to report on (usually a rotated ``JWT_SECRET_KEY``),
    not an exception that aborts the whole readiness run."""
    try:
        return decrypt(api_key.encrypted_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[readiness] decrypt failed for api_key {}: {}", api_key.id, exc
        )
        return None
