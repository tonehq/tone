from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.models import Model
from core.models.service_provider import ServiceProvider


class ModelService(BaseService):
    CREATED_ATTRS = ("service_provider_id", "name", "meta_data", "api_key_id", "status", "service_type")
    UPDATABLE_ATTRS = ("service_provider_id", "name", "meta_data", "api_key_id", "status", "service_type", "updated_at")

    def get_models_by_provider(
        self,
        service_provider_id: int,
        name: Optional[str] = None,
        status_filter: Optional[str] = None,
        service_type: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """List models for a provider with optional filters, sorting, and pagination."""
        from sqlalchemy import asc, desc

        _ensure_service_provider_exists(self.db, service_provider_id)

        query = self.db.query(Model).filter(Model.service_provider_id == service_provider_id)

        if name:
            query = query.filter(Model.name.ilike(f"%{name}%"))
        if status_filter:
            query = query.filter(Model.status == status_filter)
        if service_type:
            query = query.filter(Model.service_type == service_type)

        total = query.count()

        sort_column_map = {
            "created_at": Model.created_at,
            "updated_at": Model.updated_at,
            "name": Model.name,
        }
        sort_column = sort_column_map.get(sort_by, Model.created_at)
        order_func = asc if sort_order == "asc" else desc
        offset = (page - 1) * page_size

        models = (
            query.order_by(order_func(sort_column), Model.id)
            .offset(offset)
            .limit(page_size)
            .all()
        )

        data = [
            {
                "id": m.id,
                "service_provider_id": m.service_provider_id,
                "name": m.name,
                "meta_data": m.meta_data,
                "api_key_id": m.api_key_id,
                "status": m.status,
                "service_type": m.service_type,
                "meta_data_schema": m.meta_data_schema,
                "auth_meta_data": m.auth_meta_data,
                "endpoint_url": m.endpoint_url,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in models
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

    def delete_model(self, model_id: int):
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )
        self.db.delete(model)
        self.db.commit()
        return {"message": "Model deleted successfully"}

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
            if "api_key_id" in data:
                update_fields["api_key_id"] = int(data["api_key_id"]) if data["api_key_id"] is not None else None
            if "status" in data:
                update_fields["status"] = data["status"]
            if "service_type" in data:
                update_fields["service_type"] = data["service_type"]
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
            "api_key_id": int(data["api_key_id"]) if data.get("api_key_id") is not None else None,
            "status": data.get("status", "active"),
            "service_type": data.get("service_type"),
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
