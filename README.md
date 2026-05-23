# 🎙️ Open Source AI Voice Agent Builder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

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
- React 18+ with modern hooks
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
- Node.js 16+
- PostgreSQL 14+
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-voice-agent-builder.git
   cd ai-voice-agent-builder
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment (requires Python 3.10+)
   python -m venv venv

   # Activate the virtual environment
   source venv/bin/activate          # macOS / Linux
   # venv\Scripts\activate           # Windows (PowerShell/CMD)

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment variables
   # Create a .env file in the project root with the required configuration:
   #   DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>
   #   JWT_SECRET_KEY=<your-secret-key>
   #   ENCRYPTION_KEY=<your-encryption-key>

   # Run database migrations
   alembic upgrade head

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
   ```bash
   OPENAI_API_KEY=sk-...
   DEEPGRAM_API_KEY=...
   ELEVENLABS_API_KEY=...
   CARTESIA_API_KEY=...
   ```
   Any provider whose API key env var is not set will be seeded without a key — you can add keys later through the UI.

3. **Frontend Setup**
   ```bash
   cd frontend

   # Install dependencies
   npm install

   # Start the frontend dev server (Next.js + Turbopack on :3000)
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up -d

# The application will be available at:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
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