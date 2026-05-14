#!/usr/bin/env python3
"""
Vultr CLI wrapper for provisioning-vultr skill.

Wraps vultr-cli commands for VKE cluster provisioning.
All output is JSON for easy parsing.

Usage:
    python vultr_api.py check                           # Check prerequisites (vultr-cli, kubectl, helm)
    python vultr_api.py auth-check                      # Check Vultr CLI authentication
    python vultr_api.py set-api-key --key <API_KEY>     # Set Vultr API key
    python vultr_api.py list-regions                    # List available VKE regions
    python vultr_api.py list-plans                      # List available VKE node plans
    python vultr_api.py create-cluster --label <LABEL> --region <REGION>
    python vultr_api.py list-clusters                   # List all VKE clusters
    python vultr_api.py get-cluster --cluster-id <ID>   # Get cluster details
    python vultr_api.py create-node-pool --cluster-id <ID> --label <LABEL> --plan <PLAN> --quantity <N> [--auto-scaler --min-nodes <MIN> --max-nodes <MAX>]
    python vultr_api.py list-node-pools --cluster-id <ID>
    python vultr_api.py get-config --cluster-id <ID> --env-name <ENV>  # Download kubeconfig
    python vultr_api.py get-nodes --env-name <ENV>      # Get node list via kubectl
    python vultr_api.py install-nginx --env-name <ENV> --replicas <N>
    python vultr_api.py install-cert-manager --env-name <ENV> --replicas <N>
    python vultr_api.py apply-cluster-issuer --env-name <ENV> --manifest-path <PATH>
    python vultr_api.py create-namespace --env-name <ENV> --namespace <NS>
    python vultr_api.py create-secret-generic --env-name <ENV> --namespace <NS> --name <NAME> --literals KEY=VAL ...
    python vultr_api.py create-secret-docker --env-name <ENV> --namespace <NS> --username <USER> --password <PASS>
    python vultr_api.py install-grafana-alloy --env-name <ENV> --cluster-name <NAME> --loki-url <URL> --loki-user <ID> --prom-url <URL> --prom-user <ID> --api-key <KEY>
    python vultr_api.py verify-cluster --env-name <ENV> --namespace <NS>
"""

import argparse
import json
import os
import subprocess
import sys
import shutil



def run_cmd(cmd, timeout=60):
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}", 1
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1


def run_vultr(args_list, timeout=60):
    """Run a vultr-cli command and return parsed output."""
    cmd = ["vultr-cli"] + args_list
    stdout, stderr, code = run_cmd(cmd, timeout=timeout)
    if code != 0:
        return {"error": stderr or stdout}, code
    return {"raw": stdout}, 0


def kubeconfig_path(env_name):
    """Return the kubeconfig path for an environment."""
    return os.path.expanduser(f"~/.kube/{env_name}-config")


def kubectl_with_env(env_name, kubectl_args, timeout=30):
    """Run kubectl with the correct KUBECONFIG for the given environment."""
    kc = kubeconfig_path(env_name)
    env = {**os.environ, "KUBECONFIG": kc}
    cmd = ["kubectl"] + kubectl_args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "", "kubectl not found", 1
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1


# ─── Commands ───────────────────────────────────────────────────────────────


def cmd_check(args):
    """Check if vultr-cli, kubectl, and helm are installed."""
    tools = {
        "vultr-cli": ["vultr-cli", "version"],
        "kubectl": ["kubectl", "version", "--client", "--short"],
        "helm": ["helm", "version", "--short"],
    }
    results = {}
    all_ok = True
    for name, cmd in tools.items():
        path = shutil.which(name)
        if path:
            stdout, _, code = run_cmd(cmd, timeout=10)
            results[name] = {"status": "ok", "path": path, "version": stdout}
        else:
            all_ok = False
            install_hints = {
                "vultr-cli": "brew install vultr/vultr-cli/vultr-cli",
                "kubectl": "brew install kubectl",
                "helm": "brew install helm",
            }
            results[name] = {"status": "not_installed", "install": install_hints[name]}

    output = {"status": "ok" if all_ok else "missing_tools", "tools": results}
    print(json.dumps(output, indent=2))
    if not all_ok:
        sys.exit(1)


def cmd_auth_check(args):
    """Check Vultr CLI authentication."""
    stdout, stderr, code = run_cmd(["vultr-cli", "account", "info"], timeout=10)
    if code != 0:
        print(json.dumps({"status": "not_authenticated", "error": stderr or stdout}))
        sys.exit(1)

    # Parse the tab-separated output
    lines = stdout.strip().split("\n")
    if len(lines) >= 2:
        # Header line + data line
        values = lines[1].split("\t")
        info = {
            "status": "ok",
            "balance": values[0].strip() if len(values) > 0 else "",
            "pending_charges": values[1].strip() if len(values) > 1 else "",
            "name": values[4].strip() if len(values) > 4 else "",
            "email": values[5].strip() if len(values) > 5 else "",
        }
    else:
        info = {"status": "ok", "raw": stdout}

    print(json.dumps(info, indent=2))


