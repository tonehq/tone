"""Add ``app_integrations.userinfo_url``.

The catalog OAuth flow used to call a provider's ``userinfo`` endpoint after
the token exchange to capture the connecting user's email. The hardcoded
catalog dict supplied that URL per provider (e.g. Google's
``/oauth2/v2/userinfo``). When the catalog moved to the DB we dropped that
field — this revision restores it so seed-driven providers retain the same
behaviour.

Revision ID: a4c8e1f7b2d6
Revises: c3e7b9d2f4a1
Create Date: 2026-06-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4c8e1f7b2d6'
down_revision = 'c3e7b9d2f4a1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'app_integrations',
        sa.Column('userinfo_url', sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('app_integrations', 'userinfo_url')
