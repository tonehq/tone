"""Seed default ``app_integrations`` rows for every organization.

Usage: ``python dev/seed_app_integrations.py``

For each existing org, inserts a curated set of integrations. The descriptors
mirror what ``core/services/oauth_providers.py`` already declares for the
hardcoded catalog so the two stay in sync — over time, the DB-backed catalog
will become the single source of truth and the hardcoded dict will retire.

Idempotent: a row whose ``(organization_id, slug)`` pair already exists is
left untouched (its ``is_default = TRUE`` flag is refreshed defensively, but
no other fields are overwritten — admins may have customised them).
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── DB URL ─────────────────────────────────────────────────────────────────
# Resolved from the app config (Infisical / .env via shared.config) or the
# DATABASE_URL environment variable — never hardcode credentials in source.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from shared.config import settings

    DATABASE_URL = settings.DATABASE_URL
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit(
        "DATABASE_URL is not set. Configure it via the app config (.env / Infisical) "
        "or export DATABASE_URL before running this script."
    )


# Descriptor shape mirrors the ``app_integrations`` schema. Only the columns
# we want to set are listed — everything else falls back to model defaults.
DEFAULT_INTEGRATIONS = [
    {
        "slug": "google_calendar",
        "display_name": "Google Calendar",
        "description": (
            "Create events, check availability, and manage schedules from voice calls."
        ),
        "category": "google",
        "icon_url": None,
        "auth_type": "oauth",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        # offline access + forced consent so Google returns a refresh token.
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "client_id_env_key": "GOOGLE_CLIENT_ID",
        "client_secret_env_key": "GOOGLE_CLIENT_SECRET",
        "pkce_required": True,
        "sort_order": 10,
    },
    {
        "slug": "google_sheets",
        "display_name": "Google Sheets",
        "description": "Read and write spreadsheet data during conversations.",
        "category": "google",
        "icon_url": None,
        "auth_type": "oauth",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "client_id_env_key": "GOOGLE_CLIENT_ID",
        "client_secret_env_key": "GOOGLE_CLIENT_SECRET",
        "pkce_required": True,
        "sort_order": 20,
    },
    {
        "slug": "hubspot",
        "display_name": "HubSpot",
        "description": (
            "Read and write CRM data — contacts, companies, deals, and tickets — during calls."
        ),
        "category": "crm",
        "icon_url": None,
        "auth_type": "oauth",
        "auth_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        # Sensible CRM defaults; admins can edit the row to add more scopes
        # (e.g. ``content``, ``files``) without changing the seed.
        "scopes": [
            "crm.objects.contacts.read",
            "crm.objects.contacts.write",
            "crm.objects.companies.read",
            "crm.objects.deals.read",
            "tickets",
        ],
        "extra_auth_params": {},
        # Reuses the same MCP Auth App credentials we already plumbed through
        # for ``mcp.hubspot.com`` — one HubSpot app, one set of env vars.
        "client_id_env_key": "HUBSPOT_MCP_CLIENT_ID",
        "client_secret_env_key": "HUBSPOT_MCP_CLIENT_SECRET",
        "pkce_required": True,
        "sort_order": 30,
    },
]


_INSERT_SQL = text(
    """
    INSERT INTO app_integrations (
        id, organization_id, slug, display_name, description, category, icon_url,
        auth_type, auth_url, token_url, scopes, extra_auth_params,
        client_id_env_key, client_secret_env_key,
        pkce_required, is_enabled, is_default, sort_order,
        created_by_user_id, created_at, updated_at
    )
    VALUES (
        :id, :org_id, :slug, :display_name, :description, :category, :icon_url,
        :auth_type, :auth_url, :token_url, CAST(:scopes AS jsonb), CAST(:extra_auth_params AS jsonb),
        :client_id_env_key, :client_secret_env_key,
        :pkce_required, :is_enabled, :is_default, :sort_order,
        NULL, :created_at, :updated_at
    )
    """
)


def _params_for(org_id, descriptor, now):
    """Map a descriptor dict to the bind-params the INSERT expects."""
    return {
        "id": str(uuid.uuid4()),
        "org_id": str(org_id),
        "slug": descriptor["slug"],
        "display_name": descriptor["display_name"],
        "description": descriptor.get("description"),
        "category": descriptor.get("category"),
        "icon_url": descriptor.get("icon_url"),
        "auth_type": descriptor["auth_type"],
        "auth_url": descriptor.get("auth_url"),
        "token_url": descriptor.get("token_url"),
        "scopes": json.dumps(descriptor.get("scopes") or []),
        "extra_auth_params": json.dumps(descriptor.get("extra_auth_params") or {}),
        "client_id_env_key": descriptor.get("client_id_env_key"),
        "client_secret_env_key": descriptor.get("client_secret_env_key"),
        "pkce_required": descriptor.get("pkce_required", True),
        "is_enabled": descriptor.get("is_enabled", True),
        # ``is_default = TRUE`` marks rows as Tone-shipped — protected from
        # deletion in the service layer; admins disable via is_enabled instead.
        "is_default": True,
        "sort_order": descriptor.get("sort_order", 100),
        "created_at": now,
        "updated_at": now,
    }


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
            for descriptor in DEFAULT_INTEGRATIONS:
                existing = session.execute(
                    text(
                        "SELECT id FROM app_integrations "
                        "WHERE organization_id = :org_id AND slug = :slug"
                    ),
                    {"org_id": str(org_id), "slug": descriptor["slug"]},
                ).fetchone()

                if existing:
                    # Refresh the default-flag in case it was unset by a manual
                    # admin edit — keeps the seed contract intact without
                    # touching other (possibly customised) fields.
                    session.execute(
                        text("UPDATE app_integrations SET is_default = TRUE WHERE id = :id"),
                        {"id": existing[0]},
                    )
                    print(f"  [{org_name}] {descriptor['slug']} already exists (id={existing[0]}), skipped.")
                    skipped += 1
                    continue

                now = datetime.now(timezone.utc)
                session.execute(_INSERT_SQL, _params_for(org_id, descriptor, now))
                print(f"  [{org_name}] {descriptor['slug']} integration created.")
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