def cmd_set_api_key(args):
    """Set Vultr API key."""
    stdout, stderr, code = run_cmd(["vultr-cli", "config", "set", "api-key", args.key], timeout=10)
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)
    print(json.dumps({"status": "ok", "message": "API key configured"}))


def cmd_list_regions(args):
    """List available Vultr regions for VKE."""
    stdout, stderr, code = run_cmd(["vultr-cli", "regions", "list"], timeout=15)
    if code != 0:
        print(json.dumps({"error": stderr or stdout}))
        sys.exit(1)

    regions = []
    lines = stdout.strip().split("\n")
    for line in lines[1:]:  # Skip header
        if not line.strip() or line.startswith("---"):
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            regions.append({
                "id": parts[0].strip(),
                "city": parts[1].strip(),
                "country": parts[2].strip(),
            })

    print(json.dumps({"regions": regions}, indent=2))


def cmd_list_plans(args):
    """Fetch VKE-compatible plans dynamically from Vultr API.

    Optional --region flag filters to plans available in that region.
    """
    region_filter = getattr(args, "region", None)
    plans = {"regular": [], "high_performance": []}

    for plan_type, key in [("vc2", "regular"), ("vhp", "high_performance")]:
        stdout, stderr, code = run_cmd(
            ["vultr-cli", "plans", "list", "--type", plan_type, "-o", "json"], timeout=15)
        if code == 0:
            data = json.loads(stdout)
            for p in data.get("plans", []):
                locations = p.get("locations", [])
                # Filter: min 1GB RAM, available in 5+ regions (or in the specific region)
                if p["ram"] < 1024:
                    continue
                if region_filter and region_filter not in locations:
                    continue
                if not region_filter and len(locations) < 5:
                    continue
                monthly = p["monthly_cost"]
                plans[key].append({
                    "plan_id": p["id"],
                    "vcpus": p["vcpu_count"],
                    "ram_mb": p["ram"],
                    "ram": f"{p['ram'] // 1024} GB" if p['ram'] >= 1024 else f"{p['ram']} MB",
                    "disk": p["disk"],
                    "storage": f"{p['disk']} GB {'NVMe' if 'vhp' in p['id'] else 'SSD'}",
                    "bandwidth_gb": p.get("bandwidth", 0),
                    "monthly_cost": monthly,
                    "hourly_cost": round(monthly / 730, 4),
                    "locations": locations,
                })

    price_lookup = {}
    for category in plans.values():
        for p in category:
            price_lookup[p["plan_id"]] = {"monthly": p["monthly_cost"], "hourly": p["hourly_cost"]}

    print(json.dumps({"plans": plans, "price_lookup": price_lookup}, indent=2))


def cmd_get_plan_price(args):
    """Get price for a plan dynamically from Vultr API."""
    for plan_type in ["vc2", "vhp"]:
        stdout, stderr, code = run_cmd(
            ["vultr-cli", "plans", "list", "--type", plan_type, "-o", "json"], timeout=15)
        if code == 0:
            data = json.loads(stdout)
            for p in data.get("plans", []):
                if p["id"] == args.plan_id:
                    monthly = p["monthly_cost"]
                    print(json.dumps({
                        "plan_id": args.plan_id,
                        "monthly": monthly,
                        "hourly": round(monthly / 730, 4),
                    }))
                    return
    print(json.dumps({"plan_id": args.plan_id, "monthly": None, "hourly": None, "message": "Plan not found"}))


def cmd_list_versions(args):
    """List available Kubernetes versions."""
    stdout, stderr, code = run_cmd(["vultr-cli", "kubernetes", "versions"], timeout=15)
    if code != 0:
        print(json.dumps({"error": stderr or stdout}))
        sys.exit(1)

    versions = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("VERSION") and not line.startswith("---"):
            versions.append(line)

    print(json.dumps({"versions": versions}, indent=2))


def _build_node_pool_string(pools):
    """Build the --node-pools string from a list of pool dicts.

    Each pool dict has: label, plan, quantity, and optionally auto_scaler, min_nodes, max_nodes.
    Multiple pools are separated by '/'.
    """
    parts = []
    for pool in pools:
        pool_str = f"quantity:{pool['quantity']},plan:{pool['plan']},label:{pool['label']}"
        if pool.get("auto_scaler"):
            pool_str += f",auto-scaler:true,min-nodes:{pool['min_nodes']},max-nodes:{pool['max_nodes']}"
        parts.append(pool_str)
    return "/".join(parts)


def _parse_cluster_id(output):
    """Parse cluster ID (UUID) from vultr-cli kubernetes create output.

    The output format is:
        ID\t\t\t<uuid>
        LABEL\t\t\t<name>
    We look for the line starting with 'ID' and extract the UUID after the tabs.
    """
    import re
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("ID"):
            # Extract UUID from "ID\t\t\t<uuid>" format
            parts = line.split("\t")
            for p in parts[1:]:
                p = p.strip()
                if p and re.match(r'^[0-9a-f]{8}-', p):
                    return p
    return None


