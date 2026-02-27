"""Make system_prompt column nullable and set default for existing NULLs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from core.database.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        db.execute(text(
            "ALTER TABLE agent_configs ALTER COLUMN system_prompt DROP NOT NULL"
        ))
        db.execute(text(
            "ALTER TABLE agent_configs ALTER COLUMN system_prompt SET DEFAULT ''"
        ))
        db.commit()
        print("Successfully made system_prompt nullable with default ''.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
