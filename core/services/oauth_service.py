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

from core.models.oauth_connection import OAuthConnection
from core.services.base import BaseService
from core.services.oauth_providers import get_provider_config
from core.utils.auth_helpers import coerce_uuid
from core.utils.encryption import decrypt_json, encrypt_json


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
            "scopes": data.get("scopes"),
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
        self.db.delete(connection)
        self.db.commit()
        return {"message": "OAuth connection deleted successfully"}

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

        config = get_provider_config(provider)
        if not config:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

        refresh_data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client() as client:
            response = client.post(config["token_url"], data=refresh_data)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token refresh failed for '{provider}'. Please reconnect.",
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
            metadata["scopes"] = data["scopes"]
        if data.get("user_email") is not None:
            metadata["user_email"] = data["user_email"]
        connection.public_metadata = metadata

        self.db.commit()
        self.db.refresh(connection)
        return connection
