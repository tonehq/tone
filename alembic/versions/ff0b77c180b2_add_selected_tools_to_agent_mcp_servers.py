"""add selected_tools to agent_mcp_servers

Revision ID: ff0b77c180b2
Revises: ff9ab48e9816
Create Date: 2026-05-12 13:40:40.173236

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ff0b77c180b2'
down_revision = 'ff9ab48e9816'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('agent_mcp_servers', sa.Column('selected_tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('agent_mcp_servers', 'selected_tools')
