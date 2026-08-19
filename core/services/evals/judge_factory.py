"""Judge engine selector — the ONE place ``EVAL_JUDGE_ENGINE`` is inspected.

Returns an object that duck-types the ``JudgeService.judge(...)`` contract:
the same kwargs, and a return dict with the legacy keys
(``verdict``/``correctness``/``groundedness``/``relevance``/``reasoning``)
plus — for DeepEval — an extra ``metric_scores`` field.

Callers (``EvalService.__init__``) never inspect the setting themselves so
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
) -> object:
    """Return the judge selected by ``settings.EVAL_JUDGE_ENGINE``.

    ``prompt_loader`` is forwarded to the legacy ``JudgeService`` so it
    shares the same template cache/instance as the surrounding
    ``EvalService``. DeepEval doesn't use it (metric prompts ship inside
    the SDK).
    """
    engine = (settings.EVAL_JUDGE_ENGINE or "").strip().lower()
    if engine == "deepeval":
        # Lazy import: keeps DeepEval + its OTel hijack / nest_asyncio
        # monkey-patch / PostHog beacons out of processes that never eval
        # (the FastAPI app pod).
        from core.services.evals.deepeval import DeepEvalJudgeService

        return DeepEvalJudgeService()
    if engine == "legacy":
        return JudgeService(prompt_loader=prompt_loader)
    raise EvalConfigurationError(
        f"Unknown EVAL_JUDGE_ENGINE {settings.EVAL_JUDGE_ENGINE!r} "
        "(supported: 'deepeval', 'legacy')"
    )
