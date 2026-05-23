---
name: backend_form
description: Analyze a codebase (backend schema + frontend code) and emit FORM metadata JSON for entities that exist in the DB but DO NOT yet have a frontend create/edit UI. Pairs with [[backend_tables]]. Decides layout (page / drawer / modal / stepper) based on entity complexity, derived from the actual schema. Always asks the user where the backend and frontend live before scanning. Produces ONLY metadata — never database models, never migrations, never API endpoints. Fully project-agnostic; nothing hardcoded.
---

# backend_form — Form metadata producer (codebase-aware)

Discovers which entities have a DB definition but no frontend create/edit UI yet, and emits a **FORM metadata JSON** block for each gap. Pairs with [[backend_tables]]; both skills write to the same `entities.json` under their own key.

Project-agnostic. **No paths, framework names, entity names, layouts, or endpoint patterns are hardcoded.** Every value is derived by inspecting the actual codebase, after asking the user where to look.

## Hard constraints

- **DO NOT generate** database models, migrations, API endpoints, controllers, Pydantic / Zod / TypeBox schemas, validators, or any executable code.
- **DO NOT emit metadata** for entities that already have a create/edit UI.
- **DO NOT scan** the repo for backend/frontend code paths blindly — **always ask the user first** which directories to inspect.
- **DO NOT assume** any framework, file naming convention, route prefix, or directory structure.
- **ONLY output** JSON metadata, merged into a metadata file at a user-confirmed path.

If the user asks for code, redirect: "This skill produces metadata only."

## Step 1 — Ask the user where things live

Before scanning anything, ask up to four short questions (combine into a single prompt). Don't proceed until answered.

1. **Backend root directory** — where the database models / schema live (absolute or repo-relative path).
2. **Frontend root directory** — where the UI code lives. If the user says "no separate frontend", scope frontend discovery to the backend root.
3. **Metadata output path** — where to write `entities.json`. If no preference, propose `<repo_root>/metadata/entities.json` and let them confirm or override.
4. **Scope hint (optional)** — feature name or list of entities to focus on. Blank = scan everything.

Do not guess based on directory names alone. Ask. If the user already answered these for [[backend_tables]] in the same conversation, reuse those answers and don't re-ask.

## Step 2 — Detect the backend stack inside the supplied path

Inside the backend root, identify the schema source by inspecting file contents (not just filenames):

- SQLAlchemy: classes with `__tablename__`, `from sqlalchemy ...`.
- Django: subclasses of `models.Model`.
- Prisma: `.prisma` with `model X {}` blocks.
- Drizzle / TypeORM / Sequelize: TS exporting `pgTable(...)`, `@Entity()`, `Model.init(...)`.
- Raw SQL DDL: `CREATE TABLE` statements.
- Markdown spec: tables documented in markdown.

If multiple sources coexist, ask which is authoritative. If none, ask the user to point at the schema.

Extract every entity and its columns. Call this set **B**.

## Step 3 — Detect the frontend stack inside the supplied path

Identify how routes/components are organized inside the frontend root. Don't assume conventions — use what's actually present.

## Step 4 — Inventory the frontend's existing forms (set F_form)

Within the frontend root, identify entities that already have a create or edit UI. Combine these signals:

- **Component / file names** that include the entity plus a form-shape suffix (e.g. `Form`, `Create`, `Edit`, `New`), in whatever casing the project uses.
- **Route definitions** that look like create/edit routes for an entity.
- **API mutations** (POST / PATCH / PUT) targeting an endpoint that corresponds to the entity — whatever HTTP client / data-layer the project uses.
- **Validation schemas** named after the entity (Zod / Yup / Valibot / etc.).
- **Existing metadata entries** in the output file: any entity already keyed with a `form` block is considered in progress.

Normalize entity names. Match the project's pluralization style.

Set of frontend-implemented forms = **F_form**.

## Step 5 — Compute the gap

```
Targets = B − F_form
```

If the user supplied a scope hint, intersect Targets with that scope.

- Targets empty → print "No missing forms detected." and stop.
- 1–3 → proceed.
- 4+ → list them and ask the user which to include.

## Step 6 — Emit `form` metadata for each entity in Targets

Use the contract below. Every value is derived from the supplied schema and the supplied frontend code.

