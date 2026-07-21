"""Shared row → ``ParsedContact`` mapper for file-based contact ingestion.

Both :class:`~core.services.contact_ingestion.csv_source.CSVContactSource` and
:class:`~core.services.contact_ingestion.excel_source.ExcelContactSource` decode their
own byte format into an iterable of ``header -> value`` string rows and then hand those
rows to :func:`map_rows_to_parsed_contacts` — the ONE place that normalizes headers,
promotes the reserved dial columns, synthesizes a stable ``external_id`` and folds every
other column into ``metadata``. Keeping the mapping here (single source of truth) is what
guarantees a CSV and its equivalent ``.xlsx`` produce byte-identical ``ParsedContact``s.

Header handling is case-insensitive and tolerant of the common aliases a user's
spreadsheet might carry:

- ``name`` -> ``ParsedContact.name``
- ``phone`` / ``phone_number`` -> ``ParsedContact.phone_number`` (normalized to E.164)
- ``scheduled_at`` / ``schedule_time`` / ``scheduled_time`` / ``call_time`` ->
  ``metadata["scheduled_at"]`` (ISO-8601; a naive timestamp is assumed UTC)
- ``external_id`` -> ``ParsedContact.external_id`` (synthesized, stably, when absent so
  re-importing the same file upserts instead of duplicating)
- every other column -> ``metadata``
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, Iterator, Mapping, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from loguru import logger

from core.services.contact_ingestion.base import ParsedContact

_NAME_HEADERS = {"name", "full_name", "contact_name"}
_PHONE_HEADERS = {"phone", "phone_number", "phonenumber", "mobile", "number"}
_EXTERNAL_ID_HEADERS = {"external_id", "externalid", "id", "contact_id"}
_SCHEDULED_AT_HEADERS = {"scheduled_at", "schedule_time", "scheduled_time", "call_time"}

# Reserved headers consumed into first-class fields — everything else flows to metadata.
_RESERVED = _NAME_HEADERS | _PHONE_HEADERS | _EXTERNAL_ID_HEADERS | _SCHEDULED_AT_HEADERS

_NON_DIAL_CHARS = re.compile(r"[\s\-().]")
# A trailing ``*`` (with optional surrounding whitespace) marks a "required" column in
# downloadable sample templates; strip it so ``city*`` still maps to the ``city`` field.
_REQUIRED_MARKER = re.compile(r"\s*\*+\s*$")


def _normalize_header(header: Optional[str]) -> str:
    """Normalize a source header to its lookup key: strip whitespace, drop a trailing
    required-marker ``*``, and lowercase."""
    return _REQUIRED_MARKER.sub("", (header or "").strip()).strip().lower()


def _normalize_phone(raw: str) -> Optional[str]:
    """Best-effort E.164 normalization. Strips spaces/dashes/parens/dots; keeps a
    leading ``+``. Returns None for blanks. Validation (and rejection of un-dialable
    numbers) is left to the scheduling path, which already enforces strict E.164."""
    if not raw:
        return None
    cleaned = _NON_DIAL_CHARS.sub("", raw.strip())
    if not cleaned:
        return None
    # A bare international number without '+' but with a leading '00' -> '+'.
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    return cleaned


def parse_datetime_value(
    raw: str, *, fmt: Optional[str] = None, tz: Optional[str] = None
) -> Optional[str]:
    """Parse a datetime cell into a UTC ISO-8601 string — the ONE datetime parser shared by
    the reserved ``scheduled_at`` column and configurable datetime schema fields.

    ``fmt`` is an optional ``strptime`` format (e.g. ``"%m/%d/%Y %H:%M"``); when omitted the
    value is read as ISO-8601 (a trailing ``Z`` is tolerated). ``tz`` is an optional IANA
    source timezone applied ONLY when the parsed value is naive (has no offset); when the
    value already carries an offset that offset wins. A naive value with no ``tz`` is assumed
    UTC (preserving prior behaviour). Unparseable values / unknown timezones are logged at
    debug and yield ``None`` so a bad cell is dropped rather than crashing the run.
    """
    value = (raw or "").strip()
    if not value:
        return None
    try:
        if fmt:
            dt = datetime.strptime(value, fmt)
        else:
            # Tolerate a trailing 'Z' which fromisoformat historically rejected.
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.debug("[contact_ingestion] unparseable datetime {!r} (fmt={!r}); ignoring", raw, fmt)
        return None
    if dt.tzinfo is None:
        source_tz = timezone.utc
        if tz:
            try:
                source_tz = ZoneInfo(tz)
            except (ZoneInfoNotFoundError, ValueError):
                logger.debug("[contact_ingestion] unknown timezone {!r}; assuming UTC", tz)
        dt = dt.replace(tzinfo=source_tz)
    return dt.astimezone(timezone.utc).isoformat()


def _normalize_scheduled_at(raw: str) -> Optional[str]:
    """Parse an ISO-8601 ``scheduled_at`` into a UTC ISO string (naive = UTC). Thin wrapper
    over the shared :func:`parse_datetime_value`."""
    return parse_datetime_value(raw)


def map_rows_to_parsed_contacts(
    rows: Iterable[Mapping[str, str]],
) -> Iterator[ParsedContact]:
    """Map ``header -> value`` rows into a stream of ``ParsedContact``.

    ``rows`` is any iterable of dict-like rows keyed by the source's original headers
    (what ``csv.DictReader`` yields, or the Excel reader's per-row dict). Header
    normalization + the per-row ``header -> key`` map are built inside from each row's
    keys, so a caller only has to produce raw string rows — the mapping, dedup and
    ``external_id`` synthesis all live here.

    Fully-blank rows (no name / phone / external id / metadata) are skipped. When a row
    carries no ``external_id`` one is synthesized stably (phone, else a content hash) so a
    re-import of the same file upserts rather than duplicating.
    """
    for row in rows:
        # Map each real header to a normalized (lower/stripped) key. A trailing ``*``
        # (with any surrounding whitespace) is stripped so downloadable sample templates
        # can mark required columns as e.g. ``city*`` and still map to ``city``.
        header_map = {h: _normalize_header(h) for h in row.keys()}

        name: Optional[str] = None
        phone: Optional[str] = None
        external_id: Optional[str] = None
        scheduled_at: Optional[str] = None
        metadata: Dict[str, object] = {}

        for header, value in row.items():
            key = header_map.get(header, _normalize_header(header))
            # csv.DictReader collects overflow cells from a ragged row (e.g. a trailing
            # comma) into a list under the None restkey; coerce any non-string value to an
            # empty cell so such rows don't crash the whole import with an AttributeError.
            cell = value.strip() if isinstance(value, str) else ""
            if key in _NAME_HEADERS:
                name = cell or None
            elif key in _PHONE_HEADERS:
                phone = _normalize_phone(cell)
            elif key in _EXTERNAL_ID_HEADERS:
                external_id = cell or None
            elif key in _SCHEDULED_AT_HEADERS:
                parsed = _normalize_scheduled_at(cell)
                if parsed:
                    scheduled_at = parsed
            elif key and key not in _RESERVED:
                # Preserve extra columns under their original (normalized) header.
                if cell:
                    metadata[key] = cell

        if scheduled_at:
            metadata["scheduled_at"] = scheduled_at

        # Skip fully-blank rows (no name, no phone, no external id, no metadata).
        if not any([name, phone, external_id, metadata]):
            continue

        if not external_id:
            # Synthesize a STABLE id so re-importing the same file upserts rather than
            # duplicating: prefer the phone, else a hash of the row content.
            if phone:
                external_id = phone
            else:
                digest = hashlib.sha256(
                    # Sort by the stringified key: a ragged row (more cells than headers)
                    # carries a None restkey from csv.DictReader, and comparing None to str
                    # keys would raise TypeError and abort the whole import.
                    "|".join(f"{k}={v}" for k, v in sorted(row.items(), key=lambda kv: str(kv[0]))).encode("utf-8")
                ).hexdigest()[:32]
                external_id = f"csv-{digest}"

        yield ParsedContact(
            external_id=external_id,
            name=name,
            phone_number=phone,
            metadata=metadata,
        )
