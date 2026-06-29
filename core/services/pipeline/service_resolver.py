"""Resolve an agent's service configuration from the database.

All DB access for the pipeline lives here. These functions read the agent's
published config, resolve providers + models + voice, and decrypt API keys into
a JSON-serializable "service spec" shape:

    {provider_name, api_key, model_name, metadata, model_meta_data}

This is the read/decrypt half of the pipeline; the construct half is `service_factory.py`
(which turns these specs into Pipecat service instances, with no DB access).

`load_agent_service_config` produces the full Redis-cached prefetch dict (the same shape
the subprocess receives), and is the single resolution path used by `PipelineParams.from_agent`.

Schema note: this matches the current Tone data model — `Agent.published_config_id`
→ `AgentConfig` (with JSONB `llm_settings`/`stt_settings`/`voice_settings`), providers
via `ModelProvider.slug`, model names via `Model.name`, voices via `ModelVoice.voice_id`,
and per-provider/org keys via `ApiKey(provider_id, service_type, encrypted_key)`. (This
is the logic that previously lived in `agent_runtime_resolver`, adapted to the
resolve→build split.)
"""

import time as _time
from typing import Any, Optional, Tuple
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from core.context import get_current_org_id
from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.api_key import ApiKey
from core.models.model import Model
from core.models.model_provider import ModelProvider
from core.models.model_voice import ModelVoice
from core.utils.encryption import decrypt



# Bump whenever the cached pipeline payload's shape changes (a key is added, renamed, or
# removed in `load_agent_service_config`'s `result` dict). It is folded into every cache
# version stamp, so a deploy that changes the shape invalidates all persisted entries
# instead of serving them with a stale shape — there is no TTL to clear them otherwise.
PAYLOAD_FORMAT_VERSION = "v4"  # v4: workflow mode uses the workflow prompt alone (no base persona)


def _resolve_org_id(org_id):
    return org_id or get_current_org_id()


def _to_uuid(v: Any) -> Optional[UUID]:
    if v is None:
        return None
    if isinstance(v, UUID):
        return v
    try:
        return UUID(str(v))
    except (ValueError, TypeError, AttributeError):
        return None


def _looks_like_uuid(value: Any) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_active_agent_config(db: Session, agent: Any) -> Optional[AgentConfig]:
    """Get the published config for the given agent (Agent model or agent_id).

    Resolves via `Agent.published_config_id`; falls back to the agent's default/latest
    config so edit-mode previews (which may not be published yet) still work.
    """
    agent_id = agent.id if hasattr(agent, "id") else agent
    cfg = (
        db.query(AgentConfig)
        .join(Agent, Agent.published_config_id == AgentConfig.id)
        .filter(Agent.id == agent_id)
        .first()
    )
    if cfg:
        return cfg
    return (
        db.query(AgentConfig)
        .filter(AgentConfig.agent_id == agent_id)
        .order_by(AgentConfig.is_default.desc(), AgentConfig.version.desc())
        .first()
    )


def _make_service_spec(provider, model_name, api_key, metadata) -> Optional[dict]:
    """Assemble the {provider_name, api_key, model_name, metadata, model_meta_data} spec."""
    if not provider or not api_key:
        return None
    return {
        "provider_name": (provider.slug or "").strip().lower(),
        "api_key": api_key,
        "model_name": model_name,
        "metadata": metadata,
        "model_meta_data": {},
    }