def _parse_node_pool_id(output):
    """Parse node pool ID from vultr-cli node-pool create/list output."""
    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("ID"):
            # "ID\t\t<uuid>" format
            parts = line.split("\t")
            for p in parts[1:]:
                p = p.strip()
                if p and len(p) > 8:
                    return p
    return None


def cmd_create_cluster(args):
    """Create a VKE cluster with node pools.

    Uses a bootstrap strategy to avoid Vultr's inline plan compatibility issues:
    1. Create cluster with a minimal vc2-1c-2gb bootstrap pool (always works)
    2. Add each real node pool via node-pool create (supports all plans)
    3. Delete the bootstrap pool

    --node-pools is a JSON array of pool objects:
    [{"label":"API","plan":"vc2-4c-8gb","quantity":2,"auto_scaler":true,"min_nodes":1,"max_nodes":3}]
    """
    import time

    pools = json.loads(args.node_pools)

    # Step 1: Create cluster with bootstrap pool
    bootstrap_label = "init-bootstrap"
    bootstrap_str = f"quantity:1,plan:vc2-1c-2gb,label:{bootstrap_label}"

    sys.stderr.write("Creating cluster with bootstrap pool...\n")
    cmd_args = [
        "vultr-cli", "kubernetes", "create",
        "--label", args.label,
        "--region", args.region,
        "--version", args.version,
        "--node-pools", bootstrap_str,
    ]

    stdout, stderr, code = run_cmd(cmd_args, timeout=120)
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout, "step": "create_cluster"}))
        sys.exit(1)

    cluster_id = _parse_cluster_id(stdout)
    if not cluster_id:
        print(json.dumps({"status": "error", "error": "Could not parse cluster ID from output", "raw": stdout}))
        sys.exit(1)

    sys.stderr.write(f"Cluster created: {cluster_id}\n")

    # Step 2: Add each real node pool
    created_pools = []
    for pool in pools:
        sys.stderr.write(f"Adding node pool: {pool['label']} ({pool['plan']} x{pool['quantity']})...\n")
        np_args = [
            "vultr-cli", "kubernetes", "node-pool", "create", cluster_id,
            "--label", pool["label"],
            "--plan", pool["plan"],
            "--quantity", str(pool["quantity"]),
        ]
        if pool.get("auto_scaler"):
            np_args += [
                "--auto-scaler", "true",
                "--min-nodes", str(pool["min_nodes"]),
                "--max-nodes", str(pool["max_nodes"]),
            ]

        np_stdout, np_stderr, np_code = run_cmd(np_args, timeout=60)
        if np_code != 0:
            print(json.dumps({
                "status": "error",
                "error": np_stderr or np_stdout,
                "step": f"create_node_pool_{pool['label']}",
                "cluster_id": cluster_id,
            }))
            sys.exit(1)

        pool_id = _parse_node_pool_id(np_stdout)
        created_pools.append({"label": pool["label"], "pool_id": pool_id})
        sys.stderr.write(f"  Pool '{pool['label']}' created (ID: {pool_id})\n")

    # Step 3: Delete bootstrap pool
    sys.stderr.write("Removing bootstrap pool...\n")
    # Find bootstrap pool ID by listing pools
    list_stdout, _, list_code = run_cmd(
        ["vultr-cli", "kubernetes", "node-pool", "list", cluster_id], timeout=15
    )
    if list_code == 0:
        # Parse pool IDs and labels to find bootstrap
        current_id = None
        current_label = None
        for line in list_stdout.split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("ID"):
                parts = line_stripped.split("\t")
                for p in parts[1:]:
                    p = p.strip()
                    if p and len(p) > 8:
                        current_id = p
                        break
            elif line_stripped.startswith("LABEL"):
                parts = line_stripped.split("\t")
                for p in parts[1:]:
                    p = p.strip()
                    if p:
                        current_label = p
                        break
                # Check if this is the bootstrap pool
                if current_label == bootstrap_label and current_id:
                    del_stdout, del_stderr, del_code = run_cmd(
                        ["vultr-cli", "kubernetes", "node-pool", "delete", cluster_id, current_id],
                        timeout=30
                    )
                    if del_code == 0:
                        sys.stderr.write(f"  Bootstrap pool deleted (ID: {current_id})\n")
                    else:
                        sys.stderr.write(f"  Warning: Could not delete bootstrap pool: {del_stderr}\n")
                    current_id = None
                    current_label = None

    # Calculate total expected nodes
    total_nodes = sum(p["quantity"] for p in pools)

    print(json.dumps({
        "status": "created",
        "cluster_id": cluster_id,
        "label": args.label,
        "region": args.region,
        "version": args.version,
        "node_pools": pools,
        "created_pools": created_pools,
        "total_expected_nodes": total_nodes,
    }, indent=2))


