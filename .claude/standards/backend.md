# <repo> — backend specifics (repo-local, shared)

THIS repo's real layers, names, and helpers — **shared by both `plan-mode` (when planning) and
`code-review` (when reviewing)**. Supplements the generic **`backend-standards`** skill; where it
differs, **this wins**. When planning, follow it; when reviewing, flag hand-rolled duplicates of these
names. Fill it in with your repo's reality (delete the placeholders). **Delete this file if the repo has
no backend.**

## Layout (where things go)

```
<the repo's real backend layers — e.g.
 api/<version>/<entity>/controller.py + deps.py + rbac.py
 services/{base.py, crud.py, <domain>_service.py, <kind>_rules/}
 models/{base.py mixins, <entity>.py}   schemas/   workers/   core/   db/   config.py   main.py
 <migrations>/versions/   tests/>
```

## Mandatory patterns (repo names)

- **Tenancy:** tenant key = `<organization_id / workspace_id>`, resolved by `<get_org_id>`; scope every
  query via `<BaseService.query(...)>`. (Skip this whole line if the repo is not multi-tenant.)
- **Services:** extend `<BaseService>`; use the shared CRUD helpers `<create_record / get_or_404 / …>` —
  never hand-roll a tenant filter, id lookup, or pagination.
- **Authorization:** `<require_permission(Permission.X) / require_role(Role.Y)>` — narrowest that fits.
- **Endpoint shape:** thin controller — deps (`<session → tenant → authz → validated body>`) + one
  service call + `<.to_dict()>` (never the ORM object).
- **Lists:** `<POST /<entity>/list>` uses `<ListRequest>` and returns `<{items, total, page, page_size}>`.
- **Strategy over `if/elif`:** branch on a "kind" via `<services/<kind>_rules/ (ABC + one file per kind + factory)>`.
- **Schemas:** `<Pydantic v2>` in `<app/schemas/<domain>.py>`.

## Repo-specific DON'Ts (on top of the generic backend-standards)

- <e.g. No `<Celery>` — background work is `<subprocess workers under app/workers/>`, each with its own session.>
- <e.g. Datetimes via `<utcnow()>` (tz-aware UTC); env only via `<config.py settings>`; traceback logging on every except.>

## Migrations & API contract

- Migration tool: `<Alembic — backend/alembic/versions/>`. Additive-nullable-first, reversible `downgrade`,
  index new filtered columns, **deploy-safe expand → migrate → contract**, migration ships with the model change.
- Up/down check: `<alembic upgrade head; alembic downgrade -1>`.
- **API contract:** OpenAPI spec at `<app/openapi.json / docs/openapi.yaml>` (omit if none); Postman
  collection named in code-review's `config.md` `postman:`. code-review diffs API changes against both, read-only.
