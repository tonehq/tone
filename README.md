# 🎙️ Open Source AI Voice Agent Builder

[License: MIT](https://opensource.org/licenses/MIT)
[Python](https://www.python.org/downloads/)
[FastAPI](https://fastapi.tiangolo.com/)
[React](https://reactjs.org/)
[PostgreSQL](https://www.postgresql.org/)

> **The open source alternative to Retell, Synthflow, and Vapi** - Build reliable, observable, and easily testable AI voice agents with a focus on developer experience.

## ✨ Overview

This project is an open source AI Voice agent Builder that empowers developers and businesses to create sophisticated voice agents without vendor lock-in. Built with reliability, observability, and real-time testing at its core.

### 🎯 Vision

We believe in democratizing AI voice technology through open source solutions. Our platform provides:

- **Reliability First**: Rock-solid voice agent infrastructure
- **Full Observability**: Complete visibility into agent performance and conversations
- **Real-time Testing**: Built-in testing capabilities for seamless development
- **No Vendor Lock-in**: Own your data and infrastructure

### 🛠️ Roadmap

#### 🎯 Phase 1: Foundation (Current)

- [x] Basic agent creation and management
- [x] Tool calling infrastructure
- [x] Call management system
- [x] Multi-tenant architecture

#### 🎯 Phase 2: Enhanced Capabilities

- [ ] **Quick AI Phone and Web Voice agents** - Rapid deployment templates
- [ ] **Enhanced Tool calling** - More integrations and custom tools
- [ ] **End to end real time testing functionalities** - Built-in voice agent testing capabilities
- [ ] **Multilingual Support** - Support for multiple languages
- [ ] **Model Routing** - Connect with different LLMs (OpenAI, Anthropic, etc.)

#### 🎯 Phase 3: Workflow & Integration

- [ ] **AI Conversation Workflow Builder** - Visual workflow designer
- [ ] **MCP Actions Support** - Model Context Protocol integration
- [ ] **Multiple STT/TTS Models** - Choice of speech recognition and synthesis
- [ ] **Speech-to-Speech Models** - Direct speech-to-speech capabilities

#### 🎯 Phase 4: Ecosystem

- [ ] **CRM Integrations** - Salesforce, HubSpot, Pipedrive
- [ ] **Productivity Integrations** - Google Sheets, Cal.com, Notion
- [ ] **N8N Integration** - Workflow automation platform
- [ ] **Advanced Analytics** - Comprehensive conversation analytics

## 🏗️ Architecture

### Tech Stack

**Frontend**

- Next.js 15 (App Router) + React 19 + TypeScript
- Deployed on Vercel

**Backend**

- FastAPI (Python 3.10+)
- PostgreSQL with SQLAlchemy ORM
- Alembic for database migrations
- Infisical for secrets management

**Infrastructure**

- Docker containerization
- Kubernetes deployment
- Cloudflare R2 for file storage
- Environment-based deployments (dev, staging, production)

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher (download from [python.org](https://www.python.org/downloads/). Verify with `python --version`)
- Node.js 18.18+ (Node 20+ recommended for Next.js 15)
- PostgreSQL 14+
- Docker (optional)

### Installation

1. **Clone the repository**
  ```bash
   git clone https://github.com/tonehq/tone.git
   cd tone
  ```
2. **Set up your `.env` file**
  ```bash
   # Create a .env file in the project root with:
   #   DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>
   #   JWT_SECRET_KEY=<your-secret-key>
   #   ENCRYPTION_KEY=<your-encryption-key>
   #
   # Infisical (used by bootstrap/dev-bootstrap.sh and to run the app):
   #   INFISICAL_PROJECT_ID=<your-project-id>
   #   INFISICAL_ENV=<staging|dev|production>
   #
   # Cloudsmith (private tone-pipecat package):
   #   PIP_EXTRA_INDEX_URL=https://<user>:<token>@dl.cloudsmith.io/<entitlement>/tonehq/tone/python/simple/
   #
   # Optional: provider API keys (OPENAI_API_KEY, DEEPGRAM_API_KEY, etc.)
  ```
3. **Install the Infisical CLI and log in**
  ```bash
   # macOS
   brew install infisical/get-cli/infisical

   # Linux
   curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | sudo -E bash
   sudo apt install -y infisical

   # Log in once (opens a browser)
   infisical login
  ```
4. **Export the Cloudsmith URL** (required for the private `tone-pipecat` package)
  ```bash
   # Get the real URL from Cloudsmith → tonehq/tone repo → Set Me Up → Python.
   export PIP_EXTRA_INDEX_URL="https://<user>:<token>@dl.cloudsmith.io/<entitlement>/tonehq/tone/python/simple/"
  ```

#### Option A — One-command setup (recommended)

Runs Python install, venv, dependencies, migrations, procrastinate schema, DB seed, Node.js install, and frontend `npm install` — all in one go.

```bash
./bootstrap/dev-bootstrap.sh
```

> Adding another organization on an already-initialized DB? See
> **Adding a new organization** below.

When it finishes, start the servers:

```bash
# Backend (secrets are injected by infisical run)
source venv/bin/activate
infisical run --projectId "$INFISICAL_PROJECT_ID" --env="$INFISICAL_ENV" -- \
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in a separate terminal)
cd frontend && npm run dev
```

> **Local development: use `--env=local`, not `--env=staging`.** The auth token
> rides in an httpOnly cookie whose `Domain`/`Secure` attributes come from
> Infisical. Deployed envs set `COOKIE_DOMAIN=.trytone.ai` and `COOKIE_SECURE=true`,
> which a browser **cannot store for `http://localhost`** — so login succeeds (200)
> but the cookie is dropped, `middleware.ts` sees no session, and every route
> bounces back to `/login?next=…`. The `local` Infisical environment overrides
> these for local dev (`COOKIE_DOMAIN=localhost`, `COOKIE_SECURE=false`, `ENV=local`,
> `CORS_ALLOW_ORIGINS=http://localhost:3000`):
>
> ```bash
> infisical run --projectId "$INFISICAL_PROJECT_ID" --env=local -- \
>     uvicorn main:app --reload --host 0.0.0.0 --port 8000
> ```
>
> If you previously logged in against staging secrets, clear existing `localhost`
> cookies before retrying — a stale `Secure`/`.trytone.ai` cookie can linger.

#### Option B — Manual setup

Prefer to run each step yourself? Follow the manual backend and frontend steps below.

1. **Backend Setup**
  ```bash
   # Create virtual environment (requires Python 3.10+)
   python -m venv venv

   # Activate the virtual environment
   source venv/bin/activate          # macOS / Linux
   # venv\Scripts\activate           # Windows (PowerShell/CMD)

   # Configure Cloudsmith index for the private `tone-pipecat` package.
   # Get the entitlement token from Cloudsmith (tonehq/tone repo).
   export PIP_EXTRA_INDEX_URL="https://<user>:<token>@dl.cloudsmith.io/<entitlement>/tonehq/tone/python/simple/"

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment variables
   # Create a .env file in the project root with the required configuration:
   #   DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>
   #   JWT_SECRET_KEY=<your-secret-key>
   #   ENCRYPTION_KEY=<your-encryption-key>

   # Run database migrations
   alembic upgrade head

   # Apply the Procrastinate ingestion-queue schema (one-time, per environment).
   # Required before the document-ingestion worker can run.
   PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply

   # Seed service providers, models, and voices
   python dev/seed.py

   # Start the backend server with uvicorn (auto-reload for development)
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload

   # Enterprise edition
   # uvicorn main_ee:app --host 0.0.0.0 --port 8000 --reload
  ```
   **Seed Data (`dev/seed.py`)**
   The seed script sets up your initial data — it creates an owner user, organization, and populates all supported service providers (LLM, STT, TTS), their models, and voices from `dev/dev-data.json`.
   When you run `python dev/seed.py`, it will interactively prompt you for:
  - **Organization name** — your organization/workspace name
  - **Owner email** — the admin user's email (used for login)
  - **Password** — must be 8+ characters with uppercase, lowercase, digit, and special character
   To auto-populate API keys for providers during seeding, set the corresponding environment variables in your `.env` file before running the script. For example:
   Any provider whose API key env var is not set will be seeded without a key — you can add keys later through the UI.
2. **Frontend Setup**
  ```bash
   cd frontend

   # Install dependencies
   npm install

   # Start the frontend dev server (Next.js + Turbopack on :3000)
   npm run dev
  ```
3. **Access the application**
  - Frontend: [http://localhost:3000](http://localhost:3000)
  - Backend API: [http://localhost:8000](http://localhost:8000)
  - API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Adding a new organization

Use `bootstrap/org-bootstrap.sh` when you need to add another organization to
an **already-initialized** database (migrations + provider catalogue already
seeded via `bootstrap/db-bootstrap.sh`). Creates the user + org + member,
seeds `app_integrations` and built-in tools for **only the new org**, and
optionally attaches provider API keys pulled from environment variables.

```bash
# Prompts for org name, owner email, password. Skips API keys.
./bootstrap/org-bootstrap.sh

# Same, but also seeds provider API keys from env vars
# (OPENAI_API_KEY, DEEPGRAM_API_KEY, ELEVENLABS_API_KEY, etc.)
./bootstrap/org-bootstrap.sh --api-keys-from-env

# Run with Infisical-injected secrets (recommended — matches how the app runs)
infisical run --projectId "$INFISICAL_PROJECT_ID" --env="$INFISICAL_ENV" -- \
    ./bootstrap/org-bootstrap.sh --api-keys-from-env
```

Pre-flight checks it runs before touching the DB:
- ❌ Fails fast if the global provider catalogue is empty
  (`run ./bootstrap/db-bootstrap.sh first`)
- ❌ Fails fast if the owner email or org slug is already taken

**Which DB does it target?** The same one the app uses — resolved via
`shared/config.py` from `DATABASE_URL` in your `.env` (or Infisical if you
wrap with `infisical run`). Double-check by running:

```bash
python -c "from shared.config import settings; print(settings.DATABASE_URL)"
```

### Docker Setup

```bash
# Build the backend image
docker build -f core/Dockerfile -t tone .

# Run it (expects DATABASE_URL and other env vars to be provided)
docker run --rm -p 8000:8000 --env-file .env tone
```

## 📚 Documentation

### API Structure

Our codebase follows a clean architecture pattern:

```
core/
├── api/v1/              # FastAPI route handlers
│   ├── agents.py
│   ├── auth.py
│   ├── channels.py
│   ├── models.py
│   ├── organizations.py
│   ├── service_providers.py
│   └── voices.py
├── services/            # Business logic layer
│   ├── agent_service.py
│   ├── agent_factory_service.py
│   ├── voice_service.py
│   ├── channel_service.py
│   └── model_service.py
├── models/              # SQLAlchemy ORM models
│   ├── agent.py
│   ├── organization.py
│   ├── service_provider.py
│   ├── voice.py
│   └── user.py
├── middleware/           # Auth & request middleware
│   └── auth.py
├── utils/               # Utility functions
│   └── encryption.py    # AES encryption for API keys
├── bot.py               # Voice pipeline entry point
└── database/            # DB session & connection
dev/
├── seed.py              # Data seeding script
└── dev-data.json        # Provider/model/voice definitions
```

### Key Concepts

- **Agents**: AI voice agents with configurable personalities and capabilities
- **Tools**: External integrations and API calls that agents can use
- **Calls**: Voice call sessions with transcription and metadata
- **Organizations**: Multi-tenant structure for team collaboration

⭐ **Star this repository** if you find it useful!

Made with ❤️ by the open source community