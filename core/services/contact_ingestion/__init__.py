"""Contact ingestion package — data-source-agnostic parsing of contact blobs.

Use ``get_contact_source(datasource)`` to obtain a parser for a ``Datasource`` row; the
factory dispatches on ``datasource.type`` (``csv`` today, ``rest`` later). Adding a new
source is a new ``ContactSource`` subclass plus one entry in ``_SOURCES``.
"""

from __future__ import annotations

from typing import Dict, Type

from core.services.contact_ingestion.base import ContactSource, ParsedContact
from core.services.contact_ingestion.csv_source import CSVContactSource
from core.services.contact_ingestion.rest_source import RestContactSource

# datasource.type -> parser. New source types register exactly one entry here.
_SOURCES: Dict[str, Type[ContactSource]] = {
    "csv": CSVContactSource,
    "rest": RestContactSource,
}


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


__all__ = [
    "ContactSource",
    "ParsedContact",
    "CSVContactSource",
    "RestContactSource",
    "get_contact_source",
]
