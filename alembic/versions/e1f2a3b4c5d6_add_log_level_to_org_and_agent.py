"""add log_level to organizations and agents

Per-org and per-agent log level for calls. Both are nullable — NULL means
"inherit": an agent falls back to its organization's level, then to the env
``LOG_LEVEL`` baseline. The most specific non-NULL value wins. Resolution lives
in core/services/log_level_resolver.py; the call-pod parent resolves the level
and injects it into the call subprocess, so changing a row takes effect on the
next call with no build or restart.

Revision ID: e1f2a3b4c5d6
Revises: a8a6d8cdfae3
Create Date: 2026-07-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'a8a6d8cdfae3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('log_level', sa.String(length=20), nullable=True))
    op.add_column('agents', sa.Column('log_level', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'log_level')
    op.drop_column('organizations', 'log_level')
