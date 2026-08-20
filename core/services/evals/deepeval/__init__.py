"""DeepEval integration — isolated so the FastAPI app never triggers
DeepEval's OpenTelemetry hijack, ``nest_asyncio`` monkey-patch, or PostHog/
Sentry telemetry beacons.

Only workers (Procrastinate ``eval_ingestion_run`` task) and the
``rag-testing/`` CLI import from this package.

Import order guarantee: ``telemetry`` runs first so its opt-out env vars
are stamped BEFORE any ``deepeval`` submodule is loaded.
"""

from __future__ import annotations

from core.services.evals.deepeval import telemetry as _telemetry  # noqa: F401  (side effect: opt-out env)
from core.services.evals.deepeval.judge_service import DeepEvalJudgeService

__all__ = ["DeepEvalJudgeService"]
