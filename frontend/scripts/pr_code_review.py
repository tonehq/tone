#!/usr/bin/env python3
"""Automated PR code review using Claude API.

Fetches the PR diff (frontend files only), sends it to Claude with the
project's review checklists, and posts the review as a PR comment.

Usage:
    python frontend/scripts/pr_code_review.py --pr <NUMBER>

Environment variables:
    ANTHROPIC_API_KEY  — Required. Claude API key.
    GH_TOKEN           — Required. GitHub token with pull-requests:write scope.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

COMMENT_MARKER = "<!-- pr-code-review -->"
MAX_DIFF_BYTES = 100_000  # 100 KB
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

# Paths filtered into the review
INCLUDE_PREFIXES = ("frontend/src/", "frontend/e2e/")

# File patterns excluded from the review
EXCLUDE_SUFFIXES = (
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
)
EXCLUDE_PATHS = ("test-results/", "node_modules/", ".next/")

# Resolve repo root relative to this script (frontend/scripts/ -> repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

CHECKLIST_FILES = [
    "frontend/.claude/skills/code-review/references/solid-checklist.md",
    "frontend/.claude/skills/code-review/references/security-checklist.md",
    "frontend/.claude/skills/code-review/references/performance-checklist.md",
    "frontend/.claude/skills/code-review/references/code-quality-checklist.md",
    "frontend/.claude/skills/code-review/references/removal-plan.md",
]


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    """Run a shell command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def get_pr_diff(pr_number: int) -> str:
    """Fetch the PR diff from GitHub, filtered to frontend paths."""
    result = run(["gh", "pr", "diff", str(pr_number), "--color=never"])
    if result.returncode != 0:
        print(f"Error fetching PR diff: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    return filter_diff(result.stdout)


def filter_diff(raw_diff: str) -> str:
    """Keep only hunks for frontend/src/ and frontend/e2e/ paths, excluding
    binary assets, lock files, and build artifacts."""
    filtered_sections: list[str] = []
    current_section: list[str] = []
    current_file = ""

    for line in raw_diff.splitlines(keepends=True):
        if line.startswith("diff --git"):
            # Flush previous section if it passed filters
            if current_section and _should_include(current_file):
                filtered_sections.append("".join(current_section))
            current_section = [line]
            # Extract b-side path: "diff --git a/foo b/bar" -> "bar"
            parts = line.split(" b/", 1)
            current_file = parts[1].strip() if len(parts) > 1 else ""
        else:
            current_section.append(line)

    # Flush last section
    if current_section and _should_include(current_file):
        filtered_sections.append("".join(current_section))

    return "".join(filtered_sections)


def _should_include(filepath: str) -> bool:
    """Check whether a file path should be included in the review."""
    if not filepath:
        return False
    if not any(filepath.startswith(prefix) for prefix in INCLUDE_PREFIXES):
        return False
    if any(filepath.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return False
    if any(excluded in filepath for excluded in EXCLUDE_PATHS):
        return False
    return True


def load_checklists() -> str:
    """Read all five reference checklists and concatenate them."""
    parts: list[str] = []
    for relpath in CHECKLIST_FILES:
        fullpath = REPO_ROOT / relpath
        if fullpath.exists():
            parts.append(f"--- {relpath} ---\n{fullpath.read_text()}")
        else:
            parts.append(f"--- {relpath} ---\n(file not found)")
    return "\n\n".join(parts)


def build_system_prompt(checklists: str) -> str:
    """Build the system prompt for the code review."""
    return f"""You are a Principal Frontend Architect reviewing a pull request for a React + Next.js (App Router) project.

The project uses:
- Next.js 15 App Router with React 19 and TypeScript
- Jotai for state management (atoms in src/atoms/)
- MUI v6 with a custom theme, migrating to shadcn/Tailwind
- Axios-based API services in src/services/
- Firebase auth with JWT, cookies for auth state

Review the diff below working through ALL 9 sections. Do not skip any.

### Review Sections

1. **Correctness** — Logical bugs, TypeScript issues, state mutation, missing null checks, async without try/catch
2. **React Best Practices** — Rules of hooks, dependency arrays, missing keys, memo misuse, prop drilling
3. **Next.js Best Practices** — 'use client' placement, next/image usage, data fetching patterns
4. **SOLID + Architecture** — SRP, OCP, LSP, ISP, DIP. Services must not import atoms. Components must not call services directly.
5. **Security** — XSS, injection, auth bypass, secrets exposure, race conditions, data integrity
6. **Performance** — React rendering, SSR, bundle splitting, network/API, Core Web Vitals, memory, state mgmt, assets
7. **Code Quality** — Error handling, TypeScript quality, boundary conditions, naming, structure, dead code, async
8. **Accessibility** — Semantic HTML, ARIA, keyboard navigation, heading hierarchy, focus management
9. **Dead Code / Removal Candidates** — Unused exports, stale flags, deprecated APIs, duplicates

### Project-Specific Rules

- Buttons: Use CustomButton from @/components/shared only
- API errors: Use handleApiError from @/utils/helpers
- Auth: Roles from login_data cookie only, never query params
- Axios: Use the shared instance from src/utils/axios.ts, never raw fetch
- Direction: Prefer shadcn + Tailwind for new UI; lucide-react for icons

### Reference Checklists

{checklists}

### Output Format

```markdown
# Code Review Summary

<!-- pr-code-review -->

**Files reviewed**: <count>
**Overall assessment**: APPROVE / REQUEST_CHANGES / COMMENT

---

## Critical Issues
(security flaws, crashes, data loss, 🔴 perf regressions)

## High Priority Issues
(SOLID violations, hook misuse, SSR mistakes, 🟠 perf, major error handling gaps)

## Performance Issues
(grouped by the 8 sub-areas)
- **Performance Summary**: 🔴 / 🟠 / 🟡 / 🟢

## Medium Priority Issues
(maintainability, 🟡 perf, missing error handling, code quality)

## Low Priority Suggestions
(naming, style, 🔵 minor optimisations)

## Removal / Iteration Plan
(dead code candidates found in the diff)

## Positive Observations
(good patterns, clean code, nice improvements)
```

For each issue: **file:line** — Problem — Why it matters — Suggested fix

If a section has no findings, write a brief "No issues detected" note.
Be strict but constructive. Do NOT hallucinate code that is not in the diff."""


def call_claude(system_prompt: str, diff: str) -> str:
    """Send the diff to Claude and return the review markdown."""
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Please review this pull request diff:\n\n```diff\n{diff}\n```",
            }
        ],
    )
    # Extract text from the response
    return "".join(
        block.text for block in message.content if hasattr(block, "text")
    )


