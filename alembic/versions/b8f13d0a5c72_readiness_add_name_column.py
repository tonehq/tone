"""add nullable `name` column to agent_readiness_snapshots + agent_readiness_events

Column-only migration. No writers, no readers — just adding the column so it
exists in the DB for a follow-up task. Lives on both readiness tables via
``ReadinessRowMixin``.

Revision ID: b8f13d0a5c72
Revises: a7e12c9f4b5d
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa


revision = "b8f13d0a5c72"
down_revision = "a7e12c9f4b5d"
branch_labels = None
depends_on = None


_TABLES = ("agent_readiness_snapshots", "agent_readiness_events")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "name")
