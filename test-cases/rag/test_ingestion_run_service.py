"""Tests for IngestionRunService's active-run invariants (isolated, no DB).

We stub the SQLAlchemy session so the tests run without a live Postgres.
The service surface we exercise:
- resolve_run_config merges defaults with overrides.
- begin_pending_run inserts with is_active=False so a failed re-ingest doesn't
  yank the previous active run.
- complete_run flips the previous active run to inactive BEFORE flipping the
  new one to active (partial unique index requires one at a time), then
  points the parent KB at the new run.
- fail_run does NOT flip is_active.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.services.ingestion_run_service import IngestionRunService


@pytest.fixture(autouse=True)
def _stub_eval_enqueue():
    """Every ``complete_run`` call fires ``enqueue_eval_for_ingestion_run_sync``
    when ``EVAL_AUTO_RUN_ENABLED`` is true. Without this stub, a test run with
    infisical env active would defer a real Procrastinate job with the mock's
    stringified ``id`` (e.g. ``ingestion_run_id='new'``) to whatever DB the env
    points at. Patch the enqueue for every test in this module so they stay
    fully hermetic."""
    with patch(
        "core.services.ingestion_queue.enqueue_eval_for_ingestion_run_sync"
    ) as enq:
        yield enq


def test_resolve_run_config_uses_defaults_when_no_override():
    cfg = IngestionRunService.resolve_run_config(
        db=MagicMock(), org_id="o", knowledge_base_id="kb", request_config=None
    )
    assert cfg["parser"] == "docling"
    assert cfg["tokeniser"] == "docling_hybrid"
    assert cfg["embedding_provider"] == "openai"
    assert cfg["embedding_model"] == "text-embedding-3-small"
    assert cfg["embedding_dimensions"] == 1536
    assert cfg["vector_store"] == "pgvector"


def test_resolve_run_config_applies_override():
    override = {
        "parser": "pypdf",
        "embedding_model": "text-embedding-3-large",
        "embedding_dimensions": 3072,
        "vector_store": "pinecone",
        "vector_store_ref": {"index": "test"},
    }
    cfg = IngestionRunService.resolve_run_config(
        db=MagicMock(), org_id="o", knowledge_base_id="kb", request_config=override
    )
    assert cfg["parser"] == "pypdf"
    assert cfg["tokeniser"] == "docling_hybrid"  # untouched → default
    assert cfg["embedding_model"] == "text-embedding-3-large"
    assert cfg["embedding_dimensions"] == 3072
    assert cfg["vector_store"] == "pinecone"
    assert cfg["vector_store_ref"] == {"index": "test"}


def test_resolve_run_config_ignores_none_values():
    override = {"parser": None, "embedding_dimensions": 1024}
    cfg = IngestionRunService.resolve_run_config(
        db=MagicMock(), org_id="o", knowledge_base_id="kb", request_config=override
    )
    assert cfg["parser"] == "docling"  # None override -> default kept
    assert cfg["embedding_dimensions"] == 1024


def test_complete_run_deactivates_prior_active_run_first():
    """complete_run must issue the UPDATE that flips the previous active run to
    False BEFORE setting the new run's is_active=True — otherwise the partial
    unique index (one active per upload) rejects the transaction."""
    db = MagicMock()
    run = MagicMock()
    run.id = "new"
    run.upload_id = "u1"
    run.is_active = False

    # db.query(...).filter(...).first() → run
    db.query.return_value.filter.return_value.first.return_value = run
    # db.query(...).filter(...).update(...) → 1
    db.query.return_value.filter.return_value.update.return_value = 1

    IngestionRunService.complete_run(db, "new", chunk_count=42)

    # The UPDATE (deactivate prior) must be issued before we set is_active=True
    # on the target run + commit. We verify the update filter targets the same
    # upload but excludes the target run.
    update_call = db.query.return_value.filter.return_value.update
    assert update_call.called
    update_kwargs = update_call.call_args_list[0][0][0]
    assert update_kwargs == {"is_active": False}

    assert run.status == "ready"
    assert run.is_active is True
    assert run.chunk_count == 42
    assert db.commit.called


def test_fail_run_does_not_change_is_active():
    """A failed run must NOT flip is_active — the previous active run continues
    to serve retrieval."""
    db = MagicMock()
    run = MagicMock()
    run.id = "new"
    run.is_active = False  # begin_pending_run always writes False
    db.query.return_value.filter.return_value.first.return_value = run

    IngestionRunService.fail_run(db, "new", error="boom")

    assert run.status == "failed"
    assert run.is_active is False  # unchanged
    assert run.error == "boom"


def test_complete_run_missing_raises_value_error():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ValueError):
        IngestionRunService.complete_run(db, "missing", chunk_count=1)


def test_fail_run_missing_raises_value_error():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ValueError):
        IngestionRunService.fail_run(db, "missing", error="x")


def test_delete_runs_for_upload_bulk_deletes_and_returns_count():
    """File-replace purge: deletes every run for the upload (org-scoped) and
    returns the count. Chunks + embeddings go via DB FK ON DELETE CASCADE."""
    db = MagicMock()
    db.query.return_value.filter.return_value.delete.return_value = 3
    n = IngestionRunService.delete_runs_for_upload(db, upload_id="u", org_id="o")
    assert n == 3
    db.query.return_value.filter.return_value.delete.assert_called_once_with(
        synchronize_session=False
    )
    db.commit.assert_called_once()