### `form` block contract

```json
{
  "entity": "<from schema>",
  "display_name": "<derived>",
  "submit_endpoint":         "<derived: see Endpoint detection>",
  "submit_method":           "POST",
  "initial_values_endpoint": null,
  "update": {
    "submit_endpoint":         "<derived>/{id}",
    "submit_method":           "PATCH",
    "initial_values_endpoint": "<derived>/{id}"
  },
  "layout": {
    "container":  "<derived: see Layout decision>",
    "form_style": "<derived>",
    "size":       "<derived>",
    "submit_label": "Save",
    "cancel_label": "Cancel"
  },
  "invalidate_query_keys": [ ["<entity_plural>"], ["<entity_singular>", "{id}"] ],
  "sections": [
    {
      "key":   "main",
      "title": "<derived>",
      "description": null,
      "step_label":  null,
      "fields": [
        {
          "key":   "<column_name>",
          "label": "<Title Case>",
          "type":  "<from fixed set; mapped from schema column>",
          "required": true,
          "default": null,
          "placeholder": null,
          "help_text": null,
          "ai_assist": false,
          "validation": { "max_length": 255 },
          "reference": { "entity": "<FK target>", "value_key": "id", "display_key": "<derived>", "options_endpoint": "<derived>" }
        }
      ]
    }
  ]
}
```

### Fixed field `type` set

`string`, `textarea`, `integer`, `float`, `boolean`, `datetime`, `date`, `enum`, `reference`, `multi_reference`, `json`, `file`, `password`, `slider`

### Column → field type mapping (derive from schema's native types)

| Schema column                                  | `type`            | Notes                                                  |
|------------------------------------------------|-------------------|--------------------------------------------------------|
| short string NOT NULL                           | `string`          | `required: true`, fill `validation.max_length`         |
| short string nullable                            | `string`          | `required: false`                                      |
| long text                                        | `textarea`        | If name reads like description/prompt/instruction/notes, set `ai_assist: true` |
| integer                                          | `integer`         |                                                        |
| numeric / float                                   | `float`           |                                                        |
| boolean                                          | `boolean`         | Pull default from schema                               |
| timestamp (user-editable)                         | `datetime`        | Rare                                                   |
| date-only                                         | `date`            |                                                        |
| JSON / JSONB (structured, known keys)             | Expand to fields  | Prefix sub-fields with `<col>.`; add `_jsonb_merge_keys` |
| JSON / JSONB (free-form)                          | `json`            |                                                        |
| FK reference NOT NULL                              | `reference`       | `required: true`                                       |
| FK reference nullable                              | `reference`       | `required: false`                                      |
| M2M / junction                                     | `multi_reference` | Submitted as array of IDs                              |
| enum / CHECK / Literal                             | `enum`            | Pull options from constraint                           |
| encrypted / hashed column                          | `password`        | Write-only; empty on update = keep                     |
| file URL / blob reference                          | `file`            |                                                        |
| primary key, tenant ID, audit timestamps           | **Omit**          | System-managed                                         |
| soft-delete column                                 | **Omit**          | System-managed                                         |

### Detecting structured JSON

If a JSON column has known keys (visible in models / fixtures / docs in the supplied paths), expand into prefixed sub-fields and add `_jsonb_merge_keys: ["<col>"]`. Otherwise emit a single `json` field.

### Sectioning rules

- 1 section ("main") when ≤6 fields and no logical grouping.
- 2+ sections when fields naturally split based on the schema (NOT NULL FKs + scalar settings + optional config blobs).
- Each section gets a short, human `title`.
- If `form_style: "stepper"`, fill `step_label` per section (`"1. <Title>"`, `"2. <Title>"`).

### Layout decision (derived from the actual schema)

Compute these from the schema:

- `N_fields` — total user-editable fields after column → field mapping.
- `N_sections` — number of section groups.
- `N_required_refs` — count of `required: true` `reference` fields.
- `has_password` — any `password` field.
- `has_file` — any `file` field.
- `has_many_to_many` — any `multi_reference` field.
- `has_self_reference` — any FK whose target is the same table.

Apply this matrix:

| Condition                                                       | `container` | `form_style` | `size` |
|-----------------------------------------------------------------|-------------|--------------|--------|
| `N_fields ≤ 3` and `N_required_refs ≤ 1`                         | `modal`     | `single`     | `sm`   |
| `N_fields 4–6` and `N_sections = 1`                              | `drawer`    | `single`     | `md`   |
| `N_fields 7–10` and `N_sections = 1`                             | `drawer`    | `single`     | `lg`   |
| `N_fields 4–10` and `N_sections 2–3`                             | `drawer`    | `single`     | `lg`   |
| `N_fields ≥ 11` and `N_sections ≤ 2`                             | `page`      | `single`     | `xl`   |
| `N_fields ≥ 11` and `N_sections ≥ 3`                             | `page`      | `stepper`    | `xl`   |
| `has_many_to_many` and `N_sections ≥ 2`                          | `page`      | `stepper`    | `xl`   |
| `has_password` and only secret-related fields                    | `modal`     | `single`     | `md`   |
| `has_self_reference` and `N_fields ≤ 4`                          | `modal`     | `single`     | `md`   |

When in doubt, default `drawer` / `single` / `md`.

If the frontend root already uses a consistent container pattern across its existing forms (e.g. every existing form is a drawer), prefer that pattern to stay consistent — detect from existing form components inside the supplied frontend root.

### `invalidate_query_keys`

- List query: `[["<entity_plural>"]]`.
- Detail query (update only): also `["<entity_singular>", "{id}"]`.
- If the entity has a NOT NULL FK to a parent: also `["<parent_plural>", "{parent_id}"]`.

`{id}` / `{parent_id}` are placeholders the frontend substitutes at runtime.

### Endpoint detection (do not hardcode any prefix)

- Match the prefix and pluralization actually in use elsewhere in the supplied backend root.
- Default `/<kebab-entity-plural>` and note the assumption only if no precedent is found.

### `reference.display_key` detection

For each `reference` field, look at the referenced entity's schema. Pick the first available column in this preference order:
`display_name`, `name`, `title`, `label`, `slug`, `code`, then the first non-PK string column. Fall back to `id`.

### `reference.options_endpoint` detection

`<list_endpoint_of_referenced_entity>?page_size=100`. If the referenced entity has an `is_active` flag, also append `&is_active=true`.

## Step 7 — Write to the user-confirmed output path

- If the file doesn't exist yet, create it with a `_meta` header.
- For each in-scope entity, add or replace **only the `form` key**.
- Leave the `table` key untouched.
- Preserve every other entry verbatim.

## Step 8 — Summarize

Print:
```
Backend root: <path>     stack: <detected>
Frontend root: <path>    stack: <detected>
Discovered: <N backend entities>, <M frontend forms>, <K missing>.
Emitted form metadata for: <list of K>.
Layouts: <entity → container/form_style/size>.
Output: <metadata file path>.
Run [[backend_tables]] for the matching table blocks if not done.
```

## What NOT to do

- Do not search the repo blindly — always ask for backend/frontend roots first.
- Do not emit metadata for entities that already have a create/edit UI.
- Do not invent field types outside the fixed set.
- Do not include secret/encrypted columns as readable values.
- Do not include primary keys, tenant IDs, or audit timestamps as user-editable.
- Do not hardcode endpoint paths, layouts, or entity names — derive everything from the supplied codebase.
- Do not generate `table` blocks — that's [[backend_tables]].
- Do not produce any executable code.
- Do not regenerate entries already present in the metadata file — preserve them.

## How the two skills work together (handoff to the frontend skill)

```
User: "Generate UI metadata for what's still missing."
Claude (backend side):
  1. Ask user for backend root, frontend root, output path. (Both skills share answers.)
  2. [[backend_tables]] → Targets_listing = B − F_listing → emits `table` blocks.
  3. backend_form     → Targets_form    = B − F_form    → emits `form` blocks.
  4. The merged entities.json is the deliverable.

Claude (frontend side, via the frontend skill):
  1. Reads each entry in entities.json.
  2. Renders the data table per `table` (columns, filters, layout container).
  3. Renders the form per `form` (sections, fields, container/form_style/size).
  4. Wires cache invalidation per `invalidate_query_keys`.
```

When run together, the two skills share user-provided paths and order doesn't matter — each only touches its own key.
