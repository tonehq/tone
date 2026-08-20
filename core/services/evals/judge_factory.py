"""Judge engine selector — the ONE place ``EVAL_JUDGE_ENGINE`` is inspected.

Returns an object that duck-types the ``JudgeService.judge(...)`` contract:
the same kwargs, and a return dict with the legacy keys
(``verdict``/``correctness``/``groundedness``/``relevance``/``reasoning``)
plus — for DeepEval — an extra ``metric_scores`` field.

Callers (``EvalService.run_eval``) never inspect the setting themselves so
switching engines is a one-line env change and rollback is instant.
"""

from __future__ import annotations

from typing import Optional

from core.services.evals.errors import EvalConfigurationError
from core.services.evals.judge import JudgeService
from core.services.evals.prompt_loader import PromptLoader
from shared.config import settings


def build_judge_service(
    *,
    prompt_loader: Optional[PromptLoader] = None,
    engine: Optional[str] = None,
    metrics_enabled: Optional[list[str]] = None,
    metric_threshold: Optional[float] = None,
) -> object:
    """Return the judge for the given engine, defaulting to ``settings.EVAL_JUDGE_ENGINE``.

    ``engine`` (optional) — override for the env value. When callers
    resolve per-org eval settings they pass ``cfg.judge_engine`` here so
    the choice honors the org override without every caller re-checking env.

    ``metrics_enabled`` / ``metric_threshold`` (optional) — resolved per-org
    overrides forwarded to the DeepEval judge. ``None`` means "let the judge
    fall through to env at judge-time" (the pre-org-settings behavior).

    ``prompt_loader`` is forwarded to the legacy ``JudgeService`` so it
    shares the same template cache/instance as the surrounding
    ``EvalService``. DeepEval doesn't use it (metric prompts ship inside
    the SDK).
    """
    resolved_engine = (engine or settings.EVAL_JUDGE_ENGINE or "").strip().lower()
    if resolved_engine == "deepeval":
        # Lazy import: keeps DeepEval + its OTel hijack / nest_asyncio
        # monkey-patch / PostHog beacons out of processes that never eval
        # (the FastAPI app pod).
        from core.services.evals.deepeval import DeepEvalJudgeService

        return DeepEvalJudgeService(
            metrics_enabled=metrics_enabled,
            metric_threshold=metric_threshold,
        )
    if resolved_engine == "legacy":
        return JudgeService(prompt_loader=prompt_loader)
    raise EvalConfigurationError(
        f"Unknown judge engine {resolved_engine!r} "
        "(supported: 'deepeval', 'legacy')"
    )