def _build_service_specs(
    db: Session, org_id, config: AgentConfig
) -> Tuple[Optional[dict], Optional[dict], Optional[dict], bool]:
    """Resolve the llm/stt/tts service specs (+ is_s2s) from an AgentConfig.

    Reads the JSONB `llm_settings`/`stt_settings`/`voice_settings`, resolves each
    provider slug, model name, voice id, and decrypted API key, and returns three
    spec dicts (any of which may be None if not configured).
    """
    llm_settings = config.llm_settings or {}
    stt_settings = config.stt_settings or {}
    voice_settings = config.voice_settings or {}

    ids = _config_service_ids(config)
    llm_pid, stt_pid, tts_pid = ids["llm_pid"], ids["stt_pid"], ids["tts_pid"]
    llm_mid, stt_mid, tts_mid = ids["llm_mid"], ids["stt_mid"], ids["tts_mid"]
    provider_ids, model_ids = ids["provider_ids"], ids["model_ids"]

    stt_model_literal = stt_settings.get("model")
    voice_id_raw = voice_settings.get("voice_id")
    voice_uuid = ids["voice_uuid"]

    providers = (
        db.query(ModelProvider).filter(ModelProvider.id.in_(provider_ids)).all() if provider_ids else []
    )
    provider_by_id = {p.id: p for p in providers}

    models = db.query(Model).filter(Model.id.in_(model_ids)).all() if model_ids else []
    model_by_id = {m.id: m for m in models}

    keys = (
        db.query(ApiKey)
        .filter(
            ApiKey.provider_id.in_(provider_ids),
            ApiKey.organization_id == org_id,
            ApiKey.is_active.is_(True),
        )
        .order_by(ApiKey.is_default.desc())
        .all()
        if (provider_ids and org_id)
        else []
    )
    key_by_provider_service: dict = {}
    for k in keys:
        key_by_provider_service.setdefault((k.provider_id, k.service_type), k)

    voice_row = (
        db.query(ModelVoice).filter(ModelVoice.id == voice_uuid).first() if voice_uuid else None
    )

    def _mname(mid):
        m = model_by_id.get(mid)
        return m.name if m else None

    def _key(pid, service_type):
        ak = key_by_provider_service.get((pid, service_type))
        if not ak:
            # Fallback: a key with NULL service_type covers all services for the provider.
            ak = key_by_provider_service.get((pid, None))
        if not ak:
            return None
        try:
            return decrypt(ak.encrypted_key)
        except Exception as e:
            logger.warning("[resolver] decrypt failed for api_key {}: {}", ak.id, e)
            return None

    # Filter settings to only the params the chosen model actually supports, so stale
    # params (e.g. a temperature saved for GPT-4o) aren't sent to a model that rejects
    # them (e.g. GPT-5). Structural keys are always kept; provider params survive only
    # when present in the model's meta_data_schema. Models without a schema are unfiltered.
    _structural = {
        "provider_id", "model_id", "model", "voice_id",
        "language", "language_code", "is_s2s",
        "system_prompt", "system_instruction", "base_url",
    }

    def _filter_by_model_schema(settings: dict, model_id) -> dict:
        m = model_by_id.get(model_id) if model_id else None
        if not m or not m.meta_data_schema:
            return dict(settings)
        allowed = {f["name"] for f in m.meta_data_schema if "name" in f} | _structural
        return {k: v for k, v in settings.items() if k in allowed}

    def _build_metadata(settings: dict, model_id) -> dict:
        """Filter agent settings to model-allowed keys, then inject `Model.base_url`
        from the DB row when present. Missing/NULL `base_url` falls through — the
        factory's per-provider default (or Pipecat's class default) applies, so
        behavior is byte-identical to pre-base_url for any model without a URL.
        """
        metadata = _filter_by_model_schema(settings, model_id)
        if model_id:
            m = model_by_id.get(model_id)
            if m and m.base_url:
                metadata["base_url"] = m.base_url
        return metadata

    # ── LLM ──
    is_s2s = bool(llm_settings.get("is_s2s"))
    llm_metadata = _build_metadata(llm_settings, llm_mid)
    if is_s2s and config.system_prompt_template:
        # OpenAI Realtime reads metadata["system_prompt"]; Gemini Live reads
        # metadata["system_instruction"]. Set both so either S2S provider picks it up.
        llm_metadata["system_prompt"] = config.system_prompt_template
        llm_metadata["system_instruction"] = config.system_prompt_template
    llm_spec = _make_service_spec(
        provider_by_id.get(llm_pid),
        _mname(llm_mid),
        _key(llm_pid, "llm") if llm_pid else None,
        llm_metadata,
    )

    # ── STT ──
    stt_spec = _make_service_spec(
        provider_by_id.get(stt_pid),
        stt_model_literal or _mname(stt_mid),
        _key(stt_pid, "stt") if stt_pid else None,
        _build_metadata(stt_settings, stt_mid),
    )

    # ── TTS ──
    resolved_voice = (voice_row.voice_id if voice_row else None) or (
        voice_id_raw if (voice_id_raw and not _looks_like_uuid(voice_id_raw)) else None
    )
    tts_metadata = _build_metadata(voice_settings, tts_mid)
    tts_metadata["voice_id"] = resolved_voice
    # The factory reads metadata["language"]; prefer the language *code* (e.g. "en")
    # over the display name (e.g. "English"), which Pipecat's Language enum rejects.
    tts_language = voice_settings.get("language_code") or voice_settings.get("language")
    if tts_language:
        tts_metadata["language"] = tts_language
    tts_spec = _make_service_spec(
        provider_by_id.get(tts_pid),
        _mname(tts_mid),
        _key(tts_pid, "tts") if tts_pid else None,
        tts_metadata,
    )

    return llm_spec, stt_spec, tts_spec, is_s2s


