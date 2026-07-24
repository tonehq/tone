from datetime import timedelta
from fastapi import HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, Union
from uuid import UUID
import time
from pydantic import BaseModel
from jose import JWTError, jwt

from core.config import settings
from core.context import set_tenant_context
from core.database.session import get_db
from core.internal.capabilities import is_ee_enabled


security = HTTPBearer()

# ── httpOnly auth-cookie transport ──────────────────────────────────────
# Access/refresh JWTs live in httpOnly cookies (unreadable by JS) instead of
# localStorage. The access cookie is sent on every request (path=/); the
# refresh cookie is scoped to the auth routes so it isn't attached to normal
# API traffic. Attributes come from settings so dev (host-only, insecure) and
# prod (.trytone.ai, secure) differ only by config.
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
# Both cookies are set site-wide (Path=/). Scoping the refresh cookie to the
# auth routes was a minor hardening, but a path-scoped Set-Cookie is fragile
# behind the Next.js dev proxy (the site-wide access cookie survives while the
# scoped refresh cookie gets dropped — e.g. on org-switch). Keeping them
# symmetric makes set/rotate/clear behave identically. Still httpOnly + Secure.
REFRESH_COOKIE_PATH = "/"


def _cookie_attrs() -> Dict[str, Any]:
    return {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN or None,
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: Optional[str] = None,
) -> None:
    """Attach the access (and optionally refresh) JWT as httpOnly cookies.

    Both cookies are given the *session* (refresh-token) lifetime, not the
    short access-token TTL. The access JWT inside still expires quickly and is
    rotated by silent ``/auth/refresh``; keeping the cookie alive for the whole
    session means the Next.js middleware's presence-check and the silent
    refresh keep working after the JWT expires — otherwise the user would be
    bounced to /login every time the access token lapsed.
    """
    attrs = _cookie_attrs()
    session_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=session_max_age,
        path="/",
        **attrs,
    )
    if refresh_token is not None:
        response.set_cookie(
            key=REFRESH_COOKIE,
            value=refresh_token,
            max_age=session_max_age,
            path=REFRESH_COOKIE_PATH,
            **attrs,
        )


def clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies (used on logout). Attributes must match the
    ones used to set them or the browser keeps the cookie."""
    domain = settings.COOKIE_DOMAIN or None
    response.delete_cookie(
        key=ACCESS_COOKIE, path="/", domain=domain,
        secure=settings.COOKIE_SECURE, httponly=True, samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, domain=domain,
        secure=settings.COOKIE_SECURE, httponly=True, samesite=settings.COOKIE_SAMESITE,
    )


def set_cookies_and_strip(response: Response, result: Dict[str, Any]) -> Dict[str, Any]:
    """Move any tokens in an auth-service result dict into httpOnly cookies and
    drop them from the JSON body. No-op when the result carries no access token
    (e.g. signup pending email verification, invite-accept without auto-login)."""
    if isinstance(result, dict) and result.get("access_token"):
        set_auth_cookies(response, result["access_token"], result.get("refresh_token"))
        return {k: v for k, v in result.items() if k not in ("access_token", "refresh_token")}
    return result


def get_bearer_or_cookie_token(request: Request) -> Optional[str]:
    """Extract the access token from the ``Authorization: Bearer`` header if
    present, else from the httpOnly access cookie. Header support is kept so
    non-browser API clients (and the migration window) keep working."""
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        scheme, _, credentials = auth_header.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            return credentials.strip()
    return request.cookies.get(ACCESS_COOKIE)

class JWTClaims(BaseModel):
    user_id: str
    org_id: Optional[str] = None
    role: Optional[str] = None
    email: str
    exp: int
    iat: int
    type: Optional[str] = "access"
    # Session id (== ``user_sessions.id``). Present on tokens minted after
    # the session-tracking change. Used by ``get_jwt_claims`` to verify the
    # session is still active on every authenticated request.
    jti: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "role": self.role,
            "email": self.email,
            "exp": self.exp,
            "iat": self.iat
        }

    @property
    def user_uuid(self) -> Optional[UUID]:
        try:
            return UUID(self.user_id) if self.user_id else None
        except (ValueError, TypeError):
            return None


class JWTManager:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_hours = settings.ACCESS_TOKEN_EXPIRE_HOURS
        self.refresh_token_expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)

    def access_token_expire_seconds(self) -> int:
        return self.access_token_expire_hours * 3600

    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_expire_days)

    def create_access_token(
        self,
        user_id: Union[str, UUID],
        email: str,
        org_id: Optional[Union[str, UUID]] = None,
        role: Optional[str] = None,
        session_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        current_time = int(time.time())
        payload = {
            "user_id": str(user_id),
            "email": email,
            "org_id": str(org_id) if org_id else None,
            "role": role,
            "type": "access",
            "iat": current_time,
            "exp": current_time + (self.access_token_expire_hours * 3600)
        }
        # ``jti`` ties the access token to a ``user_sessions`` row so that
        # ``get_jwt_claims`` can reject requests as soon as the session is
        # revoked (logout, password change, password reset) — without
        # waiting for the access token to expire.
        if session_id is not None:
            payload["jti"] = str(session_id)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: Union[str, UUID],
        email: str,
        session_id: Union[str, UUID],
        family: Union[str, UUID],
        org_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        current_time = int(time.time())
        payload = {
            "user_id": str(user_id),
            "email": email,
            "org_id": str(org_id) if org_id else None,
            "type": "refresh",
            "jti": str(session_id),
            "family": str(family),
            "iat": current_time,
            "exp": current_time + (self.refresh_token_expire_days * 86400),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_refresh_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not a refresh token",
                )
            if payload.get("exp", 0) < int(time.time()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token expired",
                )
            # Refresh tokens must carry a session reference (jti). Tokens
            # minted before sessions existed do not — they are rejected so
            # the user re-logs in and gets a tracked session.
            if not payload.get("jti"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is missing a session reference. Please log in again.",
                )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    def decode_token(self, token: str) -> JWTClaims:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            current_time = int(time.time())
            if payload.get("exp", 0) < current_time:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            return JWTClaims(**payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> JWTClaims:
        token = credentials.credentials
        return self.decode_token(token)


jwt_manager = JWTManager()


def try_resolve_api_key(token: str, db) -> Optional[JWTClaims]:
    """If ``token`` looks like a Tone-minted API key, resolve it and return synthesized
    ``JWTClaims`` for the request; otherwise return ``None`` so the caller falls
    through to JWT decode.

    API keys inherit **admin** authority within their org — they are the org's
    programmatic identity, so ``require_admin_or_owner`` guards accept them.
    Tenant context is set here so downstream services/queries are scoped to the
    key's org exactly like a JWT-authenticated request. Session-tracking
    (``_enforce_active_session``) is intentionally skipped for API keys — a key
    has no session row; its lifecycle is revoke/expire on the key itself.

    Best-effort ``last_used_at`` is bumped after a successful resolve; failures
    there are swallowed so a bookkeeping error never fails a real request.
    """
    from core.services.generated_api_key_service import (  # local import — avoids circular
        KEY_PREFIX,
        GeneratedApiKeyService,
    )

    if not token or not token.startswith(KEY_PREFIX):
        return None
    svc = GeneratedApiKeyService(db)
    api_key = svc.resolve_bearer_key(token)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
        )
    now = int(time.time())
    claims = JWTClaims(
        user_id=str(api_key.created_by_user_id),
        org_id=str(api_key.organization_id),
        # Admin authority is the deliberate design — see docstring.
        role="admin",
        email=f"api-key:{api_key.id}",
        iat=now,
        # Synthetic; not persisted. Long enough to survive any single request.
        exp=now + 3600,
        type="access",
    )
    set_tenant_context(
        org_id=claims.org_id, user_id=claims.user_id, role=claims.role
    )
    svc.touch_last_used(api_key.id)
    return claims


def _enforce_active_session(claims: JWTClaims, db) -> None:
    """Reject the request if the JWT's session has been revoked.

    Imported lazily so this module stays free of service-layer imports
    at import time (avoids circular imports with ``SessionService`` →
    ``BaseService`` → models that may import middleware).

    Tokens minted **before** the session-tracking change have no ``jti``
    — we let them through so currently-logged-in users are not kicked
    out by deploying this change; they will pick up ``jti`` on their
    next ``/auth/refresh`` rotation.
    """
    if not claims.jti:
        return
    from core.services.session_service import SessionService  # local import
    session = SessionService(db).get_session(claims.jti)
    if session is None or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid. Please log in again.",
        )


def get_jwt_claims(
    request: Request,
    db=Depends(get_db),
) -> JWTClaims:
    token = get_bearer_or_cookie_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    # API-key branch runs first — cheap prefix check + point lookup, no wasted
    # JWT decode. Returns synthesized claims or raises 401 for a bad key.
    api_key_claims = try_resolve_api_key(token, db)
    if api_key_claims is not None:
        return api_key_claims

    claims = jwt_manager.decode_token(token)
    if is_ee_enabled() and claims.org_id:
        org_id = claims.org_id
    else:
        org_id = settings.DEFAULT_ORG_ID
    set_tenant_context(org_id=org_id, user_id=claims.user_id, role=claims.role)
    _enforce_active_session(claims, db)
    return claims


def get_optional_jwt_claims(
    request: Request,
    db=Depends(get_db),
) -> Optional[JWTClaims]:
    token = get_bearer_or_cookie_token(request)
    if not token:
        return None
    api_key_claims = try_resolve_api_key(token, db)
    if api_key_claims is not None:
        return api_key_claims
    claims = jwt_manager.decode_token(token)
    _enforce_active_session(claims, db)
    return claims


def require_org_member(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if not claims.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required for this operation"
        )
    return claims


def require_admin_or_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    """Shared admin/owner guard — reuse this on every admin-gated route instead of
    re-checking roles inline. Raises 403 unless the caller's role is admin or owner."""
    if claims.role not in {"admin", "owner"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner role required"
        )
    return claims


def require_owner(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if not claims.role or claims.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner role required"
        )
    return claims
