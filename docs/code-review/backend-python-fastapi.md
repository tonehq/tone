# Backend Code Review Rules — Python / FastAPI / SQLAlchemy

Stack: FastAPI, SQLAlchemy 2.0, Pydantic, Alembic, JWT auth, AES-encrypted secrets,
multi-tenancy (`TenantContext`), loguru, pytest. Layered architecture:
`core/api/v1/` (routers) → `core/services/` (`BaseService`) → `core/models/` (`TimestampModel`).

Formatting is tool-enforced (Ruff/formatter). **Review the substance below, not the whitespace.**

---

## 1. Layering & architecture (repo's core discipline)

- `[blocker]` **Routers stay thin.** `core/api/v1/*` handlers do: parse/validate input →
  authorize → call a service → shape the response. **No business logic, no raw DB queries in
  routers.** If a handler builds SQL or branches on domain rules, push it into a service.
- `[blocker]` **Business logic lives in a service** extending `BaseService` (which owns the DB
  session). New logic that touches multiple models or enforces rules → a service method, reusable
  from any router, worker, or CLI.
- `[should]` **Models are data + light domain behavior only** — no HTTP concerns, no request
  parsing in `core/models/*`. All extend `TimestampModel` (UUID + integer PK).
- `[should]` Dependencies flow one direction: api → services → models. A model importing a router,
  or a service importing FastAPI request objects, is a layering violation.
- `[should]` Cross-cutting concerns use the provided seams: `Depends(get_db)`, auth guards,
  `TenantContext`, `core/config.Settings`, `core/utils/encryption`. Don't reinvent them.

## 2. Auth, authorization & multi-tenancy

- `[blocker]` **Every non-public route declares an auth dependency** — `require_authenticated`,
  `require_admin_or_owner`, `require_org_member`, etc. A new endpoint with no guard is a hole.
  Verify the guard matches the sensitivity of the action (read vs admin vs owner).
- `[blocker]` **Tenant isolation on every query.** Reads and writes must be scoped to the caller's
  org (`TenantContext` / `DEFAULT_ORG_ID`). A query that fetches by id alone, without an org filter,
  lets one tenant read/modify another's data. This is the #1 backend bug class here — check it every time.
- `[blocker]` **Authorization checks the object, not just the role.** "Is a member" ≠ "may edit
  *this* record." Verify ownership/scope of the specific resource before mutating it (IDOR).
- `[should]` AuthZ decisions happen in one place (guard/service), not re-derived ad hoc per handler.
- `[should]` JWT claims (`JWTClaims`) are validated, not trusted blindly; expiry and role are checked.

## 3. Data access & SQLAlchemy 2.0

- `[blocker]` **No raw string-interpolated SQL.** Use the ORM / parameterized queries. Any
  `text(f"... {user_input} ...")` is a SQL-injection blocker.
- `[blocker]` **No N+1 queries.** Loading a list then lazy-loading a relationship per row → use
  `selectinload`/`joinedload` or a single query. Check every loop that touches `.some_relationship`.
- `[should]` Query only what's needed — avoid `SELECT *`-style loading of huge rows/blobs when a
  few columns suffice; paginate list endpoints (`limit`/`offset` or keyset). No unbounded `.all()`.
- `[blocker]` **Transaction boundaries are correct.** A multi-write operation commits atomically or
  rolls back as a unit. No partial commits that leave data inconsistent on error. Errors must not
  leave a half-open transaction/session.
- `[should]` Writes go through the service's session; no committing inside a loop per row when a
  single commit works; no session leaks.
- `[should]` Uniqueness/foreign-key constraints enforced at the **DB level**, not only in Python —
  Python checks race, DB constraints don't.

## 4. Alembic migrations

- `[blocker]` **Schema change → matching Alembic migration** in the same PR. A model edit without a
  migration will break every environment on deploy.
- `[blocker]` Migration is reviewed for **safety on a live table**: adding a `NOT NULL` column with
  no default, or a blocking index build, locks/breaks prod. Use nullable-then-backfill-then-constrain,
  or non-blocking index creation.
- `[should]` `downgrade()` is implemented and actually reverses `upgrade()` (or is a documented,
  deliberate no-op).
- `[should]` Migrations are additive/backward-compatible with the currently-running code where
  possible (expand/contract), since code and schema deploy at different instants.
- `[should]` Data migrations are idempotent and batched for large tables — no single `UPDATE` over
  millions of rows in one lock.
