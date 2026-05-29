"""
Seed built-in tools (send_sms, google_calendar, etc.) for all organizations.
Usage: python dev/seed_built_in_tools.py

Skips if a tool with the same tool_type already exists for an org.
"""

import uuid
import sys
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Hardcode your DB URL here ──
DATABASE_URL = "postgresql://neondb_owner:npg_QSh4dqZ2NXpV@ep-solitary-block-ame1uzci-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

BUILT_IN_TOOLS = [
    {
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
    },
    {
        "name": "google_calendar",
        "description": "Create events, check availability, and list events on Google Calendar",
        "tool_type": "google_calendar",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to perform: create_event, check_availability, or list_events",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the calendar event (for create_event)",
                },
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in HH:MM format (24-hour)",
                },
                "duration_minutes": {
                    "type": "number",
                    "description": "Duration of the event in minutes (default 30)",
                },
                "description": {
                    "type": "string",
                    "description": "Description or notes for the event",
                },
                "attendee_email": {
                    "type": "string",
                    "description": "Email address of the attendee to invite",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in HH:MM format for check_availability (default 17:00)",
                },
                "max_results": {
                    "type": "number",
                    "description": "Maximum number of events to return for list_events (default 5)",
                },
            },
            "required": ["action"],
        },
    },
]


def main():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        orgs = session.execute(text("SELECT id, name FROM organizations")).fetchall()
        if not orgs:
            print("No organizations found.")
            return

        print(f"Found {len(orgs)} organization(s).\n")

        created = 0
        skipped = 0

        for org_id, org_name in orgs:
            for tool_def in BUILT_IN_TOOLS:
                # Check if tool with this tool_type already exists for this org
                existing = session.execute(
                    text("SELECT id FROM tools WHERE tool_type = :tool_type AND organization_id = :org_id"),
                    {"tool_type": tool_def["tool_type"], "org_id": org_id},
                ).fetchone()

                if existing:
                    # Ensure is_template is set
                    session.execute(
                        text("UPDATE tools SET is_template = :is_template WHERE id = :id"),
                        {"is_template": True, "id": existing[0]},
                    )
                    print(f"  [{org_name}] {tool_def['tool_type']} already exists (id={existing[0]}), skipped.")
                    skipped += 1
                    continue

                now = datetime.now(timezone.utc)
                session.execute(
                    text(
                        """
                        INSERT INTO tools (id, name, description, tool_type, parameters, is_active, is_template, organization_id, created_at, updated_at)
                        VALUES (:id, :name, :description, :tool_type, CAST(:parameters AS jsonb), :is_active, :is_template, :org_id, :created_at, :updated_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "tool_type": tool_def["tool_type"],
                        "parameters": json.dumps(tool_def["parameters"]),
                        "is_active": True,
                        "is_template": True,
                        "org_id": org_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                print(f"  [{org_name}] {tool_def['tool_type']} tool created.")
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
