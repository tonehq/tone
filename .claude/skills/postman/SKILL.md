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

Each endpoint must include **comprehensive** example responses that cover all variations and edge cases. The goal is to produce collections rich enough that test case generation can use them as the source of truth.

### Required Examples per Endpoint Type

**For Upsert/Create endpoints:**
1. **One success example per type/provider/variant** — If the entity has a `type`, `provider`, `service_type`, `agent_type`, or similar discriminator field (including enum fields), include a separate Create example for EACH possible value. For example:
   - Channels: one Create example per ChannelType (TWILIO, EXOTEL, WEB, GOOGLE_MEET, ZOOM) — each with type-specific `meta_data`
   - Services: one Create example per service_type × provider combination (LLM/OpenAI, LLM/Anthropic, STT/Deepgram, STT/Google, TTS/ElevenLabs, TTS/OpenAI, TTS/Cartesia)
   - Models: one Create per service_type (llm, stt, tts) with provider-specific `meta_data`
   - Agents: one Create per AgentType (INBOUND, OUTBOUND, CHATBOT)
   - Voices: one Create per provider (ElevenLabs, OpenAI, Deepgram, Cartesia, Google)
   - Phone Numbers: one Create per provider (twilio, exotel)
2. **Update example** — with `id` or `uuid` to trigger the update path
3. **JSONB field variations** — If the entity has JSONB fields (meta_data, config, capabilities, etc.) that vary by type/provider, each Create example must show the correct JSONB structure for that type. To discover the correct structure:
   - Read the **service layer code** to see how `meta_data`/`config` is validated or used (e.g., `meta_data.get("account_sid")`)
   - Read **`dev/dev-data.json`** for seeded provider/model data with real meta_data structures
   - Read the **model** to see JSONB column definitions and defaults
4. **All validation error examples (400)** — Read the controller AND service code to find every `HTTPException(status_code=400)` raise. Create one example per distinct validation error (e.g., missing name, missing type, missing provider, missing required JSONB field).
5. **Not Found errors (404)** — For endpoints that look up by ID, include a Not Found example.
6. **Conflict errors (409)** — If the service raises `IntegrityError` or `HTTP_409_CONFLICT`, include examples for:
   - Duplicate name/unique constraint violations
   - Duplicate type (e.g., only one channel per type)
   - Resource already assigned (e.g., phone number already assigned to another agent)
7. **Set-as-default example** — If the entity supports `is_default`, include an example setting it to `true`.

**For List/Get-All endpoints:**
1. **Success** — With realistic data showing multiple items
2. **Filtered results** — One example per supported filter parameter (e.g., `?service_type=stt`, `?channel_id=1`)
3. **Empty result** — Returning `[]`

**For Get-By-ID endpoints:**
1. **Success** — With full response body
2. **Not Found (404)** — With the exact error message from the service code

**For Get-By-Type/Provider endpoints:**
1. **One success example per type/provider value** — Show realistic data for each
2. **Not Found (404)** — When no record exists for the given type
3. **Invalid type (400)** — If the service validates enum values

**For Delete endpoints:**
1. **Success** — With the exact success message from the service code
2. **Not Found (404)** — With the exact error message from the service code

**For Get-Default endpoints:**
1. **One example per type** (e.g., default LLM, default STT, default TTS)
2. **No default found (404)**

### How to Discover Correct Response Shapes

Do NOT guess response fields. Trace the actual code path:

1. **Read the controller** (`core/api/v1/{name}.py`) — Find the route handler and what service method it calls.
2. **Read the service** (`core/services/{name}_service.py`) — Find the service method and its return statement. This is the source of truth for response fields. Look for:
   - `_response_item()` methods that build the response dict
   - Direct ORM object returns (use the model's column definitions)
   - Joined queries that add extra fields (e.g., `service_provider_name` from a JOIN)
   - Different response shapes for different endpoints (e.g., `get_all` may return fewer fields than `get_one`)
3. **Read the model** (`core/models/{name}.py`) — For ORM object returns, use the model's column names as response fields.
4. **Check for enum value casing** — Enum `.value` often returns lowercase (e.g., `"inbound"` not `"INBOUND"`, `"twilio"` not `"TWILIO"`). Verify by reading the enum definition.

### Response Body Field Accuracy

- Use the **exact field names** from the service method return dict or ORM model columns
- Include **all fields** — don't omit nullable fields; show them as `null`
- Use **correct value types** — don't use strings for integers, don't use uppercase for lowercase enums
- For joined responses, include the joined fields (e.g., `service_provider_name`, `provider_type`)
- For flat responses (like agents), don't nest into sub-objects unless the code does

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
