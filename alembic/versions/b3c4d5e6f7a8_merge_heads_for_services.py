"""merge a1b2c3d4f5e6 and a2b3c4d5e6f7 heads

The migration tree branched: ``a1b2c3d4f5e6`` (create documents table) and
``a2b3c4d5e6f7`` (change tool description column). The DB already contains
both branches' schema changes, but the alembic pointer was orphaned at a
non-existent revision. This empty merge migration unifies the file heads
so subsequent migrations have a single ancestor.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4f5e6, a2b3c4d5e6f7
Create Date: 2026-05-23

"""

revision = "b3c4d5e6f7a8"
down_revision = ("a1b2c3d4f5e6", "a2b3c4d5e6f7")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
