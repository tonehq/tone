"""Unit tests for the mid-call find_customer CRM lookup tool (Layer 2).

Pure logic + monkeypatched CRM call — no DB or network. Run:
    pytest test-cases/test_find_customer_tool.py -v -o "addopts="
"""

import asyncio
import json
from contextlib import contextmanager

from core.services.pipeline.tools.find_customer_tool import (
    FIND_CUSTOMER_TOOL_NAME,
    FIND_CUSTOMER_TOOL_SCHEMA,
    create_find_customer_handler,
    prepend_find_customer_instructions,
)


class _Params:
    """Minimal stand-in for pipecat FunctionCallParams."""

    def __init__(self, arguments):
        self.arguments = arguments
        self.tool_call_id = None
        self.result = None

    async def result_callback(self, text):
        self.result = text


def _patch_crm(monkeypatch, record=None, raises=False, capture=None):
    @contextmanager
    def _fake_ctx():
        yield None

    monkeypatch.setattr("core.database.session.get_db_context", _fake_ctx)

    class _FakeMcp:
        def __init__(self, db, org_id=None, **kwargs):
            pass

        async def call_tool(self, mcp_server_id, tool_name, arguments):
            if capture is not None:
                capture["tool"] = tool_name
                capture["args"] = arguments
            if raises:
                raise RuntimeError("CRM down")
            return record

    monkeypatch.setattr("core.services.mcp_server_service.McpServerService", _FakeMcp)


def _run(handler, arguments):
    params = _Params(arguments)
    asyncio.run(handler(params))
    return params.result


class TestFindCustomerHandler:
    def test_schema_and_name(self):
        assert FIND_CUSTOMER_TOOL_NAME == "find_customer"
        assert FIND_CUSTOMER_TOOL_SCHEMA.name == "find_customer"
        assert set(FIND_CUSTOMER_TOOL_SCHEMA.properties["field"]["enum"]) == {
            "phone",
            "email",
            "name",
        }

    def test_email_lookup_returns_record_json(self, monkeypatch):
        capture = {}
        _patch_crm(
            monkeypatch,
            record={"results": [{"email": "ada@x.com", "firstname": "Ada"}]},
            capture=capture,
        )
        handler = create_find_customer_handler(
            org_id="org", mcp_server_id="srv", crm_slug="hubspot"
        )
        out = _run(handler, {"field": "email", "value": "ada@x.com"})
        # correct preset tool + email filter used
        assert capture["tool"] == "hubspot-search-objects"
        assert capture["args"]["filters"][0]["propertyName"] == "email"
        # returns the matched record (record_path "results" stripped) as JSON
        assert json.loads(out) == {"email": "ada@x.com", "firstname": "Ada"}

    def test_no_match_message(self, monkeypatch):
        _patch_crm(monkeypatch, record={"results": []})
        handler = create_find_customer_handler(
            org_id="org", mcp_server_id="srv", crm_slug="salesforce"
        )
        out = _run(handler, {"field": "name", "value": "Nobody"})
        assert out == "No matching customer found."

    def test_error_is_safe(self, monkeypatch):
        _patch_crm(monkeypatch, raises=True)
        handler = create_find_customer_handler(
            org_id="org", mcp_server_id="srv", crm_slug="zoho_crm"
        )
        out = _run(handler, {"field": "phone", "value": "+1555"})
        assert "could not be completed" in out

    def test_bad_field_or_empty_value(self, monkeypatch):
        _patch_crm(monkeypatch, record={"results": [{"x": 1}]})
        handler = create_find_customer_handler(
            org_id="org", mcp_server_id="srv", crm_slug="hubspot"
        )
        assert "Could not run the lookup" in _run(handler, {"field": "ssn", "value": "x"})
        assert "Could not run the lookup" in _run(handler, {"field": "email", "value": ""})


class TestPrependGuidance:
    def test_prepends_to_system_message(self):
        msgs = [{"role": "system", "content": "You are a helpful agent."}]
        out = prepend_find_customer_instructions(msgs)
        assert out[0]["content"].startswith("## Looking up the caller")
        assert out[0]["content"].endswith("You are a helpful agent.")
        # original not mutated
        assert msgs[0]["content"] == "You are a helpful agent."

    def test_noop_without_system_message(self):
        msgs = [{"role": "user", "content": "hi"}]
        assert prepend_find_customer_instructions(msgs) == msgs
