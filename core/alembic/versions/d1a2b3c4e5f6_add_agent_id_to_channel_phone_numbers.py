"""Add agent_id to channel_phone_numbers

Revision ID: d1a2b3c4e5f6
Revises: c7d8e9f0a1b2
Create Date: 2026-02-27 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1a2b3c4e5f6'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'channel_phone_numbers',
        sa.Column('agent_id', sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        'channel_phone_numbers_agent_id_fkey',
        'channel_phone_numbers',
        'agents',
        ['agent_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'channel_phone_numbers_agent_id_fkey',
        'channel_phone_numbers',
        type_='foreignkey',
    )
    op.drop_column('channel_phone_numbers', 'agent_id')
