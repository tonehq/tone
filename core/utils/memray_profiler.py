"""Memory profiling with memray, per long-running unit of work.

The ONE place a unit of work (a voice call, a document-ingestion run, …) is
wrapped in a `memray.Tracker`. Each flow has its own on/off flag and file prefix,
but they all share one implementation (`_profile_memory`) so adding a new flow is
a thin wrapper, never a copy:

- `profile_call_memory(ref)`      — gated by `MEMRAY_PROFILING_ENABLED`,           file `call_<ref>.bin`
- `profile_ingestion_memory(ref)` — gated by `MEMRAY_INGESTION_PROFILING_ENABLED`, file `ingestion_<ref>.bin`

All files land in `settings.MEMRAY_PROFILE_DIR`, so an operator can open a flame
graph for a single unit afterward:

    python -m memray flamegraph memray_profiles/<prefix>_<ref>.bin

`MEMRAY_NATIVE_TRACES` additionally captures native (C/C++) allocations for every
flow — needed to attribute ML/audio-library memory the Python heap can't see.

Profiling must NEVER break the wrapped work: every failure path (flag off, memray
not installed, unwritable dir, a Tracker already active in this process) degrades
to a silent no-op that still runs the work.
"""

import os
from contextlib import contextmanager

from loguru import logger

from shared.config import settings


def _capture_path(prefix: str, ref: str) -> str:
    """Build the capture file path, one file per (prefix, ref)."""
    # config.py guarantees MEMRAY_PROFILE_DIR is non-empty (defaults to "memray_profiles").
    out_dir = settings.MEMRAY_PROFILE_DIR
    # The identifier can carry path separators (e.g. some call transports) —
    # sanitize before using it as a filename.
    safe_ref = (ref or "none").replace("/", "_").replace(os.sep, "_")
    return os.path.join(out_dir, f"{prefix}_{safe_ref}.bin")


@contextmanager
def _profile_memory(enabled: bool, prefix: str, ref: str):
    """Capture memory allocations for the wrapped block when `enabled`.

    No-op unless `enabled` is true and memray is importable and a Tracker can start
    (only one Tracker may be active per process — a second concurrent unit in the
    same process falls through to no-op). Never raises out of the wrapped block."""
    if not enabled:
        yield
        return

    try:
        import memray
    except ImportError:
        logger.debug("[memray] profiling enabled but 'memray' is not installed — skipping")
        yield
        return

    path = _capture_path(prefix, ref)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except OSError:
        logger.debug("[memray] could not create profile dir for {} — skipping", path)
        yield
        return

    try:
        tracker = memray.Tracker(path, native_traces=settings.MEMRAY_NATIVE_TRACES)
        # Enter explicitly so a start failure (e.g. another Tracker already active,
        # or the file exists) is handled here and never masks a real error from
        # the wrapped work.
        tracker.__enter__()
    except Exception:
        logger.debug("[memray] could not start Tracker for {} — skipping", path)
        yield
        return

    logger.info("[memray] capturing {} memory → {}", prefix, path)
    try:
        yield
    finally:
        try:
            tracker.__exit__(None, None, None)
            logger.info("[memray] wrote {} memory profile → {}", prefix, path)
        except Exception:
            logger.debug("[memray] Tracker exit failed for {}", path)


def profile_call_memory(call_ref: str):
    """Profile one voice call, gated by `MEMRAY_PROFILING_ENABLED`.

    `call_ref` names the file (`call_<call_ref>.bin`) — pass the provider call id,
    falling back to the trace_id so the file is never blank/colliding."""
    return _profile_memory(settings.MEMRAY_PROFILING_ENABLED, "call", call_ref)


def profile_ingestion_memory(run_ref: str):
    """Profile one document-ingestion run, gated by `MEMRAY_INGESTION_PROFILING_ENABLED`.

    `run_ref` names the file (`ingestion_<run_ref>.bin`) — pass the ingestion run id."""
    return _profile_memory(settings.MEMRAY_INGESTION_PROFILING_ENABLED, "ingestion", run_ref)
