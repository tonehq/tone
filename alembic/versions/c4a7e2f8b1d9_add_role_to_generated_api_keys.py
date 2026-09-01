"""add role to generated_api_keys

Gives each customer-facing API key its own org role (owner/admin/member/observer)
so a request made with the key is authorized as a person of that role — instead
of every key being implicitly treated as an org admin.

Backfills existing rows to "admin" (their pre-migration behavior) via the column
server-default so keys already in use keep working. The column is NOT NULL.

Ordered AFTER the readiness merge (e7b3c9a15d24): dev/staging already ran e7b3
without this column, so the role migration must be a descendant of e7b3 for those
environments to ever receive it. The add is idempotent (ADD COLUMN IF NOT EXISTS)
so it is also safe on any DB where an earlier build already created the column.

Revision ID: c4a7e2f8b1d9
Revises: e7b3c9a15d24
Create Date: 2026-09-01 00:00:00.000000
"""
from alembic import op


revision = "c4a7e2f8b1d9"
down_revision = "e7b3c9a15d24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: an earlier build (before this migration was re-parented onto
    # e7b3) may have already added the column on some databases. IF NOT EXISTS
    # makes re-running a no-op there while still adding + backfilling ("admin")
    # everywhere the column is missing. NOT NULL is satisfied by the default.
    op.execute(
        "ALTER TABLE generated_api_keys "
        "ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'admin'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE generated_api_keys DROP COLUMN IF EXISTS role")
