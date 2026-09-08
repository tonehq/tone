"""Unit tests for ``AgentLlmEvalVersionService`` helpers + guard paths.

The DB-heavy lifecycle (generate / approve / reject) needs a real Postgres
session and is covered by integration tests; here we assert the pure helpers
and the pre-DB validation guards, matching the ``MagicMock``-session pattern
used across ``test-cases/evals/agent_llm/``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.services.evals.agent_llm.version_service import (
    AgentLlmEvalVersionService,
    GENERATION_FAILED_MESSAGE,
    _model_from_persisted,
    _prompt_hash,
)
from core.services.evals.errors import (
    AgentLlmEvalVersionNotFoundError,
    EvalGenerationError,
)


def _svc_with_first(first, db=None):
    """Build a service whose org-scoped ``query(...).filter(...).first()``
    returns ``first`` — the MagicMock-session pattern used across this file,
    hoisted so the background-generation tests don't re-wire it each time."""
    svc = AgentLlmEvalVersionService(db or MagicMock(), org_id=uuid4())
    svc.query = MagicMock()
    svc.query.return_value.filter.return_value.first.return_value = first
    return svc


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


def test_begin_generation_rejects_unknown_mode_before_touching_db():
    svc = AgentLlmEvalVersionService(MagicMock(), org_id=uuid4())
    with pytest.raises(EvalGenerationError):
        svc.begin_generation(uuid4(), mode="replace")


def test_run_generation_is_noop_when_not_generating():
    # Procrastinate replay after a prior attempt finished: the version is no
    # longer 'generating', so the worker must NOT re-run the generator (which
    # would duplicate scenarios). It returns without constructing the scenario
    # service at all.
    version = MagicMock(status="draft", id=uuid4(), agent_id=uuid4())
    svc = _svc_with_first(version)
    with patch(
        "core.services.evals.agent_llm.version_service.AgentLlmScenarioService"
    ) as scenario_service:
        svc.run_generation(version.id)
    scenario_service.assert_not_called()


def test_run_generation_raises_when_version_missing():
    svc = _svc_with_first(None)
    with pytest.raises(AgentLlmEvalVersionNotFoundError):
        svc.run_generation(uuid4())


def test_run_generation_marks_failed_with_user_safe_message_on_error():
    # A generation failure flips the version to 'failed' via ``fail_generation``
    # with the user-safe message — never the raw exception — rolls back, and is
    # swallowed (no re-raise) so a bad LLM response doesn't crash-loop the job.
    db = MagicMock()
    version = MagicMock(
        status="generating", id=uuid4(), agent_id=uuid4(), generation_prompt=None
    )
    svc = _svc_with_first(version, db=db)
    with patch(
        "core.services.evals.agent_llm.version_service.AgentLlmScenarioService"
    ) as scenario_service, patch.object(svc, "fail_generation") as fail_generation:
        scenario_service.return_value.generate_scenarios.side_effect = (
            EvalGenerationError("raw provider boom")
        )
        svc.run_generation(version.id)  # raise_on_error defaults to False
    db.rollback.assert_called_once()
    fail_generation.assert_called_once()
    args, kwargs = fail_generation.call_args
    assert GENERATION_FAILED_MESSAGE in args or GENERATION_FAILED_MESSAGE in kwargs.values()
    assert "raw provider boom" not in f"{args}{kwargs}"


def test_run_generation_reraises_on_error_when_requested():
    # The synchronous ``generate()`` wrapper (CLI/tests) passes
    # ``raise_on_error=True`` so a failure surfaces instead of silently
    # marking the version failed.
    db = MagicMock()
    version = MagicMock(
        status="generating", id=uuid4(), agent_id=uuid4(), generation_prompt=None
    )
    svc = _svc_with_first(version, db=db)
    with patch(
        "core.services.evals.agent_llm.version_service.AgentLlmScenarioService"
    ) as scenario_service, patch.object(svc, "fail_generation"):
        scenario_service.return_value.generate_scenarios.side_effect = (
            EvalGenerationError("boom")
        )
        with pytest.raises(EvalGenerationError):
            svc.run_generation(version.id, raise_on_error=True)


def test_fail_generation_sets_failed_status_and_truncates_message():
    db = MagicMock()
    version = MagicMock(status="generating", generation_error=None)
    svc = _svc_with_first(version, db=db)
    out = svc.fail_generation(uuid4(), "x" * 900)
    assert version.status == "failed"
    assert version.generation_error == "x" * 500
    db.commit.assert_called_once()
    assert out is version


def test_fail_generation_returns_none_when_version_missing():
    svc = _svc_with_first(None)
    assert svc.fail_generation(uuid4(), "boom") is None
