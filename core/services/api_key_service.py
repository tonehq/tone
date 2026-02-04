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
    def __init__(self, db: Session, user_id: Optional[int] = None):
        super().__init__(db, user_id)

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

    def get_all_api_keys(self) -> List[Dict[str, Any]]:
        results = self.db.query(ApiKey, ServiceProvider).join(
            ServiceProvider, ApiKey.service_provider_id == ServiceProvider.id
        ).filter(
            ApiKey.status == 'active'
        ).all()

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
        result = self.db.query(ApiKey, ServiceProvider).join(
            ServiceProvider, ApiKey.service_provider_id == ServiceProvider.id
        ).filter(
            ApiKey.id == api_key_id
        ).first()

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
        key = self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        self.db.delete(key)
        self.db.commit()

        return {"message": "API key deleted successfully"}

    def validate_api_key(self, api_key_id: int, is_valid: bool,
                         validation_error: Optional[str] = None) -> Dict[str, Any]:
        key = self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()

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
