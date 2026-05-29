"""add display_name to model_languages

Revision ID: 426f072133d4
Revises: a3b4c5d6e7f8
Create Date: 2026-05-28 11:59:08.850417

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '426f072133d4'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('model_languages', sa.Column('display_name', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('model_languages', 'display_name')
