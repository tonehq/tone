"""CSV contact source (stdlib ``csv``).

Owns only the CSV *byte* path: tolerant decoding + ``csv.DictReader``. The actual header
normalization and ``header -> ParsedContact`` mapping live in the shared
:func:`~core.services.contact_ingestion.row_mapping.map_rows_to_parsed_contacts`, which is
also used by :class:`~core.services.contact_ingestion.excel_source.ExcelContactSource` — so
a CSV and its equivalent ``.xlsx`` produce identical contacts.
"""

from __future__ import annotations

import csv
import io
from typing import Iterator, Optional

from loguru import logger

from core.services.contact_ingestion.base import ContactSource, ParsedContact
from core.services.contact_ingestion.row_mapping import map_rows_to_parsed_contacts


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


class CSVContactSource(ContactSource):
    def parse(self, raw: bytes) -> Iterator[ParsedContact]:
        text = _decode_csv_bytes(raw)  # BOM-aware UTF-8, then cp1252/latin-1 fallback
        reader = csv.DictReader(io.StringIO(text))
        fieldnames: Optional[list] = reader.fieldnames
        if not fieldnames:
            return
        # DictReader yields ``header -> value`` dicts; the shared mapper owns normalization,
        # reserved-field promotion, dedup and external_id synthesis.
        yield from map_rows_to_parsed_contacts(reader)
