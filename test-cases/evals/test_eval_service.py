"""EvalService tests — isolated, DB and LLM stubbed via MagicMock.

The service is transport-agnostic (takes a session + plain args), so we can
exercise every branch without a live Postgres or an OpenAI key. Focused on:

- ``generate_eval`` deletes any existing questions for the upload, then
  bulk-inserts one ``evals`` row per question.
- ``run_eval`` computes ``run_number`` from the scalar query, stamps a fresh
  ``run_id``, scores each question, and bulk-inserts one ``eval_results``
  row per scored answer via a fresh session.
- ``run_eval`` builds retrieval from the passed ``ingestion_run_id`` — same
  embedder/store the ingestion used, NOT from any global default.
- ``run_eval`` failure path never raises and marks the run failed, writing
  a placeholder row per un-scored question.
- ``_diff_scored_rows`` / ``_summarize_scored_rows`` produce the same shape
  the CLI already consumes.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from core.services.evals.eval_service import (
    EvalRunSummary,
    EvalService,
    _diff_scored_rows,
    _summarize_scored_rows,
)


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


def _make_question_row(*, external_id="q1", question_ord=0, org_id=None):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        external_id=external_id,
        question_ord=question_ord,
        question=f"What is {external_id}?",
        expected_answer=f"Answer to {external_id}",
        expected_source_snippet="snippet",
        category="factual",
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


def test_generate_eval_deletes_existing_and_bulk_inserts_new_rows():
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
    db.query.return_value.filter.return_value.first.side_effect = [upload, kb]

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        return_value="sk-xxx",
    ):
        summary = svc.generate_eval(db, upload_id=upload_id, org_id=org_id)

    # Existing rows for the upload are deleted first.
    db.query.return_value.filter.return_value.delete.assert_called_once_with(
        synchronize_session=False
    )
    # One bulk_insert per generate_eval call.
    db.bulk_insert_mappings.assert_called_once()
    _, inserted_rows = db.bulk_insert_mappings.call_args[0]
    assert len(inserted_rows) == 2
    assert [r["external_id"] for r in inserted_rows] == ["q1", "q2"]
    assert [r["question_ord"] for r in inserted_rows] == [0, 1]
    assert all(r["upload_id"] == upload_id for r in inserted_rows)
    assert all(r["organization_id"] == org_id for r in inserted_rows)
    assert all(r["generated_by_model"] == "gpt-4o" for r in inserted_rows)
    assert all(r["generation_prompt_hash"] == "sha-hex" for r in inserted_rows)
    assert db.commit.called
    q_gen.generate.assert_called_once()

    assert summary.question_count == 2
    assert summary.upload_id == upload_id
    assert summary.generated_by_model == "gpt-4o"
    assert summary.generation_prompt_hash == "sha-hex"


def test_generate_eval_regeneration_replaces_rows_in_place():
    """Second call with different questions still deletes old + inserts new —
    no leftover rows from the previous batch."""
    upload_id = uuid4()
    kb = _make_kb(uuid4())
    upload = _make_upload(upload_id)
    org_id = uuid4()

    payload = {
        "generated_by_model": "gpt-4o",
        "questions": [{"id": "q1", "question": "?", "expected_answer": "!"}],
    }
    svc, *_ = _service_with_stubs(payload, {})

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [upload, kb]
    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        return_value="sk-xxx",
    ):
        svc.generate_eval(db, upload_id=upload_id, org_id=org_id)

    db.query.return_value.filter.return_value.delete.assert_called_once_with(
        synchronize_session=False
    )
    db.bulk_insert_mappings.assert_called_once()


# ── run_eval ───────────────────────────────────────────────────────────


def _run_eval_with_scalar(scalar_run_number, judge_payload=None, extra_persist=None):
    """Helper: exercise run_eval with a stubbed next-run-number scalar and a
    single question row."""
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id
    question_row = _make_question_row(org_id=org_id)

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
        text="chunk containing snippet text", score=0.01,
        metadata={"chunk_index": 0, "upload_id": str(upload_id)},
    )
    store.query.return_value = [hit]

    db = MagicMock()
    query_chain = MagicMock()
    # Order of query hops inside run_eval:
    #   1. Eval.query — .filter().order_by().all() → questions list
    #   2. IngestionPipelineRun.query — .filter().first() → run
    #   3. func.coalesce.query — .filter().scalar() → next_run_number
    query_chain.filter.return_value.order_by.return_value.all.return_value = [question_row]
    query_chain.filter.return_value.first.return_value = run
    query_chain.filter.return_value.scalar.return_value = scalar_run_number
    db.query.return_value = query_chain

    persisted_rows: list = []

    fresh_session_cm = MagicMock()
    fresh_session_cm.__enter__.return_value = fresh_session_cm
    fresh_session_cm.__exit__.return_value = False

    def _capture_bulk_insert(_model, rows):
        persisted_rows.extend(rows)

    fresh_session_cm.bulk_insert_mappings.side_effect = _capture_bulk_insert
    session_local = MagicMock(return_value=fresh_session_cm)

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        return_value=embedder,
    ) as build_embedder, patch(
        "core.services.evals.eval_service.get_vector_store",
        return_value=store,
    ) as get_store, patch(
        "core.services.evals.eval_service.chat_complete",
        return_value="the answer",
    ), patch(
        "core.database.session.SessionLocal", session_local,
    ):
        result = svc.run_eval(
            db,
            upload_id=upload_id,
            ingestion_run_id=run_id,
            triggered_by="cli",
            top_k=8,
        )

    if extra_persist is not None:
        extra_persist.extend(persisted_rows)
    return result, build_embedder, get_store, store, run, judge, persisted_rows


def test_run_eval_uses_run_number_from_scalar():
    result, *_ = _run_eval_with_scalar(scalar_run_number=1)
    assert result.run_number == 1

    result2, *_ = _run_eval_with_scalar(scalar_run_number=2)
    assert result2.run_number == 2


def test_run_eval_stamps_new_run_id_each_call():
    result_a, *_ = _run_eval_with_scalar(1)
    result_b, *_ = _run_eval_with_scalar(1)
    assert result_a.run_id != result_b.run_id


def test_run_eval_builds_retrieval_from_ingestion_run():
    """Embedder + store MUST be built from the passed run — not from any
    global default — so query and stored vectors are always compatible."""
    _, build_embedder, get_store, store, run, _, _ = _run_eval_with_scalar(1)

    build_embedder.assert_called_once()
    (called_run,), kwargs = build_embedder.call_args
    assert called_run is run
    assert kwargs["api_key"] == "sk-xxx"

    get_store.assert_called_once_with(run.vector_store)

    _, query_kwargs = store.query.call_args
    filters = query_kwargs["filters"]
    assert filters["ingestion_run_id"] == run.id
    assert filters["embedding_provider"] == "openai"
    assert filters["embedding_dimensions"] == 1536


def test_run_eval_persists_one_result_row_per_question():
    result, *_, persisted = _run_eval_with_scalar(1)
    assert result.status == "completed"
    assert result.summary["total"] == 1
    assert result.summary["pass"] == 1
    assert len(persisted) == 1
    row = persisted[0]
    assert row["run_id"] == result.run_id
    assert row["run_number"] == result.run_number
    assert row["status"] == "completed"
    assert row["verdict"] == "PASS"
    assert row["actual_answer"] == "the answer"
    assert row["retrieval_hit"] is True


def test_run_eval_failure_path_marks_failed_and_does_not_raise():
    """A retrieval crash mid-run must set status='failed', capture the error,
    and return the summary — worker callers rely on run_eval being terminal."""
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id
    question_row = _make_question_row(org_id=org_id)

    svc, *_ = _service_with_stubs({"generated_by_model": "gpt-4o", "questions": []}, {})

    db = MagicMock()
    query_chain = MagicMock()
    query_chain.filter.return_value.order_by.return_value.all.return_value = [question_row]
    query_chain.filter.return_value.first.return_value = run
    query_chain.filter.return_value.scalar.return_value = 1
    db.query.return_value = query_chain

    persisted_rows: list = []
    fresh_session_cm = MagicMock()
    fresh_session_cm.__enter__.return_value = fresh_session_cm
    fresh_session_cm.__exit__.return_value = False
    fresh_session_cm.bulk_insert_mappings.side_effect = (
        lambda _model, rows: persisted_rows.extend(rows)
    )
    session_local = MagicMock(return_value=fresh_session_cm)

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        side_effect=RuntimeError("boom"),
    ), patch(
        "core.database.session.SessionLocal", session_local,
    ):
        result = svc.run_eval(
            db, upload_id=upload_id, ingestion_run_id=run_id,
            triggered_by="auto", top_k=4,
        )

    assert result.status == "failed"
    assert result.error and "boom" in result.error
    assert result.completed_at is not None
    # Unscored question gets a placeholder row so the run's shape is complete.
    assert len(persisted_rows) == 1
    assert persisted_rows[0]["status"] == "failed"


def test_run_eval_rejects_unknown_triggered_by():
    svc = EvalService()
    with pytest.raises(ValueError):
        svc.run_eval(
            db=MagicMock(),
            upload_id=uuid4(),
            ingestion_run_id=uuid4(),
            triggered_by="bogus",
        )


def test_run_eval_resolves_answer_provider_from_model():
    """When answer_model is a Gemini slug, the eval flow must fetch a Google
    key (not the hardcoded OpenAI one) and hand it to chat_complete. Guards
    the regression the router was built to fix."""
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id
    question_row = _make_question_row(org_id=org_id)

    svc, _, _judge, *_ = _service_with_stubs(
        {"generated_by_model": "gpt-4o", "questions": []},
        {"verdict": "PASS", "correctness": 1.0, "groundedness": 1.0,
         "relevance": 1.0, "reasoning": "ok"},
    )

    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 4
    store = MagicMock()
    store.query.return_value = []

    db = MagicMock()
    chain = MagicMock()
    chain.filter.return_value.order_by.return_value.all.return_value = [question_row]
    chain.filter.return_value.first.return_value = run
    chain.filter.return_value.scalar.return_value = 1
    db.query.return_value = chain

    fresh_session_cm = MagicMock()
    fresh_session_cm.__enter__.return_value = fresh_session_cm
    fresh_session_cm.__exit__.return_value = False
    fresh_session_cm.bulk_insert_mappings.side_effect = lambda _m, _r: None
    session_local = MagicMock(return_value=fresh_session_cm)

    def _require_by_provider(_db, _org, slug):
        return f"key-for-{slug}"

    def _get_by_provider(_db, _org, slug):
        return f"key-for-{slug}"

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        side_effect=_require_by_provider,
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        side_effect=_get_by_provider,
    ) as get_key, patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        return_value=embedder,
    ), patch(
        "core.services.evals.eval_service.get_vector_store", return_value=store,
    ), patch(
        "core.services.evals.eval_service.chat_complete",
        return_value="the gemini answer",
    ) as chat_complete_mock, patch(
        "core.database.session.SessionLocal", session_local,
    ):
        result = svc.run_eval(
            db,
            upload_id=upload_id,
            ingestion_run_id=run_id,
            triggered_by="cli",
            top_k=4,
            answer_model="gemini-2.5-flash",
            judge_model="claude-3-5-sonnet-20241022",
        )

    assert result.status == "completed"
    slugs = [call.args[2] for call in get_key.call_args_list]
    assert "google" in slugs, f"expected google key fetch, got slugs={slugs}"
    assert "anthropic" in slugs, f"expected anthropic key fetch, got slugs={slugs}"
    assert "openai" not in slugs, (
        "openai key must not be fetched when the caller opts into gemini/claude"
    )

    call_kwargs = chat_complete_mock.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash"
    assert call_kwargs["api_key"] == "key-for-google"
    assert call_kwargs["json_mode"] is False


# ── compare_results ────────────────────────────────────────────────────


def _row(qid, verdict, correctness=1.0, groundedness=1.0, relevance=1.0, hit=True):
    return {
        "id": qid,
        "judge": {
            "verdict": verdict,
            "correctness": correctness,
            "groundedness": groundedness,
            "relevance": relevance,
        },
        "retrieval_hit": hit,
    }


def _summary(run_number, run_id=None):
    return EvalRunSummary(
        run_id=run_id or uuid4(),
        upload_id=uuid4(),
        ingestion_run_id=uuid4(),
        run_number=run_number,
        triggered_by="cli",
        top_k=8,
        answer_model="gpt-4o",
        judge_model="gpt-4o",
        status="completed",
        error=None,
        started_at=None,
        completed_at=None,
        summary={"pass_rate": 1.0},
    )


def test_diff_flags_verdict_regression():
    baseline = _summary(1)
    candidate = _summary(2)
    diff = _diff_scored_rows(
        baseline_summary=baseline,
        candidate_summary=candidate,
        baseline_rows=[_row("q1", "PASS")],
        candidate_rows=[_row("q1", "FAIL", correctness=0, groundedness=0, relevance=0, hit=False)],
        score_drop=0.15,
    )
    assert diff["regression_count"] == 1
    assert diff["regressions"][0]["note"].startswith("verdict regression")


def test_diff_no_regression_when_scores_stable():
    baseline = _summary(1)
    candidate = _summary(2)
    row = _row("q1", "PASS")
    diff = _diff_scored_rows(
        baseline_summary=baseline,
        candidate_summary=candidate,
        baseline_rows=[row],
        candidate_rows=[row],
        score_drop=0.15,
    )
    assert diff["regression_count"] == 0


# ── summarize ─────────────────────────────────────────────────────────


def test_summarize_computes_rates():
    rows = [
        {"judge": {"verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0},
         "retrieval_hit": True, "latency_ms": 100, "category": "factual"},
        {"judge": {"verdict": "FAIL", "correctness": 0.0, "groundedness": 0.0, "relevance": 0.0},
         "retrieval_hit": False, "latency_ms": 200, "category": "factual"},
    ]
    s = _summarize_scored_rows(rows)
    assert s["total"] == 2
    assert s["pass_rate"] == 0.5
    assert s["fail_rate"] == 0.5
    assert s["retrieval_hit_rate"] == 0.5
    assert s["duration_ms"] == 300
    assert s["by_category"]["factual"]["total"] == 2


def test_summarize_emits_per_deepeval_metric_averages():
    """Rows with a DeepEval scorecard contribute per-metric averages under
    ``avg_<metric>``; legacy averages are untouched."""
    rows = [
        {
            "judge": {
                "verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0,
                "metric_scores": {
                    "faithfulness": {"score": 0.8, "verdict": "pass", "reason": ""},
                    "answer_relevancy": {"score": 0.9, "verdict": "pass", "reason": ""},
                    "contextual_precision": {"score": 0.6, "verdict": "fail", "reason": "x"},
                },
            },
            "retrieval_hit": True, "latency_ms": 50, "category": "factual",
        },
        {
            "judge": {
                "verdict": "PASS", "correctness": 1.0, "groundedness": 1.0, "relevance": 1.0,
                "metric_scores": {
                    "faithfulness": {"score": 1.0, "verdict": "pass", "reason": ""},
                    "answer_relevancy": {"score": 0.7, "verdict": "pass", "reason": ""},
                },
            },
            "retrieval_hit": True, "latency_ms": 60, "category": "factual",
        },
    ]
    s = _summarize_scored_rows(rows)
    assert s["avg_faithfulness"] == 0.9  # (0.8+1.0)/2
    assert s["avg_answer_relevancy"] == 0.8  # (0.9+0.7)/2
    # contextual_precision only present on the first row — averaged over 1.
    assert s["avg_contextual_precision"] == 0.6
    # Legacy averages still work.
    assert s["avg_correctness"] == 1.0


# ── metric_scores persistence + factory wiring ─────────────────────────────


def test_run_eval_persists_metric_scores_and_summary_per_metric():
    """When the judge returns a DeepEval scorecard, ``_persist_result_batch``
    stamps it on the row and ``_summarize_scored_rows`` folds it into
    per-metric averages on the returned run summary."""
    from unittest.mock import ANY as _ANY  # noqa: F401 — silence unused-import warning if trimmed
    upload_id = uuid4()
    run_id = uuid4()
    run = _make_run(run_id)
    org_id = run.organization_id
    question_row = _make_question_row(org_id=org_id)

    scorecard = {
        "faithfulness": {"score": 0.9, "verdict": "pass", "reason": ""},
        "answer_relevancy": {"score": 0.8, "verdict": "pass", "reason": ""},
        "contextual_precision": {"score": 0.75, "verdict": "pass", "reason": ""},
        "hallucination": {"score": 0.2, "verdict": "pass", "reason": ""},
        "correctness": {"score": 0.9, "verdict": "pass", "reason": ""},
    }
    verdict = {
        "verdict": "PASS",
        "correctness": 0.9,
        "groundedness": 0.9,
        "relevance": 0.8,
        "reasoning": "",
        "metric_scores": scorecard,
    }
    svc, _, _judge, *_ = _service_with_stubs(
        {"generated_by_model": "gpt-4o", "questions": []},
        verdict,
    )

    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 4
    store = MagicMock()
    store.query.return_value = []

    db = MagicMock()
    chain = MagicMock()
    chain.filter.return_value.order_by.return_value.all.return_value = [question_row]
    chain.filter.return_value.first.return_value = run
    chain.filter.return_value.scalar.return_value = 1
    db.query.return_value = chain

    persisted: list = []
    fresh = MagicMock()
    fresh.__enter__.return_value = fresh
    fresh.__exit__.return_value = False
    fresh.bulk_insert_mappings.side_effect = lambda _m, rows: persisted.extend(rows)
    session_local = MagicMock(return_value=fresh)

    with patch(
        "core.services.evals.eval_service.ProviderKeyService.require_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.ProviderKeyService.get_key",
        return_value="sk-xxx",
    ), patch(
        "core.services.evals.eval_service.build_embedder_from_run",
        return_value=embedder,
    ), patch(
        "core.services.evals.eval_service.get_vector_store",
        return_value=store,
    ), patch(
        "core.services.evals.eval_service.chat_complete",
        return_value="the answer",
    ), patch(
        "core.database.session.SessionLocal", session_local,
    ):
        result = svc.run_eval(
            db, upload_id=upload_id, ingestion_run_id=run_id,
            triggered_by="cli", top_k=4,
        )

    assert result.status == "completed"
    assert len(persisted) == 1
    row = persisted[0]
    assert row["metric_scores"] == scorecard
    # Legacy columns still flow from the mapped metrics.
    assert row["verdict"] == "PASS"
    assert row["correctness"] == 0.9
    assert row["groundedness"] == 0.9
    assert row["relevance"] == 0.8
    # Per-metric averages surface on the summary.
    summary = result.summary
    assert summary["avg_faithfulness"] == 0.9
    assert summary["avg_answer_relevancy"] == 0.8
    assert summary["avg_contextual_precision"] == 0.75
    assert summary["avg_hallucination"] == 0.2


def test_eval_service_defaults_to_factory_built_judge(monkeypatch):
    """When no judge kwarg is passed, EvalService must ask the factory —
    the env flip (``EVAL_JUDGE_ENGINE=legacy``) is the ONLY way to change
    engines, and it must actually take effect."""
    from core.services.evals.judge import JudgeService as LegacyJudge
    from shared.config import settings

    monkeypatch.setattr(settings, "EVAL_JUDGE_ENGINE", "legacy", raising=False)
    svc = EvalService()
    assert isinstance(svc._judge, LegacyJudge)
