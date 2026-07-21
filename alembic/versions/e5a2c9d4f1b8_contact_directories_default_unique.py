"""one live default "Global" contact directory per org

Revision ID: e5a2c9d4f1b8
Revises: d4f1b7c8e35a
Create Date: 2026-07-21 13:30:00.000000

``get_or_create_default_directory`` resolves-or-provisions the org's shared "Global" directory.
Two concurrent misses could both insert, leaving duplicate "Global" rows. This adds a partial,
case-insensitive unique index so at most one LIVE (non-deleted) "Global" exists per org; the
service now catches the resulting IntegrityError and returns the winner's row.

Built with CREATE UNIQUE INDEX CONCURRENTLY (non-blocking) + IF NOT EXISTS (idempotent — a
failed concurrent build leaves an INVALID index that IF NOT EXISTS then skips). The predicate
matches the service lookup exactly (``lower(name) = 'global' AND deleted_at IS NULL``).

NOTE: if an environment already contains duplicate live "Global" directories (from the race
this closes), the unique build will fail — dedupe to the oldest row first, then re-run.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "e5a2c9d4f1b8"
down_revision = "d4f1b7c8e35a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
            "uq_contact_directories_org_default_global "
            "ON contact_directories (organization_id) "
            "WHERE lower(name) = 'global' AND deleted_at IS NULL"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_contact_directories_org_default_global")
