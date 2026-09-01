import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

from loguru import logger

# ---------------------------------------------------------------------------
# Log level: resolution + sink application
# ---------------------------------------------------------------------------
# Every process boots at a baseline level (resolve_level: settings.LOG_LEVEL env
# > INFO default). For CALLS a finer level can be set per organization / per agent
# in the DB (agents.log_level > organizations.log_level > env baseline): the
# call-pod parent resolves that hierarchy — see core/services/log_level_resolver.py
# — and injects the level into the call subprocess, which applies it in
# setup_logging(level=...). This module stays free of DB/Redis so it is safe to
# import at the very top of every process.
_DEFAULT_LEVEL = "INFO"
# loguru's built-in severities. We only advertise INFO/DEBUG/TRACE to operators,
# but accept the full set so a deliberate WARNING/ERROR is honored.
_VALID_LEVELS = {"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}

# The level currently applied to this process's sink (None until setup_logging runs).
_current_level: "str | None" = None

_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | "
    "trace_id={extra[trace_id]} | job_id={extra[job_id]} | {message}"
)


def _normalize_level(level) -> "str | None":
    """Upper-case and validate a level name; return None for blank/invalid input."""
    if not level:
        return None
    lvl = str(level).strip().upper()
    return lvl if lvl in _VALID_LEVELS else None


def resolve_level() -> "tuple[str, str]":
    """Process baseline level and its source: settings.LOG_LEVEL env > INFO default.

    Never raises. Per-call org/agent overrides are resolved separately by the
    call-pod parent (core/services/log_level_resolver.py) and injected into the
    subprocess; this function is the baseline for long-lived processes."""
    try:
        from shared.config import settings

        env_level = _normalize_level(getattr(settings, "LOG_LEVEL", None))
    except Exception:
        env_level = None
    if env_level:
        return env_level, "env"
    return _DEFAULT_LEVEL, "default"


def get_applied_level() -> "str | None":
    """The level actually applied to this process's sink (None before setup)."""
    return _current_level


def _apply_sink(level: str) -> None:
    """Replace the stderr sink at the given level, preserving the trace patcher."""
    global _current_level
    logger.remove()
    logger.add(sys.stderr, format=_LOG_FORMAT, level=level)
    logger.configure(
        extra={"trace_id": "none", "job_id": "none"}, patcher=_trace_patcher
    )
    _current_level = level


# Per-call observability context. The trace_id has the structure
# "{short_uuid}-{agent_id}-{call_id}" and is rendered from these component
# contextvars, so the value is correct in every async task (contextvars propagate
# to child tasks) and in any thread that explicitly sets it.
#   _call_uuid_var : stable per-call short uuid — present in 100% of the logs.
#   _agent_id_var  : the agent id (filled once the agent is resolved).
#   _call_id_var   : the provider call id (call_data["call_id"]); "0" until known.
#   _trace_id_var  : the rendered "{short_uuid}-{agent_id}-{call_id}".
_call_uuid_var: ContextVar[str] = ContextVar("call_uuid", default="none")
_agent_id_var: ContextVar[str] = ContextVar("trace_agent_id", default="")
_call_id_var: ContextVar[str] = ContextVar("trace_call_id", default="0")
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="none")

# Background-job correlation id, mirroring trace_id. Set by the Procrastinate
# task wrapper (core/services/ingestion_queue.py::_with_job_logging) for the
# duration of one job, so every log line the job emits carries job_id=<id>.
# Stays "none" for non-job logs (API requests, live-call subprocess, etc.), the
# same way trace_id is "none" outside a call.
_job_id_var: ContextVar[str] = ContextVar("job_id", default="none")


def _trace_patcher(record):
    # Stamp every record with the current call's trace_id and (when inside a
    # background job) its job_id. Wrapped so logging can never raise into the
    # caller; leaves non-call/non-job logs as "none".
    try:
        tid = _trace_id_var.get()
        if tid and tid != "none":
            record["extra"]["trace_id"] = tid
    except Exception:
        pass
    try:
        jid = _job_id_var.get()
        if jid and jid != "none":
            record["extra"]["job_id"] = jid
    except Exception:
        pass


def setup_logging(level: "str | None" = None) -> str:
    """Configure loguru with trace_id support. Call once at process startup.

    Level resolution: an explicit ``level`` arg wins; otherwise resolve_level()
    applies the settings.LOG_LEVEL env > INFO default baseline. Runs in every
    process. For call subprocesses the parent passes the DB-resolved org/agent
    level as ``level`` (see core/services/log_level_resolver.py), so every new
    call honors the current DB level without a restart. Returns the applied level."""
    resolved = _normalize_level(level)
    if resolved is None:
        resolved, _ = resolve_level()
    _apply_sink(resolved)
    return resolved


def _render_trace() -> str:
    """Render and store the trace_id from its component contextvars.

    Empty segments are dropped, so the value is always clean: "{call_uuid}" until
    the agent is known, then "{call_uuid}-{agent_id}", then the full
    "{call_uuid}-{agent_id}-{call_id}" — never a trailing dash or a "-0" filler.
    The call_uuid prefix is present in every line, so the whole call is always
    filterable by it.
    """
    cu = _call_uuid_var.get()
    if cu == "none":
        _trace_id_var.set("none")
        return "none"
    parts = [cu]
    agent_id = _agent_id_var.get()
    if agent_id:
        parts.append(str(agent_id))
        call_id = _call_id_var.get()
        if call_id and call_id != "0":
            parts.append(str(call_id))
    tid = "-".join(parts)
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Return the trace_id set for the current context (or 'none')."""
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set the rendered trace_id directly for the current context (and any thread
    that calls this — executor threads don't inherit contextvars)."""
    _trace_id_var.set(trace_id or "none")


