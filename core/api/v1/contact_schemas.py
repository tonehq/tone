"""Contact schemas router — org-level, reusable ``ContactSchema`` + ``SchemaField`` CRUD.

Schemas are shared across directories (a directory's ``default_schema_id``) and syncs;
this router owns their lifecycle only. Setting a directory's default is done via
``PATCH /contact-directories/{id}`` — NOT here.

Two routers are exported:
- ``router`` (prefix ``/contact-schemas``): schema CRUD + nested field-create.
- ``field_router`` (prefix ``/schema-fields``): update/delete a field by its own id.

Guards: writes = admin/owner (``require_admin_or_owner``), reads = member
(``require_org_member``). Every handler is org-scoped inside the service.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database.session import get_db
from core.middleware.auth import JWTClaims, require_admin_or_owner, require_org_member
from core.services.contacts.contact_schema_service import ContactSchemaService
from shared.config import settings

router = APIRouter(prefix="/contact-schemas", tags=["contact-schemas"])
field_router = APIRouter(prefix="/schema-fields", tags=["contact-schemas"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateSchemaRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class UpdateSchemaRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class ListSchemasRequest(BaseModel):
    page_no: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class CreateSchemaFieldRequest(BaseModel):
    field_name: str = Field(min_length=1, max_length=64)
    type: str = "string"
    label: Optional[str] = None
    format: Optional[str] = None
    is_mandatory: bool = False
    validators: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, Any]]] = None
    source_key: Optional[str] = None
    display_order: int = 0
    # Free-form per-field config; for date/datetime fields carries
    # {"datetime_format": "...", "timezone": "IANA/Zone"} used by the importer.
    field_metadata: Optional[Dict[str, Any]] = None


class UpdateSchemaFieldRequest(BaseModel):
    label: Optional[str] = None
    type: Optional[str] = None
    format: Optional[str] = None
    is_mandatory: Optional[bool] = None
    validators: Optional[Dict[str, Any]] = None
    options: Optional[List[Dict[str, Any]]] = None
    source_key: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    field_metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

def _schema_service(claims: JWTClaims, db: Session) -> ContactSchemaService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    user_id = UUID(str(claims.user_id)) if getattr(claims, "user_id", None) else None
    return ContactSchemaService(db, user_id=user_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Schema CRUD
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
def create_schema(
    body: CreateSchemaRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    schema = _schema_service(claims, db).create_schema(
        name=body.name,
        description=body.description,
        is_active=body.is_active,
    )
    return schema.to_dict()


@router.post("/list")
def list_schemas(
    body: ListSchemasRequest,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _schema_service(claims, db).list_schemas(
        page_no=body.page_no,
        page_size=body.page_size,
        search=body.search,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
    )


@router.get("/{schema_id}")
def get_schema(
    schema_id: UUID,
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Schema with its active fields + a ``referenced_by`` count (directories/syncs)."""
    return _schema_service(claims, db).get_schema_detail(schema_id)


@router.get("/{schema_id}/sample")
def download_schema_sample(
    schema_id: UUID,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    """Download a schema-shaped sample import file (CSV or ``.xlsx``), generated
    server-side from the schema's fields."""
    filename, media_type, content = _schema_service(claims, db).build_sample_file(
        schema_id, format
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{schema_id}")
def update_schema(
    schema_id: UUID,
    body: UpdateSchemaRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _schema_service(claims, db).update_schema(
        schema_id, **body.model_dump(exclude_unset=True)
    )


@router.delete("/{schema_id}")
def delete_schema(
    schema_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _schema_service(claims, db).delete_schema(schema_id)


# ---------------------------------------------------------------------------
# Field create (nested under a schema)
# ---------------------------------------------------------------------------

@router.post("/{schema_id}/fields", status_code=status.HTTP_201_CREATED)
def create_schema_field(
    schema_id: UUID,
    body: CreateSchemaFieldRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    field = _schema_service(claims, db).create_schema_field(
        schema_id,
        field_name=body.field_name,
        type=body.type,
        label=body.label,
        format=body.format,
        is_mandatory=body.is_mandatory,
        validators=body.validators,
        options=body.options,
        source_key=body.source_key,
        display_order=body.display_order,
        field_metadata=body.field_metadata,
    )
    return field.to_dict()


# ---------------------------------------------------------------------------
# Field update / delete (by field id)
# ---------------------------------------------------------------------------

@field_router.patch("/{field_id}")
def update_schema_field(
    field_id: UUID,
    body: UpdateSchemaFieldRequest,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    field = _schema_service(claims, db).update_schema_field(
        field_id, **body.model_dump(exclude_unset=True)
    )
    return field.to_dict()


@field_router.delete("/{field_id}")
def delete_schema_field(
    field_id: UUID,
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _schema_service(claims, db).delete_schema_field(field_id)
