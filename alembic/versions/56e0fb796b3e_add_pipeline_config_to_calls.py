"""add pipeline_config to calls

Adds a ``pipeline_config`` JSONB column to ``calls`` that snapshots the resolved
LLM/STT/TTS service spec (provider_name, model_name, metadata, model_meta_data,
plus is_s2s) used to serve the call. API keys are stripped before persistence.

Populated during the existing INSERT in CallLogService.create_call_log — no
extra queries. A GIN index supports filter lookups by provider/model from the
Call History and Call Metrics list endpoints.

Revision ID: 56e0fb796b3e
Revises: c9a1d3f5b8e2
Create Date: 2026-06-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '56e0fb796b3e'
down_revision = 'c9a1d3f5b8e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'calls',
        sa.Column('pipeline_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        'ix_calls_pipeline_config_gin',
        'calls',
        ['pipeline_config'],
        postgresql_using='gin',
    )


def downgrade() -> None:
    op.drop_index('ix_calls_pipeline_config_gin', table_name='calls')
    op.drop_column('calls', 'pipeline_config')
