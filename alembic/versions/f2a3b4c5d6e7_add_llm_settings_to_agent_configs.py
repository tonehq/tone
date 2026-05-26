"""Add llm_settings JSONB column to agent_configs

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agent_configs', sa.Column('llm_settings', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('agent_configs', 'llm_settings')
