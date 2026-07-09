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
PAYLOAD_FORMAT_VERSION = "v7"  # v7: add voice-response rules (brevity + no Markdown) alongside tool-usage rules


# Appended to every agent's system prompt so responses stay TTS-friendly. Two rule sets:
# (1) Voice Response Rules — keep replies short and free of Markdown/formatting symbols
#     that TTS would otherwise read literally ("asterisk asterisk Thursday").
# (2) Tool Usage Rules — prevent tool invocations from leaking into speech (narration,
#     tool names, raw JSON, IDs, URLs). Kept short and generic so it composes with any
#     persona/workflow.
_VOICE_AGENT_RULES = """# Voice Response Rules

- Keep replies short — one or two sentences. Only give more detail if the user explicitly asks for it.
- Never use Markdown formatting. No asterisks, hyphens, headings, bullet points, backticks, code blocks, or links. Write plain sentences that sound natural when read aloud.
- Do not read symbols, punctuation, or formatting characters. Speak numbers and units naturally (e.g., "twenty-eight degrees" not "28°C").

# Tool Usage Rules

You may use tools to fulfill the user's request. When you do:

- Never mention that you are using a tool or describe how you are using it.
- Never mention tool names, parameters, IDs, raw outputs, JSON, URLs, or internal implementation details.
- Do not narrate your actions (e.g., "Let me check", "I'll look that up", "One moment while I fetch that").
- Respond only with the final answer in a natural, conversational way.
- If information comes from a tool, summarize it in one or two concise sentences. Do not read raw data aloud.
- If a tool fails or the requested information cannot be retrieved, briefly explain the issue in plain language and, when possible, suggest the next best step. Do not mention internal errors or implementation details.
- If the user explicitly asks how you obtained the information, simply say that you checked the available information and avoid referring to tools or internal systems."""


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
        # Human-readable provider name for the call-history snapshot. `provider_name`
        # stays the slug (the factory keys off it); this is display-only.
        "provider_display_name": provider.display_name or provider.slug,
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

        Defense (staging incident 2026-07-03): a stale `model_id` left behind by a
        provider switch can point at another provider's model row — injecting that
        row's base_url silently redirects the service (Deepgram STT ended up on the
        parakeet k8s URL). Only inject when the model row belongs to the settings'
        provider; on mismatch, warn and skip.
        """
        metadata = _filter_by_model_schema(settings, model_id)
        if model_id:
            m = model_by_id.get(model_id)
            if m and m.base_url:
                spec_pid = _to_uuid(settings.get("provider_id"))
                if spec_pid and m.provider_id != spec_pid:
                    logger.warning(
                        "[resolver] provider/model_id mismatch for agent_id={}: "
                        "model {} ({!r}) belongs to provider {} but settings.provider_id={} "
                        "— skipping base_url injection",
                        config.agent_id, m.id, m.name, m.provider_id, spec_pid,
                    )
                else:
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
    # Human-readable voice name for the call-history snapshot (falls back to the
    # resolved id). Filtered out of the factory's InputParams by build_input_params.
    tts_metadata["voice_name"] = (voice_row.name if voice_row else None) or resolved_voice
    # The factory reads metadata["language"]; prefer the language *code* (e.g. "en")
    # over the display name (e.g. "English"), which Pipecat's Language enum rejects.
    tts_language = voice_settings.get("language_code") or voice_settings.get("language")
    if tts_language:
        tts_metadata["language"] = tts_language
    # Display name (e.g. "English") for the snapshot — the factory never reads this.
    tts_language_display = voice_settings.get("language") or tts_language
    if tts_language_display:
        tts_metadata["language_display"] = tts_language_display
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


def _published_workflow_graph(db: Session, config, org_id=None) -> Optional[dict]:
    """Return the assigned workflow's working graph (org-scoped), or None outside
    workflow mode / when no workflow is assigned / there is no graph.

    Workflows have no separate publish step — ``draft_version_id`` points at the
    single working graph, which is what the call uses. Loaded once per resolve so
    the playbook text and the synthesized apiRequest tools derive from the same
    graph and share one node_id -> fn-name map (names never drift)."""
    if getattr(config, "mode", "prompt") != "workflow":
        return None
    workflow_id = getattr(config, "workflow_id", None)
    if not workflow_id:
        return None

    from core.models.workflow import Workflow, WorkflowVersion

    wf_q = db.query(Workflow).filter(Workflow.id == workflow_id)
    if org_id:
        wf_q = wf_q.filter(Workflow.organization_id == org_id)
    wf = wf_q.first()
    if not wf or not wf.draft_version_id:
        return None
    ver_q = db.query(WorkflowVersion).filter(WorkflowVersion.id == wf.draft_version_id)
    if org_id:
        ver_q = ver_q.filter(WorkflowVersion.organization_id == org_id)
    ver = ver_q.first()
    if not ver or not ver.graph:
        return None
    return ver.graph


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


def _kv_to_dict(rows, decrypt: bool) -> dict:
    """Turn a [{key, value, encrypt?}] list into a {key: value} dict, decrypting
    encrypt-flagged values (stored AES-encrypted in the graph). Bad/blank rows dropped."""
    out: dict = {}
    if not isinstance(rows, list):
        return out
    for r in rows:
        if not isinstance(r, dict):
            continue
        k = (r.get("key") or "").strip()
        if not k:
            continue
        v = r.get("value") or ""
        if decrypt and r.get("encrypt") and v:
            try:
                from core.utils.encryption import decrypt as _dec
                v = _dec(v)
            except Exception:
                continue
        out[k] = v
    return out


def _merge_tools(real_tools: list, api_tools: list) -> list:
    """Append synthesized apiRequest tools to the agent's real tools, renaming any
    apiRequest tool whose (sanitized) name collides with a real tool so both stay callable."""
    if not api_tools:
        return real_tools
    from core.services.custom_tool_service import sanitize_tool_name

    taken = {sanitize_tool_name(t.get("name") or "") for t in (real_tools or [])}
    merged = list(real_tools or [])
    for t in api_tools:
        name = t.get("name") or "api_request"
        if name in taken:
            i = 2
            while f"{name}_{i}" in taken:
                i += 1
            name = f"{name}_{i}"
            t = {**t, "name": name}
        taken.add(name)
        merged.append(t)
    return merged


def _workflow_api_fn_names(graph: dict, taken: Optional[set] = None) -> dict:
    """Map each apiRequest node id → the unique sanitized function name it is registered
    under, deduped among themselves AND against ``taken`` (the agent's real tool names). The
    playbook serializer and the synthesized tools share this map so the function names the
    model is told to call match the names actually registered."""
    from core.services.custom_tool_service import sanitize_tool_name

    claimed = set(taken or ())
    names: dict = {}
    for n in (graph.get("nodes") or []):
        if not isinstance(n, dict) or n.get("type") != "apiRequest":
            continue
        nid = n.get("id")
        d = n.get("data") or {}
        raw = (d.get("name") or nid or "api_request").strip()
        fn = sanitize_tool_name(raw)
        if fn in claimed:
            i = 2
            while f"{fn}_{i}" in claimed:
                i += 1
            fn = f"{fn}_{i}"
        claimed.add(fn)
        names[str(nid)] = fn
    return names


def _build_api_request_tools(graph: dict, fn_names: dict) -> list:
    """Synthesize the graph's apiRequest nodes into webhook-tool dicts (same shape as
    serialize_agent_tools) so the existing builder loop registers them as callable HTTP
    functions. ``fn_names`` (from _workflow_api_fn_names) supplies each node's already-deduped
    function name. Secrets in headers/static body are decrypted here for runtime use."""
    from core.services.custom_tool_service import sanitize_tool_name

    tools: list = []
    for n in (graph.get("nodes") or []):
        if not isinstance(n, dict) or n.get("type") != "apiRequest":
            continue
        nid = n.get("id")
        d = n.get("data") or {}
        raw_name = (d.get("name") or nid or "api_request").strip()
        fn_name = fn_names.get(str(nid)) or sanitize_tool_name(raw_name)

        props, required = {}, []
        for p in (d.get("requestBody") or []):
            if not isinstance(p, dict) or not (p.get("name") or "").strip():
                continue
            pname = p["name"].strip()
            props[pname] = {"type": p.get("type") or "string", "description": p.get("description") or ""}
            if p.get("required"):
                required.append(pname)

        tools.append({
            "id": None,
            "name": fn_name,
            "description": (d.get("description") or f"API request: {raw_name}"),
            "tool_type": "custom",
            "parameters": {"type": "object", "properties": props, "required": required},
            "url": d.get("url") or "",
            "method": (d.get("method") or "GET").upper(),
            "auth_type": "none",
            "auth_config": None,
            "meta_data": None,
            "oauth_connection_id": None,
            "mcp_server_id": None,
            "is_workflow_api_request": True,
            "headers": _kv_to_dict(d.get("headers"), decrypt=True),
            "static_body": _kv_to_dict(d.get("staticBody"), decrypt=True),
        })
    return tools


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

    # Workflow assignment: the assigned workflow's working-version id + updated_at are
    # folded into the SAME combined query (as scalar subqueries) so re-assigning or
    # editing the workflow invalidates the cache without a second per-call round-trip.
    # When the config isn't in workflow mode the id is NULL → the joins yield NULL.
    from core.models.workflow import Workflow, WorkflowVersion

    mode = getattr(config, "mode", "prompt") or "prompt"
    workflow_id = getattr(config, "workflow_id", None) if mode == "workflow" else None
    wf_id_sq = (
        select(WorkflowVersion.id).select_from(Workflow)
        .join(WorkflowVersion, WorkflowVersion.id == Workflow.draft_version_id)
        .where(Workflow.id == workflow_id).scalar_subquery()
    )
    wf_ts_sq = (
        select(WorkflowVersion.updated_at).select_from(Workflow)
        .join(WorkflowVersion, WorkflowVersion.id == Workflow.draft_version_id)
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

    # The referenced ids themselves are part of the stamp, not just row
    # timestamps/counts. A manual DB edit that swaps e.g. stt_settings.model_id
    # bumps no updated_at anywhere (onupdate is client-side) and doesn't
    # necessarily change MAX(updated_at) over the new id set — without the ids
    # the stamp would match and the cache would keep serving the old payload
    # until a worker restart (as happened on staging, 2026-07-03).
    ref_ids = ":".join(
        str(ids[k]) for k in ("llm_pid", "llm_mid", "stt_pid", "stt_mid", "tts_pid", "tts_mid")
    )
    version = "|".join([
        f"fmt:{PAYLOAD_FORMAT_VERSION}",
        f"cfg:{config.id}:{_s(config.updated_at)}",
        f"ids:{ref_ids}:{voice_uuid}",
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

    real_tools = serialize_agent_tools(agent_id)

    workflow_prompt = None
    workflow_greeting = None
    api_request_tools: list = []
    # Raw graph + its api-fn-name map, embedded in the payload so the runtime workflow
    # engine can drive the call deterministically. Kept alongside (not instead of) the
    # serialized playbook, which stays the fallback for prompt mode / S2S / load failures.
    workflow_graph = None
    workflow_fn_names: dict = {}
    try:
        graph = _published_workflow_graph(db, config, org_id)
        if graph:
            from core.services.custom_tool_service import sanitize_tool_name
            from core.services.workflow.prompt_serializer import (
                serialize_graph_for_llm,
                workflow_first_message,
            )

            taken = {sanitize_tool_name(t.get("name") or "") for t in real_tools}
            api_fn_names = _workflow_api_fn_names(graph, taken)
            workflow_prompt = (
                serialize_graph_for_llm(
                    graph, _workflow_tool_names(db, graph, org_id), api_fn_names
                )
                or None
            )
            workflow_greeting = workflow_first_message(graph) or None
            api_request_tools = _build_api_request_tools(graph, api_fn_names)
            workflow_graph = graph
            workflow_fn_names = api_fn_names
    except Exception as exc:  # noqa: BLE001
        logger.warning("[workflow] failed to load workflow for agent={}: {}", agent_id, exc)
        workflow_prompt = None
        workflow_greeting = None
        api_request_tools = []
        workflow_graph = None
        workflow_fn_names = {}

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

    # Append the shared voice-agent rules (brevity + no Markdown + tool-usage guardrails)
    # so every agent — prompt mode or workflow mode, S2S or classic LLM — inherits the
    # same protections against TTS leaks and long/formatted replies.
    system_content = f"{system_content}\n\n{_VOICE_AGENT_RULES}"

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
        "tools": _merge_tools(real_tools, api_request_tools),
        "kb": get_kb_document_names(agent_id),
        # `{id, name}` refs for the call-log snapshot. Cached here so the runner can
        # write them in the same INSERT that creates the call row — no per-call queries.
        "kb_refs": get_kb_refs(agent_id),
        "mcp_servers": get_mcp_server_refs(agent_id),
    }
    # Workflow-runtime payload: the raw graph + api-fn-name map, consumed by the runtime
    # engine when enabled. Only present in workflow mode with a loaded graph; its absence
    # (prompt mode, old cache entries, load failure) transparently falls back to the
    # playbook already baked into `messages`. Secrets in the graph stay encrypted.
    if _in_workflow_mode and workflow_graph:
        result["workflow"] = workflow_graph
        result["workflow_fn_names"] = workflow_fn_names
    # Persistent (no TTL): the version stamp guarantees freshness on every read, and edits
    # overwrite/invalidate the entry — so there is no need to expire it on a timer.
    cache_set(cache_key, result, ttl_seconds=None)
    logger.info("[TIMING] pipeline config: CACHE MISS — resolved + stored agent_id={} (+{:.3f}s)", agent_id, _time.monotonic() - _t)
    return result


def load_agent_service_config_cached(db: Session, agent: Any, org_id=None) -> Optional[dict]:
    """The cache is now one transport-independent key with a freshness stamp, so this just
    delegates to load_agent_service_config (kept for the no-transport call sites)."""
    return load_agent_service_config(db, agent, transport_type=None, org_id=org_id)
