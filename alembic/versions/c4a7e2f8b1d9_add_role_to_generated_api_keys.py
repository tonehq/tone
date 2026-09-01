"""add role to generated_api_keys

Gives each customer-facing API key its own org role (owner/admin/member/observer)
so a request made with the key is authorized as a person of that role — instead
of every key being implicitly treated as an org admin.

Backfills existing rows to "admin" (their pre-migration behavior) via the column
server-default so keys already in use keep working. The column is NOT NULL.

Revision ID: c4a7e2f8b1d9
Revises: f5b1c2a3e4d6
Create Date: 2026-09-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c4a7e2f8b1d9"
down_revision = "f5b1c2a3e4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default="admin" backfills every existing row in a single DDL pass,
    # preserving the old "API keys act as admin" behavior. New rows get their
    # role explicitly from the service (capped at the creator's role).
    op.add_column(
        "generated_api_keys",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="admin",
        ),
    )


def downgrade() -> None:
    op.drop_column("generated_api_keys", "role")
