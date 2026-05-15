"""add model provider tables

Revision ID: 0b5c01860610
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '0b5c01860610'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create model_providers_menu table
    op.create_table(
        'model_providers_menu',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('provider_type', sa.String(), nullable=False),
        sa.Column('logo_url', sa.String()),
        sa.Column('website_url', sa.String()),
        sa.Column('documentation_url', sa.String()),
        sa.Column('base_url', sa.String()),
        sa.Column('auth_type', sa.String(), nullable=False),
        sa.Column('supports_streaming', sa.Boolean(), server_default='false'),
        sa.Column('config_schema', JSONB()),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('is_system', sa.Boolean(), server_default='false'),
        sa.Column('meta_data_schema', JSONB()),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )

    # 2. Create hosting_providers table
    op.create_table(
        'hosting_providers',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('logo_url', sa.String()),
        sa.Column('website_url', sa.String()),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('is_system', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )

    # 3. Create model_menu table
    op.create_table(
        'model_menu',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('model_provider_menu_id', sa.BigInteger(), sa.ForeignKey('model_providers_menu.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('meta_data', sa.JSON()),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('service_type', sa.String()),
        sa.Column('meta_data_schema', JSONB()),
        sa.Column('auth_meta_data', sa.JSON()),
        sa.Column('endpoint_url', sa.String()),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )

    # 4. Create model_instance table
    op.create_table(
        'model_instance',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('uuid', UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('model_menu_id', sa.BigInteger(), sa.ForeignKey('model_menu.id'), nullable=False),
        sa.Column('hosting_provider_id', sa.BigInteger(), sa.ForeignKey('hosting_providers.id'), nullable=False),
        sa.Column('endpoint_url', sa.String()),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('meta_data', JSONB()),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )

    # 5. Alter api_keys table
    op.add_column('api_keys', sa.Column('hosting_provider_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_api_keys_hosting_provider_id',
        'api_keys',
        'hosting_providers',
        ['hosting_provider_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.alter_column('api_keys', 'service_provider_id', existing_type=sa.BigInteger(), nullable=True)

    # 6. Alter services table
    op.add_column('services', sa.Column('model_provider_menu_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_services_model_provider_menu_id',
        'services',
        'model_providers_menu',
        ['model_provider_menu_id'],
        ['id'],
    )
    op.alter_column('services', 'service_provider_id', existing_type=sa.BigInteger(), nullable=True)

    # 7. Alter voices table
    op.alter_column('voices', 'service_provider_id', existing_type=sa.BigInteger(), nullable=True)
    op.drop_constraint('voices_service_provider_id_voice_id_key', 'voices', type_='unique')
    op.add_column('voices', sa.Column('model_provider_menu_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_voices_model_provider_menu_id',
        'voices',
        'model_providers_menu',
        ['model_provider_menu_id'],
        ['id'],
    )
    op.add_column('voices', sa.Column('model_menu_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_voices_model_menu_id',
        'voices',
        'model_menu',
        ['model_menu_id'],
        ['id'],
    )
    op.create_unique_constraint(
        'voices_model_provider_menu_id_voice_id_key',
        'voices',
        ['model_provider_menu_id', 'voice_id'],
    )


def downgrade() -> None:
    # 7. Revert voices table
    op.drop_constraint('voices_model_provider_menu_id_voice_id_key', 'voices', type_='unique')
    op.drop_constraint('fk_voices_model_menu_id', 'voices', type_='foreignkey')
    op.drop_column('voices', 'model_menu_id')
    op.drop_constraint('fk_voices_model_provider_menu_id', 'voices', type_='foreignkey')
    op.drop_column('voices', 'model_provider_menu_id')
    op.alter_column('voices', 'service_provider_id', existing_type=sa.BigInteger(), nullable=False)
    op.create_unique_constraint('voices_service_provider_id_voice_id_key', 'voices', ['service_provider_id', 'voice_id'])

    # 6. Revert services table
    op.alter_column('services', 'service_provider_id', existing_type=sa.BigInteger(), nullable=False)
    op.drop_constraint('fk_services_model_provider_menu_id', 'services', type_='foreignkey')
    op.drop_column('services', 'model_provider_menu_id')

    # 5. Revert api_keys table
    op.alter_column('api_keys', 'service_provider_id', existing_type=sa.BigInteger(), nullable=False)
    op.drop_constraint('fk_api_keys_hosting_provider_id', 'api_keys', type_='foreignkey')
    op.drop_column('api_keys', 'hosting_provider_id')

    # 4. Drop model_instance table
    op.drop_table('model_instance')

    # 3. Drop model_menu table
    op.drop_table('model_menu')

    # 2. Drop hosting_providers table
    op.drop_table('hosting_providers')

    # 1. Drop model_providers_menu table
    op.drop_table('model_providers_menu')