def _config_service_ids(config) -> dict:
    """Provider/model/voice ids referenced by a config's JSONB settings, extracted once.

    Returns the per-service ids (which `_build_service_specs` needs to resolve each service)
    alongside the merged `provider_ids`/`model_ids` sets and the voice id (which the
    cache-version stamp needs) — so the `_to_uuid(settings.get(...))` extraction lives in a
    single place and the spec builder and the stamp can't drift apart.
    """
    llm = config.llm_settings or {}
    stt = config.stt_settings or {}
    voice = config.voice_settings or {}
    llm_pid, stt_pid, tts_pid = (
        _to_uuid(llm.get("provider_id")),
        _to_uuid(stt.get("provider_id")),
        _to_uuid(voice.get("provider_id")),
    )
    llm_mid, stt_mid, tts_mid = (
        _to_uuid(llm.get("model_id")),
        _to_uuid(stt.get("model_id")),
        _to_uuid(voice.get("model_id")),
    )
    return {
        "llm_pid": llm_pid, "stt_pid": stt_pid, "tts_pid": tts_pid,
        "llm_mid": llm_mid, "stt_mid": stt_mid, "tts_mid": tts_mid,
        "voice_uuid": _to_uuid(voice.get("voice_id")),
        "provider_ids": {p for p in (llm_pid, stt_pid, tts_pid) if p},
        "model_ids": {m for m in (llm_mid, stt_mid, tts_mid) if m},
    }


def _load_workflow_prompt(db: Session, config, org_id=None) -> Tuple[Optional[str], Optional[str]]:
    """When the config runs in workflow mode, render the assigned workflow's published
    graph into an instruction block for the LLM.

    Returns ``(playbook_text, start_first_message)`` — the serialized pathway plus the
    start node's opening line (the greeting to speak on connect). Both are None outside
    workflow mode, when no workflow is assigned, or when there is no published version."""
    if getattr(config, "mode", "prompt") != "workflow":
        return None, None
    workflow_id = getattr(config, "workflow_id", None)
    if not workflow_id:
        return None, None

    from core.models.workflow import Workflow, WorkflowVersion
    from core.services.workflow.prompt_serializer import (
        serialize_graph_for_llm,
        workflow_first_message,
    )

    # Org-scope the lookup: a workflow may only be resolved for an agent in the SAME org,
    # so another org's workflow can never drive this call even if the id were referenced.
    wf_q = db.query(Workflow).filter(Workflow.id == workflow_id)
    if org_id:
        wf_q = wf_q.filter(Workflow.organization_id == org_id)
    wf = wf_q.first()
    if not wf or not wf.published_version_id:
        return None, None
    ver_q = db.query(WorkflowVersion).filter(WorkflowVersion.id == wf.published_version_id)
    if org_id:
        ver_q = ver_q.filter(WorkflowVersion.organization_id == org_id)
    ver = ver_q.first()
    if not ver or not ver.graph:
        return None, None
    text = serialize_graph_for_llm(ver.graph, _workflow_tool_names(db, ver.graph, org_id))
    greeting = workflow_first_message(ver.graph)
    return (text or None), (greeting or None)


