#!/usr/bin/env python3
"""
Analyze git diff to identify impacted Next.js App Router routes.

Traces the impact chain:
  src/services/ → src/atoms/ → src/components/ → src/app/**/page.tsx

Usage:
    python analyze_diff.py --project-path /path/to/frontend --commit1 abc123 --commit2 def456
    python analyze_diff.py --project-path /path/to/frontend --auto
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
class FileChange:
    file: str           # relative to project_path
    category: str       # page | layout | middleware | component | atom | service | util | hook | type | config | other
    status: str         # added | modified | deleted
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class ImpactedRoute:
    route: str                        # URL path, e.g. /agents or /agents/edit/[type]/[id]
    page_file: str                    # relative path to page.tsx
    impact_type: str                  # direct | transitive | layout | middleware
    trigger_file: Optional[str] = None   # which changed file caused this (for transitive)
    chain: list = field(default_factory=list)  # e.g. ["agentsService.ts", "AgentsAtom.tsx", "AgentListPage.tsx"]


@dataclass
class LayoutImpact:
    layout_file: str
    url_prefix: str       # e.g. "/" for (dashboard) layout
    child_routes: list = field(default_factory=list)


@dataclass
class ImpactReport:
    metadata: dict
    summary: dict
    impacted_routes: list         # list of ImpactedRoute dicts (deduplicated)
    layout_impacts: list          # list of LayoutImpact dicts
    middleware_modified: bool
    files_changed: list           # list of FileChange dicts
    dependency_chains: list       # human-readable chain strings


# ============================================================================
# State Management
# ============================================================================

STATE_DIR = Path.home() / ".claude-skills" / "find-impacted-routes"
STATE_FILE = STATE_DIR / "last_run.json"


def load_state() -> Optional[dict]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_state(commit: str, branch: str, project_path: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "last_run_timestamp": datetime.now(timezone.utc).isoformat(),
        "last_commit_at_run": commit,
        "branch": branch,
        "project_path": project_path,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"  ✓ State saved to {STATE_FILE}")


# ============================================================================
# Git Helpers
# ============================================================================

def run_git(args: list, cwd: str) -> tuple:
    result = subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def get_current_branch(project_path: str) -> str:
    code, stdout, _ = run_git(["branch", "--show-current"], project_path)
    if code != 0:
        raise RuntimeError("Failed to get current branch")
    return stdout.strip()


def get_head_commit(project_path: str) -> str:
    code, stdout, _ = run_git(["rev-parse", "HEAD"], project_path)
    if code != 0:
        raise RuntimeError("Failed to get HEAD commit")
    return stdout.strip()


def get_commit_before_timestamp(project_path: str, timestamp: str, branch: str = None) -> Optional[str]:
    args = ["log", "-1", "--format=%H", f"--before={timestamp}"]
    if branch:
        args.append(branch)
    code, stdout, _ = run_git(args, project_path)
    if code != 0 or not stdout.strip():
        return None
    return stdout.strip()


def verify_commit(project_path: str, commit: str) -> bool:
    code, stdout, _ = run_git(["cat-file", "-t", commit], project_path)
    return code == 0 and stdout.strip() == "commit"


def get_diff_name_status(project_path: str, commit1: str, commit2: str) -> list:
    """Returns list of (status, filepath) tuples for changed files."""
    code, stdout, _ = run_git(["diff", "--name-status", commit1, commit2], project_path)
    if code != 0:
        return []
    results = []
    for line in stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            # Handle rename: R100\told\tnew
            status = parts[0][0]  # A, M, D, R
            filepath = parts[-1]  # last column is the new path
            results.append((status, filepath))
    return results


def get_diff_numstat(project_path: str, commit1: str, commit2: str) -> dict:
    """Returns {filepath: (lines_added, lines_removed)}."""
    code, stdout, _ = run_git(["diff", "--numstat", commit1, commit2], project_path)
    stats = {}
    if code == 0:
        for line in stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0].isdigit() else 0
                removed = int(parts[1]) if parts[1].isdigit() else 0
                stats[parts[2]] = (added, removed)
    return stats


# ============================================================================
# File Categorization
# ============================================================================

def categorize_file(filepath: str) -> str:
    """
    Categorize a filepath into one of:
      page | layout | loading | error | middleware |
      component | atom | service | util | hook | type | config | other
    """
    fp = filepath.replace("\\", "/")

    # Next.js App Router special files
    if re.search(r'src/app/.+/page\.(tsx?|jsx?)$', fp):
        return "page"
    if re.search(r'src/app/.+/layout\.(tsx?|jsx?)$', fp):
        return "layout"
    if re.search(r'src/app/layout\.(tsx?|jsx?)$', fp):
        return "layout"
    if re.search(r'src/app/.+/loading\.(tsx?|jsx?)$', fp):
        return "loading"
    if re.search(r'src/app/.+/error\.(tsx?|jsx?)$', fp):
        return "error"
    if re.search(r'src/app/.+/not-found\.(tsx?|jsx?)$', fp):
        return "error"
    # Root page.tsx
    if re.match(r'src/app/page\.(tsx?|jsx?)$', fp):
        return "page"

    # Middleware
    if re.match(r'src/middleware\.(tsx?|js)$', fp):
        return "middleware"

    # Atoms (Jotai state)
    if re.match(r'src/atoms/', fp):
        return "atom"

    # Services (API layer)
    if re.match(r'src/services/', fp):
        return "service"

    # Components
    if re.match(r'src/components/', fp):
        return "component"

    # Utilities and hooks
    if re.match(r'src/utils/', fp):
        return "util"
    if re.match(r'src/hooks/', fp):
        return "hook"

    # Types
    if re.match(r'src/types/', fp):
        return "type"

    # Config / constants
    if re.match(r'src/constants/', fp) or re.match(r'src/urls\.', fp):
        return "config"

    # App route config files (not page.tsx but still routing-related)
    if re.match(r'src/app/', fp):
        return "app-config"

    return "other"


def is_ts_file(filepath: str) -> bool:
    return filepath.endswith((".ts", ".tsx", ".js", ".jsx"))


# ============================================================================
# Next.js Route Resolution
# ============================================================================

def resolve_route(page_filepath: str) -> str:
    """
    Convert a page.tsx file path to its URL route.

    Examples:
      src/app/page.tsx                              → /
      src/app/(dashboard)/home/page.tsx             → /home
      src/app/auth/login/page.tsx                   → /auth/login
      src/app/(dashboard)/agents/edit/[type]/[id]/page.tsx  → /agents/edit/[type]/[id]
    """
    # Normalize slashes
    fp = page_filepath.replace("\\", "/")

    # Strip src/app prefix
    fp = re.sub(r'^src/app/', '', fp)

    # Strip trailing /page.tsx (and variants)
    fp = re.sub(r'/page\.(tsx?|jsx?)$', '', fp)
    fp = re.sub(r'^page\.(tsx?|jsx?)$', '', fp)  # root page

    # Remove route groups: (groupname)/
    fp = re.sub(r'\([^)]+\)/', '', fp)

    # Clean up leading/trailing slashes
    fp = fp.strip('/')

    return '/' + fp if fp else '/'


def resolve_layout_scope(layout_filepath: str) -> str:
    """
    Determine the URL prefix that a layout.tsx governs.

    Examples:
      src/app/layout.tsx                   → / (root, all routes)
      src/app/(dashboard)/layout.tsx       → / (route group stripped)
      src/app/auth/layout.tsx              → /auth
    """
    fp = layout_filepath.replace("\\", "/")
    fp = re.sub(r'^src/app/', '', fp)
    fp = re.sub(r'/?layout\.(tsx?|jsx?)$', '', fp)

    # Remove route groups
    fp = re.sub(r'\([^)]+\)/?', '', fp)
    fp = fp.strip('/')

    return '/' + fp if fp else '/'


def find_all_pages(project_path: str) -> list:
    """Walk src/app/ and return all page.tsx files with their resolved routes."""
    pages = []
    app_dir = os.path.join(project_path, "src", "app")
    if not os.path.isdir(app_dir):
        return pages
    for root, _dirs, files in os.walk(app_dir):
        for fname in files:
            if re.match(r'page\.(tsx?|jsx?)$', fname):
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, project_path).replace("\\", "/")
                route = resolve_route(rel_path)
                pages.append((route, rel_path))
    return pages


def find_child_routes(layout_filepath: str, all_pages: list) -> list:
    """Find all routes that fall under a given layout's scope."""
    scope = resolve_layout_scope(layout_filepath)

    # For root layout or dashboard layout (scope = /), all routes are children
    if scope == '/':
        return [route for route, _ in all_pages]

    # For a specific prefix, match routes that start with that prefix
    return [route for route, _ in all_pages if route.startswith(scope)]


