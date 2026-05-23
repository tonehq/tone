---
name: implement_feature_from_prd
description: Top-level orchestrator that reads a Feature PRD at `docs/features/<slug>.md` and runs the right downstream code-gen skills (backend_form, backend_tables, form_page, table_page, frontend_forms, frontend_tables, frontend_cards) in the correct order to scaffold a feature end-to-end. Inspects the PRD's Section 6 (DB schema), Section 7 (API design), Section 8 (backend), and Section 9 (frontend) to decide what to generate — create/edit endpoints + form UI, list endpoints + table or card UI, or both. Surfaces any "⚠ Conventions Check" flags from the PRD before running and confirms with the user. Always runs `/generate_feature_prd_and_implementation` first if no PRD exists for the requested slug. Output is generated code in `backend/app/`, `frontend/app/`, `frontend/lib/`, plus a checklist of manual follow-ups (Alembic migration, Postman updates, integration tests).
---

# implement_feature_from_prd — Feature scaffolding orchestrator

This skill takes a feature PRD as input and **scaffolds the code** — backend endpoints, frontend pages, components, hooks — by running the right code-gen skills in the right order. It is the bridge between `/generate_feature_prd_and_implementation` (which only writes docs) and the production codebase.

**This skill writes production code.** It delegates to the downstream skills; it does not duplicate their logic.

---

## When to invoke

- "Implement feature X" / "Scaffold the agents feature from the PRD" / "Build out webhooks from the doc"
- After running `/generate_feature_prd_and_implementation` and the user wants to turn the spec into code
- When the user types `/implement_feature_from_prd <slug>` directly

If the user names a feature but doesn't pass a slug, ask for it. If `docs/features/<slug>.md` does not exist, tell the user and run `/generate_feature_prd_and_implementation` first to author the PRD.

---

## Inputs

1. **Feature slug** (required) — kebab-case identifier matching a file in `docs/features/`. Verify the file exists; if not, exit with a message pointing the user at `/generate_feature_prd_and_implementation`.

2. **Implementation scope** (optional, ask if ambiguous):
   - `full` (default) — backend + frontend + everything the PRD describes
   - `backend-only` — endpoints + models only
   - `frontend-only` — UI only; assume backend exists
   - `forms-only` — just create/edit
   - `listing-only` — just the list view

---

## Phase 1 — Load and parse the PRD

1. Read `docs/features/<slug>.md` in full.
2. Extract these sections by heading:
   - **§1 Overview** → human context for log output
   - **§4 Non-functional requirements** → check for any RBAC / multi-tenancy notes
   - **§6 Data model / DB schema** → tables, columns, indexes, FKs
   - **§7 API design** → endpoint table; identify CREATE / UPDATE / LIST / DELETE shapes
   - **§8 Backend implementation** → controller / service paths, CRUD-helper usage
   - **§9 Frontend implementation** → routes, **layout mode (modal / drawer / page)**, **listing component (CustomTable vs cards)**
3. Find every `⚠` marker. Print these to the user **before running anything** — they may indicate the PRD itself flags something risky (missing RBAC, orphaned endpoints, schema drift). Ask the user whether to proceed, fix the PRD first, or run anyway and add `⚠`-tagged TODOs in the generated code.

If §6/§7/§8/§9 are empty or marked `_(not specified)_`, stop and tell the user the PRD needs more detail — re-run `/generate_feature_prd_and_implementation` and update those sections before scaffolding code.

---

## Phase 2 — Decide what to run

From the parsed PRD, decide which generators apply. Default mapping:

| PRD signal | Skills to run | Order |
|------------|---------------|-------|
| §7 has `POST /<entity>` (create) and/or `PATCH /<entity>/{id}` (update) | `/backend_form` → `/form_page` | 1 |
| §7 has `POST /<entity>/list` or `GET /<entity>` (paginated) | `/backend_tables` → `/table_page` | 2 |
| §9 says listing is **card-grid** (e.g. references `frontend_cards`, mentions cards, references `/test-profiles` pattern) | use `/frontend_cards` **instead of** `/table_page` | 2 |
| §6 declares a new table that does not yet have a model file in `backend/app/models/` | Flag — generate a placeholder model + Alembic migration command, OR ask the user to create them first |
| §7 has only `GET` endpoints (read-only feature like Providers, Analytics) | Skip form / table generators; print a TODO that the controller must be hand-written |

Layout choice for forms (`modal | drawer | page`):
- Pull from §9 if explicitly stated.
- Otherwise inspect §6: ≤3 writable fields → modal; 4–10 → drawer; 11+ → page.
- Confirm with the user before running `/form_page`.

