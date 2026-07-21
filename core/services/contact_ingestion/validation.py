"""Reusable, extensible record-validation framework.

A :class:`RecordValidator` inspects ONE normalized :class:`ParsedContact` (the common data
model every source is parsed into) and returns a list of human-readable error strings —
empty means the record is valid. Rules are composed with :class:`CompositeValidator`, so a
new validation rule is a new :class:`RecordValidator` subclass added to the composite; the
processing loop (:mod:`core.services.contact_ingestion.pipeline`) never changes.

Because validators operate on ``ParsedContact`` — not on a CSV row, an Excel row or a REST
payload — the SAME validator works for every data source. Reuse this anywhere records are
imported (schedule-call uploads, directory syncs, future third-party providers).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from core.services.contact_ingestion.base import ParsedContact
from core.services.contacts.contact_metadata_validation import (
    make_contact_metadata_validator,
    validate_contact_metadata,
)

# Strict E.164 (matches OutboundCallService's dial-target check): a leading '+', a non-zero
# country code, then 6–14 more digits.
_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class RecordValidator(ABC):
    """Validate one :class:`ParsedContact`; return a list of error strings (empty = valid).

    Stateless and reusable — build once, apply to every record in a stream.
    """

    @abstractmethod
    def validate(self, record: ParsedContact) -> List[str]:
        raise NotImplementedError


class CompositeValidator(RecordValidator):
    """Run a sequence of validators against a record and aggregate their errors.

    This is the extensibility seam: add rules with the constructor or :meth:`add` without
    touching the parsing/processing loop. An empty composite validates everything (no rules).
    """

    def __init__(self, rules: Optional[Sequence[RecordValidator]] = None):
        self._rules: List[RecordValidator] = list(rules or [])

    def add(self, rule: RecordValidator) -> "CompositeValidator":
        """Append a rule; returns self so rules can be chained fluently."""
        self._rules.append(rule)
        return self

    def validate(self, record: ParsedContact) -> List[str]:
        errors: List[str] = []
        for rule in self._rules:
            errors.extend(rule.validate(record))
        return errors


def build_contact_validator(
    schema_fields: Optional[Sequence] = None,
    *,
    require_phone: bool = False,
) -> CompositeValidator:
    """The ONE place contact-import validation is composed, so every source and destination
    validates the same way. Rules are assembled from the DESTINATION context, not the source:

    - dialing destinations (``require_phone=True``) require a valid E.164 phone (which also
      satisfies identity, so it replaces the name-or-phone check);
    - other destinations require at least a name OR phone (``RequiredIdentityValidator``);
    - when the destination has a schema (``schema_fields`` non-empty), the record's metadata is
      validated against it (``SchemaMetadataValidator``); with no schema that rule is skipped.

    Reused by the outbound file upload (phone-required, no schema) and the contact-create /
    multi-add API (schema-aware, phone optional). Extend the rule set HERE — never rebuild a
    ``CompositeValidator`` at a call site. (Directory syncs upsert by ``external_id`` and emit
    structured per-field errors, so they compose their own identity check but share the same
    underlying metadata validator via ``make_contact_metadata_validator``.)
    """
    rules: List[RecordValidator] = [
        PhoneNumberValidator() if require_phone else RequiredIdentityValidator()
    ]
    if schema_fields:
        rules.append(SchemaMetadataValidator(schema_fields))
    return CompositeValidator(rules)


class PhoneNumberValidator(RecordValidator):
    """Require a valid E.164 phone number — the dial target for an outbound call."""

    def validate(self, record: ParsedContact) -> List[str]:
        number = (record.phone_number or "").strip()
        if not number:
            return ["A phone number is required."]
        if not _E164_RE.match(number):
            return [f"'{number}' is not a valid E.164 phone number (e.g. +14155550123)."]
        return []


class RequiredIdentityValidator(RecordValidator):
    """Require at least a name or a phone number, so a contact is never identity-less."""

    def validate(self, record: ParsedContact) -> List[str]:
        if not (record.name or "").strip() and not (record.phone_number or "").strip():
            return ["A contact needs at least a name or phone number."]
        return []


class SchemaMetadataValidator(RecordValidator):
    """Validate a record's ``metadata`` against a ``ContactSchema``'s fields.

    Reuses the existing :func:`make_contact_metadata_validator` /
    :func:`validate_contact_metadata` (the SAME logic the manual-create and sync paths use),
    so there is one metadata-validation implementation. Build once from the schema's active
    fields and reuse across the whole record stream.
    """

    def __init__(self, schema_fields: Sequence):
        self._managed, self._validator = make_contact_metadata_validator(schema_fields)

    def validate(self, record: ParsedContact) -> List[str]:
        return validate_contact_metadata(record.metadata, self._managed, self._validator)
