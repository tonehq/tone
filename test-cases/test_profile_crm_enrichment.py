"""Unit tests for CRM enrichment of empty profile variables.

Pure logic + monkeypatched CRM call — no DB or network. Run:
    pytest test-cases/test_profile_crm_enrichment.py -v -o "addopts="
"""

import asyncio
from contextlib import contextmanager

from core.services.agents.agent_profile_crm_config_service import (
    AgentProfileCrmConfigService,
)
from core.services.agents.agent_profile_variable_service import (
    AgentProfileVariableService,
)
from core.services.agents.profile_context import load_profile_crm_plan
from core.services.agents.profile_crm_enrichment_service import (
    ProfileCrmEnrichmentService,
    ProfileCrmPlan,
    _first_record,
    _resolve_path,
)
from core.services.mcp_server_service import parse_tool_result


class _Text:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, content, is_error=False):
        self.content = content
        self.isError = is_error


class TestParseToolResult:
    def test_parses_json_object(self):
        r = _Result([_Text('{"firstname": "Ada"}')])
        assert parse_tool_result(r) == {"firstname": "Ada"}

    def test_parses_json_list(self):
        r = _Result([_Text('[{"a": 1}]')])
        assert parse_tool_result(r) == [{"a": 1}]

    def test_non_json_text_returned_raw(self):
        r = _Result([_Text("just text")])
        assert parse_tool_result(r) == "just text"

    def test_error_result_is_none(self):
        r = _Result([_Text('{"a": 1}')], is_error=True)
        assert parse_tool_result(r) is None

    def test_empty_content_is_none(self):
        assert parse_tool_result(_Result([])) is None
        assert parse_tool_result(None) is None


class TestResolvePath:
    def test_nested_dict(self):
        data = {"properties": {"firstname": "Ada"}}
        assert _resolve_path(data, "properties.firstname") == "Ada"

    def test_top_level(self):
        assert _resolve_path({"age": 42}, "age") == "42"

    def test_list_takes_first(self):
        data = {"contacts": [{"name": "Ada"}, {"name": "Bob"}]}
        assert _resolve_path(data, "contacts.name") == "Ada"

    def test_missing_path_is_none(self):
        assert _resolve_path({"a": 1}, "b") is None
        assert _resolve_path({"a": {"b": 1}}, "a.c") is None

    def test_non_scalar_leaf_is_none(self):
        assert _resolve_path({"a": {"b": 1}}, "a") is None


class TestFirstRecord:
    def test_list_first(self):
        assert _first_record([{"x": 1}, {"y": 2}]) == {"x": 1}

    def test_empty_list_none(self):
        assert _first_record([]) is None

    def test_dict_passthrough(self):
        assert _first_record({"x": 1}) == {"x": 1}


class TestProfileCrmPlanActionable:
    def test_disabled_not_actionable(self):
        assert not ProfileCrmPlan().is_actionable

    def test_missing_config_not_actionable(self):
        p = ProfileCrmPlan(enabled=True, fill_plan=[("name", "firstname")])
        assert not p.is_actionable

    def test_fully_configured_actionable(self):
        p = ProfileCrmPlan(
            enabled=True,
            mcp_server_id="srv",
            lookup_tool_name="search",
            phone_argument="phone",
            fill_plan=[("name", "firstname")],
        )
        assert p.is_actionable


def _patch_call_tool(monkeypatch, record=None, raises=False):
    """Replace the CRM connection with an in-memory fake."""

    @contextmanager
    def _fake_ctx():
        yield None

    monkeypatch.setattr("core.database.session.get_db_context", _fake_ctx)

    class _FakeMcp:
        def __init__(self, db, org_id=None, **kwargs):
            pass

        async def call_tool(self, mcp_server_id, tool_name, arguments):
            if raises:
                raise RuntimeError("CRM down")
            return record

    monkeypatch.setattr(
        "core.services.mcp_server_service.McpServerService", _FakeMcp
    )


def _plan():
    return ProfileCrmPlan(
        enabled=True,
        mcp_server_id="srv",
        lookup_tool_name="search",
        phone_argument="phone",
        fill_plan=[("username", "properties.firstname"), ("age", "properties.age")],
    )


class TestEnrich:
    def test_maps_fields_to_profile_keys(self, monkeypatch):
        _patch_call_tool(
            monkeypatch,
            record={"properties": {"firstname": "Ada", "age": 36}},
        )
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=_plan(), caller_phone="+15551234567"
            )
        )
        assert out == {"profile.username": "Ada", "profile.age": "36"}

    def test_takes_first_of_list(self, monkeypatch):
        _patch_call_tool(
            monkeypatch,
            record=[{"properties": {"firstname": "Ada"}}, {"properties": {"firstname": "Bob"}}],
        )
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=_plan(), caller_phone="+1555"
            )
        )
        assert out["profile.username"] == "Ada"
        assert "profile.age" not in out  # unresolved path skipped

    def test_lookup_error_degrades_to_empty(self, monkeypatch):
        _patch_call_tool(monkeypatch, raises=True)
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=_plan(), caller_phone="+1555"
            )
        )
        assert out == {}

    def test_not_actionable_skips(self, monkeypatch):
        _patch_call_tool(monkeypatch, record={"x": 1})
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=ProfileCrmPlan(), caller_phone="+1555"
            )
        )
        assert out == {}

    def test_no_phone_skips(self, monkeypatch):
        _patch_call_tool(monkeypatch, record={"properties": {"firstname": "Ada"}})
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=_plan(), caller_phone=""
            )
        )
        assert out == {}


class _Row:
    def __init__(self, key, value, crm_field):
        self.key = key
        self.value = value
        self.crm_field = crm_field


class TestGetCrmFillPlan:
    def _svc(self, rows):
        svc = AgentProfileVariableService(db=None, org_id="org")
        svc.list_variables = lambda agent_id: rows
        return svc

    def test_only_empty_and_mapped(self):
        rows = [
            _Row("username", "", "properties.firstname"),  # empty + mapped → in
            _Row("age", "", "properties.age"),  # empty + mapped → in
            _Row("set", "Ada", "properties.firstname"),  # has value → skip
            _Row("unmapped", "", None),  # no crm_field → skip
            _Row("blankmap", "", "   "),  # whitespace crm_field → skip
        ]
        plan = self._svc(rows).get_crm_fill_plan("agent")
        assert plan == [
            ("username", "properties.firstname"),
            ("age", "properties.age"),
        ]

    def test_empty_when_nothing_mapped(self):
        rows = [_Row("a", "x", None), _Row("b", "", None)]
        assert self._svc(rows).get_crm_fill_plan("agent") == []


class TestLoadProfileCrmPlan:
    def test_missing_ids_returns_disabled_plan(self):
        # Pure short-circuit path (no DB touched) — proves profile_context and
        # the config service import cleanly and the off path is safe.
        assert load_profile_crm_plan(None, None, None).is_actionable is False
        assert AgentProfileCrmConfigService is not None
