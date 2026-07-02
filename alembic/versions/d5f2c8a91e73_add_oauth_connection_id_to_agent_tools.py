"""Add ``agent_tools.oauth_connection_id``.

Allows an agent version (``agent_config``) to override the tool-level default
OAuth connection on a per-attachment basis. Resolution at runtime prefers the
link row's value and falls back to ``tools.oauth_connection_id``. Mirrors the
existing ``agent_mcp_servers.oauth_connection_id`` column.

Revision ID: d5f2c8a91e73
Revises: a4c8e1f7b2d6
Create Date: 2026-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f2c8a91e73'
down_revision = 'a4c8e1f7b2d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'agent_tools',
        sa.Column('oauth_connection_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_agent_tools_oauth_connection_id',
        'agent_tools',
        'oauth_connections',
        ['oauth_connection_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_agent_tools_oauth_connection_id', 'agent_tools', type_='foreignkey')
    op.drop_column('agent_tools', 'oauth_connection_id')
