"""OAuth connection service — v2 schema.

Each connection lives in ``oauth_connections``:
  - ``provider_slug``   — e.g. ``google_calendar``
  - ``auth_type``       — ``oauth`` | ``api_key`` | ``bearer``
  - ``encrypted_credentials`` (JSONB) — opaque, encrypted access/refresh tokens
  - ``public_metadata`` (JSONB) — non-sensitive (user_email, scopes, token_expiry)
  - ``created_by_user_id`` (UUID) — who initiated the OAuth handshake
"""

import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from loguru import logger

from core.models.oauth_connection import OAuthConnection
from core.services.base import BaseService
from core.services.oauth_providers import get_provider_config, get_provider_scopes
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt_json, encrypt_json


def normalize_scopes(scopes: Any) -> List[str]:
    """Coerce a scope value into a clean list of strings.

    Accepts a list (returned as-is, de-duped, order-preserving), a delimited string
    (space- or comma-separated — the two delimiters OAuth providers use), or ``None``.
    Centralised so stored scopes are always a list regardless of provider quirks or legacy rows.
    """
    if not scopes:
        return []
    if isinstance(scopes, str):
        # Providers delimit scopes with either spaces (Google/Slack) or commas (Linear).
        parts = scopes.replace(",", " ").split()
    elif isinstance(scopes, (list, tuple, set)):
        parts = [str(s) for s in scopes]
    else:
        return []
    seen: set = set()
    result: List[str] = []
    for p in parts:
        p = p.strip()
        if p and p not in seen:
            seen.add(p)
            result.append(p)
    return result