Listing choice:
- Default: `/table_page` (uses `CustomTable`).
- If §9 mentions "card", "tile", "grid", or references `frontend_cards`/test-profiles pattern → `/frontend_cards`.
- Confirm with the user.

---

## Phase 3 — Pre-flight check

Before invoking any downstream skill, verify these prerequisites in the codebase:

1. **Model file** — `backend/app/models/<entity>.py` exists and matches §6. If missing, stop and ask the user to create it (or generate a stub based on §6 and ask for confirmation).
2. **Router wiring** — `backend/app/api/v1/router.py` includes the feature's router. If missing, add the import + `api_router.include_router(...)` line.
3. **Alembic migration** — print the exact command for the user to run after model changes: `cd backend && alembic revision --autogenerate -m "<slug>"`. Do not run it automatically.
4. **Convention check** — confirm the PRD's chosen approach respects RULES.md / CLAUDE.md (multi-tenancy filter by `organization_id`, RBAC via `require_permission`, soft delete, `.to_dict()` serialization, CRUD helpers from `app.services.crud`, React Query for server state, Zustand for client state, `lib/toast`).

---

## Phase 4 — Run the downstream skills

Invoke the chosen skills in this order:

1. **Backend metadata generators** (if needed): `/backend_form` and/or `/backend_tables` — pass the entity name and point at `backend/app/models/<entity>.py`. These emit FORM/TABLE metadata JSON used by the UI generators.
2. **Parent orchestrators**: `/form_page` (for create/edit) and/or `/table_page` (for listing) — these run backend + frontend generators together. Pass: entity name, layout mode (for `/form_page`), parent route (if modal/drawer).
3. **Listing variant** (if cards): `/frontend_cards` instead of `/table_page`.
4. **Standalone frontend** (if backend already exists): `/frontend_forms` / `/frontend_tables` / `/frontend_cards`.

Use the metadata files (if produced by `/backend_form` / `/backend_tables`) as input to the frontend generators when possible — that keeps backend and frontend in sync.

---

## Phase 5 — Manual follow-ups checklist

After all generators finish, print a TODO list for the user:

```
✅ Scaffolded <feature> from docs/features/<slug>.md

Generated:
- Backend endpoints: <list of paths from §7>
- Backend files: <controller, service, model paths>
- Frontend routes: <list of routes from §9>
- Frontend files: <page.tsx, components, lib/api/<slug>.ts paths>

⚠ Manual follow-ups required:
- [ ] Run Alembic migration: `cd backend && alembic revision --autogenerate -m "<slug>"` then `alembic upgrade head`
- [ ] Add Postman requests to `postman/Tone-Test-API.postman_collection.json` (see §10 of the PRD)
- [ ] Write integration tests under `backend/tests/test_<slug>_journey.py` (mirror the Given/When/Then blocks in §5 of the PRD)
- [ ] Wire RBAC: add `require_permission("<entity>:<action>")` to each new endpoint (per RULES.md)
- [ ] Smoke-test in the dev environment (`uvicorn app.main:app --reload` + `npm run dev`)
- [ ] Update the PRD's Change Log: re-run `/generate_feature_prd_and_implementation` against this feature once smoke-tests pass

If anything generated diverges from the PRD, update the PRD via `/generate_feature_prd_and_implementation` — the PRD is the contract; code is downstream.
```

---

## Hard rules

- **Never deviate from the PRD.** If the PRD says `modal`, do not silently emit a page. If a field is in §6, it must be in the form. If §7 lists an endpoint, generate it.
- **Never invent fields or endpoints** that the PRD does not describe. If something is missing or ambiguous, stop and ask the user (or instruct them to update the PRD first).
- **Never skip the pre-flight check.** Missing model file, unwired router, or convention violations should pause execution.
- **Never run the Alembic migration automatically.** Print the command; let the user run it after reviewing the autogenerated revision.
- **Always respect `⚠` flags in the PRD.** Surface them to the user before running. Insert `// ⚠ TODO from PRD:` comments in generated code where the PRD flags an open issue (e.g. "RBAC missing on this endpoint").
- **Always update the PRD afterward** if the implementation diverged. The PRD is the source of truth.

---

## Failure modes

- **PRD file not found** → tell the user and offer to run `/generate_feature_prd_and_implementation`.
- **PRD sections empty** → name the empty sections and ask the user to fill them in before continuing.
- **Model file missing** → print §6 of the PRD and ask the user to create the model file (or confirm a stub).
- **Conflicting frontend routes** (a file already exists at the target path) → diff against the PRD; ask the user whether to overwrite, merge, or skip.
- **Downstream skill error** → surface the error verbatim; do not retry silently.