def _workflow_tool_names(db: Session, graph: dict, org_id=None) -> dict:
    """Map each tool node's ``toolId`` / ``mcpServerId`` → display name so the serialized
    steps can name the exact (agent-attached) tool or MCP server to use. Org-scoped;
    returns {} when there are no tool/MCP ids."""
    nodes = graph.get("nodes") or []
    tool_ids, mcp_ids = [], []
    for n in nodes:
        data = (n or {}).get("data") or {}
        if data.get("toolId"):
            tool_ids.append(data["toolId"])
        if data.get("mcpServerId"):
            mcp_ids.append(data["mcpServerId"])
    names: dict = {}
    if tool_ids:
        from core.models.tool import Tool

        q = db.query(Tool).filter(Tool.id.in_(tool_ids))
        if org_id:
            q = q.filter(Tool.organization_id == org_id)
        names.update({str(t.id): t.name for t in q.all()})
    if mcp_ids:
        from core.models.mcp_server import McpServer

        q = db.query(McpServer).filter(McpServer.id.in_(mcp_ids))
        if org_id:
            q = q.filter(McpServer.organization_id == org_id)
        names.update({str(m.id): m.name for m in q.all()})
    return names


def _compose_system_prompt(base_prompt: Optional[str], workflow_prompt: Optional[str]) -> str:
    """Layer the agent persona prompt above the workflow playbook (either may be empty)."""
    parts = [p.strip() for p in (base_prompt, workflow_prompt) if p and p.strip()]
    return "\n\n".join(parts)


