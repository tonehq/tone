"""Per-request context middleware.

Stamps a UUID ``request_id`` on every inbound HTTP request, captures the
client IP and User-Agent, and writes them into the request-scoped
``RequestContext`` so downstream service code can read them without
needing access to the FastAPI ``Request`` object.

The same ``request_id`` is echoed back as ``X-Request-ID`` on the
response so clients (and the audit-log UI) can correlate a server log
entry, an audit row, and the HTTP call that produced it.
"""
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.context import clear_request_context, set_request_context


REQUEST_ID_HEADER = "X-Request-ID"


def _client_ip(request: Request) -> Optional[str]:
    """Return the originating client IP, honouring reverse-proxy headers.

    Behind a load balancer or ingress, ``request.client.host`` is the proxy
    address — useless for an audit trail. ``X-Forwarded-For`` carries the
    chain of forwarders with the original client first, so we take element
    zero when present. Falls back to the direct connection IP.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        user_agent = request.headers.get("user-agent")

        set_request_context(
            request_id=request_id,
            ip_address=_client_ip(request),
            user_agent=user_agent,
        )
        try:
            response = await call_next(request)
        finally:
            clear_request_context()

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
