"""Typed errors for the readiness service.

Mirrors the pattern in ``core/services/ingestion_errors.py`` and the other
service ``errors`` modules: the service layer stays transport-agnostic (no
``HTTPException`` import), so ``ReadinessService`` can be reused unchanged from
an API route, a CLI, a background job, or another service. Each caller decides
how to surface these — the API maps them to HTTP via the handler registered in
``main.py`` (``_readiness_error_handler``); a CLI/job can catch the same classes
and print/log/retry.

Every error below subclasses ``ReadinessError`` so a single ``except
ReadinessError`` (or one registered handler) catches the whole family.
"""

from __future__ import annotations

from typing import Any


class ReadinessError(Exception):
    """Base for every readiness service error. Transport-agnostic."""


class InvalidAgentIdError(ReadinessError):
    """The supplied agent id isn't a valid UUID. Maps to HTTP 400."""


class AgentNotFoundError(ReadinessError):
    """No agent for the caller's (org, id) scope. Maps to HTTP 404."""


class ReadinessRateLimitedError(ReadinessError):
    """A deep readiness run was rejected by the per-(org, agent) rate limiter.
    Maps to HTTP 429."""


class ReadinessRunNotFoundError(ReadinessError):
    """No stored deep run for the requested (agent, run_number). Maps to HTTP
    404."""


class PublishGateError(ReadinessError):
    """Base for the publish-gate failures raised by ``gate_publish``.

    Carries the full ``ReadinessReport`` plus a stable machine-readable
    ``reason`` and a user-facing ``message`` so the API layer can reproduce the
    exact ``{"reason", "message", "report"}`` body the publish flow depends on
    without the service knowing anything about HTTP. Maps to HTTP 400.
    """

    #: Stable machine-readable code the frontend switches on.
    reason: str = "readiness_error"

    def __init__(self, message: str, report: Any) -> None:
        super().__init__(message)
        self.message = message
        self.report = report


class ReadinessBlockedError(PublishGateError):
    """The target version has BLOCKER-level failures — publish is refused."""

    reason = "readiness_blocked"


class ReadinessWarningsError(PublishGateError):
    """The target version has only WARNINGs and the caller didn't opt in with
    ``force_warnings=True``."""

    reason = "readiness_warnings"
