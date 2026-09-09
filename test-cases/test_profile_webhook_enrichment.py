"""Unit tests for webhook enrichment of profile variables.

Pure logic + a monkeypatched endpoint call — no DB or network. Run:
    pytest test-cases/test_profile_webhook_enrichment.py -v -o "addopts="
"""

import asyncio

from core.services.agents.agent_profile_webhook_service import (
    AgentProfileWebhookService,
    WebhookPlan,
    _descend,
    _direction_enabled,
    _first_record,
    _resolve_scalar,
)
from core.services.agents.profile_webhook_schemas import is_usable_scalar
from core.services.agents.webhook_failure_strategies import get_failure_strategy


def _svc_with_endpoint(return_value=None, raises=None):
    svc = AgentProfileWebhookService(None, org_id="org-1")

    async def fake_call(**_kwargs):
        if raises is not None:
            raise raises
        return return_value

    svc._call_endpoint = fake_call  # type: ignore[method-assign]
    return svc


def _plan(**overrides) -> WebhookPlan:
    base = dict(
        enabled=True,
        endpoint_url="https://api.example.com/lookup",
        http_method="POST",
        headers_blob=None,
        request_identifiers=[{"identifier": "phone", "param": "phone", "in": "body"}],
        directions={"inbound": True, "outbound": False},
        timeout_seconds=3,
        fill_plan=[("customer_name", "properties.name")],
    )
    base.update(overrides)
    return WebhookPlan(**base)


class TestScalarValidation:
    def test_scalars_are_usable(self):
        assert is_usable_scalar("x") is True
        assert is_usable_scalar(5) is True
        assert is_usable_scalar(1.5) is True
        assert is_usable_scalar(True) is True

    def test_non_scalars_are_not(self):
        assert is_usable_scalar(None) is False
        assert is_usable_scalar({"a": 1}) is False
        assert is_usable_scalar([1, 2]) is False


class TestResolvers:
    def test_nested_dict(self):
        assert _resolve_scalar({"properties": {"name": "Ada"}}, "properties.name") == "Ada"

    def test_deep_path(self):
        data = {"data": {"customer": {"tier": "gold"}}}
        assert _resolve_scalar(data, "data.customer.tier") == "gold"

    def test_list_takes_first(self):
        assert _first_record([{"name": "A"}, {"name": "B"}]) == {"name": "A"}
        assert _resolve_scalar(_first_record([{"name": "A"}]), "name") == "A"

    def test_missing_path_is_none(self):
        assert _resolve_scalar({"a": 1}, "properties.name") is None

    def test_non_scalar_leaf_is_none(self):
        assert _resolve_scalar({"properties": {"name": {"x": 1}}}, "properties.name") is None

    def test_number_stringified(self):
        assert _resolve_scalar({"n": 5}, "n") == "5"

    def test_descend_missing_sentinel(self):
        from core.services.agents.agent_profile_webhook_service import _MISSING

        assert _descend({"a": 1}, "b") is _MISSING


class TestDirectionGating:
    def test_inbound_enabled(self):
        assert _direction_enabled({"inbound": True, "outbound": False}, "inbound") is True

    def test_outbound_disabled(self):
        assert _direction_enabled({"inbound": True, "outbound": False}, "outbound") is False

    def test_none_direction_treated_as_inbound(self):
        assert _direction_enabled({"inbound": True}, None) is True


class TestPlanActionable:
    def test_actionable_when_enabled_url_and_fill_plan(self):
        assert _plan().is_actionable is True

    def test_not_actionable_without_fill_plan(self):
        assert _plan(fill_plan=[]).is_actionable is False

    def test_not_actionable_when_disabled(self):
        assert _plan(enabled=False).is_actionable is False


class TestEnrich:
    def test_fills_from_2xx_response(self):
        svc = _svc_with_endpoint((200, {"properties": {"name": "John"}}))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+15551234", direction="inbound"))
        assert out == {"profile.customer_name": "John"}

    def test_list_response_uses_first(self):
        svc = _svc_with_endpoint((200, [{"properties": {"name": "Jane"}}]))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="inbound"))
        assert out == {"profile.customer_name": "Jane"}

    def test_non_2xx_returns_empty(self):
        svc = _svc_with_endpoint((404, {"properties": {"name": "John"}}))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="inbound"))
        assert out == {}

    def test_missing_path_skips_variable(self):
        svc = _svc_with_endpoint((200, {"other": "x"}))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="inbound"))
        assert out == {}

    def test_disabled_direction_returns_empty(self):
        svc = _svc_with_endpoint((200, {"properties": {"name": "John"}}))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="outbound"))
        assert out == {}

    def test_blank_phone_returns_empty(self):
        svc = _svc_with_endpoint((200, {"properties": {"name": "John"}}))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="   ", direction="inbound"))
        assert out == {}

    def test_endpoint_exception_degrades_to_empty(self):
        svc = _svc_with_endpoint(raises=RuntimeError("boom"))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="inbound"))
        assert out == {}

    def test_non_dict_record_returns_empty(self):
        svc = _svc_with_endpoint((200, "plain text"))
        out = asyncio.run(svc.enrich(plan=_plan(), caller_phone="+1", direction="inbound"))
        assert out == {}


class TestFailureStrategies:
    def test_inbound_graceful(self):
        s = get_failure_strategy("inbound")
        assert s.abort is False
        assert s.on_failure() == {}

    def test_outbound_stub_graceful_for_now(self):
        s = get_failure_strategy("outbound")
        # Outbound abort is deferred; v1 degrades gracefully like inbound.
        assert s.on_failure() == {}
