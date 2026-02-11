from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.generated_api_key import GeneratedApiKey


class GeneratedApiKeyService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None):
        super().__init__(db, user_id)

    def upsert_basic_key(
        self,
        name: str,
        key_value: str,
        key_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create or update a basic API key with only name and key_value."""
        current_time = int(time.time())

        if key_id:
            # Update existing key
            key = self.db.query(GeneratedApiKey).filter(GeneratedApiKey.id == key_id).first()
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generated API key not found"
                )
            key.name = name
            key.key_value = key_value
            key.updated_at = current_time
        else:
            # Create new key
            key = GeneratedApiKey(
                uuid=uuid_lib.uuid4(),
                name=name,
                key_value=key_value,
                created_at=current_time,
                updated_at=current_time
            )
            self.db.add(key)

        self.db.commit()
        self.db.refresh(key)

        return {
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "key_value": key.key_value,
            "created_at": key.created_at,
            "updated_at": key.updated_at
        }

    def upsert_full_key(
        self,
        name: str,
        key_value: str,
        key_id: Optional[int] = None,
        domains: Optional[List[str]] = None,
        abuse_prevention: Optional[Dict[str, Any]] = None,
        fraud_protection: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Create or update an API key with full configuration."""
        current_time = int(time.time())

        if key_id:
            # Update existing key
            key = self.db.query(GeneratedApiKey).filter(GeneratedApiKey.id == key_id).first()
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generated API key not found"
                )
            key.name = name
            key.key_value = key_value
            key.domains = domains
            key.abuse_prevention = abuse_prevention
            key.fraud_protection = fraud_protection
            key.updated_at = current_time
        else:
            # Create new key
            key = GeneratedApiKey(
                uuid=uuid_lib.uuid4(),
                name=name,
                key_value=key_value,
                domains=domains,
                abuse_prevention=abuse_prevention,
                fraud_protection=fraud_protection,
                created_at=current_time,
                updated_at=current_time
            )
            self.db.add(key)

        self.db.commit()
        self.db.refresh(key)

        return {
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "key_value": key.key_value,
            "domains": key.domains,
            "abuse_prevention": key.abuse_prevention,
            "fraud_protection": key.fraud_protection,
            "created_at": key.created_at,
            "updated_at": key.updated_at
        }

    def get_all_keys(self) -> List[Dict[str, Any]]:
        """Get all generated API keys."""
        keys = self.db.query(GeneratedApiKey).all()

        return [{
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "key_value": key.key_value,
            "domains": key.domains,
            "abuse_prevention": key.abuse_prevention,
            "fraud_protection": key.fraud_protection,
            "created_at": key.created_at,
            "updated_at": key.updated_at
        } for key in keys]

    def get_key_by_id(self, key_id: int) -> Dict[str, Any]:
        """Get a specific API key by ID."""
        key = self.db.query(GeneratedApiKey).filter(
            GeneratedApiKey.id == key_id
        ).first()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated API key not found"
            )

        return {
            "id": key.id,
            "uuid": str(key.uuid),
            "name": key.name,
            "key_value": key.key_value,
            "domains": key.domains,
            "abuse_prevention": key.abuse_prevention,
            "fraud_protection": key.fraud_protection,
            "created_at": key.created_at,
            "updated_at": key.updated_at
        }

    def delete_key(self, key_id: int) -> Dict[str, str]:
        """Delete an API key by ID."""
        key = self.db.query(GeneratedApiKey).filter(
            GeneratedApiKey.id == key_id
        ).first()

        if not key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated API key not found"
            )

        self.db.delete(key)
        self.db.commit()

        return {"message": "Generated API key deleted successfully"}
