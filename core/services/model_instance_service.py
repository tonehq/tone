from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from typing import Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.model_instance import ModelInstance
from core.models.model_menu import ModelMenu


class ModelInstanceService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def upsert_model_instance(self, model_menu_id: int,
                               endpoint_url: Optional[str] = None,
                               instance_status: Optional[str] = None,
                               meta_data: Optional[Dict] = None,
                               instance_uuid: Optional[str] = None,
                               instance_id: Optional[int] = None,
                               account_id: Optional[int] = None,
                               host_region: Optional[str] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        # Validate foreign keys
        _ensure_model_menu_exists(self.db, model_menu_id)

        if instance_id is not None:
            existing = self.db.query(ModelInstance).filter(ModelInstance.id == instance_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model instance not found",
                )
            existing.model_menu_id = model_menu_id
            existing.account_id = account_id
            existing.host_region = host_region
            existing.endpoint_url = endpoint_url
            existing.meta_data = meta_data
            existing.updated_at = current_time
            if instance_status is not None:
                existing.status = instance_status
            self.db.commit()
            self.db.refresh(existing)
            instance = existing
        else:
            values = {
                "uuid": uuid_lib.UUID(instance_uuid) if instance_uuid else uuid_lib.uuid4(),
                "model_menu_id": model_menu_id,
                "account_id": account_id,
                "host_region": host_region,
                "endpoint_url": endpoint_url,
                "meta_data": meta_data,
                "created_at": current_time,
                "updated_at": current_time,
            }
            if instance_status is not None:
                values["status"] = instance_status
            instance = ModelInstance(**values)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)

        return _instance_to_dict(instance)

    def get_all_model_instances(
        self,
        model_menu_id: Optional[int] = None,
        account_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: Optional[int] = 10,
    ) -> Dict[str, Any]:
        query = self.db.query(ModelInstance)

        if model_menu_id is not None:
            query = query.filter(ModelInstance.model_menu_id == model_menu_id)

        if account_id is not None:
            query = query.filter(ModelInstance.account_id == account_id)

        if status_filter:
            query = query.filter(ModelInstance.status == status_filter)

        # Count BEFORE pagination
        total = query.count()

        sort_column_map = {
            "created_at": ModelInstance.created_at,
            "updated_at": ModelInstance.updated_at,
        }
        sort_column = sort_column_map.get(sort_by, ModelInstance.created_at)
        order_func = asc if sort_order == "asc" else desc

        ordered_query = query.order_by(order_func(sort_column), ModelInstance.id)

        if page_size is not None:
            offset = (page - 1) * page_size
            instances = ordered_query.offset(offset).limit(page_size).all()
        else:
            instances = ordered_query.all()

        data = [_instance_to_dict(i) for i in instances]

        if page_size is not None:
            total_pages = (total + page_size - 1) // page_size
        else:
            total_pages = 1

        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size if page_size is not None else total,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def get_model_instance(self, instance_id: int) -> Dict[str, Any]:
        instance = self.db.query(ModelInstance).filter(ModelInstance.id == instance_id).first()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model instance not found"
            )

        return _instance_to_dict(instance)

    def delete_model_instance(self, instance_id: int) -> Dict[str, str]:
        instance = self.db.query(ModelInstance).filter(ModelInstance.id == instance_id).first()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model instance not found"
            )

        self.db.delete(instance)
        self.db.commit()

        return {"message": "Model instance deleted successfully"}


def _instance_to_dict(instance: ModelInstance) -> Dict[str, Any]:
    return {
        "id": instance.id,
        "uuid": str(instance.uuid),
        "model_menu_id": instance.model_menu_id,
        "account_id": instance.account_id,
        "host_region": instance.host_region,
        "endpoint_url": instance.endpoint_url,
        "status": instance.status,
        "meta_data": instance.meta_data,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
    }


def _ensure_model_menu_exists(db: Session, model_menu_id: int) -> None:
    model = db.query(ModelMenu).filter(ModelMenu.id == model_menu_id).first()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model menu not found",
        )
