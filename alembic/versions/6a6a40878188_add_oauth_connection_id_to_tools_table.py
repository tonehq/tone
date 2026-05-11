"""add oauth_connection_id to tools table

Revision ID: 6a6a40878188
Revises: f7a8b9c0d1e2
Create Date: 2026-05-11 12:49:00.917765

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a6a40878188'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('oauth_connection_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_tools_oauth_connection_id'), 'tools', ['oauth_connection_id'], unique=False)
    op.create_foreign_key('fk_tools_oauth_connection_id', 'tools', 'oauth_connections', ['oauth_connection_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_tools_oauth_connection_id', 'tools', type_='foreignkey')
    op.drop_index(op.f('ix_tools_oauth_connection_id'), table_name='tools')
    op.drop_column('tools', 'oauth_connection_id')
