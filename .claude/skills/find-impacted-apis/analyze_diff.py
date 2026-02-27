#!/usr/bin/env python3
"""
Analyze git diff to identify impacted FastAPI controllers, services, and models.

Usage:
    python analyze_diff.py --project-path /path/to/repo --commit1 abc123 --commit2 def456
    python analyze_diff.py --project-path /path/to/repo --auto  # Uses last run state
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class EndpointChange:
    method: str
    path: str
    function: str
    file: str
    change_type: str  # added, modified, deleted
    line_number: Optional[int] = None


@dataclass
class ServiceChange:
    class_name: Optional[str]
    function: str
    file: str
    change_type: str


@dataclass
class ModelChange:
    model: str
    table: Optional[str]
    file: str
    added_fields: list = field(default_factory=list)
    removed_fields: list = field(default_factory=list)
    modified_fields: list = field(default_factory=list)


@dataclass
class FileChange:
    file: str
    status: str  # A (added), M (modified), D (deleted)
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class ImpactReport:
    metadata: dict
    summary: dict
    impacted_endpoints: list
    impacted_services: list
    impacted_models: list
    files_changed: list
    dependency_chains: list = field(default_factory=list)


# ============================================================================
# State Management
# ============================================================================

STATE_DIR = Path.home() / ".claude-skills" / "find-impacted-apis"
STATE_FILE = STATE_DIR / "last_run.json"


def load_state() -> Optional[dict]:
    """Load the last run state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_state(commit: str, branch: str, project_path: str):
    """Save current run state to file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "last_run_timestamp": datetime.now(timezone.utc).isoformat(),
        "last_commit_at_run": commit,
        "branch": branch,
        "project_path": project_path
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"✓ State saved to {STATE_FILE}")


# ============================================================================
# Git Operations
# ============================================================================

def run_git(args: list, cwd: str) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def get_current_branch(project_path: str) -> str:
    """Get the current git branch."""
    code, stdout, _ = run_git(["branch", "--show-current"], project_path)
    if code != 0:
        raise RuntimeError("Failed to get current branch")
    return stdout.strip()


def get_head_commit(project_path: str) -> str:
    """Get the current HEAD commit SHA."""
    code, stdout, _ = run_git(["rev-parse", "HEAD"], project_path)
    if code != 0:
        raise RuntimeError("Failed to get HEAD commit")
    return stdout.strip()


def get_commit_before_timestamp(project_path: str, timestamp: str, branch: str = None) -> Optional[str]:
    """Get the last commit before a given timestamp."""
    args = ["log", "-1", "--format=%H", f"--before={timestamp}"]
    if branch:
        args.append(branch)
    code, stdout, _ = run_git(args, project_path)
    if code != 0 or not stdout.strip():
        return None
    return stdout.strip()


def verify_commit_exists(project_path: str, commit: str) -> bool:
    """Verify that a commit exists in the repository."""
    code, stdout, _ = run_git(["cat-file", "-t", commit], project_path)
    return code == 0 and stdout.strip() == "commit"


def get_diff_name_status(project_path: str, commit1: str, commit2: str) -> list[tuple[str, str]]:
    """Get list of changed files with their status."""
    code, stdout, _ = run_git(["diff", "--name-status", commit1, commit2], project_path)
    if code != 0:
        return []
    
    changes = []
    for line in stdout.strip().split("\n"):
        if line:
            parts = line.split("\t")
            if len(parts) >= 2:
                status, filepath = parts[0], parts[1]
                changes.append((status, filepath))
    return changes


def get_diff_content(project_path: str, commit1: str, commit2: str, file_pattern: str = "*.py") -> str:
    """Get the full diff content for matching files."""
    code, stdout, _ = run_git(
        ["diff", commit1, commit2, "--", file_pattern],
        project_path
    )
    return stdout if code == 0 else ""


def get_diff_stat(project_path: str, commit1: str, commit2: str) -> dict[str, tuple[int, int]]:
    """Get lines added/removed per file."""
    code, stdout, _ = run_git(["diff", "--numstat", commit1, commit2], project_path)
    if code != 0:
        return {}
    
    stats = {}
    for line in stdout.strip().split("\n"):
        if line:
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0] != "-" else 0
                removed = int(parts[1]) if parts[1] != "-" else 0
                filepath = parts[2]
                stats[filepath] = (added, removed)
    return stats


# ============================================================================
# FastAPI Code Parsing
# ============================================================================

# Patterns for FastAPI routes
ROUTE_PATTERNS = [
    re.compile(r'@(?:router|app)\.(get|post|put|patch|delete|head|options)\s*\(\s*["\']([^"\']+)["\']'),
    re.compile(r'@(?:router|app)\.(get|post|put|patch|delete|head|options)\s*\(\s*path\s*=\s*["\']([^"\']+)["\']'),
]

# Pattern for function definitions
FUNC_PATTERN = re.compile(r'^[+-]?\s*(async\s+)?def\s+(\w+)\s*\(')

# Pattern for class definitions
CLASS_PATTERN = re.compile(r'^[+-]?\s*class\s+(\w+)\s*(?:\(([^)]*)\))?:')

# Pattern for SQLAlchemy columns
COLUMN_PATTERN = re.compile(r'(\w+)\s*=\s*(?:Column|relationship|mapped_column)\s*\(')

# Pattern for table name
TABLE_PATTERN = re.compile(r'__tablename__\s*=\s*["\'](\w+)["\']')

# Pattern for router prefix
PREFIX_PATTERN = re.compile(r'APIRouter\s*\([^)]*prefix\s*=\s*["\']([^"\']+)["\']')


def is_controller_file(filepath: str) -> bool:
    """Check if file is likely a controller/router file."""
    lower = filepath.lower()
    return any(x in lower for x in [
        "controller", "router", "route", "api/", "endpoints/", "views/"
    ]) and filepath.endswith(".py")


def is_service_file(filepath: str) -> bool:
    """Check if file is likely a service file."""
    lower = filepath.lower()
    return any(x in lower for x in [
        "service", "handler", "manager", "usecase", "interactor"
    ]) and filepath.endswith(".py")


def is_model_file(filepath: str) -> bool:
    """Check if file is likely a model file."""
    lower = filepath.lower()
    return any(x in lower for x in [
        "model", "entity", "schema", "dto"
    ]) and filepath.endswith(".py")


def parse_diff_hunks(diff_content: str) -> dict[str, list[dict]]:
    """
    Parse git diff into structured hunks per file.
    Returns: {filepath: [{"header": str, "added": [], "removed": [], "context": []}]}
    """
    files = {}
    current_file = None
    current_hunk = None
    
    lines = diff_content.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # New file
        if line.startswith("diff --git"):
            match = re.search(r'b/(.+)$', line)
            if match:
                current_file = match.group(1)
                files[current_file] = []
        
        # Hunk header
        elif line.startswith("@@"):
            if current_file:
                current_hunk = {
                    "header": line,
                    "added": [],
                    "removed": [],
                    "context": []
                }
                files[current_file].append(current_hunk)
        
        # Added line
        elif line.startswith("+") and not line.startswith("+++"):
            if current_hunk:
                current_hunk["added"].append(line[1:])
        
        # Removed line
        elif line.startswith("-") and not line.startswith("---"):
            if current_hunk:
                current_hunk["removed"].append(line[1:])
        
        # Context line
        elif line.startswith(" "):
            if current_hunk:
                current_hunk["context"].append(line[1:])
        
        i += 1
    
    return files


def extract_endpoints_from_diff(filepath: str, hunks: list[dict], status: str) -> list[EndpointChange]:
    """Extract endpoint changes from diff hunks."""
    endpoints = []
    
    for hunk in hunks:
        # Check added lines for new/modified routes
        for line in hunk["added"]:
            for pattern in ROUTE_PATTERNS:
                match = pattern.search(line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    # Try to find the function name in nearby lines
                    func_name = "unknown"
                    all_lines = hunk["added"] + hunk["context"]
                    for nearby in all_lines:
                        func_match = FUNC_PATTERN.search(nearby)
                        if func_match:
                            func_name = func_match.group(2)
                            break
                    
                    change_type = "added" if status == "A" else "modified"
                    endpoints.append(EndpointChange(
                        method=method,
                        path=path,
                        function=func_name,
                        file=filepath,
                        change_type=change_type
                    ))
        
        # Check removed lines for deleted routes
        for line in hunk["removed"]:
            for pattern in ROUTE_PATTERNS:
                match = pattern.search(line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)
                    
                    # Only mark as deleted if the file is deleted or route not in added
                    is_deleted = status == "D" or not any(
                        path in added_line 
                        for added_line in hunk["added"]
                    )
                    
                    if is_deleted:
                        endpoints.append(EndpointChange(
                            method=method,
                            path=path,
                            function="unknown",
                            file=filepath,
                            change_type="deleted"
                        ))
    
    return endpoints


def extract_services_from_diff(filepath: str, hunks: list[dict], status: str) -> list[ServiceChange]:
    """Extract service function changes from diff hunks."""
    services = []
    current_class = None
    
    for hunk in hunks:
        all_lines = hunk["context"] + hunk["added"] + hunk["removed"]
        
        # Find class context
        for line in all_lines:
            class_match = CLASS_PATTERN.search(line)
            if class_match:
                current_class = class_match.group(1)
        
        # Check for function changes
        for line in hunk["added"]:
            func_match = FUNC_PATTERN.search(line)
            if func_match:
                func_name = func_match.group(2)
                if not func_name.startswith("_"):  # Skip private methods
                    change_type = "added" if status == "A" else "modified"
                    services.append(ServiceChange(
                        class_name=current_class,
                        function=func_name,
                        file=filepath,
                        change_type=change_type
                    ))
        
        for line in hunk["removed"]:
            func_match = FUNC_PATTERN.search(line)
            if func_match:
                func_name = func_match.group(2)
                # Check if truly deleted (not just modified)
                is_deleted = status == "D" or not any(
                    f"def {func_name}" in added_line
                    for added_line in hunk["added"]
                )
                if is_deleted and not func_name.startswith("_"):
                    services.append(ServiceChange(
                        class_name=current_class,
                        function=func_name,
                        file=filepath,
                        change_type="deleted"
                    ))
    
    return services


def extract_models_from_diff(filepath: str, hunks: list[dict], status: str) -> list[ModelChange]:
    """Extract model changes from diff hunks."""
    models = {}  # model_name -> ModelChange
    current_model = None
    
    for hunk in hunks:
        all_lines = hunk["context"] + hunk["added"] + hunk["removed"]
        
        # Find model class
        for line in all_lines:
            class_match = CLASS_PATTERN.search(line)
            if class_match:
                class_name = class_match.group(1)
                bases = class_match.group(2) or ""
                # Check if it's likely a model (inherits from Base, BaseModel, etc.)
                if any(x in bases for x in ["Base", "Model", "Entity", "Table"]):
                    current_model = class_name
                    if current_model not in models:
                        models[current_model] = ModelChange(
                            model=current_model,
                            table=None,
                            file=filepath
                        )
        
        # Find table name
        for line in all_lines:
            table_match = TABLE_PATTERN.search(line)
            if table_match and current_model and current_model in models:
                models[current_model].table = table_match.group(1)
        
        # Find added fields
        for line in hunk["added"]:
            col_match = COLUMN_PATTERN.search(line)
            if col_match and current_model and current_model in models:
                field_name = col_match.group(1)
                if field_name not in models[current_model].added_fields:
                    models[current_model].added_fields.append(field_name)
        
        # Find removed fields
        for line in hunk["removed"]:
            col_match = COLUMN_PATTERN.search(line)
            if col_match and current_model and current_model in models:
                field_name = col_match.group(1)
                # Check if actually removed vs modified
                is_in_added = any(
                    field_name in added_line
                    for added_line in hunk["added"]
                )
                if is_in_added:
                    if field_name not in models[current_model].modified_fields:
                        models[current_model].modified_fields.append(field_name)
                else:
                    if field_name not in models[current_model].removed_fields:
                        models[current_model].removed_fields.append(field_name)
    
    return list(models.values())


# ============================================================================
# Main Analysis
# ============================================================================

def analyze(project_path: str, commit1: str, commit2: str, branch: str) -> ImpactReport:
    """Run the full analysis and return an ImpactReport."""
    
    print(f"\n📊 Analyzing changes: {commit1[:8]} → {commit2[:8]}")
    print(f"   Branch: {branch}")
    print(f"   Project: {project_path}\n")
    
    # Get changed files
    file_changes = get_diff_name_status(project_path, commit1, commit2)
    diff_stats = get_diff_stat(project_path, commit1, commit2)
    
    # Filter to Python files
    py_changes = [(s, f) for s, f in file_changes if f.endswith(".py")]
    
    if not py_changes:
        print("⚠️  No Python files changed between these commits.")
    
    # Get full diff for Python files
    diff_content = get_diff_content(project_path, commit1, commit2)
    parsed_hunks = parse_diff_hunks(diff_content)
    
    # Collect all changes
    all_endpoints = []
    all_services = []
    all_models = []
    all_files = []
    
    for status, filepath in py_changes:
        hunks = parsed_hunks.get(filepath, [])
        stats = diff_stats.get(filepath, (0, 0))
        
        # Record file change
        status_map = {"A": "added", "M": "modified", "D": "deleted"}
        all_files.append(FileChange(
            file=filepath,
            status=status_map.get(status, "modified"),
            lines_added=stats[0],
            lines_removed=stats[1]
        ))
        
        # Extract changes based on file type
        if is_controller_file(filepath):
            endpoints = extract_endpoints_from_diff(filepath, hunks, status)
            all_endpoints.extend(endpoints)
            print(f"  📌 {filepath}: {len(endpoints)} endpoint(s)")
        
        if is_service_file(filepath):
            services = extract_services_from_diff(filepath, hunks, status)
            all_services.extend(services)
            print(f"  ⚙️  {filepath}: {len(services)} service function(s)")
        
        if is_model_file(filepath):
            models = extract_models_from_diff(filepath, hunks, status)
            all_models.extend(models)
            print(f"  🗃️  {filepath}: {len(models)} model(s)")
    
    # Build summary
    def count_by_type(items, attr="change_type"):
        counts = {"added": 0, "modified": 0, "deleted": 0}
        for item in items:
            ct = getattr(item, attr, "modified")
            if ct in counts:
                counts[ct] += 1
        return counts
    
    summary = {
        "endpoints": count_by_type(all_endpoints),
        "services": count_by_type(all_services),
        "models": {
            "added": sum(1 for m in all_models if m.added_fields and not m.removed_fields),
            "modified": sum(1 for m in all_models if m.modified_fields or (m.added_fields and m.removed_fields)),
            "deleted": sum(1 for m in all_models if m.removed_fields and not m.added_fields)
        }
    }
    
    # Build metadata
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit1": commit1,
        "commit2": commit2,
        "branch": branch,
        "project_path": project_path
    }
    
    return ImpactReport(
        metadata=metadata,
        summary=summary,
        impacted_endpoints=[asdict(e) for e in all_endpoints],
        impacted_services=[asdict(s) for s in all_services],
        impacted_models=[asdict(m) for m in all_models],
        files_changed=[asdict(f) for f in all_files]
    )


def generate_markdown_report(report: ImpactReport) -> str:
    """Generate a markdown report from the ImpactReport."""
    
    md = []
    md.append("# Impacted APIs Report\n")
    md.append(f"> Generated: {report.metadata['generated_at']}")
    md.append(f"> Comparing: `{report.metadata['commit1'][:8]}` → `{report.metadata['commit2'][:8]}`")
    md.append(f"> Branch: {report.metadata['branch']}\n")
    
    # Summary table
    md.append("## Summary\n")
    md.append("| Category | Added | Modified | Deleted |")
    md.append("|----------|-------|----------|---------|")
    for cat in ["endpoints", "services", "models"]:
        s = report.summary.get(cat, {})
        md.append(f"| {cat.title()} | {s.get('added', 0)} | {s.get('modified', 0)} | {s.get('deleted', 0)} |")
    md.append("")
    
    # Impacted Endpoints
    if report.impacted_endpoints:
        md.append("## Impacted API Endpoints\n")
        
        for change_type in ["added", "modified", "deleted"]:
            eps = [e for e in report.impacted_endpoints if e["change_type"] == change_type]
            if eps:
                md.append(f"### {change_type.title()} Endpoints\n")
                md.append("| Method | Path | Function | File |")
                md.append("|--------|------|----------|------|")
                for e in eps:
                    md.append(f"| {e['method']} | `{e['path']}` | `{e['function']}` | `{e['file']}` |")
                md.append("")
    
    # Impacted Services
    if report.impacted_services:
        md.append("## Impacted Service Functions\n")
        md.append("| Class | Function | File | Change |")
        md.append("|-------|----------|------|--------|")
        for s in report.impacted_services:
            cls = s["class_name"] or "-"
            md.append(f"| {cls} | `{s['function']}` | `{s['file']}` | {s['change_type']} |")
        md.append("")
    
    # Impacted Models
    if report.impacted_models:
        md.append("## Impacted Models\n")
        for m in report.impacted_models:
            table_info = f" (`{m['table']}`)" if m["table"] else ""
            md.append(f"### {m['model']}{table_info}\n")
            md.append(f"**File:** `{m['file']}`\n")
            if m["added_fields"]:
                md.append(f"- **Added fields:** {', '.join(m['added_fields'])}")
            if m["removed_fields"]:
                md.append(f"- **Removed fields:** {', '.join(m['removed_fields'])}")
            if m["modified_fields"]:
                md.append(f"- **Modified fields:** {', '.join(m['modified_fields'])}")
            md.append("")
    
    # Files Changed
    if report.files_changed:
        md.append("## Files Changed\n")
        md.append("| File | Status | +Lines | -Lines |")
        md.append("|------|--------|--------|--------|")
        for f in report.files_changed:
            md.append(f"| `{f['file']}` | {f['status']} | +{f['lines_added']} | -{f['lines_removed']} |")
        md.append("")
    
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="Find impacted FastAPI endpoints, services, and models")
    parser.add_argument("--project-path", "-p", required=True, help="Path to git repository")
    parser.add_argument("--commit1", "-c1", help="Start commit (older)")
    parser.add_argument("--commit2", "-c2", help="End commit (newer)")
    parser.add_argument("--branch", "-b", help="Git branch (default: current)")
    parser.add_argument("--auto", "-a", action="store_true", help="Auto-detect commits from last run")
    parser.add_argument("--output", "-o", help="Output directory for reports (default: project-path)")
    parser.add_argument("--no-save-state", action="store_true", help="Don't update last run state")
    
    args = parser.parse_args()
    
    project_path = os.path.abspath(args.project_path)
    
    # Verify it's a git repo
    if not os.path.isdir(os.path.join(project_path, ".git")):
        print(f"❌ Error: {project_path} is not a git repository")
        sys.exit(1)
    
    # Determine branch
    branch = args.branch or get_current_branch(project_path)
    
    # Determine commits
    commit2 = args.commit2 or get_head_commit(project_path)
    
    if args.commit1:
        commit1 = args.commit1
    elif args.auto:
        state = load_state()
        if state and state.get("last_run_timestamp"):
            commit1 = get_commit_before_timestamp(
                project_path, 
                state["last_run_timestamp"],
                branch
            )
            if not commit1:
                print("❌ Error: Could not find commit before last run timestamp")
                print("   Try providing --commit1 explicitly")
                sys.exit(1)
            print(f"ℹ️  Using commit from last run: {commit1[:8]}")
        else:
            print("❌ Error: No previous run state found. Cannot use --auto")
            print("   Run once with explicit --commit1 and --commit2")
            sys.exit(1)
    else:
        print("❌ Error: Must provide --commit1 or use --auto")
        sys.exit(1)
    
    # Verify commits exist
    if not verify_commit_exists(project_path, commit1):
        print(f"❌ Error: Commit {commit1} not found")
        sys.exit(1)
    if not verify_commit_exists(project_path, commit2):
        print(f"❌ Error: Commit {commit2} not found")
        sys.exit(1)
    
    # Run analysis
    report = analyze(project_path, commit1, commit2, branch)
    
    # Output directory
    output_dir = args.output or project_path
    
    # Save JSON report
    json_path = os.path.join(output_dir, "impacted-apis-report.json")
    with open(json_path, "w") as f:
        json.dump(asdict(report), f, indent=2)
    print(f"\n✅ JSON report saved: {json_path}")
    
    # Save Markdown report
    md_content = generate_markdown_report(report)
    md_path = os.path.join(output_dir, "impacted-apis-report.md")
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"✅ Markdown report saved: {md_path}")
    
    # Update state
    if not args.no_save_state:
        save_state(commit2, branch, project_path)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 IMPACT SUMMARY")
    print("=" * 50)
    for cat in ["endpoints", "services", "models"]:
        s = report.summary.get(cat, {})
        total = s.get("added", 0) + s.get("modified", 0) + s.get("deleted", 0)
        if total > 0:
            print(f"  {cat.title()}: {total} ({s.get('added', 0)} added, {s.get('modified', 0)} modified, {s.get('deleted', 0)} deleted)")
    print(f"  Files changed: {len(report.files_changed)}")
    print("=" * 50)


if __name__ == "__main__":
    main()