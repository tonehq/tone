"""Unit tests for the reusable contacts foundations (B0) — pure logic, no DB.

Covers the shared helpers every contacts service reuses:
- ``build_contact_field_json_schema`` / ``make_contact_metadata_validator`` /
  ``validate_contact_metadata`` (metadata validation ported from the old field-def
  service, now driven by ``SchemaField``-shaped rows).
- ``map_source_row_to_contact`` (source_key → field_name mapping + type coercion).
- ``apply_search_sort_pagination`` sort-key whitelisting semantics.
"""

from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional

import pytest

from core.services.common.list_query import apply_search_sort_pagination
from core.services.contact_ingestion.contact_mapping import map_source_row_to_contact
from core.services.contacts.contact_metadata_validation import (
    build_contact_field_json_schema,
    make_contact_metadata_validator,
    validate_contact_metadata,
)


@dataclass
class _Field:
    """Minimal stand-in for a ``SchemaField`` row (only the attrs the helpers read)."""

    field_name: str
    type: str = "string"
    is_mandatory: bool = False
    format: Optional[str] = None
    validators: Dict[str, Any] = dc_field(default_factory=dict)
    options: Optional[List[Any]] = None
    source_key: Optional[str] = None


# ---------------------------------------------------------------- validation


def test_build_json_schema_types_validators_and_required():
    fields = [
        _Field("first_name", type="string", is_mandatory=True, validators={"minLength": 2}),
        _Field("age", type="integer", validators={"minimum": 0}),
        _Field("tier", type="enum", options=[{"value": "gold"}, {"value": "silver"}]),
        _Field("subscribed", type="boolean"),
    ]
    schema = build_contact_field_json_schema(fields)
    props = schema["properties"]
    assert props["first_name"] == {"type": "string", "minLength": 2}
    assert props["age"] == {"type": "integer", "minimum": 0}
    assert props["tier"] == {"enum": ["gold", "silver"]}
    assert props["subscribed"] == {"type": "boolean"}
    assert schema["required"] == ["first_name"]


def test_validator_reports_errors_only_for_managed_keys():
    fields = [_Field("age", type="integer", is_mandatory=True, validators={"minimum": 18})]
    managed, validator = make_contact_metadata_validator(fields)
    assert managed == {"age"}

    # Valid + an unmanaged extra key -> no errors (extra keys are allowed).
    assert validate_contact_metadata({"age": 30, "extra": "ok"}, managed, validator) == []
    # Violates the minimum -> reported.
    assert validate_contact_metadata({"age": 5}, managed, validator)


def test_empty_fields_make_noop_validator():
    managed, validator = make_contact_metadata_validator([])
    assert managed == set()
    assert validator is None
    assert validate_contact_metadata({"anything": 1}, managed, validator) == []


def test_mandatory_field_present_but_empty_is_rejected():
    # A required field whose value is a blank/whitespace string (e.g. an empty CSV cell)
    # must fail its `required` constraint, not slip through as "present".
    fields = [_Field("city", type="string", is_mandatory=True)]
    managed, validator = make_contact_metadata_validator(fields)
    assert validate_contact_metadata({"city": "SF"}, managed, validator) == []
    assert validate_contact_metadata({"city": ""}, managed, validator)      # blank
    assert validate_contact_metadata({"city": "   "}, managed, validator)   # whitespace
    assert validate_contact_metadata({"city": None}, managed, validator)    # null
    assert validate_contact_metadata({}, managed, validator)                # missing


def test_mandatory_boolean_false_and_number_zero_are_valid():
    # 0 / False are real values — never treated as "empty" for required fields.
    fields = [
        _Field("opted_in", type="boolean", is_mandatory=True),
        _Field("score", type="integer", is_mandatory=True),
    ]
    managed, validator = make_contact_metadata_validator(fields)
    assert validate_contact_metadata({"opted_in": False, "score": 0}, managed, validator) == []


# ------------------------------------------------------------------ mapping


def test_map_source_row_remaps_source_key_to_field_name():
    fields = [
        _Field("name", source_key="Full Name"),
        _Field("phone_number", source_key="Mobile"),
        _Field("external_id", source_key="CRM ID"),
        _Field("age", type="integer", source_key="Age"),
    ]
    raw = {"Full Name": "Ada", "Mobile": "+15551230000", "CRM ID": "crm-1", "Age": "42"}
    mapped = map_source_row_to_contact(raw, fields)
    assert mapped["name"] == "Ada"
    assert mapped["phone_number"] == "+15551230000"
    assert mapped["external_id"] == "crm-1"
    assert mapped["contact_metadata"] == {"age": 42}  # coerced to int, nested in metadata


def test_map_source_row_null_source_key_is_identity():
    fields = [_Field("name"), _Field("company")]  # no source_key -> read from field_name
    raw = {"name": "Grace", "company": "Acme"}
    mapped = map_source_row_to_contact(raw, fields)
    assert mapped["name"] == "Grace"
    assert mapped["contact_metadata"] == {"company": "Acme"}


def test_map_source_row_skips_missing_and_blank():
    fields = [_Field("name"), _Field("note")]
    mapped = map_source_row_to_contact({"name": ""}, fields)  # note absent, name blank
    assert mapped["name"] == ""
    assert mapped["contact_metadata"] == {}  # blank/missing not written to metadata


# --------------------------------------------------------------- list_query


class _FakeQuery:
    """Tiny fake SQLAlchemy Query recording the applied order/offset/limit."""

    def __init__(self, rows):
        self._rows = rows
        self.ordered_by = None

    def filter(self, *a):  # search path unused here
        return self

    def count(self):
        return len(self._rows)

    def order_by(self, col):
        self.ordered_by = col
        return self

    def offset(self, n):
        self._offset = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def all(self):
        return self._rows[self._offset:self._offset + self._limit]


class _Col:
    def __init__(self, name):
        self.name = name

    def asc(self):
        return f"{self.name} asc"

    def desc(self):
        return f"{self.name} desc"


def test_pagination_and_whitelisted_sort():
    rows = list(range(10))
    q = _FakeQuery(rows)
    sort_map = {"name": _Col("name"), "created_at": _Col("created_at")}
    page, total = apply_search_sort_pagination(
        q, sort_by="name", sort_order="asc", sort_map=sort_map, page_no=2, page_size=3
    )
    assert total == 10
    assert page == [3, 4, 5]
    assert q.ordered_by == "name asc"


def test_unknown_sort_key_falls_back_to_first_map_entry():
    q = _FakeQuery(list(range(5)))
    sort_map = {"created_at": _Col("created_at")}
    _, _ = apply_search_sort_pagination(
        q, sort_by="not_a_column", sort_order="desc", sort_map=sort_map
    )
    assert q.ordered_by == "created_at desc"
