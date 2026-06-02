"""
Script to clear all data from the database while respecting foreign key constraints.
Tables are deleted in reverse dependency order (children before parents).

Usage:
    python dev/clear_db.py
"""

from sqlalchemy import create_engine, text

# ── Hardcoded DB connection ──────────────────────────────────────────────
DATABASE_URL = "postgresql://neondb_owner:npg_6MIP1wKAkFQh@ep-round-pond-anxl0114-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# ─────────────────────────────────────────────────────────────────────────

# Deletion order: children first, parents last.
# Each table appears AFTER all tables that reference it via foreign keys.
TABLES_IN_DELETE_ORDER = [
    # Deepest children (no dependents)
    "knowledge_base_chunks",  # FK → uploads
    "agent_knowledge_bases",  # FK → agents, agent_configs, uploads
    "agent_tools",            # FK → agents, agent_configs, tools
    "agent_mcp_servers",      # FK → agents, agent_configs, mcp_servers
    "tool_executions",        # FK → calls, tools
    "phone_numbers",          # FK → agents, channels
    "webhooks",               # FK → organizations

    # Agent configs (FK → agents, models, model_languages)
    "agent_configs",

    # Calls & uploads
    "calls",                  # FK → agents
    "uploads",                # FK → organizations

    # Tools & MCP servers
    "tools",                  # FK → organizations, oauth_connections
    "mcp_servers",            # FK → organizations

    # API keys (FK → model_providers, organizations)
    "api_keys",

    # Model hierarchy
    "model_voices",           # FK → models
    "model_languages",        # FK → models
    "models",                 # FK → model_providers

    # Agents (FK → users, organizations)
    "agents",

    # Channels (FK → organizations)
    "channels",

    # OAuth
    "oauth_connections",      # FK → users

    # Organization related
    "invites",                # FK → organizations
    "email_requests",         # FK → users
    "members",                # FK → users, organizations

    # Reference data
    "model_providers",        # no FK (TimestampModel)

    # Top-level entities
    "organizations",          # FK → users (created_by)
    "users",                  # no FK

    # Alembic migration tracking (optional - uncomment to also clear migration history)
    # "alembic_version",
]


def clear_database():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # Get tables that actually exist in the database
        result = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))
        existing_tables = {row[0] for row in result}

        # Filter to only tables that exist, preserving dependency order
        tables_to_clear = [t for t in TABLES_IN_DELETE_ORDER if t in existing_tables]

        # Also find any tables in DB not in our list (except alembic_version)
        unlisted = existing_tables - set(TABLES_IN_DELETE_ORDER) - {"alembic_version"}
        if unlisted:
            print(f"Note: Found extra tables not in delete order: {unlisted}")
            tables_to_clear = list(unlisted) + tables_to_clear

        if not tables_to_clear:
            print("No tables to truncate.")
            return

        all_tables = ", ".join(f'"{t}"' for t in tables_to_clear)
        print(f"Truncating {len(tables_to_clear)} tables...")
        conn.execute(text(f"TRUNCATE TABLE {all_tables} CASCADE"))

    print("All data cleared successfully.")


if __name__ == "__main__":
    confirm = input(
        "WARNING: This will DELETE ALL DATA from the database.\n"
        f"Target: {DATABASE_URL}\n"
        "Type 'yes' to confirm: "
    )
    if confirm.strip().lower() == "yes":
        clear_database()
    else:
        print("Aborted.")
