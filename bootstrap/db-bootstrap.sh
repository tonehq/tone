#!/usr/bin/env bash
# db-bootstrap.sh — Initialize the Tone database (migrations + seed data)
#
# To run:
#   # 1. Local (.env DATABASE_URL)
#   ./bootstrap/db-bootstrap.sh
#
#   # 2. With Infisical (DATABASE_URL injected from Infisical)
#   infisical run --projectId "$INFISICAL_PROJECT_ID" --env="$INFISICAL_ENV" -- \
#       ./bootstrap/db-bootstrap.sh
#
#   # 3. Pass DATABASE_URL directly (overrides .env / Infisical)
#   ./bootstrap/db-bootstrap.sh --database-url "postgresql://user:pass@host:5432/db"
#   ./bootstrap/db-bootstrap.sh --database-url=postgresql://user:pass@host:5432/db
#
# Prerequisites:
#   - Python virtualenv activated with dependencies already installed
#   - Database connection configured via CLI arg, .env, or Infisical
#   - Optional: Provider API keys in env (OPENAI_API_KEY, etc.) for seeding API keys

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Parse CLI args ──────────────────────────────────────────────────
# --database-url <url> or --database-url=<url> takes precedence over
# any DATABASE_URL already set via .env or Infisical.

CLI_DATABASE_URL=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --database-url)
            CLI_DATABASE_URL="${2:-}"
            if [[ -z "$CLI_DATABASE_URL" ]]; then
                echo "Error: --database-url requires a value" >&2
                exit 1
            fi
            shift 2
            ;;
        --database-url=*)
            CLI_DATABASE_URL="${1#*=}"
            shift
            ;;
        -h|--help)
            sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Error: unknown argument '$1'" >&2
            echo "Usage: $0 [--database-url <url>]" >&2
            exit 1
            ;;
    esac
done

if [[ -n "$CLI_DATABASE_URL" ]]; then
    export DATABASE_URL="$CLI_DATABASE_URL"
    echo "==> Using DATABASE_URL from CLI argument."
fi

# ── Step 1: Run Alembic migrations ──────────────────────────────────
# Applies all migration scripts in alembic/versions/ to create the full
# DB schema: users, organizations, members, service_providers, models,
# api_keys, voices, agents, agent_configs, call_logs, channels, etc.
# DB URL is read from shared/config.py (which loads .env → DATABASE_URL).

echo "==> Running Alembic migrations (alembic upgrade head)..."
alembic upgrade head

# ── Step 2: Apply Procrastinate ingestion-queue schema ──────────────
# One-time per environment. Not managed by Alembic. Required before the
# document-ingestion worker can run; without it the worker error-loops on
# a missing table.

echo ""
echo "==> Applying Procrastinate ingestion-queue schema..."
if PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app healthchecks &>/dev/null; then
    echo "    Schema already applied — skipping."
else
    PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply
fi

# ── Step 3: Seed the database ───────────────────────────────────────
# Reads dev/dev-data.json and prompts for org name, email, and password.
# Seeds: User, Organization, Member, ServiceProviders (LLM/STT/TTS),
# Models, ApiKeys (encrypted, from env vars), and Voices.

echo ""
echo "==> Seeding database..."
python dev/seed.py

echo ""
echo "==> Bootstrap complete. You can now start the server with: python main.py"
