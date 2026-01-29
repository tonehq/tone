from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.context import set_tenant_context, clear_tenant_context


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("tenant_id") or request.headers.get("x-tenant-id")

        if tenant_id:
            set_tenant_context(org_id=int(tenant_id))

        try:
            response = await call_next(request)
            return response
        finally:
            clear_tenant_context()
