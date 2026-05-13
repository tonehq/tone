#!/usr/bin/env python3
"""
Neon CLI wrapper for provisioning-db skill.

Wraps neonctl commands with --org-id to skip interactive prompts.
All output is JSON for easy parsing.

Usage:
    python neon_api.py check              # Check if neonctl is installed
    python neon_api.py list-orgs          # List organizations
    python neon_api.py list-projects --org-id <ORG_ID>
    python neon_api.py create-project --org-id <ORG_ID> --name <NAME> --region <REGION>
    python neon_api.py list-branches --project-id <PROJECT_ID>
    python neon_api.py create-role --project-id <PID> --branch-id <BID> --name <NAME>
    python neon_api.py create-database --project-id <PID> --branch-id <BID> --name <NAME> --owner <OWNER>
    python neon_api.py connection-string --project-id <PID> --database <DB> --role <ROLE>
"""

import argparse
import json
import subprocess
import sys
import shutil
from urllib.parse import urlparse, parse_qs


def run_neonctl(args_list, timeout=30):
    """Run a neonctl command and return parsed JSON output."""
    cmd = ["neonctl"] + args_list + ["--output", "json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {"error": error_msg}, result.returncode
        try:
            return json.loads(result.stdout), 0
        except json.JSONDecodeError:
            return {"raw": result.stdout.strip()}, 0
    except FileNotFoundError:
        return {"error": "neonctl not found. Install: npm i -g neonctl"}, 1
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}, 1


def cmd_check(args):
    """Check if neonctl is installed."""
    path = shutil.which("neonctl")
    if path:
        result = subprocess.run(["neonctl", "--version"], capture_output=True, text=True, timeout=5)
        version = result.stdout.strip()
        print(json.dumps({"status": "ok", "path": path, "version": version}))
    else:
        print(json.dumps({"status": "not_installed", "message": "Install: npm i -g neonctl && neonctl auth"}))
        sys.exit(1)


def _region_id_to_name(region_id):
    """Convert region ID to human-readable name from the ID itself."""
    import re as _re

    # Known city mappings for common AWS region suffixes
    city_map = {
        "aws-us-east-1": "N. Virginia",
        "aws-us-east-2": "Ohio",
        "aws-us-west-1": "N. California",
        "aws-us-west-2": "Oregon",
        "aws-ap-southeast-1": "Singapore",
        "aws-ap-southeast-2": "Sydney",
        "aws-ap-northeast-1": "Tokyo",
        "aws-ap-south-1": "Mumbai",
        "aws-eu-central-1": "Frankfurt",
        "aws-eu-west-1": "Ireland",
        "aws-eu-west-2": "London",
        "aws-eu-north-1": "Stockholm",
        "aws-sa-east-1": "São Paulo",
        "aws-ca-central-1": "Canada",
        "aws-me-south-1": "Bahrain",
        "azure-eastus2": "Virginia",
    }

    city = city_map.get(region_id, "")

    parts = region_id.split("-")
    provider = parts[0].upper()

    if provider == "AWS" and len(parts) >= 4:
        geo_map = {"us": "US", "eu": "Europe", "ap": "Asia Pacific", "sa": "South America", "ca": "Canada", "me": "Middle East", "af": "Africa"}
        geo = geo_map.get(parts[1], parts[1].upper())
        direction = " ".join(p.capitalize() for p in parts[2:-1])
        num = parts[-1]
        base = f"AWS {geo} {direction} {num}"
    elif provider == "AZURE":
        base = f"Azure {'-'.join(parts[1:])}"
    else:
        base = region_id

    return f"{base} ({city})" if city else base


def cmd_list_regions(args):
    """List available Neon regions by parsing neonctl help output."""
    import re
    try:
        result = subprocess.run(
            ["neonctl", "projects", "create", "--help"],
            capture_output=True, text=True, timeout=10
        )
        # Help output may be in stdout or stderr
        text = (result.stdout + " " + result.stderr).replace("\n", " ")
        match = re.search(r'Possible values:\s*(.*?)\s*\[string\]', text)
        if match:
            raw = match.group(1)
            raw = re.sub(r'[└─│>]', '', raw)
            raw = re.sub(r'\s+', ' ', raw)
            # Remove spaces within region IDs (caused by text wrapping in terminal)
            # Matches patterns like "southe ast" -> "southeast"
            raw = re.sub(r'(\w)\s+(\w)', lambda m: m.group(1) + m.group(2) if m.start() > 0 and raw[m.start()-1:m.start()] != ',' else m.group(0), raw)
            # Simpler approach: rejoin any split words between commas
            parts_list = [p.strip() for p in raw.split(',')]
            region_ids = []
            for p in parts_list:
                # Remove any remaining internal spaces in region IDs
                cleaned = re.sub(r'\s+', '', p) if not p.startswith('azure') else p.replace(' ', '')
                if cleaned:
                    region_ids.append(cleaned)
            # region_ids already built above
            regions = []
            for rid in region_ids:
                name = _region_id_to_name(rid)
                regions.append({"id": rid, "name": name})
            print(json.dumps({"regions": regions}))
        else:
            print(json.dumps({"error": "Could not parse regions from neonctl help"}))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def cmd_list_orgs(args):
    """List organizations."""
    data, code = run_neonctl(["orgs", "list"])
    if code != 0:
        print(json.dumps(data))
        sys.exit(1)
    orgs = [{"name": o["name"], "id": o["id"], "plan": o.get("plan", "")} for o in data]
    print(json.dumps({"organizations": orgs}))


