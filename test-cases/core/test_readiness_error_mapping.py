"""Lock the readiness error → HTTP mapping.

``ReadinessService`` is transport-agnostic: it raises typed errors from
``core.services.readiness.errors`` (never ``HTTPException``) so it can be reused
from a CLI / job / another service. The API layer restores the exact HTTP
contract via the single ``_readiness_error_handler`` registered on the api_v1
sub-app in ``main.py``. These tests exercise that handler directly and assert
each error maps to the SAME status + body the routes used to raise, so the wire
contract is unchanged for existing API callers.
"""

from __future__ import annotations

import asyncio
import json

from main import _readiness_error_handler

from core.services.readiness.errors import (
    AgentNotFoundError,
    InvalidAgentIdError,
    ReadinessBlockedError,
    ReadinessError,
    ReadinessRateLimitedError,
    ReadinessRunNotFoundError,
    ReadinessWarningsError,
)
from core.services.readiness.schemas import Depth, OverallStatus, ReadinessReport


def _map(exc: ReadinessError):
    """Run the handler and return (status_code, parsed_json_body)."""
    resp = asyncio.run(_readiness_error_handler(None, exc))
    return resp.status_code, json.loads(resp.body)


class TestSimpleErrors:
    def test_invalid_agent_id_maps_to_400(self):
        status, body = _map(InvalidAgentIdError("Invalid agent id"))
        assert status == 400
        assert body == {"detail": "Invalid agent id"}

    def test_agent_not_found_maps_to_404(self):
        status, body = _map(AgentNotFoundError("Agent not found"))
        assert status == 404
        assert body == {"detail": "Agent not found"}

    def test_rate_limited_maps_to_429(self):
        status, body = _map(ReadinessRateLimitedError("slow down"))
        assert status == 429
        assert body == {"detail": "slow down"}

    def test_run_not_found_maps_to_404(self):
        status, body = _map(ReadinessRunNotFoundError("Readiness run not found"))
        assert status == 404
        assert body == {"detail": "Readiness run not found"}

    def test_unknown_subclass_falls_back_to_400(self):
        # A future ReadinessError subclass not in the map must degrade to 400,
        # never surface as an unhandled 500.
        class _Future(ReadinessError):
            pass

        status, _ = _map(_Future("something new"))
        assert status == 400


class TestPublishGateErrors:
    def _report(self) -> ReadinessReport:
        return ReadinessReport(
            agent_id="a1",
            depth=Depth.DEEP,
            overall_status=OverallStatus.NOT_READY,
            summary={"blockers": 2, "warnings": 0},
            checks=[],
        )

    def test_blocked_maps_to_400_with_structured_body(self):
        status, body = _map(ReadinessBlockedError("2 blocker(s)", self._report()))
        assert status == 400
        detail = body["detail"]
        assert detail["reason"] == "readiness_blocked"
        assert detail["message"] == "2 blocker(s)"
        # Full report is embedded and JSON-serialized (enums → their values).
        assert detail["report"]["overall_status"] == "not_ready"
        assert detail["report"]["summary"]["blockers"] == 2

    def test_warnings_maps_to_400_with_reason(self):
        status, body = _map(ReadinessWarningsError("1 warning(s)", self._report()))
        assert status == 400
        assert body["detail"]["reason"] == "readiness_warnings"
        assert body["detail"]["message"] == "1 warning(s)"


def test_service_module_imports_no_http():
    # Guard the whole point of the refactor: the service layer must not import
    # FastAPI's HTTPException. If someone reintroduces it, this fails.
    import inspect

    import core.services.readiness.readiness_service as svc_mod

    source = inspect.getsource(svc_mod)
    assert "HTTPException" not in source
