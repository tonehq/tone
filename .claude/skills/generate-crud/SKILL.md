# CRUD Operations — Code Generation Guide

## When to Use

Apply these rules whenever creating, modifying, or extending CRUD operations (Create, Read, Update, Delete) for any model in this project. This covers: FastAPI services, API routes, and router registration.

## CRITICAL RULES

### 1. Always create EE controller first, then Core
This project has two editions: **Enterprise (EE)** and **Core**. When creating new API routes:
1. **First** create the controller in `ee/api/v1/{model_name}s.py` — uses `EEJWTClaims` and `require_ee_org_member` from `ee.middleware.auth`
2. **Then** create the controller in `core/api/v1/{model_name}s.py` — uses `JWTClaims` and `require_org_member` from `core.middleware.auth`
3. Both controllers share the **same service** from `core/services/` — never duplicate service logic
4. Register the EE router in `main_ee.py` and the Core router in `main.py`

The only difference between EE and Core controllers is the **auth middleware**. The route logic, request/response schemas, and service calls are identical.

### 2. No separate Create and Update APIs — use Upsert only
**Never** create individual `create` and `update` endpoints. Always use a **single upsert endpoint** that handles both:
- If the request body contains `id` → update the existing record
- If no `id` → create a new record
- The upsert endpoint should be `POST /upsert` or `POST /upsert_{model}`
- Do **not** create `POST /create_{model}` or `PUT /update_{model}` endpoints

---

## 1. Service Layer (`core/services/`)

### Base Class
- Create a service file named as `{model_name}_service.py` in `core/services/`.
- Create controller files named as `{model_name}s.py` in **both** `ee/api/v1/` (first) and `core/api/v1/` (second).
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

### Get All with Pagination (REQUIRED for collection endpoints)
- **Every "get all" / "list" endpoint MUST include pagination.** Never return unbounded result sets.
- Use `page_no` (1-based, default 1) and `page_size` (default 10, max 100) parameters.
- Always return a paginated response wrapper: `{ data, total, page_no, page_size }`.
- Optional filter parameters default to `None`. Conditionally chain `.filter()` calls.
- Always order by `Model.id` for deterministic results.

```python
    def get_all_my_models(
        self,
        page_no: int = 1,
        page_size: int = 10,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = self.query(MyModel)

        if status_filter:
            query = query.filter(MyModel.status == status_filter)

        total = query.count()

        offset = (page_no - 1) * page_size
        rows = query.order_by(MyModel.id).offset(offset).limit(page_size).all()

        return {
            "data": [self._response_item(row) for row in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }
```

**Corresponding route handler must accept and validate pagination params:**
```python
@router.post("/list")
def get_all_my_models(
    data: Dict[str, Any] = Body(default_factory=dict),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    page_no = int(data.get("page_no", 1) or 1)
    page_size = int(data.get("page_size", 10) or 10)
    if page_no < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_no must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size must be between 1 and 100")

    return MyModelService(db, user_id=claims.user_id).get_all_my_models(
        page_no=page_no,
        page_size=page_size,
    )
```

**Note:** Use `POST /list` (not `GET`) for paginated collection endpoints so pagination and filter params can be sent in the request body.

**Joined query variant** (when related data is needed):
```python
    def get_all_my_models(
        self,
        page_no: int = 1,
        page_size: int = 10,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = (
            self.db.query(MyModel, RelatedModel)
            .outerjoin(RelatedModel, RelatedModel.my_model_id == MyModel.id)
        )

        if category:
            query = query.filter(MyModel.category == category)

        total = query.count()

        offset = (page_no - 1) * page_size
        rows = query.order_by(MyModel.id).offset(offset).limit(page_size).all()

        return {
            "data": [self._response_item(model, related) for model, related in rows],
            "total": total,
            "page_no": page_no,
            "page_size": page_size,
        }
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

**IMPORTANT:** Only 3 endpoints per model — upsert, get all, get one, and delete. Never create separate create and update endpoints.

| Operation | HTTP Method | Path | Auth Dependency |
|-----------|------------|------|-----------------|
| Upsert (create + update) | `POST` | `/upsert` or `/upsert_{model}` | `require_org_member` or `require_admin_or_owner` |
| List all (paginated) | `POST` | `/list` | `require_org_member` |
| Get one | `GET` | `/get` | `get_jwt_claims` or `require_org_member` |
| Delete | `DELETE` | `/delete` | `require_admin_or_owner` |

**Note:** List endpoints use `POST` (not `GET`) so pagination params (`page_no`, `page_size`) and filters can be sent in the request body.

### EE Controller Template (`ee/api/v1/{model_name}s.py`) — Create this FIRST
```python
from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any

from core.database.session import get_db
from core.services.my_model_service import MyModelService
from ee.middleware.auth import require_ee_org_member, EEJWTClaims

router = APIRouter()


