"""Tolerant CSV byte→str decoding shared by the eval CSV importers.

Tries UTF-8 (BOM-aware for Excel exports), then cp1252 / latin-1 so a
spreadsheet with a stray non-UTF-8 byte (é, £, smart quote) doesn't hard-fail;
the final fallback replaces undecodable bytes rather than raising. Mirrors the
tolerant decoder used by the contact-ingestion CSV source.

Extracted from the byte-identical copies previously living in
``evals/csv_import.py`` and ``evals/agent_llm/scenario_service.py`` so there is
ONE implementation. ``log_tag`` lets each caller keep its own debug prefix.
"""

from __future__ import annotations

from loguru import logger


def decode_csv_bytes(raw: bytes, *, log_tag: str = "[eval]") -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            logger.debug("{} CSV not decodable as {}; trying next", log_tag, encoding)
    return raw.decode("utf-8", errors="replace")
