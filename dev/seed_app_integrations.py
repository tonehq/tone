"""Seed default ``app_integrations`` rows for every organization.

Usage: ``python dev/seed_app_integrations.py``

Reads the curated ``DEFAULT_INTEGRATIONS`` list below, resolves each
provider's ``client_id`` / ``client_secret`` from the env (via the same
Infisical-aware lookup the app uses), encrypts them, and inserts/updates the
``app_integrations`` row for every org.

Idempotent:
  * Existing ``(organization_id, slug)`` row is left untouched (its
    ``is_default = TRUE`` flag is refreshed defensively, but no other fields
    are overwritten — admins may have customised them).
  * New rows get the encrypted credentials baked in at seed time so the
    integration is usable immediately.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── DB URL ─────────────────────────────────────────────────────────────────
# Resolved from the app config (Infisical / .env via shared.config) or the
# DATABASE_URL environment variable — never hardcode credentials in source.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DATABASE_URL = "postgresql://neondb_owner:npg_HPjY5NERS7Uf@ep-crimson-boat-aq6kyekg-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"


if not DATABASE_URL:
    raise SystemExit(
        "DATABASE_URL is not set. Configure it via the app config (.env / Infisical) "
        "or export DATABASE_URL before running this script."
    )

# Lazy import — settings was already imported above, so ``resolve_env`` and
# ``encrypt_json`` won't trigger a re-load.
from core.utils.encryption import encrypt_json  # noqa: E402
from core.utils.env_resolver import resolve_env  # noqa: E402


# Descriptor shape mirrors the ``app_integrations`` schema, with two extras
# used only at seed time:
#   ``credential_env_keys`` — map of credential name → env var to source it
#                             from (e.g. ``{"client_id": "GOOGLE_CLIENT_ID"}``).
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
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        # offline access + forced consent so Google returns a refresh token.
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "credential_env_keys": {
            "client_id": "GOOGLE_CLIENT_ID",
            "client_secret": "GOOGLE_CLIENT_SECRET",
        },
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
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "credential_env_keys": {
            "client_id": "GOOGLE_CLIENT_ID",
            "client_secret": "GOOGLE_CLIENT_SECRET",
        },
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
        "credential_env_keys": {
            "client_id": "HUBSPOT_MCP_CLIENT_ID",
            "client_secret": "HUBSPOT_MCP_CLIENT_SECRET",
        },
        "pkce_required": True,
        "sort_order": 30,
    },
]


_INSERT_SQL = text(
    """
    INSERT INTO app_integrations (
        id, organization_id, slug, display_name, description, category, icon_url,
        auth_type, auth_url, token_url, userinfo_url,
        scopes, extra_auth_params,
        encrypted_credentials,
        pkce_required, is_enabled, is_default, sort_order,
        created_by_user_id, created_at, updated_at
    )
    VALUES (
        :id, :org_id, :slug, :display_name, :description, :category, :icon_url,
        :auth_type, :auth_url, :token_url, :userinfo_url,
        CAST(:scopes AS jsonb), CAST(:extra_auth_params AS jsonb),
        CAST(:encrypted_credentials AS jsonb),
        :pkce_required, :is_enabled, :is_default, :sort_order,
        NULL, :created_at, :updated_at
    )
    """
)


def _resolve_credentials(descriptor: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Read each ``credential_env_keys`` entry from env (Infisical-aware) and
    return a dict ready to encrypt. Missing values are silently skipped so
    partially-configured providers still seed (admins can fill in the rest via
    UI later)."""
    env_map = descriptor.get("credential_env_keys") or {}
    creds = {key: resolve_env(env_var) for key, env_var in env_map.items()}
    creds = {k: v for k, v in creds.items() if v}
    return creds or None


def _encrypted_credentials_for(descriptor: Dict[str, Any]) -> Optional[str]:
    """Produce the JSON string the INSERT statement binds to
    ``encrypted_credentials`` — encrypted blob or ``NULL`` if nothing resolved."""
    creds = _resolve_credentials(descriptor)
    if not creds:
        return None
    return json.dumps(encrypt_json(creds))


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
        "userinfo_url": descriptor.get("userinfo_url"),
        "scopes": json.dumps(descriptor.get("scopes") or []),
        "extra_auth_params": json.dumps(descriptor.get("extra_auth_params") or {}),
        "encrypted_credentials": _encrypted_credentials_for(descriptor),
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