def cmd_list_clusters(args):
    """List all VKE clusters."""
    stdout, stderr, code = run_cmd(["vultr-cli", "kubernetes", "list"], timeout=15)
    if code != 0:
        print(json.dumps({"error": stderr or stdout}))
        sys.exit(1)
    print(json.dumps({"raw": stdout}))


def cmd_get_cluster(args):
    """Get details for a specific cluster."""
    stdout, stderr, code = run_cmd(["vultr-cli", "kubernetes", "get", args.cluster_id], timeout=15)
    if code != 0:
        print(json.dumps({"error": stderr or stdout}))
        sys.exit(1)
    print(json.dumps({"cluster_id": args.cluster_id, "raw": stdout}))


def cmd_create_node_pool(args):
    """Create a node pool in a VKE cluster."""
    cmd_args = [
        "vultr-cli", "kubernetes", "node-pool", "create", args.cluster_id,
        "--label", args.label,
        "--plan", args.plan,
        "--quantity", str(args.quantity),
    ]
    if args.auto_scaler:
        cmd_args += [
            "--auto-scaler", "true",
            "--min-nodes", str(args.min_nodes),
            "--max-nodes", str(args.max_nodes),
        ]

    stdout, stderr, code = run_cmd(cmd_args, timeout=60)
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)

    print(json.dumps({
        "status": "created",
        "label": args.label,
        "plan": args.plan,
        "quantity": args.quantity,
        "auto_scaler": args.auto_scaler,
        "min_nodes": args.min_nodes if args.auto_scaler else None,
        "max_nodes": args.max_nodes if args.auto_scaler else None,
        "raw": stdout,
    }, indent=2))


def cmd_list_node_pools(args):
    """List node pools in a cluster."""
    stdout, stderr, code = run_cmd(
        ["vultr-cli", "kubernetes", "node-pool", "list", args.cluster_id],
        timeout=15
    )
    if code != 0:
        print(json.dumps({"error": stderr or stdout}))
        sys.exit(1)
    print(json.dumps({"cluster_id": args.cluster_id, "raw": stdout}))


def cmd_get_config(args):
    """Download kubeconfig for a cluster. Handles base64-encoded output.

    Auto-retries up to 6 times with 15s intervals (total ~90s) since
    Vultr clusters take time to make kubeconfig available after creation.
    """
    import base64
    import time

    kc_path = kubeconfig_path(args.env_name)
    os.makedirs(os.path.dirname(kc_path), exist_ok=True)

    max_retries = 6
    retry_interval = 15
    last_error = ""

    for attempt in range(1, max_retries + 1):
        stdout, stderr, code = run_cmd(
            ["vultr-cli", "kubernetes", "config", args.cluster_id],
            timeout=30
        )
        if code == 0 and stdout.strip():
            # Success — decode and write
            content = stdout.strip()
            if not content.startswith("apiVersion") and not content.startswith("{"):
                try:
                    decoded = base64.b64decode(content).decode("utf-8")
                    content = decoded
                except Exception:
                    pass

            with open(kc_path, "w") as f:
                f.write(content)

            print(json.dumps({
                "status": "ok",
                "kubeconfig_path": kc_path,
                "cluster_id": args.cluster_id,
                "env_name": args.env_name,
                "attempts": attempt,
            }, indent=2))
            return

        last_error = stderr or stdout
        if attempt < max_retries:
            sys.stderr.write(f"Kubeconfig not ready (attempt {attempt}/{max_retries}), retrying in {retry_interval}s...\n")
            time.sleep(retry_interval)

    print(json.dumps({"status": "error", "error": last_error, "attempts": max_retries}))
    sys.exit(1)


def cmd_get_nodes(args):
    """Get nodes using kubectl with env-specific kubeconfig."""
    stdout, stderr, code = kubectl_with_env(args.env_name, ["get", "nodes"])
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)
    print(json.dumps({"status": "ok", "nodes": stdout}))


