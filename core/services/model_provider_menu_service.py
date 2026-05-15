from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_
from typing import List, Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.model_provider_menu import ModelProviderMenu
from core.models.model_menu import ModelMenu
from core.models.account import Account
from core.models.model_instance import ModelInstance


class ModelProviderMenuService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def _exists_same_name_and_provider_type(
        self, name: str, provider_type: str, exclude_id: Optional[int] = None
    ) -> bool:
        """True if a record with the same name and provider_type exists (optionally excluding one id)."""
        q = self.db.query(ModelProviderMenu).filter(
            ModelProviderMenu.name == name,
            ModelProviderMenu.provider_type == provider_type,
        )
        if exclude_id is not None:
            q = q.filter(ModelProviderMenu.id != exclude_id)
        return q.first() is not None

    def upsert_model_provider_menu(self, name: str, display_name: str, provider_type: str,
                                   auth_type: str,
                                   description: Optional[str] = None,
                                   logo_url: Optional[str] = None, website_url: Optional[str] = None,
                                   documentation_url: Optional[str] = None, base_url: Optional[str] = None,
                                   supports_streaming: bool = False, config_schema: Optional[Dict] = None,
                                   is_system: bool = False, provider_status: Optional[str] = None,
                                   provider_id: Optional[int] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        if provider_id is not None:
            existing = self.db.query(ModelProviderMenu).filter(ModelProviderMenu.id == provider_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model provider menu not found",
                )
            if self._exists_same_name_and_provider_type(name, provider_type, exclude_id=provider_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A model provider menu with this name and provider_type already exists.",
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
                    detail="A model provider menu with this name and provider_type already exists.",
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
            provider = ModelProviderMenu(**values)
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
            "updated_at": provider.updated_at,
        }

    def get_all_model_provider_menus(
        self,
        provider_type: Optional[str] = None,
        name: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: Optional[int] = 10,
    ) -> Dict[str, Any]:
        """List model provider menus with optional filters, sorting, and pagination.

        Returns {"data": [...], "pagination": {...}}.
        """
        query = self.db.query(ModelProviderMenu)

        if status_filter:
            query = query.filter(ModelProviderMenu.status == status_filter)

        if provider_type:
            query = query.filter(ModelProviderMenu.provider_type == provider_type)

        if name:
            query = query.filter(
                or_(
                    ModelProviderMenu.name.ilike(f"%{name}%"),
                    ModelProviderMenu.display_name.ilike(f"%{name}%"),
                )
            )

        # Count BEFORE pagination
        total = query.count()

        sort_column_map = {
            "created_at": ModelProviderMenu.created_at,
            "updated_at": ModelProviderMenu.updated_at,
            "name": ModelProviderMenu.name,
            "display_name": ModelProviderMenu.display_name,
        }
        sort_column = sort_column_map.get(sort_by, ModelProviderMenu.created_at)
        order_func = asc if sort_order == "asc" else desc

        ordered_query = query.order_by(order_func(sort_column), ModelProviderMenu.id)

        if page_size is not None:
            offset = (page - 1) * page_size
            providers = ordered_query.offset(offset).limit(page_size).all()
        else:
            providers = ordered_query.all()

        # Batch-fetch ModelMenu records for the paginated providers only
        provider_ids = [p.id for p in providers]
        models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
        if provider_ids:
            models = (
                self.db.query(ModelMenu)
                .filter(ModelMenu.model_provider_menu_id.in_(provider_ids))
                .order_by(ModelMenu.id)
                .all()
            )
            for m in models:
                models_by_provider.setdefault(m.model_provider_menu_id, []).append({
                    "id": m.id,
                    "model_provider_menu_id": m.model_provider_menu_id,
                    "name": m.name,
                    "meta_data": m.meta_data,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                })

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
            }
            for p in providers
        ]

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

    def get_model_provider_menu(self, provider_id: int) -> Dict[str, Any]:
        provider = self.db.query(ModelProviderMenu).filter(ModelProviderMenu.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model provider menu not found"
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
        }

    def get_providers_with_accounts(self, provider_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return model providers that have at least one active Account (org-scoped).

        Resolution chain: Account (org-scoped, active) → ModelInstance (active) → ModelMenu → ModelProviderMenu.
        """
        # Find active org-scoped accounts
        active_accounts = self.query(Account).filter(Account.status == 'active').all()
        acct_ids = [a.id for a in active_accounts]

        if not acct_ids:
            return []

        # Find active ModelInstances linked to these accounts
        mi_rows = (
            self.db.query(ModelInstance)
            .filter(
                ModelInstance.account_id.in_(acct_ids),
                ModelInstance.status == 'active',
            )
            .all()
        )

        # Get unique model_menu_ids from those instances
        model_menu_ids = list({mi.model_menu_id for mi in mi_rows})
        if not model_menu_ids:
            return []

        # Resolve ModelMenu → ModelProviderMenu IDs
        model_menus = (
            self.db.query(ModelMenu)
            .filter(ModelMenu.id.in_(model_menu_ids))
            .all()
        )
        provider_ids = list({mm.model_provider_menu_id for mm in model_menus})

        if not provider_ids:
            return []

        # Query ModelProviderMenus with optional type filter
        providers_q = (
            self.db.query(ModelProviderMenu)
            .filter(ModelProviderMenu.id.in_(provider_ids))
        )
        if provider_type:
            providers_q = providers_q.filter(ModelProviderMenu.provider_type == provider_type)
        providers = providers_q.order_by(ModelProviderMenu.id).all()

        # Batch-fetch models for returned providers
        final_provider_ids = [p.id for p in providers]
        models = (
            self.db.query(ModelMenu)
            .filter(ModelMenu.model_provider_menu_id.in_(final_provider_ids))
            .order_by(ModelMenu.id)
            .all()
        )
        models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
        for m in models:
            models_by_provider.setdefault(m.model_provider_menu_id, []).append({
                "id": m.id,
                "model_provider_menu_id": m.model_provider_menu_id,
                "name": m.name,
                "meta_data": m.meta_data,
                "service_type": m.service_type,
            })

        return [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "provider_type": p.provider_type,
                "meta_data_schema": p.meta_data_schema,
                "models": models_by_provider.get(p.id, []),
            }
            for p in providers
        ]

    def delete_model_provider_menu(self, provider_id: int) -> Dict[str, str]:
        provider = self.db.query(ModelProviderMenu).filter(ModelProviderMenu.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model provider menu not found"
            )

        if provider.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a system model provider menu"
            )

        self.db.delete(provider)
        self.db.commit()

        return {"message": "Model provider menu deleted successfully"}
