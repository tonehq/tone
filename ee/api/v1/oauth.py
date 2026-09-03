from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database.session import get_db
from core.schemas.oauth_requests import (CustomCredentialRequest,
                                          McpDiscoverRequest)
from core.services.oauth_providers import (
    get_catalog,
    get_supported_providers,
)
from core.services.oauth_service import OAuthService
from core.utils.auth_helpers import require_org_id
from ee.middleware.auth import EEJWTClaims, require_ee_org_member

router = APIRouter()

BACKEND_URL = settings.BASE_API_URL.rstrip("/")


def _get_service(claims: EEJWTClaims, db: Session) -> OAuthService:
    return OAuthService(db, org_id=require_org_id(claims.org_id))


# ─── CRUD endpoints ───


@router.get("/connections")
def get_connections(
    provider: str = Query(None, description="Filter by provider (e.g. google_calendar)"),
    app_integration_id: str = Query(
        None,
        description="Filter to connections linked to this app_integrations row.",
    ),
    claims: EEJWTClaims = Depends(require_ee_org_member),
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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).list_connections_envelope(
        provider_slug=body.get("provider_slug"),
        app_integration_id=body.get("app_integration_id"),
    )


@router.get("/connection")
def get_connection_by_provider(
    provider: str = Query(..., description="Provider name (e.g. google_calendar)"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    svc = _get_service(claims, db)
    connection = svc.get_connection_by_provider(provider)
    if not connection:
        return {"connected": False, "provider": provider}
    return {**svc.connection_response(connection), "connected": True}


@router.delete("/disconnect", status_code=status.HTTP_200_OK)
def disconnect(
    connection_id: str = Query(..., description="The connection UUID to delete"),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_connection(connection_id)


@router.get("/providers")
def list_providers(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return {"providers": get_supported_providers(db, UUID(claims.org_id))}


@router.get("/catalog")
def catalog(
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Public, secret-free provider catalog for the integrations grid."""
    return {"providers": get_catalog(db, UUID(claims.org_id))}


@router.post("/custom_credential", status_code=status.HTTP_201_CREATED)
def create_custom_credential(
    body: CustomCredentialRequest = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Create a user-defined credential (OAuth 2.0 client-credentials or Bearer token)."""
    svc = _get_service(claims, db)
    connection = svc.create_custom_credential(
        {**body.model_dump(exclude_unset=True), "created_by_user_id": claims.user_id}
    )
    return svc.connection_response(connection)


# ─── Generic MCP OAuth 2.1 discovery (works with any compliant MCP server) ───

_MCP_CALLBACK_URL = f"{BACKEND_URL}/oauth/mcp/callback"


@router.post("/mcp/discover")
def mcp_discover(
    body: McpDiscoverRequest = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    """Discover an MCP server's OAuth metadata, dynamically register a client, and return the
    authorization URL. Body: { server_url, label?, return_to? }."""
    from core.services.mcp_oauth_service import McpOAuthService

    server_url = body.server_url
    if not server_url:
        raise HTTPException(status_code=400, detail="server_url is required")
    svc = McpOAuthService(
        db, org_id=require_org_id(claims.org_id), redirect_uri=_MCP_CALLBACK_URL
    )
    return svc.start_discovery(
        server_url=server_url,
        created_by_user_id=claims.user_id,
        label=body.label,
        return_to=body.return_to,
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
    from core.models.oauth_connection import OAuthConnection
    from core.services.mcp_oauth_service import McpOAuthService

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
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    auth_url = OAuthService.build_authorize_url(
        db=db,
        provider=provider,
        org_id=UUID(claims.org_id),
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
