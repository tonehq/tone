"""Background job that materializes the per-call series-stat columns.

Runs on the ``call_metrics`` queue after a call ends. Loads the call's
``turn_metrics``, runs :func:`compute_series_stats`, and writes each of
the four resulting blocks to its own JSONB column on ``call_metrics`` —
so the metrics-summary endpoint can roll up across calls without
recomputing each turn.

Idempotent on ``call_id``: re-running for the same call overwrites the
four series-stat columns; sibling columns (``computed_stats`` etc.) are
untouched.
"""
from __future__ import annotations

from uuid import UUID

from loguru import logger

from core.database.session import get_db_context
from core.models.call_metrics import CallMetrics
from core.services.call_metrics_aggregates import (
    SERIES_STAT_KEYS,
    compute_series_stats,
)


def compute_call_metrics_aggregates(call_id: str) -> None:
    """Load the row, compute the four series blocks, write to the columns."""
    call_uuid = UUID(call_id)
    with get_db_context() as db:
        row = (
            db.query(CallMetrics)
            .filter(CallMetrics.call_id == call_uuid)
            .first()
        )
        if row is None:
            logger.warning(
                "[call_metrics_aggregates] call={} has no call_metrics row; skipping",
                call_id,
            )
            return

        series_blocks = compute_series_stats(row.turn_metrics)
        for column_name, block in series_blocks.items():
            # Column names on ``CallMetrics`` intentionally match the keys
            # returned by ``compute_series_stats`` — see ``_SERIES`` — so
            # the write is a plain setattr per key with no translation.
            setattr(row, column_name, block)

        db.commit()

    logger.info(
        "[call_metrics_aggregates] call={} wrote_columns={}",
        call_id,
        [k for k in SERIES_STAT_KEYS if series_blocks.get(k) is not None],
    )
