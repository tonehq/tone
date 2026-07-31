"""CSV import for user-authored eval questions.

Owns only the CSV *byte* → *list-of-question-dicts* path. All persistence and
validation lives downstream in :meth:`EvalService.add_questions_manual` — the
CSV route is a thin adapter, so a manual UI entry and a CSV upload go through
the same identity/collision/kb-exists checks.

Expected columns (header row, case- and whitespace-tolerant):
    question               (required)
    expected_answer        (required)
    expected_source_snippet (optional)
    category               (optional)
    external_id            (optional; auto-minted as ``manual-<uuid>`` when absent)

Header aliases: ``id`` → ``external_id``. Unknown columns are ignored so users
can drop in a spreadsheet with extra bookkeeping columns without editing it.
"""

from __future__ import annotations

import csv
import io
from typing import Iterator, List, Optional

from loguru import logger

_REQUIRED_COLUMNS = ("question", "expected_answer")
_HEADER_ALIASES = {"id": "external_id"}
_ALLOWED_COLUMNS = {
    "question",
    "expected_answer",
    "expected_source_snippet",
    "category",
    "external_id",
}


class EvalCsvParseError(ValueError):
    """Raised when the CSV cannot be parsed or is missing required headers.
    Router callers map this to HTTP 400 so the user sees the exact reason."""


def _decode_csv_bytes(raw: bytes) -> str:
    """Tolerant CSV decoding — UTF-8 (BOM-aware for Excel exports), then
    cp1252/latin-1 so a spreadsheet with a stray non-UTF-8 byte (é, £, smart
    quote) doesn't hard-fail. Mirrors the tolerant decoder used by the
    contact-ingestion CSV source."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            logger.debug(
                "[eval] CSV not decodable as %s; trying next", encoding
            )
    return raw.decode("utf-8", errors="replace")


def _normalize_header(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    key = name.strip().lower().replace(" ", "_")
    return _HEADER_ALIASES.get(key, key)


def _iter_rows(reader: csv.DictReader) -> Iterator[dict]:
    for raw in reader:
        cleaned: dict = {}
        for k, v in raw.items():
            col = _normalize_header(k)
            if col is None or col not in _ALLOWED_COLUMNS:
                continue
            if v is None:
                continue
            # csv.DictReader hands back a list when a row has more columns
            # than the header (restkey collector); ignore those overflow cells.
            if isinstance(v, list):
                continue
            text = v.strip()
            if text:
                cleaned[col] = text
        if cleaned:
            yield cleaned


def parse_eval_questions_csv(raw: bytes) -> List[dict]:
    """Decode ``raw`` and return a list of question dicts ready to hand to
    :meth:`EvalService.add_questions_manual`. Does NOT validate individual row
    contents (empty ``question``/``expected_answer``, collisions, etc.) — that
    stays in the service so the CSV path and the manual path enforce the same
    rules."""
    text = _decode_csv_bytes(raw)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    normalized = {_normalize_header(f) for f in fieldnames}
    missing = [c for c in _REQUIRED_COLUMNS if c not in normalized]
    if missing:
        raise EvalCsvParseError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Expected headers: question, expected_answer "
            f"(optional: expected_source_snippet, category, external_id)."
        )
    rows = list(_iter_rows(reader))
    if not rows:
        raise EvalCsvParseError("CSV contains no data rows.")
    return rows