def compute_agent_cache_version(db: Session, agent: Any, org_id=None) -> Tuple[Optional[str], Optional[Any]]:
    """Return (version_stamp, active_config) for an agent.

    The stamp is a composite of updated_at timestamps AND row counts across EVERY input the
    cached pipeline payload depends on — the config, the referenced provider/model/voice/
    api-key rows, the linked tools, the KB uploads, and the linked MCP servers. Any change
    (incl. an in-place API-key rotation, a model/voice edit, or a tool/KB/MCP add/remove)
    changes the stamp and invalidates the cache; the counts catch removals that a bare
    max(updated_at) would miss. MCP runtime still resolves servers live in build(); the
    stamp covers MCP only because the cached payload now snapshots `{id, name}` refs for
    the call-log so filters on `pipeline_config.mcp_servers` stay accurate.

    Cost: one config lookup + ONE combined aggregate query (all the COUNT/MAX values are
    scalar subqueries in a single round-trip) — far cheaper than a full resolve, and keeps
    call-setup latency low even on a remote DB.
    """
    from sqlalchemy import func, select

    from core.models.agent_knowledge_base import AgentKnowledgeBase
    from core.models.agent_mcp_server import AgentMcpServer
    from core.models.knowledge_base import KnowledgeBase
    from core.models.mcp_server import McpServer
    from core.models.agent_tool import AgentTool
    from core.models.tool import Tool
    from core.models.upload import Upload

    config = get_active_agent_config(db, agent)
    if not config:
        return None, None

    agent_id = agent.id if hasattr(agent, "id") else agent
    # Attachments are per-version: the runtime always wants the published
    # config's set, never the union across versions (which was the implicit
    # behaviour when these rows were keyed by `agent_id` alone).
    config_id = config.id
    org = org_id or getattr(config, "organization_id", None) or getattr(agent, "organization_id", None)
    ids = _config_service_ids(config)
    provider_ids, model_ids, voice_uuid = ids["provider_ids"], ids["model_ids"], ids["voice_uuid"]

    # Each freshness value is a scalar subquery; selecting them together is ONE round-trip.
    # Empty id-sets / a missing voice render as `IN ()` / `= NULL` → no rows → MAX = NULL,
    # which is exactly the "nothing referenced" stamp we want.
    prov_sq = select(func.max(ModelProvider.updated_at)).where(ModelProvider.id.in_(provider_ids)).scalar_subquery()
    model_sq = select(func.max(Model.updated_at)).where(Model.id.in_(model_ids)).scalar_subquery()
    voice_sq = select(func.max(ModelVoice.updated_at)).where(ModelVoice.id == voice_uuid).scalar_subquery()

    _key_where = (
        ApiKey.provider_id.in_(provider_ids),
        ApiKey.organization_id == org,
        ApiKey.is_active.is_(True),
    )
    key_cnt_sq = select(func.count(ApiKey.id)).where(*_key_where).scalar_subquery()
    key_max_sq = select(func.max(ApiKey.updated_at)).where(*_key_where).scalar_subquery()

    _tool_where = (
        AgentTool.agent_id == agent_id,
        AgentTool.agent_config_id == config_id,
        Tool.is_active.is_(True),
    )
    tool_cnt_sq = (
        select(func.count(Tool.id)).select_from(Tool)
        .join(AgentTool, AgentTool.tool_id == Tool.id).where(*_tool_where).scalar_subquery()
    )
    tool_link_sq = (
        select(func.max(AgentTool.updated_at)).select_from(AgentTool)
        .join(Tool, Tool.id == AgentTool.tool_id).where(*_tool_where).scalar_subquery()
    )
    tool_max_sq = (
        select(func.max(Tool.updated_at)).select_from(Tool)
        .join(AgentTool, AgentTool.tool_id == Tool.id).where(*_tool_where).scalar_subquery()
    )

    _kb_where = (
        AgentKnowledgeBase.agent_id == agent_id,
        AgentKnowledgeBase.agent_config_id == config_id,
        Upload.status == "ready",
    )
    kb_cnt_sq = (
        select(func.count(Upload.id)).select_from(Upload)
        .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
        .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
        .where(*_kb_where).scalar_subquery()
    )
    kb_link_sq = (
        select(func.max(AgentKnowledgeBase.updated_at)).select_from(AgentKnowledgeBase)
        .join(KnowledgeBase, KnowledgeBase.id == AgentKnowledgeBase.knowledge_base_id)
        .join(Upload, Upload.id == KnowledgeBase.upload_id).where(*_kb_where).scalar_subquery()
    )
    kb_max_sq = (
        select(func.max(Upload.updated_at)).select_from(Upload)
        .join(KnowledgeBase, KnowledgeBase.upload_id == Upload.id)
        .join(AgentKnowledgeBase, AgentKnowledgeBase.knowledge_base_id == KnowledgeBase.id)
        .where(*_kb_where).scalar_subquery()
    )

    _mcp_where = (
        AgentMcpServer.agent_id == agent_id,
        AgentMcpServer.agent_config_id == config_id,
        McpServer.is_active.is_(True),
    )
    mcp_cnt_sq = (
        select(func.count(McpServer.id)).select_from(McpServer)
        .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
        .where(*_mcp_where).scalar_subquery()
    )
    mcp_link_sq = (
        select(func.max(AgentMcpServer.updated_at)).select_from(AgentMcpServer)
        .join(McpServer, McpServer.id == AgentMcpServer.mcp_server_id)
        .where(*_mcp_where).scalar_subquery()
    )
    mcp_max_sq = (
        select(func.max(McpServer.updated_at)).select_from(McpServer)
        .join(AgentMcpServer, AgentMcpServer.mcp_server_id == McpServer.id)
        .where(*_mcp_where).scalar_subquery()
    )

    # Workflow assignment: the assigned workflow's published-version id + updated_at are
    # folded into the SAME combined query (as scalar subqueries) so re-assigning or
    # re-publishing invalidates the cache without a second per-call round-trip. When the
    # config isn't in workflow mode the id is NULL → the joins yield NULL (no extra cost).
    from core.models.workflow import Workflow, WorkflowVersion

    mode = getattr(config, "mode", "prompt") or "prompt"
    workflow_id = getattr(config, "workflow_id", None) if mode == "workflow" else None
    wf_id_sq = (
        select(WorkflowVersion.id).select_from(Workflow)
        .join(WorkflowVersion, WorkflowVersion.id == Workflow.published_version_id)
        .where(Workflow.id == workflow_id).scalar_subquery()
    )
    wf_ts_sq = (
        select(WorkflowVersion.updated_at).select_from(Workflow)
        .join(WorkflowVersion, WorkflowVersion.id == Workflow.published_version_id)
        .where(Workflow.id == workflow_id).scalar_subquery()
    )

    (
        prov_max, model_max, voice_ts, key_count, key_max,
        tool_count, tool_link_max, tool_max, kb_count, kb_link_max, kb_max,
        mcp_count, mcp_link_max, mcp_max, wf_ver_id, wf_ver_ts,
    ) = db.execute(
        select(
            prov_sq, model_sq, voice_sq, key_cnt_sq, key_max_sq,
            tool_cnt_sq, tool_link_sq, tool_max_sq, kb_cnt_sq, kb_link_sq, kb_max_sq,
            mcp_cnt_sq, mcp_link_sq, mcp_max_sq, wf_id_sq, wf_ts_sq,
        )
    ).one()

    def _s(ts):
        return ts.isoformat() if ts is not None else "none"

    wf_stamp = f"{wf_ver_id}:{_s(wf_ver_ts)}" if wf_ver_id is not None else "none"

    version = "|".join([
        f"fmt:{PAYLOAD_FORMAT_VERSION}",
        f"cfg:{config.id}:{_s(config.updated_at)}",
        f"prov:{_s(prov_max)}",
        f"model:{_s(model_max)}",
        f"voice:{_s(voice_ts)}",
        f"key:{key_count}:{_s(key_max)}",
        f"tools:{tool_count}:{_s(tool_link_max)}:{_s(tool_max)}",
        f"kb:{kb_count}:{_s(kb_link_max)}:{_s(kb_max)}",
        f"mcp:{mcp_count}:{_s(mcp_link_max)}:{_s(mcp_max)}",
        f"wf:{mode}:{workflow_id}:{wf_stamp}",
    ])
    return version, config


