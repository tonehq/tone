---
name: find-impacted-routes
description: >
  Analyzes git diffs between commits to identify which Next.js App Router routes (pages) are
  affected by code changes. Traces the full impact chain: service changes → Jotai atoms →
  components → page files → URL routes. Also detects layout changes (affecting all child routes)
  and middleware changes (affecting all protected routes). Use when the user asks "what routes
  changed", "which pages are impacted", "what did my diff affect", "find changed pages",
  "trace route impact", "what routes need testing", or "what pages were modified". Works with
  the Next.js App Router + Jotai + shadcn/ui frontend in this project.
---

# Find Impacted Routes

This skill analyzes git diffs to identify which Next.js App Router routes are affected by code
changes. It traces the full dependency chain from low-level services up to page-level routes.

## Impact Chain (this project's architecture)

```
src/services/       ← API layer
    ↓ (imported by)
src/atoms/          ← Jotai state atoms
    ↓ (imported by)
src/components/     ← React components
    ↓ (imported by)
src/app/**/page.tsx ← Route pages (URL routes)
```

Additional direct impacts:

- `src/app/**/layout.tsx` — affects all child routes under that path
- `src/middleware.ts` — affects all protected routes
- `src/utils/` / `src/hooks/` / `src/types/` — traced upward like components

---

## Inputs

| Input          | Required | Default            | Description                      |
| -------------- | -------- | ------------------ | -------------------------------- |
| `commit1`      | No       | Commit at last run | The "before" commit SHA          |
| `commit2`      | No       | Current HEAD       | The "after" commit SHA           |
| `branch`       | No       | Current branch     | Git branch to analyze            |
| `project_path` | No       | `frontend/` dir    | Path to the Next.js project root |

**Behavior:**

- Both commits provided → Diff between those two commits
- Neither provided → Diff between last run's commit and HEAD
- Only `commit2` provided → Use last run's commit as `commit1`

---

## State File

Tracks the last run at: `~/.claude-skills/find-impacted-routes/last_run.json`

```json
{
  "last_run_timestamp": "2024-01-15T10:30:00Z",
  "last_commit_at_run": "abc123def",
  "branch": "main",
  "project_path": "/path/to/frontend"
}
```

---

## Step-by-Step Execution

### Step 0 — Setup and Read State

```bash
mkdir -p ~/.claude-skills/find-impacted-routes
cat ~/.claude-skills/find-impacted-routes/last_run.json 2>/dev/null || echo "No previous run"
git branch --show-current
git rev-parse HEAD
```

---

### Step 1 — Determine the Two Commits

**Case A: Both provided**

```
commit1 = user_commit1
commit2 = user_commit2
```

**Case B: Neither provided (auto mode)**

```bash
commit2=$(git rev-parse HEAD)
commit1=$(git log -1 --format=%H --before="<last_run_timestamp>")
```

If no state file exists (first run), tell the user and ask for `commit1`.

**Case C: Only commit2 provided**

```
commit1 = last_commit_at_run  (from state file)
commit2 = user_provided
```

**Validate both commits:**

```bash
git cat-file -t <commit1>   # must output "commit"
git cat-file -t <commit2>
```

---

### Step 2 — Run the Analyzer Script

```bash
python3 .claude/skills/find-impacted-routes/analyze_diff.py \
  --project-path <project_path> \
  --commit1 <commit1> \
  --commit2 <commit2> \
  [--branch <branch>] \
  [--output <output_dir>]
```

The script handles all file categorization, import tracing, and report generation.
It prints a summary and saves the full reports to the output directory.

---

### Step 3 — Update State File

After successful run, the script automatically updates the state file. Verify:

```bash
cat ~/.claude-skills/find-impacted-routes/last_run.json
```

---

### Step 4 — Present Results

1. Show the printed summary from the script
2. Tell the user where the full reports were saved (`impacted-routes-report.md`, `impacted-routes-report.json`)
3. Offer to:
   - Dive deeper into any specific impacted route
   - Run `/generate-tests` for the impacted routes
   - Run `/code-review` scoped to the impacted files

---

## Route Resolution Rules (Next.js App Router)

