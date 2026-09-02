from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_org_member
from core.services.oauth_providers import (
    get_catalog,
    get_supported_providers,
)
from core.services.oauth_service import OAuthService
from core.utils.auth_helpers import require_org_id

router = APIRouter()

BACKEND_URL = settings.BASE_API_URL.rstrip("/")


def _get_service(claims: JWTClaims, db: Session) -> OAuthService:
    return OAuthService(db, org_id=require_org_id(claims.org_id))


# ─── CRUD endpoints ───


@router.get("/connections")
def get_connections(
    provider: str = Query(None, description="Filter by provider (e.g. google_calendar)"),
    app_integration_id: str = Query(
        None,
        description="Filter to connections linked to this app_integrations row.",
    ),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connections = svc.get_connections(
        provider=provider,
        user_id=claims.user_id,
        app_integration_id=app_integration_id,
    )
    return [svc.connection_response(c) for c in connections]


@router.post("/list")
def list_connections(
    body: Dict[str, Any] = Body(default={}),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_connections_envelope(
        provider_slug=body.get("provider_slug"),
        app_integration_id=body.get("app_integration_id"),
    )


@router.get("/connection")
def get_connection_by_provider(
    provider: str = Query(..., description="Provider name (e.g. google_calendar)"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connection = svc.get_connection_by_provider(provider)
    if not connection:
        return {"connected": False, "provider": provider}
    return {**svc.connection_response(connection), "connected": True}


@router.post("/connections/{connection_id}/refresh")
def refresh_connection_token(
    connection_id: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """User-triggered refresh of a single OAuth connection's access token.

    Thin wrapper around ``OAuthService.get_valid_access_token_for_connection``
    — the SAME refresh path runtime + deep readiness use. Reused by three UI
    surfaces (Global Tools page, Global MCP page, agent readiness drawer) so
    a broken connection can be re-verified in-context without waiting for
    the next real call or running a full agent deep test.

    Success shape mirrors the connection-detail responses elsewhere in this
    router so callers can drop the payload into the same UI state.
    """
    svc = _get_service(claims, db)
    # ``get_connection`` is org-scoped via BaseService.query — a cross-org id
    # surfaces as 404, matching the semantics of every other endpoint here.
    connection = svc.get_connection(connection_id)
    # Provider-side failures (invalid_grant, invalid_client, network error)
    # raise HTTPException with a user-visible reason; let it bubble — the
    # OAuth router doesn't wrap OAuthService HTTPExceptions elsewhere either
    # (see /connection, /disconnect above). A follow-up refactor of
    # OAuthService to use application-level exceptions is out of scope.
    svc.get_valid_access_token_for_connection(connection)
    # Re-read to pick up the freshly-persisted token_expiry / rotated tokens.
    # ``update_tokens`` (inside ``get_valid_access_token_for_connection``) commits
    # + refreshes a *different* SQLAlchemy row, so the caller's ``connection``
    # object stays stale. A second fetch is the simplest way to get the fresh
    # public_metadata + tokens.
    #
    # Guard the re-read against a rare deletion race: another admin deleting
    # the same connection in the ~ms window between the refresh commit and
    # this fetch would otherwise turn a successful refresh into a confusing
    # 404. If that happens, fall back to reporting the refresh succeeded
    # without the freshly-persisted expiry — the DB already has the new
    # tokens even though we can't read them back through this session.
    try:
        refreshed = svc.get_connection(connection_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return {
                "status": "refreshed",
                "token_expiry": None,
                "connection": None,
            }
        raise
    return {
        "status": "refreshed",
        "token_expiry": (refreshed.public_metadata or {}).get("token_expiry"),
        "connection": svc.connection_response(refreshed),
    }


@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect(
    connection_id: str = Query(..., description="The connection UUID to delete"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_connection(connection_id)


@router.get("/providers")
def list_providers(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return {"providers": get_supported_providers(db, org_id)}


@router.get("/catalog")
def catalog(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Public, secret-free provider catalog for the integrations grid."""
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return {"providers": get_catalog(db, org_id)}


@router.post("/custom_credential", status_code=status.HTTP_201_CREATED)
def create_custom_credential(
    body: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Create a user-defined credential (OAuth 2.0 client-credentials, Bearer token, or API key).

    Body: { name, auth_kind: "oauth2_client_credentials" | "bearer" | "api_key",
            token_url?, client_id?, client_secret?, scope?, token?,
            api_key?, header_name? }
    """
    svc = _get_service(claims, db)
    connection = svc.create_custom_credential({**body, "created_by_user_id": claims.user_id})
    return svc.connection_response(connection)


# ─── Generic MCP OAuth 2.1 discovery (works with any compliant MCP server) ───

_MCP_CALLBACK_URL = f"{BACKEND_URL}/oauth/mcp/callback"


@router.post("/mcp/discover")
def mcp_discover(
    body: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Discover an MCP server's OAuth metadata, dynamically register a client, and return the
    authorization URL to redirect the user to. Body: { server_url, label?, return_to? }."""
    from core.services.mcp_oauth_service import McpOAuthService

    server_url = body.get("server_url")
    if not server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    svc = McpOAuthService(
        db, org_id=require_org_id(claims.org_id), redirect_uri=_MCP_CALLBACK_URL
    )
    return svc.start_discovery(
        server_url=server_url,
        created_by_user_id=claims.user_id,
        label=body.get("label"),
        return_to=body.get("return_to"),
        app_integration_id=body.get("app_integration_id"),
    )


def _mcp_callback_redirect(connection) -> RedirectResponse:
    """Send the user back to the in-app path that launched discovery (with the new connection id so
    the form can auto-select it), falling back to the integrations page."""
    frontend_url = settings.APPLICATION_URL.rstrip("/")
    return_to = (connection.public_metadata or {}).get("return_to")
    if return_to:
        sep = "&" if "?" in return_to else "?"
        target = f"{frontend_url}{return_to}{sep}mcp_oauth=success&connection_id={connection.id}"
    else:
        target = f"{frontend_url}/integrations?provider=mcp&status=success"
    return RedirectResponse(url=target)


@router.get("/mcp/callback")
def mcp_callback(
    code: str = Query(..., description="Authorization code from the MCP authorization server"),
    state: str = Query(..., description="The pending OAuth connection id"),
    db: Session = Depends(get_db),
):
    from core.services.mcp_oauth_service import McpOAuthService

    # The pending connection row carries org scope; load it to resolve the org for the service.
    from core.models.oauth_connection import OAuthConnection

    connection = db.query(OAuthConnection).filter(OAuthConnection.id == state).first()
    if not connection:
        raise HTTPException(status_code=400, detail="Unknown or expired MCP OAuth state")

    svc = McpOAuthService(
        db, org_id=connection.organization_id, redirect_uri=_MCP_CALLBACK_URL
    )
    connection = svc.complete(connection_id=state, code=code)

    return _mcp_callback_redirect(connection)


# ─── OAuth flow endpoints ───


@router.get("/{provider}/authorize")
def authorize(
    provider: str,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    auth_url = OAuthService.build_authorize_url(
        db=db,
        provider=provider,
        org_id=org_id,
        user_id=claims.user_id,
        backend_url=BACKEND_URL,
    )
    return {"auth_url": auth_url}


@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter with org_id:user_id:provider"),
    db: Session = Depends(get_db),
):
    # Business logic (state resolution across all three shapes, the token
    # exchange, and the connection-persist branch) lives in the service. The
    # route only exchanges + persists, then renders the SAME browser redirect
    # as before.
    OAuthService.exchange_code_and_persist(
        db=db,
        provider=provider,
        code=code,
        state=state,
        backend_url=BACKEND_URL,
    )
    frontend_url = settings.APPLICATION_URL.rstrip("/")
    return RedirectResponse(
        url=f"{frontend_url}/integrations?provider={provider}&status=success"
    )
