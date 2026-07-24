"""RAG evaluation services.

Transport-agnostic building blocks that persist question sets + eval runs into
Postgres and run retrieval / grounded-answer / LLM-as-judge against the exact
pipeline recipe under test.

Callers:
- Procrastinate ``eval_ingestion_run`` task (auto-run after ingestion completes)
- ``rag-testing/scripts/*`` CLI (manual smoke test)
"""

from core.services.evals.errors import (
    EvalError,
    EvalGenerationError,
    EvalNotFoundError,
    EvalRunError,
)
from core.services.evals.eval_service import EvalService
from core.services.evals.judge import JudgeService
from core.services.evals.question_generator import QuestionGeneratorService

__all__ = [
    "EvalError",
    "EvalGenerationError",
    "EvalNotFoundError",
    "EvalRunError",
    "EvalService",
    "JudgeService",
    "QuestionGeneratorService",
]
