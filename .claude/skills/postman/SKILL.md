---
name: postman-collection-generator
description: Generate and maintain Postman collections from FastAPI route files. Use when the user asks to create Postman collections, export APIs to Postman, update Postman collections, or sync API changes to Postman format. Triggers on requests mentioning "Postman", "API collection", or "export APIs".
---

# Postman Collection Generator

Generate Postman v2.1 collections by reading FastAPI router files. Produce one collection per controller (router file) with all its endpoints fully configured.

## Inputs

The user provides:
1. **Source path** — A single file or directory containing FastAPI router files (e.g., `core/api/v1/`).
2. **Output directory** — Where to write the generated `.json` collection files (default: `postman/`).

## First Run Workflow

1. Read the router registration file (`main.py`) to discover all mounted routers and their URL prefixes.
2. For each router file in the source path:
   a. Parse all route decorators (`@router.get`, `@router.post`, `@router.put`, `@router.delete`, `@router.patch`).
   b. Extract for each endpoint:
      - **HTTP method**
      - **Path** (combine the router prefix from `main.py` with the route path)
      - **Request body schema** — inspect `Body(...)` parameters, Pydantic models, or `Dict[str, Any]` with field validation in the handler
      - **Query parameters** — inspect `Query(...)` parameters
      - **Path parameters** — inspect path variables (e.g., `{agent_id}`)
      - **Auth requirements** — detect dependency injection (`require_org_member`, `require_admin_or_owner`, `get_jwt_claims`) and set the appropriate auth header
      - **Response structure** — infer from the service method return if readable
   c. Generate a Postman collection JSON (v2.1 schema) for that controller.
3. Write each collection as `{controller_name}.postman_collection.json` in the output directory.
4. Write a timestamp file at `postman/.last_run` containing the current ISO 8601 timestamp and the git commit SHA (`git rev-parse HEAD`).

## Subsequent Run Workflow (Incremental Update)

On subsequent runs, detect changes from **two sources** and merge them into a single update, avoiding duplicates.

### Step 1: Detect changed router files

Collect changed files from both sources into a single deduplicated set:

**a) Local (uncommitted) changes:**
- Run `git diff --name-only -- {source_path}` (staged + unstaged working tree changes vs HEAD).
- Run `git diff --name-only --cached -- {source_path}` (staged changes only).
- Union the results — these are files with local modifications not yet committed.

**b) Committed changes since last run:**
- Read `postman/.last_run` to get the previous commit SHA.
- Run `git diff --name-only {previous_sha} HEAD -- {source_path}` to find files changed in commits since the last run.

**c) Merge both sets:**
- Combine local and committed changed files into a single deduplicated set (union). A file appearing in both lists is processed only once.
- If the combined set is empty, report "No API changes detected" and stop.

### Step 2: Update collections

For each changed router file in the deduplicated set:
1. Read the **current file contents on disk** (this captures both committed and uncommitted state).
2. Re-parse the file using the same extraction logic from the First Run Workflow.
3. Load the existing collection JSON for that controller.
4. Compare endpoints in the parsed file against those in the existing collection:
   - **New endpoints** (route path + method not in collection) → add them.
   - **Modified endpoints** (same route path + method but different parameters, body, or description) → update them.
   - **Removed endpoints** (in collection but no longer in the parsed file) → remove them.
5. Write the updated collection file.

### Step 3: Update `.last_run`

Update `postman/.last_run` with the current ISO 8601 timestamp and commit SHA (`git rev-parse HEAD`).

> **Note:** The `.last_run` SHA tracks committed state. Local uncommitted changes are always re-detected on each run via `git diff` against HEAD, so they are never missed even if the SHA hasn't changed.

## Collection Structure (Postman v2.1 Format)

Each generated collection must follow this structure:

```json
{
  "info": {
    "name": "{Controller Name} API",
    "description": "Auto-generated from {router_file_path}",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    { "key": "baseUrl", "value": "http://localhost:8000/api/v1" },
    { "key": "authToken", "value": "" }
  ],
  "auth": {
    "type": "bearer",
    "bearer": [{ "key": "token", "value": "{{authToken}}" }]
  },
  "item": [
    {
      "name": "{Endpoint Description}",
      "request": {
        "method": "POST",
        "header": [{ "key": "Content-Type", "value": "application/json" }],
        "url": {
          "raw": "{{baseUrl}}/{prefix}/{path}",
          "host": ["{{baseUrl}}"],
          "path": ["{prefix}", "{path}"]
        },
        "body": {
          "mode": "raw",
          "raw": "{ ... example body ... }",
          "options": { "raw": { "language": "json" } }
        }
      }
    }
  ]
}
```

## Endpoint Naming Convention

Derive endpoint names from the route handler function name, converted to title case:
- `get_all_agents` -> "Get All Agents"
- `upsert_agent` -> "Upsert Agent"
- `delete_agent` -> "Delete Agent"

## Request Body Generation Rules

- For `Dict[str, Any]` bodies: inspect field validations in the handler (e.g., `data.get("name")` checks) and the service method's `CREATED_ATTRS` / `UPDATABLE_ATTRS` to build a sample body with placeholder values.
- For Pydantic model bodies: extract fields, types, and defaults from the model class.
- Use realistic placeholder values: `"Example Name"` for strings, `1` for integers, `true` for booleans, `{}` for dicts.

## Auth Header Rules

Map auth dependencies to collection-level or request-level auth:
- `require_org_member` / `require_admin_or_owner` / `get_jwt_claims` -> Bearer token auth using `{{authToken}}` variable.
- No auth dependency -> No auth on that request.

## Output Rules

- Write valid JSON with 2-space indentation.
- One collection file per controller/router file.
- File naming: `{controller_name}.postman_collection.json` (e.g., `agents.postman_collection.json`).
- Prefix all URL paths with `/api/v1` followed by the router prefix from `main.py`.
