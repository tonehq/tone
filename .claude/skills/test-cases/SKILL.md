---
name: test-cases
description: >
  Generate and maintain pytest test cases for FastAPI endpoints by reading the APIs.md documentation
  and tracing actual controller/service code. Creates one test file per controller with comprehensive
  coverage (success, failure, validation, auth, edge cases). Use this skill when the user asks to
  generate tests, create test cases, write API tests, add pytest coverage, or mentions "test my APIs".
  Also triggers on "generate tests", "write test cases", "add test coverage", or "pytest for my endpoints".
---

# Test Case Generator

Generate comprehensive pytest test cases for FastAPI API endpoints. Uses `APIs.md` (produced by the
`generate-api-code-documentation` skill) as the primary reference for endpoint details, and traces
actual source code for implementation-specific edge cases.

---

## Prerequisites

- **APIs.md must exist.** This skill depends on the output of the `generate-api-code-documentation` skill.
  If `APIs.md` does not exist in the project root, stop and tell the user:
  "APIs.md not found. Please run the `generate-api-code-documentation` skill first to generate it."
- FastAPI project with the structure described in CLAUDE.md (core/api/v1/, core/services/, core/models/)
- pytest installed (`pip install pytest pytest-asyncio httpx`)

---

## Inputs

The user provides:
1. **Scope** (optional) — A specific controller file or directory (e.g., `core/api/v1/agents.py`).
   If omitted, generate tests for ALL controllers found in `APIs.md`.
2. **Output directory** (optional) — Where to write test files (default: `test-cases/`).

---

## Step 0: Discover Project Context

```
1. FIND the project root (look for pyproject.toml, .git/, main.py)

2. CHECK for APIs.md:
   - Read {project_root}/APIs.md
   - If it doesn't exist → STOP, ask user to run generate-api-code-documentation first

3. READ main.py to understand:
   - How routers are mounted and their URL prefixes
   - The app factory / lifespan setup
   - IMPORTANT: main.py exports BOTH `app` (the outer FastAPI) and `api_v1` (the sub-app
     where routers are mounted). Dependency overrides MUST be applied to `api_v1`, not `app`.
   - Whether EE (Enterprise) or Core routes are loaded — this is determined at startup
     by `is_ee_enabled()` from `core.internal.capabilities`
   - If EE is enabled, routers come from `ee/api/v1/`; otherwise from `core/api/v1/`

4. READ core/middleware/auth.py to understand:
   - Auth dependency functions: get_jwt_claims, require_org_member, require_admin_or_owner,
     require_owner, get_optional_jwt_claims
   - JWTClaims model fields: user_id (int), org_id (Optional[Union[str, int]]),
     role (Optional[str]), email (str), exp (int), iat (int)
   - The `security` object (HTTPBearer instance) — must be overridden in tests
   - How TenantContext is set via set_tenant_context() from core.context

5. IF ee/ directory exists, also READ ee/middleware/auth.py for:
   - EE auth dependencies: get_ee_jwt_claims, get_ee_current_user, require_ee_org_member,
     require_ee_admin_or_owner, require_ee_owner, get_optional_ee_jwt_claims
   - EEJWTClaims is aliased to JWTClaims (same model, just re-exported)
   - get_ee_current_user accepts an optional `tenant_id` header (Header alias) — if a
     valid UUID is provided, it overrides claims.org_id and updates TenantContext. This
     enables multi-tenant org switching in EE.
   - require_ee_org_member validates that org_id is a valid UUID (stricter than core)
   - These must also be overridden in test fixtures when EE is enabled
   - IMPORTANT: EE controllers pass `org_id=UUID(claims.org_id)` explicitly to services,
     while core controllers rely on TenantContext fallback. Tests must account for this.

6. READ core/services/base.py to understand:
   - BaseService.__init__(db, user_id, org_id) — services receive db session, user_id, org_id
   - BaseService.org_id property — falls back to get_current_org_id() from TenantContext
   - BaseService.query(model) — auto-filters by organization_id for OrgScopedModel subclasses
   - BaseService.upsert() — PostgreSQL insert-on-conflict, auto-injects organization_id

7. READ core/models/base.py to understand:
   - TimestampModel: id (BigInteger PK), created_at, updated_at (BigInteger unix timestamps)
   - OrgScopedModel: extends TimestampModel, adds organization_id (UUID FK to organizations)
   - All org-scoped models inherit from OrgScopedModel

8. CHECK for existing test infrastructure:
   - Does test-cases/ directory exist?
   - Does test-cases/conftest.py exist?
   - If not, they will be created in Step 1

9. CHECK for postman/ or postman_collection/ directory:
   - If Postman collections exist (from the postman skill — see .claude/skills/postman/SKILL.md),
     cross-reference them for request body examples and endpoint paths.
   - Postman collections contain realistic sample payloads that can be reused as test fixtures.
```

---

## Step 1: Set Up Test Infrastructure (First Run Only)

