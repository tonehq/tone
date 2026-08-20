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


def _make_db(*, agent=None, config=None, provider=None, model=None):
    """Return a MagicMock db whose ``.query(X).filter(...).first()`` returns
    the row registered for that model type."""
    from core.models.agent import Agent
    from core.models.agent_config import AgentConfig
    from core.models.model import Model
    from core.models.model_provider import ModelProvider

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
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = _query
    return db


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
