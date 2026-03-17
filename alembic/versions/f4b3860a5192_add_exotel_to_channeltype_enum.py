"""add exotel to channeltype enum

Revision ID: f4b3860a5192
Revises: 561cffbb81b8
Create Date: 2026-03-16 11:12:34.609844

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f4b3860a5192'
down_revision = '561cffbb81b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE channeltype ADD VALUE IF NOT EXISTS 'exotel'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # To fully reverse, you'd need to recreate the type without 'exotel'.
    pass