Tests are split into **two directories** — one for Core edition, one for EE edition — each with its own
conftest that overrides the correct auth dependencies. Shared helpers live in the root `test-cases/conftest.py`.

### Directory Structure

```
test-cases/
├── __init__.py
├── conftest.py                           # Shared fixtures (mock_db, make_claims, auth_headers)
├── core/
│   ├── __init__.py
│   ├── conftest.py                       # Core auth overrides (require_org_member, etc.)
│   ├── test_agents.py                    # Patches core.api.v1.agents
│   ├── test_agent_configs.py
│   ├── test_agent_channel_phone_numbers.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_organizations.py
│   ├── test_channels.py
│   ├── test_channel_phone_numbers.py
│   ├── test_call_logs.py
│   ├── test_api_keys.py
│   ├── test_services.py
│   ├── test_service_providers.py
│   ├── test_models.py
│   ├── test_voices.py
│   ├── test_generated_api_keys.py
│   └── test_telephony.py                # WebSocket, no auth
├── ee/
│   ├── __init__.py
│   ├── conftest.py                       # EE auth overrides (require_ee_org_member, etc.)
│   ├── test_agents.py                    # Patches ee.api.v1.agents
│   ├── test_agent_configs.py
│   ├── test_agent_channel_phone_numbers.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_organizations.py            # Includes EE-only endpoints (tenants, access requests)
│   ├── test_channels.py
│   ├── test_channel_phone_numbers.py
│   ├── test_call_logs.py
│   ├── test_api_keys.py
│   ├── test_services.py
│   ├── test_service_providers.py
│   ├── test_models.py
│   ├── test_voices.py
│   ├── test_generated_api_keys.py
│   └── test_telephony.py                # WebSocket, same as core (re-exported)
```

### Root conftest: `test-cases/conftest.py`

Shared fixtures used by both Core and EE tests:

```python
"""Shared fixtures for all API test cases (Core and EE)."""

import pytest
import time
from unittest.mock import MagicMock
from fastapi.security import HTTPAuthorizationCredentials

from core.middleware.auth import JWTClaims


def make_claims(
    user_id: int = 1,
    org_id: str = "550e8400-e29b-41d4-a716-446655440000",
    role: str = "member",
    email: str = "test@example.com",
) -> JWTClaims:
    """Build a JWTClaims instance with sensible defaults."""
    now = int(time.time())
    return JWTClaims(
        user_id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        iat=now,
        exp=now + 3600,
    )


# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    db.count.return_value = 0
    return db


@pytest.fixture
def member_claims():
    """JWT claims for a regular org member."""
    return make_claims(role="member")


@pytest.fixture
def admin_claims():
    """JWT claims for an admin user."""
    return make_claims(role="admin")


@pytest.fixture
def owner_claims():
    """JWT claims for an owner user."""
    return make_claims(role="owner")


@pytest.fixture
def auth_headers():
    """Bearer token headers for authenticated requests."""
    return {"Authorization": "Bearer test-token"}


def _fake_security():
    """Bypass HTTPBearer so tests don't need an Authorization header."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")


def _override_auth(claims: JWTClaims):
    """Return a dependency override function that returns *claims*."""
    def _override():
        return claims
    return _override
```

### Core conftest: `test-cases/core/conftest.py`

Overrides **Core** auth dependencies only:

```python
"""Core edition test fixtures — overrides core auth dependencies."""

import pytest
from fastapi.testclient import TestClient

from main import app, api_v1
from core.middleware.auth import get_jwt_claims, require_org_member, require_admin_or_owner, require_owner, security
from core.database.session import get_db

# Import shared helpers from parent conftest
from conftest import _fake_security, _override_auth


@pytest.fixture
def client_as_member(mock_db, member_claims):
    """TestClient authenticated as a regular org member (Core auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(member_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    """TestClient authenticated as an admin (Core auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(admin_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(mock_db, owner_claims):
    """TestClient authenticated as an owner (Core auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_jwt_claims] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_org_member] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_admin_or_owner] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_owner] = _override_auth(owner_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    """TestClient with DB mocked but NO auth override — auth should reject."""
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides.pop(get_jwt_claims, None)
    api_v1.dependency_overrides.pop(require_org_member, None)
    api_v1.dependency_overrides.pop(require_admin_or_owner, None)
    api_v1.dependency_overrides.pop(require_owner, None)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()
```

### EE conftest: `test-cases/ee/conftest.py`

Overrides **EE** auth dependencies:

