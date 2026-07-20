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

# Procrastinate ingestion-queue schema (ONE-TIME, PER ENVIRONMENT)
# Required before the document-ingestion worker can run. Not managed by alembic —
# run this once against each environment's DB (local/staging/prod) before deploy.
# Until applied, the in-process worker error-loops on a missing table.
PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply

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

- **Service layer & reuse (single source of truth):** Business logic lives in a service extending `BaseService` — **never in routers/controllers**. Routers only: parse/validate input → authorize → call a service method → shape the response. Any behavior that is (or will be) invoked from more than one place — another router, a worker, a CLI, a test — MUST be a shared service method or a helper in `core/services/common/` / `core/utils/`, called by everyone; do not copy-paste or re-implement the same logic in a second location. Before writing new logic, search for an existing service/helper and extend it; when the same functionality is needed from anywhere, factor it out so there is exactly one implementation. On the frontend the mirror rule holds: shared UI → `@/components/shared`, shared logic → `@/hooks`/`@/lib`/`@/utils`, all HTTP through `@/services` / `@/lib/api` hooks — never duplicate fetch/format/validation per page. Follow the rule of three (extract on the 3rd occurrence) but extract by *responsibility*, not by shape. See the reusable-functions catalog below and `docs/code-review/`.
- **Auth pattern:** Routes use FastAPI dependency injection — `require_authenticated`, `require_admin_or_owner`, `require_org_member`
- **Encryption:** API keys stored AES-encrypted in DB (`core/utils/encryption.py`)
- **Multi-tenancy:** Core edition defaults to single-tenant (`IS_MULTI_TENANT=false`, all users share `DEFAULT_ORG_ID`)
- **DB models:** UUID primary keys alongside integer IDs; JSONB columns for flexible metadata/settings
- **Config:** Settings loaded from Infisical (if `USE_INFISICAL=true`) or `.env` with fallback defaults
- **Logging & observability:** Use the shared loguru `logger`. Every error-handling `except` must capture a full traceback via `logger.exception(...)` (never message-only `logger.error("...", e)` or `print`); expected control-flow `except`s (parse fallbacks, cache miss, optional import, hot-loop/per-frame) use `logger.debug`; never silently swallow and never swallow `asyncio.CancelledError`. Prefix logs with a context tag (`[bot]`, `[inbound]`, `[outbound]`, service name); correlate by the per-call `trace_id`. Never call `logger.add/remove/configure` outside `core/logging.py` (it owns the single sink; pipecat shares the same loguru singleton). Per-call verbosity is DB-driven — `agent.log_level > organization.log_level > env LOG_LEVEL > INFO`, resolved only in `core/services/log_level_resolver.py` and applied by `run_bot` via `setup_logging(level=...)`; never read the `log_level` columns directly. Full reference: `docs/LOGGING_OBSERVABILITY.md`.

### Common reusable functions (Contacts Directories module — reuse, don't re-implement)

Registered so future work discovers them (paths are import targets):
- **`require_admin_or_owner`** (`core/middleware/auth.py`) — shared admin/owner route guard; enforces `claims.role in {"admin","owner"}`. Use on every admin-gated route; never re-check roles inline.
- **`apply_search_sort_pagination`** (`core/services/common/list_query.py`) — search + whitelisted sort + paginate a scoped query → `(rows, total)`. Use in every `POST /…/list`.
- **`BaseService.get_or_404`** (`core/services/base.py`) — org-scoped, soft-delete-aware fetch-or-404.
- **`build_contact_field_json_schema` / `make_contact_metadata_validator` / `validate_contact_metadata`** (`core/services/contacts/contact_metadata_validation.py`) — `SchemaField`s → JSON-Schema + Draft7 validator + per-row errors (manual create, multi-add, sync validation).
- **`map_source_row_to_contact`** (`core/services/contact_ingestion/contact_mapping.py`) — `source_key→field_name` map + type coercion (null = identity).
- **`upsert_contact`** (`core/services/contacts/contact_upsert.py`) — upsert by `(directory_id, external_id)` → `(contact, action)`; sets `sync_id`.
- **`ContactService.list_contact_ids_in_directories`** (`core/services/contacts/contact_service.py`) — active contact ids across directories (agent-assign expansion).
- **`get_contact_source(datasource)`** (`core/services/contact_ingestion/__init__.py`) — datasource-type → `ContactSource` factory.
- **`run_contact_sync` / `enqueue_contact_sync[_sync]`** (`core/services/contacts/contact_sync_service.py`, `core/services/ingestion_queue.py`) — the single sync pipeline + Procrastinate deferral.
- **`create_default_datasource`** (`core/services/contacts/contact_directory_service.py`) — provision the CSV datasource on directory create (no schema is auto-created; `default_schema_id` is optional/user-selected).
- **`summarize_directory_deletion` / `hard_delete_directory_and_children`** (`core/services/contacts/directory_delete.py`) — delete-impact counts; FK-safe hard delete (cancels queued dial jobs, keeps org schemas, detaches syncs).