def cmd_install_nginx(args):
    """Install nginx-ingress controller via helm."""
    kc = kubeconfig_path(args.env_name)
    env = {**os.environ, "KUBECONFIG": kc}

    # Add repo and update
    subprocess.run(["helm", "repo", "add", "ingress-nginx", "https://kubernetes.github.io/ingress-nginx"],
                    capture_output=True, text=True, timeout=30, env=env)
    subprocess.run(["helm", "repo", "update"], capture_output=True, text=True, timeout=30, env=env)

    # Install
    cmd = [
        "helm", "install", "ingress-nginx", "ingress-nginx/ingress-nginx",
        "--namespace", "ingress-nginx",
        "--create-namespace",
        "--set", f"controller.replicaCount={args.replicas}",
        "--set", "controller.nodeSelector.kubernetes\\.io/os=linux",
        "--set", "controller.service.type=LoadBalancer",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": result.stderr.strip() or result.stdout.strip()}))
        sys.exit(1)

    # Get pods and service
    pods_out, _, _ = kubectl_with_env(args.env_name, ["get", "pods", "-n", "ingress-nginx"])
    svc_out, _, _ = kubectl_with_env(args.env_name, ["get", "svc", "-n", "ingress-nginx"])

    # Try to extract external IP
    external_ip = None
    for line in svc_out.split("\n"):
        if "LoadBalancer" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "LoadBalancer" and i + 1 < len(parts):
                    external_ip = parts[i + 1]
                    break

    print(json.dumps({
        "status": "ok",
        "pods": pods_out,
        "services": svc_out,
        "external_ip": external_ip,
    }, indent=2))


def cmd_install_cert_manager(args):
    """Install cert-manager via helm."""
    kc = kubeconfig_path(args.env_name)
    env = {**os.environ, "KUBECONFIG": kc}

    subprocess.run(["helm", "repo", "add", "jetstack", "https://charts.jetstack.io"],
                    capture_output=True, text=True, timeout=30, env=env)
    subprocess.run(["helm", "repo", "update"], capture_output=True, text=True, timeout=30, env=env)

    cmd = [
        "helm", "install", "cert-manager", "jetstack/cert-manager",
        "--namespace", "cert-manager",
        "--create-namespace",
        "--set", "crds.enabled=true",
        "--set", f"replicaCount={args.replicas}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
    if result.returncode != 0:
        print(json.dumps({"status": "error", "error": result.stderr.strip() or result.stdout.strip()}))
        sys.exit(1)

    # Quick check if pods are ready (10s timeout — don't block if nodes aren't up yet)
    kubectl_with_env(args.env_name, [
        "wait", "--for=condition=Ready", "pods", "--all", "-n", "cert-manager", "--timeout=10s"
    ], timeout=15)

    pods_out, _, _ = kubectl_with_env(args.env_name, ["get", "pods", "-n", "cert-manager"])

    print(json.dumps({"status": "ok", "pods": pods_out}, indent=2))


def cmd_apply_cluster_issuer(args):
    """Apply a ClusterIssuer manifest."""
    stdout, stderr, code = kubectl_with_env(args.env_name, ["apply", "-f", args.manifest_path])
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)

    ci_out, _, _ = kubectl_with_env(args.env_name, ["get", "clusterissuer"])
    print(json.dumps({"status": "ok", "output": stdout, "cluster_issuers": ci_out}, indent=2))


def cmd_create_namespace(args):
    """Create a Kubernetes namespace."""
    stdout, stderr, code = kubectl_with_env(args.env_name, [
        "create", "namespace", args.namespace, "--dry-run=client", "-o", "yaml"
    ])
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)

    # Pipe through kubectl apply
    kc = kubeconfig_path(args.env_name)
    env_vars = {**os.environ, "KUBECONFIG": kc}
    apply = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=stdout, capture_output=True, text=True, timeout=15, env=env_vars
    )
    if apply.returncode != 0:
        print(json.dumps({"status": "error", "error": apply.stderr.strip()}))
        sys.exit(1)

    print(json.dumps({"status": "ok", "namespace": args.namespace, "output": apply.stdout.strip()}, indent=2))


def cmd_create_secret_generic(args):
    """Create a generic Kubernetes secret."""
    cmd_args = [
        "create", "secret", "generic", args.name,
        f"--namespace={args.namespace}",
    ]
    for literal in args.literals:
        cmd_args.append(f"--from-literal={literal}")
    cmd_args += ["--dry-run=client", "-o", "yaml"]

    stdout, stderr, code = kubectl_with_env(args.env_name, cmd_args)
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)

    kc = kubeconfig_path(args.env_name)
    env_vars = {**os.environ, "KUBECONFIG": kc}
    apply = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=stdout, capture_output=True, text=True, timeout=15, env=env_vars
    )
    if apply.returncode != 0:
        print(json.dumps({"status": "error", "error": apply.stderr.strip()}))
        sys.exit(1)

    print(json.dumps({"status": "ok", "secret": args.name, "namespace": args.namespace}, indent=2))


def cmd_create_secret_docker(args):
    """Create a Docker registry secret."""
    cmd_args = [
        "create", "secret", "docker-registry", "dockerhub-auth",
        f"--namespace={args.namespace}",
        "--docker-server=https://index.docker.io/v1/",
        f"--docker-username={args.username}",
        f"--docker-password={args.password}",
        "--dry-run=client", "-o", "yaml",
    ]

    stdout, stderr, code = kubectl_with_env(args.env_name, cmd_args)
    if code != 0:
        print(json.dumps({"status": "error", "error": stderr or stdout}))
        sys.exit(1)

    kc = kubeconfig_path(args.env_name)
    env_vars = {**os.environ, "KUBECONFIG": kc}
    apply = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=stdout, capture_output=True, text=True, timeout=15, env=env_vars
    )
    if apply.returncode != 0:
        print(json.dumps({"status": "error", "error": apply.stderr.strip()}))
        sys.exit(1)

    print(json.dumps({"status": "ok", "secret": "dockerhub-auth", "namespace": args.namespace}, indent=2))