# ============================================================================
# Import Tracing
# ============================================================================

# Regex to find import statements
IMPORT_PATTERN = re.compile(
    r'''(?:import|from)\s+['"]([^'"]+)['"]''',
    re.MULTILINE
)


def resolve_import_to_filepath(import_path: str, project_path: str) -> Optional[str]:
    """
    Resolve an import path to a relative filepath within the project.

    Handles:
      @/components/agents/AgentListPage  →  src/components/agents/AgentListPage.tsx
      @/atoms/AgentsAtom                 →  src/atoms/AgentsAtom.tsx
    Returns None for external packages.
    """
    if not import_path.startswith('@/') and not import_path.startswith('./') and not import_path.startswith('../'):
        return None  # External package

    if import_path.startswith('@/'):
        # @/ maps to src/
        rel = 'src/' + import_path[2:]
    else:
        rel = import_path  # relative — harder to resolve without context; skip

    # Try common extensions
    for ext in ['', '.tsx', '.ts', '.jsx', '.js']:
        candidate = os.path.join(project_path, rel + ext)
        if os.path.isfile(candidate):
            return (rel + ext).replace("\\", "/")

    # Try as directory with index file
    for ext in ['.tsx', '.ts', '.jsx', '.js']:
        candidate = os.path.join(project_path, rel, 'index' + ext)
        if os.path.isfile(candidate):
            return (rel + '/index' + ext).replace("\\", "/")

    return None


