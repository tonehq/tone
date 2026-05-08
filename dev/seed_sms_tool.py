"""
Seed the built-in send_sms tool for all organizations in the database.
Usage: python dev/seed_sms_tool.py

Hardcode your DB URL below before running.
"""

import uuid
import time
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Hardcode your DB URL here ──
DATABASE_URL = "postgresql://neondb_owner:npg_6MIP1wKAkFQh@ep-round-pond-anxl0114-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

SEND_SMS_TOOL = {
    "name": "send_sms",
    "description": "Send an SMS message to the caller during a voice call",
    "tool_type": "send_sms",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The text message content to send via SMS",
            }
        },
        "required": ["message"],
    },
}


def main():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all organizations
        orgs = session.execute(text("SELECT id, name FROM organizations")).fetchall()
        if not orgs:
            print("No organizations found.")
            return

        print(f"Found {len(orgs)} organization(s).\n")

        created = 0
        skipped = 0

        for org_id, org_name in orgs:
            # Check if send_sms tool already exists for this org
            existing = session.execute(
                text("SELECT id FROM tools WHERE name = :name AND organization_id = :org_id"),
                {"name": SEND_SMS_TOOL["name"], "org_id": org_id},
            ).fetchone()

            if existing:
                # Update existing tool to ensure is_template is set
                session.execute(
                    text("UPDATE tools SET is_template = :is_template, tool_type = :tool_type WHERE id = :id"),
                    {"is_template": True, "tool_type": "send_sms", "id": existing[0]},
                )
                print(f"  [{org_name}] send_sms tool already exists (id={existing[0]}), updated is_template=True.")
                skipped += 1
                continue

            now = int(time.time())
            session.execute(
                text(
                    """
                    INSERT INTO tools (uuid, name, description, tool_type, parameters, is_active, is_template, organization_id, created_at, updated_at)
                    VALUES (:uuid, :name, :description, :tool_type, CAST(:parameters AS jsonb), :is_active, :is_template, :org_id, :created_at, :updated_at)
                    """
                ),
                {
                    "uuid": str(uuid.uuid4()),
                    "name": SEND_SMS_TOOL["name"],
                    "description": SEND_SMS_TOOL["description"],
                    "tool_type": SEND_SMS_TOOL["tool_type"],
                    "parameters": str(SEND_SMS_TOOL["parameters"]).replace("'", '"'),
                    "is_active": True,
                    "is_template": True,
                    "org_id": org_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            print(f"  [{org_name}] send_sms tool created.")
            created += 1

        session.commit()
        print(f"\nDone. Created: {created}, Skipped: {skipped}")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