def get_job_id() -> str:
    """Return the job_id set for the current context (or 'none')."""
    return _job_id_var.get()


def set_job_id(job_id) -> None:
    """Set the background-job id for the current context. Empty/None → 'none'."""
    _job_id_var.set(str(job_id) if job_id not in (None, "") else "none")


@contextmanager
def job_logging_context(job_id):
    """Bind ``job_id`` for the duration of the ``with`` block, then restore the
    previous value.

    Used to wrap a single background-job execution so every log line it emits
    carries ``job_id=<id>`` and the id never leaks to the next job on a reused
    worker thread. Mirrors the trace_id contract. Never raises out of enter/exit.
    """
    value = str(job_id) if job_id not in (None, "") else "none"
    token = _job_id_var.set(value)
    try:
        yield
    finally:
        try:
            _job_id_var.reset(token)
        except Exception:
            _job_id_var.set("none")


# The four contextvars that together render the trace_id, with their defaults —
# used to snapshot/restore the whole trace context as a unit.
_TRACE_VARS = (
    (_call_uuid_var, "none"),
    (_agent_id_var, ""),
    (_call_id_var, "0"),
    (_trace_id_var, "none"),
)


@contextmanager
def isolated_trace_context():
    """Start the ``with`` block with a CLEAN trace (trace_id='none'), then restore
    the previous trace values on exit.

    Bounds a trace to exactly the span that configures it. A Procrastinate worker
    thread is reused across jobs and contextvars persist on a thread, so without
    this a ``trace_id`` one job sets (e.g. an ingestion run via
    ``start_ingestion_trace``) would leak into the NEXT job on the same thread
    that never configured its own. Wrapping each job run in this guarantees the
    ``trace_id`` appears ONLY from the point the job configures it to the job's
    end — a job that configures no trace logs ``trace_id=none`` throughout.
    Independent of ``job_id`` (a separate contextvar / log key). Never raises out
    of enter/exit.
    """
    tokens = [var.set(default) for var, default in _TRACE_VARS]
    try:
        yield
    finally:
        for (var, _default), token in zip(_TRACE_VARS, tokens):
            try:
                var.reset(token)
            except Exception:
                var.set(_default)


def start_call_trace(agent_id=None, call_id=None, external=None) -> str:
    """Fix one call_uuid for the whole call; fill agent_id / call_id once known.

    Idempotent: safe to call multiple times during a call — the call_uuid never
    changes (the first caller wins), only the agent_id / call_id segments are
    filled in. This lets the earliest entry (e.g. bot() before the agent is
    resolved) establish a stable id, and later callers refine it to
    "{short_uuid}-{agent_id}-{call_id}".
    """
    if _call_uuid_var.get() == "none":
        cu = (external.split("-")[0] if external else None) or uuid.uuid4().hex[:8]
        _call_uuid_var.set(cu)
    if agent_id is not None:
        _agent_id_var.set(str(agent_id))
    if call_id:
        _call_id_var.set(str(call_id))
    return _render_trace()


def make_trace_id(agent_id, call_id=0):
    """Generate trace ID in format: {short_uuid}-{agent_id}-{call_id}."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{short_uuid}-{agent_id}-{call_id}"


# ---------------------------------------------------------------------------
# Ingestion trace_id — mirrors the call trace_id pattern above so every log
# line emitted during one ingestion pipeline run carries the same filterable
# id. Format: "{short_uuid}-ing-{run_id}". The "ing" tag lets an operator
# distinguish an ingestion trace from a call trace at a glance.
# ---------------------------------------------------------------------------

def make_ingestion_trace_id(run_id) -> str:
    """Generate an ingestion trace_id in format: {short_uuid}-ing-{run_id}."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"{short_uuid}-ing-{run_id}"


def start_ingestion_trace(run_id, existing=None) -> str:
    """Establish the trace_id for one ingestion run and set the contextvar so
    every subsequent log line in this task's context carries it.

    Idempotent (mirrors ``start_call_trace``): if ``existing`` is truthy — e.g.
    the run row already has a persisted ``trace_id`` from a prior retry — that
    value is reused; otherwise a fresh id is minted. The single caller
    (``IngestionRunService.ensure_trace_id``, invoked at the top of the
    ``ingest_upload`` Procrastinate task) persists the returned value onto the
    run row, so retries and the original attempt share one filterable id.
    """
    tid = existing or make_ingestion_trace_id(run_id)
    set_trace_id(tid)
    return tid


def update_trace_id_with_call_log(current_trace_id, call_log_id):
    """Replace the trailing segment with the given value.

    Retained for backward compatibility; the live path now fills the call_id
    segment via start_call_trace(call_id=...)."""
    parts = current_trace_id.rsplit("-", 1)
    return f"{parts[0]}-{call_log_id}"
