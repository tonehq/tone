"""add webhook_result to calls

Additive JSONB column holding a compact, PII/secret-safe summary of the
profile-variable webhook data source for a call (status flags + which
variables resolved/applied). NULL for every existing row and whenever no
webhook ran.

Revision ID: c7f3a1b9d2e5
Revises: b2e8f4a1c9d5
Create Date: 2026-09-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "c7f3a1b9d2e5"
down_revision = "b2e8f4a1c9d5"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if _has_table("calls") and not _has_column("calls", "webhook_result"):
        op.add_column(
            "calls",
            sa.Column(
                "webhook_result",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("calls", "webhook_result"):
        op.drop_column("calls", "webhook_result")
