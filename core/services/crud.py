"""
Standalone CRUD helpers for use in controllers.

These complement BaseService — they accept a db session directly
and don't require service class instantiation.
"""

from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def create_record(db: Session, model: Type, organization_id: UUID = None, **kwargs) -> Any:
    """Create a new record, commit, refresh, and return it."""
    values = dict(kwargs)
    if organization_id and hasattr(model, "organization_id"):
        values["organization_id"] = organization_id
    record = model(**values)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, record: Any, data: Dict[str, Any]) -> Any:
    """Update allowed fields on an existing record, commit, and return it."""
    for key, value in data.items():
        if hasattr(record, key):
            setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def get_or_404(db: Session, model: Type, record_id: UUID, organization_id: UUID = None) -> Any:
    """Fetch a single record by ID (and org_id if applicable), or raise 404."""
    query = db.query(model).filter(model.id == record_id)
    if organization_id and hasattr(model, "organization_id"):
        query = query.filter(model.organization_id == organization_id)
    record = query.first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found",
        )
    return record


def list_records(
    db: Session,
    model: Type,
    organization_id: UUID,
    page: int = 1,
    page_size: int = 20,
    filters: Optional[List] = None,
    order_by=None,
    options: Optional[List] = None,
) -> Tuple[List, int]:
    """
    Paginated list with filters. Returns (items, total).

    - Automatically filters by organization_id if model has that column.
    - `filters` is a list of SQLAlchemy filter expressions.
    - `order_by` is a SQLAlchemy order_by clause.
    - `options` is a list of SQLAlchemy loader options (e.g. joinedload).
    """
    query = db.query(model)
    if hasattr(model, "organization_id") and organization_id:
        query = query.filter(model.organization_id == organization_id)
    if hasattr(model, "deleted_at"):
        query = query.filter(model.deleted_at.is_(None))
    if filters:
        for f in filters:
            query = query.filter(f)
    total = query.count()
    if order_by is not None:
        query = query.order_by(order_by)
    if options:
        query = query.options(*options)
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return items, total
