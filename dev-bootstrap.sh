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
#   6. Applies Procrastinate ingestion-queue schema
#   7. Seeds the database with providers, models, voices, and first user
#   8. Installs Node.js 20 (if missing) and frontend npm dependencies

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

# ── Preflight: Cloudsmith URL ──────────────────────────────────────
# Fail fast so we don't install Python/venv before discovering the
# private-package URL isn't set.

if [ -z "${PIP_EXTRA_INDEX_URL:-}" ]; then
    echo ""
    echo "==> Cloudsmith access is required to install the private tone-pipecat package."
    echo ""
    echo "    Please configure it by exporting PIP_EXTRA_INDEX_URL, then re-run this script:"
    echo ""
    echo "      export PIP_EXTRA_INDEX_URL=\"https://<user>:<token>@dl.cloudsmith.io/<entitlement>/tonehq/tone/python/simple/\""
    echo ""
    echo "    Get the real URL from Cloudsmith → tonehq/tone repo → Set Me Up → Python."
    exit 1
fi

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

REQUIRED_PY="3.11"
if [ -d "$VENV_DIR" ]; then
    VENV_PY_VERSION="$("$VENV_DIR/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "unknown")"
    if [ "$VENV_PY_VERSION" != "$REQUIRED_PY" ]; then
        echo "    Existing venv uses Python $VENV_PY_VERSION; required $REQUIRED_PY. Recreating..."
        rm -rf "$VENV_DIR"
        python3.11 -m venv "$VENV_DIR"
        echo "    Recreated virtual environment at $VENV_DIR"
    else
        echo "    Virtual environment already exists at $VENV_DIR (Python $VENV_PY_VERSION)"
    fi
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

# ── Step 5, 6 & 7: Run migrations, procrastinate schema, and seed ──
# Delegates to db-bootstrap.sh.

echo ""
"$SCRIPT_DIR/db-bootstrap.sh"

# ── Step 8: Frontend setup ─────────────────────────────────────────
# Ensures Node.js 18.18+ is installed (installs Node 20 via brew/apt if not
# found or too old) and installs npm dependencies in frontend/.

echo ""
echo "==> Setting up frontend..."

REQUIRED_NODE_MAJOR=18
REQUIRED_NODE_MINOR=18

need_node_install=false
if command -v node &>/dev/null; then
    NODE_VERSION="$(node --version | sed 's/^v//')"
    NODE_MAJOR="${NODE_VERSION%%.*}"
    NODE_MINOR="$(echo "$NODE_VERSION" | cut -d. -f2)"
    if [ "$NODE_MAJOR" -lt "$REQUIRED_NODE_MAJOR" ] || \
       { [ "$NODE_MAJOR" -eq "$REQUIRED_NODE_MAJOR" ] && [ "$NODE_MINOR" -lt "$REQUIRED_NODE_MINOR" ]; }; then
        echo "    Node.js $NODE_VERSION is too old (need ${REQUIRED_NODE_MAJOR}.${REQUIRED_NODE_MINOR}+). Installing Node 20..."
        need_node_install=true
    else
        echo "    Node.js already installed: v$NODE_VERSION"
    fi
else
    echo "    Node.js not found. Installing Node 20..."
    need_node_install=true
fi

if [ "$need_node_install" = true ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &>/dev/null; then
            echo "ERROR: Homebrew not found. Install it from https://brew.sh"
            exit 1
        fi
        brew install node@20
        brew link --overwrite --force node@20
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
    else
        echo "ERROR: Unsupported OS. Please install Node.js 18.18+ manually."
        exit 1
    fi
fi

echo ""
echo "==> Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
npm install
cd "$SCRIPT_DIR"

echo ""
echo "==> Full setup complete."
echo "    Start backend:  python main.py"
echo "    Start frontend: cd frontend && npm run dev"
