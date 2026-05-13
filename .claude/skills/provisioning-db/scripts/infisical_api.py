#!/usr/bin/env python3
"""
Infisical API helper for provisioning-db skill.

Handles JWT extraction from macOS Keychain, project listing,
environment listing/creation, and secrets management.

Usage:
    python infisical_api.py auth-check
    python infisical_api.py list-orgs
    python infisical_api.py list-projects --org-id <ORG_ID>
    python infisical_api.py list-envs --project-id <PROJECT_ID>
    python infisical_api.py create-env --project-id <PROJECT_ID> --name <NAME> --slug <SLUG>
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

KEYCHAIN_SERVICE = "infisical-cli"
CONFIG_PATH = os.path.expanduser("~/.infisical/infisical-config.json")


def get_config():
    """Read infisical config file."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_domain_from_config():
    """Read logged-in domain from infisical config."""
    config = get_config()
    domain = config.get("LoggedInUserDomain", "")
    if domain:
        return domain
    # Fallback: check domains list
    domains = config.get("domains", [])
    if domains:
        return domains[0] if not domains[0].endswith("/api") else domains[0] + "/api"
    return None


def get_email_from_config():
    """Read logged-in email from infisical config."""
    return get_config().get("loggedInUserEmail")


def get_jwt_from_keychain(email=None):
    """Extract JWT from macOS Keychain."""
    if not email:
        email = get_email_from_config()
    if not email:
        return None, "No logged-in email found in ~/.infisical/infisical-config.json"

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", email, "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None, f"No keychain entry for {email}"

        vault_raw = result.stdout.strip()
        # Remove go-keyring-base64: prefix
        vault_b64 = vault_raw.replace("go-keyring-base64:", "")

        import base64
        vault_data = json.loads(base64.b64decode(vault_b64))
        jwt = vault_data.get("JTWToken")
        if not jwt:
            return None, "JTWToken not found in vault data"
        return jwt, None
    except Exception as e:
        return None, str(e)


def get_domain():
    """Get the Infisical domain, from config or default."""
    domain = get_domain_from_config()
    if not domain:
        return None
    # Ensure it ends with /api
    if not domain.endswith("/api"):
        domain = domain.rstrip("/") + "/api"
    return domain


def api_call(method, path, jwt, data=None, domain=None):
    """Make an API call to Infisical using curl (urllib has SSL/auth issues)."""
    if not domain:
        domain = get_domain()
    if not domain:
        return {"error": "No Infisical domain found. Run: infisical login --domain <YOUR_DOMAIN>"}, 500
    url = f"{domain}{path}"

    cmd = ["curl", "-s", "-w", "\n%{http_code}", "-H", f"Authorization: Bearer {jwt}",
           "-H", "Content-Type: application/json"]

    if method == "POST":
        cmd += ["-X", "POST"]
        if data:
            cmd += ["-d", json.dumps(data)]

    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        lines = output.rsplit("\n", 1)
        body = lines[0] if len(lines) > 1 else ""
        code = int(lines[-1]) if lines[-1].isdigit() else 500

        try:
            return json.loads(body), code
        except json.JSONDecodeError:
            return {"raw": body}, code
    except Exception as e:
        return {"error": str(e)}, 500


def cmd_auth_check(args):
    """Check if JWT is valid."""
    domain = get_domain()
    email = get_email_from_config()

    if not domain:
        print(json.dumps({"status": "no_config", "message": "No Infisical domain found. Run: infisical login --domain <YOUR_DOMAIN>"}))
        sys.exit(1)

    if not email:
        print(json.dumps({"status": "no_config", "domain": domain, "message": f"Not logged in. Run: infisical login --domain {domain}"}))
        sys.exit(1)

    jwt, err = get_jwt_from_keychain(email)
    if err:
        print(json.dumps({"status": "no_token", "email": email, "domain": domain, "error": err}))
        sys.exit(1)

    data, code = api_call("GET", "/v2/users/me/organizations", jwt, domain=domain)
    if code == 200:
        print(json.dumps({"status": "ok", "email": email, "domain": domain}))
    else:
        print(json.dumps({"status": "expired", "email": email, "domain": domain, "message": f"JWT expired. Run: infisical login --domain {domain}"}))
        sys.exit(1)