### Frontend: shared components

- **Buttons:** Use `CustomButton` from `@/components/shared` only. Do not use native `<button>` or `Button` from `@/components/ui/button` in app/feature code (exception: inside `CustomButton.tsx` itself).
- **Other UI:** Prefer shared components (`CustomModal`, `CustomTable`, `TextInput`, `SelectInput`, `CustomTab`, `CustomLink`, etc.) over raw `@/components/ui/*` or native elements. Use `@/components/ui/*` only when building or composing shared components.
- **Date/time selection:** Use the shared `DateTimePicker` (single instant → UTC ISO) or `DateRangePicker` (range) for ALL date/time input. Do NOT use native `<input type="date"/datetime-local">` or other calendar libraries in app/feature code.
- See `.cursor/rules/shared-components.mdc` for full rule and exceptions.

## Code Review Rules

Before reviewing any diff, writing new code, or opening a PR, follow the repo's code-review
rulebook in `docs/code-review/`. These rules are mandatory for all agents:

- `docs/code-review/README.md` — shared philosophy, severity labels (`[blocker]`/`[should]`/`[nit]`/`[question]`/`[praise]`), universal checklist, and the DRY/reuse doctrine (rule of three; extract by responsibility, not shape).
- `docs/code-review/frontend-nextjs-typescript.md` — Next.js 15 / React 19 / TypeScript rules.
- `docs/code-review/backend-python-fastapi.md` — FastAPI / SQLAlchemy 2.0 / Alembic rules.

Do not comment on style the linter/formatter already fixes (ESLint+Prettier on FE, Ruff on BE) —
focus on correctness, security, design, and tests. Always-check blockers:
- **Reuse & layering (both stacks):** flag logic that belongs in a service but sits in a router/component; flag duplicated logic that should be a shared service method / helper / hook (especially the *same* functionality re-implemented in a second call site instead of calling the existing one); flag a new endpoint/component that rebuilds something a shared function already provides. The fix is "call the shared service", not "copy it here."
- **FE:** no type-erasing `any`/`!`; correct `useEffect` deps (`exhaustive-deps` is OFF — the reviewer is the guard); stable list keys; no secrets in the client bundle; server state in TanStack Query; buttons use `CustomButton` and prefer shared components; HTTP via `@/services` / `@/lib/api` hooks.
- **BE:** every route has the right auth guard; **every query is tenant/org-scoped** (no IDOR); no raw/interpolated SQL; schema changes ship a safe Alembic migration; secrets stay AES-encrypted and are never logged; no blocking I/O in async paths; logic lives in a `BaseService`, not routers, and is reused (not duplicated) wherever the same behavior is needed; **every `except` logs a full traceback (`logger.exception`) — no silent swallow, no message-only error log, `CancelledError` never dropped** (see Logging & observability above).

New behavior needs tests; bug fixes need a regression test.


##SKILLS:

-For generating code for crud operations, use skills from:
.claude/skills/generate-code/crud-operations-skills.md

-For generating postman collection
.claude/skills/postman/SKILL.md

-For generating test cases
.claude/skills/test-cases/SKILL.md

-For setting up a new deployment environment (creates branch + k8s manifests + GitHub Actions workflow)
.claude/skills/setup-new-deployment/SKILL.md

-For generating Kubernetes deployment manifests only
.claude/skills/generate-kubernetes-deployment/SKILL.md

-For generating GitHub Actions CI/CD workflow only
.claude/skills/generate-github-actions/SKILL.md

-For provisioning a Neon database and configuring Infisical secrets for a new environment
.claude/skills/provisioning-db/SKILL.md

-For provisioning a Vultr Kubernetes Engine (VKE) cluster with node pools and add-ons
.claude/skills/provisioning-cluster/provisioning-vultr/SKILL.md

-For complete end-to-end environment provisioning (DB + Secrets + Cluster + Manifests + Migrations in one run)
.claude/skills/provisioning-environment/SKILL.md

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **havana** (12473 symbols, 31301 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
3. `READ gitnexus://repo/havana/process/{processName}` — trace the full execution flow step by step
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
| `gitnexus://repo/havana/context` | Codebase overview, check index freshness |
| `gitnexus://repo/havana/clusters` | All functional areas |
| `gitnexus://repo/havana/processes` | All execution flows |
| `gitnexus://repo/havana/process/{name}` | Step-by-step execution trace |

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

<!-- gitnexus:end -->
