"""api_keys: add service_type, description, is_default, config + partial unique index

Adds the four columns the Services page needs onto the existing ``api_keys``
table (no new tables). The partial unique index enforces "at most one default
ApiKey per (org, service_type)" — the service layer also does an atomic
flip-others-to-false inside the same DB transaction.

Revision ID: c4d5e6f7a8b9
Revises: 389d07c1be1d
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c4d5e6f7a8b9"
down_revision = "389d07c1be1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("service_type", sa.String(20), nullable=True))
    op.add_column("api_keys", sa.Column("description", sa.String(500), nullable=True))
    op.add_column(
        "api_keys",
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "api_keys",
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "uq_api_keys_one_default_per_org_type",
        "api_keys",
        ["organization_id", "service_type"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_api_keys_one_default_per_org_type", table_name="api_keys")
    op.drop_column("api_keys", "config")
    op.drop_column("api_keys", "is_default")
    op.drop_column("api_keys", "description")
    op.drop_column("api_keys", "service_type")
