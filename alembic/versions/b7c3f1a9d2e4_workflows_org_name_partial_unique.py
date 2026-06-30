"""Make workflow org+name uniqueness ignore soft-deleted rows

The original workflows migration (d4f7a1c9e2b8) created a plain UNIQUE
constraint on (organization_id, name). That blocks reusing a workflow's name
forever, even after it is soft-deleted (deleted_at set). Swap it for a partial
unique INDEX scoped to live rows (deleted_at IS NULL) so a deleted name frees up.

This is a separate migration (rather than an in-place edit of d4f7a1c9e2b8)
because that revision is already applied in existing environments; editing its
body would never re-run there. The drop-then-create here converges every
database to the same end state.

Revision ID: b7c3f1a9d2e4
Revises: a4c8e1f7b2d6
Create Date: 2026-06-30

Note: re-pointed onto the dev head (a4c8e1f7b2d6) when dev was merged into this
branch, so the two migration heads collapse into one linear history that applies
cleanly on top of the current DB revision.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c3f1a9d2e4'
down_revision = 'a4c8e1f7b2d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('uq_workflows_org_name', 'workflows', type_='unique')
    op.create_index(
        'uq_workflows_org_name',
        'workflows',
        ['organization_id', 'name'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_workflows_org_name', table_name='workflows')
    op.create_unique_constraint(
        'uq_workflows_org_name', 'workflows', ['organization_id', 'name']
    )
