"""scheduled_calls per-batch concurrency columns

Revision ID: d4f1b7c8e35a
Revises: f7a3c2b9e1d8
Create Date: 2026-07-21 12:45:00.000000

Per-batch outbound concurrency moves from ``metadata`` JSONB onto typed, indexed columns —
``batch_id`` is filtered on the dispatch hot path (COUNT of a batch's in-flight calls), so it
needs a real index. Additive and backward-compatible: both columns are NULL for existing rows,
which means "no per-batch limit" (unchanged behaviour). The composite ``(batch_id, status)``
index makes the per-batch active-count an index range scan.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "d4f1b7c8e35a"
# Re-parented onto f7a3c2b9e1d8 (staging-aws's onboarding-fields migration, which also
# branched from b7d2f0a91e4c) when staging-aws was merged in, so alembic keeps a single
# linear head instead of a fork. Safe: this migration is new/undeployed, so re-pointing its
# parent affects no already-migrated environment.
down_revision = "f7a3c2b9e1d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: these columns/index may already exist on an environment where they were added
    # out-of-band (e.g. a DB whose alembic history diverged, so `alembic upgrade` couldn't run
    # and the change was applied via direct DDL). IF NOT EXISTS makes re-application a safe no-op.
    op.execute("ALTER TABLE scheduled_calls ADD COLUMN IF NOT EXISTS batch_id UUID")
    op.execute("ALTER TABLE scheduled_calls ADD COLUMN IF NOT EXISTS max_concurrency INTEGER")
    # The index is composite over (batch_id, status): batch_id is new/all-NULL, but `status` is a
    # pre-existing populated column, so the build must scan every existing row. A plain CREATE
    # INDEX would hold a write-blocking SHARE lock for that whole scan — on a large scheduled_calls
    # table that stalls dispatch. Build it CONCURRENTLY (non-blocking) instead; IF NOT EXISTS keeps
    # it idempotent (a failed concurrent build leaves an INVALID index that IF NOT EXISTS skips).
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_scheduled_calls_batch_status "
            "ON scheduled_calls (batch_id, status)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_scheduled_calls_batch_status")
    op.execute("ALTER TABLE scheduled_calls DROP COLUMN IF EXISTS max_concurrency")
    op.execute("ALTER TABLE scheduled_calls DROP COLUMN IF EXISTS batch_id")
