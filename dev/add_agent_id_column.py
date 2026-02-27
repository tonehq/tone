"""One-time script to add agent_id column to channel_phone_numbers table."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from core.database.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'channel_phone_numbers' AND column_name = 'agent_id'"
        ))
        if result.fetchone():
            print("agent_id column already exists. Nothing to do.")
            return

        # Add the column
        db.execute(text(
            "ALTER TABLE channel_phone_numbers ADD COLUMN agent_id BIGINT"
        ))
        # Add foreign key
        db.execute(text(
            "ALTER TABLE channel_phone_numbers "
            "ADD CONSTRAINT channel_phone_numbers_agent_id_fkey "
            "FOREIGN KEY (agent_id) REFERENCES agents(id)"
        ))
        db.commit()
        print("Successfully added agent_id column to channel_phone_numbers table.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
