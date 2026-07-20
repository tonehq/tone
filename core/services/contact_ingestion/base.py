"""Data-source-agnostic contact ingestion.

A ``ContactSource`` parses a raw blob (whatever a data source hands us — a CSV file
today, an API export or spreadsheet tomorrow) into a stream of ``ParsedContact``.
Adding a new source = a new ``ContactSource`` subclass + a factory entry; nothing
downstream (the service upsert, the router, the parse job) has to change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional


@dataclass
class ParsedContact:
    """One normalized contact row, independent of the originating source format.

    ``phone_number`` is the dedicated dial target (E.164 where the source provided a
    parseable one). ``metadata`` holds every other column from the source, including an
    optional ``scheduled_at`` (ISO-8601) that later overrides a batch schedule time.
    """

    external_id: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContactSource(ABC):
    """Parse a raw blob into ``ParsedContact`` rows."""

    @abstractmethod
    def parse(self, raw: bytes) -> Iterator[ParsedContact]:
        """Yield one ``ParsedContact`` per source record. Blank rows are skipped."""
        raise NotImplementedError
