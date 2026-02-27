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
2. **Output directory** (optional) — Where to write test files (default: `tests/`).

---

## Step 0: Discover Project Context

```
1. FIND the project root (look for pyproject.toml, .git/, main.py)

2. CHECK for APIs.md:
   - Read {project_root}/APIs.md
   - If it doesn't exist → STOP, ask user to run generate-api-code-documentation first

3. READ main.py (or main_ee.py) to understand:
   - How routers are mounted and their URL prefixes
   - The app factory / lifespan setup
   - Database session dependency (get_db)

4. READ core/middleware/auth.py to understand:
   - Auth dependency functions (require_authenticated, require_admin_or_owner, require_org_member)
   - How JWTClaims works, what fields it contains
   - This is critical for mocking auth in tests

5. CHECK for existing test infrastructure:
   - Does tests/ directory exist?
   - Does tests/conftest.py exist?
   - If not, they will be created in Step 1

6. CHECK for postman/ directory:
   - If Postman collections exist (from the postman skill — see .claude/skills/postman/SKILL.md),
     cross-reference them for request body examples and endpoint paths.
   - Postman collections contain realistic sample payloads that can be reused as test fixtures.
```

---

## Step 1: Set Up Test Infrastructure (First Run Only)

If `tests/conftest.py` does not exist, create it with:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app  # Adjust import based on project entry point


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=Session)
    db.query.return_value = db
    db.filter.return_value = db
    db.first.return_value = None
    db.all.return_value = []
    db.commit.return_value = None
    db.refresh.return_value = None
    db.add.return_value = None
    db.delete.return_value = None
    return db


@pytest.fixture
def mock_authenticated_user():
    """Mock JWT claims for an authenticated regular user."""
    return {
        "sub": "test-user-uuid",
        "org_id": "test-org-uuid",
        "role": "member",
        "email": "test@example.com"
    }


@pytest.fixture
def mock_admin_user():
    """Mock JWT claims for an admin user."""
    return {
        "sub": "admin-user-uuid",
        "org_id": "test-org-uuid",
        "role": "admin",
        "email": "admin@example.com"
    }


@pytest.fixture
def auth_headers():
    """Bearer token headers for authenticated requests."""
    return {"Authorization": "Bearer test-token"}
```

Adapt the conftest based on what you discover in Step 0 about auth patterns and DB dependencies.

Also create `tests/__init__.py` if it doesn't exist.

---

## Step 2: Parse APIs.md for Endpoint Inventory

Read `APIs.md` and extract for EVERY documented route:

| Field | What to Extract |
|---|---|
| **HTTP method** | GET, POST, PUT, PATCH, DELETE |
| **Full path** | e.g., `/api/v1/agents/{agent_id}` |
| **Controller file** | e.g., `core/api/v1/agents.py` |
| **Function name** | e.g., `get_agent()` |
| **Auth requirements** | Which auth dependency is used |
| **Request body fields** | Field name, type, required, default |
| **Path/query params** | Parameter names and types |
| **Response status** | Success status code (200, 201, 204) |
| **Error responses** | All documented error codes and conditions |
| **Models used** | SQLAlchemy models involved |
| **Service methods** | Which service methods are called |

---

## Step 3: Trace Source Code for Each Endpoint

For each endpoint extracted from APIs.md, READ the actual source code to discover:

```
1. READ the controller function in core/api/v1/{controller}.py
   - Identify exact parameter names and types
   - Identify dependency injection (Depends(...)) — especially auth and db
   - Identify what service method(s) are called
   - Identify any inline validation or early returns

2. READ the service method in core/services/{service}.py
   - Identify all DB queries (what can return None, empty list, raise exceptions)
   - Identify business logic branches (if/else, validation checks)
   - Identify all raised HTTPException or custom exceptions with their status codes
   - Identify side effects (other services called, external API calls)

3. READ the model in core/models/{model}.py
   - Identify required fields, nullable fields, unique constraints
   - Identify foreign key relationships (for testing cascades/dependencies)
   - Identify JSONB/complex fields that need special test data

4. READ the schema (if exists) in core/schemas/
   - Identify Pydantic validation rules (min_length, regex, enum values)
   - These become validation error test cases
