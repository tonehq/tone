"""Resolve an agent's LLM eval config from the DB.

The eval must score the agent's ACTUAL config (the LLM the agent would use
on a real call), NOT a synthetic one — otherwise the developer's "did my
system-prompt change help?" question isn't answerable. This loader walks
``agents.published_config_id → agent_configs.{system_prompt_template,
llm_settings}`` and hands back a plain ``AgentEvalConfig`` dataclass the
service reads once and then closes the DB session (so no pool connection is
held across the LLM loop).

Mirrors ``core/services/pipeline/service_resolver.py:_build_service_specs``
LLM branch — same JSONB keys (``provider_id``, ``model_id``,
``temperature``, …), same decrypt path — so what the eval scores matches
what production dials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.services.evals.errors import AgentLlmEvalConfigError
from core.services.rag.provider_keys import ProviderKeyService


# JSONB keys that identify the provider / model / snapshot — mirrors
# ``core/services/pipeline/service_resolver.py`` so the two paths can't drift.
_LLM_PROVIDER_KEY = "provider_id"
_LLM_MODEL_ID_KEY = "model_id"
_LLM_MODEL_NAME_KEY = "model"
# Keys we pull into the JSONB snapshot column verbatim (the hybrid schema —
# typed columns for model/provider/system-prompt, JSONB for the rest).
_SNAPSHOT_KEYS = ("temperature", "top_p", "top_k", "max_tokens")


@dataclass
class AgentEvalConfig:
    """Snapshot of every attribute the LLM loop needs — resolved once, then
    the caller can close the session. The service passes this to
    ``chat_complete`` (for the agent's own LLM) and stamps the snapshot
    fields onto every persisted result row.
    """

    agent_id: UUID
    agent_name: str
    organization_id: UUID
    agent_config_id: Optional[UUID]
    llm_model: Optional[str]
    llm_provider: Optional[str]
    llm_api_key: Optional[str]
    system_prompt: Optional[str]
    llm_settings_snapshot: dict
    # Kwargs pulled out of the snapshot for ``chat_complete`` — kept
    # separate so the persisted snapshot stays raw (no defaults/coercion).
    temperature: float
    max_tokens: int
    # Workflow-mode extension. ``mode`` mirrors ``agent_configs.mode``; when
    # it's ``"workflow"``, ``workflow_serialized`` holds the markdown playbook
    # rendered by ``serialize_graph_for_llm`` — the SAME text the runtime
    # injects as the system prompt (see ``pipeline/service_resolver.py``).
    # Both defaults keep prompt-mode agents byte-identical to the old shape.
    mode: str = "prompt"
    workflow_id: Optional[UUID] = None
    workflow_serialized: Optional[str] = None
    # Tool + MCP snapshot for Phase 2 (tool-aware eval). Both default to
    # empty lists so prompt-mode agents with no tools attached see zero
    # behavior change downstream — every consumer branches on truthiness.
    #
    # ``tools`` uses OpenAI tool-call shape:
    #   [{"type": "function", "function": {"name", "description", "parameters"}}]
    # so it drops directly into ``chat_complete_with_tools``.
    #
    # ``mcp_server_summaries`` is name+description only (no live tool
    # enumeration) — the judge uses it to invent MCP-aware scenarios;
    # the executor doesn't attempt MCP calls.
    tools: List[dict] = field(default_factory=list)
    mcp_server_summaries: List[dict] = field(default_factory=list)

    @property
    def effective_system_prompt(self) -> Optional[str]:
        """Return the string the generator + executor should treat as the
        agent's "instructions". Workflow playbook wins when present; falls
        back to ``system_prompt`` for prompt-mode agents. Keeps the
        prompt-vs-workflow branch in ONE place instead of at every call site.
        """
        return self.workflow_serialized or self.system_prompt


class AgentConfigLoader:
    """Loads and freezes the LLM-related bits of an agent's published config
    for one eval run. Injected into ``AgentLlmEvalService`` so tests can
    stub the DB path out without patching module globals.
    """

    def load_for_eval(
        self,
        db: Session,
        agent_id: Any,
        *,
        organization_id: Optional[UUID] = None,
    ) -> AgentEvalConfig:
        """Resolve the agent's published config + decrypted LLM API key.

        Raises ``AgentLlmEvalConfigError`` with an actionable message when:
        - the agent row doesn't exist,
        - the agent has no ``published_config_id`` (unpublished draft),
        - the config carries no LLM model / provider,
        - or no API key is configured for that provider on the org.

        When ``organization_id`` is supplied the lookup is tenant-scoped —
        the CLI runs single-tenant so this is optional today; a future
        API adapter MUST pass ``org_id`` from ``JWTClaims`` to prevent
        cross-tenant reads of the decrypted API key.
        """
        q = db.query(Agent).filter(Agent.id == agent_id)
        if organization_id is not None:
            q = q.filter(Agent.organization_id == organization_id)
        agent = q.first()
        if agent is None:
            raise AgentLlmEvalConfigError(f"Agent {agent_id} not found")

        if agent.published_config_id is None:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} has no published config — publish the "
                "agent before running an LLM eval."
            )

        cfg: Optional[AgentConfig] = (
            db.query(AgentConfig)
            .filter(AgentConfig.id == agent.published_config_id)
            .first()
        )
        if cfg is None:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} published_config_id "
                f"{agent.published_config_id} points at a missing agent_configs row."
            )

        llm_settings = dict(cfg.llm_settings or {})

        # Resolve the concrete model name — either baked directly on
        # ``llm_settings.model`` (some templates) or via the ``model_id`` UUID
        # (the resolver's canonical path). Missing model = the agent has never
        # been fully configured; we can't dial the LLM either.
        model_name: Optional[str] = llm_settings.get(_LLM_MODEL_NAME_KEY)
        model_id = llm_settings.get(_LLM_MODEL_ID_KEY)
        provider_slug: Optional[str] = None
        model_row: Optional[Model] = None
        if model_id:
            model_row = db.query(Model).filter(Model.id == model_id).first()
            if model_row and not model_name:
                model_name = model_row.name

        # Provider slug — resolve via the ``provider_id`` FK on the settings.
        # ``ModelProvider.provider_id`` is the slug ``chat_complete`` /
        # ``ProviderKeyService`` expect (openai / anthropic / google / …).
        provider_id = llm_settings.get(_LLM_PROVIDER_KEY)
        if provider_id:
            prov = (
                db.query(ModelProvider)
                .filter(ModelProvider.id == provider_id)
                .first()
            )
            if prov:
                provider_slug = prov.provider_id
        elif model_row:
            prov = (
                db.query(ModelProvider)
                .filter(ModelProvider.id == model_row.provider_id)
                .first()
            )
            if prov:
                provider_slug = prov.provider_id

        if not model_name:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} config has no LLM model — set an LLM "
                "on the agent before running an LLM eval."
            )
        if not provider_slug:
            raise AgentLlmEvalConfigError(
                f"Agent {agent.name!r} config has no LLM provider — set an "
                "LLM provider on the agent before running an LLM eval."
            )

        api_key = ProviderKeyService.get_key(db, agent.organization_id, provider_slug)
        if not api_key:
            raise AgentLlmEvalConfigError(
                f"No {provider_slug!r} API key configured for organisation "
                f"{agent.organization_id} (needed by agent {agent.name!r})."
            )

        snapshot = {k: llm_settings[k] for k in _SNAPSHOT_KEYS if k in llm_settings}

        # ``chat_complete`` needs a numeric temperature and max_tokens. Pull
        # them out of the raw settings with safe fallbacks (agents that never
        # touched the sliders keep the OpenAI defaults).
        temperature = _coerce_float(llm_settings.get("temperature"), default=0.0)
        max_tokens = _coerce_int(llm_settings.get("max_tokens"), default=1024)

        # Workflow mode: render the playbook once here so downstream (generator
        # + executor) never has to touch the workflow tables. Uses the SAME
        # serializer + name maps as the runtime resolver — see
        # ``core/services/pipeline/service_resolver.py`` — so what the judge
        # grades against is byte-identical to what the bot actually runs.
        # Tool + MCP snapshot (Phase 2). Both helpers are best-effort —
        # a failure to snapshot must NOT block the eval, because a plain
        # prompt-mode agent with no tools attached is fully valid and
        # snapshotting should return an empty list. Any unexpected error
        # here is logged with a full traceback and treated as "no tools /
        # no MCP" so the eval still runs.
        #
        # Loaded BEFORE workflow serialization so the playbook can dedup
        # apiRequest function names against the agent's real tool names —
        # keeping the eval-serialized playbook byte-identical to what the
        # runtime pipeline would inject when an apiRequest node's
        # sanitized name collides with a real tool.
        tools = self._snapshot_tools(agent_id=agent.id)
        mcp_server_summaries = self._snapshot_mcp_servers(agent_id=agent.id)

        mode = getattr(cfg, "mode", "prompt") or "prompt"
        workflow_id = getattr(cfg, "workflow_id", None)
        workflow_serialized: Optional[str] = None
        if mode == "workflow":
            workflow_serialized = self._serialize_workflow(
                db,
                agent_name=agent.name,
                workflow_id=workflow_id,
                organization_id=agent.organization_id,
                real_tool_names={
                    t["function"]["name"]
                    for t in tools
                    if isinstance(t, dict)
                    and isinstance(t.get("function"), dict)
                    and t["function"].get("name")
                },
            )

        return AgentEvalConfig(
            agent_id=agent.id,
            agent_name=agent.name,
            organization_id=agent.organization_id,
            agent_config_id=cfg.id,
            llm_model=model_name,
            llm_provider=provider_slug,
            llm_api_key=api_key,
            system_prompt=cfg.system_prompt_template,
            llm_settings_snapshot=snapshot,
            temperature=temperature,
            max_tokens=max_tokens,
            mode=mode,
            workflow_id=workflow_id,
            workflow_serialized=workflow_serialized,
            tools=tools,
            mcp_server_summaries=mcp_server_summaries,
        )

    def _serialize_workflow(
        self,
        db: Session,
        *,
        agent_name: str,
        workflow_id: Optional[UUID],
        organization_id: UUID,
        real_tool_names: Optional[set] = None,
    ) -> str:
        """Load the assigned workflow's working graph and render it into the
        markdown playbook the runtime injects as the system prompt.

        Fail-loud with an actionable ``AgentLlmEvalConfigError`` on every
        broken-state we can hit (no workflow assigned, workflow deleted,
        no working version, empty graph) — the eval can't proceed with
        no instructions and the user needs to know which specific gap to fix.
        """
        if workflow_id is None:
            raise AgentLlmEvalConfigError(
                f"Agent {agent_name!r} is configured for workflow mode but has "
                "no workflow assigned. Assign a workflow before running an "
                "LLM eval."
            )

        # Local imports keep the sqlalchemy graph out of prompt-mode hot paths
        # (this branch only runs when mode='workflow').
        from core.models.workflow import Workflow, WorkflowVersion
        from core.services.workflow.prompt_serializer import (
            serialize_graph_for_llm,
        )
        from core.services.workflow.tool_names import (
            workflow_api_fn_names,
            workflow_tool_names,
        )

        wf = (
            db.query(Workflow)
            .filter(
                Workflow.id == workflow_id,
                Workflow.organization_id == organization_id,
            )
            .first()
        )
        if wf is None or not wf.draft_version_id:
            raise AgentLlmEvalConfigError(
                f"Agent {agent_name!r} points at workflow {workflow_id} which "
                "has no working version. Open the workflow and save it before "
                "running an LLM eval."
            )
        ver = (
            db.query(WorkflowVersion)
            .filter(
                WorkflowVersion.id == wf.draft_version_id,
                WorkflowVersion.organization_id == organization_id,
            )
            .first()
        )
        if ver is None or not ver.graph or not (ver.graph.get("nodes") or []):
            raise AgentLlmEvalConfigError(
                f"Agent {agent_name!r} workflow has an empty graph — add at "
                "least one step before running an LLM eval."
            )

        # Pass ``real_tool_names`` as ``taken`` so apiRequest nodes get the
        # SAME deduped function names the runtime pipeline registers. This
        # keeps the eval-serialized playbook byte-identical to what the
        # bot actually runs — critical for the tool_selection metric, which
        # matches expected_tools (generated against this playbook) against
        # actual_tools (emitted by the runtime-facing LLM). ``None`` /
        # empty set are safe: the workflow_api_fn_names helper treats
        # falsy ``taken`` the same as an empty set (no external names to
        # avoid), so prompt-mode-only agents behave identically to before.
        tool_names = workflow_tool_names(db, ver.graph, organization_id)
        api_fn_names = workflow_api_fn_names(ver.graph, taken=real_tool_names)
        serialized = serialize_graph_for_llm(
            ver.graph, tool_names=tool_names, api_fn_names=api_fn_names,
        )
        if not serialized.strip():
            raise AgentLlmEvalConfigError(
                f"Agent {agent_name!r} workflow rendered as empty text — the "
                "workflow has no reachable instructions."
            )
        logger.info(
            "[agent-llm-eval-loader] workflow serialized agent={} workflow_id={} bytes={}",
            agent_name, workflow_id, len(serialized),
        )
        return serialized

    def _snapshot_tools(self, *, agent_id: UUID) -> List[dict]:
        """Return the agent's active custom tools in OpenAI tool-call shape,
        ready to hand to ``chat_complete_with_tools``.

        Reuses ``serialize_agent_tools`` (the SAME serializer the runtime
        pipeline uses to cache tools) so the tool JSON the judge sees is
        the same JSON production dials. MCP-backed tools are excluded here —
        they surface under the MCP block in the generator prompt instead of
        as individual tool entries.

        Snapshot failures are non-fatal: an agent without tools attached is
        the majority case, and every downstream consumer branches on
        ``bool(agent_config.tools)`` — an empty list means the tool-aware
        code paths are skipped entirely, matching pre-Phase-2 behavior.
        """
        # Local import — heavy transitive graph (Pipecat, custom-tool runtime);
        # only loaded when the eval loader is actually invoked.
        from core.services.custom_tool_service import (
            sanitize_tool_name,
            serialize_agent_tools,
        )

        try:
            raw = serialize_agent_tools(agent_id)
        except Exception:
            logger.exception(
                "[agent-llm-eval-loader] tool snapshot failed agent={} — treating as no tools",
                agent_id,
            )
            return []

        out: List[dict] = []
        for t in raw or []:
            # Exclude MCP-backed tools from the direct tool list — they
            # surface via ``mcp_server_summaries`` and would double-count
            # in the generator prompt otherwise.
            if t.get("mcp_server_id"):
                continue
            name = t.get("name") or ""
            if not name:
                continue
            out.append({
                "type": "function",
                "function": {
                    "name": sanitize_tool_name(name),
                    "description": t.get("description") or "",
                    "parameters": t.get("parameters") or {
                        "type": "object",
                        "properties": {},
                    },
                },
            })
        return out

    def _snapshot_mcp_servers(self, *, agent_id: UUID) -> List[dict]:
        """Return ``[{name, description}]`` for every active MCP server on
        the agent's published config. Deliberately does NOT enumerate the
        tools each MCP exposes — that would require live network calls
        (see plan: MCP is server-name-only). The generator uses this list
        to invent MCP-aware scenarios; the executor is MCP-agnostic (it
        never attempts an MCP call).
        """
        from core.services.mcp_tool_service import get_mcp_servers_for_agent

        try:
            servers = get_mcp_servers_for_agent(agent_id)
        except Exception:
            logger.exception(
                "[agent-llm-eval-loader] MCP snapshot failed agent={} — treating as no MCP servers",
                agent_id,
            )
            return []

        out: List[dict] = []
        for s in servers or []:
            name = getattr(s, "name", None)
            if not name:
                continue
            out.append({
                "name": name,
                "description": getattr(s, "description", None) or "",
            })
        return out

    def resolve_agent_id(
        self,
        db: Session,
        agent_ref: str,
        *,
        organization_id: Optional[UUID] = None,
    ) -> UUID:
        """Resolve a CLI ``--agent`` argument to an agent UUID.

        ``agent_ref`` can be a UUID (matched to ``agents.id``) or a name
        (matched case-insensitively to ``agents.name``). Raises
        ``AgentLlmEvalConfigError`` for no-match / ambiguous cases so the CLI
        surfaces an actionable message instead of a stack trace.

        ``%`` / ``_`` in the caller-supplied name are ESCAPED before the
        ``ILIKE`` — otherwise ``--agent '%'`` would match every agent in
        every tenant. When ``organization_id`` is supplied both branches are
        tenant-scoped.
        """
        candidate = (agent_ref or "").strip()
        if not candidate:
            raise AgentLlmEvalConfigError("--agent must be a UUID or name; got empty string")

        try:
            uuid_val = UUID(candidate)
        except ValueError:
            uuid_val = None

        if uuid_val is not None:
            q = db.query(Agent).filter(Agent.id == uuid_val)
            if organization_id is not None:
                q = q.filter(Agent.organization_id == organization_id)
            agent = q.first()
            if agent is None:
                raise AgentLlmEvalConfigError(f"Agent with id {uuid_val} not found")
            return agent.id

        # Escape LIKE wildcards so a user-supplied '%'/'_' matches literally
        # (both would otherwise silently expand into a wildcard match across
        # the tenant / whole DB when unscoped).
        escaped = (
            candidate.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        q = db.query(Agent).filter(Agent.name.ilike(escaped, escape="\\"))
        if organization_id is not None:
            q = q.filter(Agent.organization_id == organization_id)
        matches = q.all()
        if not matches:
            raise AgentLlmEvalConfigError(f"No agent named {candidate!r} found")
        if len(matches) > 1:
            ids = ", ".join(str(m.id) for m in matches)
            raise AgentLlmEvalConfigError(
                f"Multiple agents named {candidate!r} — pass a UUID instead "
                f"(candidates: {ids})"
            )
        return matches[0].id


def _coerce_float(v: Any, *, default: float) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_int(v: Any, *, default: int) -> int:
    if v is None or v == "":
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default