def get_imports_from_file(filepath: str, project_path: str) -> list:
    """Return resolved relative file paths imported by the given file."""
    abs_path = os.path.join(project_path, filepath)
    if not os.path.isfile(abs_path):
        return []
    try:
        content = open(abs_path, encoding='utf-8', errors='ignore').read()
    except IOError:
        return []

    imports = []
    for match in IMPORT_PATTERN.finditer(content):
        resolved = resolve_import_to_filepath(match.group(1), project_path)
        if resolved:
            imports.append(resolved)
    return imports


def build_reverse_import_map(project_path: str, scope_dirs: list) -> dict:
    """
    Build a map of {file → set of files that import it} for all .ts/.tsx files
    in the given directories.

    scope_dirs: relative dirs to scan, e.g. ['src/components', 'src/atoms', 'src/app']
    """
    reverse_map = {}  # filepath → set of importer filepaths

    for scope_dir in scope_dirs:
        abs_scope = os.path.join(project_path, scope_dir)
        if not os.path.isdir(abs_scope):
            continue
        for root, _dirs, files in os.walk(abs_scope):
            for fname in files:
                if not is_ts_file(fname):
                    continue
                abs_file = os.path.join(root, fname)
                rel_file = os.path.relpath(abs_file, project_path).replace("\\", "/")
                for imported in get_imports_from_file(rel_file, project_path):
                    if imported not in reverse_map:
                        reverse_map[imported] = set()
                    reverse_map[imported].add(rel_file)

    return reverse_map


def trace_to_pages(
    start_file: str,
    reverse_map: dict,
    all_pages: list,
    max_depth: int = 5,
) -> list:
    """
    BFS from start_file upward through the reverse import map until we reach page files.
    Returns list of (route, page_file, chain) tuples.
    """
    page_set = {pf for _, pf in all_pages}
    route_lookup = {pf: route for route, pf in all_pages}

    found_routes = []
    visited = set()
    # queue: (current_file, chain_so_far)
    queue = [(start_file, [os.path.basename(start_file)])]

    while queue:
        current, chain = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current in page_set:
            route = route_lookup.get(current, '?')
            found_routes.append((route, current, chain))
            continue  # Don't trace past a page

        if len(chain) > max_depth:
            continue

        importers = reverse_map.get(current, set())
        for importer in importers:
            if importer not in visited:
                queue.append((importer, chain + [os.path.basename(importer)]))

    return found_routes


