# `.claude/code-review/` — this repo's review context

This folder is read by the **`code-review`** plugin (installed from the `tonehq-skills` marketplace — it
is **not** copied into this repo; only this small folder lives here). Whenever anyone reviews a change,
code-review reads **every `.md` in this folder tree — subfolders included — in full**, and follows it.

## Files

| File | Purpose | code-review uses it to… |
|---|---|---|
| `config.md` | Control — what loads + overrides + the Postman collection + extra paths | decide what to load (`include:`/`exclude:` — marketplace standards by name, repo-local skills by path), apply repo `overrides:`, name/disable the Postman collection + spec (`postman:`), pick research tools, pull in extra sources (`paths:`) |
| `*.md` / `<subfolder>/*.md` (any you add) | Extra review context (patterns, glossary, gotchas) | read in full too — the easy way to add context later, no config change. Subfolders are fine — organize however you like |

> This repo's **FE/BE specifics** are NOT in this folder — they live in **`.claude/standards/frontend.md`
> and `.claude/standards/backend.md`**, a **shared** pair read by both code-review and plan-mode (so
> there's one source of repo rules, not two). code-review reads them in full every review; they supplement
> and **beat** the generic `frontend-standards` / `backend-standards`, and the review flags reuse against
> their names.

## The API-contract check (`config.md` → `postman:`)

When a reviewed diff touches backend **API surface** (FastAPI routes, request/response Pydantic schema),
code-review diffs the change against your OpenAPI **spec** and Postman **collection** — **read-only** —
and reports anything stale: missing endpoints, mismatched method/path/params, drifted example bodies.
Point it at the collection (and optionally a spec file):

```md
postman:
  collection: <name-or-id>   # omit to auto-detect; add `disable` on its own line to skip the whole check
  spec: app/openapi.json     # optional: a repo OpenAPI spec to also diff against
```

**Connecting the Postman MCP** — code-review references it, it doesn't bundle or connect it:

- Easiest: install the **official Postman plugin** (it bundles a `.mcp.json`):
  `/plugin install postman@claude-plugins-official` → `/postman:setup` to authenticate.
- Or connect the Postman MCP yourself in `.mcp.json` / `.claude/settings.json` `mcpServers`.
- Auth via **OAuth** (recommended) or the `POSTMAN_API_KEY` env var.
- Prefer a **read-only tool mode** — set `POSTMAN_MCP_MODE=code` (~24 read-only tools); this check is
  report-only and never needs write tools.

It **never writes to Postman and never runs a collection** against a live API. If the Postman MCP isn't
connected and no spec is available, the review says so and lists what would need updating from the diff
alone.

## Reading from other paths (`config.md` → `paths:`)

You don't have to keep everything in this folder. List extra sources under `paths:` in `config.md` and
code-review reads them **in full** too — a file, a directory (every `.md` under it), or a glob; relative
to the repo root or absolute:

```md
paths:
  - docs/architecture/            # a directory → every .md under it
  - packages/*/STRUCTURE.md       # a glob → each match
  - ../shared-standards/code-review/ # elsewhere (relative or absolute) — e.g. shared org standards
```

**Read order:** this folder's whole tree first, then every `paths:` source. On a conflict, a file inside
this folder **wins** over an external `paths:` source (the committed folder is more specific).

## How it fits together (precedence)

```
repo CLAUDE.md / RULES.md → .claude/code-review/ (this folder) → .claude/standards/ (shared FE/BE) → generic standard skills
   (from the repo itself)       (tailors this repo)               (repo FE/BE specifics)              (fill the gaps)
```

**Two separate sources — don't mix them:** `CLAUDE.md` / `RULES.md` are always read from the **repo
itself** (repo root, nested dirs, `.claude/CLAUDE.md`) — **do not put them in this folder**. This folder
holds **only** code-review's own files (`config.md` and any extras).

- `CLAUDE.md` / `RULES.md` still win over anything here.
- The generic standards (`frontend-standards` / `react-vite-frontend-standards` / `backend-standards`)
  are the source of truth for each stack's reuse rules; code-review flags DRY/reuse violations *against*
  the one matching the changed file.

## Maintaining it

- Keep `config.md` short — only the skills to force in/out, the Postman collection, and the rules that
  differ from the generic.
- Keep the `postman:` collection name current when the repo's collection is renamed or split.
- Drop in extra `.md` files (top-level or in a subfolder) for anything else a review should always
  respect; they're picked up next review. For big or shared docs that live elsewhere, add a `paths:`
  entry in `config.md` instead of duplicating them here.

> Requires the `code-review` plugin: `/plugin marketplace add tonehq/claude-skills` →
> `/plugin install code-review@tonehq-skills` (plus the standards plugins this repo uses).
