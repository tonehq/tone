"""Add audit_logs table

Revision ID: f1a2b3c4d5e6
Revises: 4e4fc977b458, 6696b9e0556b, e8a3c5d9f1b2
Create Date: 2026-06-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = ('4e4fc977b458', '6696b9e0556b', 'e8a3c5d9f1b2')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('actor_user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=False),
        sa.Column('agent_config_id', sa.UUID(), nullable=True),
        sa.Column('target_resource_type', sa.String(length=32), nullable=True),
        sa.Column('target_resource_id', sa.String(length=64), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index(
        'ix_audit_logs_org_agent_created',
        'audit_logs',
        ['organization_id', 'agent_id', 'created_at'],
        unique=False,
    )
    op.create_index(
        'ix_audit_logs_org_created',
        'audit_logs',
        ['organization_id', 'created_at'],
        unique=False,
    )
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'], unique=False)
    op.create_index(
        op.f('ix_audit_logs_organization_id'),
        'audit_logs',
        ['organization_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_organization_id'), table_name='audit_logs')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_org_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_org_agent_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_table('audit_logs')
