"""drop ws_trigger_allowed_users — WS trigger now gated by the super_admin role

Revision ID: a7c4e1f92b06
Revises: f6b3d9c2a4e7
Create Date: 2026-07-22 15:00:00.000000

Access to the WebSocket ("test bridge") outbound trigger moved from a global email allowlist table
to a role gate: only users whose ``members.role == 'super_admin'`` may use it (assigned via SQL,
no UI/API) — see OutboundCallService.is_ws_trigger_allowed. The allowlist table is no longer read by
the app, so drop it. No data migration: assign the role via SQL after deploy.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c4e1f92b06"
down_revision = "f6b3d9c2a4e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS so re-application on a DB whose alembic history diverged is a safe no-op.
    op.execute("DROP INDEX IF EXISTS ix_ws_trigger_allowed_users_email")
    op.execute("DROP TABLE IF EXISTS ws_trigger_allowed_users")


def downgrade() -> None:
    # Recreate the table exactly as f6b3d9c2a4e7 created it (empty — no data to restore).
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
