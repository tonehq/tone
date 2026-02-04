"""drop_service_providers_name_unique

Revision ID: 8949ec845f35
Revises: 60d17c852ecb
Create Date: 2026-01-31 12:28:57.746159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8949ec845f35'
down_revision = '60d17c852ecb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('service_providers_name_key', 'service_providers', type_='unique')


def downgrade() -> None:
    op.create_unique_constraint('service_providers_name_key', 'service_providers', ['name'])
