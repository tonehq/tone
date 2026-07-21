"""Contact ingestion package — data-source-agnostic parsing of contact blobs.

Two selection paths:

- ``get_contact_source(datasource)`` — dispatch on ``datasource.type`` (``csv`` / ``rest``)
  for a configured ``Datasource`` row.
- ``select_source_for_upload(raw)`` — for an *uploaded file* (a ``csv``-type datasource),
  sniff the leading magic bytes to pick CSV vs ``.xlsx`` and reject legacy ``.xls``.

Adding a new datasource type is a new ``ContactSource`` subclass plus one entry in
``_SOURCES``; adding a new upload file-format is a new subclass wired into
``select_source_for_upload``.
"""

from __future__ import annotations

from typing import Dict, Type

from core.services.contact_ingestion.base import ContactSource, ParsedContact
from core.services.contact_ingestion.csv_source import CSVContactSource
from core.services.contact_ingestion.excel_source import ExcelContactSource
from core.services.contact_ingestion.pipeline import (
    ParseResult,
    RecordParser,
    parsed_contact_to_row,
)
from core.services.contact_ingestion.rest_source import RestContactSource
from core.services.contact_ingestion.validation import (
    CompositeValidator,
    PhoneNumberValidator,
    RecordValidator,
    RequiredIdentityValidator,
    SchemaMetadataValidator,
)

# datasource.type -> parser. New source types register exactly one entry here.
_SOURCES: Dict[str, Type[ContactSource]] = {
    "csv": CSVContactSource,
    "rest": RestContactSource,
}

# Leading magic bytes used to sniff an uploaded file's real format (extension is not
# trusted). ``.xlsx`` is a ZIP container; legacy ``.xls`` is an OLE2 compound file.
_XLSX_MAGIC = b"PK\x03\x04"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def get_contact_source(datasource) -> ContactSource:
    """Return a ``ContactSource`` for a ``Datasource`` row, keyed by ``datasource.type``.

    ``datasource`` is any object exposing a ``.type`` attribute (a ``Datasource`` model
    row). Raises ``ValueError`` for an unsupported type so a misconfigured sync fails
    loudly instead of silently importing nothing.
    """
    source_type = getattr(datasource, "type", None)
    key = (source_type or "csv").strip().lower()
    source_cls = _SOURCES.get(key)
    if source_cls is None:
        raise ValueError(
            f"Unsupported datasource type {source_type!r}. "
            f"Supported: {', '.join(sorted(_SOURCES))}."
        )
    return source_cls()


def select_source_for_upload(raw: bytes) -> ContactSource:
    """Pick a ``ContactSource`` for an uploaded file by sniffing its leading magic bytes.

    - ``.xlsx`` (ZIP, ``PK\\x03\\x04``) -> :class:`ExcelContactSource`
    - legacy ``.xls`` (OLE2 compound file) -> ``ValueError`` (unsupported; the caller marks
      the sync ``failed`` with this friendly message)
    - anything else -> :class:`CSVContactSource` (the historical default; the CSV path is
      tolerant of encodings and non-CSV blobs simply import nothing)

    Content — not the filename/extension — decides, so a ``.csv`` that is really an
    ``.xlsx`` (or vice-versa) is still parsed correctly.
    """
    head = raw[:8] if raw else b""
    if head.startswith(_XLSX_MAGIC):
        return ExcelContactSource()
    if head.startswith(_OLE2_MAGIC):
        raise ValueError(
            "Legacy .xls files are not supported — please save the file as .xlsx or CSV "
            "and re-upload."
        )
    return CSVContactSource()


__all__ = [
    "ContactSource",
    "ParsedContact",
    "CSVContactSource",
    "ExcelContactSource",
    "RestContactSource",
    "get_contact_source",
    "select_source_for_upload",
    # Parse → loop → validate framework (reusable across data sources / destinations).
    "RecordParser",
    "ParseResult",
    "parsed_contact_to_row",
    "RecordValidator",
    "CompositeValidator",
    "PhoneNumberValidator",
    "RequiredIdentityValidator",
    "SchemaMetadataValidator",
]
