#!/usr/bin/env bash
# dev-bootstrap.sh — Full development environment setup for Tone
#
# Usage:
#   ./dev-bootstrap.sh
#
# What it does:
#   1. Installs Python 3.11 (via Homebrew on macOS, apt on Linux)
#   2. Creates a virtual environment using Python 3.11
#   3. Activates the virtual environment
#   4. Installs all Python dependencies from requirements.txt
#   5. Runs Alembic migrations to create the DB schema
#   6. Seeds the database with providers, models, voices, and first user

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

# ── Step 1: Install Python 3.11 ────────────────────────────────────

echo "==> Checking for Python 3.11..."

if command -v python3.11 &>/dev/null; then
    echo "    Python 3.11 already installed: $(python3.11 --version)"
else
    echo "    Python 3.11 not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &>/dev/null; then
            echo "ERROR: Homebrew not found. Install it from https://brew.sh"
            exit 1
        fi
        brew install python@3.11
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update
        sudo apt install -y python3.11 python3.11-venv python3.11-dev
    else
        echo "ERROR: Unsupported OS. Please install Python 3.11 manually."
        exit 1
    fi
fi

# ── Step 2: Create virtual environment ──────────────────────────────

echo ""
echo "==> Setting up virtual environment..."

if [ -d "$VENV_DIR" ]; then
    echo "    Virtual environment already exists at $VENV_DIR"
else
    python3.11 -m venv "$VENV_DIR"
    echo "    Created virtual environment at $VENV_DIR"
fi

# ── Step 3: Activate virtual environment ────────────────────────────

echo ""
echo "==> Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "    Using: $(python --version) from $(which python)"

# ── Step 4: Install dependencies ───────────────────────────────────

echo ""
echo "==> Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── Step 5 & 6: Run migrations and seed database ───────────────────
# Delegates to db-bootstrap.sh for Alembic migrations and database seeding.

echo ""
"$SCRIPT_DIR/db-bootstrap.sh"