def cmd_list_projects(args):
    """List projects in an org."""
    data, code = run_neonctl(["projects", "list", "--org-id", args.org_id])
    if code != 0:
        print(json.dumps(data))
        sys.exit(1)
    projects = [{"name": p["name"], "id": p["id"], "region": p.get("region_id", "")} for p in data]
    print(json.dumps({"projects": projects}))


def cmd_create_project(args):
    """Create a new project."""
    cmd_args = ["projects", "create", "--name", args.name, "--org-id", args.org_id]
    if args.region:
        cmd_args += ["--region-id", args.region]
    data, code = run_neonctl(cmd_args)
    if code != 0:
        print(json.dumps(data))
        sys.exit(1)

    project = data.get("project", {})
    conn = data.get("connection_uris", [{}])[0].get("connection_parameters", {})
    result = {
        "project_id": project.get("id", ""),
        "name": project.get("name", ""),
        "region": project.get("region_id", ""),
        "default_database": conn.get("database", ""),
        "default_role": conn.get("role", ""),
        "default_host": conn.get("host", ""),
        "default_password": conn.get("password", ""),
    }
    print(json.dumps(result, indent=2))


def cmd_list_branches(args):
    """List branches in a project."""
    data, code = run_neonctl(["branches", "list", "--project-id", args.project_id])
    if code != 0:
        print(json.dumps(data))
        sys.exit(1)
    branches = [{"name": b.get("name", ""), "id": b["id"]} for b in data]
    print(json.dumps({"branches": branches}))


def cmd_create_role(args):
    """Create a database role."""
    data, code = run_neonctl([
        "roles", "create",
        "--project-id", args.project_id,
        "--branch-id", args.branch_id,
        "--name", args.name
    ])
    if code != 0:
        error = data.get("error", "")
        if "already exists" in error:
            print(json.dumps({"status": "exists", "name": args.name, "message": "Role already exists"}))
            return
        print(json.dumps(data))
        sys.exit(1)
    print(json.dumps({
        "status": "created",
        "name": data.get("name", args.name),
        "password": data.get("password", ""),
    }))


def cmd_create_database(args):
    """Create a database."""
    data, code = run_neonctl([
        "databases", "create",
        "--project-id", args.project_id,
        "--branch-id", args.branch_id,
        "--name", args.name,
        "--owner-name", args.owner
    ])
    if code != 0:
        error = data.get("error", "")
        if "already exists" in error:
            print(json.dumps({"status": "exists", "name": args.name, "message": "Database already exists"}))
            return
        print(json.dumps(data))
        sys.exit(1)
    print(json.dumps({
        "status": "created",
        "name": data.get("name", args.name),
        "owner": data.get("owner_name", args.owner),
    }))


def cmd_connection_string(args):
    """Get and parse the connection string."""
    cmd = ["neonctl", "connection-string",
           "--project-id", args.project_id,
           "--database-name", args.database,
           "--role-name", args.role]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            print(json.dumps({"error": result.stderr.strip()}))
            sys.exit(1)

        conn_str = result.stdout.strip()
        parsed = urlparse(conn_str)

        print(json.dumps({
            "DATABASE_URL": conn_str,
            "DB_HOST": parsed.hostname or "",
            "DB_PORT": str(parsed.port or 5432),
            "DB_NAME": parsed.path.lstrip("/") if parsed.path else "",
            "DB_USER": parsed.username or "",
            "DB_PASSWORD": parsed.password or "",
        }, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Neon CLI wrapper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Check neonctl installation")
    sub.add_parser("list-regions", help="List available regions")
    sub.add_parser("list-orgs", help="List organizations")

    p_proj = sub.add_parser("list-projects", help="List projects")
    p_proj.add_argument("--org-id", required=True)

    p_cpro = sub.add_parser("create-project", help="Create a project")
    p_cpro.add_argument("--org-id", required=True)
    p_cpro.add_argument("--name", required=True)
    p_cpro.add_argument("--region", default="aws-us-east-1")

    p_br = sub.add_parser("list-branches", help="List branches")
    p_br.add_argument("--project-id", required=True)

    p_role = sub.add_parser("create-role", help="Create a role")
    p_role.add_argument("--project-id", required=True)
    p_role.add_argument("--branch-id", required=True)
    p_role.add_argument("--name", required=True)

    p_db = sub.add_parser("create-database", help="Create a database")
    p_db.add_argument("--project-id", required=True)
    p_db.add_argument("--branch-id", required=True)
    p_db.add_argument("--name", required=True)
    p_db.add_argument("--owner", required=True)

    p_conn = sub.add_parser("connection-string", help="Get connection string")
    p_conn.add_argument("--project-id", required=True)
    p_conn.add_argument("--database", required=True)
    p_conn.add_argument("--role", required=True)

    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "list-regions": cmd_list_regions,
        "list-orgs": cmd_list_orgs,
        "list-projects": cmd_list_projects,
        "create-project": cmd_create_project,
        "list-branches": cmd_list_branches,
        "create-role": cmd_create_role,
        "create-database": cmd_create_database,
        "connection-string": cmd_connection_string,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