| Pattern                | Example File                               | URL Route                       |
| ---------------------- | ------------------------------------------ | ------------------------------- |
| Root page              | `src/app/page.tsx`                         | `/`                             |
| Route group (stripped) | `src/app/(dashboard)/home/page.tsx`        | `/home`                         |
| Auth routes            | `src/app/auth/login/page.tsx`              | `/auth/login`                   |
| Dynamic segment        | `src/app/agents/edit/[type]/[id]/page.tsx` | `/agents/edit/[type]/[id]`      |
| Layout scope           | `src/app/(dashboard)/layout.tsx`           | all routes under `(dashboard)/` |

---

## File Categories

| Category        | Path Pattern                      | Impact Level                        |
| --------------- | --------------------------------- | ----------------------------------- |
| `page`          | `src/app/**/page.tsx`             | Direct route                        |
| `layout`        | `src/app/**/layout.tsx`           | All child routes                    |
| `middleware`    | `src/middleware.ts`               | All protected routes                |
| `component`     | `src/components/**`               | Traced → pages                      |
| `atom`          | `src/atoms/**`                    | Traced → components → pages         |
| `service`       | `src/services/**`                 | Traced → atoms → components → pages |
| `util` / `hook` | `src/utils/**`, `src/hooks/**`    | Traced → components → pages         |
| `type`          | `src/types/**`                    | Structural — noted but not traced   |
| `config`        | `src/constants/**`, `src/urls.ts` | Noted, traced if imported           |

---

## Output Report Structure

Saved to `<output_dir>/impacted-routes-report.md` and `impacted-routes-report.json`.

```markdown
# Impacted Routes Report

> Generated: <timestamp>
> Comparing: `<commit1>` → `<commit2>`
> Branch: <branch>

## Summary

| Category             | Count  |
| -------------------- | ------ |
| Direct route changes | X      |
| Transitive impacts   | X      |
| Layout changes       | X      |
| Middleware modified  | Yes/No |
| Total unique routes  | X      |

---

## Directly Modified Routes

Routes where page.tsx itself (or an inline component within it) changed.

| Route   | File                                | Change   |
| ------- | ----------------------------------- | -------- |
| /agents | src/app/(dashboard)/agents/page.tsx | Modified |

---

## Transitively Impacted Routes

Routes impacted by changes to shared components, atoms, or services.

| Route   | File                                | Via            | Impact Chain                                      |
| ------- | ----------------------------------- | -------------- | ------------------------------------------------- |
| /agents | src/app/(dashboard)/agents/page.tsx | AgentsAtom.tsx | agentsService → AgentsAtom → AgentListPage → page |

---

## Layout Changes (Affect All Child Routes)

| Layout                         | Scope     | Child Routes                              |
| ------------------------------ | --------- | ----------------------------------------- |
| src/app/(dashboard)/layout.tsx | Dashboard | /home, /agents, /settings, /phone-numbers |

---

## Middleware Impact

_Modified_ — All routes protected by `src/middleware.ts` may be affected:
/home, /agents, /agents/create/inbound, ...

---

## Changed Files by Category

| File                     | Category | Status   | +Lines | -Lines |
| ------------------------ | -------- | -------- | ------ | ------ |
| src/atoms/AgentsAtom.tsx | atom     | modified | +28    | -40    |

---

## Dependency Chains

### src/services/agentsService.ts (modified)

└── src/atoms/AgentsAtom.tsx [imports agentsService]
└── src/components/agents/AgentListPage.tsx [uses AgentsAtom]
└── /agents (src/app/(dashboard)/agents/page.tsx)

### src/components/shared/CustomButton.tsx (modified)

└── [used by 40+ components — see JSON for full list]
└── AFFECTS ALL ROUTES (shared component)
```

---

## Error Handling

| Error                         | Action                                               |
| ----------------------------- | ---------------------------------------------------- |
| Not a git repository          | Ask user to run from the frontend dir                |
| Commit not found              | Show `git log --oneline -10` to help find valid SHAs |
| No state / first run          | Ask for `commit1` explicitly                         |
| No `.ts`/`.tsx` files changed | Report "No frontend files changed"                   |
| Python not available          | Offer to manually trace with bash greps              |

---

## Example Invocations

```bash
# Automatic — compare since last run
/find-impacted-routes

# Against a specific commit
/find-impacted-routes commit1=abc123 commit2=HEAD

# Compare current branch vs main
/find-impacted-routes commit1=main commit2=HEAD

# With explicit project path
/find-impacted-routes project_path=/Users/me/tonehq/frontend
```