```python
"""EE edition test fixtures — overrides EE auth dependencies."""

import pytest
from fastapi.testclient import TestClient

from main import app, api_v1
from ee.middleware.auth import (
    get_ee_jwt_claims,
    get_ee_current_user,
    require_ee_org_member,
    require_ee_admin_or_owner,
    require_ee_owner,
)
from core.middleware.auth import security
from core.database.session import get_db

# Import shared helpers from parent conftest
from conftest import _fake_security, _override_auth


@pytest.fixture
def client_as_member(mock_db, member_claims):
    """TestClient authenticated as a regular org member (EE auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(member_claims)
    api_v1.dependency_overrides[get_ee_current_user] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_ee_org_member] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(member_claims)
    api_v1.dependency_overrides[require_ee_owner] = _override_auth(member_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_admin(mock_db, admin_claims):
    """TestClient authenticated as an admin (EE auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(admin_claims)
    api_v1.dependency_overrides[get_ee_current_user] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_org_member] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(admin_claims)
    api_v1.dependency_overrides[require_ee_owner] = _override_auth(admin_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_as_owner(mock_db, owner_claims):
    """TestClient authenticated as an owner (EE auth)."""
    api_v1.dependency_overrides[security] = _fake_security
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides[get_ee_jwt_claims] = _override_auth(owner_claims)
    api_v1.dependency_overrides[get_ee_current_user] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_org_member] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_admin_or_owner] = _override_auth(owner_claims)
    api_v1.dependency_overrides[require_ee_owner] = _override_auth(owner_claims)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def client_unauthenticated(mock_db):
    """TestClient with DB mocked but NO auth override — EE auth should reject."""
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    api_v1.dependency_overrides.pop(get_ee_jwt_claims, None)
    api_v1.dependency_overrides.pop(get_ee_current_user, None)
    api_v1.dependency_overrides.pop(require_ee_org_member, None)
    api_v1.dependency_overrides.pop(require_ee_admin_or_owner, None)
    api_v1.dependency_overrides.pop(require_ee_owner, None)

    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()
```

Adapt each conftest based on what you discover in Step 0 about auth patterns and DB dependencies.

Also create `test-cases/__init__.py`, `test-cases/core/__init__.py`, and `test-cases/ee/__init__.py` if they don't exist.

---

## Step 2: Parse APIs.md for Endpoint Inventory

Read `APIs.md` and extract for EVERY documented route:

| Field | What to Extract |
|---|---|
| **HTTP method** | GET, POST, PUT, PATCH, DELETE |
| **Full path** | e.g., `/api/v1/agent/get_agent` |
| **Controller file** | e.g., `core/api/v1/agents.py` (and `ee/api/v1/agents.py` if EE) |
| **Function name** | e.g., `get_agent()` |
| **Auth requirements** | Which auth dependency is used (require_org_member, require_admin_or_owner, get_jwt_claims, require_owner, or none for public) |
| **Request body fields** | Field name, type, required, default |
| **Path/query params** | Parameter names and types |
| **Response status** | Success status code (200, 201, 204) |
| **Error responses** | All documented error codes and conditions |
| **Models used** | SQLAlchemy models involved (note if OrgScopedModel or TimestampModel) |
| **Service methods** | Which service methods are called |

---

## Step 3: Trace Source Code for Each Endpoint

For each endpoint extracted from APIs.md, READ the actual source code for **BOTH** editions to discover:

```
1. READ BOTH the core and ee router modules for each controller:
   - Core: core/api/v1/{controller}.py
   - EE: ee/api/v1/{controller}.py
   - IMPORTANT: When patching services, use the module path where the service is IMPORTED.
     For EE tests: patch("ee.api.v1.agents.AgentService")
     For Core tests: patch("core.api.v1.agents.AgentService")

2. READ the controller function
   - Identify exact parameter names and types
   - Identify dependency injection (Depends(...)) — especially auth and db
   - Identify what service method(s) are called
   - Identify any inline validation or early returns
   - Note: Most controllers accept Dict[str, Any] request bodies (not strict Pydantic schemas)
     and do validation in the service layer

3. READ the service method in core/services/{service}.py
   - Identify all DB queries (what can return None, empty list, raise exceptions)
   - Note if the service extends BaseService — if so, queries auto-filter by organization_id
   - Identify business logic branches (if/else, validation checks)
   - Identify all raised HTTPException or custom exceptions with their status codes
   - Identify side effects (other services called, external API calls)
   - Note how org_id is resolved (explicit param vs TenantContext fallback)

4. READ the model in core/models/{model}.py
   - Identify if it extends OrgScopedModel (has organization_id) or TimestampModel
   - Identify required fields, nullable fields, unique constraints
   - Identify foreign key relationships (for testing cascades/dependencies)
   - Identify JSONB/JSON columns that need special test data
   - Note enum fields (AgentType, ChannelType, Role, etc.) from core/models/enums.py

5. READ the schema (if exists) in core/schemas/
   - Note: Most endpoints use Dict[str, Any] — only auth and user have Pydantic schemas
   - For endpoints with schemas, identify validation rules
```

---

## Step 4: Generate Test Cases for Each Endpoint

For EVERY endpoint, generate test cases in these categories:

### Category 1: Success Cases
- Happy path with all required fields
- Happy path with optional fields included
- Happy path with minimum valid data

