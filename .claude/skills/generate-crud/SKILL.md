# CRUD Operations — Code Generation Guide

## When to Use

Apply these rules whenever creating, modifying, or extending CRUD operations (Create, Read, Update, Delete) for any model in this project. This covers: FastAPI services, API routes, and router registration.

---

## 1. Service Layer (`core/services/`)

### Base Class
- Create a service file named as `{model_name}_service.py)` in core/services.
- Create a controller file named as `{model_name}s.py)` in core/api/v1.
- Every service **must** extend `BaseService` from `core.services.base`.
- Constructor signature: `def __init__(self, db: Session, user_id: Optional[int] = None)`.
- Access `self.db` for queries, `self.user_id` and `self.org_id` for context.

### Attribute Allowlists
- Define `CREATED_ATTRS` tuple — fields allowed during creation.
- Define `UPDATABLE_ATTRS` tuple — fields allowed during update.
- Filter incoming data through these allowlists before writing.

### CRUD Method Naming
| Operation | Method Name Pattern |
|-----------|-------------------|
| Create/Update | `upsert_{model_name}(self, data: Dict[str, Any], ...)` |
| Get one | `get_{model_name}(self, {model}_id: int)` |
| Get all | `get_all_{model_name}s(self, **filters)` |
| Delete | `delete_{model_name}(self, {model}_id: int)` |

### Service Imports Template
```python
# Standard library
import time
import uuid as uuid_lib
from typing import Dict, Any, List, Optional

# SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# FastAPI
from fastapi import HTTPException, status

# Logging
from loguru import logger

# Local
from core.services.base import BaseService
from core.models.my_model import MyModel
```

### Upsert Pattern (Preferred for Create + Update)
Use PostgreSQL `ON CONFLICT` via the `BaseService.upsert()` helper:
```python
class MyModelService(BaseService):
    CREATED_ATTRS = ("name", "description", "status", "meta_data")
    UPDATABLE_ATTRS = ("name", "description", "status", "meta_data")

    def upsert_my_model(self, data: Dict[str, Any], created_by: int) -> Dict[str, Any]:
        if not data.get("name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )

        # Determine UUID
        model_id = data.get("id")
        if model_id is not None:
            existing = self.db.query(MyModel).filter(MyModel.id == int(model_id)).first()
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MyModel not found")
            model_uuid = existing.uuid
        else:
            model_uuid = uuid_lib.uuid4()

        now = int(time.time())
        values = {
            "uuid": model_uuid,
            "name": data["name"],
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
        }

        # Add optional fields from allowlist
        for key in self.CREATED_ATTRS:
            if key in data and data[key] is not None:
                values[key] = data[key]

        try:
            self.upsert(
                model=MyModel,
                values=values,
                conflict_fields=["uuid"],
                update_fields=[f for f in self.UPDATABLE_ATTRS if f in values],
                extra_update={"updated_at": now},
            )
        except IntegrityError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A record with this name already exists",
            ) from e

        record = self.db.query(MyModel).filter(MyModel.uuid == model_uuid).first()
        return self._response_item(record)
```

### Get One Pattern
```python
    def get_my_model(self, my_model_id: int) -> Dict[str, Any]:
        record = self.db.query(MyModel).filter(MyModel.id == my_model_id).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MyModel not found",
            )

        return self._response_item(record)
```

### Get All with Filters Pattern
- Optional filter parameters default to `None`.
- Conditionally chain `.filter()` calls — only apply when the param is provided.
- Always filter `status == "active"` for soft-deletable models.
- Always order by `Model.id` for deterministic results.
- No pagination — return the full list.
```python
    def get_all_my_models(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(MyModel).filter(MyModel.status == "active")

        if status_filter:
            query = query.filter(MyModel.status == status_filter)

        rows = query.order_by(MyModel.id).all()
        return [self._response_item(row) for row in rows]
```

**Joined query variant** (when related data is needed):
```python
    def get_all_my_models(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (
            self.db.query(MyModel, RelatedModel)
            .outerjoin(RelatedModel, RelatedModel.my_model_id == MyModel.id)
        )

        if category:
            query = query.filter(MyModel.category == category)

        rows = query.order_by(MyModel.id).all()
        return [self._response_item(model, related) for model, related in rows]
```

### Delete Pattern
- Use **hard delete** with `self.db.delete()` + `self.db.commit()`.
- Return `{"message": "..."}` on success.
- Add business-rule guards before deleting if needed (e.g., `is_system` flag).
```python
    def delete_my_model(self, my_model_id: int) -> Dict[str, str]:
        record = self.db.query(MyModel).filter(MyModel.id == my_model_id).first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MyModel not found",
            )

        self.db.delete(record)
        self.db.commit()

        return {"message": "MyModel deleted successfully"}
```

