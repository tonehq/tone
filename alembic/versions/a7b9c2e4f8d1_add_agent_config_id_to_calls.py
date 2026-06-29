"""add agent_config_id to calls

Records the exact agent_configs version that served each call. Nullable so
backfill isn't required for historical rows; FK uses SET NULL so deleting a
config version doesn't fail with a referential-integrity error and old call
rows keep pointing at the (now-null) version.

Revision ID: a7b9c2e4f8d1
Revises: f1a2b3c4d5e6
Create Date: 2026-06-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b9c2e4f8d1'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'calls',
        sa.Column('agent_config_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_calls_agent_config_id',
        'calls',
        'agent_configs',
        ['agent_config_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_calls_agent_config_id',
        'calls',
        ['agent_config_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_calls_agent_config_id', table_name='calls')
    op.drop_constraint('fk_calls_agent_config_id', 'calls', type_='foreignkey')
    op.drop_column('calls', 'agent_config_id')
