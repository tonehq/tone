from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_
from typing import List, Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.services.api_key_service import ApiKeyService
from core.services.redis_service import cache_delete_pattern
from core.models.service_provider import ServiceProvider
from core.models.models import Model
from core.models.api_key import ApiKey
from core.models.voice import Voice
from core.utils.encryption import encrypt


class ServiceProviderService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def _exists_same_name_and_provider_type(
        self, name: str, provider_type: str, exclude_id: Optional[int] = None
    ) -> bool:
        """True if a record with the same name and provider_type exists (optionally excluding one id)."""
        q = self.db.query(ServiceProvider).filter(
            ServiceProvider.name == name,
            ServiceProvider.provider_type == provider_type,
        )
        if exclude_id is not None:
            q = q.filter(ServiceProvider.id != exclude_id)
        return q.first() is not None

    def upsert_service_provider(self, name: str, display_name: str, provider_type: str,
                                auth_type: str, api_key: Dict[str, Any],
                                description: Optional[str] = None,
                                logo_url: Optional[str] = None, website_url: Optional[str] = None,
                                documentation_url: Optional[str] = None, base_url: Optional[str] = None,
                                supports_streaming: bool = False, config_schema: Optional[Dict] = None,
                                is_system: bool = False, provider_status: Optional[str] = None,
                                provider_id: Optional[int] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        if provider_id is not None:
            existing = self.db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Service provider not found",
                )
            if self._exists_same_name_and_provider_type(name, provider_type, exclude_id=provider_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A service provider with this name and provider_type already exists.",
                )
            existing.display_name = display_name
            existing.description = description
            existing.provider_type = provider_type
            existing.logo_url = logo_url
            existing.website_url = website_url
            existing.documentation_url = documentation_url
            existing.base_url = base_url
            existing.auth_type = auth_type
            existing.supports_streaming = supports_streaming
            existing.config_schema = config_schema
            existing.is_system = is_system
            existing.updated_at = current_time
            if name is not None:
                existing.name = name
            if provider_status is not None:
                existing.status = provider_status
            self.db.commit()
            self.db.refresh(existing)
            provider = existing
        else:
            if self._exists_same_name_and_provider_type(name, provider_type):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A service provider with this name and provider_type already exists.",
                )
            values = {
                "uuid": uuid_lib.uuid4(),
                "name": name,
                "display_name": display_name,
                "description": description,
                "provider_type": provider_type,
                "logo_url": logo_url,
                "website_url": website_url,
                "documentation_url": documentation_url,
                "base_url": base_url,
                "auth_type": auth_type,
                "supports_streaming": supports_streaming,
                "config_schema": config_schema,
                "is_system": is_system,
                "created_at": current_time,
                "updated_at": current_time,
            }
            if provider_status is not None:
                values["status"] = provider_status
            provider = ServiceProvider(**values)
            self.db.add(provider)
            self.db.commit()
            self.db.refresh(provider)

        api_key_payload = self._upsert_provider_api_key(provider.id, api_key)

        return {
            "id": provider.id,
            "uuid": str(provider.uuid),
            "name": provider.name,
            "display_name": provider.display_name,
            "description": provider.description,
            "provider_type": provider.provider_type,
            "logo_url": provider.logo_url,
            "website_url": provider.website_url,
            "documentation_url": provider.documentation_url,
            "base_url": provider.base_url,
            "auth_type": provider.auth_type,
            "supports_streaming": provider.supports_streaming,
            "config_schema": provider.config_schema,
            "is_system": provider.is_system,
            "status": provider.status,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
            "api_key": api_key_payload,
        }

    def _get_provider_api_key(self, provider_id: int) -> Optional[Dict[str, Any]]:
        key = (
            self.db.query(ApiKey)
            .filter(ApiKey.service_provider_id == provider_id, ApiKey.status == "active")
            .order_by(ApiKey.id.desc())
            .first()
        )
        if not key:
            return None
        return {
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "description": key.description,
            "api_key_hint": key.api_key_hint,
            "service_provider_id": key.service_provider_id,
            "additional_credentials": key.additional_credentials,
            "rate_limit_config": key.rate_limit_config,
            "expires_at": key.expires_at,
            "status": key.status,
            "is_valid": key.is_valid,
            "created_at": key.created_at,
            "updated_at": key.updated_at,
        }

    def _upsert_provider_api_key(self, provider_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        api_key_value = payload.get("api_key")
        api_key_id = payload.get("id")

        existing: Optional[ApiKey] = None
        if api_key_id is not None:
            try:
                api_key_id = int(api_key_id)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="api_key.id must be an integer",
                )
            existing = self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found",
                )
            if existing.service_provider_id != provider_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key does not belong to this service provider",
                )

        if existing is None:
            if not api_key_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="api_key.api_key (secret value) is required to create a new key",
                )
            provider = self.db.query(ServiceProvider).get(provider_id)
            name = payload.get("name") or f"{provider.name} key"
            ApiKeyService(self.db, user_id=self._user_id).upsert_api_key(
                service_provider_id=provider_id,
                name=name,
                api_key_value=api_key_value,
                description=payload.get("description"),
                additional_credentials=payload.get("additional_credentials"),
                rate_limit_config=payload.get("rate_limit_config"),
                expires_at=payload.get("expires_at"),
                key_status=payload.get("status"),
            )
            return self._get_provider_api_key(provider_id)

        current_time = int(time.time())
        if payload.get("name") is not None:
            existing.name = payload["name"]
        if "description" in payload:
            existing.description = payload.get("description")
        if "additional_credentials" in payload:
            existing.additional_credentials = payload.get("additional_credentials")
        if "rate_limit_config" in payload:
            existing.rate_limit_config = payload.get("rate_limit_config")
        if "expires_at" in payload:
            existing.expires_at = payload.get("expires_at")
        if payload.get("status") is not None:
            existing.status = payload["status"]
        if api_key_value:
            existing.api_key_encrypted = encrypt(api_key_value)
            existing.api_key_hint = (
                api_key_value[:4] + "..." + api_key_value[-4:]
                if len(api_key_value) > 8 else "****"
            )
            existing.is_valid = False
            existing.last_validated_at = None
            existing.validation_error = None
        existing.updated_at = current_time
        self.db.commit()
        self.db.refresh(existing)
        cache_delete_pattern("agent_bot_data:*")
        return self._get_provider_api_key(provider_id)

    def get_all_service_providers(
        self,
        provider_type: Optional[str] = None,
        name: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """List service providers with optional filters, sorting, and pagination.

        Excludes TTS providers that have no active voices (matches legacy behaviour).
        Returns {"data": [...], "pagination": {...}}.
        """
        query = self.db.query(ServiceProvider)

        if status_filter:
            query = query.filter(ServiceProvider.status == status_filter)
        else:
            query = query.filter(ServiceProvider.status == "active")

        if provider_type:
            query = query.filter(ServiceProvider.provider_type == provider_type)

        if name:
            query = query.filter(
                or_(
                    ServiceProvider.name.ilike(f"%{name}%"),
                    ServiceProvider.display_name.ilike(f"%{name}%"),
                )
            )

        # Exclude TTS providers without active voices (so pagination total stays correct)
        tts_with_voices_subq = (
            self.db.query(Voice.service_provider_id)
            .filter(Voice.is_active == True)
            .distinct()
        )
        query = query.filter(
            or_(
                ServiceProvider.provider_type != "tts",
                ServiceProvider.id.in_(tts_with_voices_subq),
            )
        )

        # Count BEFORE pagination
        total = query.count()

        sort_column_map = {
            "created_at": ServiceProvider.created_at,
            "updated_at": ServiceProvider.updated_at,
            "name": ServiceProvider.name,
            "display_name": ServiceProvider.display_name,
        }
        sort_column = sort_column_map.get(sort_by, ServiceProvider.created_at)
        order_func = asc if sort_order == "asc" else desc
        offset = (page - 1) * page_size

        providers = (
            query.order_by(order_func(sort_column), ServiceProvider.id)
            .offset(offset)
            .limit(page_size)
            .all()
        )

        # Batch-fetch models for the paginated providers only
        provider_ids = [p.id for p in providers]
        models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
        api_key_by_provider: Dict[int, Dict[str, Any]] = {}
        if provider_ids:
            models = (
                self.db.query(Model)
                .filter(Model.service_provider_id.in_(provider_ids))
                .order_by(Model.id)
                .all()
            )
            for m in models:
                models_by_provider.setdefault(m.service_provider_id, []).append({
                    "id": m.id,
                    "service_provider_id": m.service_provider_id,
                    "name": m.name,
                    "meta_data": m.meta_data,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                })

            api_keys = (
                self.db.query(ApiKey)
                .filter(
                    ApiKey.service_provider_id.in_(provider_ids),
                    ApiKey.status == "active",
                )
                .order_by(ApiKey.service_provider_id, ApiKey.id.desc())
                .all()
            )
            for k in api_keys:
                # First (latest) wins per provider
                if k.service_provider_id in api_key_by_provider:
                    continue
                api_key_by_provider[k.service_provider_id] = {
                    "id": k.id,
                    "uuid": str(k.uuid),
                    "name": k.name,
                    "description": k.description,
                    "api_key_hint": k.api_key_hint,
                    "service_provider_id": k.service_provider_id,
                    "additional_credentials": k.additional_credentials,
                    "rate_limit_config": k.rate_limit_config,
                    "expires_at": k.expires_at,
                    "status": k.status,
                    "is_valid": k.is_valid,
                    "created_at": k.created_at,
                    "updated_at": k.updated_at,
                }

        data = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "provider_type": p.provider_type,
                "logo_url": p.logo_url,
                "website_url": p.website_url,
                "documentation_url": p.documentation_url,
                "base_url": p.base_url,
                "auth_type": p.auth_type,
                "supports_streaming": p.supports_streaming,
                "config_schema": p.config_schema,
                "is_system": p.is_system,
                "status": p.status,
                "created_at": p.created_at,
                "meta_data_schema": p.meta_data_schema,
                "models": models_by_provider.get(p.id, []),
                "api_key": api_key_by_provider.get(p.id),
            }
            for p in providers
        ]

        total_pages = (total + page_size - 1) // page_size
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def get_service_provider(self, provider_id: int) -> Dict[str, Any]:
        provider = self.db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service provider not found"
            )

        return {
            "id": provider.id,
            "uuid": str(provider.uuid),
            "name": provider.name,
            "display_name": provider.display_name,
            "description": provider.description,
            "provider_type": provider.provider_type,
            "logo_url": provider.logo_url,
            "website_url": provider.website_url,
            "documentation_url": provider.documentation_url,
            "base_url": provider.base_url,
            "auth_type": provider.auth_type,
            "supports_streaming": provider.supports_streaming,
            "config_schema": provider.config_schema,
            "is_system": provider.is_system,
            "status": provider.status,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
            "api_key": self._get_provider_api_key(provider.id),
        }

    def delete_service_provider(self, provider_id: int) -> Dict[str, str]:
        provider = self.db.query(ServiceProvider).filter(ServiceProvider.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service provider not found"
            )

        if provider.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a system service provider"
            )

        self.db.delete(provider)
        self.db.commit()

        return {"message": "Service provider deleted successfully"}
