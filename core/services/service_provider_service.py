from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.service_provider import ServiceProvider


class ServiceProviderService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None):
        super().__init__(db, user_id)

    def upsert_service_provider(self, name: str, display_name: str, provider_type: str,
                                auth_type: str, description: Optional[str] = None,
                                logo_url: Optional[str] = None, website_url: Optional[str] = None,
                                documentation_url: Optional[str] = None, base_url: Optional[str] = None,
                                supports_streaming: bool = False, config_schema: Optional[Dict] = None,
                                is_system: bool = False, provider_status: Optional[str] = None) -> Dict[str, Any]:
        current_time = int(time.time())

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
            "updated_at": current_time
        }

        if provider_status is not None:
            values["status"] = provider_status

        update_fields = [
            "display_name", "description", "provider_type", "logo_url",
            "website_url", "documentation_url", "base_url", "auth_type",
            "supports_streaming", "config_schema", "is_system", "updated_at"
        ]
        if provider_status is not None:
            update_fields.append("status")

        self.upsert(
            model=ServiceProvider,
            values=values,
            conflict_fields=["name"],
            update_fields=update_fields
        )

        provider = self.db.query(ServiceProvider).filter(ServiceProvider.name == name).first()

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
        query = self.db.query(ServiceProvider).filter(ServiceProvider.status == 'active')

        if provider_type:
            query = query.filter(ServiceProvider.provider_type == provider_type)

        providers = query.all()

        return [{
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
            "created_at": p.created_at
        } for p in providers]

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
