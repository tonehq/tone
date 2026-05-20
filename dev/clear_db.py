"""
Script to clear all data from the database while respecting foreign key constraints.
Tables are deleted in reverse dependency order (children before parents).

Usage:
    python dev/clear_db.py
"""

from sqlalchemy import create_engine, text

# ── Hardcoded DB connection ──────────────────────────────────────────────
DATABASE_URL = "postgresql://neondb_owner:npg_QSh4dqZ2NXpV@ep-solitary-block-ame1uzci-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# ─────────────────────────────────────────────────────────────────────────

# Deletion order: children first, parents last.
# Each table appears AFTER all tables that reference it via foreign keys.
TABLES_IN_DELETE_ORDER = [
    # Deepest children (no dependents)
    "document_chunks",        # FK → documents
    "agent_tools",            # FK → agents, tools
    "agent_mcp_servers",      # FK → agents, mcp_servers
    "agent_configs",          # FK → agents, services
    "agent_channels",         # FK → agents, channels
    "agent_channel_phone_numbers",  # FK → agents, channels
    "channel_phone_numbers",  # FK → channels

    # Documents & uploads have circular-ish refs via call_logs
    "documents",              # FK → uploads, agents
    "uploads",                # FK → agents, call_logs
    "call_logs",              # FK → agents, uploads

    # Tools & MCP servers
    "tools",                  # FK → oauth_connections, mcp_servers
    "mcp_servers",            # FK → organizations

    # Services layer
    "services",               # FK → service_providers, api_keys, model_instance, users
    "api_keys",               # FK → service_providers, accounts, users

    # Model hierarchy
    "model_instance",         # FK → model_menu, accounts
    "model_menu",             # FK → model_providers_menu
    "voices",                 # FK → service_providers, models, model_providers_menu, model_menu

    # Agents
    "agents",                 # FK → users

    # Generated API keys
    "generated_api_keys",     # FK → organizations

    # Channels
    "channels",               # FK → organizations

    # OAuth
    "oauth_connections",      # FK → users

    # Organization related
    "organization_access_requests",  # FK → users, organizations
    "organization_invites",          # FK → users, organizations
    "members",                       # FK → users, organizations

    # Auth related
    "email_verifications",    # FK → users
    "password_resets",        # FK → users

    # Reference data
    "models",                 # FK → service_providers
    "hosting_providers",      # no FK (TimestampModel)
    "model_providers_menu",   # no FK (TimestampModel)
    "service_providers",      # no FK (TimestampModel)

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
