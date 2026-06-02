"""Generic MCP OAuth 2.1 discovery + authorization (MCP spec 2025-06-18).

This is the *second* path to authenticating an MCP server (the first being a catalog provider in
``oauth_providers.py``). It works with ANY spec-compliant remote MCP server by discovering its
authorization metadata at runtime rather than hard-coding it:

    1. Probe the server unauthenticated → 401 with a ``WWW-Authenticate`` header pointing at the
       Protected Resource Metadata (RFC 9728).
    2. Fetch ``/.well-known/oauth-protected-resource`` → authorization_servers + scopes_supported.
    3. Fetch the AS metadata ``/.well-known/oauth-authorization-server`` (RFC 8414) →
       authorization/token/registration endpoints.
    4. Dynamic Client Registration (RFC 7591) → obtain a client_id (+ secret).
    5. Build an authorize URL with PKCE (S256) + the ``resource`` indicator (RFC 8707).
    6. On callback, exchange code + code_verifier + resource for tokens, audience-bound to the
       server.

The in-flight handshake is persisted on a *pending* ``OAuthConnection`` row (provider_slug
``mcp:<host>``); the OAuth ``state`` carries that row's id. No new table is needed — the connection
row IS the handshake store, and becomes the live credential once the callback completes.
"""

import base64
import hashlib
import secrets
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode, urljoin, urlparse
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from loguru import logger

from core.models.oauth_connection import OAuthConnection
from core.services.base import BaseService
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt_json, encrypt_json

# A client we dynamically register identifies itself with these defaults.
_CLIENT_NAME = "Tone Voice Agent"
_HTTP_TIMEOUT = 15.0


def _canonical_resource(server_url: str) -> str:
    """Canonical resource URI per RFC 8707 / MCP spec: lowercase scheme+host, no fragment, no
    trailing slash, path kept only if present."""
    parsed = urlparse(server_url)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{host}{path}" if path else f"{scheme}://{host}"


def _well_known(base: str, suffix: str) -> str:
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return urljoin(origin + "/", suffix)


def _safe_return_path(return_to: Optional[str]) -> Optional[str]:
    """Accept only a same-app relative path (``/...``), rejecting absolute/protocol-relative URLs to
    avoid an open redirect on the post-auth callback. Returns ``None`` when not safe."""
    if not return_to or not isinstance(return_to, str):
        return None
    candidate = return_to.strip()
    # Must be a root-relative path and not protocol-relative ("//host") or a scheme ("http:").
    if candidate.startswith("/") and not candidate.startswith("//") and "://" not in candidate:
        return candidate
    return None


def _pkce_pair() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return verifier, challenge


