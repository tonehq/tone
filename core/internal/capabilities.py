from typing import List, Optional, Callable
from functools import wraps
from fastapi import HTTPException

from core.internal.license import get_license_info, LicenseInfo


CAPABILITY_CODES = {
    "a": "agents",
    "c": "channels",
    "v": "voices",
    "p": "providers",
    "t": "team",
    "wa": "workspace_admin",
    "au": "audit_logs",
    "ss": "sso",
}

BASE_CAPABILITIES = ["a", "c", "v", "p"]

_current_capabilities: List[str] = BASE_CAPABILITIES.copy()
_license_info: Optional[LicenseInfo] = None


def init_capabilities(fingerprint: Optional[str] = None, skip_license_check: bool = False) -> List[str]:
    global _current_capabilities, _license_info
    if skip_license_check:
        _current_capabilities = list(CAPABILITY_CODES.keys())
        _license_info = get_license_info(fingerprint)
    else:
        _license_info = get_license_info(fingerprint)
        if _license_info.is_valid:
            _current_capabilities = _license_info.capabilities
        else:
            _current_capabilities = BASE_CAPABILITIES.copy()
    return _current_capabilities


def get_capabilities() -> List[str]:
    return _current_capabilities.copy()


def get_current_license_info() -> Optional[LicenseInfo]:
    return _license_info


def has_capability(code: str) -> bool:
    return code in _current_capabilities


def is_ee_enabled() -> bool:
    return any(cap not in BASE_CAPABILITIES for cap in _current_capabilities)


def require_capability(capability_code: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not has_capability(capability_code):
                raise HTTPException(status_code=404, detail="Not found")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def capability_guard(capability_code: str):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not has_capability(capability_code):
                raise HTTPException(status_code=404, detail="Not found")
            return func(*args, **kwargs)
        return wrapper
    return decorator
