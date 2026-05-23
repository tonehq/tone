"""add missing mcp_servers columns: transport_type, auth_config, meta_data, is_active

Revision ID: da4fa42d3470
Revises: e2f3a4b5c6d7
Create Date: 2026-05-23 13:02:13.647600

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'da4fa42d3470'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('mcp_servers', sa.Column('transport_type', sa.String(length=50), nullable=False, server_default='streamable_http'))
    op.add_column('mcp_servers', sa.Column('auth_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('mcp_servers', sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('mcp_servers', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade() -> None:
    op.drop_column('mcp_servers', 'is_active')
    op.drop_column('mcp_servers', 'meta_data')
    op.drop_column('mcp_servers', 'auth_config')
    op.drop_column('mcp_servers', 'transport_type')