# ============================================================================
# Protected Routes (from middleware)
# ============================================================================

def get_protected_routes(project_path: str, all_pages: list) -> list:
    """
    Parse src/middleware.ts to find which routes are protected.
    Falls back to assuming all non-auth routes are protected if parsing fails.
    """
    middleware_path = os.path.join(project_path, "src", "middleware.ts")
    if not os.path.isfile(middleware_path):
        middleware_path = os.path.join(project_path, "src", "middleware.tsx")

    if not os.path.isfile(middleware_path):
        return [route for route, _ in all_pages]

    try:
        content = open(middleware_path, encoding='utf-8').read()
    except IOError:
        return [route for route, _ in all_pages]

    # Heuristic: routes NOT matching /auth/** are usually protected
    # Look for matcher config
    matcher_match = re.search(r'matcher[:\s]*\[([^\]]+)\]', content)
    if matcher_match:
        # Return all dashboard pages as affected (simplified)
        return [r for r, _ in all_pages if not r.startswith('/auth')]

    # Default: all non-auth pages
    return [r for r, _ in all_pages if not r.startswith('/auth')]


# ============================================================================
# Main Analysis
# ============================================================================

def analyze(project_path: str, git_root: str, commit1: str, commit2: str, branch: str) -> ImpactReport:
    print(f"\n🔍 Analyzing frontend route impact: {commit1[:8]} → {commit2[:8]}")
    print(f"   Branch:  {branch}")
    print(f"   Project: {project_path}\n")

    # Compute path prefix that git uses (relative from git_root to project_path)
    # e.g. git_root=/repo, project_path=/repo/frontend → prefix = "frontend/"
    prefix = ""
    if git_root != project_path:
        rel = os.path.relpath(project_path, git_root).replace("\\", "/")
        if rel and rel != ".":
            prefix = rel.rstrip("/") + "/"

    # ── Gather changed files ──────────────────────────────────────────────────
    raw_changes = get_diff_name_status(git_root, commit1, commit2)
    diff_stats = get_diff_numstat(git_root, commit1, commit2)

    # Filter to TypeScript/JavaScript files inside this project's src/
    # Strip the monorepo prefix so paths become relative to project_path (e.g. src/...)
    ts_changes = []
    for status, fp in raw_changes:
        # Normalize diff paths that include the monorepo prefix
        if prefix and fp.startswith(prefix):
            local_fp = fp[len(prefix):]
        else:
            local_fp = fp
        if is_ts_file(local_fp) and local_fp.startswith('src/'):
            ts_changes.append((status, local_fp))

    # Also fix diff_stats keys the same way
    normalized_stats = {}
    for fp, stat in diff_stats.items():
        if prefix and fp.startswith(prefix):
            normalized_stats[fp[len(prefix):]] = stat
        else:
            normalized_stats[fp] = stat
    diff_stats = normalized_stats

    if not ts_changes:
        print("⚠️  No TypeScript/JavaScript files changed under src/.")

    # ── Categorize files ─────────────────────────────────────────────────────
    file_changes = []
    status_map = {'A': 'added', 'M': 'modified', 'D': 'deleted', 'R': 'renamed'}

    for status, fp in ts_changes:
        cat = categorize_file(fp)
        stats = diff_stats.get(fp, (0, 0))
        fc = FileChange(
            file=fp,
            category=cat,
            status=status_map.get(status, 'modified'),
            lines_added=stats[0],
            lines_removed=stats[1],
        )
        file_changes.append(fc)
        print(f"  [{cat:12s}] {fp}  ({fc.status}, +{fc.lines_added}/-{fc.lines_removed})")

    print()

    # ── Discover all pages in the project ────────────────────────────────────
    all_pages = find_all_pages(project_path)
    page_file_set = {pf for _, pf in all_pages}

    # ── Build reverse import map (needed for transitive tracing) ─────────────
    print("  📐 Building import graph...")
    reverse_map = build_reverse_import_map(
        project_path,
        ['src/components', 'src/atoms', 'src/services', 'src/utils', 'src/hooks', 'src/app'],
    )
    print(f"     Indexed {len(reverse_map)} imported files.\n")

    # ── Classify changed files into impact buckets ────────────────────────────
    pages_changed = [fc for fc in file_changes if fc.category == 'page']
    layouts_changed = [fc for fc in file_changes if fc.category == 'layout']
    middleware_changed = any(fc.category == 'middleware' for fc in file_changes)
    traceable_changes = [
        fc for fc in file_changes
        if fc.category in ('component', 'atom', 'service', 'util', 'hook', 'config')
    ]

    impacted_routes: list = []     # final deduplicated list
    seen_routes: set = set()
    dependency_chains: list = []

    def add_route(route, page_file, impact_type, trigger=None, chain=None):
        if route in seen_routes:
            return
        seen_routes.add(route)
        impacted_routes.append(ImpactedRoute(
            route=route,
            page_file=page_file,
            impact_type=impact_type,
            trigger_file=trigger,
            chain=chain or [],
        ))

    # ── Direct page changes ───────────────────────────────────────────────────
    for fc in pages_changed:
        route = resolve_route(fc.file)
        add_route(route, fc.file, 'direct')
        print(f"  🟢 Direct: {route}  ({fc.file})")

    # ── Transitive: trace component/atom/service changes up to pages ──────────
    for fc in traceable_changes:
        hits = trace_to_pages(fc.file, reverse_map, all_pages)
        for route, page_file, chain in hits:
            chain_str = ' → '.join(chain) if chain else fc.file
            dependency_chains.append(
                f"{fc.file} ({fc.category}, {fc.status})\n"
                f"  → {'  → '.join(chain)}\n"
                f"  → {route}  [{page_file}]"
            )
            add_route(route, page_file, 'transitive', trigger=fc.file, chain=chain)
            print(f"  🔵 Transitive: {route}  via {os.path.basename(fc.file)} → {chain_str}")

    # ── Layout impacts ────────────────────────────────────────────────────────
    layout_impacts = []
    for fc in layouts_changed:
        scope = resolve_layout_scope(fc.file)
        child_routes = find_child_routes(fc.file, all_pages)
        layout_impacts.append(LayoutImpact(
            layout_file=fc.file,
            url_prefix=scope,
            child_routes=child_routes,
        ))
        print(f"  🟡 Layout changed: {fc.file}  →  affects {len(child_routes)} child routes")
        # Add child routes as layout-impacted (don't duplicate already direct/transitive)
        for child_route in child_routes:
            page_file = next((pf for r, pf in all_pages if r == child_route), child_route)
            if child_route not in seen_routes:
                add_route(child_route, page_file, 'layout', trigger=fc.file)

    # ── Middleware impact ─────────────────────────────────────────────────────
    protected = []
    if middleware_changed:
        protected = get_protected_routes(project_path, all_pages)
        print(f"  🔴 Middleware modified → {len(protected)} protected routes affected")

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = {
        'direct_route_changes': sum(1 for r in impacted_routes if r.impact_type == 'direct'),
        'transitive_impacts': sum(1 for r in impacted_routes if r.impact_type == 'transitive'),
        'layout_impacts': sum(1 for r in impacted_routes if r.impact_type == 'layout'),
        'middleware_modified': middleware_changed,
        'total_unique_routes': len(impacted_routes),
        'files_changed_total': len(file_changes),
    }

    metadata = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'commit1': commit1,
        'commit2': commit2,
        'branch': branch,
        'project_path': project_path,
    }

    return ImpactReport(
        metadata=metadata,
        summary=summary,
        impacted_routes=[asdict(r) for r in impacted_routes],
        layout_impacts=[asdict(li) for li in layout_impacts],
        middleware_modified=middleware_changed,
        files_changed=[asdict(fc) for fc in file_changes],
        dependency_chains=dependency_chains,
    )