### Category 2: Authentication & Authorization
- Request without auth token → 401/403 (use `client_unauthenticated` fixture)
- Request with wrong role — e.g., member accessing admin-only endpoint
- Request for resource in different org (if multi-tenant / OrgScopedModel) → 403/404
- **Auth dependency mapping:**
  - `require_org_member` / `require_ee_org_member` → any authenticated user passes, use `client_as_member`
  - `require_admin_or_owner` / `require_ee_admin_or_owner` → use `client_as_admin` for success tests
  - `require_owner` / `require_ee_owner` → only owner role passes, use `client_as_owner` for success tests
  - `get_jwt_claims` / `get_ee_jwt_claims` → basic auth, no role check
  - No auth dependency → public endpoint, skip auth tests

### Category 3: Validation Errors
- Missing required body fields → 400 (service-level validation) or 422 (Pydantic)
- Empty string for required fields → 400
- Invalid field types → 422
- Invalid enum values (e.g., invalid ChannelType, AgentType) → 400/422
- Invalid query parameter types → 422
- Missing required query parameters → 422

### Category 4: Not Found / Conflict
- Resource not found (GET/DELETE with non-existent ID) → 404
- Duplicate creation (if service checks uniqueness) → 409
- Foreign key reference doesn't exist → 400/404

### Category 5: Edge Cases (discovered from code tracing)
- Empty string vs null for optional fields
- Empty list responses
- Service-layer exceptions (mock side_effect with HTTPException)
- JSONB field handling (empty dict, nested objects)
- Enum boundary values (valid and invalid enum members)

### Test Function Naming Convention

```python
# Pattern: test_{action}_{scenario}
# Grouped in classes per endpoint
class TestGetAllAgents:
    def test_get_all_agents_success(self, client_as_member):
    def test_get_all_agents_empty(self, client_as_member):
    def test_get_all_agents_unauthenticated(self, client_unauthenticated):
    def test_get_all_agents_invalid_query_param(self, client_as_member):
```

---

## Step 5: Write Test Files

### File Structure

One test file per controller per edition, in `test-cases/core/` and `test-cases/ee/`:

```
test-cases/
├── __init__.py
├── conftest.py                           # Shared fixtures (mock_db, make_claims, helpers)
├── core/
│   ├── __init__.py
│   ├── conftest.py                       # Core auth overrides
│   ├── test_agents.py                    # Patches core.api.v1.agents
│   ├── test_agent_configs.py
│   ├── test_agent_channel_phone_numbers.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_organizations.py             # Core-specific logic (member limits, capability checks)
│   ├── test_channels.py
│   ├── test_channel_phone_numbers.py
│   ├── test_call_logs.py
│   ├── test_api_keys.py
│   ├── test_services.py
│   ├── test_service_providers.py
│   ├── test_models.py
│   ├── test_voices.py
│   ├── test_generated_api_keys.py
│   └── test_telephony.py                # WebSocket, no auth
├── ee/
│   ├── __init__.py
│   ├── conftest.py                       # EE auth overrides
│   ├── test_agents.py                    # Patches ee.api.v1.agents
│   ├── test_agent_configs.py
│   ├── test_agent_channel_phone_numbers.py
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_organizations.py             # EE-specific endpoints (tenants, access requests)
│   ├── test_channels.py
│   ├── test_channel_phone_numbers.py
│   ├── test_call_logs.py
│   ├── test_api_keys.py
│   ├── test_services.py
│   ├── test_service_providers.py
│   ├── test_models.py
│   ├── test_voices.py
│   ├── test_generated_api_keys.py
│   └── test_telephony.py                # WebSocket (re-exports core, same tests)
```

### Test File Template

Each test file follows this structure. The **only difference** between core/ and ee/ versions is the
patch path and service instantiation assertions:

**Core test file** (`test-cases/core/test_agents.py`):

```python
"""Tests for Agents API endpoints (Core edition).

Source: core/api/v1/agents.py
Generated from APIs.md by test-cases skill.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── Fixtures specific to this controller ───

@pytest.fixture
def sample_agent_data():
    """Valid agent creation payload."""
    return {
        "name": "Test Agent",
        "description": "A test voice agent",
    }


@pytest.fixture
def mock_agent_response():
    """Mock response from service layer."""
    return {
        "id": 1,
        "name": "Test Agent",
        "description": "A test voice agent",
        "agent_config": {},
        "service_providers": {},
    }


# ─── GET /api/v1/agent/get_all_agents — Get All Agents ───

class TestGetAllAgents:
    """Tests for GET /api/v1/agent/get_all_agents"""

    @patch("core.api.v1.agents.AgentService")  # Core: patch core module
    def test_get_all_agents_success(self, mock_service_cls, client_as_member, mock_agent_response):
        mock_service_cls.return_value.get_all_agents.return_value = [mock_agent_response]
        response = client_as_member.get("/api/v1/agent/get_all_agents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        # Core: service instantiated WITHOUT org_id
        mock_service_cls.assert_called_once_with(mock_service_cls.call_args[0][0])

    def test_get_all_agents_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent/get_all_agents")
        assert response.status_code in (401, 403)
```

**EE test file** (`test-cases/ee/test_agents.py`):

