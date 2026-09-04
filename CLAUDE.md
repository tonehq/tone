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
- **Build reusable, generic, extensible structures FIRST (mandatory for every new feature):** design new work as reusable classes/functions and shared building blocks from the start — not a one-off implementation you refactor later. Concretely: (1) **Model the common shape** — normalize every input into ONE data model (e.g. `ParsedContact`) so all downstream code is source-agnostic. (2) **One pipeline, many inputs** — parsing/looping/validating/processing lives in ONE place that every source and destination reuses; adding a new input is a new small class, never a new copy of the loop. Follow the reference framework in `core/services/contact_ingestion/` (`ContactSource` ABC + `select_source_for_upload` factory → `RecordParser` common `Parse → loop → Validate` → `RecordValidator`/`CompositeValidator` extensible rules → shared destination like `create_contacts` (Create+Assign) / `schedule_calls_for_contacts` (Schedule)). (3) **Extensible by extension, not modification** — new data source = new ABC subclass + factory entry; new rule = new validator added to a composite/registry; **never edit the core loop/pipeline to bolt on a case.** (4) **Skip only the step you don't need** — e.g. an API with already-structured records calls the SAME loop/validator via `RecordParser.process(records)` (skipping Parse); it never re-implements validation. (5) **Route through existing shared functions** — reuse the established Schedule→Assign→Create path (`OutboundCallService.create_outbound_calls_from_rows` → `ContactService.create_contacts(agent_id=)` → `schedule_calls_for_contacts`) instead of duplicating create/assign/schedule logic. Register every new reusable primitive in the "Common reusable functions" catalog below so future work discovers it. If a feature can't reuse an existing abstraction, extract a new generic one (ABC/protocol + composable pieces) rather than writing a bespoke flow.
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
- **`build_contact_field_json_schema` / `make_contact_metadata_validator` / `validate_contact_metadata` / `normalize_contact_metadata_dates`** (`core/services/contacts/contact_metadata_validation.py`) — `SchemaField`s → JSON-Schema + Draft7 validator + per-row errors (manual create, multi-add, sync validation). `normalize_contact_metadata_dates(metadata, fields)` coerces managed `date`/`datetime` fields to a UTC ISO string (reusing `parse_datetime_value`) so manual create/update store the SAME shape as the CSV sync path — returns `(normalized, errors)`; manual entry rejects unparseable values (the DateTimePicker sends ISO, so `datetime_format`/`timezone` are CSV-only).
- **`map_source_row_to_contact`** (`core/services/contact_ingestion/contact_mapping.py`) — `source_key→field_name` map + type coercion (null = identity).
- **`map_rows_to_parsed_contacts`** (`core/services/contact_ingestion/row_mapping.py`) — the ONE `header→ParsedContact` mapper (header normalization, reserved-field promotion, `external_id` synthesis). Shared by `CSVContactSource` and `ExcelContactSource` so a CSV and its equivalent `.xlsx` produce identical contacts; per-format classes only decode bytes → string rows and call this.
- **Parser + Validator framework** (`core/services/contact_ingestion/pipeline.py`, `validation.py`) — the ONE `Parse → loop → Validate` implementation over the common `ParsedContact` model, reusable for ANY data source (CSV/Excel/REST/API/…) and destination. `RecordParser(validator).parse(source, raw)` parses+loops+validates a raw blob; `RecordParser(validator).process(records)` runs the SAME loop+validate on already-structured records (skip Parse). Both partition `ParseResult{valid, invalid, total}` (unlimited by default — pass `max_records` only for a hard cap). `parsed_contact_to_row` converts a `ParsedContact` to the `create_contacts` row shape. Validators are extensible: `RecordValidator` (ABC) + `CompositeValidator` (add rules dynamically, no loop change) + built-ins `PhoneNumberValidator` / `RequiredIdentityValidator` / `SchemaMetadataValidator` (reuses `make_contact_metadata_validator`). **`build_contact_validator(schema_fields=None, *, require_phone=False)`** is the ONE place validation is composed — every RecordParser entrypoint calls it (never rebuild a `CompositeValidator` at a call site): `require_phone=True` (dialing) → phone-required (satisfies identity); else name-or-phone identity; a non-empty `schema_fields` adds schema-metadata validation, skipped when there's no schema. Every entrypoint uses it: the file flow (`POST /outbound-call/create-from-file`) does Parse→loop→Validate with `build_contact_validator(require_phone=True)`; the **Contact-Create API** (`ContactService.create_contacts`) skips Parse and calls `RecordParser.process` with `build_contact_validator(schema_fields)` — both then go Schedule → Assign → Create (`create_outbound_calls_from_rows` → `create_contacts(agent_id=)` → `schedule_calls_for_contacts`). Add a new source/rule here, never a new loop. No per-request row caps (MAX_BULK / MAX_CREATE_ROWS removed).
- **`select_source_for_upload(raw)`** (`core/services/contact_ingestion/__init__.py`) — pick a `ContactSource` for an uploaded file by sniffing magic bytes: `.xlsx` (ZIP) → `ExcelContactSource`, legacy `.xls` (OLE2) → friendly `ValueError`, else → `CSVContactSource`. Used by `run_contact_sync` for csv-type (upload) datasources; REST/other datasource types still use `get_contact_source`.
- **`upsert_contact`** (`core/services/contacts/contact_upsert.py`) — upsert by `(directory_id, external_id)` → `(contact, action)`; sets `sync_id`.
- **`ContactService.list_contact_ids_in_directories`** (`core/services/contacts/contact_service.py`) — active contact ids across directories (agent-assign expansion).
- **`get_contact_source(datasource)`** (`core/services/contact_ingestion/__init__.py`) — datasource-type → `ContactSource` factory.
- **`run_contact_sync` / `enqueue_contact_sync[_sync]`** (`core/services/contacts/contact_sync_service.py`, `core/services/ingestion_queue.py`) — the single sync pipeline + Procrastinate deferral.
- **`create_default_datasource`** (`core/services/contacts/contact_directory_service.py`) — provision the CSV datasource on directory create (no schema is auto-created; `default_schema_id` is optional/user-selected).
- **`summarize_directory_deletion` / `hard_delete_directory_and_children`** (`core/services/contacts/directory_delete.py`) — delete-impact counts; FK-safe hard delete (cancels queued dial jobs, keeps org schemas, detaches syncs).
- **`get_or_create_default_directory`** (`core/services/contacts/contact_directory_service.py`) — resolve-or-provision the org's default `"Global"` directory (`DEFAULT_DIRECTORY_NAME`); the ONE way any flow lands ad-hoc contacts in a shared directory.
- **`parse_datetime_value(raw, *, fmt=None, tz=None)`** (`core/services/contact_ingestion/row_mapping.py`) — the ONE datetime parser (UTC ISO out) shared by the reserved `scheduled_at` column and configurable date/datetime schema fields (`format` = `date|datetime`, `field_metadata` = `{datetime_format, timezone}`, parsed via `zoneinfo`).
- **`OutboundCallService.select_from_number(agent, explicit=None)`** (`core/services/outbound_call_service.py`) — the ONE outbound caller-id resolver: explicit wins; else auto-select org Twilio numbers (single → that one, multiple → round-robin LRU). Reused by create + dispatch.
- **`resolve_batch_concurrency(requested)` / `get_env_outbound_ceiling()`** (`core/services/outbound_capacity.py`) — outbound concurrency is **per scheduling batch**, not global/org. Each batch (one schedule action / one API call) dials up to its own `max_concurrency` at once; the next fires as one finishes. `get_env_outbound_ceiling()` is the env value (`settings.MAX_CONCURRENT_OUTBOUND_CALLS`, `<=0` → `None`) — used ONLY as the UI selector's upper bound + the default; it is NOT a separate runtime ceiling. `resolve_batch_concurrency(requested)` is the ONE place a requested value becomes the effective limit (valid → clamp to `[1, ceiling]`; empty/`0`/`None` → the env default; no env → `None`/unlimited); called inside `OutboundCallService.schedule_calls_for_contacts`, so the UI, file upload, AND API-without-UI all behave the same. The limit + a `batch_id` are stamped on typed `scheduled_calls.batch_id` / `scheduled_calls.max_concurrency` columns (indexed `(batch_id, status)` for the hot-path count; NULL = no per-batch limit). Enforced at DISPATCH: `dispatch_scheduled_call` folds the batch's live in-flight count (`_ACTIVE_OUTBOUND_STATES` filtered by the `batch_id` column) into the atomic scheduled→processing claim, so a batch never exceeds its limit; held rows stay `scheduled`. Freed slots refill two ways — `_refill_after_completion(sc)` (instant, enqueues the next due row of the SAME batch from the terminal status webhook) and the `drain_outbound_calls` periodic task → `drain_outbound_capacity` (per-minute safety net over batch-limited rows). UI reads the ceiling via `OutboundCallService.get_concurrency_max` (`GET /outbound-call/concurrency-max`) and sends `max_concurrency` on create / create-from-file. Never re-derive the per-batch limit at a call site — call `resolve_batch_concurrency`.
- **`OutboundCallService._schedule_via_contacts`** (`core/services/outbound_call_service.py`) — Schedule → Assign → Create: bulk/scheduled outbound routes through `ContactService.create_contacts(GlobalDir, rows, agent_id=)` (create+assign) then `schedule_calls_for_contacts`; no duplicate contact create/assign logic.
- **`get_scheduling_timezone(settings)`** (`core/services/org_settings.py`) — resolve the org's default scheduling timezone from `organizations.settings["scheduling_timezone"]` (IANA, default `UTC`). The org settings PUT (`AuthService.update_organization_settings`) merges (read-modify-write) so a partial update never clobbers other keys.
- **`ContactSchemaService.build_sample_file(schema_id, fmt)`** (`core/services/contacts/contact_schema_service.py`) — server-side schema-shaped sample import file (CSV or `.xlsx` via openpyxl); served by `GET /contact-schemas/{id}/sample?format=`. Sample content (incl. example values) is built here, NOT in the client.
- **`ContactSchemaService.apply_scheduled_at_from_column(records, schema_id, column)`** (`core/services/contacts/contact_schema_service.py`) — for an uploaded outbound file, map a user-named column into each `ParsedContact.metadata["scheduled_at"]`, parsed with the matching date/datetime schema field's `datetime_format` and timezone (field tz → org `get_scheduling_timezone` → UTC), so the schedule column and stored metadata resolve to the SAME instant. Per-row time overrides the request `scheduled_at` (fallback for empty cells). Returns `(record, reason)` for cells that are unparseable or in the PAST so the caller drops them to `invalid` instead of dialing ASAP. Used by `POST /outbound-call/create-from-file` (the past→invalid seam is gated to the file path; `_resolve_contact_when` is unchanged for manual/API scheduling).

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

This project is indexed by GitNexus as **providence** (19162 symbols, 48035 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
3. `READ gitnexus://repo/providence/process/{processName}` — trace the full execution flow step by step
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
| `gitnexus://repo/providence/context` | Codebase overview, check index freshness |
| `gitnexus://repo/providence/clusters` | All functional areas |
| `gitnexus://repo/providence/processes` | All execution flows |
| `gitnexus://repo/providence/process/{name}` | Step-by-step execution trace |

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
