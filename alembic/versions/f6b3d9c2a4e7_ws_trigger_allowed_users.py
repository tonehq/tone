"""ws_trigger_allowed_users — global allowlist for the WebSocket outbound trigger

Revision ID: f6b3d9c2a4e7
Revises: e5a2c9d4f1b8
Create Date: 2026-07-22 13:00:00.000000

A small GLOBAL (not org-scoped) allowlist table of user emails permitted to use the WebSocket
("test bridge") outbound trigger, replacing the WS_TRIGGER_ALLOWED_EMAILS env var so the list can
change without a redeploy. Read-only from the app (no CRUD API); rows are managed directly in the
DB. New empty table, so a plain CREATE TABLE / CREATE INDEX is safe (nothing to scan/lock).
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6b3d9c2a4e7"
down_revision = "e5a2c9d4f1b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Raw DDL with IF NOT EXISTS (matches the sibling migrations on this branch) so re-application
    # on a DB whose alembic history diverged is a safe no-op. Server-side defaults on id/timestamps
    # so the table can be populated with a bare ``INSERT INTO ... (email) VALUES ('x@y.com')`` —
    # the app never writes to it. gen_random_uuid() is built into Postgres 13+ (no extension).
    op.execute(
        "CREATE TABLE IF NOT EXISTS ws_trigger_allowed_users ("
        "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
        "email VARCHAR(255) NOT NULL, "
        "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        "CONSTRAINT uq_ws_trigger_allowed_users_email UNIQUE (email))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ws_trigger_allowed_users_email "
        "ON ws_trigger_allowed_users (email)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ws_trigger_allowed_users_email")
    op.execute("DROP TABLE IF EXISTS ws_trigger_allowed_users")