def load_agent_service_config(
    db: Session, agent: Any, transport_type: str = None, org_id=None
) -> Optional[dict]:
    """Resolve the full pipeline payload (LLM/STT/TTS specs + prompt + tools + KB) for an
    agent, served from a version-stamped Redis cache under one transport-independent key.

    On every call the live version stamp is recomputed and compared to the cached stamp: a
    byte-identical match returns the cached payload with no further DB work; ANY change
    (config, provider/model/voice/key, tools, or KB) forces a fresh resolve + re-stamp, so a
    call never runs on stale data. `transport_type` is accepted for signature compatibility
    but no longer affects the cache — telephony credentials are resolved per-transport at the
    serializer, not cached here. Returns None if config/required services are missing.
    """
    from core.services.custom_tool_service import serialize_agent_tools
    from core.services.document_tool_service import get_kb_document_names, get_kb_refs
    from core.services.mcp_tool_service import get_mcp_server_refs
    from core.services.redis_service import cache_get, cache_set

    _t = _time.monotonic()
    agent_id = agent.id if hasattr(agent, "id") else agent
    org_id = _resolve_org_id(org_id)

    version, config = compute_agent_cache_version(db, agent, org_id=org_id)
    if config is None:
        return None
    # A runnable agent needs either a system prompt or an assigned workflow (workflow mode
    # can drive the call with no standalone prompt). Cheap signal check — the workflow graph
    # itself is only serialized below on a cache miss.
    _in_workflow_mode = (
        getattr(config, "mode", "prompt") == "workflow" and getattr(config, "workflow_id", None)
    )
    if not config.system_prompt_template and not _in_workflow_mode:
        return None

    cache_key = f"agent_pipeline_config:{agent_id}"
    cached = cache_get(cache_key)
    if cached is not None and cached.get("_cache_version") == version:
        logger.info("[TIMING] pipeline config: CACHE HIT (fresh) agent_id={} (+{:.3f}s)", agent_id, _time.monotonic() - _t)
        return cached

    org_id = org_id or getattr(config, "organization_id", None) or getattr(agent, "organization_id", None)
    llm_spec, stt_spec, tts_spec, is_s2s = _build_service_specs(db, org_id, config)
    if not llm_spec:
        return None
    if not is_s2s and (not stt_spec or not tts_spec):
        return None

    # Workflow mode: flatten the assigned workflow's published graph into the system prompt
    # so the LLM follows the pathway. Guarded so a bad/missing workflow degrades to prompt
    # mode instead of aborting a live-call resolve.
    try:
        workflow_prompt, workflow_greeting = _load_workflow_prompt(db, config, org_id)
    except Exception as exc:  # noqa: BLE001 — never let workflow load kill the resolve
        logger.warning("[workflow] failed to load workflow prompt for agent={}: {}", agent_id, exc)
        workflow_prompt, workflow_greeting = None, None
    if _in_workflow_mode and workflow_prompt:
        # Workflow selected and loaded: drive the call ENTIRELY from the workflow playbook.
        # The agent's base persona prompt is intentionally dropped — keeping it would let its
        # own greeting/flow/instructions conflict with and override the workflow's steps.
        system_content = workflow_prompt.strip()
    else:
        # Prompt mode, or workflow mode but the workflow failed/empty → fall back to the
        # base persona prompt (compose handles either part being empty).
        system_content = _compose_system_prompt(
            getattr(config, "system_prompt_template", None), workflow_prompt
        )
    if not system_content:
        return None

    # S2S models read the system prompt from the LLM metadata (set in _build_service_specs
    # from system_prompt_template); override it with the composed content so workflow mode
    # reaches realtime models too.
    if is_s2s and isinstance(llm_spec.get("metadata"), dict):
        llm_spec["metadata"]["system_prompt"] = system_content
        llm_spec["metadata"]["system_instruction"] = system_content

    messages = [{"role": "system", "content": system_content}]
    # Greeting spoken on connect. In workflow mode the workflow's start step owns the
    # opening line — use it and ignore config.first_message, falling back to
    # config.first_message only when the workflow defines no start message.
    cfg_first = (getattr(config, "first_message", None) or "").strip()
    if _in_workflow_mode and workflow_prompt:
        greeting = (workflow_greeting or "").strip() or cfg_first
    else:
        greeting = cfg_first
    if greeting:
        messages.append({"role": "assistant", "content": greeting})

    result = {
        "_cache_version": version,
        "llm": llm_spec,
        "stt": stt_spec,
        "tts": tts_spec,
        "is_s2s": is_s2s,
        "messages": messages,
        "end_call_message": getattr(config, "end_call_message", None),
        "tools": serialize_agent_tools(agent_id),
        "kb": get_kb_document_names(agent_id),
        # `{id, name}` refs for the call-log snapshot. Cached here so the runner can
        # write them in the same INSERT that creates the call row — no per-call queries.
        "kb_refs": get_kb_refs(agent_id),
        "mcp_servers": get_mcp_server_refs(agent_id),
    }
    # Persistent (no TTL): the version stamp guarantees freshness on every read, and edits
    # overwrite/invalidate the entry — so there is no need to expire it on a timer.
    cache_set(cache_key, result, ttl_seconds=None)
    logger.info("[TIMING] pipeline config: CACHE MISS — resolved + stored agent_id={} (+{:.3f}s)", agent_id, _time.monotonic() - _t)
    return result


def load_agent_service_config_cached(db: Session, agent: Any, org_id=None) -> Optional[dict]:
    """The cache is now one transport-independent key with a freshness stamp, so this just
    delegates to load_agent_service_config (kept for the no-transport call sites)."""
    return load_agent_service_config(db, agent, transport_type=None, org_id=org_id)
