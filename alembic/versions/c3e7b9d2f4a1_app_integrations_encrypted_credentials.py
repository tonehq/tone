"""Replace ``client_id_env_key`` / ``client_secret_env_key`` with a single
encrypted JSONB column on ``app_integrations``.

The two env-key columns required admins to know an env var name and to set
that var separately in ``.env`` or Infisical. The new ``encrypted_credentials``
column holds the actual values directly (Fernet-encrypted via
``core.utils.encryption.encrypt_json``), making the create-integration flow
fully UI self-serve. Matches the pattern already used by
``oauth_connections.encrypted_credentials``.

Revision ID: c3e7b9d2f4a1
Revises: f5a8c2e6b3d9
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c3e7b9d2f4a1'
down_revision = 'f5a8c2e6b3d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'app_integrations',
        sa.Column(
            'encrypted_credentials',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.drop_column('app_integrations', 'client_id_env_key')
    op.drop_column('app_integrations', 'client_secret_env_key')


def downgrade() -> None:
    op.add_column(
        'app_integrations',
        sa.Column('client_secret_env_key', sa.String(length=120), nullable=True),
    )
    op.add_column(
        'app_integrations',
        sa.Column('client_id_env_key', sa.String(length=120), nullable=True),
    )
    op.drop_column('app_integrations', 'encrypted_credentials')
