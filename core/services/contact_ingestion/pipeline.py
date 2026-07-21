"""Common parse → loop → validate pipeline for contact ingestion.

This is the ONE place the record loop lives. Any :class:`ContactSource` (CSV, Excel, a REST
sync provider, …) parses a raw blob into a stream of :class:`ParsedContact` — the common
data model — and :class:`RecordParser` iterates that stream once, validates each record
through a (composable) :class:`RecordValidator`, and partitions the results into ``valid``
records and ``invalid`` rows (with their errors). Downstream handlers (schedule calls,
directory upsert, …) consume ``ParseResult.valid`` and never re-implement the loop.

Flow (source-agnostic):

    select source → source.parse(raw) → RecordParser.process(records)
        → for each record: validator.validate(record)
        → ParseResult(valid=[...], invalid=[{index, name, phone_number, errors}], total)

Add a new data source = a new ``ContactSource`` subclass; add a new rule = a new
``RecordValidator`` in the composite. The loop below is untouched either way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from core.services.contact_ingestion.base import ContactSource, ParsedContact
from core.services.contact_ingestion.validation import RecordValidator


@dataclass
class ParseResult:
    """Outcome of running a record stream through the parser.

    ``valid`` are the records that passed every rule; ``invalid`` carries one entry per
    rejected record (its identity + the error messages) so callers can report exactly which
    rows failed and why. ``total`` is how many records were seen (post-truncation).
    """

    valid: List[ParsedContact] = field(default_factory=list)
    invalid: List[Dict[str, Any]] = field(default_factory=list)
    total: int = 0

    @property
    def valid_count(self) -> int:
        return len(self.valid)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid)


def parsed_contact_to_row(record: ParsedContact) -> Dict[str, Any]:
    """Convert the common :class:`ParsedContact` model into the ``rows`` dict shape that
    ``ContactService.create_contacts`` (and thus the Schedule→Assign→Create path) expects.
    One conversion, reused by every caller that turns parsed records into contacts."""
    return {
        "external_id": record.external_id,
        "name": record.name,
        "phone_number": record.phone_number,
        "contact_metadata": record.metadata or {},
    }


class RecordParser:
    """The single parse+loop+validate implementation, reused by every source and destination.

    Construct with a :class:`RecordValidator` (typically a
    :class:`~core.services.contact_ingestion.validation.CompositeValidator`). ``max_records``
    is optional and defaults to ``None`` (unlimited) — pass an int only where a hard cap is
    genuinely wanted. Call :meth:`parse` with a source + raw bytes, or :meth:`process` with
    an already-parsed record iterable (e.g. the Contact-Create API, which skips parsing).
    """

    def __init__(self, validator: RecordValidator, *, max_records: Optional[int] = None):
        self._validator = validator
        self._max_records = max_records

    def parse(self, source: ContactSource, raw: bytes) -> ParseResult:
        """Parse ``raw`` with ``source`` and run every record through validation."""
        return self.process(source.parse(raw))

    def process(self, records: Iterable[ParsedContact]) -> ParseResult:
        """Loop ``records`` once, validating each; partition into valid / invalid."""
        result = ParseResult()
        for index, record in enumerate(records):
            if self._max_records is not None and index >= self._max_records:
                result.invalid.append(
                    {
                        "index": index,
                        "name": None,
                        "phone_number": None,
                        "errors": [f"Import truncated at {self._max_records} rows."],
                    }
                )
                break
            result.total += 1
            errors = self._validator.validate(record)
            if errors:
                result.invalid.append(
                    {
                        "index": index,
                        "name": record.name,
                        "phone_number": record.phone_number,
                        "errors": errors,
                    }
                )
            else:
                result.valid.append(record)
        return result
