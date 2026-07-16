"""create scheduled_calls table

Scheduled outbound calls live in a dedicated ``scheduled_calls`` table (shown on a
separate page), so the ``calls`` table holds only real call logs — a ``calls`` row is
created only when a call actually connects. A scheduled call links to the log it
produces via ``scheduled_calls.call_id``.

Revision ID: b7d4e9c2f1a8
Revises: f3a7c9d21b48
Create Date: 2026-07-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'b7d4e9c2f1a8'
down_revision = 'f3a7c9d21b48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scheduled_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('from_number', sa.String(length=20), nullable=False),
        sa.Column('to_number', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='scheduled'),
        sa.Column('provider', sa.String(length=20), nullable=False, server_default='twilio'),
        sa.Column('provider_call_sid', sa.String(length=120), nullable=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('queue_job_id', sa.Integer(), nullable=True),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scheduled_calls_organization_id', 'scheduled_calls', ['organization_id'])
    op.create_index('ix_scheduled_calls_status', 'scheduled_calls', ['status'])
    op.create_index('ix_scheduled_calls_scheduled_at', 'scheduled_calls', ['scheduled_at'])


def downgrade() -> None:
    op.drop_index('ix_scheduled_calls_scheduled_at', table_name='scheduled_calls')
    op.drop_index('ix_scheduled_calls_status', table_name='scheduled_calls')
    op.drop_index('ix_scheduled_calls_organization_id', table_name='scheduled_calls')
    op.drop_table('scheduled_calls')
