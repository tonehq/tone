"""Unit tests for profile-variable source/source_path validation.

Pure logic — no DB. Run:
    pytest test-cases/test_profile_variable_source.py -v -o "addopts="
"""

import pytest

from core.services.agents.agent_profile_variable_service import (
    _validate_source,
    _validate_source_path,
)
from core.services.agents.errors import ProfileVariableInvalidError


class TestValidateSource:
    def test_defaults_to_static(self):
        assert _validate_source(None) == "static"
        assert _validate_source("") == "static"

    def test_accepts_webhook(self):
        assert _validate_source("webhook") == "webhook"

    def test_rejects_unknown(self):
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source("ftp")


class TestValidateSourcePath:
    def test_static_forces_none(self):
        assert _validate_source_path("static", "properties.name") is None
        assert _validate_source_path("static", None) is None

    def test_webhook_requires_path(self):
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source_path("webhook", "")
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source_path("webhook", "   ")

    def test_webhook_accepts_dot_path(self):
        assert _validate_source_path("webhook", "properties.name") == "properties.name"
        assert _validate_source_path("webhook", "data.customer.tier") == "data.customer.tier"

    def test_webhook_rejects_bad_path(self):
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source_path("webhook", "properties..name")
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source_path("webhook", "results[0].name")

    def test_webhook_rejects_oversize_path(self):
        with pytest.raises(ProfileVariableInvalidError):
            _validate_source_path("webhook", "a." * 200)