def cmd_wait_for_nodes(args):
    """Poll kubectl get nodes until ALL expected nodes are Ready.

    Keeps waiting until every expected node registers and shows Ready.
    Default timeout is 600s (10 min) to handle slow regions like blr.
    """
    import time
    timeout = args.timeout
    interval = 30
    expected = args.expected_nodes
    start = time.time()

    while time.time() - start < timeout:
        stdout, stderr, code = kubectl_with_env(args.env_name, ["get", "nodes", "--no-headers"])
        if code == 0:
            lines = [l for l in stdout.strip().split("\n") if l.strip()]
            ready_count = sum(1 for l in lines if "Ready" in l and "NotReady" not in l)
            total_count = len(lines)

            if ready_count >= expected:
                full_out, _, _ = kubectl_with_env(args.env_name, ["get", "nodes"])
                print(json.dumps({
                    "status": "ok",
                    "ready_nodes": ready_count,
                    "total_nodes": total_count,
                    "expected_nodes": expected,
                    "nodes": full_out,
                    "elapsed_seconds": int(time.time() - start),
                }, indent=2))
                return

            elapsed = int(time.time() - start)
            sys.stderr.write(f"Waiting for nodes... {ready_count}/{expected} ready ({elapsed}s elapsed)\n")

        time.sleep(interval)

    # Timeout — report what we have
    stdout, _, _ = kubectl_with_env(args.env_name, ["get", "nodes", "--no-headers"])
    lines = [l for l in stdout.strip().split("\n") if l.strip()] if stdout.strip() else []
    ready_count = sum(1 for l in lines if "Ready" in l and "NotReady" not in l)
    full_out, _, _ = kubectl_with_env(args.env_name, ["get", "nodes"])

    print(json.dumps({
        "status": "timeout",
        "message": f"{ready_count}/{expected} nodes ready after {timeout}s.",
        "ready_nodes": ready_count,
        "expected_nodes": expected,
        "nodes": full_out,
        "elapsed_seconds": timeout,
    }, indent=2))
    sys.exit(1)


def cmd_install_grafana_alloy(args):
    """Install Grafana Alloy DaemonSet for log and metrics collection.

    Deploys Alloy to a 'monitoring' namespace via Helm, configured to push
    logs to Grafana Cloud Loki and metrics to Grafana Cloud Prometheus.
    """
    import tempfile
    import time

    kc = kubeconfig_path(args.env_name)
    env = {**os.environ, "KUBECONFIG": kc}
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "..", "templates", "alloy-values.yaml")

    # Step 1: Add Grafana Helm repo
    sys.stderr.write("Adding Grafana Helm repo...\n")
    subprocess.run(
        ["helm", "repo", "add", "grafana", "https://grafana.github.io/helm-charts"],
        capture_output=True, text=True, timeout=30, env=env
    )
    subprocess.run(
        ["helm", "repo", "update"],
        capture_output=True, text=True, timeout=60, env=env
    )

    # Step 2: Create monitoring namespace
    sys.stderr.write("Creating monitoring namespace...\n")
    dry_result = subprocess.run(
        ["kubectl", "create", "namespace", "monitoring", "--dry-run=client", "-o", "yaml"],
        capture_output=True, text=True, timeout=10, env=env
    )
    apply_result = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=dry_result.stdout, capture_output=True, text=True, timeout=15, env=env
    )
    if apply_result.returncode != 0:
        print(json.dumps({"status": "error", "error": apply_result.stderr.strip(), "step": "create_namespace"}))
        sys.exit(1)

    # Step 3: Create Grafana Cloud credentials secret
    sys.stderr.write("Creating Grafana Cloud credentials secret...\n")
    secret_dry = subprocess.run(
        ["kubectl", "create", "secret", "generic", "grafana-cloud-credentials",
         "--namespace=monitoring",
         f"--from-literal=loki-url={args.loki_url}",
         f"--from-literal=loki-user={args.loki_user}",
         f"--from-literal=prom-url={args.prom_url}",
         f"--from-literal=prom-user={args.prom_user}",
         f"--from-literal=api-key={args.api_key}",
         "--dry-run=client", "-o", "yaml"],
        capture_output=True, text=True, timeout=10, env=env
    )
    secret_apply = subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=secret_dry.stdout, capture_output=True, text=True, timeout=15, env=env
    )
    if secret_apply.returncode != 0:
        print(json.dumps({"status": "error", "error": secret_apply.stderr.strip(), "step": "create_secret"}))
        sys.exit(1)

    # Step 4: Generate values file from template
    sys.stderr.write("Generating Alloy values from template...\n")
    if not os.path.exists(template_path):
        print(json.dumps({"status": "error", "error": f"Template not found: {template_path}"}))
        sys.exit(1)

    with open(template_path, "r") as f:
        values_content = f.read()

    values_content = values_content.replace("${CLUSTER_NAME}", args.cluster_name)
    values_content = values_content.replace("${LOKI_URL}", args.loki_url)
    values_content = values_content.replace("${LOKI_USER}", args.loki_user)
    values_content = values_content.replace("${PROM_URL}", args.prom_url)
    values_content = values_content.replace("${PROM_USER}", args.prom_user)
    values_content = values_content.replace("${API_KEY}", args.api_key)

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        tmp.write(values_content)
        tmp_path = tmp.name

    # Step 5: Helm install Alloy
    sys.stderr.write("Installing Grafana Alloy via Helm...\n")
    helm_cmd = [
        "helm", "upgrade", "--install", "alloy", "grafana/alloy",
        "--namespace", "monitoring",
        "--values", tmp_path,
        "--wait",
        "--timeout", "120s",
    ]
    helm_result = subprocess.run(helm_cmd, capture_output=True, text=True, timeout=180, env=env)

    # Clean up temp file
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    if helm_result.returncode != 0:
        print(json.dumps({
            "status": "error",
            "error": helm_result.stderr.strip() or helm_result.stdout.strip(),
            "step": "helm_install",
        }))
        sys.exit(1)

    # Step 6: Verify DaemonSet
    sys.stderr.write("Verifying Alloy DaemonSet...\n")
    time.sleep(5)  # Brief pause for DaemonSet to schedule pods

    ds_result = subprocess.run(
        ["kubectl", "get", "daemonset", "-n", "monitoring", "-o", "wide"],
        capture_output=True, text=True, timeout=15, env=env
    )

    pods_result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "monitoring", "-o", "wide"],
        capture_output=True, text=True, timeout=15, env=env
    )

    print(json.dumps({
        "status": "ok",
        "cluster_name": args.cluster_name,
        "namespace": "monitoring",
        "loki_url": args.loki_url,
        "prom_url": args.prom_url,
        "daemonset": ds_result.stdout.strip(),
        "pods": pods_result.stdout.strip(),
    }, indent=2))


