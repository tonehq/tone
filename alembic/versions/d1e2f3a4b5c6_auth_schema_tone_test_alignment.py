"""Auth schema — align users/organizations/members/invites with tone-test

Also merges the three open heads (a0b1c2d3e4f5 v2 revamp, 356e4af099b9
documents, af6013ae5648 tools) into a single linear history.

The `invites` table gets `token`, `invited_by`, `expires_at` etc. as
nullable so existing rows survive — application code enforces NOT NULL
on insert via the ORM model.

Revision ID: d1e2f3a4b5c6
Revises: a0b1c2d3e4f5, 356e4af099b9, af6013ae5648
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d1e2f3a4b5c6"
down_revision = ("a0b1c2d3e4f5", "356e4af099b9", "af6013ae5648")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── organizations ──────────────────────────────────────────────────
    op.alter_column(
        "organizations", "name",
        type_=sa.String(255),
        existing_type=sa.String(120),
        existing_nullable=False,
    )
    op.alter_column(
        "organizations", "slug",
        type_=sa.String(255),
        existing_type=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        "organizations", "description",
        type_=sa.Text(),
        existing_type=sa.String(500),
        existing_nullable=True,
    )
    op.drop_constraint("uq_organizations_name", "organizations", type_="unique")
    op.drop_column("organizations", "is_active")
    op.drop_column("organizations", "archived_at")

    op.add_column("organizations", sa.Column("logo_url", sa.String(512), nullable=True))
    op.add_column("organizations", sa.Column("website", sa.String(512), nullable=True))
    op.add_column("organizations", sa.Column(
        "subscription_tier", sa.String(50),
        nullable=False, server_default=sa.text("'free'"),
    ))
    op.add_column("organizations", sa.Column(
        "status", sa.String(50),
        nullable=False, server_default=sa.text("'active'"),
    ))
    op.add_column("organizations", sa.Column(
        "max_agents", sa.Integer(),
        nullable=False, server_default=sa.text("5"),
    ))
    op.add_column("organizations", sa.Column(
        "max_test_runs_per_month", sa.Integer(),
        nullable=False, server_default=sa.text("100"),
    ))
    op.add_column("organizations", sa.Column(
        "max_production_calls_per_month", sa.Integer(),
        nullable=False, server_default=sa.text("1000"),
    ))
    op.add_column("organizations", sa.Column(
        "max_users", sa.Integer(),
        nullable=False, server_default=sa.text("5"),
    ))
    op.add_column("organizations", sa.Column(
        "sso_enabled", sa.Boolean(),
        nullable=False, server_default=sa.text("false"),
    ))
    op.add_column("organizations", sa.Column("sso_provider", sa.String(50), nullable=True))
    op.add_column("organizations", sa.Column("sso_config", postgresql.JSONB(), nullable=True))
    op.add_column("organizations", sa.Column("settings", postgresql.JSONB(), nullable=True))
    op.add_column("organizations", sa.Column("metadata", postgresql.JSONB(), nullable=True))

    # ── users ──────────────────────────────────────────────────────────
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.drop_column("users", "full_name")
    op.drop_column("users", "encrypted_password")
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "default_organization_id")

    op.add_column("users", sa.Column(
        "organization_id", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True,
    ))
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(512), nullable=True))
    op.add_column("users", sa.Column(
        "role", sa.String(50),
        nullable=False, server_default=sa.text("'developer'"),
    ))
    op.add_column("users", sa.Column(
        "is_verified", sa.Boolean(),
        nullable=False, server_default=sa.text("false"),
    ))
    op.add_column("users", sa.Column(
        "auth_provider", sa.String(50),
        nullable=False, server_default=sa.text("'local'"),
    ))
    op.add_column("users", sa.Column("auth_provider_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_login_ip", sa.String(45), nullable=True))
    op.add_column("users", sa.Column("preferences", postgresql.JSONB(), nullable=True))
    op.add_column("users", sa.Column("notification_settings", postgresql.JSONB(), nullable=True))

    # ── members ────────────────────────────────────────────────────────
    op.alter_column(
        "members", "role",
        type_=sa.String(50),
        existing_type=sa.String(20),
        existing_nullable=False,
        server_default=sa.text("'developer'"),
    )
    op.add_column("members", sa.Column(
        "is_default", sa.Boolean(),
        nullable=False, server_default=sa.text("false"),
    ))
    op.add_column("members", sa.Column(
        "joined_at", sa.DateTime(timezone=True),
        nullable=False, server_default=sa.text("timezone('utc', now())"),
    ))
    op.create_foreign_key(
        "fk_members_organization_id_organizations",
        "members", "organizations",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("uq_members_org_user", "members", type_="unique")
    op.create_unique_constraint("uq_members_user_org", "members", ["user_id", "organization_id"])

    # ── invites ────────────────────────────────────────────────────────
    op.drop_column("invites", "invited_by_user_id")
    op.drop_column("invites", "email_request_id")
    op.alter_column(
        "invites", "role",
        type_=sa.String(50),
        existing_type=sa.String(20),
        existing_nullable=False,
        server_default=sa.text("'developer'"),
    )
    # `token`, `invited_by`, `expires_at` are nullable at the DB level so
    # this migration runs against tables that may have rows. The Invite
    # ORM model declares them NOT NULL — application code enforces.
    op.add_column("invites", sa.Column("token", sa.String(255), nullable=True))
    op.create_index("ix_invites_token", "invites", ["token"], unique=True)
    op.add_column("invites", sa.Column(
        "invited_by", postgresql.UUID(as_uuid=True),
        sa.ForeignKey("users.id"), nullable=True,
    ))
    op.add_column("invites", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invites", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_foreign_key(
        "fk_invites_organization_id_organizations",
        "invites", "organizations",
        ["organization_id"], ["id"],
    )
    op.drop_column("invites", "updated_at")


def downgrade() -> None:
    # Downgrade is intentionally not implemented — restoring dropped
    # columns (full_name, encrypted_password, etc.) would lose data.
    # Roll back by restoring DB from backup or dropping & re-running
    # alembic upgrade from the previous head.
    raise NotImplementedError(
        "Downgrade of auth schema alignment is not supported."
    )
