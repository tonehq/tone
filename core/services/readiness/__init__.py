"""Agent readiness — pre-flight validation for voice agents.

Public surface:

- ``ReadinessService`` — the service the routers call.
- ``schemas.ReadinessReport`` / ``schemas.ReadinessSummary`` — response shapes.
- ``schemas.Depth`` — request-parameter enum ("shallow" | "deep").

Everything else (checks, runner, registry, cache, rate limiter) is internal
and intentionally not re-exported so callers can only depend on the facade.
"""

from core.services.readiness.readiness_service import ReadinessService
from core.services.readiness.schemas import (
    Depth,
    ReadinessReport,
    ReadinessSummary,
)

__all__ = ["ReadinessService", "Depth", "ReadinessReport", "ReadinessSummary"]