class McpOAuthService(BaseService):
    """Drives the discovery handshake and persists it on a pending OAuthConnection."""

    def __init__(self, db, org_id, redirect_uri: str):
        super().__init__(db, org_id=org_id)
        self.redirect_uri = redirect_uri

    # ── Discovery ────────────────────────────────────────────────────────

    def _discover_metadata(self, server_url: str) -> Dict[str, Any]:
        """Return {authorization_endpoint, token_endpoint, registration_endpoint, scopes_supported}.

        Tries the spec path (401 → PRM → AS metadata) and falls back to the conventional
        ``/.well-known`` locations derived from the server origin.
        """
        prm_url: Optional[str] = None
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            # 1. Probe for the resource-metadata pointer in WWW-Authenticate.
            try:
                probe = client.get(server_url, headers={"MCP-Protocol-Version": "2025-06-18"})
                if probe.status_code == 401:
                    prm_url = self._parse_resource_metadata_url(
                        probe.headers.get("www-authenticate", "")
                    )
            except httpx.HTTPError as exc:
                logger.info("MCP OAuth probe failed for {}: {}", server_url, exc)

            prm_url = prm_url or _well_known(server_url, ".well-known/oauth-protected-resource")

            # 2. Protected Resource Metadata → authorization server(s).
            auth_server = None
            scopes_supported = []
            try:
                prm = client.get(prm_url)
                if prm.status_code == 200:
                    prm_json = prm.json()
                    servers = prm_json.get("authorization_servers") or []
                    auth_server = servers[0] if servers else None
                    scopes_supported = prm_json.get("scopes_supported") or []
            except httpx.HTTPError as exc:
                logger.info("MCP PRM fetch failed at {}: {}", prm_url, exc)

            # The AS defaults to the server's own origin when PRM is unavailable.
            as_base = auth_server or f"{urlparse(server_url).scheme}://{urlparse(server_url).netloc}"

            # 3. Authorization Server Metadata (RFC 8414).
            meta: Dict[str, Any] = {}
            as_meta_url = _well_known(as_base, ".well-known/oauth-authorization-server")
            try:
                resp = client.get(as_meta_url)
                if resp.status_code == 200:
                    meta = resp.json()
            except httpx.HTTPError as exc:
                logger.info("MCP AS metadata fetch failed at {}: {}", as_meta_url, exc)

        authorization_endpoint = meta.get("authorization_endpoint") or urljoin(
            as_base + "/", "authorize"
        )
        token_endpoint = meta.get("token_endpoint") or urljoin(as_base + "/", "token")
        registration_endpoint = meta.get("registration_endpoint") or urljoin(
            as_base + "/", "register"
        )
        return {
            "authorization_endpoint": authorization_endpoint,
            "token_endpoint": token_endpoint,
            "registration_endpoint": registration_endpoint,
            "scopes_supported": scopes_supported,
        }

    @staticmethod
    def _parse_resource_metadata_url(www_authenticate: str) -> Optional[str]:
        """Extract the ``resource_metadata`` URL from a WWW-Authenticate header, if present."""
        if not www_authenticate:
            return None
        marker = "resource_metadata="
        idx = www_authenticate.find(marker)
        if idx == -1:
            return None
        value = www_authenticate[idx + len(marker) :].split(",")[0].strip().strip('"')
        return value or None

    def _register_client(
        self, registration_endpoint: str
    ) -> Tuple[str, Optional[str]]:
        """Dynamic Client Registration (RFC 7591). Returns (client_id, client_secret?)."""
        payload = {
            "client_name": _CLIENT_NAME,
            "redirect_uris": [self.redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post",
        }
        try:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                resp = client.post(registration_endpoint, json=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dynamic client registration request failed: {exc}",
            )
        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dynamic client registration failed ({resp.status_code}): {resp.text}",
            )
        data = resp.json()
        client_id = data.get("client_id")
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration response did not include a client_id",
            )
        return client_id, data.get("client_secret")

    def start_discovery(
        self,
        server_url: str,
        created_by_user_id,
        label: Optional[str] = None,
        return_to: Optional[str] = None,
    ) -> Dict[str, str]:
        """Run discovery + DCR, persist a pending connection, return the authorize URL.

        ``return_to`` is an optional in-app path the callback should send the user back to (e.g. the
        MCP form they launched discovery from). Only a safe relative path is honoured.
        """
        created_by = coerce_uuid(created_by_user_id)
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_by_user_id (UUID) is required",
            )

        resource = _canonical_resource(server_url)
        meta = self._discover_metadata(server_url)
        client_id, client_secret = self._register_client(meta["registration_endpoint"])
        verifier, challenge = _pkce_pair()
        host = urlparse(server_url).netloc or "mcp"
        provider_slug = f"mcp:{host}"

        encrypted_credentials = encrypt_json(
            {"code_verifier": verifier, "client_secret": client_secret}
        )
        public_metadata = {
            "status": "pending",
            "server_url": server_url,
            "resource": resource,
            "authorization_endpoint": meta["authorization_endpoint"],
            "token_endpoint": meta["token_endpoint"],
            "client_id": client_id,
            "scopes": meta["scopes_supported"],
        }
        safe_return_to = _safe_return_path(return_to)
        if safe_return_to:
            public_metadata["return_to"] = safe_return_to

        # Reuse an existing connection for the same server (mirrors OAuthService.create_connection's
        # upsert): a reconnect re-runs discovery and must refresh the SAME row, so MCP servers linked
        # via oauth_connection_id keep working and duplicate rows don't accumulate in the grid.
        connection = (
            self.query(OAuthConnection)
            .filter(
                OAuthConnection.provider_slug == provider_slug,
                OAuthConnection.created_by_user_id == created_by,
            )
            .first()
        )
        if connection:
            connection.label = label or connection.label or f"MCP — {host}"
            connection.auth_type = "oauth"
            connection.encrypted_credentials = encrypted_credentials
            connection.public_metadata = public_metadata
        else:
            connection = OAuthConnection(
                organization_id=self.org_id,
                provider_slug=provider_slug,
                label=label or f"MCP — {host}",
                auth_type="oauth",
                encrypted_credentials=encrypted_credentials,
                public_metadata=public_metadata,
                created_by_user_id=created_by,
            )
            self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        params = {
            "client_id": client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": str(connection.id),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": resource,
        }
        if meta["scopes_supported"]:
            params["scope"] = " ".join(meta["scopes_supported"])
        auth_url = f"{meta['authorization_endpoint']}?{urlencode(params)}"
        return {"auth_url": auth_url, "connection_id": str(connection.id)}

    # ── Callback ─────────────────────────────────────────────────────────

    def complete(self, connection_id: str, code: str) -> OAuthConnection:
        """Exchange the auth code for tokens and activate the pending connection."""
        uid = coerce_uuid(connection_id)
        connection = (
            self.query(OAuthConnection).filter(OAuthConnection.id == uid).first()
            if uid
            else None
        )
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown or expired MCP OAuth state",
            )

        meta = dict(connection.public_metadata or {})
        creds = decrypt_json(connection.encrypted_credentials) or {}

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": meta.get("client_id"),
            "code_verifier": creds.get("code_verifier"),
            "resource": meta.get("resource"),
        }
        if creds.get("client_secret"):
            token_data["client_secret"] = creds["client_secret"]

        try:
            with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
                resp = client.post(meta["token_endpoint"], data=token_data)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MCP token exchange request failed: {exc}",
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MCP token exchange failed ({resp.status_code}): {resp.text}",
            )

        tokens = resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token returned by MCP authorization server",
            )

        import time

        expires_in = tokens.get("expires_in")
        new_creds = {
            "access_token": access_token,
            "refresh_token": tokens.get("refresh_token") or creds.get("refresh_token"),
            # Keep DCR client_secret around for token refresh.
            "client_secret": creds.get("client_secret"),
        }
        connection.encrypted_credentials = encrypt_json(new_creds)
        meta["status"] = "active"
        if tokens.get("scope"):
            from core.services.oauth_service import normalize_scopes

            meta["scopes"] = normalize_scopes(tokens["scope"])
        if expires_in:
            meta["token_expiry"] = int(time.time()) + int(expires_in)
        connection.public_metadata = meta
        self.db.commit()
        self.db.refresh(connection)
        return connection
