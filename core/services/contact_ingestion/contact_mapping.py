"""Reusable source-row → contact mapping.

``map_source_row_to_contact`` translates a raw source record (a dict of external
header → value, e.g. one parsed CSV row) into a normalized contact dict, driven by a
schema's ``SchemaField`` rows: each field reads from its ``source_key`` (the external
header) and writes to its ``field_name`` (the target contact column or metadata key).
A ``null`` ``source_key`` is identity (read from ``field_name`` itself), which is how a
directory's default schema maps manual input.

Reserved targets (``name``, ``phone_number``, ``external_id``) become top-level contact
attributes; every other target lands in ``contact_metadata``. Values are coerced to the
field's ``type`` (best-effort; un-coercible values are left as-is so the downstream
validator can report a clean per-row error instead of crashing the run). Used by the CSV
source today and the future REST source.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from loguru import logger

from core.services.contact_ingestion.row_mapping import parse_datetime_value

# Targets that are first-class contact columns rather than metadata keys.
_RESERVED_TARGETS = {"name", "phone_number", "external_id"}

# Field ``format`` values that mark a datetime column (parsed via parse_datetime_value
# using the field's ``field_metadata`` {datetime_format, timezone}).
_DATETIME_FORMATS = {"date", "datetime"}


def _coerce(value: Any, type_: str) -> Any:
    """Best-effort coerce ``value`` to ``type_``. On failure return the original value
    (the metadata validator will surface a clean per-row error)."""
    if value is None:
        return None
    if type_ in ("string", "enum"):
        return value if isinstance(value, str) else str(value)
    text = value.strip() if isinstance(value, str) else value
    if text == "" or text is None:
        return None
    try:
        if type_ == "integer":
            return int(text)
        if type_ == "number":
            return float(text)
        if type_ == "boolean":
            if isinstance(text, bool):
                return text
            return str(text).strip().lower() in {"true", "1", "yes", "y", "t"}
    except (ValueError, TypeError):
        logger.debug("[contact_ingestion] could not coerce {!r} to {}; keeping raw", value, type_)
        return value
    return value


def map_source_row_to_contact(raw: Dict[str, Any], schema_fields: Sequence) -> Dict[str, Any]:
    """Map one raw source row to a contact dict using a schema's fields.

    Args:
        raw: external header → cell value for one source record.
        schema_fields: the schema's ``SchemaField`` rows (active ones; caller-filtered).

    Returns:
        ``{"name", "phone_number", "external_id", "contact_metadata"}`` — reserved
        targets promoted to top level, everything else nested in ``contact_metadata``.
    """
    name: Optional[str] = None
    phone_number: Optional[str] = None
    external_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    for f in schema_fields:
        source_key = f.source_key if f.source_key else f.field_name
        if source_key not in raw:
            continue
        # A field marked as a date/datetime format parses through the shared datetime
        # parser using its configured source format + timezone (field_metadata), yielding
        # a normalized UTC ISO string; all other types use best-effort type coercion.
        if getattr(f, "format", None) in _DATETIME_FORMATS:
            raw_val = raw.get(source_key)
            cfg = getattr(f, "field_metadata", None) or {}
            value = parse_datetime_value(
                str(raw_val) if raw_val is not None else "",
                fmt=(cfg.get("datetime_format") or None),
                tz=(cfg.get("timezone") or None),
            )
        else:
            value = _coerce(raw.get(source_key), f.type)
        if f.field_name == "name":
            name = value if value in (None,) or isinstance(value, str) else str(value)
        elif f.field_name == "phone_number":
            phone_number = value if value in (None,) or isinstance(value, str) else str(value)
        elif f.field_name == "external_id":
            external_id = value if value in (None,) or isinstance(value, str) else str(value)
        else:
            if value is not None and value != "":
                metadata[f.field_name] = value

    return {
        "name": name,
        "phone_number": phone_number,
        "external_id": external_id,
        "contact_metadata": metadata,
    }
