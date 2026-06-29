"""add workflows + workflow_versions and agent_configs.mode/workflow_id

Adds the org-level visual workflow ("pathway") feature:

* ``workflows`` — reusable container (name, status, draft/published version pointers).
* ``workflow_versions`` — graph snapshots; one draft + immutable published snapshots.
  ``graph`` is the canonical React-Flow-native JSONB graph (Vapi fields nested in
  ``node.data``); GIN-indexed.
* ``agent_configs.mode`` (prompt|workflow) + ``agent_configs.workflow_id`` FK — the
  per-agent assignment of a published workflow.

Purely additive with safe defaults: existing agents keep running in ``prompt`` mode.

Revision ID: d4f7a1c9e2b8
Revises: a4e21c9b3d7f
Create Date: 2026-06-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'd4f7a1c9e2b8'
down_revision = 'a4e21c9b3d7f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- workflows (container) ---
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='draft'),
        sa.Column('published_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('draft_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('latest_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
    )
    op.create_index('ix_workflows_organization_id', 'workflows', ['organization_id'])
    # Names are unique per org among LIVE rows only — a partial unique index lets a
    # soft-deleted name be reused (a plain UNIQUE constraint would block reuse forever).
    op.create_index(
        'uq_workflows_org_name', 'workflows', ['organization_id', 'name'],
        unique=True, postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # --- workflow_versions (graph snapshots + draft) ---
    op.create_table(
        'workflow_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_draft', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            'graph',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'{"schemaVersion": 1, "nodes": [], "edges": [], "globalPrompt": ""}\'::jsonb'),
        ),
        sa.Column('start_node_name', sa.String(length=120), nullable=True),
        sa.Column('graph_checksum', sa.String(length=64), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.UniqueConstraint('workflow_id', 'version', name='uq_workflow_versions_workflow_version'),
    )
    op.create_index('ix_workflow_versions_organization_id', 'workflow_versions', ['organization_id'])
    op.create_index('ix_workflow_versions_workflow_id', 'workflow_versions', ['workflow_id'])
    op.create_index(
        'ix_workflow_versions_graph_gin', 'workflow_versions', ['graph'], postgresql_using='gin'
    )

    # --- circular FKs: workflows.{published,draft}_version_id -> workflow_versions.id ---
    op.create_foreign_key(
        'fk_workflows_published_version', 'workflows', 'workflow_versions',
        ['published_version_id'], ['id'], ondelete='SET NULL', use_alter=True,
    )
    op.create_foreign_key(
        'fk_workflows_draft_version', 'workflows', 'workflow_versions',
        ['draft_version_id'], ['id'], ondelete='SET NULL', use_alter=True,
    )

    # --- agent_configs: the per-agent assignment lives here ---
    op.add_column(
        'agent_configs',
        sa.Column('mode', sa.String(length=16), nullable=False, server_default='prompt'),
    )
    op.add_column(
        'agent_configs',
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_agent_configs_workflow', 'agent_configs', 'workflows',
        ['workflow_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_agent_configs_workflow', 'agent_configs', type_='foreignkey')
    op.drop_column('agent_configs', 'workflow_id')
    op.drop_column('agent_configs', 'mode')

    op.drop_constraint('fk_workflows_draft_version', 'workflows', type_='foreignkey')
    op.drop_constraint('fk_workflows_published_version', 'workflows', type_='foreignkey')

    op.drop_index('ix_workflow_versions_graph_gin', table_name='workflow_versions')
    op.drop_index('ix_workflow_versions_workflow_id', table_name='workflow_versions')
    op.drop_index('ix_workflow_versions_organization_id', table_name='workflow_versions')
    op.drop_table('workflow_versions')

    op.drop_index('ix_workflows_organization_id', table_name='workflows')
    op.drop_table('workflows')
