"""Extract device + network info from an incoming request.

This module is the only place that talks to the User-Agent parser and to
request headers, so the rest of the codebase stays framework-agnostic and
testable. If the optional ``user-agents`` dependency is missing, parsing
fields stay ``None`` (the session row is still created — we just don't
show "Chrome / macOS" in the UI).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request

try:
    from user_agents import parse as _ua_parse  # type: ignore
except ImportError:  # pragma: no cover - optional dep, see requirements.txt
    _ua_parse = None


@dataclass
class DeviceContext:
    """Plain transport for the device fields stored on ``user_sessions``.

    Producers: ``extract_device_context`` (router boundary).
    Consumers: ``SessionService.create_session`` / ``rotate_session``.
    """

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    device_name: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First entry is the originating client; the rest are proxies.
        return forwarded.split(",")[0].strip() or None
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip() or None
    if request.client and request.client.host:
        return request.client.host
    return None


def _format_family_version(family: Optional[str], version: Optional[str]) -> Optional[str]:
    if not family or family == "Other":
        return None
    if version:
        return f"{family} {version}"
    return family


def _parsed_ua_fields(raw_ua: Optional[str]) -> dict:
    if not raw_ua or _ua_parse is None:
        return {}
    try:
        ua = _ua_parse(raw_ua)
    except Exception:
        return {}

    if ua.is_mobile:
        device_type = "mobile"
    elif ua.is_tablet:
        device_type = "tablet"
    elif ua.is_pc:
        device_type = "desktop"
    elif ua.is_bot:
        device_type = "bot"
    else:
        device_type = None

    return {
        "device_type": device_type,
        "device_name": (ua.device.family or None) if ua.device.family != "Other" else None,
        "browser": _format_family_version(ua.browser.family, ua.browser.version_string),
        "os": _format_family_version(ua.os.family, ua.os.version_string),
    }


def extract_device_context(request: Request) -> DeviceContext:
    """Pull IP + parsed UA from the request. Never raises."""
    raw_ua = request.headers.get("user-agent")
    parsed = _parsed_ua_fields(raw_ua)
    return DeviceContext(
        ip_address=_client_ip(request),
        user_agent=raw_ua,
        device_type=parsed.get("device_type"),
        device_name=parsed.get("device_name"),
        browser=parsed.get("browser"),
        os=parsed.get("os"),
    )
