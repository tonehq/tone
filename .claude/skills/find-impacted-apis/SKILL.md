---
name: find-impacted-apis
description: >
  Analyzes git diffs between commits to identify impacted FastAPI controller endpoints, service 
  functions, and model classes. Use this skill when the user asks to find changed APIs, identify
  impacted endpoints, analyze code changes between commits, see what APIs were modified, detect
  affected controllers/services/models, or audit changes since last run. Triggers on phrases like
  "what APIs changed", "find impacted endpoints", "diff my code", "what did I change", 
  "analyze commits", "show affected controllers", "what's different since last time", or 
  "compare commits". Works with Python/FastAPI codebases. Can accept explicit commit SHAs or 
  automatically compare against the last run timestamp.
---

# Find Impacted APIs

This skill analyzes git diffs to identify which FastAPI controller endpoints, service functions, 
and model classes have been modified between two commits.

## Inputs

The skill accepts these optional inputs (ask the user if not provided):

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `commit1` | No | Last commit before previous run | The "before" commit SHA |
| `commit2` | No | Latest commit on current branch | The "after" commit SHA |
| `branch` | No | Current branch | Git branch to analyze |
| `project_path` | No | Current directory | Path to the git repository |

**Behavior:**
- If both `commit1` and `commit2` are provided → Diff between those specific commits
- If neither is provided → Diff between "last commit before skill's last run" and "current HEAD"
- If only one is provided → Ask user for the other, or use HEAD as commit2

---

## State File Location

The skill tracks its last run time in: `~/.claude-skills/find-impacted-apis/last_run.json`

```json
{
  "last_run_timestamp": "2024-01-15T10:30:00Z",
  "last_commit_at_run": "abc123def",
  "branch": "main",
  "project_path": "/path/to/project"
}
```

**On every run:**
1. Read the state file (if exists)
2. After completing analysis, update the file with current timestamp and commit

---

## Step-by-Step Execution

### Step 0: Setup and Read State

```bash
# Create state directory if needed
mkdir -p ~/.claude-skills/find-impacted-apis

# Check if state file exists
cat ~/.claude-skills/find-impacted-apis/last_run.json 2>/dev/null || echo "No previous run found"
```

If the state file exists, parse it to get:
- `last_run_timestamp` — when the skill last ran
- `last_commit_at_run` — which commit was HEAD at that time

---

### Step 1: Determine the Two Commits

**Case A: User provided both commits**
```
commit1 = user_provided_commit1
commit2 = user_provided_commit2
```

**Case B: User provided neither commit (automatic mode)**
```bash
# Get current HEAD commit
commit2=$(git rev-parse HEAD)

# Get the commit that existed at last_run_timestamp
# Using git log with --before flag
commit1=$(git log -1 --format=%H --before="<last_run_timestamp>")
```

If no `last_run_timestamp` exists (first run), inform the user:
> "This is the first run — I don't have a previous timestamp. Please provide commit1, or I can 
> compare against a time-based reference (e.g., 'commits from the last 24 hours')."

**Case C: User provided only commit2**
```
commit1 = last_commit_at_run (from state file)
commit2 = user_provided
```

**Validation:**
```bash
# Verify both commits exist
git cat-file -t <commit1>  # Should output "commit"
git cat-file -t <commit2>  # Should output "commit"
```

---

### Step 2: Get the Git Diff

```bash
# Navigate to project
cd <project_path>

# Ensure we're on the right branch
git checkout <branch>

# Get the diff with file names and stats
git diff --name-status <commit1> <commit2>

# Get the full diff content for analysis
git diff <commit1> <commit2> -- "*.py"
```

**Filter for relevant files:**
- `**/controllers/**/*.py` or `**/api/**/*.py` — Controller files
- `**/services/**/*.py` — Service files  
- `**/models/**/*.py` — Model files
- `**/schemas/**/*.py` — Schema/DTO files
- `**/routers/**/*.py` — Router files (alternative naming)

---

### Step 3: Parse the Diff and Identify Changes

For each changed Python file, analyze the diff hunks to identify:

#### 3.1 Controller/Router Changes (Impacted API Endpoints)

Look for changes in lines containing:
```python
@router.get(
@router.post(
@router.put(
@router.patch(
@router.delete(
@app.get(
@app.post(
# etc.
```

**Extract:**
- HTTP method (GET, POST, PUT, PATCH, DELETE)
- Route path (e.g., `/users/{user_id}`)
- Function name
- Whether it was Added (+), Modified (M), or Deleted (-)

#### 3.2 Service Function Changes

Look for changes in:
```python
def <function_name>(
async def <function_name>(
class <ClassName>:
    def <method_name>(
```

**Extract:**
- Class name (if method)
- Function/method name
- Whether signature changed vs just implementation

#### 3.3 Model Class Changes

Look for changes in:
```python
class <ModelName>(Base):
class <ModelName>(BaseModel):  # Pydantic
__tablename__ = 
Column(
relationship(
```

**Extract:**
- Model class name
- Table name
- Changed columns/fields
- Changed relationships

---

### Step 4: Trace Impact Relationships

For each changed service function, find which controllers call it:
```bash
# Search for usages of the service function
grep -r "<function_name>" --include="*.py" <project_path>/controllers/
grep -r "<function_name>" --include="*.py" <project_path>/api/
```

For each changed model, find which services/controllers use it:
```bash
grep -r "<ModelName>" --include="*.py" <project_path>/services/
grep -r "<ModelName>" --include="*.py" <project_path>/api/
```

Build a dependency map:
```
Model Change → Services Affected → Controllers/APIs Affected
```

---

