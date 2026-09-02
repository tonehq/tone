"""Add unique constraints on model_voices and model_languages

Guard against duplicate catalog rows that nothing currently prevents at the DB
level:

- ``model_voices``   → UNIQUE (model_id, voice_id)
- ``model_languages``→ UNIQUE (model_id, name)

Both match the exact dedup keys the seed script already uses (it queries the
existing (model_id, voice_id) / (model_id, name) set and skips rows that are
already present), so no existing or seed-driven insert can violate them. NULL
``voice_id`` rows are unconstrained (Postgres treats NULLs as distinct); the
seed never inserts a NULL voice_id anyway.

Verified against the target DB before writing: zero duplicates on either key.

Revision ID: e7b1c4a9d3f2
Revises: f4d2a9c1e6b8
Create Date: 2026-09-02

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e7b1c4a9d3f2'
down_revision = 'f4d2a9c1e6b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_model_voices_model_voice_id",
        "model_voices",
        ["model_id", "voice_id"],
    )
    op.create_unique_constraint(
        "uq_model_languages_model_name",
        "model_languages",
        ["model_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_model_languages_model_name", "model_languages", type_="unique"
    )
    op.drop_constraint(
        "uq_model_voices_model_voice_id", "model_voices", type_="unique"
    )
