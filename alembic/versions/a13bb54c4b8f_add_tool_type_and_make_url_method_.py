"""add tool_type and make url method nullable in tools

Revision ID: a13bb54c4b8f
Revises: 7e3e62a7dbe0
Create Date: 2026-05-07 11:46:21.580225

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a13bb54c4b8f'
down_revision = '7e3e62a7dbe0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tools', sa.Column('tool_type', sa.String(), server_default='custom', nullable=False))
    op.alter_column('tools', 'url',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('tools', 'method',
               existing_type=sa.VARCHAR(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('tools', 'method',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('tools', 'url',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('tools', 'tool_type')
