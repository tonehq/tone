"""add missing tool columns: parameters, mcp_server_id, is_active

Revision ID: f1a2b3c4d5e6
Revises: da4fa42d3470
Create Date: 2026-05-23 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'da4fa42d3470'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tools', sa.Column('mcp_server_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mcp_servers.id', ondelete='CASCADE'), nullable=True))
    op.add_column('tools', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('tools', 'is_active')
    op.drop_column('tools', 'mcp_server_id')
    op.drop_column('tools', 'parameters')