```python
"""Tests for Agents API endpoints (EE edition).

Source: ee/api/v1/agents.py
Generated from APIs.md by test-cases skill.
"""

import pytest
from uuid import UUID
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException

EXPECTED_ORG_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


# ─── Fixtures specific to this controller ───

@pytest.fixture
def sample_agent_data():
    """Valid agent creation payload."""
    return {
        "name": "Test Agent",
        "description": "A test voice agent",
    }


# ─── GET /api/v1/agent/get_all_agents — Get All Agents ───

class TestGetAllAgents:
    """Tests for GET /api/v1/agent/get_all_agents"""

    @patch("ee.api.v1.agents.AgentService")  # EE: patch ee module
    def test_get_all_agents_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.get_all_agents.return_value = [{"id": 1}]
        response = client_as_member.get("/api/v1/agent/get_all_agents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        # EE: service instantiated WITH org_id
        mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)

    def test_get_all_agents_unauthenticated(self, client_unauthenticated):
        response = client_unauthenticated.get("/api/v1/agent/get_all_agents")
        assert response.status_code in (401, 403)
```

**Key differences between Core and EE test files:**

| Aspect | Core tests | EE tests |
|---|---|---|
| Patch path | `@patch("core.api.v1.{controller}.ServiceClass")` | `@patch("ee.api.v1.{controller}.ServiceClass")` |
| Service assertion | `mock_service_cls.assert_called_once_with(ANY)` | `mock_service_cls.assert_called_once_with(ANY, org_id=EXPECTED_ORG_ID)` |
| Auth fixtures | From `test-cases/core/conftest.py` (core auth) | From `test-cases/ee/conftest.py` (EE auth) |
| Extra endpoints | Core organizations: member limits, capability checks | EE organizations: tenants, access requests |
| Docstring Source | `Source: core/api/v1/{controller}.py` | `Source: ee/api/v1/{controller}.py` |

### Mock Strategy

```
1. OVERRIDE dependencies on `api_v1` (the sub-app), NOT on `app` (the outer app)
   - api_v1.dependency_overrides[get_db] = lambda: mock_db
   - api_v1.dependency_overrides[security] = _fake_security
   - This is handled by the edition-specific conftest client fixtures

2. PATCH service classes using unittest.mock.patch
   - Patch at the module where the service is IMPORTED, not where it's defined
   - Core tests: ALWAYS patch "core.api.v1.{controller}.ServiceClass"
   - EE tests: ALWAYS patch "ee.api.v1.{controller}.ServiceClass"
   - This is deterministic — no runtime EE detection needed

3. OVERRIDE auth dependencies in edition-specific conftest fixtures
   - Core conftest overrides: security, get_jwt_claims, require_org_member,
     require_admin_or_owner, require_owner
   - EE conftest overrides: security, get_ee_jwt_claims, get_ee_current_user,
     require_ee_org_member, require_ee_admin_or_owner, require_ee_owner
   - For unauthenticated tests: use client_unauthenticated which does NOT override auth

4. ASSERT service instantiation patterns
   - Core: services are called as ServiceClass(db) — no org_id parameter
   - EE: services are called as ServiceClass(db, org_id=UUID(claims.org_id))
   - Use EXPECTED_ORG_ID constant in EE tests to verify org_id is passed

5. DO NOT mock Pydantic validation — let FastAPI's real validation run for query params
   - This catches actual 422 errors from invalid query parameters
   - Note: most request bodies use Dict[str, Any], so body validation happens in the
     service layer and returns 400, not 422

6. USE role-appropriate client fixtures:
   - client_as_member for endpoints using require_org_member / require_ee_org_member
   - client_as_admin for endpoints using require_admin_or_owner / require_ee_admin_or_owner
   - client_as_owner for endpoints using require_owner / require_ee_owner
   - client_unauthenticated for auth failure tests

7. HANDLE telephony specially:
   - telephony is a WebSocket endpoint at /ws, NOT under /api/v1/ — use TestClient.websocket_connect("/ws")
     and test the WebSocket handshake, not HTTP methods
   - EE telephony re-exports the core router, so tests are identical in both editions
```

---

## Step 6: Write the Test Files

```
1. For each controller, WRITE TWO test files — one in core/, one in ee/:
   - test-cases/core/test_{controller}.py — patches core.api.v1.{controller}
   - test-cases/ee/test_{controller}.py — patches ee.api.v1.{controller}

2. Key differences per edition:
   - Core tests: service instantiated as ServiceClass(db) — no org_id
   - EE tests: service instantiated as ServiceClass(db, org_id=UUID(claims.org_id))
   - EE organizations: include extra endpoints (tenants, access requests, members)
   - Core organizations: include member limit and capability check tests
   - Telephony: identical in both (EE re-exports core router)

3. After writing each file:
   - Verify the file was created by reading it back
   - Confirm all endpoints from APIs.md are covered in BOTH editions

4. Update test-cases/.last_run with current timestamp and git SHA

5. REPORT to user:
   Test files generated:
   Core edition (test-cases/core/):
   - test_agents.py — 24 tests (4 endpoints × ~6 cases each)
   - test_auth.py — 18 tests (7 endpoints × ~3 cases each)
   - ...
   EE edition (test-cases/ee/):
   - test_agents.py — 24 tests (4 endpoints × ~6 cases each)
   - test_organizations.py — 30 tests (includes EE-only endpoints)
   - ...
   Total: {N} test cases across {M} files ({X} core + {Y} ee)
```