- `[should]` **Index an already-populated column with `CREATE INDEX CONCURRENTLY`**
  (`op.create_index(..., postgresql_concurrently=True)` in a non-transactional migration —
  `with op.get_context().autocommit_block():`, and an idempotent/`if_not_exists` build since a failed
  concurrent index leaves an `INVALID` index). A plain `CREATE INDEX` takes a write-blocking lock for
  the whole build. **Exception:** an index on a column added *in the same migration* (all-`NULL`, empty)
  builds instantly — a plain `CREATE INDEX` is fine and simpler there; don't reach for `CONCURRENTLY`
  when there's nothing to scan.

## 5. Pydantic schemas & validation

- `[blocker]` **Validate input at the boundary** with Pydantic request models — don't accept a raw
  dict and index into it. Untyped input is an injection and crash surface.
- `[should]` **Separate request / response / DB models.** Never return an ORM object directly if it
  exposes internal fields; use a response schema. Never let a request schema set server-controlled
  fields (id, org_id, role, is_admin, created_at) — mass-assignment bug.
- `[should]` Constraints live in the schema (`min_length`, `ge`, `EmailStr`, enums), not as manual
  `if` checks in the handler.
- `[nit]` Reuse base schemas via inheritance/composition instead of copy-pasting field lists.

## 6. Secrets, encryption & config

- `[blocker]` **Provider API keys and secrets are AES-encrypted at rest** via
  `core/utils/encryption.py` — never stored plaintext, never logged, never returned in a response.
  Check any new secret-bearing field goes through encryption on write and decryption only where used.
- `[blocker]` **No secrets/PII in logs or exceptions.** loguru output ships to Grafana — log ids and
  context, never tokens, keys, passwords, or full request bodies with credentials.
- `[should]` Config comes from `Settings` (Infisical/`.env`), not `os.environ` reads scattered in
  code or hard-coded literals. New config has a sensible default and is documented.

## 7. Error handling & responses

- `[blocker]` **Raise `HTTPException` with the correct status code**, not a bare 500 for a 400/403/404
  case. Don't leak internal messages/stack traces to the client; log the detail, return a safe message.
- `[should]` External calls (LLM/STT/TTS providers, webhooks, DB) have timeouts and handle failure —
  no unbounded awaits that hang the worker. Retries are bounded and idempotent.
