"""Tests for license validation logic (core/internal/license.py).

Covers the skip_license_check flow and all license validation paths.
No mocks — tests the actual LicenseValidator class directly.
"""

import json
import base64
import time
import pytest

from core.internal.license import (
    LicenseValidator,
    LicenseInfo,
    LicenseTier,
    TIER_CAPABILITIES,
    init_license_validator,
    get_license_validator,
    get_license_info,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_license_key(payload: dict) -> str:
    """Encode a payload dict into the license key format: base64payload.base64signature."""
    payload_bytes = json.dumps(payload).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    # Use a dummy signature (signature validation is skipped in dev/test ENV)
    sig_b64 = base64.urlsafe_b64encode(b"test_signature_for_development").rstrip(b"=").decode()
    return f"{payload_b64}.{sig_b64}"


def _make_enterprise_payload(**overrides) -> dict:
    """Build a valid enterprise license payload."""
    now = int(time.time())
    payload = {
        "license_id": "test-license-001",
        "organization_id": "test-org-001",
        "tier": "enterprise",
        "capabilities": ["a", "c", "v", "p", "t", "wa", "au", "ss"],
        "seats": 10,
        "issued_at": now,
        "expires_at": now + 86400 * 365,  # 1 year from now
    }
    payload.update(overrides)
    return payload


def _make_pro_payload(**overrides) -> dict:
    """Build a valid pro license payload."""
    now = int(time.time())
    payload = {
        "license_id": "test-license-002",
        "organization_id": "test-org-002",
        "tier": "pro",
        "capabilities": ["a", "c", "v", "p", "t", "wa"],
        "seats": 5,
        "issued_at": now,
        "expires_at": now + 86400 * 365,
    }
    payload.update(overrides)
    return payload


# ===========================================================================
# SKIP LICENSE CHECK TESTS
# ===========================================================================

class TestSkipLicenseCheck:
    """Tests for the skip_license_check=True flow (EE without license key)."""

    def test_skip_returns_enterprise_tier(self):
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.tier == LicenseTier.ENTERPRISE

    def test_skip_returns_all_enterprise_capabilities(self):
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.capabilities == TIER_CAPABILITIES[LicenseTier.ENTERPRISE]

    def test_skip_is_valid(self):
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.is_valid is True

    def test_skip_no_validation_error(self):
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.validation_error is None

    def test_skip_license_id_is_skip(self):
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.license_id == "skip"

    def test_skip_ignores_provided_license_key(self):
        """Even if a license key is provided, skip_license_check takes priority."""
        validator = LicenseValidator(license_key="some-invalid-key", skip_license_check=True)
        info = validator.validate()
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True

    def test_skip_ignores_fingerprint(self):
        """Fingerprint validation is skipped when skip_license_check=True."""
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info = validator.validate(fingerprint="some-fingerprint")
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True

    def test_skip_get_info_caches_result(self):
        """get_info() should cache and return the same result within the TTL."""
        validator = LicenseValidator(license_key=None, skip_license_check=True)
        info1 = validator.get_info()
        info2 = validator.get_info()
        assert info1 is info2  # Same object due to caching


# ===========================================================================
# NO LICENSE KEY TESTS (FREE TIER)
# ===========================================================================

class TestNoLicenseKey:
    """Tests for when no license key is provided and skip is False."""

    def test_no_key_returns_free_tier(self):
        validator = LicenseValidator(license_key=None, skip_license_check=False)
        info = validator.validate()
        assert info.tier == LicenseTier.FREE

    def test_no_key_returns_free_capabilities(self):
        validator = LicenseValidator(license_key=None, skip_license_check=False)
        info = validator.validate()
        assert info.capabilities == TIER_CAPABILITIES[LicenseTier.FREE]
        assert info.capabilities == ["a", "c", "v", "p"]

    def test_no_key_is_valid(self):
        """No license key = valid free tier (not an error)."""
        validator = LicenseValidator(license_key=None, skip_license_check=False)
        info = validator.validate()
        assert info.is_valid is True

    def test_no_key_seats_is_one(self):
        validator = LicenseValidator(license_key=None, skip_license_check=False)
        info = validator.validate()
        assert info.seats == 1

    def test_empty_string_key_returns_free_tier(self):
        validator = LicenseValidator(license_key="", skip_license_check=False)
        info = validator.validate()
        assert info.tier == LicenseTier.FREE
        assert info.is_valid is True


# ===========================================================================
# VALID LICENSE KEY TESTS
# ===========================================================================

class TestValidLicenseKey:
    """Tests for valid license key decoding and validation."""

    def test_enterprise_license(self):
        payload = _make_enterprise_payload()
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate()
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True
        assert info.license_id == "test-license-001"
        assert info.organization_id == "test-org-001"
        assert info.seats == 10

    def test_pro_license(self):
        payload = _make_pro_payload()
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate()
        assert info.tier == LicenseTier.PRO
        assert info.is_valid is True
        assert info.capabilities == ["a", "c", "v", "p", "t", "wa"]

    def test_capabilities_from_payload(self):
        """Capabilities come from the payload, not just the tier default."""
        payload = _make_enterprise_payload(capabilities=["a", "c", "custom"])
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate()
        assert info.capabilities == ["a", "c", "custom"]

    def test_fingerprint_match(self):
        payload = _make_enterprise_payload(fingerprint="fp-abc-123")
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate(fingerprint="fp-abc-123")
        assert info.is_valid is True
        assert info.fingerprint == "fp-abc-123"


# ===========================================================================
# INVALID LICENSE KEY TESTS
# ===========================================================================

class TestInvalidLicenseKey:
    """Tests for invalid, expired, and tampered license keys."""

    def test_invalid_format_no_dot(self):
        validator = LicenseValidator(license_key="not-a-valid-key")
        info = validator.validate()
        assert info.is_valid is False
        assert info.validation_error == "invalid_license_format"
        assert info.tier == LicenseTier.FREE

    def test_invalid_format_too_many_dots(self):
        validator = LicenseValidator(license_key="a.b.c")
        info = validator.validate()
        assert info.is_valid is False
        assert info.validation_error == "invalid_license_format"

    def test_invalid_base64_payload(self):
        validator = LicenseValidator(license_key="!!!invalid!!!.signature")
        info = validator.validate()
        assert info.is_valid is False
        assert info.validation_error == "invalid_license_format"

    def test_expired_license(self):
        payload = _make_enterprise_payload(expires_at=int(time.time()) - 3600)  # Expired 1 hour ago
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate()
        assert info.is_valid is False
        assert info.validation_error == "license_expired"
        assert info.tier == LicenseTier.FREE

    def test_fingerprint_mismatch(self):
        payload = _make_enterprise_payload(fingerprint="expected-fp")
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate(fingerprint="different-fp")
        assert info.is_valid is False
        assert info.validation_error == "fingerprint_mismatch"
        assert info.tier == LicenseTier.FREE

    def test_unknown_tier_defaults_to_free(self):
        payload = _make_enterprise_payload(tier="premium_plus")
        key = _make_license_key(payload)
        validator = LicenseValidator(license_key=key)
        info = validator.validate()
        assert info.tier == LicenseTier.FREE
        assert info.is_valid is True  # Valid format, just unknown tier


# ===========================================================================
# GLOBAL INIT / GETTER TESTS
# ===========================================================================

class TestGlobalLicenseInit:
    """Tests for init_license_validator / get_license_validator / get_license_info."""

    def test_init_with_skip_returns_enterprise(self):
        validator = init_license_validator(license_key=None, skip_license_check=True)
        info = validator.validate()
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True

    def test_init_without_skip_returns_free(self):
        validator = init_license_validator(license_key=None, skip_license_check=False)
        info = validator.validate()
        assert info.tier == LicenseTier.FREE

    def test_get_license_validator_returns_initialized(self):
        init_license_validator(license_key=None, skip_license_check=True)
        validator = get_license_validator()
        info = validator.validate()
        assert info.tier == LicenseTier.ENTERPRISE

    def test_get_license_info_with_skip(self):
        init_license_validator(license_key=None, skip_license_check=True)
        info = get_license_info()
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True

    def test_get_license_info_with_valid_key(self):
        payload = _make_pro_payload()
        key = _make_license_key(payload)
        init_license_validator(license_key=key, skip_license_check=False)
        info = get_license_info()
        assert info.tier == LicenseTier.PRO
        assert info.is_valid is True
