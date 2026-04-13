"""Tests for capabilities module (core/internal/capabilities.py).

Covers skip_license_check flow, capability detection, and is_ee_enabled logic.
No mocks — tests the actual module functions directly.
"""

import pytest

from core.internal.license import (
    LicenseTier,
    TIER_CAPABILITIES,
    init_license_validator,
)
from core.internal.capabilities import (
    CAPABILITY_CODES,
    BASE_CAPABILITIES,
    init_capabilities,
    get_capabilities,
    get_current_license_info,
    has_capability,
    is_ee_enabled,
)


# ===========================================================================
# SKIP LICENSE CHECK → ALL CAPABILITIES
# ===========================================================================

class TestSkipLicenseCheckCapabilities:
    """When skip_license_check=True, all capabilities should be enabled."""

    def setup_method(self):
        """Reset the license validator before each test."""
        init_license_validator(license_key=None, skip_license_check=True)

    def test_init_returns_all_capability_codes(self):
        caps = init_capabilities(skip_license_check=True)
        assert set(caps) == set(CAPABILITY_CODES.keys())

    def test_has_all_base_capabilities(self):
        init_capabilities(skip_license_check=True)
        for cap in BASE_CAPABILITIES:
            assert has_capability(cap) is True

    def test_has_ee_capabilities(self):
        init_capabilities(skip_license_check=True)
        assert has_capability("t") is True   # team
        assert has_capability("wa") is True  # workspace_admin
        assert has_capability("au") is True  # audit_logs
        assert has_capability("ss") is True  # sso

    def test_is_ee_enabled_true(self):
        init_capabilities(skip_license_check=True)
        assert is_ee_enabled() is True

    def test_get_capabilities_returns_copy(self):
        init_capabilities(skip_license_check=True)
        caps1 = get_capabilities()
        caps2 = get_capabilities()
        assert caps1 == caps2
        assert caps1 is not caps2  # Must be a copy

    def test_license_info_is_enterprise(self):
        init_capabilities(skip_license_check=True)
        info = get_current_license_info()
        assert info is not None
        assert info.tier == LicenseTier.ENTERPRISE
        assert info.is_valid is True


# ===========================================================================
# NO LICENSE (FREE TIER) → BASE CAPABILITIES ONLY
# ===========================================================================

class TestFreeTierCapabilities:
    """When no license key and skip=False, only base capabilities."""

    def setup_method(self):
        init_license_validator(license_key=None, skip_license_check=False)

    def test_init_returns_base_capabilities(self):
        caps = init_capabilities(skip_license_check=False)
        assert caps == BASE_CAPABILITIES

    def test_has_base_capabilities(self):
        init_capabilities(skip_license_check=False)
        assert has_capability("a") is True   # agents
        assert has_capability("c") is True   # channels
        assert has_capability("v") is True   # voices
        assert has_capability("p") is True   # providers

    def test_no_ee_capabilities(self):
        init_capabilities(skip_license_check=False)
        assert has_capability("t") is False   # team
        assert has_capability("wa") is False  # workspace_admin
        assert has_capability("au") is False  # audit_logs
        assert has_capability("ss") is False  # sso

    def test_is_ee_enabled_false(self):
        init_capabilities(skip_license_check=False)
        assert is_ee_enabled() is False

    def test_license_info_is_free(self):
        init_capabilities(skip_license_check=False)
        info = get_current_license_info()
        assert info is not None
        assert info.tier == LicenseTier.FREE


# ===========================================================================
# CAPABILITY CODES MAPPING
# ===========================================================================

class TestCapabilityCodes:
    """Verify the capability code mapping is correct."""

    def test_base_capabilities_are_subset(self):
        assert set(BASE_CAPABILITIES).issubset(set(CAPABILITY_CODES.keys()))

    def test_all_tiers_have_base_capabilities(self):
        for tier in LicenseTier:
            caps = TIER_CAPABILITIES[tier]
            for base_cap in BASE_CAPABILITIES:
                assert base_cap in caps, f"Tier {tier.value} missing base capability {base_cap}"

    def test_enterprise_has_all_capabilities(self):
        enterprise_caps = TIER_CAPABILITIES[LicenseTier.ENTERPRISE]
        assert set(enterprise_caps) == set(CAPABILITY_CODES.keys())

    def test_pro_has_team_and_workspace_admin(self):
        pro_caps = TIER_CAPABILITIES[LicenseTier.PRO]
        assert "t" in pro_caps
        assert "wa" in pro_caps

    def test_free_does_not_have_ee_capabilities(self):
        free_caps = TIER_CAPABILITIES[LicenseTier.FREE]
        assert "t" not in free_caps
        assert "wa" not in free_caps
        assert "au" not in free_caps
        assert "ss" not in free_caps