def _get_service(claims: EEJWTClaims, db: Session) -> MyModelService:
    from uuid import UUID
    return MyModelService(db, user_id=claims.user_id, org_id=UUID(claims.org_id))


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_my_model(
    data: Dict[str, Any] = Body(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).upsert_my_model(data, created_by=claims.user_id)

@router.post("/list")
def get_all_my_models(
    data: Dict[str, Any] = Body(default_factory=dict),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    page_no = int(data.get("page_no", 1) or 1)
    page_size = int(data.get("page_size", 10) or 10)
    if page_no < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_no must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size must be between 1 and 100")
    return _get_service(claims, db).get_all_my_models(page_no=page_no, page_size=page_size)

@router.get("/get")
def get_my_model(
    my_model_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_my_model(my_model_id)

@router.delete("/delete")
def delete_my_model(
    my_model_id: int = Query(...),
    claims: EEJWTClaims = Depends(require_ee_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_my_model(my_model_id)
```

### Core Controller Template (`core/api/v1/{model_name}s.py`) — Create this SECOND
```python
from fastapi import APIRouter, Depends, Body, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from uuid import UUID

from core.database.session import get_db
from core.services.my_model_service import MyModelService
from core.middleware.auth import require_org_member, require_admin_or_owner, JWTClaims
from shared.config import settings

router = APIRouter()


def _get_service(claims: JWTClaims, db: Session) -> MyModelService:
    org_id = UUID(str(claims.org_id)) if claims.org_id else UUID(settings.DEFAULT_ORG_ID)
    return MyModelService(db, user_id=claims.user_id, org_id=org_id)


@router.post("/upsert", status_code=status.HTTP_200_OK)
def upsert_my_model(
    data: Dict[str, Any] = Body(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).upsert_my_model(data, created_by=claims.user_id)

@router.post("/list")
def get_all_my_models(
    data: Dict[str, Any] = Body(default_factory=dict),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    page_no = int(data.get("page_no", 1) or 1)
    page_size = int(data.get("page_size", 10) or 10)
    if page_no < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_no must be >= 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size must be between 1 and 100")
    return _get_service(claims, db).get_all_my_models(page_no=page_no, page_size=page_size)

@router.get("/get")
def get_my_model(
    my_model_id: int = Query(...),
    claims: JWTClaims = Depends(require_org_member),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).get_my_model(my_model_id)

@router.delete("/delete")
def delete_my_model(
    my_model_id: int = Query(...),
    claims: JWTClaims = Depends(require_admin_or_owner),
    db: Session = Depends(get_db),
):
    return _get_service(claims, db).delete_my_model(my_model_id)
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

## 3. Router Registration

After creating new routers, register them in **both** main files:

**`main_ee.py`** (register FIRST):
```python
from ee.api.v1 import my_models

api_v1.include_router(my_models.router, prefix="/my-model", tags=["my-model"])
```

**`main.py`** (register SECOND):
```python
from core.api.v1 import my_models

api_v1.include_router(my_models.router, prefix="/my-model", tags=["my-model"])
```

- Use **kebab-case** for URL prefixes.
- Use the **plural or singular model name** matching existing conventions.
- Both editions must use the **same prefix** and **same tags**.

---

## 4. File Checklist

When generating CRUD for a new model, create/modify these files **in this exact order**:

1. `core/services/{model_name}_service.py` — Implement the service with CRUD methods (shared by both editions).
2. `ee/api/v1/{model_name}s.py` — Define EE API routes (uses `EEJWTClaims`, `require_ee_org_member`).
3. `core/api/v1/{model_name}s.py` — Define Core API routes (uses `JWTClaims`, `require_org_member`).
4. `main_ee.py` — Register the EE router.
5. `main.py` — Register the Core router.

---

## 5. Rules to Always Follow

1. **Always create EE controller first, then Core** — `ee/api/v1/` before `core/api/v1/`. Both share the same service from `core/services/`.
2. **Never create separate create and update endpoints** — always use a single upsert endpoint. If `id` is in the body → update, otherwise → create.
3. **Always paginate collection endpoints** — Every "get all" / "list" endpoint must accept `page_no` and `page_size` and return `{ data, total, page_no, page_size }`. Never return unbounded result sets.
4. **Never bypass the service layer** — routes must not contain business logic or direct DB queries.
4. **Never return ORM objects** from services — always build and return plain dicts.
5. **Never expose sensitive data** (encrypted keys, password hashes) in API responses.
6. **Always use UUID for upsert conflict resolution** — not integer `id` or business keys.
7. **Always set `updated_at = int(time.time())`** when modifying records.
8. **Always rollback on IntegrityError** — call `self.db.rollback()` before raising HTTPException.
9. **Always validate required fields** in both the route handler and the service method.
10. **Always use dependency injection** for DB sessions and auth — never instantiate sessions manually in routes.
11. **Match existing naming conventions** — check similar models/services/routes before creating new ones.
12. **Keep routes thin** — input validation and service delegation only; no query logic.
