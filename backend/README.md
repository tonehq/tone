# 🎙️ Open Source AI Voice Agent Builder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
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
- FastAPI (Python 3.13)
- PostgreSQL with SQLAlchemy ORM
- Alembic for database migrations
- Infiscal for secrets management

**Infrastructure**
- Docker containerization
- Kubernetes deployment
- Cloudflare R2 for file storage
- Environment-based deployments (dev, staging, production)

## 🚀 Quick Start

### Prerequisites

- Python 3.13
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
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration
   
   # Run database migrations
   alembic upgrade head
   
   # Start the backend server
   python app.py --env=dev
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm start
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
src/
├── controller/          # HTTP route handlers
│   ├── agent_controller.py
│   ├── call_controller.py
│   └── tool_controller.py
├── services/           # Business logic layer
│   ├── agent_service.py
│   ├── call_service.py
│   └── tool_service.py
├── models/            # Database models
│   ├── agent_model.py
│   ├── call_model.py
│   └── tool_model.py
└── utils/             # Utility functions
    ├── r2.py         # Cloudflare R2 integration
    └── secrets.py    # Infiscal secrets management
```

### Key Concepts

- **Agents**: AI voice agents with configurable personalities and capabilities
- **Tools**: External integrations and API calls that agents can use
- **Calls**: Voice call sessions with transcription and metadata
- **Organizations**: Multi-tenant structure for team collaboration



⭐ **Star this repository** if you find it useful!

Made with ❤️ by the open source community