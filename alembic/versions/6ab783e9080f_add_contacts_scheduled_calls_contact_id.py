"""add contact directories + schemas + syncs + contacts + agent_contacts + scheduled_calls.contact_id

Revision ID: 6ab783e9080f
Revises: c5d9a4e7b2f1
Create Date: 2026-07-17 20:47:45.117376

The single, clean Contact **Directories** migration. Creates the whole module:
``contact_schemas`` (org-level reusable) + ``schema_fields`` (replaces the dropped
``contact_field_definitions``), ``contact_directories``, ``datasources``,
``contact_syncs``, ``contacts`` (directory-scoped, ``sync_id``, no ``source_upload_id``),
``agent_contacts``, and adds ``scheduled_calls.contact_id``. Additive-only: unrelated
pre-existing model/DB drift is intentionally left out so this revision touches only the
contacts/directories surface.

FK creation order is dependency-safe: referenced tables are created before referencing
ones (schemas → schema_fields → directories → datasources → contact_syncs → contacts →
agent_contacts).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6ab783e9080f'
down_revision = 'c5d9a4e7b2f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------- contact_schemas
    op.create_table(
        'contact_schemas',
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contact_schemas_organization_id'), 'contact_schemas', ['organization_id'], unique=False)
    op.create_index('ix_contact_schemas_org_name', 'contact_schemas', ['organization_id', 'name'], unique=False)

    # ------------------------------------------------------------- schema_fields
    op.create_table(
        'schema_fields',
        sa.Column('schema_id', sa.UUID(), nullable=False),
        sa.Column('field_name', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=True),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('format', sa.String(length=32), nullable=True),
        sa.Column('validators', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_key', sa.String(length=120), nullable=True),
        sa.Column('field_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['schema_id'], ['contact_schemas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('schema_id', 'field_name', name='uq_schema_fields_schema_field_name'),
    )
    op.create_index(op.f('ix_schema_fields_organization_id'), 'schema_fields', ['organization_id'], unique=False)
    op.create_index(op.f('ix_schema_fields_schema_id'), 'schema_fields', ['schema_id'], unique=False)

    # ------------------------------------------------------- contact_directories
    op.create_table(
        'contact_directories',
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('default_schema_id', sa.UUID(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['default_schema_id'], ['contact_schemas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contact_directories_organization_id'), 'contact_directories', ['organization_id'], unique=False)
    op.create_index(op.f('ix_contact_directories_default_schema_id'), 'contact_directories', ['default_schema_id'], unique=False)
    op.create_index('ix_contact_directories_org_name', 'contact_directories', ['organization_id', 'name'], unique=False)

    # ---------------------------------------------------------------- datasources
    op.create_table(
        'datasources',
        sa.Column('directory_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['directory_id'], ['contact_directories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_datasources_organization_id'), 'datasources', ['organization_id'], unique=False)
    op.create_index(op.f('ix_datasources_directory_id'), 'datasources', ['directory_id'], unique=False)

    # -------------------------------------------------------------- contact_syncs
    op.create_table(
        'contact_syncs',
        sa.Column('directory_id', sa.UUID(), nullable=True),
        sa.Column('datasource_id', sa.UUID(), nullable=True),
        sa.Column('schema_id', sa.UUID(), nullable=False),
        sa.Column('upload_id', sa.UUID(), nullable=True),
        sa.Column('agent_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('row_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('app_id', sa.String(length=255), nullable=True),
        sa.Column('connection_id', sa.String(length=255), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['directory_id'], ['contact_directories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['schema_id'], ['contact_schemas.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['upload_id'], ['uploads.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contact_syncs_organization_id'), 'contact_syncs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_contact_syncs_directory_id'), 'contact_syncs', ['directory_id'], unique=False)
    op.create_index(op.f('ix_contact_syncs_datasource_id'), 'contact_syncs', ['datasource_id'], unique=False)
    op.create_index(op.f('ix_contact_syncs_schema_id'), 'contact_syncs', ['schema_id'], unique=False)
    op.create_index(op.f('ix_contact_syncs_agent_id'), 'contact_syncs', ['agent_id'], unique=False)
    op.create_index(op.f('ix_contact_syncs_status'), 'contact_syncs', ['status'], unique=False)

    # ------------------------------------------------------------------- contacts
    op.create_table(
        'contacts',
        sa.Column('directory_id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('contact_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sync_id', sa.UUID(), nullable=True),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['directory_id'], ['contact_directories.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sync_id'], ['contact_syncs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('directory_id', 'external_id', name='uq_contacts_directory_external_id'),
    )
    op.create_index(op.f('ix_contacts_organization_id'), 'contacts', ['organization_id'], unique=False)
    op.create_index(op.f('ix_contacts_directory_id'), 'contacts', ['directory_id'], unique=False)
    op.create_index(op.f('ix_contacts_external_id'), 'contacts', ['external_id'], unique=False)
    op.create_index(op.f('ix_contacts_phone_number'), 'contacts', ['phone_number'], unique=False)
    op.create_index('ix_contacts_org_phone_number', 'contacts', ['organization_id', 'phone_number'], unique=False)

    # ------------------------------------------------------------- agent_contacts
    op.create_table(
        'agent_contacts',
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('contact_id', sa.UUID(), nullable=False),
        sa.Column('created_by_user_id', sa.UUID(), nullable=True),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'contact_id', name='uq_agent_contacts_agent_contact'),
    )
    op.create_index(op.f('ix_agent_contacts_organization_id'), 'agent_contacts', ['organization_id'], unique=False)
    op.create_index(op.f('ix_agent_contacts_agent_id'), 'agent_contacts', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_contacts_contact_id'), 'agent_contacts', ['contact_id'], unique=False)

    # ---------------------------------------------------- scheduled_calls.contact_id
    op.add_column('scheduled_calls', sa.Column('contact_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_scheduled_calls_contact_id'), 'scheduled_calls', ['contact_id'], unique=False)
    op.create_foreign_key(
        'fk_scheduled_calls_contact_id', 'scheduled_calls', 'contacts',
        ['contact_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_scheduled_calls_contact_id', 'scheduled_calls', type_='foreignkey')
    op.drop_index(op.f('ix_scheduled_calls_contact_id'), table_name='scheduled_calls')
    op.drop_column('scheduled_calls', 'contact_id')

    op.drop_index(op.f('ix_agent_contacts_contact_id'), table_name='agent_contacts')
    op.drop_index(op.f('ix_agent_contacts_agent_id'), table_name='agent_contacts')
    op.drop_index(op.f('ix_agent_contacts_organization_id'), table_name='agent_contacts')
    op.drop_table('agent_contacts')

    op.drop_index('ix_contacts_org_phone_number', table_name='contacts')
    op.drop_index(op.f('ix_contacts_phone_number'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_external_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_directory_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_organization_id'), table_name='contacts')
    op.drop_table('contacts')

    op.drop_index(op.f('ix_contact_syncs_status'), table_name='contact_syncs')
    op.drop_index(op.f('ix_contact_syncs_agent_id'), table_name='contact_syncs')
    op.drop_index(op.f('ix_contact_syncs_schema_id'), table_name='contact_syncs')
    op.drop_index(op.f('ix_contact_syncs_datasource_id'), table_name='contact_syncs')
    op.drop_index(op.f('ix_contact_syncs_directory_id'), table_name='contact_syncs')
    op.drop_index(op.f('ix_contact_syncs_organization_id'), table_name='contact_syncs')
    op.drop_table('contact_syncs')

    op.drop_index(op.f('ix_datasources_directory_id'), table_name='datasources')
    op.drop_index(op.f('ix_datasources_organization_id'), table_name='datasources')
    op.drop_table('datasources')

    op.drop_index('ix_contact_directories_org_name', table_name='contact_directories')
    op.drop_index(op.f('ix_contact_directories_default_schema_id'), table_name='contact_directories')
    op.drop_index(op.f('ix_contact_directories_organization_id'), table_name='contact_directories')
    op.drop_table('contact_directories')

    op.drop_index(op.f('ix_schema_fields_schema_id'), table_name='schema_fields')
    op.drop_index(op.f('ix_schema_fields_organization_id'), table_name='schema_fields')
    op.drop_table('schema_fields')

    op.drop_index('ix_contact_schemas_org_name', table_name='contact_schemas')
    op.drop_index(op.f('ix_contact_schemas_organization_id'), table_name='contact_schemas')
    op.drop_table('contact_schemas')
