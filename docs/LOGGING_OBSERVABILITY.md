# Pipeline Logging & Observability

How to control log verbosity per **organization** and per **agent** from the DB —
no build, no restart — why pipecat's own logs appear when you lower the level,
and how much log volume each level produces.

---

## 1. Log levels & where the level comes from

The effective level for a **call** is resolved most-specific-first:

```
agent.log_level  >  organization.log_level  >  env LOG_LEVEL  >  "INFO" default
```

- **`agents.log_level`** / **`organizations.log_level`** — nullable DB columns.
  `NULL` means "inherit the parent". An agent's level overrides its org's; the
  org's overrides the env baseline.
- **`LOG_LEVEL` env** — the process baseline (resolved via
  `get_secret("LOG_LEVEL", "INFO")`: Infisical → OS env → `INFO`). Not hardcoded
  in the k8s manifests.

Resolution lives in **one place**: `core/services/log_level_resolver.py`
(`resolve_call_log_level`). Nothing else reads the `log_level` columns.

Valid levels: `TRACE`, `DEBUG`, `INFO` (operator-facing), plus loguru's
`SUCCESS`/`WARNING`/`ERROR`/`CRITICAL` if deliberately set. Blank/invalid values
are ignored and fall through to the next level down.

### How a change takes effect without a restart

Calls run in **per-call subprocesses** (`bot_worker` / `warm_worker`), each scoped
to exactly one agent + org. When a call starts, `run_bot()` (`core/bot.py`)
resolves the level from the DB — reusing the session it already opens to resolve
the agent — and applies it for that call. So **updating a row changes the next
call's level immediately**; in-flight calls are undisturbed.

**DB-safety:** the prefetch/warm path reconstructs the agent as a *transient* ORM
object to avoid a DB connection in the subprocess. The resolver detects that and
**skips the org query** there (it would force an expensive first connection),
falling back to the agent's own carried level or the env baseline. The org query
only runs for real DB-backed agents, where a warm connection already exists.

---

## 2. Changing the level

### Option A — Admin endpoint

```
GET  /api/v1/admin/log-level              → effective level for the caller's org
GET  /api/v1/admin/log-level?agent_id=…   → effective level for one agent
POST /api/v1/admin/log-level              → set it
     body: { "level": "DEBUG" }                     # sets the caller's ORG level
     body: { "level": "DEBUG", "agent_id": "…" }    # sets that AGENT's level
     body: { "level": null,    "agent_id": "…" }    # clears → inherit parent
```

Admin/owner only (`require_admin_or_owner`); all reads/writes are scoped to the
caller's organization. Invalid level → `400`.

### Option B — direct SQL

```sql
-- org-wide
UPDATE organizations SET log_level = 'DEBUG' WHERE id = '<org-uuid>';
-- one agent
UPDATE agents SET log_level = 'TRACE' WHERE id = '<agent-uuid>';
-- clear (inherit)
UPDATE agents SET log_level = NULL WHERE id = '<agent-uuid>';
```

Either way, the next call for that agent/org picks up the new level.

---

## 3. Pipecat's own logs

Pipecat uses the **same global loguru `logger`** as Havana. Its lines already
flow through our single `sys.stderr` sink; they're just emitted at `DEBUG` and
`TRACE`, below the default `INFO`. So:

- **No separate pipecat logging setup is needed or exists in this path.**
  "Enable pipecat loggers" simply means lowering the level for that agent/org.
- At `DEBUG`: pipecat service/pipeline logs interleave with Havana logs under the
  same `trace_id`.
- At `TRACE`: pipecat frame-level logs appear (per-audio-frame) — the dominant
  cost driver, so `TRACE` is investigation-only.

---

## 4. Log growth per call (KB/min)

TRACE volume is driven by per-audio-frame pipecat logs (~50–100 lines/s), which
is why TRACE is investigation-only and the baseline is `INFO`.

### Method (run against a real or fixed-duration scripted call)

1. Set the agent (or org) to each level in turn (SQL or the admin endpoint) and
   place one representative call at each: `INFO`, `DEBUG`, `TRACE`.
2. Capture the **call subprocess** stderr to a file and note the wall-clock
   duration (`... 2> call_LEVEL.log`).
3. Compute `KB_per_min = bytes(logfile) / 1024 / (duration_seconds / 60)`.
4. Repeat for 2–3 call durations to get a **range**.

### Results

> ⚠️ **To be measured in staging** — the numbers below are preliminary engineering
> estimates (order of magnitude), not measured values. Fill this table from the
> method above before enabling verbose levels broadly.

| Level | KB/min (range, per call) | Projected MB / 1000 call-minutes | Dominant driver |
|---|---|---|---|
| INFO  | _tens of KB/min_ (measure)      | _measure_ | lifecycle + turn events |
| DEBUG | _hundreds of KB/min_ (measure)  | _measure_ | pipecat service/pipeline debug |
| TRACE | _multiple MB/min_ (measure)     | _measure_ | per-audio-frame pipecat traces (~50–100 lines/s) |

---

## 5. Config & schema reference

| Where | What | Purpose |
|---|---|---|
| env `LOG_LEVEL` | default `INFO` | Process baseline (Infisical → env → INFO). |
| `organizations.log_level` | nullable | Per-org override; NULL = inherit env. |
| `agents.log_level` | nullable | Per-agent override; NULL = inherit org. |
| `core/services/log_level_resolver.py` | `resolve_call_log_level` | The one place that reads the columns. |

Migration: `alembic/versions/e1f2a3b4c5d6_add_log_level_to_org_and_agent.py`.

**Scope note:** org/agent levels take effect for **calls** (each call subprocess =
one agent/org). Long-lived API pods use the env baseline; per-request org/agent
levels there are out of scope because loguru's sink level is process-global.
