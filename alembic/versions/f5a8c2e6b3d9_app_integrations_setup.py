"""App integrations: catalog table + FK columns on tools / mcp_servers / oauth_connections.

Consolidates five iterative migrations from the original feature work:

    c7d9e1f3a5b8  add app_integrations table
    e9f4b2d6c8a7  link resources to app_integration_id + add ``type``
    b3d5e8f1a4c9  make app_integrations org-scoped
    d8f1c6a3b5e2  drop ``app_integrations.type``
    e2a5c9b4d7f1  drop ``app_integrations.supports_dcr``

Net effect:

* New ``app_integrations`` table — org-scoped, no ``type`` column, no
  ``supports_dcr`` column. Unique slug **per org**.
* New nullable ``app_integration_id`` FK on ``tools``, ``mcp_servers``, and
  ``oauth_connections``, each with ``ON DELETE SET NULL``.

Environments that already ran the five iterative revisions need a one-time
swap in their ``alembic_version`` table — see the deploy notes accompanying
this commit; nothing in this file performs that swap.

Revision ID: f5a8c2e6b3d9
Revises: a7b9c2e4f8d1
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f5a8c2e6b3d9'
down_revision = 'a7b9c2e4f8d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── app_integrations ──────────────────────────────────────────────
    op.create_table(
        'app_integrations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=60), nullable=True),
        sa.Column('icon_url', sa.String(length=500), nullable=True),
        sa.Column('auth_type', sa.String(length=20), nullable=False),
        sa.Column('auth_url', sa.String(length=500), nullable=True),
        sa.Column('token_url', sa.String(length=500), nullable=True),
        sa.Column('scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('extra_auth_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('client_id_env_key', sa.String(length=120), nullable=True),
        sa.Column('client_secret_env_key', sa.String(length=120), nullable=True),
        sa.Column('pkce_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'organization_id', 'slug', name='uq_app_integrations_org_slug',
        ),
    )
    op.create_index(
        'ix_app_integrations_slug',
        'app_integrations',
        ['slug'],
        unique=False,
    )
    op.create_index(
        'ix_app_integrations_category',
        'app_integrations',
        ['category'],
        unique=False,
    )
    op.create_index(
        'ix_app_integrations_organization_id',
        'app_integrations',
        ['organization_id'],
        unique=False,
    )
    op.create_index(
        'ix_app_integrations_enabled',
        'app_integrations',
        ['is_enabled'],
        unique=False,
        postgresql_where=sa.text('is_enabled = true'),
    )

    # ── tools.app_integration_id ──────────────────────────────────────
    op.add_column(
        'tools',
        sa.Column('app_integration_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_tools_app_integration_id',
        'tools',
        'app_integrations',
        ['app_integration_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_tools_app_integration_id',
        'tools',
        ['app_integration_id'],
        unique=False,
    )

    # ── mcp_servers.app_integration_id ────────────────────────────────
    op.add_column(
        'mcp_servers',
        sa.Column('app_integration_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_mcp_servers_app_integration_id',
        'mcp_servers',
        'app_integrations',
        ['app_integration_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_mcp_servers_app_integration_id',
        'mcp_servers',
        ['app_integration_id'],
        unique=False,
    )

    # ── oauth_connections.app_integration_id ──────────────────────────
    op.add_column(
        'oauth_connections',
        sa.Column('app_integration_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_oauth_connections_app_integration_id',
        'oauth_connections',
        'app_integrations',
        ['app_integration_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_oauth_connections_app_integration_id',
        'oauth_connections',
        ['app_integration_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_oauth_connections_app_integration_id', table_name='oauth_connections')
    op.drop_constraint(
        'fk_oauth_connections_app_integration_id',
        'oauth_connections',
        type_='foreignkey',
    )
    op.drop_column('oauth_connections', 'app_integration_id')

    op.drop_index('ix_mcp_servers_app_integration_id', table_name='mcp_servers')
    op.drop_constraint(
        'fk_mcp_servers_app_integration_id',
        'mcp_servers',
        type_='foreignkey',
    )
    op.drop_column('mcp_servers', 'app_integration_id')

    op.drop_index('ix_tools_app_integration_id', table_name='tools')
    op.drop_constraint(
        'fk_tools_app_integration_id',
        'tools',
        type_='foreignkey',
    )
    op.drop_column('tools', 'app_integration_id')

    op.drop_index('ix_app_integrations_enabled', table_name='app_integrations')
    op.drop_index('ix_app_integrations_organization_id', table_name='app_integrations')
    op.drop_index('ix_app_integrations_category', table_name='app_integrations')
    op.drop_index('ix_app_integrations_slug', table_name='app_integrations')
    op.drop_table('app_integrations')