def cmd_verify_cluster(args):
    """Run verification checks on the cluster."""
    results = {}

    # Cluster list
    stdout, _, _ = run_cmd(["vultr-cli", "kubernetes", "list"], timeout=15)
    results["clusters"] = stdout

    # Nodes
    stdout, _, _ = kubectl_with_env(args.env_name, ["get", "nodes"])
    results["nodes"] = stdout

    # Namespaces
    stdout, _, _ = kubectl_with_env(args.env_name, ["get", "namespaces"])
    results["namespaces"] = stdout

    # Ingress
    stdout, stderr, code = kubectl_with_env(args.env_name, ["get", "svc", "-n", "ingress-nginx"])
    results["ingress"] = stdout if code == 0 else "nginx-ingress not installed"

    # Cert-manager
    stdout, stderr, code = kubectl_with_env(args.env_name, ["get", "pods", "-n", "cert-manager"])
    results["cert_manager"] = stdout if code == 0 else "cert-manager not installed"

    # Secrets
    if args.namespace:
        stdout, stderr, code = kubectl_with_env(args.env_name, ["get", "secrets", "-n", args.namespace])
        results["secrets"] = stdout if code == 0 else f"Namespace '{args.namespace}' not found"

    print(json.dumps({"status": "ok", "verification": results}, indent=2))