class OAuthService(BaseService):
    # ──────────────────────────────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────────────────────────────

    def create_connection(self, data: Dict[str, Any]) -> OAuthConnection:
        """Persist a new OAuth connection from the provider callback payload.

        Expected keys: ``provider`` (alias: ``provider_slug``), ``access_token``,
        ``refresh_token``, ``token_expiry``, ``scopes``, ``user_email``,
        ``user_id`` (alias: ``created_by_user_id``), ``auth_type`` (default ``oauth``).
        """
        provider_slug = data.get("provider_slug") or data.get("provider")
        if not provider_slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider_slug is required",
            )

        created_by = coerce_uuid(data.get("created_by_user_id") or data.get("user_id"))
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_by_user_id (UUID) is required",
            )

        user_email = data.get("user_email")
        existing_q = self.query(OAuthConnection).filter(
            OAuthConnection.provider_slug == provider_slug,
            OAuthConnection.created_by_user_id == created_by,
        )
        if user_email:
            existing_q = existing_q.filter(
                OAuthConnection.public_metadata["user_email"].astext == user_email
            )
        existing = existing_q.first()
        if existing:
            # Refresh the existing record in place instead of failing — the user
            # is reconnecting with the same identity.
            return self._apply_tokens(existing, data)

        public_metadata = {
            "user_email": user_email,
            "scopes": normalize_scopes(data.get("scopes")),
            "token_expiry": data.get("token_expiry"),
        }

        encrypted_credentials = encrypt_json({
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
        })

        connection = OAuthConnection(
            organization_id=self.org_id,
            provider_slug=provider_slug,
            label=data.get("label") or provider_slug.replace("_", " ").title(),
            auth_type=data.get("auth_type", "oauth"),
            encrypted_credentials=encrypted_credentials,
            public_metadata=public_metadata,
            created_by_user_id=created_by,
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_connections(
        self,
        provider: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
    ) -> List[OAuthConnection]:
        q = self.query(OAuthConnection)
        if provider:
            q = q.filter(OAuthConnection.provider_slug == provider)
        uid = coerce_uuid(user_id)
        if uid is not None:
            q = q.filter(OAuthConnection.created_by_user_id == uid)
        return q.order_by(OAuthConnection.updated_at.desc()).all()

    def list_connections(
        self,
        provider_slug: Optional[str] = None,
        user_id: Optional[Union[str, UUID]] = None,
    ) -> List[Dict[str, Any]]:
        """Return every connection in the org (no pagination)."""
        q = self.query(OAuthConnection)
        if provider_slug:
            q = q.filter(OAuthConnection.provider_slug == provider_slug)
        uid = coerce_uuid(user_id)
        if uid is not None:
            q = q.filter(OAuthConnection.created_by_user_id == uid)
        items = q.order_by(OAuthConnection.updated_at.desc()).all()
        return [c.to_dict() for c in items]

    def get_connection_by_provider(self, provider: str) -> Optional[OAuthConnection]:
        return (
            self.query(OAuthConnection)
            .filter(OAuthConnection.provider_slug == provider)
            .order_by(OAuthConnection.updated_at.desc())
            .first()
        )

    def get_connection(self, connection_id: Union[str, UUID]) -> OAuthConnection:
        uid = coerce_uuid(connection_id)
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connection_id must be a valid UUID",
            )
        connection = (
            self.query(OAuthConnection).filter(OAuthConnection.id == uid).first()
        )
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OAuth connection not found",
            )
        return connection

    def delete_connection(self, connection_id: Union[str, UUID]) -> Dict[str, str]:
        connection = self.get_connection(connection_id)
        # Disconnecting a connection leaves anything that relied on it unable to
        # authenticate. Deactivate those tools and MCP servers (and clear the
        # dangling link) so they aren't silently called and failing during a
        # conversation. The FK's SET NULL would otherwise leave them active but
        # unauthenticated, silently exposing zero tools at call time.
        from core.models.tool import Tool
        from core.models.mcp_server import McpServer

        self.db.query(Tool).filter(Tool.oauth_connection_id == connection.id).update(
            {Tool.is_active: False, Tool.oauth_connection_id: None},
            synchronize_session=False,
        )
        self.db.query(McpServer).filter(McpServer.oauth_connection_id == connection.id).update(
            {McpServer.is_active: False, McpServer.oauth_connection_id: None},
            synchronize_session=False,
        )
        self.db.delete(connection)
        self.db.commit()
        return {"message": "OAuth connection deleted successfully"}

    # ──────────────────────────────────────────────────────────────────────
    # Scope handling
    # ──────────────────────────────────────────────────────────────────────

    def get_granted_scopes(self, connection: OAuthConnection) -> List[str]:
        """Scopes actually granted to this connection (from ``public_metadata.scopes``)."""
        metadata = connection.public_metadata or {}
        return normalize_scopes(metadata.get("scopes"))

    def validate_scopes(
        self, connection: OAuthConnection, required: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Check whether ``connection`` was granted every scope in ``required``.

        Returns a structured result (never raises) so callers can choose to block or warn:
        ``{ ok, provider, granted: [...], required: [...], missing: [...] }``.
        """
        required_list = normalize_scopes(required)
        granted = set(self.get_granted_scopes(connection))
        missing = [s for s in required_list if s not in granted]
        return {
            "ok": len(missing) == 0,
            "provider": connection.provider_slug,
            "granted": sorted(granted),
            "required": required_list,
            "missing": missing,
        }

    def validate_connection_for_provider(
        self, connection: OAuthConnection, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate a connection against the catalog-declared scopes of ``provider``.

        Defaults to the connection's own provider when ``provider`` is omitted.
        """
        provider = provider or connection.provider_slug
        return self.validate_scopes(connection, get_provider_scopes(provider))

    @staticmethod
    def raise_if_missing_scopes(result: Dict[str, Any]) -> None:
        """Raise a 400 with the standard ``missing_scopes`` error contract when a scope
        validation result is not ``ok``. Single source of truth for the error shape so every
        config path (tool, MCP server, …) blocks with an identical, parseable response."""
        if result["ok"]:
            return
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    f"The linked '{result['provider']}' connection is missing required "
                    f"scopes. Reconnect it to grant: {', '.join(result['missing'])}."
                ),
                "code": "missing_scopes",
                "provider": result["provider"],
                "missing_scopes": result["missing"],
            },
        )

    # ──────────────────────────────────────────────────────────────────────
    # Custom credentials (Vapi-style)
    # ──────────────────────────────────────────────────────────────────────

    def create_custom_credential(self, data: Dict[str, Any]) -> OAuthConnection:
        """Create a user-defined credential not tied to a catalog provider.

        Supported ``auth_kind``:
          - ``oauth2_client_credentials`` — token_url + client_id + client_secret (+ scope);
            tokens are minted via the client-credentials grant on demand.
          - ``bearer`` — a static bearer token supplied directly.

        Stored as an ``OAuthConnection`` with ``provider_slug = "custom:<slug>"`` so it appears
        alongside other connections and can back a tool/MCP server via ``oauth_connection_id``.
        """
        import re

        created_by = coerce_uuid(data.get("created_by_user_id") or data.get("user_id"))
        if not created_by:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="created_by_user_id (UUID) is required",
            )

        name = (data.get("name") or data.get("label") or "").strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credential name is required",
            )

        auth_kind = data.get("auth_kind") or "oauth2_client_credentials"
        slug_suffix = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "credential"
        provider_slug = f"custom:{slug_suffix}"

        if auth_kind == "bearer":
            token = (data.get("token") or "").strip()
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="token is required for a bearer credential",
                )
            encrypted = encrypt_json({"access_token": token})
            metadata: Dict[str, Any] = {
                "credential_type": "custom",
                "auth_kind": "bearer",
                "status": "active",
            }
            auth_type = "bearer"
        elif auth_kind == "oauth2_client_credentials":
            token_url = (data.get("token_url") or "").strip()
            client_id = (data.get("client_id") or "").strip()
            client_secret = (data.get("client_secret") or "").strip()
            if not (token_url and client_id and client_secret):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="token_url, client_id and client_secret are required for OAuth 2.0",
                )
            scopes = normalize_scopes(data.get("scopes") or data.get("scope"))
            # Verify the credential up front by minting a real token, so a credential that can't
            # authenticate (e.g. a provider that doesn't support client-credentials) is rejected
            # here with a clear error instead of silently showing "Connected" then failing at use.
            token_result = self._request_client_credentials_token(
                token_url, client_id, client_secret, scopes, label=name
            )
            encrypted = encrypt_json(
                {"client_secret": client_secret, "access_token": token_result["access_token"]}
            )
            metadata = {
                "credential_type": "custom",
                "auth_kind": "oauth2_client_credentials",
                "grant_type": "client_credentials",
                "token_url": token_url,
                "client_id": client_id,
                "scopes": scopes,
                "token_expiry": int(time.time()) + int(token_result.get("expires_in", 3600)),
                "status": "active",
            }
            auth_type = "oauth"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported auth_kind '{auth_kind}'",
            )

        connection = OAuthConnection(
            organization_id=self.org_id,
            provider_slug=provider_slug,
            label=name,
            auth_type=auth_type,
            encrypted_credentials=encrypted,
            public_metadata=metadata,
            created_by_user_id=created_by,
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def _request_client_credentials_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: List[str],
        label: str = "credential",
    ) -> Dict[str, Any]:
        """Perform a client-credentials token request. Returns {access_token, expires_in}.

        Raises HTTPException(400) with a clear message on any failure so the caller (creation or
        refresh) surfaces it to the user rather than producing a half-working credential.
        """
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scopes:
            payload["scope"] = " ".join(scopes)
        try:
            with httpx.Client() as client:
                response = client.post(token_url, data=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not reach the token URL for '{label}': {exc}",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Client-credentials token request failed for '{label}' "
                    f"(HTTP {response.status_code}). This provider may not support the "
                    "client-credentials grant — check the token URL, client ID and secret."
                ),
            )
        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No access token returned for '{label}'.",
            )
        return {"access_token": access_token, "expires_in": body.get("expires_in", 3600)}

    def _mint_client_credentials_token(self, connection: OAuthConnection) -> str:
        """Return a cached client-credentials token, minting a fresh one when missing/expired."""
        metadata = connection.public_metadata or {}
        tokens = self.get_decrypted_tokens(connection)
        now = int(time.time())
        expiry = tokens.get("token_expiry")
        if tokens.get("access_token") and expiry and now < (expiry - 60):
            return tokens["access_token"]

        credentials = decrypt_json(connection.encrypted_credentials) or {}
        token_url = metadata.get("token_url")
        if not token_url:
            raise HTTPException(status_code=400, detail="Credential is missing a token URL.")

        result = self._request_client_credentials_token(
            token_url,
            metadata.get("client_id"),
            credentials.get("client_secret"),
            metadata.get("scopes") or [],
            label=connection.label or connection.provider_slug,
        )
        new_expiry = int(time.time()) + int(result.get("expires_in", 3600))
        self.update_tokens(connection.id, access_token=result["access_token"], token_expiry=new_expiry)
        return result["access_token"]

    # ──────────────────────────────────────────────────────────────────────
    # Token management
    # ──────────────────────────────────────────────────────────────────────

    def get_decrypted_tokens(self, connection: OAuthConnection) -> Dict[str, Any]:
        credentials = decrypt_json(connection.encrypted_credentials)
        metadata = connection.public_metadata or {}
        return {
            "access_token": credentials.get("access_token"),
            "refresh_token": credentials.get("refresh_token"),
            "token_expiry": metadata.get("token_expiry"),
        }

    def update_tokens(
        self,
        connection_id: Union[str, UUID],
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry: Optional[int] = None,
    ) -> OAuthConnection:
        connection = self.get_connection(connection_id)
        existing = decrypt_json(connection.encrypted_credentials)
        existing["access_token"] = access_token
        if refresh_token:
            existing["refresh_token"] = refresh_token
        connection.encrypted_credentials = encrypt_json(existing)
        metadata = dict(connection.public_metadata or {})
        if token_expiry:
            metadata["token_expiry"] = token_expiry
        connection.public_metadata = metadata
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_valid_access_token(self, provider: str) -> str:
        connection = self.get_connection_by_provider(provider)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active OAuth connection found for '{provider}'",
            )
        return self.get_valid_access_token_for_connection(connection)

    def get_valid_access_token_for_connection(self, connection: OAuthConnection) -> str:
        provider = connection.provider_slug
        metadata = connection.public_metadata or {}

        # Custom credentials (Vapi-style) don't use the 3-legged authorization-code flow:
        #  - "bearer": a static token, returned as-is.
        #  - "oauth2_client_credentials": machine-to-machine grant, minted/cached on demand.
        auth_kind = metadata.get("auth_kind")
        if auth_kind == "bearer":
            token = self.get_decrypted_tokens(connection).get("access_token")
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bearer credential '{connection.label or provider}' has no token.",
                )
            return token
        if metadata.get("grant_type") == "client_credentials":
            return self._mint_client_credentials_token(connection)

        try:
            tokens = self.get_decrypted_tokens(connection)
        except Exception as exc:
            # Decryption failed (rotated key, corrupted blob, etc.) — the user
            # needs to reconnect rather than see a generic 500.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stored credentials for '{provider}' could not be decrypted. Please reconnect.",
            ) from exc
        now = int(time.time())
        expiry = tokens.get("token_expiry")

        if expiry and now < (expiry - 60):
            return tokens["access_token"]

        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token expired and no refresh token available for '{provider}'. Please reconnect.",
            )

        # Generic MCP connections (provider_slug ``mcp:<host>``) aren't in the catalog — their
        # token endpoint and dynamically-registered client live in the connection record itself.
        config = get_provider_config(provider)
        if config:
            token_url = config["token_url"]
            refresh_data = {
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        else:
            metadata = connection.public_metadata or {}
            token_url = metadata.get("token_endpoint")
            if not token_url:
                raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
            credentials = decrypt_json(connection.encrypted_credentials) or {}
            refresh_data = {
                "client_id": metadata.get("client_id"),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            if credentials.get("client_secret"):
                refresh_data["client_secret"] = credentials["client_secret"]
            if metadata.get("resource"):
                refresh_data["resource"] = metadata["resource"]

        with httpx.Client() as client:
            response = client.post(token_url, data=refresh_data)

        if response.status_code != 200:
            # Surface the provider's real reason (e.g. invalid_grant = token
            # expired/revoked → must reconnect; invalid_client = config issue).
            # Without this the failure is opaque and looks like a code bug.
            provider_error = ""
            try:
                body = response.json()
                provider_error = body.get("error") or ""
                if body.get("error_description"):
                    provider_error = f"{provider_error}: {body['error_description']}"
            except Exception:
                provider_error = (response.text or "")[:200]
            logger.warning(
                "OAuth refresh failed for '{}' (status={}): {}",
                provider, response.status_code, provider_error,
            )
            hint = "Please reconnect."
            if "invalid_grant" in provider_error:
                hint = (
                    "Refresh token expired or revoked — reconnect, and publish the "
                    "OAuth app (Google Cloud Console → OAuth consent screen) so tokens "
                    "stop expiring in 7 days."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token refresh failed for '{provider}' ({provider_error or response.status_code}). {hint}",
            )

        new_tokens = response.json()
        new_access_token = new_tokens["access_token"]
        new_expiry = int(time.time()) + new_tokens.get("expires_in", 3600)
        # Google may rotate refresh tokens; keep the old one if not returned.
        new_refresh_token = new_tokens.get("refresh_token")

        self.update_tokens(
            connection.id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_expiry=new_expiry,
        )
        return new_access_token

    # ──────────────────────────────────────────────────────────────────────
    # Response helpers
    # ──────────────────────────────────────────────────────────────────────

    def connection_response(self, connection: OAuthConnection) -> Dict[str, Any]:
        return connection.to_dict()

    # ──────────────────────────────────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────────────────────────────────

    def _apply_tokens(self, connection: OAuthConnection, data: Dict[str, Any]) -> OAuthConnection:
        credentials = decrypt_json(connection.encrypted_credentials)
        credentials["access_token"] = data["access_token"]
        if data.get("refresh_token"):
            credentials["refresh_token"] = data["refresh_token"]
        connection.encrypted_credentials = encrypt_json(credentials)

        metadata = dict(connection.public_metadata or {})
        if data.get("token_expiry") is not None:
            metadata["token_expiry"] = data["token_expiry"]
        if data.get("scopes") is not None:
            metadata["scopes"] = normalize_scopes(data["scopes"])
        if data.get("user_email") is not None:
            metadata["user_email"] = data["user_email"]
        connection.public_metadata = metadata

        self.db.commit()
        self.db.refresh(connection)
        return connection
