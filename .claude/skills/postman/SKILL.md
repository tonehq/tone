---
name: postman-collection-generator
description: Generate and maintain Postman collections from FastAPI route files. Use when the user asks to create Postman collections, export APIs to Postman, update Postman collections, or sync API changes to Postman format. Triggers on requests mentioning "Postman", "API collection", or "export APIs".
---

# Postman Collection Generator

Generate Postman v2.1 collections by reading FastAPI router files. Produce one collection per controller (router file) with all its endpoints fully configured.

## Core vs EE Handling

This project has two editions — **Core** (`core/api/v1/`) and **EE** (`ee/api/v1/`). A single `main.py` handles both: it checks `is_ee_enabled()` at startup and loads either core or EE routers (never both). The edition is determined by the license key and whether the `ee/` folder exists.

Both editions share the same API paths (`/api/v1/...`) and request/response formats. The only differences are:
- **Auth guards** — EE uses `require_ee_org_member` / `require_ee_admin_or_owner` instead of core equivalents (internal, not visible in the API).
- **Org context** — EE passes `org_id` (UUID) internally for multi-tenancy.
- **A few EE-only endpoints** — e.g., `switch_organization`, `get_associated_tenants`, `create_tenants`, `request_access`.

From Postman's perspective, the request is identical for both editions — same URLs, same server, same port. Which controllers handle it depends on the server's edition.

**Rules:**
- Maintain a **single collection per controller** — do NOT create separate core and EE collections.
- Use the **core controller** (`core/api/v1/`) as the primary source for generating collections.
- Also check the **EE controller** (`ee/api/v1/`) for any extra endpoints not in core. Add those to the same collection with an `[EE]` prefix in the endpoint name (e.g., `[EE] Switch Organization`).
- Each controller file gets its own collection — do NOT merge different controllers into one collection (e.g., `agent_channel_phone_numbers` and `channel_phone_numbers` are separate controllers and must have separate collection files).

## Inputs

The user provides:
1. **Source path** — A single file or directory containing FastAPI router files (e.g., `core/api/v1/`).
2. **Output directory** — Where to write the generated `.json` collection files (default: `postman_collection/`).

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

## Subsequent Run Workflow (Incremental Update)

On subsequent runs, use the **`find-impacted-apis` skill** (`.claude/skills/find-impacted-apis/`)
to detect which endpoints have changed. Do NOT implement custom git diff logic — delegate
change detection entirely to that skill.

### Step 1: Run find-impacted-apis to Detect Changes

Use the `analyze_diff.py` script from `.claude/skills/find-impacted-apis/`:

```bash
python .claude/skills/find-impacted-apis/analyze_diff.py \
  --project-path . \
  --auto \
  --output postman_collection/
```

This produces:
- `postman_collection/impacted-apis-report.json` — structured data with all changed endpoints, services, and models
- `postman_collection/impacted-apis-report.md` — human-readable summary

If this is the first run of `find-impacted-apis` (no state file at
`~/.claude-skills/find-impacted-apis/last_run.json`), you can either:
- Ask the user for a commit range, OR
- Fall back to a full run (regenerate all collections from scratch)

**If the report shows zero impacted endpoints → report "No API changes detected" and stop.**

### Step 2: Parse the Impact Report

Read `postman/impacted-apis-report.json` and extract:

```
1. impacted_endpoints[] — list of {method, path, function, file, change_type}
   - change_type is "added", "modified", or "deleted"

2. files_changed[] — list of {file, status, lines_added, lines_removed}
   - Use this to identify which controller files need collection updates

3. Group the impacted endpoints by their controller file
   - e.g., all endpoints from core/api/v1/agents.py → agents.postman_collection.json
```

### Step 3: Update collections

For each controller file that has impacted endpoints:

1. Read the **current file contents on disk** (captures both committed and uncommitted state).
2. Re-parse the file using the same extraction logic from the First Run Workflow.
3. Load the existing collection JSON for that controller.
4. Compare endpoints in the parsed file against those in the existing collection:
   - **New endpoints** (from impact report with `change_type: "added"`) → add them to the collection.
   - **Modified endpoints** (`change_type: "modified"`) → update their parameters, body, and description.
   - **Removed endpoints** (`change_type: "deleted"`) → remove them from the collection.
5. Write the updated collection file.

> **Note:** The `find-impacted-apis` skill handles both committed AND uncommitted changes,
> state tracking, and dependency chain analysis. Its state is stored at
> `~/.claude-skills/find-impacted-apis/last_run.json`. There is no need for a separate
> `postman/.last_run` file.

---

## Cross-Referencing Other Skills

### find-impacted-apis (`.claude/skills/find-impacted-apis/`)
- **Change detection engine.** On subsequent runs, identifies exactly which endpoints changed.
- Uses `analyze_diff.py` and maintains its own state at `~/.claude-skills/find-impacted-apis/last_run.json`.
- Produces `impacted-apis-report.json` which this skill consumes to know which collections to update.
- **Do NOT reimplement change detection.** Always delegate to this skill.

## Collection Structure (Postman v2.1 Format)

Each generated collection must follow this structure. Every endpoint item MUST include both a `request` and a `response` array with example responses (success case + relevant error cases).

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
      },
      "response": [
        {
          "name": "{Endpoint Description} - Success",
          "originalRequest": { "...same as request above..." },
          "status": "OK",
          "code": 200,
          "header": [
            { "key": "Content-Type", "value": "application/json" }
          ],
          "body": "{ ... example success response body ... }"
        },
        {
          "name": "{Endpoint Description} - {Error Case}",
          "originalRequest": { "...request with invalid data..." },
          "status": "Bad Request",
          "code": 400,
          "header": [
            { "key": "Content-Type", "value": "application/json" }
          ],
          "body": "{ \"detail\": \"error message\" }"
        }
      ]
    }
  ]
}
```

## Response Example Rules

Each endpoint must include example responses:
- **Success response** — Always include at least one 200/201 success example with realistic response body.
- **Error responses** — Include examples for validation errors (400) found in the handler (e.g., missing required fields), not-found errors (404) if applicable, and auth errors if the endpoint requires specific roles.
- **Multiple success variants** — For upsert endpoints, include both "Create" and "Update" success examples.
- Infer response body structure from the service method return or the model's fields. Use realistic placeholder values consistent with the request body examples.

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
- Core: `require_org_member` / `require_admin_or_owner` / `get_jwt_claims` -> Bearer token auth using `{{authToken}}` variable.
- EE: `require_ee_org_member` / `require_ee_admin_or_owner` / `get_ee_jwt_claims` -> Same Bearer token auth (the JWT format differs but the header is identical).
- No auth dependency -> No auth on that request (set `"auth": { "type": "noauth" }` at the request level).

## Output Rules

- Write valid JSON with 2-space indentation.
- One collection file per controller/router file. Never merge different controllers into one file.
- File naming: `{controller_name}.postman_collection.json` (e.g., `agents.postman_collection.json`).
- Output directory: `postman_collection/` (not `postman/`).
- Prefix all URL paths with `/api/v1` followed by the router prefix from `main.py`.
- Single collection per controller covers both core and EE. EE-only endpoints are prefixed with `[EE]` in the name.
