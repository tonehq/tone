"""add overlapped_calls to calls

Adds a JSONB column ``overlapped_calls`` to ``calls`` that stores the ids of
other calls whose active time window overlapped with this call on the same
infrastructure (pod today, node/other scopes later). Populated by the
``detect_call_overlaps`` background job that runs when a call ends.

Also merges two pre-existing heads (`1b30e7c3d05f`, `b8f2c1d5e9a7`) that were
created on parallel branches.

Revision ID: a1b2c3d4e5f6
Revises: 1b30e7c3d05f, b8f2c1d5e9a7
Create Date: 2026-07-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'a1b2c3d4e5f6'
down_revision = ('1b30e7c3d05f', 'b8f2c1d5e9a7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'calls',
        sa.Column(
            'overlapped_calls',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('calls', 'overlapped_calls')
