#!/usr/bin/env bash
# org-bootstrap.sh — Add a new organization to an already-initialized Tone DB
#
# To run:
#   # 1. Local (.env DATABASE_URL), no API keys
#   ./bootstrap/org-bootstrap.sh
#
#   # 2. Local (.env DATABASE_URL), API keys pulled from env vars
#   ./bootstrap/org-bootstrap.sh --api-keys-from-env
#
#   # 3. With Infisical (secrets — including DATABASE_URL — injected from Infisical)
#   infisical run --projectId "$INFISICAL_PROJECT_ID" --env="$INFISICAL_ENV" -- \
#       ./bootstrap/org-bootstrap.sh [--api-keys-from-env]
#
# Prerequisites:
#   - Python virtualenv activated with dependencies already installed
#   - Database already migrated + global providers/models/voices seeded
#     (via ./bootstrap/db-bootstrap.sh or an existing environment)
#   - Optional: provider API keys exported in env if using --api-keys-from-env
#     (OPENAI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, etc.)
#
# What it does NOT do:
#   - Run Alembic migrations
#   - Seed the global provider/model/voice catalogue
#   Use ./bootstrap/db-bootstrap.sh for a fresh database.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Seeding new organization (user + org + member + app_integrations + built-in tools)..."
python dev/seed_org.py "$@"

echo ""
echo "==> Org bootstrap complete."
