"""invites: add nullable name column

The FE captures an invitee display name on the Invite Member form and
the Invitations table renders it. The tone-test schema doesn't have
this column, so add it here on top.

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa


revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invites", sa.Column("name", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("invites", "name")
