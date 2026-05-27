"""Add end_call_message column to agent_configs

The form has had an "End call message" textarea for a while but the column
was missing — Pydantic silently dropped the field and the textarea reset to
empty on reload. This migration adds the missing column.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-05-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'agent_configs',
        sa.Column('end_call_message', sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('agent_configs', 'end_call_message')
