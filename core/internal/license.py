import json
import base64
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class LicenseTier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


TIER_CAPABILITIES = {
    LicenseTier.FREE: ["a", "c", "v", "p"],
    LicenseTier.PRO: ["a", "c", "v", "p", "t", "wa"],
    LicenseTier.ENTERPRISE: ["a", "c", "v", "p", "t", "wa", "au", "ss"],
}


PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAVGhpcyBpcyBhIHBsYWNlaG9sZGVyIGtleQAAAAAAAAA=
-----END PUBLIC KEY-----"""


@dataclass
class LicenseInfo:
    license_id: str
    organization_id: str
    tier: LicenseTier
    capabilities: List[str]
    seats: int
    expires_at: int
    issued_at: int
    fingerprint: Optional[str] = None
    is_valid: bool = False
    validation_error: Optional[str] = None


class LicenseValidator:
    def __init__(self, license_key: Optional[str] = None):
        self._license_key = license_key
        self._cached_info: Optional[LicenseInfo] = None
        self._last_validation: int = 0

    def _decode_license(self, license_key: str) -> Optional[Dict[str, Any]]:
        try:
            parts = license_key.split(".")
            if len(parts) != 2:
                return None

            payload_b64, signature_b64 = parts
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
            payload = json.loads(payload_bytes.decode("utf-8"))

            if HAS_CRYPTO:
                try:
                    public_key = serialization.load_pem_public_key(PUBLIC_KEY)
                    signature = base64.urlsafe_b64decode(signature_b64 + "==")
                    public_key.verify(signature, payload_bytes)
                except InvalidSignature:
                    return None
                except Exception:
                    pass

            return payload
        except Exception:
            return None

    def validate(self, fingerprint: Optional[str] = None) -> LicenseInfo:
        if not self._license_key:
            return LicenseInfo(
                license_id="",
                organization_id="",
                tier=LicenseTier.FREE,
                capabilities=TIER_CAPABILITIES[LicenseTier.FREE],
                seats=1,
                expires_at=0,
                issued_at=0,
                is_valid=True,
                validation_error=None,
            )

        payload = self._decode_license(self._license_key)
        if not payload:
            return LicenseInfo(
                license_id="",
                organization_id="",
                tier=LicenseTier.FREE,
                capabilities=TIER_CAPABILITIES[LicenseTier.FREE],
                seats=1,
                expires_at=0,
                issued_at=0,
                is_valid=False,
                validation_error="invalid_license_format",
            )

        try:
            tier = LicenseTier(payload.get("tier", "free"))
        except ValueError:
            tier = LicenseTier.FREE

        expires_at = payload.get("expires_at", 0)
        if expires_at and expires_at < int(time.time()):
            return LicenseInfo(
                license_id=payload.get("license_id", ""),
                organization_id=payload.get("organization_id", ""),
                tier=LicenseTier.FREE,
                capabilities=TIER_CAPABILITIES[LicenseTier.FREE],
                seats=1,
                expires_at=expires_at,
                issued_at=payload.get("issued_at", 0),
                fingerprint=payload.get("fingerprint"),
                is_valid=False,
                validation_error="license_expired",
            )

        license_fingerprint = payload.get("fingerprint")
        if license_fingerprint and fingerprint and license_fingerprint != fingerprint:
            return LicenseInfo(
                license_id=payload.get("license_id", ""),
                organization_id=payload.get("organization_id", ""),
                tier=LicenseTier.FREE,
                capabilities=TIER_CAPABILITIES[LicenseTier.FREE],
                seats=1,
                expires_at=expires_at,
                issued_at=payload.get("issued_at", 0),
                fingerprint=license_fingerprint,
                is_valid=False,
                validation_error="fingerprint_mismatch",
            )

        capabilities = payload.get("capabilities") or TIER_CAPABILITIES.get(tier, [])

        return LicenseInfo(
            license_id=payload.get("license_id", ""),
            organization_id=payload.get("organization_id", ""),
            tier=tier,
            capabilities=capabilities,
            seats=payload.get("seats", 1),
            expires_at=expires_at,
            issued_at=payload.get("issued_at", 0),
            fingerprint=license_fingerprint,
            is_valid=True,
            validation_error=None,
        )

    def get_info(self, fingerprint: Optional[str] = None) -> LicenseInfo:
        current_time = int(time.time())
        if self._cached_info and (current_time - self._last_validation) < 3600:
            return self._cached_info

        self._cached_info = self.validate(fingerprint)
        self._last_validation = current_time
        return self._cached_info


_license_validator: Optional[LicenseValidator] = None


def init_license_validator(license_key: Optional[str] = None) -> LicenseValidator:
    global _license_validator
    _license_validator = LicenseValidator(license_key)
    return _license_validator


def get_license_validator() -> LicenseValidator:
    global _license_validator
    if _license_validator is None:
        _license_validator = LicenseValidator()
    return _license_validator


def get_license_info(fingerprint: Optional[str] = None) -> LicenseInfo:
    return get_license_validator().get_info(fingerprint)
