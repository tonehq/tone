import sys
import uuid
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
    "trace_id={extra[trace_id]} | {message}"
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
    logger.configure(extra={"trace_id": "none"}, patcher=_trace_patcher)
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


def _trace_patcher(record):
    # Stamp every record with the current call's trace_id. Wrapped so logging
    # can never raise into the caller; leaves non-call/global logs as "none".
    try:
        tid = _trace_id_var.get()
        if tid and tid != "none":
            record["extra"]["trace_id"] = tid
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


def update_trace_id_with_call_log(current_trace_id, call_log_id):
    """Replace the trailing segment with the given value.

    Retained for backward compatibility; the live path now fills the call_id
    segment via start_call_trace(call_id=...)."""
    parts = current_trace_id.rsplit("-", 1)
    return f"{parts[0]}-{call_log_id}"
