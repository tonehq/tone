"""REST contact source (future — stub).

A placeholder ``ContactSource`` registered for the ``rest`` datasource type so the sync
pipeline's factory (``get_contact_source``) resolves it uniformly. It shares the same
``ContactSource`` ABC as ``CSVContactSource``; ``parse`` intentionally raises
``NotImplementedError`` until REST ingestion is built, so a misconfigured ``rest``
datasource fails loudly with a clear message rather than silently importing nothing.
"""

from __future__ import annotations

from typing import Iterator

from core.services.contact_ingestion.base import ContactSource, ParsedContact


class RestContactSource(ContactSource):
    """Future REST-datasource parser (not yet implemented)."""

    def parse(self, raw: bytes) -> Iterator[ParsedContact]:
        raise NotImplementedError(
            "RestContactSource is not implemented yet; only 'csv' datasources are supported."
        )
