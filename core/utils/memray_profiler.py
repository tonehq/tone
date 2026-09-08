"""Per-call memory profiling with memray.

The ONE place a call's pipeline run is wrapped in a `memray.Tracker`, gated by
`settings.MEMRAY_PROFILING_ENABLED`. Each profiled call writes a capture file to
`settings.MEMRAY_PROFILE_DIR` named by the provider call id, so an operator can
open a flame graph for a single call afterward:

    python -m memray flamegraph memray_profiles/call_<call_id>.bin

Profiling must NEVER break a call: every failure path (flag off, memray not
installed, unwritable dir, a Tracker already active in this process) degrades to
a silent no-op that still runs the call.
"""

import os
from contextlib import contextmanager

from loguru import logger

from shared.config import settings


def _capture_path(call_ref: str) -> str:
    """Build the capture file path for a call, one file per call identifier."""
    # config.py guarantees MEMRAY_PROFILE_DIR is non-empty (defaults to "memray_profiles").
    out_dir = settings.MEMRAY_PROFILE_DIR
    # The identifier (provider call id, or trace_id fallback) can carry path
    # separators from some transports — sanitize before using it as a filename.
    safe_ref = (call_ref or "none").replace("/", "_").replace(os.sep, "_")
    return os.path.join(out_dir, f"call_{safe_ref}.bin")


@contextmanager
def profile_call_memory(call_ref: str):
    """Capture memory allocations for the wrapped call when profiling is enabled.

    `call_ref` names the capture file (`call_<call_ref>.bin`) — pass the provider
    call id, falling back to the trace_id so the file is never blank/colliding.

    No-op unless `MEMRAY_PROFILING_ENABLED` is true and memray is importable and a
    Tracker can start (only one Tracker may be active per process — concurrent
    calls in the dev shared-process path fall through to no-op)."""
    if not settings.MEMRAY_PROFILING_ENABLED:
        yield
        return

    try:
        import memray
    except ImportError:
        logger.debug("[memray] profiling enabled but 'memray' is not installed — skipping")
        yield
        return

    path = _capture_path(call_ref)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    except OSError:
        logger.debug("[memray] could not create profile dir for {} — skipping", path)
        yield
        return

    try:
        tracker = memray.Tracker(path)
        # Enter explicitly so a start failure (e.g. another Tracker already active,
        # or the file exists) is handled here and never masks a real call error.
        tracker.__enter__()
    except Exception:
        logger.debug("[memray] could not start Tracker for {} — skipping", path)
        yield
        return

    logger.info("[memray] capturing call memory → {}", path)
    try:
        yield
    finally:
        try:
            tracker.__exit__(None, None, None)
            logger.info("[memray] wrote call memory profile → {}", path)
        except Exception:
            logger.debug("[memray] Tracker exit failed for {}", path)
