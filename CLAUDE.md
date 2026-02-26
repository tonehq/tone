# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tone is an open-source AI Voice Agent Builder (alternative to Retell, Synthflow, Vapi). It lets users create voice agents backed by configurable LLM/STT/TTS pipelines using the Pipecat framework.

## Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (Core edition)
python main.py                    # Starts uvicorn on :8000

# Run the server (Enterprise edition)
python main_ee.py

# Database migrations
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration

# Seed service providers and models
python dev/seed.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev          # Dev server on :3000 (Next.js + Turbopack)
npm run build        # Production build
npm run lint         # ESLint
npm run lint:fix     # ESLint with auto-fix
npm run format       # Prettier
```

### Docker
```bash
# Backend image
docker build -f core/Dockerfile -t tone .
# Runs: uvicorn main:app --host 0.0.0.0 --port 8000
```

## Architecture

### Backend (Python/FastAPI)

**Two editions** share the same core: `main.py` (Core) and `main_ee.py` (Enterprise). Both mount routers under `/api/v1`.

**Layered architecture:**
- `core/api/v1/` — FastAPI routers (thin HTTP handlers, use `Depends(get_db)` and `Depends(require_authenticated)`)
- `core/services/` — Business logic layer; all services extend `BaseService` with DB session access
- `core/models/` — SQLAlchemy ORM models; all extend `TimestampModel` with UUID + integer PK
- `core/middleware/auth.py` — JWT auth with `JWTManager`, `JWTClaims`, role-based guards
- `core/config.py` — `Settings` class loading from Infisical or `.env`
- `core/context.py` — `TenantContext` for request-scoped multi-tenancy

**Voice pipeline (the core product):**
1. `core/bot.py` — Entry point (`run_bot`), called by transports (Daily WebRTC, Twilio, WebSocket)
2. `core/services/agent_factory_service.py` — Builds pipelines: reads agent config from DB, decrypts provider API keys, instantiates Pipecat LLM/STT/TTS services
3. `core/services/voice_service.py` — Fetches available voices from TTS providers

**Pipeline flow:** Transport Input → STT → LLM → TTS → Transport Output

### Frontend (Next.js 15 / React 19 / TypeScript)

- App Router in `frontend/src/app/`
- MUI 6 component library
- Jotai for state management
- Axios-based API services in `frontend/src/services/`
- Pre-commit hooks via Husky + lint-staged (ESLint + Prettier on `.ts`/`.tsx`)

### Pipecat Integration

The `pipecat/` directory is a custom fork (`tonehq/pipecat`) of the Pipecat AI framework. It provides the actual voice pipeline runtime with 55+ provider integrations across LLM, STT, and TTS categories.

### Data Seeding

`dev/seed.py` reads `dev/dev-data.json` to populate ServiceProvider and Model records. Provider API keys are loaded from environment variables specified in each provider's config.

## Key Conventions

- **Auth pattern:** Routes use FastAPI dependency injection — `require_authenticated`, `require_admin_or_owner`, `require_org_member`
- **Encryption:** API keys stored AES-encrypted in DB (`core/utils/encryption.py`)
- **Multi-tenancy:** Core edition defaults to single-tenant (`IS_MULTI_TENANT=false`, all users share `DEFAULT_ORG_ID`)
- **DB models:** UUID primary keys alongside integer IDs; JSONB columns for flexible metadata/settings
- **Config:** Settings loaded from Infisical (if `USE_INFISICAL=true`) or `.env` with fallback defaults

### Frontend: shared components

- **Buttons:** Use `CustomButton` from `@/components/shared` only. Do not use native `<button>` or `Button` from `@/components/ui/button` in app/feature code (exception: inside `CustomButton.tsx` itself).
- **Other UI:** Prefer shared components (`CustomModal`, `CustomTable`, `TextInput`, `SelectInput`, `CustomTab`, `CustomLink`, etc.) over raw `@/components/ui/*` or native elements. Use `@/components/ui/*` only when building or composing shared components.
- See `.cursor/rules/shared-components.mdc` for full rule and exceptions.


##SKILLS:

-For generating code for crud operations, use skills from:
.claude/skills/generate-code/crud-operations-skills.md