```

---

## Step 4: Generate Test Cases for Each Endpoint

For EVERY endpoint, generate test cases in these categories:

### Category 1: Success Cases
- Happy path with all required fields
- Happy path with optional fields included
- Happy path with minimum valid data

### Category 2: Authentication & Authorization
- Request without auth token → 401/403
- Request with invalid/expired token → 401
- Request with wrong role (if role-based) → 403
- Request for resource in different org (if multi-tenant) → 403/404

### Category 3: Validation Errors
- Missing required body fields → 422
- Invalid field types (string where int expected) → 422
- Fields exceeding constraints (too long, out of range) → 422
- Invalid enum values → 422
- Invalid path parameter format (non-UUID where UUID expected) → 422

### Category 4: Not Found / Conflict
- Resource not found (GET/PUT/DELETE with non-existent ID) → 404
- Duplicate creation (POST with existing unique field) → 409
- Foreign key reference doesn't exist → 400/404

### Category 5: Edge Cases (discovered from code tracing)
- Empty string vs null for optional fields
- Empty list responses
- Pagination boundaries (if applicable)
- Concurrent modification scenarios (if service handles them)
- Large payloads / special characters in string fields

### Test Function Naming Convention

```python
# Pattern: test_{method}_{endpoint}_{scenario}
def test_post_agents_success():
def test_post_agents_missing_name_returns_422():
def test_post_agents_unauthenticated_returns_401():
def test_get_agent_not_found_returns_404():
def test_delete_agent_wrong_org_returns_403():
```

---

## Step 5: Write Test Files

### File Structure

One test file per controller:

```
tests/
├── __init__.py
├── conftest.py
├── test_agents.py          # Tests for core/api/v1/agents.py
├── test_auth.py            # Tests for core/api/v1/auth.py
├── test_users.py           # Tests for core/api/v1/users.py
├── test_organizations.py   # Tests for core/api/v1/organizations.py
├── test_channels.py        # Tests for core/api/v1/channels.py
└── ...
```

### Test File Template

Each test file follows this structure:

```python
"""Tests for {Controller Name} API endpoints.

Source: core/api/v1/{controller}.py
Generated from APIs.md by test-cases skill.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ─── Fixtures specific to this controller ───

@pytest.fixture
def sample_agent_data():
    """Valid agent creation payload."""
    return {
        "name": "Test Agent",
        # ... all required fields with realistic values
    }


@pytest.fixture
def mock_agent():
    """Mock agent model instance."""
    agent = MagicMock()
    agent.id = "test-agent-uuid"
    agent.name = "Test Agent"
    agent.org_id = "test-org-uuid"
    # ... all fields that the response serializes
    return agent


# ─── POST /api/v1/agents/ — Create Agent ───

class TestCreateAgent:
    """Tests for POST /api/v1/agents/"""

    def test_create_agent_success(self, client, auth_headers, sample_agent_data):
        """Should create agent and return 201."""
        with patch("core.services.agent_service.AgentService.create") as mock_create:
            mock_create.return_value = MagicMock(id="new-uuid", **sample_agent_data)
            response = client.post("/api/v1/agents/", json=sample_agent_data, headers=auth_headers)
            assert response.status_code == 201

    def test_create_agent_unauthenticated(self, client, sample_agent_data):
        """Should return 401 without auth token."""
        response = client.post("/api/v1/agents/", json=sample_agent_data)
        assert response.status_code in (401, 403)

    def test_create_agent_missing_required_field(self, client, auth_headers):
        """Should return 422 when required field is missing."""
        response = client.post("/api/v1/agents/", json={}, headers=auth_headers)
        assert response.status_code == 422

    # ... more tests for this endpoint


# ─── GET /api/v1/agents/{agent_id} — Get Agent ───

class TestGetAgent:
    """Tests for GET /api/v1/agents/{agent_id}"""

    def test_get_agent_success(self, client, auth_headers, mock_agent):
        # ...

    def test_get_agent_not_found(self, client, auth_headers):
        # ...

    # ... more tests


# ─── (EVERY endpoint gets its own test class) ───
```

### Mock Strategy

```
1. MOCK the database dependency (get_db) at the FastAPI dependency level
   - Use app.dependency_overrides[get_db] = lambda: mock_db in conftest

2. MOCK service methods using unittest.mock.patch
   - Patch at the module where the service is imported, not where it's defined
   - e.g., patch("core.api.v1.agents.AgentService") not "core.services.agent_service.AgentService"

3. MOCK auth dependencies
   - Override require_authenticated / require_org_member to return mock claims
   - For auth failure tests, do NOT override (let the real dependency reject)

4. DO NOT mock Pydantic validation — let FastAPI's real validation run
   - This catches actual 422 errors from invalid payloads
```

---

## Step 6: Write the Test Files

```
1. For each controller, WRITE the complete test file using the Write tool
2. After writing each file:
   - Verify the file was created by reading it back
   - Confirm all endpoints from APIs.md are covered
3. Update tests/.last_run with current timestamp and git SHA

4. REPORT to user:
   Test files generated:
   - tests/test_agents.py — 24 tests (6 endpoints × ~4 cases each)
   - tests/test_auth.py — 12 tests (3 endpoints × ~4 cases each)
   - ...
   Total: {N} test cases across {M} files
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
  --output tests/
```

This produces two files:
- `tests/impacted-apis-report.json` — structured data for programmatic use
- `tests/impacted-apis-report.md` — human-readable summary

If this is the first run of `find-impacted-apis` (no state file at
`~/.claude-skills/find-impacted-apis/last_run.json`), you can either:
- Ask the user for a commit range, OR
- Fall back to a full run (treat all endpoints as "added" — same as first-run behavior)

**If the report shows zero impacted endpoints, services, and models → report
"No API changes detected since last run" and stop.**

### Step B: Parse the Impact Report

Read `tests/impacted-apis-report.json` and extract:

```
1. impacted_endpoints[] — list of {method, path, function, file, change_type}
   - change_type is "added", "modified", or "deleted"

2. impacted_services[] — list of {class_name, function, file, change_type}
   - Map each service back to the controller that calls it

3. impacted_models[] — list of {model, table, file, added_fields, removed_fields, modified_fields}
   - Map each model back to the services/controllers that use it

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
1. READ the existing test file (tests/test_{controller}.py)
2. READ the current controller and service source code
3. MATCH the impact report entries to test classes:

   For "added" endpoints:
   → ADD a new test class with all 5 categories (success, auth, validation, not-found, edge cases)

   For "modified" endpoints or services:
   → READ the updated source code to understand what changed
   → UPDATE test cases to reflect new behavior (new fields, changed validation, new error codes)
   → ADD tests for any new branches/error paths introduced by the change

   For "deleted" endpoints:
   → REMOVE the corresponding test class

   For model changes (added/removed/modified fields):
   → UPDATE test fixtures (sample data) to include new fields or remove old ones
   → ADD validation tests for new field constraints
   → UPDATE mock objects to reflect the new model shape

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
  - tests/test_agents.py — 8 tests added, 3 updated, 1 removed
  - tests/test_users.py — 2 tests updated (model field change)
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
- **Optional input.** If `postman/` directory exists with `.postman_collection.json` files:
  - Reuse the sample request bodies from Postman collections as test fixtures (realistic payloads)
  - Cross-check that every endpoint in the Postman collection has test coverage

---

## Important Rules

1. **Every endpoint in APIs.md gets a test class.** Do not skip endpoints. If APIs.md documents 15 routes, produce 15 test classes.

2. **Always write to files.** Never just print test code to chat. The whole point is runnable test files.

3. **Read actual source code.** APIs.md is the starting point, but always verify by reading the controller and service to catch undocumented edge cases.

4. **Test real validation.** Do not mock Pydantic/FastAPI validation. Send actual invalid payloads and assert 422 responses.

5. **Mock at the right level.** Patch service methods, not internal implementation details. Tests should be resilient to refactoring within services.

6. **Use descriptive test names.** Each test name should explain the scenario and expected outcome without reading the body.

7. **Do not duplicate tests.** Each scenario is tested exactly once. If an auth check applies to all endpoints, test it once per endpoint, not per-scenario.

8. **Preserve manual tests.** On incremental updates, never delete or overwrite test functions that were manually written by the user.

9. **Keep fixtures close.** Controller-specific fixtures go in the test file. Shared fixtures go in conftest.py.

10. **Match the project's patterns.** Read existing test files (if any) before generating. Adapt to the project's mock strategy, fixture style, and assertion patterns.
