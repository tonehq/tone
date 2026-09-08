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
from core.services.agents.profile_context import (
    load_profile_crm_plan,
    resolve_crm_lookup_binding,
)
from core.services.agents.crm_lookup_presets import (
    get_crm_lookup_preset,
    has_crm_lookup_preset,
)
from core.services.agents.profile_crm_enrichment_service import (
    ProfileCrmEnrichmentService,
    ProfileCrmPlan,
    _first_record,
    _resolve_path,
    extract_record,
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


class TestExtractRecord:
    def test_wrapper_descend_first(self):
        assert extract_record({"results": [{"a": 1}, {"a": 2}]}, "results") == {"a": 1}
        assert extract_record({"records": [{"b": 2}]}, "records") == {"b": 2}
        assert extract_record({"data": [{"c": 3}]}, "data") == {"c": 3}

    def test_no_record_path_takes_dict_or_first(self):
        assert extract_record({"x": 1}, "") == {"x": 1}
        assert extract_record([{"x": 1}], "") == {"x": 1}

    def test_missing_or_empty_none(self):
        assert extract_record({"results": []}, "results") is None
        assert extract_record({"other": [{"a": 1}]}, "results") is None
        assert extract_record(None, "results") is None


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


class TestCrmLookupPresets:
    def test_zoho_fields(self):
        p = get_crm_lookup_preset("zoho_crm")
        assert p.default_tool_name == "Search Records"
        assert p.record_path == "data"
        assert p.build_arguments("phone", "+1555") == {"phone": "+1555", "module": "Contacts"}
        assert p.build_arguments("email", "a@x.com") == {"email": "a@x.com", "module": "Contacts"}
        assert p.build_arguments("name", "Ada Lee") == {"word": "Ada Lee", "module": "Contacts"}

    def test_hubspot_fields(self):
        p = get_crm_lookup_preset("hubspot")
        assert p.default_tool_name == "hubspot-search-objects"
        assert p.record_path == "results"
        phone_args = p.build_arguments("phone", "+1 (443) 443-9905")
        assert phone_args["object_type"] == "contacts"
        assert phone_args["filters"][0] == {
            "propertyName": "phone",
            "operator": "CONTAINS_TOKEN",
            "value": "+1 (443) 443-9905",
        }
        email_args = p.build_arguments("email", "a@x.com")
        assert email_args["filters"][0] == {
            "propertyName": "email",
            "operator": "EQ",
            "value": "a@x.com",
        }
        # name → full-text query, no filters
        name_args = p.build_arguments("name", "Ada Lee")
        assert name_args == {"object_type": "contacts", "query": "Ada Lee"}

    def test_salesforce_fields_and_soql_escaping(self):
        p = get_crm_lookup_preset("salesforce")
        assert p.default_tool_name == "Query"
        assert p.record_path == "records"
        phone_soql = p.build_arguments("phone", "+1 (443) 443-9905")["query"]
        assert "FROM Contact" in phone_soql
        assert "14434439905" in phone_soql  # non-digits stripped
        assert "LIMIT 1" in phone_soql
        assert p.build_arguments("email", "a@x.com")["query"].count("Email = 'a@x.com'") == 1
        # single quote in a spoken name is escaped, not left to break the literal
        esc = p.build_arguments("name", "O'Brien")["query"]
        assert "O\\'Brien" in esc

    def test_unsupported_field_raises(self):
        import pytest

        with pytest.raises(ValueError):
            get_crm_lookup_preset("zoho_crm").build_arguments("ssn", "x")


class _Config:
    def __init__(self, is_enabled=True, mcp_server_id="srv"):
        self.is_enabled = is_enabled
        self.mcp_server_id = mcp_server_id


def _patch_binding(monkeypatch, config, slug):
    class _FakeConfigSvc:
        def __init__(self, db, org_id=None, **kwargs):
            pass

        def get_config(self, agent_id):
            return config

    class _FakeMcp:
        def __init__(self, db, org_id=None, **kwargs):
            pass

        def get_integration_slug(self, mcp_server_id):
            return slug

    monkeypatch.setattr(
        "core.services.agents.agent_profile_crm_config_service.AgentProfileCrmConfigService",
        _FakeConfigSvc,
    )
    monkeypatch.setattr("core.services.mcp_server_service.McpServerService", _FakeMcp)


class TestResolveCrmLookupBinding:
    def test_enabled_preset_returns_binding(self, monkeypatch):
        _patch_binding(monkeypatch, _Config(), "hubspot")
        assert resolve_crm_lookup_binding(None, "org", "agent") == ("srv", "hubspot")

    def test_disabled_returns_none(self, monkeypatch):
        _patch_binding(monkeypatch, _Config(is_enabled=False), "hubspot")
        assert resolve_crm_lookup_binding(None, "org", "agent") is None

    def test_non_preset_slug_returns_none(self, monkeypatch):
        _patch_binding(monkeypatch, _Config(), "some_custom_crm")
        assert resolve_crm_lookup_binding(None, "org", "agent") is None

    def test_no_config_returns_none(self, monkeypatch):
        _patch_binding(monkeypatch, None, "hubspot")
        assert resolve_crm_lookup_binding(None, "org", "agent") is None

    def test_unknown_and_none_slug(self):
        assert get_crm_lookup_preset("mystery") is None
        assert get_crm_lookup_preset(None) is None
        assert has_crm_lookup_preset("hubspot") is True
        assert has_crm_lookup_preset(None) is False


def _preset_plan(slug):
    """Actionable plan for a preset CRM — no tool/phone_argument stored (the
    preset supplies them)."""
    return ProfileCrmPlan(
        enabled=True,
        mcp_server_id="srv",
        crm_slug=slug,
        fill_plan=[("username", "properties.firstname"), ("age", "properties.age")],
    )


class TestPresetActionable:
    def test_preset_needs_no_tool_or_phone_arg(self):
        assert _preset_plan("hubspot").is_actionable is True

    def test_generic_still_requires_tool_and_arg(self):
        assert ProfileCrmPlan(
            enabled=True, mcp_server_id="srv", fill_plan=[("a", "b")]
        ).is_actionable is False


class TestEnrichWithPreset:
    def test_hubspot_wrapper_and_args(self, monkeypatch):
        captured = {}

        @contextmanager
        def _fake_ctx():
            yield None

        monkeypatch.setattr("core.database.session.get_db_context", _fake_ctx)

        class _FakeMcp:
            def __init__(self, db, org_id=None, **kwargs):
                pass

            async def call_tool(self, mcp_server_id, tool_name, arguments):
                captured["tool"] = tool_name
                captured["args"] = arguments
                # HubSpot wraps matches under "results".
                return {"results": [{"properties": {"firstname": "Ada", "age": 36}}]}

        monkeypatch.setattr("core.services.mcp_server_service.McpServerService", _FakeMcp)

        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=_preset_plan("hubspot"), caller_phone="+1555"
            )
        )
        # preset tool + structured filter used
        assert captured["tool"] == "hubspot-search-objects"
        assert captured["args"]["filters"][0]["operator"] == "CONTAINS_TOKEN"
        # crm_field resolved RELATIVE to the record (record_path "results" stripped)
        assert out == {"profile.username": "Ada", "profile.age": "36"}

    def test_salesforce_records_wrapper(self, monkeypatch):
        @contextmanager
        def _fake_ctx():
            yield None

        monkeypatch.setattr("core.database.session.get_db_context", _fake_ctx)

        class _FakeMcp:
            def __init__(self, db, org_id=None, **kwargs):
                pass

            async def call_tool(self, mcp_server_id, tool_name, arguments):
                assert tool_name == "Query"
                assert "SELECT" in arguments["query"]
                return {"records": [{"FirstName": "Bob"}]}

        monkeypatch.setattr("core.services.mcp_server_service.McpServerService", _FakeMcp)

        plan = ProfileCrmPlan(
            enabled=True,
            mcp_server_id="srv",
            crm_slug="salesforce",
            fill_plan=[("username", "FirstName")],
        )
        out = asyncio.run(
            ProfileCrmEnrichmentService().enrich(
                org_id="org", plan=plan, caller_phone="+1555"
            )
        )
        assert out == {"profile.username": "Bob"}
