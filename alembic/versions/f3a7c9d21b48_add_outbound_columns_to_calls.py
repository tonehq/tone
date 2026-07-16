"""relax calls.started_at/channel_id for outbound + merge branch heads

Outbound support needs ``calls.started_at`` and ``calls.channel_id`` to be nullable:
a ``calls`` row is only written when the media stream connects, and until then an
outbound attempt has neither an answer time nor (necessarily) a resolved channel.
The scheduled-call lifecycle itself lives in its own ``scheduled_calls`` table
(created in the next revision, ``b7d4e9c2f1a8``), so no lifecycle columns are added
to ``calls`` here.

This revision also merges the two pre-existing heads on this branch
(``1b30e7c3d05f`` and ``b8f2c1d5e9a7``) back into a single head.

Revision ID: f3a7c9d21b48
Revises: 1b30e7c3d05f, b8f2c1d5e9a7
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f3a7c9d21b48'
down_revision = ('1b30e7c3d05f', 'b8f2c1d5e9a7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Relax NOT NULL so pre-connect outbound attempts don't force a value that only
    # exists once the call actually connects.
    op.alter_column('calls', 'started_at', existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column('calls', 'channel_id', existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    # Restore NOT NULL. Guarded backfills keep the re-tightening from failing on any
    # rows that legitimately left these NULL.
    op.execute("DELETE FROM calls WHERE channel_id IS NULL OR started_at IS NULL")
    op.alter_column('calls', 'channel_id', existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column('calls', 'started_at', existing_type=sa.DateTime(timezone=True), nullable=False)