def cmd_list_orgs(args):
    """List organizations."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    data, code = api_call("GET", "/v2/users/me/organizations", jwt)
    if code != 200:
        print(json.dumps({"error": data}))
        sys.exit(1)

    orgs = [{"name": o["name"], "id": o["id"]} for o in data.get("organizations", [])]
    print(json.dumps({"organizations": orgs}))


def cmd_create_org(args):
    """Create a new Infisical organization."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    payload = {"name": args.name}
    data, code = api_call("POST", "/v2/organizations", jwt, payload)
    if code not in (200, 201):
        print(json.dumps({"error": data}))
        sys.exit(1)

    org = data.get("organization", {})
    print(json.dumps({
        "status": "created",
        "name": org.get("name", ""),
        "id": org.get("id", ""),
    }, indent=2))


def cmd_list_projects(args):
    """List projects/workspaces in an org."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    data, code = api_call("GET", f"/v2/organizations/{args.org_id}/workspaces", jwt)
    if code != 200:
        print(json.dumps({"error": data}))
        sys.exit(1)

    projects = [{"name": w["name"], "id": w["id"]} for w in data.get("workspaces", [])]
    print(json.dumps({"projects": projects}))


def cmd_list_envs(args):
    """List environments in a project."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    data, code = api_call("GET", f"/v1/workspace/{args.project_id}", jwt)
    if code != 200:
        print(json.dumps({"error": data}))
        sys.exit(1)

    envs = [{"name": e["name"], "slug": e["slug"], "id": e.get("id", "")}
            for e in data.get("workspace", {}).get("environments", [])]
    print(json.dumps({"environments": envs}))