- `[should]` Input-validation failures return 422/400 with a clear field-level message (Pydantic does
  this for free — don't bypass it).

### 7a. Logging & tracebacks (repo standard — apply to every new service/function)

- `[blocker]` **Every error-handling `except` captures a full traceback** — use `logger.exception(...)`
  (loguru), never message-only `logger.error("...", e)` / `logger.warning("...", e)` / `print(...)`.
  `logger.exception` must sit **inside an active `except` block** (elsewhere it logs a useless
  `NoneType: None`). Across the subprocess IPC boundary only, use `traceback.format_exc()` as a plain
  string (loguru's formatting doesn't survive the pipe framing).
- `[blocker]` **No silent swallow.** `except ...: pass` (or a bare `return`/`continue` with no log) that
  drops an *unexpected* error is a blocker — log it (at least `logger.debug`) and keep the recovery.
  **Never swallow `asyncio.CancelledError`** — re-raise it; a broad `except Exception` in an async path
  must not convert cancellation into a swallow.
- `[should]` **Named exception first, then a catch-all fallback.** `except <SpecificError>:` for known
  failure modes (with context), then `except Exception:` as the backstop — each logging a traceback and
  preserving prior behavior (re-raise / `HTTPException` / safe 204 / `return None` degradation).
- `[should]` **Right level = right noise.** Real/unexpected failures → `logger.exception`. *Expected*
  control-flow `except`s (parse fallbacks like `int()`/`json`, cache miss, optional `ImportError`,
  best-effort cleanup, per-audio-frame/hot-loop errors) → `logger.debug`, **not** an ERROR traceback on
  every call/boot. Don't remove a guard's behavior; just add the trace.
- `[should]` **Tag logs with a context prefix** (`[bot]`, `[inbound]`, `[outbound]`, `[transport]`,
  `[runner]`, `[resolver]`, or the service name) and rely on the per-call `trace_id` for correlation.
  Log setup/lifecycle milestones at INFO; keep the hot path at DEBUG/TRACE.
- `[blocker]` **Use the shared loguru `logger`.** Never call `logger.add` / `logger.remove` /
  `logger.configure` outside `core/logging.py` — that owns the single stderr sink. Pipecat and Havana
  share the one loguru singleton, so a stray sink change breaks the whole process's logging/level.
- `[blocker]` **Log level is resolved in one place.** Per-call verbosity comes from
  `core/services/log_level_resolver.py` (`agent.log_level > organization.log_level > env LOG_LEVEL >
  INFO`). Never read the `log_level` columns directly and never hardcode a level; `run_bot` resolves and
  applies it via `setup_logging(level=...)`. New per-call code inherits this automatically.
- `[should]` **No secrets/PII in any log line** (see §6) — log ids, provider slugs, statuses; never keys,
  tokens, prompts with user PII, or full request bodies.

## 8. Async & concurrency

- `[blocker]` **No blocking I/O in an `async def` path.** Sync DB drivers, `requests`, `time.sleep`,
  or CPU-heavy work inside an async handler block the event loop and stall the whole server. Use the
  async equivalent or `run_in_executor`.
- `[should]` Shared mutable state across async tasks/requests is synchronized or avoided; no
  request-scoped data stashed on a module global.
- `[should]` Background/queue work (Procrastinate ingestion, pipeline runners) is idempotent —
  safe to run twice — because retries happen. No "credit the account" that double-fires on retry.
- `[should]` `asyncio` tasks are awaited or tracked; no fire-and-forget that swallows exceptions.

## 9. Performance & resources

- `[should]` Hot paths (per-call pipeline, per-request middleware) avoid re-decrypting keys,
  re-reading config, or re-instantiating clients each call — cache/reuse where safe.
- `[should]` Connections, files, sessions, and provider clients are closed/released (context
  managers) — no leaks that exhaust the pool.
- `[should]` Batch what can be batched (bulk insert vs row-by-row); don't call an external API in a
  tight loop when one batched call works.

## 10. Testing (pytest)

- `[blocker]` New endpoints/services have tests in `test-cases/`. Bug fixes include a regression test
  that fails without the fix.
- `[should]` Tests cover success, validation failure, **auth/authorization denial**, and tenant
  isolation (a user cannot access another org's data) — the last two are the highest-value tests here.
- `[should]` Tests assert on behavior and DB state, not internal call counts, where practical.
- `[should]` External providers (LLM/STT/TTS, network) are mocked; tests are deterministic and don't
  hit real services or require secrets.
- `[nit]` Async pipeline tests that can't run under xdist are marked/segregated per the repo's pytest
  config, not left to flake.

## 11. Structure, naming & reuse

- `[blocker]` **Single source of truth.** The same functionality has one implementation and every
  caller (router, worker, CLI, test) invokes it. A PR that re-implements or copy-pastes logic an
  existing service/helper already provides must call the shared function instead — flag the
  duplication and point to the canonical one. New logic that will be needed from more than one place
  is written as a shared service method / `core/services/common` / `core/utils` helper from the start.
- `[blocker]` **All business logic runs through the service layer.** Routers stay thin (parse →
  authorize → call service → shape response); domain rules, multi-model operations, and queries live
  in a `BaseService`, callable from anywhere. (Reinforces §1.)
- `[should]` Shared logic → a service method or `core/utils` helper, reused across routers — not
  copy-pasted between endpoints (rule of three).
- `[should]` Functions do one thing; a service method spanning fetch + transform + external call +
  persist should be decomposed for testability.
- `[should]` Public/exported surface is minimal; internal helpers are private (`_prefixed`).
- `[nit]` Type hints on public functions; names describe intent; no dead code or stray `print`.

## Quick reviewer checklist (BE)

- [ ] Router is thin; logic in a `BaseService`; models stay data-only.
- [ ] **No duplicated logic — same functionality is one shared service/helper, called everywhere (not re-implemented per endpoint).**
- [ ] Every route has the right auth guard; **every query is org/tenant-scoped**.
- [ ] AuthZ checks the specific object (no IDOR), not just the role.
- [ ] No raw/interpolated SQL; no N+1; queries paginated; transactions atomic.
- [ ] Schema change ships an Alembic migration that's safe on a live table + has downgrade.
- [ ] Pydantic validates input; request schema can't set server-controlled fields.
- [ ] Secrets AES-encrypted, never logged/returned; config via `Settings`.
- [ ] Correct HTTPException status; no swallowed exceptions; external calls time out.
- [ ] Every `except` logs a traceback via `logger.exception` (expected control-flow → `logger.debug`); no message-only `logger.error("...", e)` / `print`; `CancelledError` never swallowed.
- [ ] Uses the shared loguru `logger`; no `logger.add/remove/configure` outside `core/logging.py`; per-call level via `log_level_resolver` (never reads `log_level` columns directly).
- [ ] No blocking I/O in async paths; background work is idempotent.
- [ ] Tests cover success + validation + auth-denial + tenant isolation; providers mocked.
