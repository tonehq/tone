"""change agent_config service FKs from service_providers to services, drop models.api_key_id

Revision ID: c27f5a6dbd95
Revises: 3a0ff9a90776
Create Date: 2026-04-29 15:54:29.876841

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c27f5a6dbd95'
down_revision = '3a0ff9a90776'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change agent_configs FKs from service_providers to services
    op.drop_constraint('agent_configs_llm_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_tts_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_stt_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.create_foreign_key('agent_configs_llm_service_id_fkey', 'agent_configs', 'services', ['llm_service_id'], ['id'])
    op.create_foreign_key('agent_configs_tts_service_id_fkey', 'agent_configs', 'services', ['tts_service_id'], ['id'])
    op.create_foreign_key('agent_configs_stt_service_id_fkey', 'agent_configs', 'services', ['stt_service_id'], ['id'])

    # Drop api_key_id from models (no longer needed — API keys are on services)
    op.drop_constraint('models_api_key_id_fkey', 'models', type_='foreignkey')
    op.drop_column('models', 'api_key_id')


def downgrade() -> None:
    # Restore models.api_key_id
    op.add_column('models', sa.Column('api_key_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('models_api_key_id_fkey', 'models', 'api_keys', ['api_key_id'], ['id'], ondelete='SET NULL')

    # Restore agent_configs FKs to service_providers
    op.drop_constraint('agent_configs_llm_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_tts_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.drop_constraint('agent_configs_stt_service_id_fkey', 'agent_configs', type_='foreignkey')
    op.create_foreign_key('agent_configs_llm_service_id_fkey', 'agent_configs', 'service_providers', ['llm_service_id'], ['id'])
    op.create_foreign_key('agent_configs_tts_service_id_fkey', 'agent_configs', 'service_providers', ['tts_service_id'], ['id'])
    op.create_foreign_key('agent_configs_stt_service_id_fkey', 'agent_configs', 'service_providers', ['stt_service_id'], ['id'])
