from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.service_provider import ServiceProvider
from core.models.models import Model


class ServiceProviderService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None):
        super().__init__(db, user_id)

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
                                auth_type: str, description: Optional[str] = None,
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
            "updated_at": provider.updated_at
        }

    def get_all_service_providers(self, provider_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (
            self.db.query(ServiceProvider, Model)
            .outerjoin(Model, Model.service_provider_id == ServiceProvider.id)
            .filter(ServiceProvider.status == "active")
        )

        if provider_type:
            query = query.filter(ServiceProvider.provider_type == provider_type)

        rows = query.order_by(ServiceProvider.id, Model.id).all()

        # Group by provider, collect models
        by_id: Dict[int, Dict[str, Any]] = {}
        for sp, m in rows:
            if sp.id not in by_id:
                by_id[sp.id] = {
                    "id": sp.id,
                    "uuid": str(sp.uuid),
                    "name": sp.name,
                    "display_name": sp.display_name,
                    "description": sp.description,
                    "provider_type": sp.provider_type,
                    "logo_url": sp.logo_url,
                    "website_url": sp.website_url,
                    "documentation_url": sp.documentation_url,
                    "base_url": sp.base_url,
                    "auth_type": sp.auth_type,
                    "supports_streaming": sp.supports_streaming,
                    "config_schema": sp.config_schema,
                    "is_system": sp.is_system,
                    "status": sp.status,
                    "created_at": sp.created_at,
                    "models": [],
                }
            if m is not None:
                by_id[sp.id]["models"].append({
                    "id": m.id,
                    "service_provider_id": m.service_provider_id,
                    "name": m.name,
                    "meta_data": m.meta_data,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                })

        return list(by_id.values())

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
            "updated_at": provider.updated_at
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
