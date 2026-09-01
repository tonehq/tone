"""Pure helpers for turning a raw Loki line into stored fields + a dedup key.

Kept dependency-free and side-effect-free so they're trivially unit-testable.
Identifiers (trace_id/agent_id/call_id/org_id) are deliberately NOT parsed here
— they are stamped from the ``Call`` row by ``PipelineLogSyncService``. Only the
human-facing ``level``/``logger_name``/``message`` are extracted, and always
defensively: a line that doesn't match the loguru format keeps its full text as
the message rather than being dropped.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Optional, TypedDict

# Mirrors core/logging._LOG_FORMAT:
#   "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | trace_id=... | job_id=... | {message}"
# Tolerant of padding/whitespace and either '.' or ',' as the ms separator. The
# ``job_id=...`` field is matched OPTIONALLY (and consumed, not stored) so this
# parser handles both current lines and any older line emitted before job_id was
# added to the format — in both cases ``message`` excludes the id prefixes.
_LINE_RE = re.compile(
    r"^\s*\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[.,]\d+\s*\|\s*"
    r"(?P<level>[A-Z]+)\s*\|\s*"
    r"(?P<location>[^|]*?)\s*\|\s*"
    r"trace_id=(?P<trace_id>[^|]*?)\s*\|\s*"
    r"(?:job_id=[^|]*?\s*\|\s*)?"
    r"(?P<message>.*)$",
    re.DOTALL,
)


class ParsedLine(TypedDict):
    level: Optional[str]
    logger_name: Optional[str]
    message: str


def parse_line(line: str) -> ParsedLine:
    """Extract ``level``/``logger_name``/``message`` from a loguru-formatted line.

    On no match (continuation lines of a multiline traceback, non-loguru output,
    etc.) the whole line is returned as ``message`` with ``level``/``logger_name``
    None — a line is never dropped."""
    match = _LINE_RE.match(line or "")
    if not match:
        return ParsedLine(level=None, logger_name=None, message=line)

    location = (match.group("location") or "").strip()
    # location is "{name}:{function}:{line}"; the module name is the head.
    logger_name = location.split(":", 1)[0] or None
    return ParsedLine(
        level=match.group("level") or None,
        logger_name=logger_name,
        message=match.group("message"),
    )


def extract_trace_id(line: str) -> Optional[str]:
    """Return the ``trace_id`` token from a loguru-formatted line, or None.

    None on a non-matching line (multiline-traceback continuation, non-loguru
    output) — such lines carry no token and must never be dropped. Used to
    disambiguate lines fetched by the short-uuid prefix filter: a line whose
    token names a *different* fully-qualified call is dropped rather than
    misattributed to this one."""
    match = _LINE_RE.match(line or "")
    if not match:
        return None
    token = (match.group("trace_id") or "").strip()
    return token or None


def fingerprint(ts_ns: int, labels: Optional[dict], line: str) -> str:
    """Deterministic sha256 hex over (ts_ns, sorted labels, full line).

    Label order from Loki is not guaranteed, so labels are serialized
    sort-key'd → the same line yields the same fingerprint on every re-sync,
    making the UNIQUE-constraint dedup stable."""
    labels_repr = json.dumps(labels or {}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256()
    digest.update(str(ts_ns).encode("utf-8"))
    digest.update(b"\x00")
    digest.update(labels_repr.encode("utf-8"))
    digest.update(b"\x00")
    digest.update((line or "").encode("utf-8"))
    return digest.hexdigest()