def cmd_create_project(args):
    """Create a new Infisical project/workspace."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    payload = {"projectName": args.name, "organizationId": args.org_id}
    data, code = api_call("POST", "/v2/workspace", jwt, payload)
    if code not in (200, 201):
        print(json.dumps({"error": data}))
        sys.exit(1)

    project = data.get("project", {})
    print(json.dumps({
        "status": "created",
        "name": project.get("name", ""),
        "id": project.get("id", ""),
        "org_id": project.get("orgId", ""),
    }, indent=2))


def cmd_create_env(args):
    """Create a new environment."""
    jwt, err = get_jwt_from_keychain()
    if err:
        print(json.dumps({"error": err}))
        sys.exit(1)

    payload = {"name": args.name, "slug": args.slug}
    data, code = api_call("POST", f"/v1/projects/{args.project_id}/environments", jwt, payload)
    print(json.dumps(data, indent=2))
    if code not in (200, 201):
        sys.exit(1)


def _login_api(email, password, domain):
    """Call Infisical login API to get JWT and org list."""
    import re
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

    url = f"{domain}/v1/auth/login1"
    # Step 1: Get login1 challenge
    req = Request(url, method="POST",
                  headers={"Content-Type": "application/json"},
                  data=json.dumps({"email": email, "clientPublicKey": "placeholder"}).encode())
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()), resp.status
    except HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body), e.code
        except:
            return {"error": body}, e.code


def cmd_login(args):
    """Login to Infisical non-interactively with email + password."""
    import re

    domain = args.domain
    if not domain:
        domain = get_domain()
    if not domain:
        print(json.dumps({"error": "No domain. Provide --domain flag"}))
        sys.exit(1)

    # Ensure domain ends with /api
    if not domain.endswith("/api"):
        domain = domain.rstrip("/") + "/api"

    # First try without org-id
    cmd = [
        "infisical", "login",
        "--method", "user",
        "--email", args.email,
        "--password", args.password,
        "--domain", domain,
    ]

    if args.org_id:
        cmd += ["--organization-id", args.org_id]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stderr.strip() or result.stdout.strip()
        # Clean ANSI codes
        output = re.sub(r'\x1b\[[0-9;]*m', '', output)

        if result.returncode != 0:
            # Check if it needs org-id
            if "organization-id" in output.lower():
                print(json.dumps({
                    "status": "needs_org_id",
                    "message": "Login requires --org-id. Run: python3 <script> login --email <EMAIL> --password <PASS> --domain <DOMAIN> --org-id <ORG_ID>",
                    "domain": domain,
                    "email": args.email,
                }))
                sys.exit(1)
            print(json.dumps({"status": "error", "message": output}))
            sys.exit(1)

        print(json.dumps({"status": "ok", "email": args.email, "domain": domain}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


def cmd_list_login_orgs(args):
    """Login temporarily and list orgs to get org-id for full login."""
    import re

    domain = args.domain
    if not domain:
        domain = get_domain()
    if not domain:
        print(json.dumps({"error": "No domain"}))
        sys.exit(1)
    if not domain.endswith("/api"):
        domain = domain.rstrip("/") + "/api"

    # Use infisical CLI to do a partial login that returns orgs
    # Since CLI needs org-id, we use the API directly
    url = f"{domain}/v1/auth/login1"
    payload = json.dumps({"email": args.email, "clientPublicKey": ""}).encode()
    req = Request(url, method="POST",
                  headers={"Content-Type": "application/json"},
                  data=payload)
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            print(json.dumps(data, indent=2))
    except HTTPError as e:
        body = e.read().decode()
        print(json.dumps({"error": body, "status_code": e.code}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def cmd_create_service_token(args):
    """Create a service token via infisical CLI."""
    domain = get_domain()
    if not domain:
        print(json.dumps({"error": "No domain found"}))
        sys.exit(1)

    cmd = [
        "infisical", "service-token", "create",
        "--name", args.name,
        "--projectId", args.project_id,
        "--scope", f"{args.env}:/",
        "--access-level", "read",
        "--expiry-seconds", str(args.expiry),
        "--token-only",
        "--domain", domain,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            print(json.dumps({"error": error}))
            sys.exit(1)

        token = result.stdout.strip()
        print(json.dumps({
            "status": "created",
            "token": token,
            "name": args.name,
            "env": args.env,
            "project_id": args.project_id,
            "expiry_seconds": args.expiry,
        }))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Infisical API helper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("auth-check", help="Check auth status")

    p_login = sub.add_parser("login", help="Login to Infisical")
    p_login.add_argument("--email", required=True)
    p_login.add_argument("--password", required=True)
    p_login.add_argument("--domain", default=None, help="Infisical domain (auto-detected if not provided)")
    p_login.add_argument("--org-id", default=None, help="Organization ID")

    sub.add_parser("list-orgs", help="List organizations")

    p_corg = sub.add_parser("create-org", help="Create organization")
    p_corg.add_argument("--name", required=True)

    p_proj = sub.add_parser("list-projects", help="List projects")
    p_proj.add_argument("--org-id", required=True)

    p_cpro = sub.add_parser("create-project", help="Create project")
    p_cpro.add_argument("--org-id", required=True)
    p_cpro.add_argument("--name", required=True)

    p_envs = sub.add_parser("list-envs", help="List environments")
    p_envs.add_argument("--project-id", required=True)

    p_cenv = sub.add_parser("create-env", help="Create environment")
    p_cenv.add_argument("--project-id", required=True)
    p_cenv.add_argument("--name", required=True)
    p_cenv.add_argument("--slug", required=True)

    p_token = sub.add_parser("create-service-token", help="Create service token")
    p_token.add_argument("--project-id", required=True)
    p_token.add_argument("--env", required=True, help="Environment slug")
    p_token.add_argument("--name", required=True, help="Token name")
    p_token.add_argument("--expiry", type=int, default=0, help="Expiry in seconds (0=never)")

    args = parser.parse_args()

    commands = {
        "auth-check": cmd_auth_check,
        "login": cmd_login,
        "list-orgs": cmd_list_orgs,
        "create-org": cmd_create_org,
        "list-projects": cmd_list_projects,
        "create-project": cmd_create_project,
        "list-envs": cmd_list_envs,
        "create-env": cmd_create_env,
        "create-service-token": cmd_create_service_token,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
