"""add account_id and host_region to model_instances

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = '2f0435e7a13d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account_id column (FK to accounts.id, CASCADE on delete)
    op.add_column('model_instance', sa.Column('account_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_model_instance_account_id',
        'model_instance', 'accounts',
        ['account_id'], ['id'],
        ondelete='CASCADE',
    )

    # Add host_region column
    op.add_column('model_instance', sa.Column('host_region', sa.String(), nullable=True))

    # Make hosting_provider_id nullable (was NOT NULL before)
    op.alter_column('model_instance', 'hosting_provider_id',
                     existing_type=sa.BigInteger(),
                     nullable=True)

    # Create composite index for efficient lookups
    op.create_index('ix_model_instance_account_model', 'model_instance', ['account_id', 'model_menu_id'])

    # Data migration: link existing model_instances to matching accounts
    op.execute("""
        UPDATE model_instance
        SET account_id = a.id
        FROM accounts a
        JOIN model_menu mm ON mm.model_provider_menu_id = a.model_provider_menu_id
        WHERE model_instance.model_menu_id = mm.id
          AND model_instance.account_id IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_model_instance_account_model', table_name='model_instance')
    op.drop_constraint('fk_model_instance_account_id', 'model_instance', type_='foreignkey')
    op.drop_column('model_instance', 'host_region')
    op.drop_column('model_instance', 'account_id')
    op.alter_column('model_instance', 'hosting_provider_id',
                     existing_type=sa.BigInteger(),
                     nullable=False)
