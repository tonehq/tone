"""add trace_id to calls

Stores the per-call log trace_id ({short_uuid}-{agent_id}-{call_id}) on the call
row so a call can be correlated to its server logs.

Revision ID: c8d2e4f6a1b9
Revises: b7e1c0a2d9f3
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8d2e4f6a1b9'
down_revision = 'b7e1c0a2d9f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('calls', sa.Column('trace_id', sa.String(120), nullable=True))
    op.create_index(op.f('ix_calls_trace_id'), 'calls', ['trace_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_calls_trace_id'), table_name='calls')
    op.drop_column('calls', 'trace_id')
