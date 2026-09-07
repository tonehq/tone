"""add cloud_providers table + models.cloud_provider_id FK

Additive only (expand step): a new ``cloud_providers`` table (same shape as
``model_providers``) and a nullable ``models.cloud_provider_id`` FK. Nothing
reads the column yet, so this is backward-compatible with the running release.

Revision ID: f3b8d1e0c6a9
Revises: e7c2a9f4b1d6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "f3b8d1e0c6a9"
down_revision = "e7c2a9f4b1d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cloud_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("provider_id", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("website_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("meta_data_schema", JSONB(), nullable=True),
        sa.UniqueConstraint("provider_id", name="uq_cloud_providers_provider_id"),
    )

    op.add_column("models", sa.Column("cloud_provider_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_models_cloud_provider_id",
        "models",
        "cloud_providers",
        ["cloud_provider_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_models_cloud_provider_id", "models", ["cloud_provider_id"])


def downgrade() -> None:
    op.drop_index("ix_models_cloud_provider_id", table_name="models")
    op.drop_constraint("fk_models_cloud_provider_id", "models", type_="foreignkey")
    op.drop_column("models", "cloud_provider_id")
    op.drop_table("cloud_providers")
