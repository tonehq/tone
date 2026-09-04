"""Unit tests for `_optional_json`, the request-body coercion behind model
`meta_data` / `meta_data_schema` writes.

`create_provider_model` / `update_provider_model` previously accepted neither
field, so a model created through the API or the UI was stored without its
per-model metadata: the agent-config validator then fell back to the
provider-level schema and no per-model override was possible. These cover the
type guard added with the fields, since a wrong-typed body must fail loudly
rather than persist a shape the rest of the stack cannot read
(`Model.meta_data` is a JSON object, `Model.meta_data_schema` a JSON array).

Pure logic — no DB, no HTTP client.

Run:
    pytest test-cases/test_provider_model_metadata_body.py -v -o "addopts="
"""

import pytest
from fastapi import HTTPException, status

from core.services.model_provider_service import _optional_json


class TestOptionalJson:
    def test_missing_key_returns_none(self):
        assert _optional_json({}, "meta_data", expect=dict) is None

    def test_explicit_null_returns_none(self):
        assert _optional_json({"meta_data": None}, "meta_data", expect=dict) is None

    def test_object_passes_through_unchanged(self):
        body = {"meta_data": {"model": "sarvam-105b"}}
        assert _optional_json(body, "meta_data", expect=dict) == {"model": "sarvam-105b"}

    def test_array_passes_through_unchanged(self):
        schema = [{"name": "temperature", "data_type": "float"}]
        assert _optional_json({"meta_data_schema": schema},
                              "meta_data_schema", expect=list) == schema

    def test_empty_object_and_array_survive(self):
        # Falsy but present: must not be silently coerced to None.
        assert _optional_json({"meta_data": {}}, "meta_data", expect=dict) == {}
        assert _optional_json({"meta_data_schema": []},
                              "meta_data_schema", expect=list) == []

    @pytest.mark.parametrize("value", [[], "string", 3, True])
    def test_non_object_rejected_when_object_expected(self, value):
        with pytest.raises(HTTPException) as exc:
            _optional_json({"meta_data": value}, "meta_data", expect=dict)
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be a JSON object" in exc.value.detail

    @pytest.mark.parametrize("value", [{}, "string", 3])
    def test_non_array_rejected_when_array_expected(self, value):
        with pytest.raises(HTTPException) as exc:
            _optional_json({"meta_data_schema": value},
                           "meta_data_schema", expect=list)
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be a JSON array" in exc.value.detail

    def test_error_names_the_offending_field(self):
        with pytest.raises(HTTPException) as exc:
            _optional_json({"meta_data": "x"}, "meta_data", expect=dict)
        assert "meta_data" in exc.value.detail
