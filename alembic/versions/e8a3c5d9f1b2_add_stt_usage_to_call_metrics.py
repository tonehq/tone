"""Add stt_usage to call_metrics

Captures per-call STT audio-duration metering (milliseconds of audio sent
to the STT provider) for billing. Pipecat does not emit STT usage natively,
so Tone derives it via STTAudioUsageTap and stores the per-utterance
breakdown here as ``[{processor, model, audio_ms}, ...]``.

Revision ID: e8a3c5d9f1b2
Revises: d4f7a1c9e2b8
Create Date: 2026-06-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'e8a3c5d9f1b2'
down_revision = 'd4f7a1c9e2b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('call_metrics', sa.Column('stt_usage', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('call_metrics', 'stt_usage')