def post_or_update_comment(pr_number: int, body: str) -> None:
    """Post a new PR comment or update an existing one (matched by marker)."""
    # Get repo owner/name from gh
    repo_result = run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    )
    if repo_result.returncode != 0:
        print(f"Error getting repo info: {repo_result.stderr}", file=sys.stderr)
        sys.exit(1)

    repo = repo_result.stdout.strip()

    # Search for existing comment with our marker
    comments_result = run(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{pr_number}/comments",
            "--paginate",
            "-q",
            f'[.[] | select(.body | contains("{COMMENT_MARKER}"))][0].id',
        ]
    )

    existing_id = comments_result.stdout.strip()

    if existing_id:
        # Update existing comment
        result = run(
            [
                "gh",
                "api",
                f"repos/{repo}/issues/comments/{existing_id}",
                "-X",
                "PATCH",
                "-f",
                f"body={body}",
            ]
        )
        if result.returncode != 0:
            print(f"Error updating comment: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(f"Updated existing review comment (id: {existing_id})")
    else:
        # Create new comment
        result = run(
            ["gh", "pr", "comment", str(pr_number), "--body", body]
        )
        if result.returncode != 0:
            print(f"Error posting comment: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        print("Posted new review comment")


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated PR code review")
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    args = parser.parse_args()

    # Validate environment
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("GH_TOKEN"):
        print("Error: GH_TOKEN environment variable is not set", file=sys.stderr)
        sys.exit(1)

    # Step 1: Get filtered diff
    print(f"Fetching diff for PR #{args.pr}...")
    diff = get_pr_diff(args.pr)

    if not diff.strip():
        body = f"{COMMENT_MARKER}\n\n# Code Review Summary\n\nNo frontend changes to review (`frontend/src/` and `frontend/e2e/`)."
        post_or_update_comment(args.pr, body)
        print("No frontend changes found. Posted skip comment.")
        return

    # Truncate if too large
    truncated = False
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        diff = diff[: MAX_DIFF_BYTES]
        truncated = True
        print(f"Warning: Diff truncated to {MAX_DIFF_BYTES // 1000} KB")

    # Step 2: Build prompt with checklists
    print("Loading review checklists...")
    checklists = load_checklists()
    system_prompt = build_system_prompt(checklists)

    # Step 3: Call Claude
    print(f"Sending diff to Claude ({MODEL})...")
    try:
        review = call_claude(system_prompt, diff)
    except Exception as e:
        body = (
            f"{COMMENT_MARKER}\n\n# Code Review Summary\n\n"
            f"Automated review failed: `{e}`\n\n"
            "Please run `/code-review` manually."
        )
        post_or_update_comment(args.pr, body)
        print(f"Claude API error: {e}", file=sys.stderr)
        # Exit 0 so we don't block the PR
        return

    # Step 4: Post comment
    truncation_note = ""
    if truncated:
        truncation_note = (
            "\n\n> **Note**: The diff was larger than 100 KB and was truncated. "
            "Some files may not have been reviewed. Run `/code-review` locally "
            "for a complete review.\n"
        )

    # Ensure the marker is in the body for future identification
    if COMMENT_MARKER not in review:
        body = f"{COMMENT_MARKER}\n\n{review}{truncation_note}"
    else:
        body = f"{review}{truncation_note}"

    print("Posting review comment...")
    post_or_update_comment(args.pr, body)
    print("Done!")


if __name__ == "__main__":
    main()
