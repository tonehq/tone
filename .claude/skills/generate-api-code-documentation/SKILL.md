---
name: generate-api-code-documentation
description: >
  Automatically reads FastAPI controller, service, and model files to generate a comprehensive APIs.md
  reference document. Traces code execution paths from route handler through service layer to database
  queries, producing human-readable pseudo-code documentation. Use this skill whenever the user asks to
  document APIs, generate API documentation, create an APIs.md, map API code, trace API logic, or
  understand what their APIs do. Also trigger when the user mentions "document my endpoints",
  "what does this API do", "trace the code flow", "map my controllers", "generate API reference",
  or wants a reference doc for their backend code. Even if they just say "document my code" or
  "I need API docs", this skill should trigger. This skill is specifically designed for FastAPI +
  SQLAlchemy projects with a controllers/services/models folder structure.
---

# Generate API Code Documentation

This skill reads a FastAPI codebase (controllers, services, models) and produces a structured
`APIs.md` document that serves as a living reference for other skills (e.g., CRUD generation,
bug fixing, code review).

The output has TWO layers:
1. **File-level summaries** — what each .py file contains (functions, classes, overview)
2. **Per-route API documentation** — every single API route gets its own detailed section with request/response, pseudo-code, queries, and models

---

## CRITICAL: Writing to APIs.md

**This skill MUST write the output to an actual file. Do NOT just print it to the conversation.**

### File Location Rules

1. **Check if user provided a path.** If user says "write to docs/APIs.md", use that path.
2. **If no path provided**, look for an existing `APIs.md` in the project root directory.
3. **If no `APIs.md` exists in the root**, CREATE one at `{project_root}/APIs.md`.
4. **Always confirm the path** before writing. Example: "I'll write the documentation to `./APIs.md`. Sound good?"

### How to Write the File

Use the file write/create tools available in your environment to write the complete markdown content
to the APIs.md file. After writing:
1. Verify the file was created/updated by reading it back
2. Print a summary: "✅ APIs.md written to `{path}` — {N} routes documented across {M} files"

### Updating an Existing APIs.md