---

## Subsequent Run Workflow (Incremental Update)

On subsequent runs, use the **`find-impacted-apis` skill** (`.claude/skills/find-impacted-apis/`)
to detect which endpoints, services, and models have changed. Do NOT implement custom change
detection logic — delegate entirely to that skill.

### Step A: Run find-impacted-apis to Detect Changes

Use the `analyze_diff.py` script from `.claude/skills/find-impacted-apis/`:

```bash
python .claude/skills/find-impacted-apis/analyze_diff.py \
  --project-path . \
  --auto \
  --output test-cases/
```

This produces two files:
- `test-cases/impacted-apis-report.json` — structured data for programmatic use
- `test-cases/impacted-apis-report.md` — human-readable summary

If this is the first run of `find-impacted-apis` (no state file at
`~/.claude-skills/find-impacted-apis/last_run.json`), you can either:
- Ask the user for a commit range, OR
- Fall back to a full run (treat all endpoints as "added" — same as first-run behavior)

**If the report shows zero impacted endpoints, services, and models → report
"No API changes detected since last run" and stop.**

### Step B: Parse the Impact Report

Read `test-cases/impacted-apis-report.json` and extract:

```
1. impacted_endpoints[] — list of {method, path, function, file, change_type}
   - change_type is "added", "modified", or "deleted"

2. impacted_services[] — list of {class_name, function, file, change_type}
   - Map each service back to the controller that calls it

3. impacted_models[] — list of {model, table, file, added_fields, removed_fields, modified_fields}
   - Map each model back to the services/controllers that use it
   - Pay attention to OrgScopedModel changes — these affect org_id filtering behavior

4. dependency_chains[] — traces showing Model → Service → Controller impact paths
   - Use these to identify controllers that need test updates even if the controller
     file itself didn't change (e.g., a model field was added that affects a service
     which is called by the controller)
```

The key insight: `find-impacted-apis` already handles both committed AND uncommitted changes,
git diff logic, and dependency chain tracing. This skill just consumes its output.

### Step C: Re-read APIs.md for Affected Endpoints

- Re-read `APIs.md` (should have been updated by the `generate-api-code-documentation` skill)
- Filter to only the endpoints identified in Step B
- If APIs.md doesn't reflect recent changes, warn the user:
  "APIs.md may be outdated. Consider re-running `generate-api-code-documentation` first."

### Step D: Update Affected Test Files

For each affected controller (derived from the impact report):

```
1. READ the existing test file (test-cases/test_{controller}.py)
2. READ the current controller and service source code
3. MATCH the impact report entries to test classes:

   For "added" endpoints:
   → ADD a new test class with all 5 categories (success, auth, validation, not-found, edge cases)

   For "modified" endpoints or services:
   → READ the updated source code to understand what changed
   → UPDATE test cases to reflect new behavior (new fields, changed validation, new error codes)
   → ADD tests for any new branches/error paths introduced by the change
   → CHECK if the patch path changed (e.g., Core→EE switch) and update accordingly

   For "deleted" endpoints:
   → REMOVE the corresponding test class

   For model changes (added/removed/modified fields):
   → UPDATE test fixtures (sample data) to include new fields or remove old ones
   → ADD validation tests for new field constraints
   → UPDATE mock objects to reflect the new model shape
   → If model changed from TimestampModel to OrgScopedModel (or vice versa), update
     org_id handling in fixtures

4. PRESERVE any manually written test functions:
   - Detect functions NOT matching the generated naming pattern
   - Or functions wrapped in # <!-- MANUAL --> ... # <!-- /MANUAL --> comments
   - NEVER delete or overwrite these

5. WRITE the updated test file
```

### Step E: Report Results

```
Report to user:
  Impact detected:
  - {N} endpoints changed ({added} added, {modified} modified, {deleted} deleted)
  - {M} services affected
  - {K} models affected

  Test files updated:
  - test-cases/test_agents.py — 8 tests added, 3 updated, 1 removed
  - test-cases/test_users.py — 2 tests updated (model field change)
  - ...
  Total: {X} tests added, {Y} updated, {Z} removed
```

---

## Cross-Referencing Other Skills

This skill is designed to work in a pipeline with other skills. Here's how they connect:

### APIs.md (generate-api-code-documentation — `.claude/skills/generate-api-code-documentation/SKILL.md`)
- **Primary input.** Every endpoint documented in APIs.md must have corresponding test cases.
- The code traces, error responses, and SQLAlchemy queries in APIs.md directly inform what to test.
- If APIs.md documents a `409 Conflict` for duplicate email, there MUST be a test for it.
- **Run this skill first** if APIs.md is missing or outdated.

