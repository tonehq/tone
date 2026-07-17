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
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'e1f2a3b4c5d6'
down_revision = 'a8a6d8cdfae3'
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    # Idempotent: on some environments these columns were added out-of-band
    # (the DB has them but this revision was never stamped), so a plain
    # add_column raises DuplicateColumn and blocks every later migration.
    for table in ("organizations", "agents"):
        if _has_column(table, "log_level"):
            logger.info("[e1f2a3b4c5d6] %s.log_level already exists — skipping add", table)
            continue
        op.add_column(table, sa.Column("log_level", sa.String(length=20), nullable=True))


def downgrade() -> None:
    for table in ("agents", "organizations"):
        if _has_column(table, "log_level"):
            op.drop_column(table, "log_level")
