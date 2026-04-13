# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tone is an open-source AI Voice Agent Builder (alternative to Retell, Synthflow, Vapi). It lets users create voice agents backed by configurable LLM/STT/TTS pipelines using the Pipecat framework.

## Commands

### Backend
```bash
# Auth for the private tone-pipecat package (Cloudsmith PyPI).
# Get this URL from Cloudsmith → entitlement token for the tonehq/tone repo.
export PIP_EXTRA_INDEX_URL="https://<user>:<token>@dl.cloudsmith.io/<entitlement>/tonehq/tone/python/simple/"

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

-For generating postman collection
.claude/skills/postman/SKILL.md

-For generating test cases
.claude/skills/test-cases/SKILL.md

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **tone** (12696 symbols, 50186 relationships, 293 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/tone/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/tone/context` | Codebase overview, check index freshness |
| `gitnexus://repo/tone/clusters` | All functional areas |
| `gitnexus://repo/tone/processes` | All execution flows |
| `gitnexus://repo/tone/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |
| Work in the Foundational area (1237 symbols) | `.claude/skills/generated/foundational/SKILL.md` |
| Work in the Tests area (654 symbols) | `.claude/skills/generated/tests/SKILL.md` |
| Work in the Services area (447 symbols) | `.claude/skills/generated/services/SKILL.md` |
| Work in the Cartesia area (347 symbols) | `.claude/skills/generated/cartesia/SKILL.md` |
| Work in the Test-cases area (250 symbols) | `.claude/skills/generated/test-cases/SKILL.md` |
| Work in the Realtime area (194 symbols) | `.claude/skills/generated/realtime/SKILL.md` |
| Work in the Daily area (183 symbols) | `.claude/skills/generated/daily/SKILL.md` |
| Work in the V1 area (168 symbols) | `.claude/skills/generated/v1/SKILL.md` |
| Work in the Aggregators area (161 symbols) | `.claude/skills/generated/aggregators/SKILL.md` |
| Work in the Processors area (145 symbols) | `.claude/skills/generated/processors/SKILL.md` |
| Work in the Frameworks area (108 symbols) | `.claude/skills/generated/frameworks/SKILL.md` |
| Work in the Smallwebrtc area (108 symbols) | `.claude/skills/generated/smallwebrtc/SKILL.md` |
| Work in the Openai_realtime_beta area (102 symbols) | `.claude/skills/generated/openai-realtime-beta/SKILL.md` |
| Work in the Ui area (94 symbols) | `.claude/skills/generated/ui/SKILL.md` |
| Work in the Frames area (94 symbols) | `.claude/skills/generated/frames/SKILL.md` |
| Work in the Websocket area (88 symbols) | `.claude/skills/generated/websocket/SKILL.md` |
| Work in the Pipeline area (85 symbols) | `.claude/skills/generated/pipeline/SKILL.md` |
| Work in the Scripts area (77 symbols) | `.claude/skills/generated/scripts/SKILL.md` |
| Work in the Google area (76 symbols) | `.claude/skills/generated/google/SKILL.md` |
| Work in the Heygen area (70 symbols) | `.claude/skills/generated/heygen/SKILL.md` |

<!-- gitnexus:end -->
