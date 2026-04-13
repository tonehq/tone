#!/usr/bin/env bash
# db-bootstrap.sh — Initialize the Tone database (migrations + seed data)
#
# Usage:
#   ./db-bootstrap.sh
#
# Prerequisites:
#   - Python virtualenv activated with dependencies already installed
#   - Database connection configured via .env or shared/config.py
#   - Optional: Provider API keys in env (OPENAI_API_KEY, etc.) for seeding API keys

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Run Alembic migrations ──────────────────────────────────
# Applies all migration scripts in alembic/versions/ to create the full
# DB schema: users, organizations, members, service_providers, models,
# api_keys, voices, agents, agent_configs, call_logs, channels, etc.
# DB URL is read from shared/config.py (which loads .env → DATABASE_URL).

echo "==> Running Alembic migrations (alembic upgrade head)..."
alembic upgrade head

# ── Step 2: Seed the database ───────────────────────────────────────
# Reads dev/dev-data.json and prompts for org name, email, and password.
# Seeds: User, Organization, Member, ServiceProviders (LLM/STT/TTS),
# Models, ApiKeys (encrypted, from env vars), and Voices.

echo ""
echo "==> Seeding database..."
python dev/seed.py

echo ""
echo "==> Bootstrap complete. You can now start the server with: python main.py"
