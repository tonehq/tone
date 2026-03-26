"""fix channeltype enum to lowercase

Revision ID: 9ddb305bedc2
Revises: f4b3860a5192
Create Date: 2026-03-16

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '9ddb305bedc2'
down_revision = 'f4b3860a5192'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename old enum type
    op.execute("ALTER TYPE channeltype RENAME TO channeltype_old")

    # Create new enum with lowercase values
    op.execute("CREATE TYPE channeltype AS ENUM ('twilio', 'exotel', 'web', 'google_meet', 'zoom')")

    # Update existing data to lowercase
    op.execute("ALTER TABLE channels ALTER COLUMN type TYPE channeltype USING LOWER(type::text)::channeltype")

    # Drop old enum type
    op.execute("DROP TYPE channeltype_old")


def downgrade() -> None:
    op.execute("ALTER TYPE channeltype RENAME TO channeltype_old")
    op.execute("CREATE TYPE channeltype AS ENUM ('TWILIO', 'WEB', 'GOOGLE_MEET', 'ZOOM', 'exotel')")
    op.execute("ALTER TABLE channels ALTER COLUMN type TYPE channeltype USING UPPER(type::text)::channeltype")
    op.execute("DROP TYPE channeltype_old")