# ============================================================================
# Report Generation
# ============================================================================

def generate_markdown(report: ImpactReport, all_pages: list) -> str:
    md = []
    m = report.metadata

    md.append("# Impacted Routes Report\n")
    md.append(f"> Generated: {m['generated_at']}")
    md.append(f"> Comparing: `{m['commit1'][:8]}` → `{m['commit2'][:8]}`")
    md.append(f"> Branch: `{m['branch']}`\n")

    # ── Summary ────────────────────────────────────────────────────────────
    s = report.summary
    md.append("## Summary\n")
    md.append("| Category | Count |")
    md.append("|----------|-------|")
    md.append(f"| Direct route changes | {s['direct_route_changes']} |")
    md.append(f"| Transitively impacted routes | {s['transitive_impacts']} |")
    md.append(f"| Layout-impacted routes | {s['layout_impacts']} |")
    md.append(f"| Middleware modified | {'✅ Yes' if s['middleware_modified'] else '❌ No'} |")
    md.append(f"| **Total unique routes affected** | **{s['total_unique_routes']}** |")
    md.append(f"| Files changed | {s['files_changed_total']} |")
    md.append("")

    # ── Direct Routes ──────────────────────────────────────────────────────
    direct = [r for r in report.impacted_routes if r['impact_type'] == 'direct']
    if direct:
        md.append("---\n")
        md.append("## Directly Modified Routes\n")
        md.append("Routes where `page.tsx` itself was changed.\n")
        md.append("| Route | File | Change |")
        md.append("|-------|------|--------|")
        for r in direct:
            trigger = r.get('trigger_file', r['page_file'])
            fc = next((f for f in report.files_changed if f['file'] == r['page_file']), None)
            change = fc['status'] if fc else 'modified'
            md.append(f"| `{r['route']}` | `{r['page_file']}` | {change} |")
        md.append("")

    # ── Transitive Routes ─────────────────────────────────────────────────
    transitive = [r for r in report.impacted_routes if r['impact_type'] == 'transitive']
    if transitive:
        md.append("---\n")
        md.append("## Transitively Impacted Routes\n")
        md.append("Routes affected via shared components, atoms, or services.\n")
        md.append("| Route | File | Via | Impact Chain |")
        md.append("|-------|------|-----|--------------|")
        for r in transitive:
            via = os.path.basename(r.get('trigger_file', '?'))
            chain_str = ' → '.join(r.get('chain', [])) if r.get('chain') else '-'
            md.append(f"| `{r['route']}` | `{r['page_file']}` | `{via}` | {chain_str} |")
        md.append("")

    # ── Layout Changes ────────────────────────────────────────────────────
    if report.layout_impacts:
        md.append("---\n")
        md.append("## Layout Changes\n")
        md.append("These layout files changed — all their child routes inherit the change.\n")
        md.append("| Layout File | URL Scope | Child Routes |")
        md.append("|-------------|-----------|--------------|")
        for li in report.layout_impacts:
            children = ', '.join(f'`{r}`' for r in li['child_routes'][:8])
            overflow = f" (+{len(li['child_routes']) - 8} more)" if len(li['child_routes']) > 8 else ""
            md.append(f"| `{li['layout_file']}` | `{li['url_prefix']}` | {children}{overflow} |")
        md.append("")

    # ── Middleware ────────────────────────────────────────────────────────
    if report.middleware_modified:
        md.append("---\n")
        md.append("## Middleware Modified ⚠️\n")
        md.append("`src/middleware.ts` was changed. This affects all protected routes:\n")
        protected = get_protected_routes_from_pages(all_pages)
        md.append(", ".join(f"`{r}`" for r in protected))
        md.append("")

    # ── Changed Files by Category ─────────────────────────────────────────
    if report.files_changed:
        md.append("---\n")
        md.append("## Changed Files by Category\n")
        md.append("| File | Category | Status | +Lines | -Lines |")
        md.append("|------|----------|--------|--------|--------|")
        for fc in sorted(report.files_changed, key=lambda x: (x['category'], x['file'])):
            md.append(
                f"| `{fc['file']}` | {fc['category']} | {fc['status']} "
                f"| +{fc['lines_added']} | -{fc['lines_removed']} |"
            )
        md.append("")

    # ── Dependency Chains ─────────────────────────────────────────────────
    if report.dependency_chains:
        md.append("---\n")
        md.append("## Dependency Chains\n")
        for chain in report.dependency_chains:
            md.append("```")
            md.append(chain)
            md.append("```\n")

    return "\n".join(md)


