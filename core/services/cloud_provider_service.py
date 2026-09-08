"""Business logic for the Cloud Providers catalog. Mirrors the provider-CRUD
slice of ``ModelProviderService`` — routes are thin wrappers over this.

Like ``ModelProvider``, ``CloudProvider`` is a GLOBAL catalog (extends
``TimestampModel``, no ``organization_id``), so reads/writes here are not
org-scoped; write endpoints are admin-gated at the route layer.
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.models.cloud_provider import CloudProvider
from core.models.model import Model
from core.services.base import BaseService

ALLOWED_CLOUD_PROVIDER_SORT_FIELDS = {
    "display_name",
    "slug",
    "provider_id",
    "is_active",
    "created_at",
    "updated_at",
}


def _parse_uuid(value: Any, *, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field}"
        )


def _optional_str(body: dict, key: str) -> Optional[str]:
    return (body.get(key) or "").strip() or None


class CloudProviderService(BaseService):
    """CRUD for the global cloud-provider catalog."""

    def _cloud_provider_or_404(self, cloud_provider_id: UUID) -> CloudProvider:
        record = (
            self.db.query(CloudProvider)
            .filter(CloudProvider.id == cloud_provider_id)
            .first()
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cloud provider not found"
            )
        return record

    def cloud_provider_response(self, cp: CloudProvider) -> dict:
        """Public formatter — one place so create/update/list responses match."""
        return {
            "id": str(cp.id),
            "provider_id": cp.provider_id,
            "slug": cp.slug,
            "display_name": cp.display_name,
            "description": cp.description,
            "website_url": cp.website_url,
            "is_active": bool(cp.is_active),
            "meta_data_schema": cp.meta_data_schema,
            "created_at": int(cp.created_at.timestamp()) if cp.created_at else None,
            "updated_at": int(cp.updated_at.timestamp()) if cp.updated_at else None,
        }

    def _assert_unique(
        self,
        *,
        provider_id: str | None = None,
        slug: str | None = None,
        exclude_id: UUID | None = None,
    ) -> None:
        """Pre-check provider_id/slug uniqueness so duplicates return a clean
        409 instead of a 500 IntegrityError."""
        for field, value in (("provider_id", provider_id), ("slug", slug)):
            if not value:
                continue
            q = self.db.query(CloudProvider.id).filter(
                getattr(CloudProvider, field) == value
            )
            if exclude_id is not None:
                q = q.filter(CloudProvider.id != exclude_id)
            if q.first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A cloud provider with this {field} already exists.",
                )

    def list_cloud_providers(self, body: dict) -> dict:
        page = max(int(body.get("page") or 1), 1)
        page_size = min(max(int(body.get("page_size") or 20), 1), 100)
        search = (body.get("search") or "").strip()
        sort_by = body.get("sort_by")
        is_active = body.get("is_active")

        q = self.db.query(CloudProvider)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    CloudProvider.display_name.ilike(like),
                    CloudProvider.slug.ilike(like),
                    CloudProvider.provider_id.ilike(like),
                )
            )
        if is_active is True or is_active is False:
            q = q.filter(CloudProvider.is_active.is_(bool(is_active)))

        total = q.count()

        order_by = CloudProvider.display_name.asc()
        if sort_by:
            d = sort_by.startswith("-")
            f = sort_by.lstrip("-")
            if f in ALLOWED_CLOUD_PROVIDER_SORT_FIELDS:
                col = getattr(CloudProvider, f)
                order_by = col.desc() if d else col.asc()
        q = q.order_by(order_by)

        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [self.cloud_provider_response(cp) for cp in rows],
            "total": int(total),
            "page": page,
            "page_size": page_size,
        }

    def get_cloud_provider(self, cloud_provider_id: str) -> CloudProvider:
        cp_uuid = _parse_uuid(cloud_provider_id, field="cloud provider id")
        return self._cloud_provider_or_404(cp_uuid)

    def create_cloud_provider(self, body: dict) -> CloudProvider:
        provider_id_str = (body.get("provider_id") or "").strip()
        slug = (body.get("slug") or "").strip()
        display_name = (body.get("display_name") or "").strip()
        if not provider_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="provider_id is required"
            )
        if not slug:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="slug is required"
            )
        if not display_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="display_name is required"
            )

        meta_data_schema = body.get("meta_data_schema")
        if meta_data_schema is not None and not isinstance(meta_data_schema, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meta_data_schema must be a JSON object",
            )

        self._assert_unique(provider_id=provider_id_str, slug=slug)

        record = CloudProvider(
            provider_id=provider_id_str,
            slug=slug,
            display_name=display_name,
            description=_optional_str(body, "description"),
            website_url=_optional_str(body, "website_url"),
            is_active=bool(body.get("is_active", True)),
            meta_data_schema=meta_data_schema,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_cloud_provider(self, cloud_provider_id: str, body: dict) -> CloudProvider:
        cp_uuid = _parse_uuid(cloud_provider_id, field="cloud provider id")
        record = self._cloud_provider_or_404(cp_uuid)

        new_provider_id: str | None = None
        new_slug: str | None = None

        if "provider_id" in body:
            candidate = (body.get("provider_id") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="provider_id cannot be empty",
                )
            if candidate != record.provider_id:
                new_provider_id = candidate

        if "slug" in body:
            candidate = (body.get("slug") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="slug cannot be empty",
                )
            if candidate != record.slug:
                new_slug = candidate

        if new_provider_id or new_slug:
            self._assert_unique(
                provider_id=new_provider_id, slug=new_slug, exclude_id=record.id
            )

        if new_provider_id:
            record.provider_id = new_provider_id
        if new_slug:
            record.slug = new_slug

        if "display_name" in body:
            candidate = (body.get("display_name") or "").strip()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="display_name cannot be empty",
                )
            record.display_name = candidate
        if "description" in body:
            record.description = _optional_str(body, "description")
        if "website_url" in body:
            record.website_url = _optional_str(body, "website_url")
        if "is_active" in body:
            record.is_active = bool(body["is_active"])
        if "meta_data_schema" in body:
            value = body.get("meta_data_schema")
            if value is not None and not isinstance(value, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="meta_data_schema must be a JSON object",
                )
            record.meta_data_schema = value

        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_cloud_provider(self, cloud_provider_id: str) -> dict:
        """Hard-delete a CloudProvider. Blocked if any model still references it
        so the link isn't silently cleared — reassign those models first."""
        cp_uuid = _parse_uuid(cloud_provider_id, field="cloud provider id")
        record = self._cloud_provider_or_404(cp_uuid)

        in_use = (
            self.db.query(Model.id)
            .filter(Model.cloud_provider_id == cp_uuid)
            .first()
        )
        if in_use:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot delete cloud provider: one or more models are assigned "
                    "to it. Reassign those models first."
                ),
            )

        self.db.delete(record)
        self.db.commit()
        return {"ok": True}