# ─── Main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Vultr VKE provisioning helper")
    sub = parser.add_subparsers(dest="command")

    # Prerequisites
    sub.add_parser("check", help="Check prerequisites")
    sub.add_parser("auth-check", help="Check Vultr CLI authentication")

    p_key = sub.add_parser("set-api-key", help="Set Vultr API key")
    p_key.add_argument("--key", required=True)

    # Discovery
    sub.add_parser("list-regions", help="List Vultr regions")

    p_plans = sub.add_parser("list-plans", help="List available node plans with prices")
    p_plans.add_argument("--region", default=None, help="Filter plans to those available in this region")

    sub.add_parser("list-versions", help="List available Kubernetes versions")

    p_price = sub.add_parser("get-plan-price", help="Get price for a plan")
    p_price.add_argument("--plan-id", required=True)

    # Cluster
    p_create = sub.add_parser("create-cluster", help="Create VKE cluster with node pools")
    p_create.add_argument("--label", required=True)
    p_create.add_argument("--region", required=True)
    p_create.add_argument("--version", required=True, help="Kubernetes version (e.g. v1.35.2+1)")
    p_create.add_argument("--node-pools", required=True, help="JSON array of pool objects")

    sub.add_parser("list-clusters", help="List VKE clusters")

    p_get = sub.add_parser("get-cluster", help="Get cluster details")
    p_get.add_argument("--cluster-id", required=True)

    # Node pools
    p_np = sub.add_parser("create-node-pool", help="Create node pool")
    p_np.add_argument("--cluster-id", required=True)
    p_np.add_argument("--label", required=True)
    p_np.add_argument("--plan", required=True)
    p_np.add_argument("--quantity", type=int, required=True)
    p_np.add_argument("--auto-scaler", action="store_true", default=False)
    p_np.add_argument("--min-nodes", type=int, default=1)
    p_np.add_argument("--max-nodes", type=int, default=3)

    p_lnp = sub.add_parser("list-node-pools", help="List node pools")
    p_lnp.add_argument("--cluster-id", required=True)

    # Kubeconfig
    p_cfg = sub.add_parser("get-config", help="Download kubeconfig")
    p_cfg.add_argument("--cluster-id", required=True)
    p_cfg.add_argument("--env-name", required=True)

    # Kubectl
    p_nodes = sub.add_parser("get-nodes", help="Get node list")
    p_nodes.add_argument("--env-name", required=True)

    # Wait for nodes
    p_wait = sub.add_parser("wait-for-nodes", help="Wait for nodes to be ready")
    p_wait.add_argument("--env-name", required=True)
    p_wait.add_argument("--expected-nodes", type=int, required=True)
    p_wait.add_argument("--timeout", type=int, default=300, help="Timeout in seconds (default 300 — 5 min)")

    # Add-ons
    p_nginx = sub.add_parser("install-nginx", help="Install nginx-ingress")
    p_nginx.add_argument("--env-name", required=True)
    p_nginx.add_argument("--replicas", type=int, default=2)

    p_cert = sub.add_parser("install-cert-manager", help="Install cert-manager")
    p_cert.add_argument("--env-name", required=True)
    p_cert.add_argument("--replicas", type=int, default=2)

    p_ci = sub.add_parser("apply-cluster-issuer", help="Apply ClusterIssuer manifest")
    p_ci.add_argument("--env-name", required=True)
    p_ci.add_argument("--manifest-path", required=True)

    # Namespace & Secrets
    p_ns = sub.add_parser("create-namespace", help="Create namespace")
    p_ns.add_argument("--env-name", required=True)
    p_ns.add_argument("--namespace", required=True)

    p_sg = sub.add_parser("create-secret-generic", help="Create generic secret")
    p_sg.add_argument("--env-name", required=True)
    p_sg.add_argument("--namespace", required=True)
    p_sg.add_argument("--name", required=True)
    p_sg.add_argument("--literals", nargs="+", required=True, help="KEY=VALUE pairs")

    p_sd = sub.add_parser("create-secret-docker", help="Create Docker registry secret")
    p_sd.add_argument("--env-name", required=True)
    p_sd.add_argument("--namespace", required=True)
    p_sd.add_argument("--username", required=True)
    p_sd.add_argument("--password", required=True)

    # Grafana Alloy observability
    p_alloy = sub.add_parser("install-grafana-alloy", help="Install Grafana Alloy DaemonSet for logs + metrics")
    p_alloy.add_argument("--env-name", required=True, help="Environment name (for kubeconfig selection)")
    p_alloy.add_argument("--cluster-name", required=True, help="Cluster label for multi-cluster log separation")
    p_alloy.add_argument("--loki-url", required=True, help="Grafana Cloud Loki push URL")
    p_alloy.add_argument("--loki-user", required=True, help="Grafana Cloud Loki instance ID (basic auth username)")
    p_alloy.add_argument("--prom-url", required=True, help="Grafana Cloud Prometheus remote write URL")
    p_alloy.add_argument("--prom-user", required=True, help="Grafana Cloud Prometheus instance ID (basic auth username)")
    p_alloy.add_argument("--api-key", required=True, help="Grafana Cloud API token (basic auth password)")

    # Verification
    p_verify = sub.add_parser("verify-cluster", help="Verify cluster setup")
    p_verify.add_argument("--env-name", required=True)
    p_verify.add_argument("--namespace", default="")

    commands = {
        "check": cmd_check,
        "auth-check": cmd_auth_check,
        "set-api-key": cmd_set_api_key,
        "list-regions": cmd_list_regions,
        "list-plans": cmd_list_plans,
        "list-versions": cmd_list_versions,
        "get-plan-price": cmd_get_plan_price,
        "create-cluster": cmd_create_cluster,
        "list-clusters": cmd_list_clusters,
        "get-cluster": cmd_get_cluster,
        "create-node-pool": cmd_create_node_pool,
        "list-node-pools": cmd_list_node_pools,
        "get-config": cmd_get_config,
        "get-nodes": cmd_get_nodes,
        "wait-for-nodes": cmd_wait_for_nodes,
        "install-nginx": cmd_install_nginx,
        "install-cert-manager": cmd_install_cert_manager,
        "apply-cluster-issuer": cmd_apply_cluster_issuer,
        "create-namespace": cmd_create_namespace,
        "create-secret-generic": cmd_create_secret_generic,
        "create-secret-docker": cmd_create_secret_docker,
        "install-grafana-alloy": cmd_install_grafana_alloy,
        "verify-cluster": cmd_verify_cluster,
    }

    args = parser.parse_args()
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
