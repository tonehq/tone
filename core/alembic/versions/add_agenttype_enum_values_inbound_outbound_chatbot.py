"""add INBOUND, OUTBOUND, CHATBOT to agenttype enum

Revision ID: b4c8e1f2a3d5
Revises: a483053dfd8d
Create Date: 2026-02-04

The original migration 00898b55ef80 created the agenttype enum with only
'bot' and 'human'. The application expects 'INBOUND', 'OUTBOUND', 'CHATBOT'.
This migration adds those values to the existing PostgreSQL enum.
"""
from alembic import op
from sqlalchemy import text


revision = "b4c8e1f2a3d5"
down_revision = "a483053dfd8d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for value in ("INBOUND", "OUTBOUND", "CHATBOT"):
        op.execute(text(f"ALTER TYPE agenttype ADD VALUE IF NOT EXISTS '{value}'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values. No-op.
    pass
