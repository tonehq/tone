"""add to_number snapshot column to calls

Stores the dialed number as an immutable string on the ``calls`` row so history
survives PhoneNumber reassignment/deletion (the ``to_phone_number_id`` FK uses
``ondelete=SET NULL``, which retroactively nulled the join-derived to_number in
call history whenever an agent's phone number was removed or reassigned).

Backfills existing rows from ``phone_numbers`` while the FK is still intact,
so no historical to_number is lost when subsequent reassignments happen.

Revision ID: d9e4b8c1a2f3
Revises: c4e1f7a9b3d2
Create Date: 2026-07-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd9e4b8c1a2f3'
down_revision = 'c4e1f7a9b3d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('calls', sa.Column('to_number', sa.String(length=50), nullable=True))

    # Backfill from phone_numbers via the still-intact FK. Runs once, guarded by
    # IS NULL so re-runs (should the migration be reapplied on a partially-migrated
    # database) don't overwrite fresher snapshots written by application code.
    op.execute(
        """
        UPDATE calls
        SET to_number = phone_numbers.number
        FROM phone_numbers
        WHERE calls.to_phone_number_id = phone_numbers.id
          AND calls.to_number IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column('calls', 'to_number')
