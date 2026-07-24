"""add generated_api_keys table

Introduces the customer-facing programmatic-access API keys (distinct from the
provider-credential ``api_keys`` table, which stores encrypted LLM/STT/TTS keys).

We store only a SHA-256 hash of the full key so a database dump does not leak
usable credentials. A partial unique index enforces "one active name per org"
without blocking name reuse after a key is revoked or deleted.

Revision ID: 2178f950024d
Revises: a7c4e1f92b06
Create Date: 2026-07-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "2178f950024d"
down_revision = "a7c4e1f92b06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generated_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # O(1) auth-path lookup: every request hashes the incoming Bearer and does
    # a point query on this column. Unique also stops hash collisions on insert.
    op.create_index(
        "uq_generated_api_keys_key_hash",
        "generated_api_keys",
        ["key_hash"],
        unique=True,
    )

    # List endpoint sorts by created_at DESC within an org.
    op.create_index(
        "ix_generated_api_keys_org_created",
        "generated_api_keys",
        ["organization_id", sa.text("created_at DESC")],
    )

    # Partial unique on (org, lower(name)) for LIVE (non-deleted, non-revoked)
    # rows. Built CONCURRENTLY so a large existing table (theoretical, since the
    # table is new) does not block writes. IF NOT EXISTS keeps it idempotent.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "
            "uq_generated_api_keys_org_active_name "
            "ON generated_api_keys (organization_id, lower(name)) "
            "WHERE deleted_at IS NULL AND revoked_at IS NULL"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS uq_generated_api_keys_org_active_name"
        )
    op.drop_index("ix_generated_api_keys_org_created", table_name="generated_api_keys")
    op.drop_index("uq_generated_api_keys_key_hash", table_name="generated_api_keys")
    op.drop_table("generated_api_keys")
