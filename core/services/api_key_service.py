from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.api_key import ApiKey
from core.models.service_provider import ServiceProvider
from core.utils.encryption import encrypt, decrypt


class ApiKeyService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def upsert_api_key(self, service_provider_id: int, name: str,
                       api_key_value: str, description: Optional[str] = None,
                       additional_credentials: Optional[Dict] = None,
                       rate_limit_config: Optional[Dict] = None,
                       expires_at: Optional[int] = None,
                       key_uuid: Optional[str] = None,
                       key_status: Optional[str] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == service_provider_id
        ).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service provider not found"
            )

        # Generate hint: for JSON credentials show project_id, else show first/last chars
        if api_key_value.strip().startswith("{"):
            import json as _json
            try:
                cred_data = _json.loads(api_key_value)
                identifier = cred_data.get("project_id") or cred_data.get("client_email") or ""
                hint = f"json:{identifier[:20]}..." if identifier else "json:****"
            except (ValueError, _json.JSONDecodeError):
                hint = api_key_value[:4] + "..." + api_key_value[-4:] if len(api_key_value) > 8 else "****"
        else:
            hint = api_key_value[:4] + "..." + api_key_value[-4:] if len(api_key_value) > 8 else "****"

        values = {
            "uuid": UUID(key_uuid) if key_uuid else uuid_lib.uuid4(),
            "service_provider_id": service_provider_id,
            "name": name,
            "description": description,
            "api_key_encrypted": encrypt(api_key_value),
            "api_key_hint": hint,
            "additional_credentials": additional_credentials,
            "rate_limit_config": rate_limit_config,
            "expires_at": expires_at,
            "created_by": self._user_id,
            "created_at": current_time,
            "updated_at": current_time
        }

        if key_status is not None:
            values["status"] = key_status

        update_fields = [
            "service_provider_id", "name", "description", "api_key_encrypted",
            "api_key_hint", "additional_credentials", "rate_limit_config",
            "expires_at", "updated_at"
        ]
        if key_status is not None:
            update_fields.append("status")

        self.upsert(
            model=ApiKey,
            values=values,
            conflict_fields=["uuid"],
            update_fields=update_fields,
            extra_update={"is_valid": False, "last_validated_at": None, "validation_error": None}
        )

        record_uuid = values["uuid"]
        api_key = self.db.query(ApiKey).filter(ApiKey.uuid == record_uuid).first()

        # API key change can affect any agent — invalidate all cached agent bot data
        from core.services.redis_service import cache_delete_pattern
        cache_delete_pattern("agent_bot_data:*")

        return {
            "id": api_key.id,
            "uuid": str(api_key.uuid),
            "name": api_key.name,
            "description": api_key.description,
            "api_key_hint": api_key.api_key_hint,
            "service_provider_id": api_key.service_provider_id,
            "status": api_key.status,
            "is_valid": api_key.is_valid,
            "created_at": api_key.created_at,
            "updated_at": api_key.updated_at
        }

    def list_by_provider(
        self,
        service_provider_id: int,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: Optional[int] = 20,
    ) -> Dict[str, Any]:
        """List api_keys for a single provider, scoped to caller's org."""
        from sqlalchemy import asc, desc

        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == service_provider_id
        ).first()
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service provider not found",
            )

        query = self.query(ApiKey).filter(ApiKey.service_provider_id == service_provider_id)
        if status_filter:
            query = query.filter(ApiKey.status == status_filter)

        total = query.count()

        sort_column_map = {
            "created_at": ApiKey.created_at,
            "updated_at": ApiKey.updated_at,
            "name": ApiKey.name,
            "id": ApiKey.id,
        }
        sort_column = sort_column_map.get(sort_by, ApiKey.created_at)
        order_func = asc if sort_order == "asc" else desc
        query = query.order_by(order_func(sort_column), ApiKey.id.desc())

        if page_size:
            query = query.offset((page - 1) * page_size).limit(page_size)

        rows = query.all()
        data = [
            {
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
                "last_validated_at": k.last_validated_at,
                "validation_error": k.validation_error,
                "last_used_at": k.last_used_at,
                "usage_count": k.usage_count,
                "created_at": k.created_at,
                "updated_at": k.updated_at,
            }
            for k in rows
        ]

        total_pages = (total + page_size - 1) // page_size if page_size else 1
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size or total,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def get_all_api_keys(self) -> List[Dict[str, Any]]:
        base_query = self.query(ApiKey)
        results = base_query.join(
            ServiceProvider, ApiKey.service_provider_id == ServiceProvider.id
        ).filter(
            ApiKey.status == 'active'
        ).add_entity(ServiceProvider).all()

        return [{
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "api_key_hint": key.api_key_hint,
            "service_provider_id": key.service_provider_id,
            "service_provider_name": provider.display_name,
            "provider_type": provider.provider_type,
            "status": key.status,
            "is_valid": key.is_valid,
            "last_used_at": key.last_used_at,
            "usage_count": key.usage_count,
            "created_at": key.created_at,
            "expires_at": key.expires_at
        } for key, provider in results]

    def get_api_key(self, api_key_id: int) -> Dict[str, Any]:
        result = self.query(ApiKey).join(
            ServiceProvider, ApiKey.service_provider_id == ServiceProvider.id
        ).filter(
            ApiKey.id == api_key_id
        ).add_entity(ServiceProvider).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        key, provider = result

        return {
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "description": key.description,
            "api_key": decrypt(key.api_key_encrypted),
            "api_key_hint": key.api_key_hint,
            "service_provider_id": key.service_provider_id,
            "service_provider_name": provider.display_name,
            "provider_type": provider.provider_type,
            "status": key.status,
            "is_valid": key.is_valid,
            "last_validated_at": key.last_validated_at,
            "validation_error": key.validation_error,
            "last_used_at": key.last_used_at,
            "usage_count": key.usage_count,
            "additional_credentials": key.additional_credentials,
            "rate_limit_config": key.rate_limit_config,
            "created_at": key.created_at,
            "updated_at": key.updated_at,
            "expires_at": key.expires_at
        }

    def delete_api_key(self, api_key_id: int) -> Dict[str, str]:
        key = self.query(ApiKey).filter(ApiKey.id == api_key_id).first()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        self.db.delete(key)
        self.db.commit()

        # API key deleted — invalidate all cached agent bot data
        from core.services.redis_service import cache_delete_pattern
        cache_delete_pattern("agent_bot_data:*")

        return {"message": "API key deleted successfully"}

    def validate_api_key(self, api_key_id: int, is_valid: bool,
                         validation_error: Optional[str] = None) -> Dict[str, Any]:
        key = self.query(ApiKey).filter(ApiKey.id == api_key_id).first()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        current_time = int(time.time())
        key.is_valid = is_valid
        key.last_validated_at = current_time
        key.validation_error = validation_error if not is_valid else None
        key.updated_at = current_time
        self.db.commit()

        return {
            "id": key.id,
            "is_valid": key.is_valid,
            "last_validated_at": key.last_validated_at,
            "validation_error": key.validation_error,
            "message": "API key validation updated"
        }
