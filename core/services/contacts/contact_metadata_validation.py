"""Reusable contact-metadata validation — compose a schema's fields into one JSON
Schema and validate a contact's ``contact_metadata`` against it.

Ported from the old ``ContactFieldDefinitionService`` (now removed): the same logic,
but operating on a schema's ``SchemaField`` rows instead of org-level field definitions.
Reused by manual create, multi-add, and per-row sync validation — build the validator
ONCE (``make_contact_metadata_validator``) and reuse it across many rows.

Only a constrained JSON-Schema subset is honoured from ``validators`` (minLength,
maxLength, pattern, minimum, maximum) so a user can't inject arbitrary/exploitable
schema; ``enum`` choices come from ``options``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from jsonschema import Draft7Validator

# Validator keys accepted per underlying JSON-Schema primitive.
_STRING_VALIDATORS = {"minLength", "maxLength", "pattern"}
_NUMBER_VALIDATORS = {"minimum", "maximum"}


def build_contact_field_json_schema(fields: Sequence) -> Dict[str, Any]:
    """Compose a schema's ``SchemaField`` rows into one JSON Schema object.

    Each field's ``field_name`` becomes a property keyed by ``type`` (string/number/
    integer/boolean/enum), carrying its whitelisted validators + optional ``format``.
    Mandatory fields go into ``required``. Only active (caller-filtered) fields should
    be passed in.
    """
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for f in fields:
        prop: Dict[str, Any] = {}
        if f.type == "enum":
            prop["enum"] = [
                o.get("value") if isinstance(o, dict) else o for o in (f.options or [])
            ]
        elif f.type == "boolean":
            prop["type"] = "boolean"
        elif f.type == "integer":
            prop["type"] = "integer"
        elif f.type == "number":
            prop["type"] = "number"
        else:
            prop["type"] = "string"
        for k, v in (f.validators or {}).items():
            if k in _STRING_VALIDATORS or k in _NUMBER_VALIDATORS:
                prop[k] = v
        if f.format:
            prop["format"] = f.format
        properties[f.field_name] = prop
        if f.is_mandatory:
            required.append(f.field_name)
    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def make_contact_metadata_validator(
    fields: Sequence,
) -> Tuple[Set[str], Optional[Draft7Validator]]:
    """Build ``(managed_keys, Draft7Validator)`` from a schema's fields.

    Returns ``(set(), None)`` when there are no fields, so callers can cheaply skip
    validation. Build once and reuse across every row of an import rather than
    re-composing the schema per row.
    """
    if not fields:
        return set(), None
    managed = {f.field_name for f in fields}
    return managed, Draft7Validator(build_contact_field_json_schema(fields))


def _is_empty(value: Any) -> bool:
    """A value counts as "not provided" for required-field enforcement when it is None
    or a blank/whitespace-only string (e.g. an empty CSV cell). Numbers/booleans —
    including ``0`` and ``False`` — are real values and never treated as empty."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def validate_contact_metadata(
    metadata: Optional[Dict[str, Any]],
    managed: Set[str],
    validator: Optional[Draft7Validator],
) -> List[str]:
    """Validate one metadata dict against a prebuilt validator, returning a list of
    human-readable error strings (empty = valid).

    Only keys that are ``managed`` (have a field in the schema) are constrained;
    unmanaged extra keys are allowed through (e.g. surplus CSV columns). Empty values
    (None / blank string — a blank CSV cell or cleared input) are dropped so a mandatory
    field that is *present but empty* still fails its ``required`` constraint.
    """
    if validator is None:
        return []
    subset = {
        k: v for k, v in (metadata or {}).items() if k in managed and not _is_empty(v)
    }
    errors: List[str] = []
    for err in validator.iter_errors(subset):
        loc = ".".join(str(p) for p in err.path)
        errors.append(f"{loc}: {err.message}" if loc else err.message)
    return errors