def get_protected_routes_from_pages(all_pages: list) -> list:
    return [r for r, _ in all_pages if not r.startswith('/auth')]


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Find impacted Next.js routes from a git diff"
    )
    parser.add_argument("--project-path", "-p", required=True,
                        help="Path to the Next.js frontend project root")
    parser.add_argument("--commit1", "-c1",
                        help="Older commit SHA (before state)")
    parser.add_argument("--commit2", "-c2",
                        help="Newer commit SHA (default: HEAD)")
    parser.add_argument("--branch", "-b",
                        help="Git branch (default: current branch)")
    parser.add_argument("--auto", "-a", action="store_true",
                        help="Auto-detect commit1 from last run state")
    parser.add_argument("--output", "-o",
                        help="Output directory for reports (default: project-path)")
    parser.add_argument("--no-save-state", action="store_true",
                        help="Skip updating the last run state file")
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)

    # Verify git repo
    if not os.path.isdir(os.path.join(project_path, ".git")):
        # Try parent (in case project_path is frontend/ inside a monorepo)
        parent = os.path.dirname(project_path)
        if os.path.isdir(os.path.join(parent, ".git")):
            git_root = parent
        else:
            print(f"❌ {project_path} is not a git repository (checked parent too)")
            sys.exit(1)
    else:
        git_root = project_path

    branch = args.branch or get_current_branch(git_root)
    commit2 = args.commit2 or get_head_commit(git_root)

    if args.commit1:
        commit1 = args.commit1
    elif args.auto:
        state = load_state()
        if state and state.get("last_run_timestamp"):
            commit1 = get_commit_before_timestamp(
                git_root, state["last_run_timestamp"], branch
            )
            if not commit1:
                print("❌ Could not find commit before last run timestamp. Use --commit1.")
                sys.exit(1)
            print(f"  ℹ️  Using commit from last run: {commit1[:8]}")
        else:
            print("❌ No previous run state. Provide --commit1 or run once explicitly.")
            sys.exit(1)
    else:
        print("❌ Provide --commit1 or use --auto to use last run state.")
        sys.exit(1)

    # Validate commits
    for commit, label in [(commit1, "commit1"), (commit2, "commit2")]:
        if not verify_commit(git_root, commit):
            print(f"❌ {label} '{commit}' not found in repository.")
            sys.exit(1)

    # Run analysis — git commands use git_root, file scanning uses project_path
    report = analyze(project_path, git_root, commit1, commit2, branch)

    # Discover all pages for the markdown report
    all_pages = find_all_pages(project_path)

    # Output directory
    output_dir = args.output or project_path

    # Save JSON
    json_path = os.path.join(output_dir, "impacted-routes-report.json")
    with open(json_path, "w") as f:
        json.dump(asdict(report), f, indent=2)
    print(f"\n  ✅ JSON report saved:     {json_path}")

    # Save Markdown
    md_content = generate_markdown(report, all_pages)
    md_path = os.path.join(output_dir, "impacted-routes-report.md")
    with open(md_path, "w") as f:
        f.write(md_content)
    print(f"  ✅ Markdown report saved: {md_path}")

    # Update state
    if not args.no_save_state:
        save_state(commit2, branch, project_path)

    # Print summary
    s = report.summary
    print("\n" + "=" * 56)
    print("📍 IMPACTED ROUTES SUMMARY")
    print("=" * 56)
    print(f"  Direct route changes      : {s['direct_route_changes']}")
    print(f"  Transitive route impacts  : {s['transitive_impacts']}")
    print(f"  Layout-impacted routes    : {s['layout_impacts']}")
    print(f"  Middleware modified       : {'YES ⚠️' if s['middleware_modified'] else 'No'}")
    print(f"  ─────────────────────────────────────")
    print(f"  Total unique routes       : {s['total_unique_routes']}")
    print(f"  Files changed             : {s['files_changed_total']}")
    print("=" * 56)

    if report.impacted_routes:
        print("\n  Routes:")
        for r in report.impacted_routes:
            tag = {'direct': '🟢', 'transitive': '🔵', 'layout': '🟡', 'middleware': '🔴'}.get(
                r['impact_type'], '⚪'
            )
            print(f"    {tag} {r['route']}  ({r['impact_type']})")
    print()


if __name__ == "__main__":
    main()
