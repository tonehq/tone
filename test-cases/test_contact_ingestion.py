"""Unit tests for contact ingestion + per-row schedule-time resolution.

Pure logic, no DB:
- core/services/contact_ingestion/csv_source.py — CSV parsing/normalization.
- core/services/contact_ingestion/__init__.py — source factory.
- core/services/outbound_call_service.py::_resolve_contact_when — per-row schedule time.
"""

from datetime import datetime, timezone

import pytest

from core.services.contact_ingestion import get_contact_source
from core.services.contact_ingestion.base import ParsedContact
from core.services.contact_ingestion.csv_source import CSVContactSource
from core.services.outbound_call_service import OutboundCallService as Svc


def _parse(raw: str):
    return list(CSVContactSource().parse(raw.encode("utf-8")))


class TestCSVParsing:
    def test_one_parsed_contact_per_row(self):
        rows = _parse("name,phone_number\nAlice,+14155550123\nBob,+14155550124\n")
        assert len(rows) == 2
        assert rows[0].name == "Alice"
        assert rows[0].phone_number == "+14155550123"

    def test_headers_are_case_insensitive_and_aliased(self):
        rows = _parse("Name,Phone\nAlice,+14155550123\n")
        assert rows[0].name == "Alice"
        assert rows[0].phone_number == "+14155550123"

    def test_scheduled_at_goes_to_metadata_iso_utc(self):
        rows = _parse("name,phone,scheduled_at\nA,+14155550123,2026-08-01T15:30:00Z\n")
        assert rows[0].metadata["scheduled_at"] == "2026-08-01T15:30:00+00:00"

    def test_naive_scheduled_at_assumed_utc(self):
        rows = _parse("name,phone,call_time\nA,+14155550123,2026-08-01T15:30:00\n")
        assert rows[0].metadata["scheduled_at"] == "2026-08-01T15:30:00+00:00"

    def test_extra_columns_flow_to_metadata(self):
        rows = _parse("name,phone,company,notes\nA,+14155550123,Acme,VIP\n")
        assert rows[0].metadata["company"] == "Acme"
        assert rows[0].metadata["notes"] == "VIP"

    def test_required_marker_star_stripped_from_headers(self):
        # Sample templates mark required columns with a trailing ``*`` (e.g. ``city*``);
        # the marker is stripped so a filled-in template still maps to the real field.
        rows = _parse("name*,phone_number*,city*\nJohn Doe,+14155550123,SF\n")
        assert rows[0].name == "John Doe"
        assert rows[0].phone_number == "+14155550123"
        assert rows[0].metadata["city"] == "SF"

    def test_external_id_used_when_present(self):
        rows = _parse("external_id,name,phone\ncust-1,A,+14155550123\n")
        assert rows[0].external_id == "cust-1"

    def test_external_id_synthesized_from_phone_when_absent(self):
        rows = _parse("name,phone\nA,+14155550123\n")
        assert rows[0].external_id == "+14155550123"

    def test_external_id_stable_hash_when_no_phone(self):
        rows1 = _parse("name,company\nA,Acme\n")
        rows2 = _parse("name,company\nA,Acme\n")
        # Same row content → same synthesized id (idempotent re-import).
        assert rows1[0].external_id == rows2[0].external_id
        assert rows1[0].external_id.startswith("csv-")

    def test_blank_rows_skipped(self):
        rows = _parse("name,phone\nA,+14155550123\n,\n")
        assert len(rows) == 1

    def test_phone_normalization_strips_formatting(self):
        rows = _parse("name,phone\nA,(415) 555-0123\n")
        assert rows[0].phone_number == "4155550123"

    def test_phone_00_prefix_becomes_plus(self):
        rows = _parse("name,phone\nA,0044 20 7946 0000\n")
        assert rows[0].phone_number == "+442079460000"

    def test_unparseable_scheduled_at_dropped(self):
        rows = _parse("name,phone,scheduled_at\nA,+14155550123,not-a-date\n")
        assert "scheduled_at" not in rows[0].metadata

    def test_bom_tolerated(self):
        rows = list(CSVContactSource().parse("﻿name,phone\nA,+14155550123\n".encode("utf-8")))
        assert rows[0].name == "A"


class _FakeDatasource:
    """Minimal stand-in for a ``Datasource`` row — the factory only reads ``.type``."""

    def __init__(self, type):
        self.type = type


class TestSourceFactory:
    def test_csv_default(self):
        assert isinstance(get_contact_source(_FakeDatasource("csv")), CSVContactSource)

    def test_csv_case_insensitive(self):
        assert isinstance(get_contact_source(_FakeDatasource("CSV")), CSVContactSource)

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError):
            get_contact_source(_FakeDatasource("xlsx"))


class _FakeContact:
    def __init__(self, meta=None):
        self.id = "c-1"
        self.contact_metadata = meta or {}


class TestResolveContactWhen:
    def test_metadata_time_wins(self):
        future = "2999-01-01T00:00:00+00:00"
        c = _FakeContact({"scheduled_at": future})
        got = Svc._resolve_contact_when(c, None)
        assert got == datetime.fromisoformat(future)

    def test_request_time_used_when_no_metadata(self):
        req = datetime(2999, 6, 1, tzinfo=timezone.utc)
        got = Svc._resolve_contact_when(_FakeContact(), req)
        assert got == req

    def test_past_metadata_time_collapses_to_now(self):
        c = _FakeContact({"scheduled_at": "2000-01-01T00:00:00+00:00"})
        got = Svc._resolve_contact_when(c, None)
        assert (datetime.now(timezone.utc) - got).total_seconds() < 5

    def test_none_when_no_time_is_asap(self):
        got = Svc._resolve_contact_when(_FakeContact(), None)
        assert (datetime.now(timezone.utc) - got).total_seconds() < 5

    def test_unparseable_metadata_falls_back(self):
        req = datetime(2999, 6, 1, tzinfo=timezone.utc)
        c = _FakeContact({"scheduled_at": "garbage"})
        assert Svc._resolve_contact_when(c, req) == req


def test_parsed_contact_defaults():
    pc = ParsedContact(external_id="x")
    assert pc.name is None and pc.phone_number is None and pc.metadata == {}
