# `.claude/plan-mode/` — this repo's planning context

This folder is read by the **`plan-mode`** plugin (installed from the `tonehq-skills` marketplace — it
is **not** copied into this repo; only this small folder lives here). Whenever anyone plans a change in
plan mode, plan-mode reads **every `.md` in this folder tree — subfolders included — in full**, and
follows it. (PRDs are **not** in this folder — they live in `.claude/prd/`, its own top-level folder, and
are **authored by the user**; plan-mode lists them and reads only the one for the feature being planned,
not all of them every time.)

## Files

| File | Purpose | plan-mode uses it to… |
|---|---|---|
| `config.md` | Control — what loads + overrides + extra paths | decide what to load (`include:`/`exclude:` — marketplace standards by name, repo-local skills like `architecture` by path), apply repo `overrides:`, pick research tools, pull in extra sources (`paths:`) |
| `*.md` / `<subfolder>/*.md` (any you add) | Extra planning context (patterns, glossary, gotchas) | read in full too — the easy way to add context later, no config change. Subfolders are fine — organize however you like |

> **PRDs live in `.claude/prd/<feature-name>/requirements.md`** — their own top-level folder, NOT in
> this folder and NOT under `.claude/standards/` — see the "PRDs" section below.

> This repo's **FE/BE specifics** are NOT in this folder — they live in **`.claude/standards/frontend.md`
> and `.claude/standards/backend.md`**, a **shared** pair read by both plan-mode and code-review (so
> there's one source of repo rules, not two). plan-mode reads them in full every plan; they supplement
> and **beat** the generic `frontend-standards` / `backend-standards`.

> Code & file **structure** is NOT a file in this folder — it's the repo's **`architecture` skill**
> (repo-local, under `.claude/skills/`, named in `config.md` `include:`). plan-mode loads it as the
> single source of structure for planning.

## PRDs — `.claude/prd/<feature-name>/requirements.md`

Each feature's PRD lives in `.claude/prd/<feature-name>/requirements.md` — its own top-level folder, one
folder per feature (beside the `lessons.md` that `feature-context` maintains). plan-mode **creates the
empty template at intake** and then **reads `requirements.md` only** — the user authors it, and plan-mode
ignores `lessons.md` and anything else in the folder.

```
.claude/prd/
  <feature-name>/          # one folder per feature, kebab-case (e.g. user-invites/)
    requirements.md        # feature spec (global PRD standard, see example-feature) — plan-mode reads it; changes need user approval
    lessons.md             # feature-context's lessons log (what the AI should improve next time) — NOT read by plan-mode
    tasks/<task>.md        # ONE file per task — the specific task to do; the plan is built from it
  example-feature/         # placeholder template shipped by plan-mode — copy its shape
```

`requirements.md` follows the **global PRD standard** (see `.claude/prd/example-feature/requirements.md`):

1. **Overview** — routes/entry points, goal, scope, shared surfaces
2. **Involved Files** — file → responsibility
3. **Layout & Structure** *(UI only)* · 4. **Content & Copy** *(UI only)* · 5. **Theming & Colors** *(UI
   only)* · 6. **Motion & Animation** *(UI only)* — delete these for non-UI features
7. **Behavior & Functionality** — validation, actions, state/data, **APIs & data model**, error handling
8. **Non-Functional Requirements** — standards, performance, SSR, security, observability
9. **Acceptance Criteria** — verifiable "done" conditions, each mapping to a numbered requirement
10. **Out of Scope**

**This file is authored by the USER — plan-mode never overwrites it.** plan-mode creates the empty
template at intake (one folder per feature), then **reads** your filled-in `requirements.md` as the plan's
**source of truth** and builds the plan from it. The finalized plan lives in the plan file, not here.
Start from the shape in `.claude/prd/example-feature/requirements.md`.

## Reading from other paths (`config.md` → `paths:`)

You don't have to keep everything in this folder. List extra sources under `paths:` in `config.md` and
plan-mode reads them **in full** too — a file, a directory (every `.md` under it), or a glob; relative to
the repo root or absolute:

```md
paths:
  - docs/architecture/            # a directory → every .md under it
  - packages/*/STRUCTURE.md       # a glob → each match
  - ../shared-standards/plan-mode/ # elsewhere (relative or absolute) — e.g. shared org standards
```

**Read order:** this folder's whole tree first, then every `paths:` source. On a conflict, a file inside
this folder **wins** over an external `paths:` source (the committed folder is more specific).

## How it fits together (precedence)

```
repo CLAUDE.md / RULES.md → .claude/plan-mode/ (this folder) → .claude/standards/ (shared FE/BE) → generic standard skills
   (from the repo itself)       (tailors this repo)             (repo FE/BE specifics)              (fill the gaps)
```

**Two separate sources — don't mix them:** `CLAUDE.md` / `RULES.md` are always read from the **repo
itself** (repo root, nested dirs, `.claude/CLAUDE.md`) — **do not put them in this folder**. This folder
holds **only** plan-mode's own files (`config.md` and any extras).

- `CLAUDE.md` / `RULES.md` still win over anything here.
- The repo's **`architecture` skill** (named in `config.md`, under `.claude/skills/`) is the **only**
  source of code/file structure for planning in this repo.
- The generic standards (`frontend-standards` / `backend-standards`) fill in the code rules this folder
  doesn't specify.

## Maintaining it

- Keep `config.md` short — only the skills to force in/out (incl. the `architecture` skill) and the rules
  that differ from the generic.
- Keep the **`architecture` skill** matching reality — when the repo's layout changes, update it so plans
  keep landing files in the right place.
- Drop in extra `.md` files (top-level or in a subfolder) for anything else a plan should always respect;
  they're picked up next plan. For big or shared docs that live elsewhere, add a `paths:` entry in
  `config.md` instead of duplicating them here.

> Requires the `plan-mode` plugin: `/plugin marketplace add tonehq/claude-skills` →
> `/plugin install plan-mode@tonehq-skills` (plus the standards plugins this repo uses).
