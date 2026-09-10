"""EvaluationConfigService tests — DB + judge stubbed via MagicMock.

Covers the two behaviors the plan calls out as regression-worthy:
- ``run_config`` re-judges the source run's FROZEN answers (no retrieval /
  answer generation) and threads a custom prompt through as the GEval
  ``correctness`` criterion.
- create/validation rules: a custom prompt forces the deepeval engine + the
  ``correctness`` carrier metric; unsupported metrics and out-of-range
  thresholds are rejected.

The evals-package conftest stubs the DeepEval SDK, so importing the service
(which pulls the judge factory) is safe without the real install.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from core.services.evals.evaluation_config_service import EvaluationConfigService


def _chain(*, first=None, scalar=1):
    """A self-returning query chain whose terminal methods are configurable."""
    chain = MagicMock()
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.first.return_value = first
    chain.scalar.return_value = scalar
    chain.all.return_value = []
    chain.update.return_value = None
    return chain


def _frozen_rows(n=2):
    return [
        {
            "eval_id": uuid4(),
            "question": f"Q{i}",
            "expected_answer": f"A{i}",
            "actual_answer": f"actual {i}",
            "retrieved_chunks": [{"text": f"chunk {i}"}],
        }
        for i in range(n)
    ]


def _config(judge_prompt=None, engine="deepeval", metrics=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        judge_model="gpt-4o",
        judge_engine=engine,
        judge_prompt=judge_prompt,
        metrics_enabled=metrics or ["faithfulness", "correctness"],
        metric_threshold=0.7,
    )


def _run_config(config, rows, verdict=None):
    """Exercise run_config with a stubbed config row, frozen rows, and judge."""
    db = MagicMock()
    db.query.return_value = _chain(first=config, scalar=1)

    judge = MagicMock()
    judge.judge.return_value = verdict or {
        "verdict": "PASS",
        "reasoning": "ok",
        "metric_scores": {"correctness": {"score": 1.0, "verdict": "pass", "reason": "ok"}},
    }

    persisted: list = []
    fresh = MagicMock()
    fresh.__enter__.return_value = fresh
    fresh.__exit__.return_value = False
    fresh.bulk_insert_mappings.side_effect = lambda _m, rowlist: persisted.extend(rowlist)

    eval_svc = MagicMock()
    eval_svc.get_scored_rows_for_run.return_value = rows

    with patch(
        "core.services.evals.evaluation_config_service.EvalService",
        return_value=eval_svc,
    ), patch(
        "core.services.evals.evaluation_config_service._require_llm_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.evaluation_config_service.build_judge_service",
        return_value=judge,
    ), patch(
        "core.database.session.SessionLocal", MagicMock(return_value=fresh)
    ):
        svc = EvaluationConfigService(db)
        result = svc.run_config(
            db,
            source_run_id=uuid4(),
            evaluation_config_id=config.id,
        )
    return result, judge, persisted, eval_svc


def test_run_config_reuses_frozen_answers_no_retrieval():
    rows = _frozen_rows(2)
    result, judge, persisted, eval_svc = _run_config(_config(), rows)

    # Frozen answers came from the source run — never re-retrieved / re-answered.
    eval_svc.get_scored_rows_for_run.assert_called_once()
    assert judge.judge.call_count == 2
    # The judge received the FROZEN actual_answer + retrieved_chunks verbatim.
    first_kwargs = judge.judge.call_args_list[0].kwargs
    assert first_kwargs["actual_answer"] == rows[0]["actual_answer"]
    assert first_kwargs["retrieved_chunks"] == rows[0]["retrieved_chunks"]
    assert first_kwargs["model"] == "gpt-4o"

    # One persisted row per question, all sharing config_run_id + run number.
    assert len(persisted) == 2
    assert result["total"] == 2
    assert result["completed"] == 2
    config_run_ids = {r["config_run_id"] for r in persisted}
    assert len(config_run_ids) == 1
    assert str(next(iter(config_run_ids))) == result["config_run_id"]
    assert all(r["config_run_number"] == result["config_run_number"] for r in persisted)


def test_run_config_threads_custom_prompt_as_correctness_criterion():
    prompt = "Only full marks when the answer cites a source."
    _, judge, _, _ = _run_config(_config(judge_prompt=prompt), _frozen_rows(1))
    kwargs = judge.judge.call_args.kwargs
    assert kwargs["criteria"] == {"correctness": prompt}


def test_run_config_without_prompt_omits_criteria():
    _, judge, _, _ = _run_config(_config(judge_prompt=None), _frozen_rows(1))
    assert "criteria" not in judge.judge.call_args.kwargs


def test_run_config_failsoft_marks_row_failed_and_continues():
    db = MagicMock()
    config = _config()
    db.query.return_value = _chain(first=config, scalar=1)

    judge = MagicMock()
    # First question raises, second succeeds → one failed, one completed row.
    judge.judge.side_effect = [
        RuntimeError("boom"),
        {"verdict": "PASS", "reasoning": "ok", "metric_scores": {}},
    ]
    persisted: list = []
    fresh = MagicMock()
    fresh.__enter__.return_value = fresh
    fresh.__exit__.return_value = False
    fresh.bulk_insert_mappings.side_effect = lambda _m, rowlist: persisted.extend(rowlist)
    eval_svc = MagicMock()
    eval_svc.get_scored_rows_for_run.return_value = _frozen_rows(2)

    with patch(
        "core.services.evals.evaluation_config_service.EvalService", return_value=eval_svc
    ), patch(
        "core.services.evals.evaluation_config_service._require_llm_key", return_value="sk"
    ), patch(
        "core.services.evals.evaluation_config_service.build_judge_service", return_value=judge
    ), patch(
        "core.database.session.SessionLocal", MagicMock(return_value=fresh)
    ):
        result = EvaluationConfigService(db).run_config(
            db, source_run_id=uuid4(), evaluation_config_id=config.id
        )

    assert result["total"] == 2
    assert result["completed"] == 1
    assert result["failed"] == 1
    statuses = sorted(r["status"] for r in persisted)
    assert statuses == ["completed", "failed"]


# ── Validation (create_config) ─────────────────────────────────────────────


def _svc_for_create():
    """Service whose dupe-check query returns None (name free)."""
    db = MagicMock()
    db.query.return_value = _chain(first=None)
    return EvaluationConfigService(db, org_id=uuid4()), db


def test_create_custom_prompt_forces_correctness_and_deepeval():
    svc, db = _svc_for_create()
    captured = {}

    def _add(obj):
        captured["obj"] = obj

    db.add.side_effect = _add
    config = svc.create_config(
        name="Custom",
        judge_model="gpt-4o",
        judge_engine="deepeval",
        judge_prompt="grade strictly",
        metrics_enabled=["faithfulness"],  # correctness intentionally omitted
    )
    # The carrier metric is auto-added so the prompt actually takes effect.
    assert "correctness" in captured["obj"].metrics_enabled


def test_create_custom_prompt_rejects_legacy_engine():
    svc, _ = _svc_for_create()
    with pytest.raises(HTTPException) as exc:
        svc.create_config(
            name="Bad",
            judge_model="gpt-4o",
            judge_engine="legacy",
            judge_prompt="grade strictly",
            metrics_enabled=["correctness"],
        )
    assert exc.value.status_code == 400


def test_create_rejects_unsupported_metric():
    svc, _ = _svc_for_create()
    with pytest.raises(HTTPException) as exc:
        svc.create_config(
            name="Bad metric",
            judge_model="gpt-4o",
            metrics_enabled=["role_adherence"],  # conversation-native, not RAG-safe
        )
    assert exc.value.status_code == 400


def test_create_rejects_threshold_out_of_range():
    svc, _ = _svc_for_create()
    with pytest.raises(HTTPException) as exc:
        svc.create_config(
            name="Bad threshold",
            judge_model="gpt-4o",
            metrics_enabled=["faithfulness"],
            metric_threshold=1.5,
        )
    assert exc.value.status_code == 400


def test_create_rejects_duplicate_name():
    db = MagicMock()
    db.query.return_value = _chain(first=SimpleNamespace(id=uuid4()))  # name taken
    svc = EvaluationConfigService(db, org_id=uuid4())
    with pytest.raises(HTTPException) as exc:
        svc.create_config(
            name="Taken",
            judge_model="gpt-4o",
            metrics_enabled=["faithfulness"],
        )
    assert exc.value.status_code == 400


# ── Human-agreement % (list_config_runs) ───────────────────────────────────


def _cfg_result_row(*, config_run_id, run_number, eval_id, verdict):
    return SimpleNamespace(
        config_run_id=config_run_id,
        evaluation_config_id=uuid4(),
        config_run_number=run_number,
        source_run_id=uuid4(),
        verdict=verdict,
        metric_scores={},
        created_at=None,
        eval_id=eval_id,
    )


class _AgreementDB:
    """A db that dispatches ``query`` by model: config-result rows, the human
    label tuples, and (empty) judge-model rows."""

    def __init__(self, *, config_rows, human_rows):
        self._config_rows = config_rows
        self._human_rows = human_rows

    def query(self, *args):
        from core.models.eval_result import EvalResult
        from core.models.evaluation_config_result import EvaluationConfigResult

        head = args[0]
        if head is EvaluationConfigResult:
            return _FakeAgreementQuery(self._config_rows)
        if head is EvalResult:
            return _FakeAgreementQuery(self._human_rows)
        return _FakeAgreementQuery([])  # judge_models lookup → none


class _FakeAgreementQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *a, **k):
        return self

    def with_entities(self, *a, **k):
        return self

    def all(self):
        return list(self._rows)


def test_list_config_runs_scores_agreement_against_human_labels():
    """The pass whose accept/reject matches the human marks scores higher.
    Rule: judge-accept == (verdict==PASS); human-accept == (label=='accept');
    only labeled questions count."""
    e1, e2, e3 = uuid4(), uuid4(), uuid4()
    pass_a, pass_b = uuid4(), uuid4()

    # Human labels: e1 accept, e2 reject, e3 unlabeled (excluded).
    human_rows = [(e1, "accept"), (e2, "reject")]

    config_rows = [
        # Pass A agrees on both labeled questions → 100%.
        _cfg_result_row(config_run_id=pass_a, run_number=1, eval_id=e1, verdict="PASS"),
        _cfg_result_row(config_run_id=pass_a, run_number=1, eval_id=e2, verdict="FAIL"),
        _cfg_result_row(config_run_id=pass_a, run_number=1, eval_id=e3, verdict="PASS"),
        # Pass B disagrees on e1 (says FAIL vs human accept) → 50%.
        _cfg_result_row(config_run_id=pass_b, run_number=2, eval_id=e1, verdict="FAIL"),
        _cfg_result_row(config_run_id=pass_b, run_number=2, eval_id=e2, verdict="FAIL"),
        _cfg_result_row(config_run_id=pass_b, run_number=2, eval_id=e3, verdict="PASS"),
    ]

    db = _AgreementDB(config_rows=config_rows, human_rows=human_rows)
    svc = EvaluationConfigService(db, org_id=uuid4())
    passes = svc.list_config_runs(source_run_id=uuid4())

    by_id = {p["config_run_id"]: p for p in passes}
    a = by_id[str(pass_a)]
    b = by_id[str(pass_b)]

    assert a["labeled_count"] == 2
    assert a["human_agreement"] == 1.0
    assert b["labeled_count"] == 2
    assert b["human_agreement"] == 0.5
    # The better-matching config scores strictly higher.
    assert a["human_agreement"] > b["human_agreement"]


def test_list_config_runs_no_labels_yields_none_agreement():
    """With no human labels, agreement is None and labeled_count is 0 (UI '—')."""
    pass_a = uuid4()
    config_rows = [
        _cfg_result_row(config_run_id=pass_a, run_number=1, eval_id=uuid4(), verdict="PASS"),
    ]
    db = _AgreementDB(config_rows=config_rows, human_rows=[])
    svc = EvaluationConfigService(db, org_id=uuid4())
    passes = svc.list_config_runs(source_run_id=uuid4())

    assert passes[0]["labeled_count"] == 0
    assert passes[0]["human_agreement"] is None
