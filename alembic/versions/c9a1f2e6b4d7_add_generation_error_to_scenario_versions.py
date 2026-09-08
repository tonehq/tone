"""add generation_error to agent_llm_eval_scenario_versions

Background auto-generation of agent-LLM eval scenarios moves off the request
thread onto a Procrastinate job. A failed generation now lands the version on
``status='failed'`` with a user-safe reason stored in ``generation_error`` so
the FE can surface it. Additive-nullable + guarded (expand-only, deploy-safe):
the currently-running release ignores the column, and the ``generating`` /
``failed`` ``status`` values need no schema change (the column is free-text).

Revision ID: c9a1f2e6b4d7
Revises: 690c618340d6
Create Date: 2026-09-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "c9a1f2e6b4d7"
down_revision = "690c618340d6"
branch_labels = None
depends_on = None


_VERSIONS = "agent_llm_eval_scenario_versions"


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if _has_table(_VERSIONS) and not _has_column(_VERSIONS, "generation_error"):
        op.add_column(_VERSIONS, sa.Column("generation_error", sa.Text(), nullable=True))


def downgrade() -> None:
    if _has_table(_VERSIONS) and _has_column(_VERSIONS, "generation_error"):
        op.drop_column(_VERSIONS, "generation_error")