### Step 5: Generate the Impact Report

Create a structured report file at `<project_path>/impacted-apis-report.md`:

```markdown
# Impacted APIs Report

> Generated: <timestamp>
> Comparing: `<commit1>` → `<commit2>`
> Branch: <branch>

## Summary

| Category | Added | Modified | Deleted |
|----------|-------|----------|---------|
| API Endpoints | X | Y | Z |
| Service Functions | X | Y | Z |
| Model Classes | X | Y | Z |

---

## Impacted API Endpoints

### Added Endpoints
| Method | Path | Function | File |
|--------|------|----------|------|
| POST | /api/v1/users/ | create_user | api/v1/user_controller.py |

### Modified Endpoints
| Method | Path | Function | File | Change Type |
|--------|------|----------|------|-------------|
| GET | /api/v1/users/{id} | get_user | api/v1/user_controller.py | Implementation |

### Deleted Endpoints
| Method | Path | Function | File |
|--------|------|----------|------|
| DELETE | /api/v1/legacy/ | legacy_delete | api/v1/legacy_controller.py |

---

## Impacted Service Functions

### Direct Changes
| Service Class | Function | File | Change Type |
|---------------|----------|------|-------------|
| UserService | create_user | services/user_service.py | Modified |

### Indirectly Affected (via Model Changes)
| Service Class | Function | File | Affected By |
|---------------|----------|------|-------------|
| UserService | get_by_id | services/user_service.py | UserModel.status field added |

---

## Impacted Models

### Changed Models
| Model | Table | File | Changes |
|-------|-------|------|---------|
| UserModel | users | models/user.py | +status column, -legacy_field |

### Field-Level Changes
#### UserModel (models/user.py)
- **Added:** `status: Column(String)` — New user status field
- **Removed:** `legacy_field` — Deprecated column removed
- **Modified:** `email` — Added unique constraint

---

## Dependency Impact Chain

```
UserModel.status (added)
  └── UserService.update_status() [NEW]
      └── PUT /api/v1/users/{id}/status [NEW ENDPOINT]
  └── UserService.get_user() [MODIFIED - returns new field]
      └── GET /api/v1/users/{id} [AFFECTED]
```

---

## Files Changed

| File | Status | Lines Added | Lines Removed |
|------|--------|-------------|---------------|
| api/v1/user_controller.py | Modified | +45 | -12 |
| services/user_service.py | Modified | +23 | -5 |
| models/user.py | Modified | +8 | -3 |

---

## Raw Diff Summary

<details>
<summary>Click to expand full diff</summary>

```diff
(Include relevant portions of the git diff here)
```

</details>
```

---

### Step 6: Update State File

After successful completion, update the state file:

```bash
cat > ~/.claude-skills/find-impacted-apis/last_run.json << 'EOF'
{
  "last_run_timestamp": "<current_iso_timestamp>",
  "last_commit_at_run": "<commit2>",
  "branch": "<branch>",
  "project_path": "<project_path>"
}
EOF
```

---

### Step 7: Present Results

1. Save the report to `<project_path>/impacted-apis-report.md`
2. Also save a JSON version to `<project_path>/impacted-apis-report.json` for programmatic use
3. Present a summary to the user
4. Offer to dive deeper into any specific change

---

## JSON Output Format

For programmatic consumption, also generate `impacted-apis-report.json`:

```json
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00Z",
    "commit1": "abc123",
    "commit2": "def456",
    "branch": "main",
    "project_path": "/path/to/project"
  },
  "summary": {
    "endpoints": { "added": 1, "modified": 3, "deleted": 0 },
    "services": { "added": 0, "modified": 2, "deleted": 0 },
    "models": { "added": 0, "modified": 1, "deleted": 0 }
  },
  "impacted_endpoints": [
    {
      "method": "POST",
      "path": "/api/v1/users/",
      "function": "create_user",
      "file": "api/v1/user_controller.py",
      "change_type": "added",
      "line_number": 45
    }
  ],
  "impacted_services": [
    {
      "class": "UserService",
      "function": "create_user",
      "file": "services/user_service.py",
      "change_type": "modified"
    }
  ],
  "impacted_models": [
    {
      "model": "UserModel",
      "table": "users",
      "file": "models/user.py",
      "changes": {
        "added_fields": ["status"],
        "removed_fields": ["legacy_field"],
        "modified_fields": ["email"]
      }
    }
  ],
  "dependency_chains": [
    {
      "root": "UserModel.status",
      "root_type": "model_field",
      "impacts": [
        { "type": "service", "name": "UserService.get_user" },
        { "type": "endpoint", "path": "GET /api/v1/users/{id}" }
      ]
    }
  ],
  "files_changed": [
    {
      "file": "api/v1/user_controller.py",
      "status": "modified",
      "lines_added": 45,
      "lines_removed": 12
    }
  ]
}
```

---

## Error Handling

| Error | How to Handle |
|-------|---------------|
| Not a git repository | Tell user to run from a git repo or provide `project_path` |
| Commit not found | Verify commit SHA, suggest using `git log` to find valid commits |
| No state file (first run) | Explain this is first run, ask for commit1 or use time-based fallback |
| No Python files changed | Report "No Python files changed between these commits" |
| Branch doesn't exist | List available branches, ask user to choose |

---

## Example Invocations

**Automatic mode (compare since last run):**
> "Find impacted APIs in my project"

**Explicit commits:**
> "Find impacted APIs between commit abc123 and def456"

**Branch-specific:**
> "What APIs changed on the feature/auth branch since yesterday?"

**With project path:**
> "Analyze /home/user/my-fastapi-project for API changes"