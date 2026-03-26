"""change call_logs transcript column from text to jsonb

Revision ID: 2190a0cc1ca8
Revises: ea87145a1dc0
Create Date: 2026-03-19 17:46:00.928341

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '2190a0cc1ca8'
down_revision = 'ea87145a1dc0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change transcript column from TEXT to JSONB
    # First set any existing text data to NULL (since text format is incompatible with JSONB)
    op.execute("UPDATE call_logs SET transcript = NULL WHERE transcript IS NOT NULL")
    op.alter_column('call_logs', 'transcript',
               existing_type=sa.Text(),
               type_=JSONB,
               existing_nullable=True,
               postgresql_using='transcript::jsonb')


def downgrade() -> None:
    op.alter_column('call_logs', 'transcript',
               existing_type=JSONB,
               type_=sa.Text(),
               existing_nullable=True,
               postgresql_using='transcript::text')
