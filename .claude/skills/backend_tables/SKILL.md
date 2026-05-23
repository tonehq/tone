---
name: backend_tables
description: Analyze a codebase (backend schema + frontend code) and emit TABLE metadata JSON for entities that exist in the DB but DO NOT yet have a frontend listing UI. Pairs with [[backend_form]]. Always asks the user where the backend and frontend live before scanning. Produces ONLY metadata — never database models, never migrations, never API endpoints. Fully project-agnostic; nothing hardcoded.
---

# backend_tables — Table metadata producer (codebase-aware)

Discovers which entities have a DB definition but no frontend listing yet, and emits a **TABLE metadata JSON** block for each gap. Pairs with [[backend_form]].

This skill is project-agnostic. **No paths, framework names, entity names, layouts, colors, or endpoint patterns are hardcoded.** Every value is derived by inspecting the actual codebase, after asking the user where to look.

## Hard constraints

- **DO NOT generate** database models, migrations, API endpoints, validators, or any executable code.
- **DO NOT emit metadata** for entities that already have a listing UI.
- **DO NOT scan** the repo for backend/frontend code paths blindly — **always ask the user first** which directories to inspect.
- **DO NOT assume** any framework, file naming convention, route prefix, or directory structure.
- **ONLY output** JSON metadata, merged into a metadata file at a user-confirmed path.

If the user asks for code, redirect: "This skill produces metadata only."

## Step 1 — Ask the user where things live

Before any scanning, ask up to four short questions (combine into one prompt). Don't proceed until answered.

1. **Backend root directory** — where the database models / schema live (absolute or repo-relative path).
2. **Frontend root directory** — where the UI code lives. If the user says "no separate frontend" or "same dir", scope frontend discovery to the backend root.
3. **Metadata output path** — where to write `entities.json`. If the user has no preference, propose `<repo_root>/metadata/entities.json` and let them confirm or override.
4. **Scope hint (optional)** — a feature name or list of entities they care about. If blank, scan everything.

If the user supplies a single directory for the whole repo, ask whether backend and frontend live there or in nested subdirs.

Do not guess based on directory names like `backend/` or `frontend/`. Ask.

## Step 2 — Detect the backend stack inside the supplied path

Inside the backend root only, look for the dominant schema source. Use the file contents to confirm — not the filenames alone.

- Files with `class ... __tablename__` / SQLAlchemy imports → SQLAlchemy.
- Files with `from django.db import models` / `Model` subclass → Django.
- `*.prisma` containing `model X` blocks → Prisma.
- `*.ts` exporting `pgTable(...)`, `sqliteTable(...)`, `@Entity()`, `Model.init(...)` → Drizzle / TypeORM / Sequelize.
- `*.sql` files containing `CREATE TABLE` → raw DDL.
- Markdown files describing tables → spec doc.

If multiple sources exist in the backend root, ask which is authoritative. If none, ask the user to point at the schema explicitly.

Extract every entity and its columns. Call this set **B**.

## Step 3 — Detect the frontend stack inside the supplied path

Inside the frontend root only, identify how the UI is organized. Look for one of:

- Next.js (`app/` or `pages/` routes).
- Vite + React (`src/routes`, `src/pages`, or a router config).
- Remix / TanStack Router / React Router (config files declaring routes).
- A Vue / Svelte / Angular project (note it, but the discovery logic still applies).
- An admin framework already in place (Refine, react-admin, etc.) — note it; the metadata still applies but the frontend skill will render differently.

Don't assume framework conventions. Use what's actually in the supplied directory.

## Step 4 — Inventory the frontend's existing listing UI (set F_listing)

Within the frontend root, identify entities that already have a listing implemented. Use any combination of these signals — combine, don't rely on a single one:

- **Route definitions** that mention an entity-shaped path (whatever the project's router uses).
- **Component / file names** that include the entity name plus a listing-shape suffix (e.g. `Table`, `List`, `Listing`, `Index`, `Grid`) in whatever casing the project uses.
- **Data-fetching calls** to an endpoint whose path corresponds to the entity (whatever the project's HTTP client looks like — fetch / axios / TanStack Query / SWR / RTK Query / GraphQL).
- **Type imports** of an entity type, co-located with components that render rows/columns.
- **Existing entries** in the metadata file: any entity already keyed there is considered in progress and is skipped (unless the user explicitly asks to refresh it).

Normalize entity names to a single canonical form for comparison (snake_case suggested). Account for pluralization differences visible in the codebase (look at how the project itself pluralizes — `categories`, `boxes`, etc. — and match it).

Set of frontend-implemented listings = **F_listing**.

## Step 5 — Compute the gap

```
Targets = B − F_listing
```

If the user supplied a scope hint, intersect Targets with that scope.

- Targets empty → print "No missing listings detected." and stop.
- Targets has 1–3 entries → proceed.
- Targets has 4+ entries → list them and ask the user which to include.

## Step 6 — Emit `table` metadata for each entity in Targets

Use the contract below. Every value is derived from the supplied schema and the supplied frontend code — nothing is taken from this skill file.

### `table` block contract

```json
{
  "entity": "<from schema>",
  "display_name": "<derived: Title Case from entity name>",
  "primary_key": "<from schema; default 'id' if not specified>",
  "default_sort": { "by": "<best timestamp column from schema, else primary key>", "dir": "desc" },
  "list_endpoint":      "<derived: see Endpoint detection — POST method>",
  "list_method":        "POST",
  "form_meta_endpoint": "<derived>/meta/form",
  "row_actions": ["<derived: see Row actions detection>"],
  "bulk_actions": [],
  "layout": {
    "container":  "<derived: page | inline | section>",
    "density":    "comfortable",
    "show_search":     true,
    "show_filters":    true,
    "show_pagination": true,
    "page_size_default": 20,
    "page_size_options": [10, 20, 50, 100]
  },
  "columns": [
    {
      "key": "<column_name from schema>",
      "label": "<Title Case>",
      "type": "<from the fixed set, mapped from the schema column type>",
      "sortable": true,
      "filterable": true,
      "searchable": false,
      "width": null,
      "align": "left",
      "options":   [ { "value": "<from constraint>", "label": "...", "color": "<from existing UI tokens if found>" } ],
      "reference": { "entity": "<from FK target>", "display_key": "<derived>", "filter_endpoint": "<derived>" }
    }
  ]
}
```

### Fixed column `type` set (frontend renders by this — DO NOT invent new values)

`string`, `text`, `integer`, `float`, `boolean`, `datetime`, `date`, `enum`, `reference`, `json`, `status_badge`

### Column-type mapping (derive from the schema's native types)

| Schema column shape                              | `type`         |
|--------------------------------------------------|----------------|
| short string                                      | `string`       |
| long text                                         | `text`         |
| integer                                           | `integer`      |
| numeric / float / decimal                         | `float`        |
| boolean                                           | `boolean`      |
| timestamp                                         | `datetime`     |
| date-only                                          | `date`         |
| JSON / JSONB                                      | `json`         |
| FK reference                                      | `reference`    |
| enum / CHECK / Literal whose name reads as status | `status_badge` |
| enum / CHECK / Literal otherwise                  | `enum`         |
| encrypted / hashed / secret column                | **omit**       |
| soft-delete column                                | **omit**       |

For `status_badge` color hints: if the frontend root already contains status-color conventions (Tailwind classes, theme tokens, badge components), reuse them. Otherwise leave `"color": null` and let the frontend skill assign defaults.

### Column selection (derived, not hardcoded)

- Include columns a user would meaningfully scan in a listing: name/label fields, status, key FKs, booleans, primary timestamp.
- Skip: primary keys, tenant IDs (any FK whose target appears to represent an org/workspace/account), `updated_at`, `deleted_at`, secrets, large JSONB.
- Cap at ~6 columns. The detail page handles the long tail.

### `searchable` / `filterable` / `sortable` defaults

- `searchable: true` only for `string`/`text` that reads as a name, label, code, or description.
- `filterable: true` for: `boolean`, `enum`, `status_badge`, `reference`, `date`/`datetime`, low-cardinality strings.
- `sortable: true` for: `string` (name-like), `integer`, `float`, `datetime`, `date`, `enum`, `status_badge`. Never: `text`, `json`, `reference`.

### `layout.container` heuristics

- `inline` — entity has a NOT NULL FK to a single parent and isn't listed standalone in the frontend root.
- `section` — entity is referenced only from dashboards/reports based on existing UI usage.
- `page` — default, top-level listing.

If uncertain, use `page`.

### `row_actions` detection (derived from schema features)

- `["view", "edit", "delete"]` — entities with soft-delete or `is_active` flag.
- `["view", "edit"]` — pure lookup tables.
- `["view", "cancel", "delete"]` — entities with a `status` enum that includes terminal states (`completed`/`failed`/`cancelled`).
- `["edit", "delete"]` — entities containing any secret column.

### Endpoint detection (do not hardcode any prefix)

- Inspect the backend root for how routes are registered. Extract the prefix pattern actually in use.
- If the project uses a versioned API prefix (whatever it is), match it.
- Pluralization: kebab-case the entity name and use the pluralization style visible elsewhere in the routes.
- **List endpoints use POST** with a `/list` suffix — e.g. `POST /<entity>/list`. Filter, sort, and pagination params go in the JSON request body, not query params.
- If no precedent: default to `/<kebab-entity-plural>/list` (POST, no `/api/` prefix unless evidence supports it) and note the assumption in the summary.

## Step 7 — Write the metadata file at the user-confirmed output path

- If the file doesn't exist yet, create it with a `_meta` header:
  ```json
  { "_meta": { "version": "1.0.0", "generated_for": "<inferred from repo root name>" } }
  ```
- For each in-scope entity, add or replace **only the `table` key** under that entity.
- Leave the `form` key untouched (it belongs to [[backend_form]]).
- Preserve every other entry in the file verbatim.

## Step 8 — Summarize

Print:
```
Backend root: <path>     stack: <detected>
Frontend root: <path>    stack: <detected>
Discovered: <N backend entities>, <M frontend listings>, <K missing>.
Emitted table metadata for: <list of K>.
Output: <metadata file path>.
Run [[backend_form]] to emit the matching form blocks.
```

## What NOT to do

- Do not search the repo for backend/frontend paths without asking the user first.
- Do not emit metadata for entities that already have a listing in the frontend.
- Do not invent column types outside the fixed set.
- Do not expose secret / encrypted / hashed columns.
- Do not hardcode endpoint paths, layouts, colors, or framework conventions — derive everything from the codebase being analyzed.
- Do not regenerate entries already present in the metadata file — preserve them.
- Do not produce `form` metadata — that's [[backend_form]].
- Do not produce any executable code.

## How to call this skill in practice

```
User: "Generate listing metadata for whatever's still missing."
Claude:
  1. Ask: backend root? frontend root? output path? scope?
  2. Detect stacks inside the supplied paths.
  3. Build B (backend entities) and F_listing (frontend listings).
  4. Targets = B − F_listing. Confirm with user if large.
  5. Emit a `table` block per target. Merge into entities.json.
  6. Print the summary. Recommend running [[backend_form]] next.
```
