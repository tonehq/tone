"""Unit tests for ``AgentConfigLoader`` — DB path is stubbed via
``MagicMock`` sessions so the tests never require a real Postgres.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from core.services.evals.agent_llm.agent_config_loader import AgentConfigLoader
from core.services.evals.errors import AgentLlmEvalConfigError


def _agent(**overrides):
    """Build an ``Agent``-shaped MagicMock so ``getattr`` returns real values
    (a bare MagicMock returns MagicMock for every attribute)."""
    m = MagicMock()
    m.id = overrides.get("id", uuid4())
    m.name = overrides.get("name", "sales-bot")
    m.organization_id = overrides.get("organization_id", uuid4())
    m.published_config_id = overrides.get("published_config_id", uuid4())
    return m


def _config(**overrides):
    m = MagicMock()
    m.id = overrides.get("id", uuid4())
    m.system_prompt_template = overrides.get(
        "system_prompt_template", "You are a helpful assistant."
    )
    m.llm_settings = overrides.get(
        "llm_settings",
        {
            "provider_id": str(uuid4()),
            "model_id": str(uuid4()),
            "model": "gpt-4o",
            "temperature": 0.4,
            "max_tokens": 512,
        },
    )
    m.mode = overrides.get("mode", "prompt")
    m.workflow_id = overrides.get("workflow_id", None)
    return m


def _provider(slug: str = "openai"):
    m = MagicMock()
    m.id = uuid4()
    m.provider_id = slug
    return m


def _model(name: str = "gpt-4o"):
    m = MagicMock()
    m.id = uuid4()
    m.name = name
    m.provider_id = uuid4()
    return m


def _make_db(*, agent=None, config=None, provider=None, model=None,
             workflow=None, workflow_version=None):
    """Return a MagicMock db whose ``.query(X).filter(...).first()`` returns
    the row registered for that model type. Workflow/WorkflowVersion default
    to ``None`` so prompt-mode tests keep working unchanged."""
    from core.models.agent import Agent
    from core.models.agent_config import AgentConfig
    from core.models.model import Model
    from core.models.model_provider import ModelProvider
    from core.models.workflow import Workflow, WorkflowVersion

    db = MagicMock()

    def _query(cls):
        q = MagicMock()
        if cls is Agent:
            q.filter.return_value.first.return_value = agent
        elif cls is AgentConfig:
            q.filter.return_value.first.return_value = config
        elif cls is ModelProvider:
            q.filter.return_value.first.return_value = provider
        elif cls is Model:
            q.filter.return_value.first.return_value = model
        elif cls is Workflow:
            q.filter.return_value.first.return_value = workflow
        elif cls is WorkflowVersion:
            q.filter.return_value.first.return_value = workflow_version
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = _query
    return db


def _workflow_row(**overrides):
    m = MagicMock()
    m.id = overrides.get("id", uuid4())
    m.draft_version_id = overrides.get("draft_version_id", uuid4())
    return m


def _workflow_version_row(**overrides):
    m = MagicMock()
    m.id = overrides.get("id", uuid4())
    m.graph = overrides.get(
        "graph",
        {
            "schemaVersion": 1,
            "nodes": [
                {
                    "id": "n1",
                    "type": "conversation",
                    "data": {
                        "name": "Greet",
                        "isStart": True,
                        "prompt": "Greet the caller warmly.",
                        "messagePlan": {"firstMessage": "Hello!"},
                    },
                },
            ],
            "edges": [],
            "globalPrompt": "Speak clearly.",
        },
    )
    return m


# ── load_for_eval ────────────────────────────────────────────────────────


def test_load_for_eval_returns_snapshot():
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)
    assert result.agent_id == agent.id
    assert result.agent_name == "sales-bot"
    assert result.llm_model == "gpt-4o"
    assert result.llm_provider == "openai"
    assert result.llm_api_key == "sk-live"
    assert result.system_prompt == "You are a helpful assistant."
    assert result.temperature == 0.4
    assert result.max_tokens == 512
    assert result.llm_settings_snapshot == {"temperature": 0.4, "max_tokens": 512}
    assert result.agent_config_id == cfg.id


def test_load_for_eval_missing_agent_raises():
    db = _make_db(agent=None)
    with pytest.raises(AgentLlmEvalConfigError, match="not found"):
        AgentConfigLoader().load_for_eval(db, uuid4())


def test_load_for_eval_no_published_config_raises():
    agent = _agent(published_config_id=None)
    db = _make_db(agent=agent)
    with pytest.raises(AgentLlmEvalConfigError, match="no published config"):
        AgentConfigLoader().load_for_eval(db, agent.id)


def test_load_for_eval_missing_model_raises():
    agent = _agent()
    cfg = _config(llm_settings={"provider_id": str(uuid4())})  # no model
    prov = _provider("openai")
    db = _make_db(agent=agent, config=cfg, provider=prov)
    with pytest.raises(AgentLlmEvalConfigError, match="no LLM model"):
        AgentConfigLoader().load_for_eval(db, agent.id)


def test_load_for_eval_missing_provider_raises():
    agent = _agent()
    # No provider_id and no model_id → provider can't be inferred.
    cfg = _config(llm_settings={"model": "gpt-4o"})
    db = _make_db(agent=agent, config=cfg)
    with pytest.raises(AgentLlmEvalConfigError, match="no LLM provider"):
        AgentConfigLoader().load_for_eval(db, agent.id)


def test_load_for_eval_missing_api_key_raises():
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value=None,
    ):
        with pytest.raises(AgentLlmEvalConfigError, match="No 'openai' API key"):
            AgentConfigLoader().load_for_eval(db, agent.id)


# ── load_for_eval: workflow mode ─────────────────────────────────────────


def test_load_for_eval_workflow_mode_serializes_graph():
    """Workflow-mode agent renders its assigned graph through
    ``serialize_graph_for_llm`` and hands the text back on
    ``workflow_serialized`` — the SAME text the runtime injects.
    Prompt-mode fields remain populated (mode/workflow_id set correctly)."""
    workflow_id = uuid4()
    agent = _agent()
    cfg = _config(mode="workflow", workflow_id=workflow_id)
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    wf = _workflow_row(id=workflow_id)
    ver = _workflow_version_row(id=wf.draft_version_id)
    db = _make_db(
        agent=agent, config=cfg, provider=prov, model=mdl,
        workflow=wf, workflow_version=ver,
    )
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)

    assert result.mode == "workflow"
    assert result.workflow_id == workflow_id
    assert result.workflow_serialized is not None
    assert result.workflow_serialized.strip()
    # The playbook mentions the sole step's name so we know the serializer
    # actually ran on the graph fixture (not just returned an empty header).
    assert "Greet" in result.workflow_serialized
    # ``effective_system_prompt`` returns the playbook for workflow agents.
    assert result.effective_system_prompt == result.workflow_serialized


def test_load_for_eval_workflow_mode_missing_workflow_raises():
    """Agent marked workflow-mode but ``workflow_id`` is NULL → actionable
    error (not a 500)."""
    agent = _agent()
    cfg = _config(mode="workflow", workflow_id=None)
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ):
        with pytest.raises(AgentLlmEvalConfigError, match="no workflow assigned"):
            AgentConfigLoader().load_for_eval(db, agent.id)


def test_load_for_eval_workflow_mode_empty_graph_raises():
    """Workflow row exists but its working version has an empty ``graph`` —
    the eval has nothing to score against, fail loud."""
    workflow_id = uuid4()
    agent = _agent()
    cfg = _config(mode="workflow", workflow_id=workflow_id)
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    wf = _workflow_row(id=workflow_id)
    ver = _workflow_version_row(id=wf.draft_version_id, graph={"nodes": [], "edges": []})
    db = _make_db(
        agent=agent, config=cfg, provider=prov, model=mdl,
        workflow=wf, workflow_version=ver,
    )
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ):
        with pytest.raises(AgentLlmEvalConfigError, match="empty graph"):
            AgentConfigLoader().load_for_eval(db, agent.id)


def test_load_for_eval_prompt_mode_leaves_workflow_fields_none():
    """Regression guard: prompt-mode agents get ``mode='prompt'`` and every
    workflow-related field defaults to ``None`` — the workflow branch never
    ran, so no workflow tables were queried."""
    agent = _agent()
    cfg = _config()  # default mode='prompt'
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)
    assert result.mode == "prompt"
    assert result.workflow_id is None
    assert result.workflow_serialized is None
    assert result.effective_system_prompt == "You are a helpful assistant."


# ── load_for_eval: tools + MCP snapshot (Phase 2) ────────────────────────


class _StubTool:
    """MagicMock-friendly stand-in for a Tool ORM row. Only the fields
    ``serialize_agent_tools`` reads are needed."""

    def __init__(self, *, tool_id, name, description, parameters, mcp_server_id=None):
        self.id = tool_id
        self.name = name
        self.description = description
        self.parameters = parameters
        self.tool_type = "custom"
        self.url = None
        self.method = "POST"
        self.auth_type = "none"
        self.auth_config = None
        self.meta_data = None
        self.oauth_connection_id = None
        self.effective_oauth_connection_id = None
        self.mcp_server_id = mcp_server_id


def _stub_mcp_server(name: str, description: str = ""):
    m = MagicMock()
    m.name = name
    m.description = description
    return m


def test_load_snapshots_tools_when_attached():
    """Agent with active custom tools → ``AgentEvalConfig.tools`` populated
    in OpenAI tool-call shape, ready to hand to ``chat_complete_with_tools``.
    MCP-backed tools are excluded here (they surface via
    ``mcp_server_summaries``) to avoid double-counting in the generator prompt."""
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)

    fake_tools = [
        _StubTool(
            tool_id=uuid4(),
            name="book appointment",  # deliberately unsanitized
            description="Books a slot",
            parameters={
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
            },
        ),
        _StubTool(
            tool_id=uuid4(),
            name="mcp_backed",
            description="lives on an MCP server",
            parameters={},
            mcp_server_id=str(uuid4()),  # ← should be filtered out
        ),
    ]
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ), patch(
        "core.services.custom_tool_service.get_custom_tools_for_agent",
        return_value=fake_tools,
    ), patch(
        "core.services.mcp_tool_service.get_mcp_servers_for_agent",
        return_value=[],
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)

    assert len(result.tools) == 1  # MCP-backed tool filtered out
    entry = result.tools[0]
    assert entry["type"] == "function"
    # Name is sanitized to satisfy OpenAI's ^[a-zA-Z0-9_-]+$
    assert entry["function"]["name"] == "book_appointment"
    assert entry["function"]["description"] == "Books a slot"
    assert entry["function"]["parameters"]["required"] == ["date"]
    assert result.mcp_server_summaries == []


def test_load_snapshots_mcp_summaries_when_attached():
    """Agent with active MCP servers → ``mcp_server_summaries`` populated
    with name + description only (NO per-server live tool enumeration).
    """
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)

    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ), patch(
        "core.services.custom_tool_service.get_custom_tools_for_agent",
        return_value=[],
    ), patch(
        "core.services.mcp_tool_service.get_mcp_servers_for_agent",
        return_value=[
            _stub_mcp_server("calendar_mcp", "Manages calendar events"),
            _stub_mcp_server("crm_mcp"),  # no description
        ],
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)

    assert result.mcp_server_summaries == [
        {"name": "calendar_mcp", "description": "Manages calendar events"},
        {"name": "crm_mcp", "description": ""},
    ]
    # Only name + description keys — never leak the full ORM row.
    assert all(set(s.keys()) == {"name", "description"} for s in result.mcp_server_summaries)


def test_load_empty_tools_when_no_attachments():
    """Regression guard (Phase 2 no-tool agent stays byte-identical to v1).
    A prompt-mode agent with no tools + no MCP attached → empty lists on
    both new fields; downstream ``bool(agent_config.tools)`` guards keep the
    executor + generator on the pre-Phase-2 code path."""
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ), patch(
        "core.services.custom_tool_service.get_custom_tools_for_agent",
        return_value=[],
    ), patch(
        "core.services.mcp_tool_service.get_mcp_servers_for_agent",
        return_value=[],
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)
    assert result.tools == []
    assert result.mcp_server_summaries == []


def test_load_tool_snapshot_failure_degrades_gracefully():
    """When ``serialize_agent_tools`` raises (transient DB blip, etc.), the
    eval must still load with an empty tool list — a broken tool snapshot
    is NOT a reason to fail an entire eval run."""
    agent = _agent()
    cfg = _config()
    prov = _provider("openai")
    mdl = _model("gpt-4o")
    db = _make_db(agent=agent, config=cfg, provider=prov, model=mdl)
    with patch(
        "core.services.evals.agent_llm.agent_config_loader.ProviderKeyService.get_key",
        return_value="sk-live",
    ), patch(
        "core.services.custom_tool_service.get_custom_tools_for_agent",
        side_effect=RuntimeError("db went away"),
    ), patch(
        "core.services.mcp_tool_service.get_mcp_servers_for_agent",
        return_value=[],
    ):
        result = AgentConfigLoader().load_for_eval(db, agent.id)
    assert result.tools == []
    assert result.mcp_server_summaries == []


# ── resolve_agent_id ─────────────────────────────────────────────────────


def test_resolve_agent_id_by_uuid_returns_id():
    agent = _agent()
    db = _make_db(agent=agent)
    got = AgentConfigLoader().resolve_agent_id(db, str(agent.id))
    assert got == agent.id


def test_resolve_agent_id_by_name_case_insensitive():
    agent = _agent(name="Sales-Bot")
    from core.models.agent import Agent

    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.all.return_value = [agent]

    def _query(cls):
        if cls is Agent:
            return q
        raise AssertionError(f"unexpected query({cls})")

    db.query.side_effect = _query
    got = AgentConfigLoader().resolve_agent_id(db, "SALES-BOT")
    assert got == agent.id


def test_resolve_agent_id_no_match_raises():
    from core.models.agent import Agent

    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.all.return_value = []

    def _query(cls):
        if cls is Agent:
            return q
        return MagicMock()

    db.query.side_effect = _query
    with pytest.raises(AgentLlmEvalConfigError, match="No agent named"):
        AgentConfigLoader().resolve_agent_id(db, "ghost")


def test_resolve_agent_id_multiple_matches_raises():
    from core.models.agent import Agent

    a, b = _agent(name="ambig"), _agent(name="ambig")
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.all.return_value = [a, b]

    def _query(cls):
        if cls is Agent:
            return q
        return MagicMock()

    db.query.side_effect = _query
    with pytest.raises(AgentLlmEvalConfigError, match="Multiple agents named"):
        AgentConfigLoader().resolve_agent_id(db, "ambig")


def test_resolve_agent_id_uuid_missing_raises():
    from core.models.agent import Agent

    missing_id = uuid4()
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = None

    def _query(cls):
        if cls is Agent:
            return q
        return MagicMock()

    db.query.side_effect = _query
    with pytest.raises(AgentLlmEvalConfigError, match=str(missing_id)):
        AgentConfigLoader().resolve_agent_id(db, str(missing_id))


def test_resolve_agent_id_empty_raises():
    with pytest.raises(AgentLlmEvalConfigError, match="empty string"):
        AgentConfigLoader().resolve_agent_id(MagicMock(), "")
