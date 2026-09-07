"""Unit tests for ``AgentLlmEvalVersionService`` helpers + guard paths.

The DB-heavy lifecycle (generate / approve / reject) needs a real Postgres
session and is covered by integration tests; here we assert the pure helpers
and the pre-DB validation guards, matching the ``MagicMock``-session pattern
used across ``test-cases/evals/agent_llm/``.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from core.services.evals.agent_llm.version_service import (
    AgentLlmEvalVersionService,
    _model_from_persisted,
    _prompt_hash,
)
from core.services.evals.errors import EvalGenerationError


def test_prompt_hash_is_deterministic_and_none_safe():
    assert _prompt_hash(None) is None
    assert _prompt_hash("") is None
    h1 = _prompt_hash("focus on refunds")
    h2 = _prompt_hash("focus on refunds")
    assert h1 == h2
    assert h1 != _prompt_hash("focus on cancellations")
    # SHA-256 hex digest length.
    assert len(h1) == 64


def test_model_from_persisted_reads_first_recorded_model():
    row_no_meta = MagicMock(generation_metadata=None)
    row_with_model = MagicMock(generation_metadata={"model": "gpt-4o-mini"})
    assert _model_from_persisted([row_no_meta, row_with_model]) == "gpt-4o-mini"
    # Falls back through the alternative keys.
    row_judge = MagicMock(generation_metadata={"judge_model": "claude-x"})
    assert _model_from_persisted([row_judge]) == "claude-x"
    # Nothing usable → None.
    assert _model_from_persisted([MagicMock(generation_metadata={})]) is None
    assert _model_from_persisted([]) is None


def test_generate_rejects_unknown_mode_before_touching_db():
    svc = AgentLlmEvalVersionService(MagicMock(), org_id=uuid4())
    with pytest.raises(EvalGenerationError):
        svc.generate(uuid4(), mode="replace")


def test_resolve_version_overwrite_requires_version_id():
    svc = AgentLlmEvalVersionService(MagicMock(), org_id=uuid4())
    with pytest.raises(EvalGenerationError):
        svc._resolve_generation_version(
            uuid4(), mode="overwrite", version_id=None, generation_prompt=None
        )
