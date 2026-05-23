---
name: generate_feature_prd_and_implementation
description: Interactively author or update a Feature PRD for the Tone-Test platform. Walks the user section-by-section through requirements, edge cases, test cases, DB schema, API design, backend (controllers + services), frontend (routes + components), and Postman examples. Emits ONE artifact — a team-readable Markdown PRD at `docs/features/<feature-slug>.md`. On re-invocation against an existing feature, detects the prior PRD, asks which sections to update, merges, and appends a dated entry to the Change Log. Always ends with a "Next steps" block linking to downstream code-gen skills ([[implement_feature_from_prd]], [[table_page]], [[form_page]], [[backend_form]], [[backend_tables]], [[frontend_forms]], [[frontend_tables]], [[frontend_cards]]) — those skills read the PRD as their input.
---

# generate_feature_prd_and_implementation — Feature PRD authoring

This is the **first skill you run when starting a new feature** (or modifying an existing one) in the Tone-Test platform. It produces a single source of truth — a PRD that captures requirements, edge cases, DB/API/UI implementation details, and Postman examples — as a Markdown file under `docs/features/`.

Once a PRD exists, downstream skills consume it:

- [[implement_feature_from_prd]] — orchestrator that reads the PRD and runs the right code generators
- [[form_page]] / [[backend_form]] / [[frontend_forms]] — create/edit forms
- [[table_page]] / [[backend_tables]] / [[frontend_tables]] — listings
- [[frontend_cards]] — card-grid listings

**This skill writes documentation only. It never writes production code.**

---

## When to invoke

Run this skill when the user says any of:

- "Let's start a new feature"
- "Document this feature before we build it"
- "Generate a PRD for X"
- "Update the PRD for X"
- "Add edge cases / test cases / new endpoints to the X feature spec"

If a feature is **modified** in code, the user should re-invoke this skill to refresh its PRD — the PRD is the contract downstream skills rely on.

---

## Inputs the skill ALWAYS asks for first

Before walking through sections, ask:

1. **Feature name** — short human label (e.g. "Webhook Retry Queue", "Agent Personality Editor"). Convert internally to kebab-case slug (`webhook-retry-queue`, `agent-personality-editor`).
2. **New or update?** — auto-detect by checking if `docs/features/<slug>.md` already exists. If it exists, treat as update.
3. **One-line summary** — what does this feature do, in plain language?
4. **Expected outcomes** — what does "done" look like? (Captured into the user-stories / test-cases sections later.)

If updating: read the existing PRD first, list its sections, and ask **which sections the user wants to modify**. Only walk through those sections interactively. Append a new entry to "Change Log" with today's date (use the current date from environment context) and a one-line summary of what changed.

---

## Interactive walkthrough — section by section

For each section below, ask one focused question (or a small batch of tight questions). Do not dump the whole template at once. Capture answers, then move on. If the user says "skip" or "n/a" for a section, write `_(not specified)_` in that section but keep the heading.

### Section 1 — Overview

Ask: "What is this feature, who is it for, and what problem does it solve?"

Capture: one-paragraph description; target user/role; problem statement / motivation.

### Section 2 — User stories & use cases

Ask: "Give me 2–5 user stories in the form 'As a <role>, I want <action>, so that <outcome>.' Add any concrete use cases or flows."

### Section 3 — Functional requirements

Ask: "What must this feature do? List each requirement as a bullet. Be specific."

Then ask the follow-up: **"What are the edge cases and failure modes?"** Capture each as a sub-bullet. Edge cases to probe for explicitly: empty/null inputs, duplicates, concurrent writes, org isolation (multi-tenancy), permission boundaries (RBAC), pagination limits, rate limits / quotas, external service failures (LLM, telephony, S3), partial failures.

### Section 4 — Non-functional requirements

Ask about each that's relevant; skip ones the user says don't apply: performance budget; security / compliance; multi-tenancy enforcement points; observability (logs, metrics, alerts); backward compatibility.

### Section 5 — Test cases (requirements-as-tests)

Ask: "Write the test cases that would prove this feature is done. Either pseudocode or plain-English Given/When/Then. These lock the requirements down."

Capture each as:
```
TEST: <short name>
  GIVEN <preconditions>
  WHEN  <action>
  THEN  <expected result>
```

### Section 6 — Data model / DB schema

Ask: "What database changes does this feature need?" For each new/modified table capture: name; columns (name, type, nullable, default, constraints); indexes; relationships; migration notes.

Reference `backend/app/models/` for existing model conventions. Every table in this project has `organization_id` for multi-tenancy and soft-delete columns — confirm the new table follows the same pattern, and flag if it doesn't.

### Section 7 — API design

Ask: "What endpoints does this feature expose?" For each endpoint capture: method + path (under `/api/v1/`); auth requirement; required permission (cite the `require_permission(...)` call); request shape; response shape (always `.to_dict()` per RULES.md); pagination shape for list endpoints; WebSocket events emitted on `/ws/{org_id}`.

