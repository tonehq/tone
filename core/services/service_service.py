from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.service import Service
from core.models.service_provider import ServiceProvider
from core.models.models import Model
from core.models.api_key import ApiKey


class ServiceConfigService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def upsert_service(self, service_provider_id: int, name: str, service_type: str,
                       config: Dict, api_key_id: Optional[int] = None,
                       description: Optional[str] = None,
                       is_default: bool = False, is_public: bool = False,
                       tags: Optional[list] = None, service_uuid: Optional[str] = None,
                       service_status: Optional[str] = None,
                       api_key_value: Optional[str] = None,
                       api_key_name: Optional[str] = None,
                       additional_credentials: Optional[Dict] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == service_provider_id
        ).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service provider not found"
            )

        if api_key_id:
            api_key = self.db.query(ApiKey).filter(
                ApiKey.id == api_key_id,
                ApiKey.status == 'active'
            ).first()
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found or inactive"
                )
        elif api_key_value:
            from core.services.api_key_service import ApiKeyService
            api_key_result = ApiKeyService(self.db, user_id=self._user_id, org_id=self.org_id).upsert_api_key(
                service_provider_id=service_provider_id,
                name=api_key_name or f"{name} key",
                api_key_value=api_key_value,
                additional_credentials=additional_credentials,
            )
            api_key_id = api_key_result["id"]

        if is_default:
            self.db.query(Service).filter(
                Service.service_type == service_type,
                Service.is_default == True
            ).update({"is_default": False, "updated_at": current_time})

        values = {
            "uuid": UUID(service_uuid) if service_uuid else uuid_lib.uuid4(),
            "service_provider_id": service_provider_id,
            "api_key_id": api_key_id,
            "name": name,
            "description": description,
            "service_type": service_type,
            "config": config,
            "is_default": is_default,
            "is_public": is_public,
            "tags": tags,
            "created_by": self._user_id,
            "created_at": current_time,
            "updated_at": current_time
        }

        if service_status is not None:
            values["status"] = service_status

        update_fields = [
            "service_provider_id", "api_key_id", "name", "description",
            "service_type", "config", "is_default", "is_public", "tags", "updated_at"
        ]
        if service_status is not None:
            update_fields.append("status")

        self.upsert(
            model=Service,
            values=values,
            conflict_fields=["uuid"],
            update_fields=update_fields
        )

        record_uuid = values["uuid"]
        svc = self.db.query(Service).filter(Service.uuid == record_uuid).first()

        api_key_hint = None
        if svc.api_key_id:
            ak = self.db.query(ApiKey.api_key_hint).filter(ApiKey.id == svc.api_key_id).scalar()
            api_key_hint = ak

        return {
            "id": svc.id,
            "uuid": str(svc.uuid),
            "name": svc.name,
            "description": svc.description,
            "service_type": svc.service_type,
            "service_provider_id": svc.service_provider_id,
            "api_key_id": svc.api_key_id,
            "api_key_hint": api_key_hint,
            "config": svc.config,
            "status": svc.status,
            "is_default": svc.is_default,
            "is_public": svc.is_public,
            "tags": svc.tags,
            "created_at": svc.created_at,
            "updated_at": svc.updated_at
        }

    def get_all_services(self, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.query(Service).join(
            ServiceProvider, Service.service_provider_id == ServiceProvider.id
        ).filter(Service.status == 'active').add_entity(ServiceProvider)

        if service_type:
            query = query.filter(Service.service_type == service_type)

        results = query.all()

        # Collect api_key_ids to batch-fetch hints
        api_key_ids = [svc.api_key_id for svc, _ in results if svc.api_key_id]
        api_key_hints = {}
        if api_key_ids:
            hint_rows = self.db.query(ApiKey.id, ApiKey.api_key_hint).filter(ApiKey.id.in_(api_key_ids)).all()
            api_key_hints = {row.id: row.api_key_hint for row in hint_rows}

        # Batch-fetch models for all providers referenced by these services
        provider_ids = list({svc.service_provider_id for svc, _ in results})
        models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
        if provider_ids:
            models = (
                self.db.query(Model)
                .filter(Model.service_provider_id.in_(provider_ids), Model.status == "active")
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

        return [{
            "id": svc.id,
            "uuid": str(svc.uuid),
            "name": svc.name,
            "display_name": svc.name,
            "description": svc.description,
            "service_type": svc.service_type,
            "service_provider_id": svc.service_provider_id,
            "service_provider_name": provider.display_name,
            "provider_type": provider.provider_type,
            "api_key_id": svc.api_key_id,
            "api_key_hint": api_key_hints.get(svc.api_key_id) if svc.api_key_id else None,
            "config": svc.config,
            "status": svc.status,
            "is_default": svc.is_default,
            "is_public": svc.is_public,
            "tags": svc.tags,
            "usage_count": svc.usage_count,
            "last_used_at": svc.last_used_at,
            "created_at": svc.created_at,
            "models": models_by_provider.get(svc.service_provider_id, []),
            "meta_data_schema": provider.meta_data_schema,
        } for svc, provider in results]

    def get_service(self, service_id: int) -> Dict[str, Any]:
        result = self.query(Service).join(
            ServiceProvider, Service.service_provider_id == ServiceProvider.id
        ).filter(Service.id == service_id).add_entity(ServiceProvider).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        svc, provider = result

        api_key_hint = None
        if svc.api_key_id:
            ak = self.db.query(ApiKey.api_key_hint).filter(ApiKey.id == svc.api_key_id).scalar()
            api_key_hint = ak

        return {
            "id": svc.id,
            "uuid": str(svc.uuid),
            "name": svc.name,
            "description": svc.description,
            "service_type": svc.service_type,
            "service_provider_id": svc.service_provider_id,
            "service_provider_name": provider.display_name,
            "provider_type": provider.provider_type,
            "api_key_id": svc.api_key_id,
            "api_key_hint": api_key_hint,
            "config": svc.config,
            "status": svc.status,
            "is_default": svc.is_default,
            "is_public": svc.is_public,
            "tags": svc.tags,
            "usage_count": svc.usage_count,
            "last_used_at": svc.last_used_at,
            "created_at": svc.created_at,
            "updated_at": svc.updated_at
        }

    def delete_service(self, service_id: int) -> Dict[str, str]:
        svc = self.query(Service).filter(Service.id == service_id).first()

        if not svc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )

        self.db.delete(svc)
        self.db.commit()

        return {"message": "Service deleted successfully"}

    def get_default_service(self, service_type: str) -> Dict[str, Any]:
        result = self.query(Service).join(
            ServiceProvider, Service.service_provider_id == ServiceProvider.id
        ).filter(
            Service.service_type == service_type,
            Service.is_default == True,
            Service.status == 'active'
        ).add_entity(ServiceProvider).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No default service found for type: {service_type}"
            )

        svc, provider = result

        api_key_hint = None
        if svc.api_key_id:
            ak = self.db.query(ApiKey.api_key_hint).filter(ApiKey.id == svc.api_key_id).scalar()
            api_key_hint = ak

        return {
            "id": svc.id,
            "uuid": str(svc.uuid),
            "name": svc.name,
            "service_type": svc.service_type,
            "service_provider_id": svc.service_provider_id,
            "service_provider_name": provider.display_name,
            "api_key_id": svc.api_key_id,
            "api_key_hint": api_key_hint,
            "config": svc.config,
            "status": svc.status,
            "is_default": svc.is_default
        }
