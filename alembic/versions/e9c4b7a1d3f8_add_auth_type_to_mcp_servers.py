"""Add ``mcp_servers.auth_type``.

Mirrors ``tools.auth_type`` so MCP servers have an explicit auth-method column
instead of the runtime having to peek at ``oauth_connection_id`` + the keys
inside ``auth_config``. Downstream code (frontend picker, runtime header builder,
validation) branches cleanly on this value.

Backfill rule (matches the current inference the code was doing):

* ``oauth_connection_id`` set                 -> ``'oauth'``
* ``auth_config->>'bearer_token'`` non-null    -> ``'bearer'``
* ``auth_config->>'api_key'`` non-null         -> ``'api_key'``
* otherwise                                   -> ``'none'``

``'basic'`` isn't backfilled: today's MCP form doesn't emit basic-auth
credentials, so no existing rows are in that state. Future writes can set it
directly.

Revision ID: e9c4b7a1d3f8
Revises: 1b567efe78d3
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'e9c4b7a1d3f8'
down_revision = '1b567efe78d3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ``nullable=True`` is deliberate: the header-builder falls back to legacy
    # key-inference when ``auth_type IS NULL``, which is what keeps unmigrated
    # rows working during a rolling deploy. After this migration runs every
    # row has a concrete value (see backfill below), but leaving the column
    # nullable preserves the safety net for any future path that inserts
    # without setting it explicitly.
    op.add_column(
        'mcp_servers',
        sa.Column('auth_type', sa.String(length=50), nullable=True, server_default='none'),
    )
    # Backfill from existing shape so live rows keep authenticating the same way
    # they did before this column existed.
    op.execute(
        """
        UPDATE mcp_servers
        SET auth_type = CASE
            WHEN oauth_connection_id IS NOT NULL THEN 'oauth'
            WHEN auth_config ? 'bearer_token'
                 AND auth_config->>'bearer_token' IS NOT NULL
                 AND auth_config->>'bearer_token' <> '' THEN 'bearer'
            WHEN auth_config ? 'api_key'
                 AND auth_config->>'api_key' IS NOT NULL
                 AND auth_config->>'api_key' <> '' THEN 'api_key'
            ELSE 'none'
        END
        """
    )


def downgrade() -> None:
    op.drop_column('mcp_servers', 'auth_type')
