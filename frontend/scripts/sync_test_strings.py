#!/usr/bin/env python3
"""
Sync UI string changes from source files into Playwright test assertions.

Parses `git diff -U0` to extract old→new string literal changes, then finds
and replaces those strings in test spec files within assertion/selector contexts.

Usage:
    python3 scripts/sync_test_strings.py \
        --project-path /path/to/frontend \
        --commit1 <sha> --commit2 <sha> \
        --report-json impacted-routes-report.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class StringChange:
    old: str
    new: str
    source_file: str
    hunk_header: str = ""


@dataclass
class HunkStrings:
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


# ============================================================================
# Route-to-Test Mapping
# ============================================================================

ROUTE_TO_TEST: dict[str, list[str]] = {
    "/auth/login":             ["e2e/auth/login.spec.ts"],
    "/auth/signup":            ["e2e/auth/signup.spec.ts"],
    "/home":                   ["e2e/dashboard/home.spec.ts"],
    "/agents":                 ["e2e/dashboard/agents.spec.ts"],
    "/agents/create/inbound":  ["e2e/dashboard/agents-create-inbound.spec.ts"],
    "/agents/create/outbound": ["e2e/dashboard/agents-create-outbound.spec.ts"],
    "/agents/edit":            ["e2e/dashboard/agents-edit.spec.ts"],
}

# Always scan auth helper when login route is impacted
AUTH_HELPER = "e2e/helpers/auth.ts"


# ============================================================================
# String Extraction Patterns (for source files)
# ============================================================================

# JSX text content: >Some text</
RE_JSX_TEXT = re.compile(r">([^<>{}\n]+)</")

# Prop string values: placeholder="..." label="..." name="..." alt="..." title="..."
RE_PROP_VALUE = re.compile(
    r'(?:placeholder|label|name|alt|title)=["\']([^"\']+)["\']'
)

# Toast calls: showToast.success('...')  showToast.error("...")
RE_TOAST = re.compile(r"showToast\.\w+\(['\"]([^'\"]+)['\"]")

# Component children: <CustomButton>text</CustomButton>, <CustomLink>text</CustomLink>
RE_COMPONENT_CHILDREN = re.compile(
    r"<(?:CustomButton|CustomLink|Button|Link)[^>]*>([^<]+)</"
)

# Plain string assignments in JSX: {'Some text'} or {"Some text"}
RE_JSX_EXPR = re.compile(r"\{['\"]([^'\"]{3,})['\"]}")

SOURCE_PATTERNS = [RE_JSX_TEXT, RE_PROP_VALUE, RE_TOAST, RE_COMPONENT_CHILDREN, RE_JSX_EXPR]


# ============================================================================
# Test File Replacement Patterns
# ============================================================================

# Patterns that define assertion/selector contexts in test files.
# Each pattern captures a prefix, the string to replace, and a suffix.
# We only replace within these contexts for safety.
TEST_CONTEXT_PATTERNS = [
    # getByRole('button', { name: 'OLD' })  or  { name: "OLD" }
    re.compile(r"""(name:\s*['"])([^'"]+)(['"])"""),
    # getByPlaceholder('OLD')
    re.compile(r"""(getByPlaceholder\(\s*['"])([^'"]+)(['"]\s*\))"""),
    # getByText('OLD')  or  getByText("OLD")
    re.compile(r"""(getByText\(\s*['"])([^'"]+)(['"]\s*\))"""),
    # toContainText('OLD')
    re.compile(r"""(toContainText\(\s*['"])([^'"]+)(['"]\s*\))"""),
    # toHaveText('OLD')
    re.compile(r"""(toHaveText\(\s*['"])([^'"]+)(['"]\s*\))"""),
    # hasText: 'OLD'
    re.compile(r"""(hasText:\s*['"])([^'"]+)(['"])"""),
    # page.getByLabel('OLD')
    re.compile(r"""(getByLabel\(\s*['"])([^'"]+)(['"]\s*\))"""),
]


# ============================================================================
# Git Diff Parsing
# ============================================================================

def run_git_diff(project_path: str, commit1: str, commit2: str) -> str:
    """Run git diff -U0 between two commits for source files."""
    repo_root = find_repo_root(project_path)
    result = subprocess.run(
        [
            "git", "-C", repo_root, "diff", "-U0", commit1, commit2,
            "--", f"{project_path}/src/",
        ],
        capture_output=True, text=True,
    )
    return result.stdout


def find_repo_root(project_path: str) -> str:
    """Find the git repository root from the project path."""
    result = subprocess.run(
        ["git", "-C", project_path, "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def parse_diff_hunks(diff_output: str) -> dict[str, list[HunkStrings]]:
    """
    Parse unified diff output into per-file hunks with removed/added lines.

    Returns: { relative_file_path: [HunkStrings, ...] }
    """
    files: dict[str, list[HunkStrings]] = {}
    current_file: Optional[str] = None
    current_hunk: Optional[HunkStrings] = None

    for line in diff_output.splitlines():
        # New file header: diff --git a/src/... b/src/...
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
                if current_file not in files:
                    files[current_file] = []
            current_hunk = None
            continue

        # Hunk header: @@ -n,m +n,m @@
        if line.startswith("@@") and current_file is not None:
            current_hunk = HunkStrings()
            files[current_file].append(current_hunk)
            continue

        if current_hunk is None:
            continue

        # Removed line
        if line.startswith("-") and not line.startswith("---"):
            current_hunk.removed.append(line[1:])
        # Added line
        elif line.startswith("+") and not line.startswith("+++"):
            current_hunk.added.append(line[1:])

    return files


# ============================================================================
# String Extraction
# ============================================================================

def extract_strings_from_lines(lines: list[str]) -> list[str]:
    """Extract UI-visible string literals from source code lines."""
    strings: list[str] = []
    text = "\n".join(lines)

    for pattern in SOURCE_PATTERNS:
        for match in pattern.finditer(text):
            s = match.group(1).strip()
            if len(s) >= 3:
                # Decode common HTML entities
                s = decode_html_entities(s)
                strings.append(s)

    return strings


def decode_html_entities(s: str) -> str:
    """Decode common HTML entities in a string."""
    replacements = {
        "&apos;": "'",
        "&#39;": "'",
        "&quot;": '"',
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
    }
    for entity, char in replacements.items():
        s = s.replace(entity, char)
    return s


def pair_string_changes(hunks: list[HunkStrings], source_file: str) -> list[StringChange]:
    """
    Pair removed strings with added strings within each hunk by position.
    First removed → first added, second removed → second added, etc.
    """
    changes: list[StringChange] = []

    for hunk in hunks:
        removed_strings = extract_strings_from_lines(hunk.removed)
        added_strings = extract_strings_from_lines(hunk.added)

        # Deduplicate while preserving order
        removed_strings = list(dict.fromkeys(removed_strings))
        added_strings = list(dict.fromkeys(added_strings))

        # Remove strings that appear in both (unchanged)
        common = set(removed_strings) & set(added_strings)
        removed_strings = [s for s in removed_strings if s not in common]
        added_strings = [s for s in added_strings if s not in common]

        # Pair by position
        pairs = min(len(removed_strings), len(added_strings))
        for i in range(pairs):
            changes.append(StringChange(
                old=removed_strings[i],
                new=added_strings[i],
                source_file=source_file,
            ))

        # Log unpaired strings
        if len(removed_strings) > pairs:
            for s in removed_strings[pairs:]:
                print(f"  WARNING: Unpaired removed string: \"{s}\" in {source_file}")
        if len(added_strings) > pairs:
            for s in added_strings[pairs:]:
                print(f"  WARNING: Unpaired added string: \"{s}\" in {source_file}")

    return changes


# ============================================================================
# Test File Replacement
# ============================================================================

def should_skip_line(line: str) -> bool:
    """Check if a line should be skipped for replacement (mock bodies, JSON, etc.)."""
    stripped = line.strip()
    # Skip lines inside JSON.stringify or mock response bodies
    if "JSON.stringify" in line:
        return True
    if "route.fulfill" in line:
        return True
    if "body:" in stripped and "JSON" in line:
        return True
    # Skip regex selectors: { name: /pattern/i }
    if re.search(r"name:\s*/", line):
        return True
    return False


def replace_in_test_file(file_path: str, changes: list[StringChange]) -> bool:
    """
    Replace old strings with new strings in test assertion/selector patterns.

    Returns True if the file was modified.
    """
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r") as f:
        content = f.read()

    original = content

    # Process longer strings first to avoid substring collisions
    sorted_changes = sorted(changes, key=lambda c: len(c.old), reverse=True)

    for change in sorted_changes:
        content = apply_string_change(content, change)

    if content != original:
        with open(file_path, "w") as f:
            f.write(content)
        return True

    return False


def apply_string_change(content: str, change: StringChange) -> str:
    """Apply a single string change across all test context patterns in file content."""
    lines = content.split("\n")
    modified_lines = []

    for line in lines:
        if should_skip_line(line):
            modified_lines.append(line)
            continue

        new_line = line
        for pattern in TEST_CONTEXT_PATTERNS:
            new_line = replace_in_context(new_line, pattern, change.old, change.new)

        modified_lines.append(new_line)

    return "\n".join(modified_lines)


def replace_in_context(line: str, pattern: re.Pattern, old: str, new: str) -> str:
    """Replace old string with new string only within a specific test context pattern."""
    def replacer(match: re.Match) -> str:
        prefix = match.group(1)
        captured = match.group(2)
        suffix = match.group(3)

        # Only replace exact matches of the old string
        if captured == old:
            return f"{prefix}{new}{suffix}"
        return match.group(0)

    return pattern.sub(replacer, line)


# ============================================================================
# Route Resolution
# ============================================================================

def get_impacted_routes(report_path: str) -> list[str]:
    """Read impacted routes from the analysis report JSON."""
    if not os.path.exists(report_path):
        return []

    with open(report_path, "r") as f:
        report = json.load(f)

    return [r["route"] for r in report.get("impacted_routes", [])]


def resolve_test_files(routes: list[str], project_path: str) -> list[str]:
    """Map impacted routes to their test spec files."""
    test_files: set[str] = set()
    login_impacted = False

    for route in routes:
        # Normalize route for matching (handle parameterized routes)
        normalized = route
        for prefix, specs in ROUTE_TO_TEST.items():
            if route == prefix or route.startswith(prefix + "/"):
                for spec in specs:
                    full_path = os.path.join(project_path, spec)
                    if os.path.exists(full_path):
                        test_files.add(spec)
                if prefix == "/auth/login":
                    login_impacted = True

    # Always include auth helper when login is impacted
    if login_impacted:
        helper_path = os.path.join(project_path, AUTH_HELPER)
        if os.path.exists(helper_path):
            test_files.add(AUTH_HELPER)

    return sorted(test_files)


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync UI string changes into Playwright test files"
    )
    parser.add_argument("--project-path", required=True, help="Path to frontend directory")
    parser.add_argument("--commit1", required=True, help="Base commit SHA")
    parser.add_argument("--commit2", required=True, help="Head commit SHA")
    parser.add_argument("--report-json", required=True, help="Path to impacted-routes-report.json")
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    report_path = os.path.join(project_path, args.report_json)

    # 1. Get impacted routes from the analysis report
    routes = get_impacted_routes(report_path)
    if not routes:
        print("  No impacted routes — nothing to sync.")
        return 0

    # 2. Resolve routes to test files
    test_files = resolve_test_files(routes, project_path)
    if not test_files:
        print("  No test files found for impacted routes.")
        return 0

    print(f"  Impacted routes: {', '.join(routes)}")
    print(f"  Test files to check: {', '.join(test_files)}")

    # 3. Get diff and extract string changes
    diff_output = run_git_diff(project_path, args.commit1, args.commit2)
    if not diff_output:
        print("  No diff output — nothing to sync.")
        return 0

    file_hunks = parse_diff_hunks(diff_output)
    if not file_hunks:
        print("  No hunks parsed from diff — nothing to sync.")
        return 0

    # 4. Extract string changes from all changed source files
    all_changes: list[StringChange] = []
    for source_file, hunks in file_hunks.items():
        changes = pair_string_changes(hunks, source_file)
        all_changes.extend(changes)

    if not all_changes:
        print("  No string changes detected in source files.")
        return 0

    print(f"  Found {len(all_changes)} string change(s):")
    for c in all_changes:
        print(f'    "{c.old}" → "{c.new}"  ({c.source_file})')

    # 5. Apply changes to test files
    modified_count = 0
    for test_file in test_files:
        full_path = os.path.join(project_path, test_file)
        if replace_in_test_file(full_path, all_changes):
            modified_count += 1
            print(f"  Updated: {test_file}")

    if modified_count == 0:
        print("  No test files needed updating.")
    else:
        print(f"  {modified_count} test file(s) updated.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
