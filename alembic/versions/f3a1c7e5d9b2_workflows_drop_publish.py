"""Drop the workflow publish/version machinery

Workflows are now agent-version-scoped copies with a single working graph — the
agent version's own publish is the only "go live" gate, so a workflow-level
publish layer is redundant. This removes it:

- Deletes the immutable published-snapshot rows (workflow_versions.is_draft = false).
- Drops workflows.published_version_id / status / latest_version.
- Drops workflow_versions.is_draft / published_at.

The single working graph stays on the workflow_versions row pointed at by
workflows.draft_version_id.

Revision ID: f3a1c7e5d9b2
Revises: e2d8b4a7c9f1
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f3a1c7e5d9b2'
down_revision = 'e2d8b4a7c9f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the published-version pointer first so deleting the snapshot rows
    # below can't trip the FK, then remove the now-orphan published snapshots.
    op.drop_column('workflows', 'published_version_id')
    op.execute("DELETE FROM workflow_versions WHERE is_draft = false")

    op.drop_column('workflows', 'status')
    op.drop_column('workflows', 'latest_version')
    op.drop_column('workflow_versions', 'is_draft')
    op.drop_column('workflow_versions', 'published_at')


def downgrade() -> None:
    op.add_column(
        'workflow_versions',
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'workflow_versions',
        sa.Column('is_draft', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    op.add_column(
        'workflows',
        sa.Column('latest_version', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'workflows',
        sa.Column('status', sa.String(length=16), nullable=False, server_default='draft'),
    )
    op.add_column(
        'workflows',
        sa.Column('published_version_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'workflows_published_version_id_fkey',
        'workflows',
        'workflow_versions',
        ['published_version_id'],
        ['id'],
        ondelete='SET NULL',
        use_alter=True,
    )
