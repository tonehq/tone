from sqlalchemy.orm import Session
from typing import Dict, Any
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.models import Model
from core.models.service_provider import ServiceProvider


class ModelService(BaseService):
    CREATED_ATTRS = ("service_provider_id", "name", "meta_data")
    UPDATABLE_ATTRS = ("service_provider_id", "name", "meta_data", "updated_at")

    def upsert_model(self, data: Dict[str, Any]):
        if data.get("service_provider_id") is None and data.get("id") is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_provider_id is required when creating a new model",
            )
        if not data.get("name") and data.get("id") is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required when creating a new model",
            )

        model_id = data.get("id")
        now = int(time.time())

        if model_id is not None:
            existing = self.db.query(Model).filter(Model.id == int(model_id)).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model not found",
                )
            update_fields = {}
            if "service_provider_id" in data and data["service_provider_id"] is not None:
                _ensure_service_provider_exists(self.db, int(data["service_provider_id"]))
                update_fields["service_provider_id"] = int(data["service_provider_id"])
            if "name" in data:
                update_fields["name"] = data["name"]
            if "meta_data" in data:
                update_fields["meta_data"] = data["meta_data"]
            update_fields["updated_at"] = now
            for key, value in update_fields.items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        service_provider_id = int(data["service_provider_id"])
        _ensure_service_provider_exists(self.db, service_provider_id)
        values = {
            "service_provider_id": service_provider_id,
            "name": data["name"],
            "meta_data": data.get("meta_data"),
            "created_at": now,
            "updated_at": now,
        }
        model = Model(**values)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model


def _ensure_service_provider_exists(db: Session, service_provider_id: int) -> None:
    provider = db.query(ServiceProvider).filter(ServiceProvider.id == service_provider_id).first()
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service provider not found",
        )
