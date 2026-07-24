"""EvalService tests — isolated, DB and LLM stubbed via MagicMock.

The service is transport-agnostic (takes a session + plain args), so we can
exercise every branch without a live Postgres or an OpenAI key. Focused on:

- ``generate_eval`` inserts an ``Eval`` row with ``question_count`` matching
  the generator output and ``status="ready"``.
- ``run_eval`` computes ``run_number = 1`` on first call, ``2`` on second.
- ``run_eval`` builds retrieval from the passed ``ingestion_run_id`` — same
  embedder/store the ingestion used, NOT from any global default.
- ``run_eval`` failure path never raises and marks the row failed.
- ``compare_results`` flags verdict downgrades as regressions.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.services.evals.eval_service import (
    EvalService,
    _diff_results,
    _summarize,
)


class _QueryChain:
    """Minimal SQLAlchemy query-chain stub. Each ``query(Model).filter(...).first()``
    hop is dispatched through a per-model handler set by the test."""

    def __init__(self, first_map=None, scalar=None, order_first=None):
        self._first_map = first_map or {}
        self._scalar = scalar
        self._order_first = order_first
        self._current_model = None

    def query(self, *args, **kwargs):
        self._current_model = args[0] if args else None
        return self

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_map.get(self._current_model)

    def scalar(self):
        return self._scalar


def _make_upload(upload_id):
    return SimpleNamespace(
        id=upload_id,
        file_path="uploads/foo.pdf",
        file_type="application/pdf",
        file_name="foo.pdf",
    )


def _make_kb(kb_id, name="KB Name"):
    return SimpleNamespace(id=kb_id, name=name)


def _make_run(run_id):
    return SimpleNamespace(
        id=run_id,
        upload_id=uuid4(),
        organization_id=uuid4(),
        embedding_provider="openai",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=1536,
        vector_store="pgvector",
        vector_store_ref=None,
    )


def _service_with_stubs(question_payload, judge_payload):
    q_gen = MagicMock()
    q_gen.prompt_hash.return_value = "sha-hex"
    q_gen.generate.return_value = question_payload

    judge = MagicMock()
    judge.judge.return_value = judge_payload

    reader = MagicMock()
    reader.read.return_value = SimpleNamespace(text="hello world")

    r2 = MagicMock()
    r2.download_file.return_value = b"pdf-bytes"

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = "Answer the {{QUESTION}} from {{CONTEXT}}"

    svc = EvalService(
        question_generator=q_gen,
        judge=judge,
        prompt_loader=prompt_loader,
        reader=reader,
        r2_service=r2,
    )
    return svc, q_gen, judge, reader, r2


# ── generate_eval ──────────────────────────────────────────────────────


def test_generate_eval_inserts_new_row_when_none_exists():
    upload_id = uuid4()
    kb = _make_kb(uuid4())
    upload = _make_upload(upload_id)
    org_id = uuid4()

    payload = {
        "generated_by_model": "gpt-4o",
        "questions": [
            {"id": "q1", "question": "What?", "expected_answer": "Yes", "category": "factual"},
            {"id": "q2", "question": "Why?", "expected_answer": "Because", "category": "factual"},
        ],
    }
    svc, q_gen, *_ = _service_with_stubs(payload, {})

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        upload,  # Upload lookup
        kb,      # KnowledgeBase lookup
        None,    # existing Eval → none
    ]

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ):
        svc.generate_eval(db, upload_id=upload_id, org_id=org_id)

    added = db.add.call_args_list[0][0][0]
    assert added.question_count == 2
    assert added.status == "ready"
    assert added.generated_by_model == "gpt-4o"
    assert added.generation_prompt_hash == "sha-hex"
    assert added.upload_id == upload_id
    assert added.organization_id == org_id
    assert db.commit.called
    q_gen.generate.assert_called_once()


def test_generate_eval_updates_existing_row_in_place():
    upload_id = uuid4()
    kb = _make_kb(uuid4())
    upload = _make_upload(upload_id)
    org_id = uuid4()
    existing = SimpleNamespace(
        id=uuid4(),
        upload_id=upload_id,
        organization_id=org_id,
        name="stale",
        question_count=0,
        questions={},
        generated_by_model=None,
        generation_prompt_hash=None,
        status="failed",
        error="prev failure",
    )

    payload = {
        "generated_by_model": "gpt-4o",
        "questions": [{"id": "q1", "question": "?", "expected_answer": "!"}],
    }
    svc, *_ = _service_with_stubs(payload, {})

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        upload,
        kb,
        existing,
    ]
    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ):
        svc.generate_eval(db, upload_id=upload_id, org_id=org_id)

    # Existing row mutated — no new insert.
    assert db.add.called is False
    assert existing.status == "ready"
    assert existing.question_count == 1
    assert existing.error is None
    assert existing.generated_by_model == "gpt-4o"


# ── run_eval ───────────────────────────────────────────────────────────


def _run_eval_with_scalar(scalar_run_number, judge_payload=None):
    """Helper: exercise run_eval with a stubbed next-run-number scalar."""
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id

    eval_row = SimpleNamespace(
        id=uuid4(),
        organization_id=org_id,
        upload_id=upload_id,
        questions={"questions": [
            {"id": "q1", "question": "What?", "expected_answer": "Yes",
             "expected_source_snippet": "", "category": "factual"},
        ]},
    )

    payload = {"generated_by_model": "gpt-4o", "questions": []}
    verdict = judge_payload or {
        "verdict": "PASS", "correctness": 1.0, "groundedness": 1.0,
        "relevance": 1.0, "reasoning": "ok",
    }
    svc, _, judge, *_ = _service_with_stubs(payload, verdict)

    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 4
    store = MagicMock()
    hit = SimpleNamespace(
        text="matching chunk", score=0.01,
        metadata={"chunk_index": 0, "upload_id": str(upload_id)},
    )
    store.query.return_value = [hit]

    db = MagicMock()
    query_chain = MagicMock()
    # Order of .filter().first() calls in run_eval:
    #   Eval lookup, IngestionPipelineRun lookup
    query_chain.filter.return_value.first.side_effect = [eval_row, run]
    # Order of scalar() call: next_run_number
    query_chain.filter.return_value.scalar.return_value = scalar_run_number
    db.query.return_value = query_chain

    openai_client = MagicMock()
    openai_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="the answer"))]
    )

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        return_value=embedder,
    ) as build_embedder, patch(
        "core.services.evals.eval_service.get_vector_store",
        return_value=store,
    ) as get_store, patch(
        "openai.OpenAI", return_value=openai_client,
    ):
        result = svc.run_eval(
            db,
            eval_id=eval_row.id,
            ingestion_run_id=run_id,
            triggered_by="cli",
            top_k=8,
        )

    return result, build_embedder, get_store, store, run, judge


def test_run_eval_uses_run_number_from_scalar():
    result, *_ = _run_eval_with_scalar(scalar_run_number=1)
    assert result.run_number == 1

    result2, *_ = _run_eval_with_scalar(scalar_run_number=2)
    assert result2.run_number == 2


def test_run_eval_builds_retrieval_from_ingestion_run():
    """Embedder + store MUST be built from the passed run — not from any
    global default — so query and stored vectors are always compatible."""
    _, build_embedder, get_store, store, run, _ = _run_eval_with_scalar(1)

    build_embedder.assert_called_once()
    (called_run,), kwargs = build_embedder.call_args
    assert called_run is run
    assert kwargs["api_key"] == "sk-xxx"

    get_store.assert_called_once_with(run.vector_store)

    # store.query filters must include ingestion_run_id pin
    _, query_kwargs = store.query.call_args
    filters = query_kwargs["filters"]
    assert filters["ingestion_run_id"] == run.id
    assert filters["embedding_provider"] == "openai"
    assert filters["embedding_dimensions"] == 1536


def test_run_eval_marks_completed_and_populates_summary():
    result, *_ = _run_eval_with_scalar(1)
    assert result.status == "completed"
    assert result.summary is not None
    assert result.summary["total"] == 1
    assert result.summary["pass"] == 1
    assert result.per_question and result.per_question[0]["id"] == "q1"


def test_run_eval_failure_path_marks_failed_and_does_not_raise():
    """A retrieval crash mid-run must set status='failed', capture the error,
    and return the row — worker callers rely on run_eval being terminal."""
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id

    eval_row = SimpleNamespace(
        id=uuid4(),
        organization_id=org_id,
        upload_id=upload_id,
        questions={"questions": [{"id": "q1", "question": "?", "expected_answer": "!"}]},
    )
    svc, *_ = _service_with_stubs({"generated_by_model": "gpt-4o", "questions": []}, {})

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.filter.return_value.first.side_effect = [eval_row, run]
    query_chain.filter.return_value.scalar.return_value = 1
    db.query.return_value = query_chain

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        side_effect=RuntimeError("boom"),
    ):
        result = svc.run_eval(
            db, eval_id=eval_row.id, ingestion_run_id=run_id,
            triggered_by="auto", top_k=4,
        )

    assert result.status == "failed"
    assert result.error and "boom" in result.error
    assert result.completed_at is not None


def test_run_eval_rejects_unknown_triggered_by():
    svc = EvalService()
    with pytest.raises(ValueError):
        svc.run_eval(
            db=MagicMock(),
            eval_id=uuid4(),
            ingestion_run_id=uuid4(),
            triggered_by="bogus",
        )


# ── compare_results ────────────────────────────────────────────────────


def test_diff_flags_verdict_regression():
    baseline = SimpleNamespace(
        id=uuid4(), run_number=1, started_at=None,
        summary={"pass_rate": 1.0},
        per_question=[
            {"id": "q1", "judge": {"verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0}, "retrieval_hit": True},
        ],
    )
    candidate = SimpleNamespace(
        id=uuid4(), run_number=2, started_at=None,
        summary={"pass_rate": 0.0},
        per_question=[
            {"id": "q1", "judge": {"verdict": "FAIL", "correctness": 0.0, "groundedness": 0.0, "relevance": 0.0}, "retrieval_hit": False},
        ],
    )
    diff = _diff_results(baseline, candidate, score_drop=0.15)
    assert diff["regression_count"] == 1
    assert diff["regressions"][0]["note"].startswith("verdict regression")


def test_diff_no_regression_when_scores_stable():
    row = {"id": "q1", "judge": {"verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0}, "retrieval_hit": True}
    baseline = SimpleNamespace(id=uuid4(), run_number=1, started_at=None, summary={}, per_question=[row])
    candidate = SimpleNamespace(id=uuid4(), run_number=2, started_at=None, summary={}, per_question=[row])
    diff = _diff_results(baseline, candidate, score_drop=0.15)
    assert diff["regression_count"] == 0


# ── summarize ─────────────────────────────────────────────────────────


def test_summarize_computes_rates():
    rows = [
        {"judge": {"verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0},
         "retrieval_hit": True, "latency_ms": 100, "category": "factual"},
        {"judge": {"verdict": "FAIL", "correctness": 0.0, "groundedness": 0.0, "relevance": 0.0},
         "retrieval_hit": False, "latency_ms": 200, "category": "factual"},
    ]
    s = _summarize(rows)
    assert s["total"] == 2
    assert s["pass_rate"] == 0.5
    assert s["fail_rate"] == 0.5
    assert s["retrieval_hit_rate"] == 0.5
    assert s["duration_ms"] == 300
    assert s["by_category"]["factual"]["total"] == 2