### Section 8 — Backend implementation

Ask: "Which controller file(s) and service function(s) implement this?" Capture: controller file path + handler names; service file path + function names + CRUD helpers used (`create_record`, `get_or_404`, `list_records`, `update_record`, `soft_delete`); Celery tasks; background workers/cron.

### Section 9 — Frontend implementation

Ask: "Which routes, pages, and components does this feature add or modify?" Capture: app-router paths under `frontend/app/(dashboard)/...` or `frontend/app/(auth)/...`; page file paths; components (new vs modifies an existing shared component); Zustand stores; React Query hooks; **form layout mode** (modal / drawer / page) — this drives whether downstream skills run in modal/drawer/page mode; **listing component** (CustomTable, cards, etc.).

### Section 10 — Postman collection & examples

Ask: "Paste (or describe) the Postman requests for each endpoint, with example bodies and responses."

For each endpoint emit a code block with method+path, request body JSON, response JSON, and a `curl` example. Note: "Add these requests to `postman/Tone-Test-API.postman_collection.json` under folder `<area>`."

### Section 11 — Next steps (downstream skills)

This block is **auto-generated** from the answers above. Do not ask the user for it. Emit a checklist like:

```
- [ ] Run `/implement_feature_from_prd <slug>` — orchestrator reads this PRD and runs the right code generators in order
- [ ] Or run individual generators:
      - `/backend_tables` with entity `<entity>` for the list endpoint
      - `/backend_form`   with entity `<entity>` for the create/edit endpoint
      - `/table_page`     for the listing UI
      - `/form_page`      with layout=<modal|drawer|page> for the form UI
      - `/frontend_cards` instead of `/table_page` for card-grid listings
- [ ] Add Postman requests to `postman/Tone-Test-API.postman_collection.json`
- [ ] Write Alembic migration: `alembic revision --autogenerate -m "<feature>"`
- [ ] Add integration tests under `backend/tests/`
```

Pick the right skills based on what the user described in sections 6–9:

- Has a list/table view → include `/backend_tables` + `/table_page`
- Has a create/edit form → include `/backend_form` + `/form_page`
- Card-grid listing → use `/frontend_cards` instead of `/table_page`

### Section 12 — Change Log

Always include this section at the bottom. On first creation:

```
- YYYY-MM-DD — Initial PRD authored.
```

On update, prepend a new entry above prior ones:

```
- YYYY-MM-DD — <one-line summary of what changed; which sections>
- <prior entries kept as-is>
```

Use today's date from the environment context (do not guess).

---

## Output

Write **one** file:

**Path:** `docs/features/<feature-slug>.md`

**Structure:**

```markdown
# <Feature Name> — PRD & Implementation Spec

> Authored 2026-MM-DD. Update via `/generate_feature_prd_and_implementation` whenever the feature changes.

## 1. Overview
...
## 12. Change Log
- 2026-MM-DD — Initial PRD authored.
```

If `docs/features/` does not exist, create it.

**Do not** create a per-feature skill file under `.claude/skills/<slug>/`. PRDs live only in `docs/features/`.

---

## Update flow (existing feature)

If `docs/features/<slug>.md` already exists:

1. Read the file.
2. Print a summary: "Found existing PRD for <feature> last updated <date from Change Log>. Sections: 1. Overview, 2. User stories, ... 12. Change Log."
3. Ask: "Which sections do you want to update?" (multi-select)
4. For each chosen section, show the current content and ask what to change (replace / append / specific edits).
5. Re-emit the file with the updates merged in.
6. Prepend a new Change Log entry at the top of section 12 with today's date and a one-line description of what changed.

Never silently overwrite. If the user wants to discard the existing PRD entirely, confirm explicitly first.

---

## Hard rules

- **Never write production code in this skill** — only the PRD Markdown file.
- **Never invent technical details** the user didn't provide. If a section is empty, write `_(not specified)_` and move on. Hallucinating endpoints or schemas defeats the point.
- **Always cross-check against the project's mandatory patterns** in `RULES.md` and `CLAUDE.md`:
  - Multi-tenancy: every table filters by `organization_id`
  - RBAC: every endpoint uses `require_permission()` or `require_role()`
  - Serialization: `.to_dict()` only, never raw ORM objects
  - Soft deletes: `soft_delete()`, never `db.delete()`
  - CRUD helpers from `app.services.crud`
  - Frontend uses React Query for server state, Zustand for client state
  - Toast/errors via `lib/toast`, not raw sonner

  If the user's spec violates any of these, flag it explicitly in the PRD under a "⚠ Conventions Check" callout in the relevant section, and ask the user to confirm or revise before writing the file.
- **Always use today's date** from environment context for Change Log entries — never guess.
- **Always print the final PRD path** to the user so they can open it.

---

## Output confirmation

After writing the file, print:

```
✅ Feature PRD generated:
   docs/features/<slug>.md

Next: run `/implement_feature_from_prd <slug>` to scaffold code, or invoke the individual skills under "Next steps" in the PRD.
```
