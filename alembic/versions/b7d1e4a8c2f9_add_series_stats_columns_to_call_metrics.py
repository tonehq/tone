"""Add per-series stat columns to call_metrics

Materializes the four per-call series-stat blocks (LLM/STT/TTS TTFB and
end-to-end latency) as dedicated JSONB columns on ``call_metrics``.
Populated at post-call time by ``compute_call_metrics_aggregates``; the
metrics-summary endpoint reads them per-call and rolls up across calls
without walking ``turn_metrics`` on every request.

Nullable and no default — existing rows stay untouched; the analytics
reader falls back to inline compute from ``turn_metrics`` until the
per-call job populates them.

Revision ID: b7d1e4a8c2f9
Revises: a9c1e5b3d7f2
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = 'b7d1e4a8c2f9'
down_revision = 'a9c1e5b3d7f2'
branch_labels = None
depends_on = None


_COLUMNS = (
    'llm_series_stats',
    'stt_series_stats',
    'tts_series_stats',
    'end_to_end_series_stats',
)


def upgrade() -> None:
    for name in _COLUMNS:
        op.add_column('call_metrics', sa.Column(name, JSONB(), nullable=True))


def downgrade() -> None:
    for name in _COLUMNS:
        op.drop_column('call_metrics', name)
