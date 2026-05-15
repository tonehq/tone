"""remove service_provider_id from accounts

Revision ID: 17160d116550
Revises: e5f6a7b8c9d0
Create Date: 2026-05-15 09:45:42.834855

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17160d116550'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('services_service_provider_id_fkey', 'accounts', type_='foreignkey')
    op.drop_column('accounts', 'service_provider_id')
 

def downgrade() -> None:
    op.add_column('accounts', sa.Column('service_provider_id', sa.BIGINT(), autoincrement=False, nullable=True))
    op.create_foreign_key('services_service_provider_id_fkey', 'accounts', 'service_providers', ['service_provider_id'], ['id'], ondelete='CASCADE')
