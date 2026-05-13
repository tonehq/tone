"""add mcp_server_id to tools

Revision ID: b2c3d4e5f6a7
Revises: ff0b77c180b2
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'ff0b77c180b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('mcp_server_id', sa.BigInteger(), nullable=True))
    op.create_index('ix_tools_mcp_server_id', 'tools', ['mcp_server_id'])
    op.create_foreign_key(
        'fk_tools_mcp_server_id',
        'tools',
        'mcp_servers',
        ['mcp_server_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_tools_mcp_server_id', 'tools', type_='foreignkey')
    op.drop_index('ix_tools_mcp_server_id', table_name='tools')
    op.drop_column('tools', 'mcp_server_id')
