import time
import uuid as uuid_lib
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.oauth_connection import OAuthConnection
from core.utils.encryption import encrypt, decrypt
from core.services.oauth_providers import get_provider_config


class OAuthService(BaseService):

    def create_connection(self, data: Dict[str, Any]) -> OAuthConnection:
        existing = self.query(OAuthConnection).filter(
            OAuthConnection.provider == data["provider"],
            OAuthConnection.user_id == data.get("user_id"),
            OAuthConnection.is_active == True,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active connection for '{data['provider']}' already exists in this organization",
            )

        now = int(time.time())
        connection = OAuthConnection(
            uuid=uuid_lib.uuid4(),
            organization_id=self.org_id,
            user_id=data.get("user_id"),
            provider=data["provider"],
            access_token=encrypt(data["access_token"]),
            refresh_token=encrypt(data["refresh_token"]) if data.get("refresh_token") else None,
            token_expiry=data.get("token_expiry"),
            scopes=data.get("scopes"),
            user_email=data.get("user_email"),
            is_active=True,
            meta_data=data.get("meta_data", {}),
            created_at=now,
            updated_at=now,
        )
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def get_connections(self, provider: Optional[str] = None, user_id: Optional[int] = None) -> List[OAuthConnection]:
        q = self.query(OAuthConnection).filter(
            OAuthConnection.is_active == True,
        )
        if provider:
            q = q.filter(OAuthConnection.provider == provider)
        if user_id is not None:
            q = q.filter(OAuthConnection.user_id == user_id)
        return q.all()

    def get_connection_by_provider(self, provider: str) -> Optional[OAuthConnection]:
        return self.query(OAuthConnection).filter(
            OAuthConnection.provider == provider,
            OAuthConnection.is_active == True,
        ).first()

    def get_connection(self, connection_id: int) -> OAuthConnection:
        connection = self.query(OAuthConnection).filter(
            OAuthConnection.id == connection_id,
        ).first()
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OAuth connection not found",
            )
        return connection

    def update_tokens(self, connection_id: int, access_token: str,
                      refresh_token: Optional[str] = None,
                      token_expiry: Optional[int] = None) -> OAuthConnection:
        connection = self.get_connection(connection_id)
        connection.access_token = encrypt(access_token)
        if refresh_token:
            connection.refresh_token = encrypt(refresh_token)
        if token_expiry:
            connection.token_expiry = token_expiry
        connection.updated_at = int(time.time())
        self.db.commit()
        self.db.refresh(connection)
        return connection

    def delete_connection(self, connection_id: int) -> Dict[str, str]:
        connection = self.get_connection(connection_id)
        self.db.delete(connection)
        self.db.commit()
        return {"message": "OAuth connection deleted successfully"}

    def get_decrypted_tokens(self, connection: OAuthConnection) -> Dict[str, Any]:
        return {
            "access_token": decrypt(connection.access_token),
            "refresh_token": decrypt(connection.refresh_token) if connection.refresh_token else None,
            "token_expiry": connection.token_expiry,
        }

    def get_valid_access_token(self, provider: str) -> str:
        """Get a valid (non-expired) access token for the provider. Refreshes automatically if expired."""
        connection = self.get_connection_by_provider(provider)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active OAuth connection found for '{provider}'",
            )
        return self.get_valid_access_token_for_connection(connection)

    def get_valid_access_token_for_connection(self, connection: 'OAuthConnection') -> str:
        """Get a valid (non-expired) access token for a specific connection. Refreshes automatically if expired."""
        provider = connection.provider
        tokens = self.get_decrypted_tokens(connection)
        now = int(time.time())

        # If token is still valid (with 60s buffer), return it
        if connection.token_expiry and now < (connection.token_expiry - 60):
            return tokens["access_token"]

        # Token expired — refresh it
        if not tokens["refresh_token"]:
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
            "refresh_token": tokens["refresh_token"],
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
        # Google may return a new refresh token (rare), keep the old one if not
        new_refresh_token = new_tokens.get("refresh_token")

        self.update_tokens(
            connection.id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_expiry=new_expiry,
        )

        return new_access_token

    def connection_response(self, connection: OAuthConnection) -> Dict[str, Any]:
        return {
            "id": connection.id,
            "uuid": str(connection.uuid),
            "provider": connection.provider,
            "user_email": connection.user_email,
            "scopes": connection.scopes,
            "token_expiry": connection.token_expiry,
            "is_active": connection.is_active,
            "meta_data": connection.meta_data,
            "created_at": connection.created_at,
            "updated_at": connection.updated_at,
        }