### find-impacted-apis (`.claude/skills/find-impacted-apis/`)
- **Change detection engine.** On subsequent runs, this skill identifies exactly which endpoints,
  services, and models changed — including indirect impacts via dependency chains.
- Uses `analyze_diff.py` script and maintains its own state at `~/.claude-skills/find-impacted-apis/last_run.json`.
- Produces `impacted-apis-report.json` which this skill consumes to know what to update.
- **Do NOT reimplement change detection.** Always delegate to this skill.

### Postman Collections (postman skill — `.claude/skills/postman/SKILL.md`)
- **Optional input.** If `postman_collection/` directory exists with `.postman_collection.json` files:
  - Reuse the sample request bodies from Postman collections as test fixtures (realistic payloads)
  - Cross-check that every endpoint in the Postman collection has test coverage

---

## Project-Specific Reference

### Controllers & Route Prefixes

**Note:** Route prefixes are the same in both Core and EE editions. Auth dependencies differ (Core uses `require_org_member` etc., EE uses `require_ee_org_member` etc.).

| Controller File | Route Prefix | Auth Pattern (Core / EE) |
|---|---|---|
| `agents.py` | `/api/v1/agent/` | `require_org_member` / `require_ee_org_member` |
| `agent_configs.py` | `/api/v1/agent_config/` | `require_org_member` / `require_ee_org_member` |
| `agent_channel_phone_numbers.py` | `/api/v1/agent_channel_phone_number/` | `require_org_member` / `require_ee_org_member` |
| `auth.py` | `/api/v1/auth/` | None (public) |
| `users.py` | `/api/v1/user/` | `require_org_member` / `require_ee_org_member` |
| `organizations.py` | `/api/v1/organization/` | Mixed (`require_admin_or_owner`, `require_org_member`, `get_jwt_claims`, public) |
| `channels.py` | `/api/v1/channel/` | Mixed (`require_org_member`, `require_admin_or_owner`, public) |
| `channel_phone_numbers.py` | `/api/v1/channel_phone_number/` | Mixed (`require_org_member`, public) |
| `call_logs.py` | `/api/v1/call-log/` | `require_org_member` |
| `api_keys.py` | `/api/v1/api-keys/` | Mixed (`require_admin_or_owner`, `get_jwt_claims`) |
| `services.py` | `/api/v1/services/` | Mixed (`require_admin_or_owner`, `get_jwt_claims`) |
| `service_providers.py` | `/api/v1/service-providers/` | Mixed (`require_admin_or_owner`, `get_jwt_claims`) |
| `models.py` | `/api/v1/model/` | `require_org_member` / `require_ee_org_member` |
| `voices.py` | `/api/v1/voice/` | `require_org_member` / `require_ee_org_member` |
| `generated_api_keys.py` | `/api/v1/generated-api-keys/` | Mixed (`require_admin_or_owner`, `get_jwt_claims`) |
| `telephony.py` | `/ws` (on `app`, not `api_v1`) | None (public WebSocket) |

**Special cases:**
- **`call_logs.py`** — Exists in both `core/api/v1/` and `ee/api/v1/`. The EE version uses `require_ee_org_member` and passes `org_id=UUID(claims.org_id)` to `CallLogService`. Core version uses `require_org_member` without explicit org_id.
- **`telephony.py`** — Core has the full implementation. EE version (`ee/api/v1/telephony.py`) re-exports the core router since telephony providers don't send auth tokens. It is a **WebSocket** endpoint mounted on `app` directly (not under `api_v1`), so it lives at `/ws`. No auth required. Test with `TestClient.websocket_connect()`.
- **Root-level endpoints** — `app` directly mounts `/` (root), `/health`, `/ready`, and `/environment`. These are edition-agnostic, no auth required, mounted on `app` not `api_v1`.
- **Capabilities endpoint** — `GET /api/v1/capabilities` is defined inline in `main.py` on `api_v1`. No auth required. Returns `{"capabilities": ..., "edition": ..., "ee_enabled": ...}`.

### Model Enums (from `core/models/enums.py`)

| Enum | Values |
|---|---|
| `UserStatus` | pending, active, suspended, deleted |
| `OrganizationStatus` | active, suspended, deleted |
| `Role` | owner, admin, member, viewer |
| `InviteStatus` | pending, accepted, expired, cancelled |
| `AccessRequestStatus` | pending, approved, rejected |
| `AuthProvider` | email, firebase, google, github |
| `AgentType` | inbound, outbound, chatbot |
| `ChannelType` | twilio, exotel, web, google_meet, zoom |

### Auth Dependency Functions

**Core auth** (`core/middleware/auth.py`):

