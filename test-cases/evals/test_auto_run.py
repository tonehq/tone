"""Tests for the auto-run wiring: IngestionRunService.complete_run enqueues
the Procrastinate eval task iff the kill-switch is enabled, and enqueue
failures never break ingestion completion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from core.services.ingestion_run_service import IngestionRunService


def _make_db_returning(run):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = run
    db.query.return_value.filter.return_value.update.return_value = 1
    return db


def test_complete_run_enqueues_eval_when_auto_run_enabled():
    run = MagicMock()
    run.id = uuid4()
    run.upload_id = uuid4()
    run.is_active = False
    db = _make_db_returning(run)

    with patch("core.services.ingestion_run_service.settings") as fake_settings, \
         patch("core.services.ingestion_queue.enqueue_eval_for_ingestion_run_sync") as enq:
        fake_settings.EVAL_AUTO_RUN_ENABLED = True
        IngestionRunService.complete_run(db, run.id, chunk_count=5)

    enq.assert_called_once_with(run.id)


def test_complete_run_does_not_enqueue_when_auto_run_disabled():
    run = MagicMock()
    run.id = uuid4()
    run.upload_id = uuid4()
    run.is_active = False
    db = _make_db_returning(run)

    with patch("core.services.ingestion_run_service.settings") as fake_settings, \
         patch("core.services.ingestion_queue.enqueue_eval_for_ingestion_run_sync") as enq:
        fake_settings.EVAL_AUTO_RUN_ENABLED = False
        IngestionRunService.complete_run(db, run.id, chunk_count=5)

    enq.assert_not_called()


def test_complete_run_swallows_enqueue_failure():
    """Queue outage must NOT fail ingestion — a broken eval path can't take
    down the primary pipeline."""
    run = MagicMock()
    run.id = uuid4()
    run.upload_id = uuid4()
    run.is_active = False
    db = _make_db_returning(run)

    with patch("core.services.ingestion_run_service.settings") as fake_settings, \
         patch(
             "core.services.ingestion_queue.enqueue_eval_for_ingestion_run_sync",
             side_effect=RuntimeError("queue down"),
         ):
        fake_settings.EVAL_AUTO_RUN_ENABLED = True
        # Must not raise
        result = IngestionRunService.complete_run(db, run.id, chunk_count=5)

    assert result is run
    assert run.status == "ready"
    assert run.is_active is True
