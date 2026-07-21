"""add onboarding fields to organizations

Adds industry, use_case, onboarding_completed to organizations. New signups
default to onboarding_completed=false so they get routed through the
onboarding wizard; existing rows are backfilled to true so current users
aren't force-routed through onboarding on next login.

Revision ID: f7a3c2b9e1d8
Revises: b7d2f0a91e4c
Create Date: 2026-07-21 00:00:00.000000

"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "f7a3c2b9e1d8"
down_revision = "b7d2f0a91e4c"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_column("organizations", "industry"):
        op.add_column("organizations", sa.Column("industry", sa.String(length=100), nullable=True))
    if not _has_column("organizations", "use_case"):
        op.add_column("organizations", sa.Column("use_case", sa.String(length=100), nullable=True))
    if not _has_column("organizations", "onboarding_completed"):
        op.add_column(
            "organizations",
            sa.Column(
                "onboarding_completed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
        # Backfill existing orgs as already onboarded so current users
        # aren't force-routed through the onboarding wizard on next login.
        op.execute("UPDATE organizations SET onboarding_completed = true")


def downgrade() -> None:
    for col in ("onboarding_completed", "use_case", "industry"):
        if _has_column("organizations", col):
            op.drop_column("organizations", col)
