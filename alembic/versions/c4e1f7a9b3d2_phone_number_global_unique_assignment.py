"""phone number global unique assignment

Enforce that a phone number can be ASSIGNED to only one agent globally (across all
orgs). Inbound calls are resolved by number alone, so the same number assigned in two
orgs routed non-deterministically. Adds a partial unique index on ``number`` where
``agent_id IS NOT NULL``; unassigned numbers may still coexist per-org.

Self-heals any pre-existing duplicate assignments by keeping the earliest-created
assigned row per number (matching the resolver's ``created_at ASC`` tie-break) and
unassigning the rest, so the unique index builds cleanly on dirty environments.

Revision ID: c4e1f7a9b3d2
Revises: 733a3ca12fdb
Create Date: 2026-07-07 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e1f7a9b3d2'
down_revision = '733a3ca12fdb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Resolve existing duplicate assignments deterministically: keep the earliest
    #    assigned row per number, unassign the newer ones (they were unreachable
    #    anyway — routing already picked only one). Keeps routing stable post-migrate.
    op.execute(
        """
        UPDATE phone_numbers p
        SET agent_id = NULL
        WHERE p.agent_id IS NOT NULL
          AND p.id <> (
            SELECT p2.id
            FROM phone_numbers p2
            WHERE p2.number = p.number AND p2.agent_id IS NOT NULL
            ORDER BY p2.created_at ASC, p2.id ASC
            LIMIT 1
          )
        """
    )

    # 2) Enforce global uniqueness of an ASSIGNED number.
    op.create_index(
        "uq_phone_numbers_assigned_number",
        "phone_numbers",
        ["number"],
        unique=True,
        postgresql_where=sa.text("agent_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_phone_numbers_assigned_number", table_name="phone_numbers")
