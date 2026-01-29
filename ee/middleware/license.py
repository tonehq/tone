from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ee.config import ee_settings


class LicenseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not ee_settings.LICENSE_KEY:
            return JSONResponse(
                status_code=403,
                content={"detail": "Valid EE license required"}
            )

        response = await call_next(request)
        return response