| Function | Behavior | Failure Code |
|---|---|---|
| `get_jwt_claims` | Validates JWT, sets TenantContext (uses `DEFAULT_ORG_ID` in core), returns JWTClaims | 401 |
| `get_optional_jwt_claims` | Same but returns None if no token | — |
| `require_org_member` | Depends on `get_jwt_claims`, validates user_id exists | 400 |
| `require_admin_or_owner` | Depends on `get_jwt_claims`, validates user_id exists | 403 |
| `require_owner` | Depends on `get_jwt_claims`, validates role == "owner" | 403 |

**EE auth** (`ee/middleware/auth.py`):

| Function | Behavior | Failure Code |
|---|---|---|
| `get_ee_jwt_claims` | Validates JWT, sets TenantContext with org_id from JWT | 401 |
| `get_optional_ee_jwt_claims` | Same but returns None if no token | — |
| `get_ee_current_user` | Depends on `get_ee_jwt_claims`, accepts optional `tenant_id` header to override org_id | 401 |
| `require_ee_org_member` | Depends on `get_ee_current_user`, validates user_id + org_id is valid UUID | 400 |
| `require_ee_admin_or_owner` | Depends on `get_ee_current_user`, validates user_id + org_id UUID + role in (admin, owner) | 403 |
| `require_ee_owner` | Depends on `get_ee_current_user`, validates role == "owner" | 403 |

**Key difference:** EE controllers pass `org_id=UUID(claims.org_id)` explicitly to service constructors, while core controllers don't (they rely on TenantContext fallback in `BaseService`).

### JWTClaims Structure

```python
class JWTClaims(BaseModel):
    user_id: int
    org_id: Optional[Union[str, int]] = None
    role: Optional[str] = None
    email: str
    exp: int
    iat: int
```

### Multi-Tenancy

- **Core edition**: `org_id` defaults to `settings.DEFAULT_ORG_ID` (`"00000000-0000-0000-0000-000000000001"`)
- **EE edition**: `org_id` comes from JWT claims
- **BaseService.query()** auto-filters by `organization_id` for `OrgScopedModel` subclasses
- **BaseService.upsert()** auto-injects `organization_id` for org-scoped models
- **TenantContext** (`core/context.py`) stores `org_id`, `user_id`, `role` per request via ContextVar

---

## Important Rules

1. **Every endpoint in APIs.md gets a test class.** Do not skip endpoints. If APIs.md documents 15 routes, produce 15 test classes.

2. **Always write to files.** Never just print test code to chat. The whole point is runnable test files.

3. **Read actual source code.** APIs.md is the starting point, but always verify by reading the controller and service to catch undocumented edge cases.

4. **Test real validation.** Do not mock FastAPI query parameter validation. Send actual invalid params and assert 422 responses. For body validation (which happens in services), test for 400 responses.

5. **Mock at the right level.** Patch service classes at the import site (ee.api.v1.X or core.api.v1.X depending on which edition is active). Tests should be resilient to refactoring within services.

6. **Use descriptive test names.** Each test name should explain the scenario and expected outcome without reading the body.

7. **Do not duplicate tests.** Each scenario is tested exactly once. If an auth check applies to all endpoints, test it once per endpoint, not per-scenario.

8. **Preserve manual tests.** On incremental updates, never delete or overwrite test functions that were manually written by the user.

9. **Keep fixtures close.** Controller-specific fixtures go in the test file. Shared fixtures go in conftest.py.

10. **Match the project's patterns.** Read existing test files (if any) before generating. Adapt to the project's mock strategy, fixture style, and assertion patterns.

11. **Override on `api_v1`, not `app`.** Dependency overrides must be set on the `api_v1` sub-app (from `main import api_v1`) because that's where routers are mounted. Using `app.dependency_overrides` will NOT work.

12. **Generate tests for BOTH editions.** Every controller gets two test files: one in `test-cases/core/` (patching `core.api.v1.*`), one in `test-cases/ee/` (patching `ee.api.v1.*`). Each edition has its own conftest with the correct auth overrides.

13. **Use `client_as_member`/`client_as_admin`/`client_as_owner` fixtures.** Do not create ad-hoc TestClient instances. Use the edition-specific conftest fixtures from `test-cases/core/conftest.py` or `test-cases/ee/conftest.py`.

14. **Test directory is `test-cases/`.** Not `tests/`. Test files go in `test-cases/core/` and `test-cases/ee/` subdirectories. Shared fixtures go in `test-cases/conftest.py`.

15. **Route prefix consistency.** All controllers use the same route prefix in both Core and EE editions. Always verify against `main.py` if unsure.

16. **Assert org_id handling.** In EE tests, verify services are called with `org_id=UUID(claims.org_id)`. In Core tests, verify services are called WITHOUT explicit org_id. This is the primary behavioral difference between editions.

17. **Telephony is WebSocket.** `telephony.py` provides a WebSocket endpoint at `/ws` mounted on `app` (not `api_v1`). It has no auth. EE re-exports the core router. Test with `TestClient.websocket_connect("/ws")` — do NOT use HTTP methods. Mock `BotRunnerService` and `bot()` since they require actual voice pipeline infrastructure.
