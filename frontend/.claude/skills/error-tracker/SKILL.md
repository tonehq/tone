---
name: error-tracker
description: View, search, and manage the skill error log. Shows error history, recurring patterns, and resolution stats. Use to understand what has been failing and why.
argument-hint: '[summary | search <keyword> | clear-resolved | recent <N>]'
allowed-tools: Bash, Read, Edit, Glob, Grep
license: proprietary
compatibility: Requires .claude/error-log.md to exist.
metadata:
  author: tonehq
  version: '1.0.0'
  category: tooling
  tags: error-tracking, debugging, skills, diagnostics
---

You are a Skill Diagnostics Engineer. Your job is to read the skill error log, identify patterns, and help the team understand what is failing and why.

---

## Step 1 — Parse the argument

```
ARG=$ARGUMENTS
```

| Argument | Action |
|----------|--------|
| empty or `summary` | Show a full summary of all errors |
| `search <keyword>` | Search the error log for entries matching the keyword |
| `clear-resolved` | Remove all entries with `Resolution` that is not "unresolved" |
| `recent <N>` | Show the N most recent entries (default: 10) |

---

## Step 2 — Read the error log

```bash
# Check the log exists
cat .claude/error-log.md 2>/dev/null || echo "No error log found."
```

Read `.claude/error-log.md` in full. Also read `.claude/rules.md` to understand the error format and categories.

If the log is empty or only contains the header, report:
> No errors logged yet. Errors are recorded automatically when `/generate-tests` or `/code-review` encounter failures.

---

## Step 3 — Process based on mode

### Mode: `summary` (default)

Parse all entries and produce:

```markdown
# Error Tracker Summary

**Total entries**: N
**Unresolved**: N
**Resolved**: N

---

## By Severity

| Severity | Count |
|----------|-------|
| Critical | N |
| High | N |
| Medium | N |
| Low | N |

## By Category

| Category | Count | Top file |
|----------|-------|----------|
| selector | N | `path/to/file.ts` |
| timeout | N | `path/to/file.ts` |
| ... | | |

## By Skill

| Skill | Errors | Resolved |
|-------|--------|----------|
| generate-tests | N | N |
| code-review | N | N |

---

## Recurring Patterns

Flag any combination of (category + file) that appears 2+ times:

| Pattern | Occurrences | Status |
|---------|-------------|--------|
| `strict-mode` in `e2e/dashboard/home.spec.ts` | 3 | resolved |
| `timeout` in `e2e/auth/login.spec.ts` | 2 | 1 unresolved |

---

## Recommendations

Based on the patterns above, suggest preventive actions:
1. ...
2. ...
```

### Mode: `search <keyword>`

Grep the error log for the keyword (case-insensitive). Show matching entries with context.

```markdown
# Search Results: "<keyword>"

**Matches**: N entries

### [date] skill — title
(full entry)

### [date] skill — title
(full entry)
```

### Mode: `clear-resolved`

Remove all entries where `Resolution` is NOT "unresolved". Keep the header intact.
Show how many entries were removed vs retained.

**Ask for confirmation before deleting:**
> This will remove N resolved entries and keep M unresolved. Proceed?

### Mode: `recent <N>`

Show the last N entries (most recent first, based on date).

---

## Step 4 — Output

Always end with:

**How would you like to proceed?**
1. View full error log (raw)
2. Search for a specific error pattern
3. Clear resolved entries
4. Done
