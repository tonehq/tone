from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_
from typing import Optional, Dict, Any
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.hosting_provider import HostingProvider


class HostingProviderService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def _exists_same_name(
        self, name: str, exclude_id: Optional[int] = None
    ) -> bool:
        """True if a record with the same name exists (optionally excluding one id)."""
        q = self.db.query(HostingProvider).filter(
            HostingProvider.name == name,
        )
        if exclude_id is not None:
            q = q.filter(HostingProvider.id != exclude_id)
        return q.first() is not None

    def upsert_hosting_provider(self, name: str, display_name: str,
                                description: Optional[str] = None,
                                logo_url: Optional[str] = None, website_url: Optional[str] = None,
                                is_system: bool = False, provider_status: Optional[str] = None,
                                provider_id: Optional[int] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        if provider_id is not None:
            existing = self.db.query(HostingProvider).filter(HostingProvider.id == provider_id).first()
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Hosting provider not found",
                )
            if self._exists_same_name(name, exclude_id=provider_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A hosting provider with this name already exists.",
                )
            existing.display_name = display_name
            existing.description = description
            existing.logo_url = logo_url
            existing.website_url = website_url
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
            if self._exists_same_name(name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A hosting provider with this name already exists.",
                )
            values = {
                "uuid": uuid_lib.uuid4(),
                "name": name,
                "display_name": display_name,
                "description": description,
                "logo_url": logo_url,
                "website_url": website_url,
                "is_system": is_system,
                "created_at": current_time,
                "updated_at": current_time,
            }
            if provider_status is not None:
                values["status"] = provider_status
            provider = HostingProvider(**values)
            self.db.add(provider)
            self.db.commit()
            self.db.refresh(provider)

        return {
            "id": provider.id,
            "uuid": str(provider.uuid),
            "name": provider.name,
            "display_name": provider.display_name,
            "description": provider.description,
            "logo_url": provider.logo_url,
            "website_url": provider.website_url,
            "is_system": provider.is_system,
            "status": provider.status,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }

    def get_all_hosting_providers(
        self,
        name: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: Optional[int] = 10,
    ) -> Dict[str, Any]:
        """List hosting providers with optional filters, sorting, and pagination.

        Returns {"data": [...], "pagination": {...}}.
        """
        query = self.db.query(HostingProvider)

        if status_filter:
            query = query.filter(HostingProvider.status == status_filter)

        if name:
            query = query.filter(
                or_(
                    HostingProvider.name.ilike(f"%{name}%"),
                    HostingProvider.display_name.ilike(f"%{name}%"),
                )
            )

        # Count BEFORE pagination
        total = query.count()

        sort_column_map = {
            "created_at": HostingProvider.created_at,
            "updated_at": HostingProvider.updated_at,
            "name": HostingProvider.name,
            "display_name": HostingProvider.display_name,
        }
        sort_column = sort_column_map.get(sort_by, HostingProvider.created_at)
        order_func = asc if sort_order == "asc" else desc

        ordered_query = query.order_by(order_func(sort_column), HostingProvider.id)

        if page_size is not None:
            offset = (page - 1) * page_size
            providers = ordered_query.offset(offset).limit(page_size).all()
        else:
            providers = ordered_query.all()

        data = [
            {
                "id": p.id,
                "uuid": str(p.uuid),
                "name": p.name,
                "display_name": p.display_name,
                "description": p.description,
                "logo_url": p.logo_url,
                "website_url": p.website_url,
                "is_system": p.is_system,
                "status": p.status,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
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

    def get_hosting_provider(self, provider_id: int) -> Dict[str, Any]:
        provider = self.db.query(HostingProvider).filter(HostingProvider.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hosting provider not found"
            )

        return {
            "id": provider.id,
            "uuid": str(provider.uuid),
            "name": provider.name,
            "display_name": provider.display_name,
            "description": provider.description,
            "logo_url": provider.logo_url,
            "website_url": provider.website_url,
            "is_system": provider.is_system,
            "status": provider.status,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }

    def delete_hosting_provider(self, provider_id: int) -> Dict[str, str]:
        provider = self.db.query(HostingProvider).filter(HostingProvider.id == provider_id).first()

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hosting provider not found"
            )

        if provider.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a system hosting provider"
            )

        self.db.delete(provider)
        self.db.commit()

        return {"message": "Hosting provider deleted successfully"}