### Response Item Builder Pattern
- Define a private `_response_item()` helper to convert ORM objects to dicts.
- Always include `id`, `uuid` (cast to `str`), `created_at`, `updated_at`.
- Cast `Decimal` to `float`, enums to `.value`, UUIDs to `str`.
- Use null-safe access: `x if x is not None else None`.
- Validate JSONB fields: `isinstance(x, dict) else {}`.
- Never expose encrypted or hashed fields.
```python
    def _response_item(self, record: MyModel) -> Dict[str, Any]:
        return {
            "id": record.id,
            "uuid": str(record.uuid),
            "name": record.name,
            "description": record.description,
            "status": record.status,
            "meta_data": record.meta_data if isinstance(record.meta_data, dict) else {},
            "created_by": record.created_by,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
```

### Transaction Handling
- Services **own** commit/rollback — never rely on auto-commit.
- `self.db.commit()` after every successful write (`upsert`, `add`, `delete`, `setattr` updates).
- `self.db.refresh(record)` after commit when you need the updated DB state.
- `self.db.rollback()` inside `except IntegrityError` before raising HTTPException.

### Logging
- Use `loguru`: `from loguru import logger`.
- Log warnings and errors for operational issues, not routine business logic.
```python
logger.warning("Failed to process %s: %s", record_id, e)
logger.error("Unexpected error in upsert: %s", e)
```

### Error Handling
- Raise `HTTPException` with appropriate status codes:
  - `400` — missing required fields, invalid input.
  - `404` — record not found.
  - `409` — uniqueness constraint violation.
- Catch `IntegrityError` and `self.db.rollback()` before raising.
- Delete success returns `{"message": "X deleted successfully"}`.

---

## 2. API Route Layer (`core/api/v1/`)

### Router Setup
```python
from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from core.database.session import get_db
from core.services.my_model_service import MyModelService
from core.middleware.auth import require_org_member, require_admin_or_owner, get_jwt_claims, JWTClaims

router = APIRouter()
```

### Route Patterns
| Operation | HTTP Method | Path | Auth Dependency |
|-----------|------------|------|-----------------|
| Upsert | `POST` | `/upsert` or `/upsert_{model}` | `require_org_member` or `require_admin_or_owner` |
| Get all | `GET` | `/list` or `/get_all_{model}s` | `get_jwt_claims` or `require_org_member` |
| Get one | `GET` | `/get` | `get_jwt_claims` or `require_org_member` |
| Delete | `DELETE` | `/delete` | `require_admin_or_owner` |

### Route Template
```python
@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_my_model(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    name = data.get("name")
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required",
        )
    return MyModelService(db, user_id=claims.user_id).upsert_my_model(
        data, created_by=claims.user_id
    )

@router.get("/list")
def get_all_my_models(
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return MyModelService(db, user_id=claims.user_id).get_all_my_models()

@router.get("/get")
def get_my_model(
    my_model_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return MyModelService(db, user_id=claims.user_id).get_my_model(my_model_id)

@router.delete("/delete")
def delete_my_model(
    my_model_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return MyModelService(db, user_id=claims.user_id).delete_my_model(my_model_id)
```

### Dependency Injection Rules
- **Always** inject `db: Session = Depends(get_db)` for database access.
- **Always** inject an auth dependency (`require_org_member`, `require_admin_or_owner`, or `get_jwt_claims`).
- Use `Body(...)` for POST/PUT request bodies (typed as `Dict[str, Any]`).
- Use `Query(...)` for GET/DELETE parameters.
- Validate required fields in the route handler **before** calling the service.

### Auth Dependency Selection
- `get_jwt_claims` — any authenticated user (read-only operations).
- `require_org_member` — authenticated user with org membership (standard CRUD).
- `require_admin_or_owner` — admin/owner role required (destructive or sensitive operations).

---

## 3. Router Registration (`main.py`)

After creating a new router, register it in `main.py` (and `main_ee.py` if applicable):

```python
from core.api.v1 import my_models

api_v1.include_router(my_models.router, prefix="/my-model", tags=["my-model"])
```

- Use **kebab-case** for URL prefixes.
- Use the **plural or singular model name** matching existing conventions.

---

## 4. File Checklist

When generating CRUD for a new model, create/modify these files **in order**:

1. `core/services/{model_name}_service.py` — Implement the service with CRUD methods.
2. `core/api/v1/{model_name}s.py` — Define API routes.
3. `main.py` (and `main_ee.py`) — Register the new router.

---

## 5. Rules to Always Follow

1. **Never bypass the service layer** — routes must not contain business logic or direct DB queries.
2. **Never return ORM objects** from services — always build and return plain dicts.
3. **Never expose sensitive data** (encrypted keys, password hashes) in API responses.
4. **Always use UUID for upsert conflict resolution** — not integer `id` or business keys.
5. **Always set `updated_at = int(time.time())`** when modifying records.
6. **Always rollback on IntegrityError** — call `self.db.rollback()` before raising HTTPException.
7. **Always validate required fields** in both the route handler and the service method.
8. **Always use dependency injection** for DB sessions and auth — never instantiate sessions manually in routes.
9. **Match existing naming conventions** — check similar models/services/routes before creating new ones.
10. **Keep routes thin** — input validation and service delegation only; no query logic.
