import ipaddress
import re
from typing import Any, Dict, List, Optional, Tuple

from shared.config import settings

SIP_TRANSPORTS = ("udp", "tcp", "tls")
AUTH_MODES = ("ip_acl", "digest")
MEDIA_ENCRYPTION_MODES = ("none", "srtp")
DEFAULT_SIP_PORT = 5060
DEFAULT_SIPS_PORT = 5061
DEFAULT_SIP_SAMPLE_RATE = 8000

_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
)
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")
_TECH_PREFIX_RE = re.compile(r"^[0-9*#]{1,32}$")


class SipConfigError(ValueError):
    pass


def default_port(transport: str) -> int:
    return DEFAULT_SIPS_PORT if transport == "tls" else DEFAULT_SIP_PORT


def normalize_host(raw: Any) -> str:
    host = str(raw or "").strip().lower()
    if not host:
        raise SipConfigError("Gateway host is required.")
    try:
        return str(ipaddress.ip_network(host, strict=False))
    except ValueError:
        pass
    if _HOSTNAME_RE.match(host):
        return host
    raise SipConfigError(f"'{host}' is not a valid hostname, IP address or CIDR block.")


def normalize_transport(raw: Any) -> str:
    transport = str(raw or "udp").strip().lower()
    if transport not in SIP_TRANSPORTS:
        raise SipConfigError(
            f"transport must be one of {', '.join(SIP_TRANSPORTS)} (got '{transport}')."
        )
    return transport


def normalize_port(raw: Any, transport: str) -> int:
    if raw in (None, "", 0):
        return default_port(transport)
    try:
        port = int(raw)
    except (TypeError, ValueError):
        raise SipConfigError(f"'{raw}' is not a valid SIP port.")
    if not 1 <= port <= 65535:
        raise SipConfigError("SIP port must be between 1 and 65535.")
    return port


def normalize_gateway(raw: Any, index: int) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise SipConfigError(f"Gateway #{index + 1} must be an object.")
    transport = normalize_transport(raw.get("transport"))
    return {
        "host": normalize_host(raw.get("host")),
        "port": normalize_port(raw.get("port"), transport),
        "transport": transport,
        "inbound_enabled": bool(raw.get("inbound_enabled", True)),
        "outbound_enabled": bool(raw.get("outbound_enabled", True)),
        "priority": int(raw.get("priority") or index + 1),
    }


def normalize_gateways(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise SipConfigError("At least one gateway is required.")
    gateways = [normalize_gateway(entry, index) for index, entry in enumerate(raw)]
    seen: set = set()
    for gateway in gateways:
        key = (gateway["host"], gateway["port"], gateway["transport"])
        if key in seen:
            raise SipConfigError(
                f"Duplicate gateway {gateway['host']}:{gateway['port']}/{gateway['transport']}."
            )
        seen.add(key)
    return sorted(gateways, key=lambda gateway: gateway["priority"])


def normalize_auth_mode(raw: Any) -> str:
    mode = str(raw or "ip_acl").strip().lower()
    if mode not in AUTH_MODES:
        raise SipConfigError(f"auth_mode must be one of {', '.join(AUTH_MODES)}.")
    return mode


def normalize_media_encryption(raw: Any) -> str:
    mode = str(raw or "none").strip().lower()
    if mode not in MEDIA_ENCRYPTION_MODES:
        raise SipConfigError(
            f"media_encryption must be one of {', '.join(MEDIA_ENCRYPTION_MODES)}."
        )
    return mode


def normalize_tech_prefix(raw: Any) -> Optional[str]:
    prefix = str(raw or "").strip()
    if not prefix:
        return None
    if not _TECH_PREFIX_RE.match(prefix):
        raise SipConfigError("tech_prefix may only contain digits, '*' and '#'.")
    return prefix


def normalize_auth(
    raw: Any, auth_mode: str, existing: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], Dict[str, Any]]:
    payload = raw if isinstance(raw, dict) else {}
    existing = existing or {}
    username = str(payload.get("auth_username") or existing.get("auth_username") or "").strip()
    password = str(payload.get("auth_password") or existing.get("auth_password") or "").strip()
    register_server = str(
        payload.get("register_server") or existing.get("register_server") or ""
    ).strip()

    if auth_mode != "digest":
        return (username or None, {"auth_username": username} if username else {})

    if not username or not password:
        raise SipConfigError(
            "auth_username and auth_password are required when auth_mode is 'digest'."
        )
    auth = {"auth_username": username, "auth_password": password}
    if register_server:
        auth["register_server"] = normalize_host(register_server)
    return username, auth


def validate_gateway_coverage(
    gateways: List[Dict[str, Any]], inbound_enabled: bool, outbound_enabled: bool
) -> None:
    if inbound_enabled and not any(gateway["inbound_enabled"] for gateway in gateways):
        raise SipConfigError(
            "Inbound is enabled but no gateway accepts inbound traffic."
        )
    if outbound_enabled and not any(gateway["outbound_enabled"] for gateway in gateways):
        raise SipConfigError(
            "Outbound is enabled but no gateway accepts outbound traffic."
        )


def termination_host(trunk_id: Any) -> str:
    domain = (settings.SIP_TERMINATION_FQDN or "").strip()
    return f"{trunk_id}.{domain}" if domain else ""


def inbound_uri_template(trunk_id: Any) -> str:
    host = termination_host(trunk_id)
    return f"sip:{{number}}@{host}" if host else ""


def outbound_gateways(gateways: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [gateway for gateway in gateways or [] if gateway.get("outbound_enabled", True)]


def inbound_source_hosts(gateways: List[Dict[str, Any]]) -> List[str]:
    return [
        gateway["host"]
        for gateway in gateways or []
        if gateway.get("inbound_enabled", True) and gateway.get("host")
    ]


def host_matches_source(host: str, source_ip: str) -> bool:
    if not host or not source_ip:
        return False
    try:
        address = ipaddress.ip_address(source_ip.strip())
    except ValueError:
        return False
    try:
        return address in ipaddress.ip_network(host, strict=False)
    except ValueError:
        return False


def is_e164(number: str) -> bool:
    return bool(_E164_RE.match((number or "").strip()))


def format_outbound_number(
    number: str,
    e164_check: bool = True,
    leading_plus: bool = True,
    tech_prefix: Optional[str] = None,
) -> str:
    dialed = (number or "").strip().replace(" ", "")
    if e164_check and not is_e164(dialed):
        raise SipConfigError(f"'{number}' is not a valid E.164 number.")
    if not leading_plus:
        dialed = dialed.lstrip("+")
    return f"{tech_prefix}{dialed}" if tech_prefix else dialed


def sip_uri(number: str, gateway: Dict[str, Any]) -> str:
    scheme = "sips" if gateway.get("transport") == "tls" else "sip"
    return f"{scheme}:{number}@{gateway['host']}:{gateway['port']};transport={gateway['transport']}"