If `APIs.md` already exists:
1. Read the existing file
2. Re-scan the codebase
3. OVERWRITE the file with the new complete documentation
4. Preserve any sections wrapped in `<!-- MANUAL -->` ... `<!-- /MANUAL -->` (user's custom notes)
5. Update the "Last updated" timestamp

---

## Prerequisites

- FastAPI project with a dual-edition folder structure:
  ```
  project-root/
  ├── core/                    # Community Edition (CE)
  │   ├── api/v1/              # Route handlers / API endpoints (controllers)
  │   ├── services/            # Business logic layer
  │   ├── models/              # SQLAlchemy ORM models
  │   └── schemas/             # Pydantic request/response schemas (optional)
  ├── ee/                      # Enterprise Edition (EE)
  │   ├── api/v1/              # EE-specific route handlers
  │   ├── services/            # EE-specific business logic
  │   ├── models/              # EE-specific models
  │   └── schemas/             # EE-specific schemas (optional)
  └── APIs.md                  # ← OUTPUT FILE (created here if not specified)
  ```
- The skill scans BOTH `core/` and `ee/` directories and documents them separately
- EE endpoints that extend or override CE functionality should be clearly marked

---

## Step 0: Discover Project Structure & Determine Output Path

Before doing anything else:

```
1. FIND the project root:
   - Look for pyproject.toml, setup.py, .git/, or main.py as anchors
   - The project root is where APIs.md will be written (unless user specifies otherwise)

2. DETERMINE the APIs.md path:
   - Did user provide a path? → Use it
   - Does {project_root}/APIs.md exist? → Will overwrite it
   - Neither? → Will create {project_root}/APIs.md
   - CONFIRM with user: "I'll write to ./APIs.md"

3. Look for the dual-edition structure:
   - core/ → Community Edition code
   - ee/   → Enterprise Edition code

4. Within each edition, locate:
   - api/v1/        → Controller/route files (the endpoints)
   - services/      → Business logic layer
   - models/        → SQLAlchemy ORM models
   - schemas/       → Pydantic schemas (if present)

5. List the directory tree (2 levels deep) to confirm the layout

6. Identify the naming convention:
   - Are controllers named *_controller.py, *_router.py, *_routes.py, *_api.py?
   - Are services named *_service.py, *_handler.py, *_manager.py?
   - Are models named *_model.py, or just *.py in a models/ folder?

7. Note any EE files that extend/override CE files
```

---

## Step 1: Parse Models (Foundation Layer)

Read ALL model files in `core/models/` and `ee/models/`. For each model, extract:

| Field | How to Find It |
|---|---|
| **Class name** | `class UserModel(Base):` or `class User(Base):` |
| **Table name** | `__tablename__ = "users"` |
| **Columns & types** | `Column(String, nullable=False)`, `Column(Integer, primary_key=True)` |
| **Relationships** | `relationship("Order", back_populates="user")` |
| **Foreign keys** | `ForeignKey("organizations.id")` |
| **Indexes & constraints** | `UniqueConstraint`, `Index`, `CheckConstraint` |
| **Mixins / base classes** | `TimestampMixin`, `SoftDeleteMixin`, custom bases |

---

## Step 2: Parse Schemas (if present)

If there's a `schemas/` or `dtos/` folder, extract:
- Request schemas (Pydantic BaseModel — field names, types, validators, defaults)
- Response schemas
- Shared/nested schemas
- Map which schema is used by which route (needed for Step 3)

---

## Step 3: Scan Controllers — Document EVERY SINGLE ROUTE

**This is the most critical step.**

Read ALL controller/route files in `core/api/v1/` and `ee/api/v1/`.

For EVERY route decorator you find (`@router.get`, `@router.post`, `@router.put`, `@router.patch`, `@router.delete`), create a **dedicated documentation block**.

### How to Find Routes

Look for these patterns:
```python
@router.get("/users/{user_id}")
@router.post("/users/")
@router.put("/users/{user_id}")
@router.patch("/users/{user_id}")
@router.delete("/users/{user_id}")
```

Also check for router prefix:
```python
router = APIRouter(prefix="/api/v1/users", tags=["users"])
```
Combine prefix + route path = FULL route path.

### For EACH Route, Document ALL of the Following

**Every single route produces a block like this:**

```markdown
##### `POST /api/v1/users/` — Create User
> **File:** `core/api/v1/user_controller.py` | **Function:** `create_user()`

**Auth:** Requires authenticated user with `admin` role (`Depends(get_current_user)`, `Depends(require_role("admin"))`)

**Request:**
- **Path Params:** none
- **Query Params:** none
- **Body:** `CreateUserRequest`

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| email | string | yes | — | User email address |
| name | string | yes | — | Full name |
| role | enum(admin,user) | no | "user" | User role |

**Response:** `UserResponse` (201 Created)

| Field | Type | Description |
|---|---|---|
| id | uuid | Created user ID |
| email | string | User email |
| created_at | datetime | Creation timestamp |

**Error Responses:**
- `400` — Validation error (invalid email format)
- `409` — User with this email already exists
- `403` — Insufficient permissions

**Models Used:** `UserModel`, `OrganizationModel`

**SQLAlchemy Queries:**
1. **SELECT** on `users` — check if email already exists
   ```python
   db.query(User).filter(User.email == data.email).first()
   ```
2. **INSERT** into `users` — create new user record
   ```python
   db.add(new_user)
   db.commit()
   db.refresh(new_user)
   ```

**Code Trace (Pseudo-code):**
```
ROUTE: POST /api/v1/users/
CONTROLLER: create_user() in core/api/v1/user_controller.py
SERVICE: UserService.create_user() in core/services/user_service.py

1. [CONTROLLER] Receive request body (CreateUserRequest)
2. [CONTROLLER] Extract current_user from auth dependency
3. [CONTROLLER] Call user_service.create_user(db, data, current_user)
4. [SERVICE] CHECK if user with same email exists
   → db.query(User).filter(User.email == data.email).first()
   → IF exists: RAISE 409 "Email already registered"
5. [SERVICE] HASH password using bcrypt
6. [SERVICE] CREATE UserModel instance with provided data
7. [SERVICE] SAVE to database
   → db.add(new_user), db.commit(), db.refresh(new_user)
8. [SERVICE] LOG info: "User created: {user.id}"
9. [SERVICE] CALL notification_service.send_welcome_email(user.email)
   → Sends async email via SendGrid
10. [CONTROLLER] RETURN UserResponse(new_user)

ERROR HANDLING:
- IntegrityError → ROLLBACK, return 409
- ValidationError → return 422 with field details
- Exception → LOG error, ROLLBACK, return 500
```

**Service Dependencies:**
- `UserService.create_user()` — primary handler
- `NotificationService.send_welcome_email()` — called within UserService
```

### How to Trace Each Route

For each route, follow this process:

```
1. READ the controller function body
2. IDENTIFY which service method(s) it calls
3. GO READ that service method (follow the import to find the file)
4. Inside the service method:
   a. Note every db.query / db.execute / db.add / db.commit call → these are SQLAlchemy queries
   b. Note every model class referenced → these are Models Used
   c. Note every other service called → follow those too (recursive)
   d. Note logger lines → use them as clues for pseudo-code descriptions
   e. Note try/except blocks → these are error handling paths
   f. Note if/else branches → these are business rules
5. ASSEMBLE all findings into the documentation block above
```

---

## Step 4: Build the File-Level Summary

In ADDITION to the per-route docs, include a summary of every .py file scanned.

```markdown
## File Summary

### core/api/v1/
| File | Routes | Functions |
|---|---|---|
| user_controller.py | 5 routes | create_user, get_user, list_users, update_user, delete_user |
| auth_controller.py | 3 routes | login, logout, refresh_token |

### core/services/
| File | Class | Methods |
|---|---|---|
| user_service.py | UserService | create_user, get_by_id, get_by_email, update, delete, list_all, search, count |
| auth_service.py | AuthService | authenticate, generate_token, verify_token, refresh, revoke |

### core/models/
| File | Model | Table | Columns | Relationships |
|---|---|---|---|---|
| user_model.py | UserModel | users | 12 | 3 |
| org_model.py | OrganizationModel | organizations | 8 | 2 |

### ee/api/v1/
| File | Routes | Functions |
|---|---|---|
| sso_controller.py | 4 routes | saml_login, saml_callback, oidc_login, oidc_callback |

### ee/services/
| File | Class | Extends | Methods |
|---|---|---|---|
| sso_service.py | SSOService | AuthService | saml_authenticate, oidc_authenticate, validate_assertion |
```

---

## Step 5: Assemble and WRITE the APIs.md File

### Final Document Structure

```markdown
# API Documentation — [Project Name]

> Auto-generated by `generate-api-code-documentation` skill.
> Last updated: YYYY-MM-DD
> Total routes documented: N | Models: M | Services: S

## Table of Contents
- [File Summary](#file-summary)
- [Models](#models)
  - [Core Models](#core-models)
  - [EE Models](#ee-models)
- [API Routes](#api-routes)
  - [Core (Community Edition)](#core-community-edition)
    - [User APIs (user_controller.py)](#user-apis)
    - [Auth APIs (auth_controller.py)](#auth-apis)
  - [Enterprise Edition](#enterprise-edition)
    - [SSO APIs (sso_controller.py)](#sso-apis)
- [Service Dependency Map](#service-dependency-map)

---

## File Summary
(Output from Step 4)

---

## Models

### Core Models
(Each model: class name, table, columns, relationships, constraints)

### EE Models
(EE-only models, note if they extend core models)

---

## API Routes

### Core (Community Edition)

#### User APIs
> Source: `core/api/v1/user_controller.py`

##### `POST /api/v1/users/` — Create User
(FULL per-route block: auth, request, response, errors, models, queries, pseudo-code, deps)

##### `GET /api/v1/users/{user_id}` — Get User
(FULL per-route block)

##### `GET /api/v1/users/` — List Users
(FULL per-route block)

##### `PUT /api/v1/users/{user_id}` — Update User
(FULL per-route block)

##### `DELETE /api/v1/users/{user_id}` — Delete User
(FULL per-route block)

#### Auth APIs
> Source: `core/api/v1/auth_controller.py`

##### `POST /api/v1/auth/login` — Login
(FULL per-route block)

... (EVERY route in every controller)

### Enterprise Edition

#### SSO APIs
> Source: `ee/api/v1/sso_controller.py`
> **Extends:** core auth system with SAML/OIDC support

##### `POST /api/v1/sso/saml/callback` — SAML Callback
(FULL per-route block)

... (EVERY route)

---

## Service Dependency Map

| Service | File | Depends On | Used By (Routes) |
|---|---|---|---|
| UserService | core/services/user_service.py | NotificationService, AuthService | POST /users, GET /users/{id}, ... |
| AuthService | core/services/auth_service.py | TokenService, UserService | POST /auth/login, POST /auth/refresh |
| SSOService | ee/services/sso_service.py | AuthService (extends) | POST /sso/saml/callback, ... |

---
```

### WRITE THE FILE

After assembling the complete document content:

```
1. DETERMINE output path (from Step 0)

2. IF APIs.md already exists at that path:
   a. Read existing file
   b. Extract any <!-- MANUAL --> ... <!-- /MANUAL --> blocks
   c. Insert preserved manual blocks into the new content at the same locations

3. WRITE the complete markdown content to the file using file create/write tools
   - Write the ENTIRE document — do NOT truncate, summarize, or skip routes
   - If the file is very large, write it in sections but ensure ALL content is written

4. VERIFY the write succeeded:
   - Read back the file
   - Confirm it starts with "# API Documentation"
   - Confirm it contains all the routes you documented

5. REPORT to user:
   ✅ APIs.md written to ./APIs.md
   - Routes documented: 23
   - Models documented: 8
   - Services traced: 6
   - Controller files scanned: 5
   - Total lines: 1,247
```

---

## Important Rules

1. **EVERY route gets its own section.** Do not skip routes. Do not combine routes. If a controller has 15 endpoints, produce 15 separate blocks. This is the #1 rule.

2. **ALWAYS write to a file.** Never just print documentation to chat. The whole point is a persistent APIs.md that other skills can reference. If you cannot find or create the file, tell the user and ask for the correct path.

3. **Follow imports to trace code.** If a controller imports `from services.user_service import UserService`, go read that service file. If the service imports `from services.email_service import EmailService`, follow that too.

4. **Don't skip error paths.** Document what happens on failure, not just success. Try/except blocks and logger.error lines reveal edge cases.

5. **Use logger lines as a guide.** Logger lines are written by humans to describe intent. Use them as clues for pseudo-code descriptions.

6. **Include actual SQLAlchemy query code.** Don't write "queries the database." Include the Python code snippet. Downstream skills need exact patterns.

7. **Note auth patterns.** Document the exact `Depends()` chain so CRUD generation skills can replicate it.

8. **Group by edition → controller file.** Core vs EE first, then by controller file within each.

9. **Document request/response as tables.** Field name, type, required, default, description. Every field.

10. **Read the actual schema files.** Don't just write the class name — go read the Pydantic model and document every field.

11. **When in doubt, read more code.** Follow utility functions, helpers, mixins. Complete traces, not surface scans.

12. **File-level summaries AND per-route docs.** Both layers. The summary gives a quick overview; the per-route docs give the detail.