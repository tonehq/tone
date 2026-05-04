"""add documents and document_chunks tables (no-op duplicate)

Revision ID: a1b2c3d4e5f6
Revises: 87108f8c2496
Create Date: 2026-04-15 00:00:00.000000

NOTE: This revision is a no-op. The `documents` and `document_chunks` tables
are created by the parallel revision `356e4af099b9`. Both revisions were
authored on separate branches for the same change; this one is preserved
only to keep the branch/merge history intact (`3a0ff9a90776` merges both).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '87108f8c2496'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op: tables are created by revision 356e4af099b9 on the parallel branch.
    pass


def downgrade() -> None:
    # No-op: matching downgrade lives on revision 356e4af099b9.
    pass
