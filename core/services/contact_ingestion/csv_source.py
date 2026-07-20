"""CSV contact source (stdlib ``csv``).

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

import csv
import hashlib
import io
import re
from datetime import datetime, timezone
from typing import Dict, Iterator, Optional

from loguru import logger

from core.services.contact_ingestion.base import ContactSource, ParsedContact

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


def _decode_csv_bytes(raw: bytes) -> str:
    """Decode uploaded CSV bytes tolerantly.

    Prefer UTF-8 (BOM-aware, for Excel exports), then fall back to cp1252/latin-1 so a
    spreadsheet saved on Windows/Excel with a single non-UTF-8 byte (é, £, a smart quote)
    doesn't hard-fail the whole import with a cryptic ``UnicodeDecodeError``. latin-1 maps
    every byte, so the final replace-fallback is only a belt-and-suspenders guard.
    """
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            logger.debug("[contact_ingestion] CSV not decodable as %s; trying next", encoding)
    return raw.decode("utf-8", errors="replace")


def _normalize_header(header: Optional[str]) -> str:
    """Normalize a CSV header to its lookup key: strip whitespace, drop a trailing
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


def _normalize_scheduled_at(raw: str) -> Optional[str]:
    """Parse an ISO-8601 timestamp and return it as an ISO string with a UTC offset.
    A naive timestamp (no tz) is assumed to be UTC. Unparseable values are dropped."""
    value = (raw or "").strip()
    if not value:
        return None
    try:
        # Tolerate a trailing 'Z' which fromisoformat historically rejected.
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.debug("[contact_ingestion] unparseable scheduled_at {!r}; ignoring", raw)
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class CSVContactSource(ContactSource):
    def parse(self, raw: bytes) -> Iterator[ParsedContact]:
        text = _decode_csv_bytes(raw)  # BOM-aware UTF-8, then cp1252/latin-1 fallback
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return

        # Map each real header to a normalized (lower/stripped) key once. A trailing
        # ``*`` (with any surrounding whitespace) is stripped so downloadable sample
        # templates can mark required columns as e.g. ``city*`` and still map to ``city``.
        header_map = {h: _normalize_header(h) for h in reader.fieldnames}

        for row in reader:
            name: Optional[str] = None
            phone: Optional[str] = None
            external_id: Optional[str] = None
            scheduled_at: Optional[str] = None
            metadata: Dict[str, object] = {}

            for header, value in row.items():
                key = header_map.get(header, _normalize_header(header))
                cell = (value or "").strip()
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
                # Synthesize a STABLE id so re-importing the same file upserts rather
                # than duplicating: prefer the phone, else a hash of the row content.
                if phone:
                    external_id = phone
                else:
                    digest = hashlib.sha256(
                        "|".join(f"{k}={v}" for k, v in sorted(row.items())).encode("utf-8")
                    ).hexdigest()[:32]
                    external_id = f"csv-{digest}"

            yield ParsedContact(
                external_id=external_id,
                name=name,
                phone_number=phone,
                metadata=metadata,
            )
