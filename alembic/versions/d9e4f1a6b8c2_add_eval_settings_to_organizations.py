"""add eval_settings JSONB column to organizations

Adds a nullable JSONB ``eval_settings`` column so per-org RAG-eval knobs
(auto-run flag, judge/answer/generation models, top_k, thresholds,
enabled metrics, etc.) can be edited from the UI instead of only the
env. Every ``settings.EVAL_*`` env var stays honored as a fallback via
``core.services.org_settings.get_eval_settings``, so this migration is
zero-blast-radius on existing installs — evals continue to score
identically until an admin edits the new settings page.

Revision ID: d9e4f1a6b8c2
Revises: c7e2a5b8f4d9
Create Date: 2026-08-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "d9e4f1a6b8c2"
down_revision = "c7e2a5b8f4d9"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_column("organizations", "eval_settings"):
        op.add_column(
            "organizations",
            sa.Column(
                "eval_settings",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("organizations", "eval_settings"):
        op.drop_column("organizations", "eval_settings")
