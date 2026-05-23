"""add tool custom fields: url, method, auth_type, auth_config, meta_data, is_template

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-05-23 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('url', sa.String(500), nullable=True))
    op.add_column('tools', sa.Column('method', sa.String(10), nullable=True, server_default='POST'))
    op.add_column('tools', sa.Column('auth_type', sa.String(50), nullable=True, server_default='none'))
    op.add_column('tools', sa.Column('auth_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tools', sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tools', sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('tools', 'is_template')
    op.drop_column('tools', 'meta_data')
    op.drop_column('tools', 'auth_config')
    op.drop_column('tools', 'auth_type')
    op.drop_column('tools', 'method')
    op.drop_column('tools', 'url')
