import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_KEYS = ("CLICKUP_TOKEN", "CLICKUP_LIST_ID", "CLICKUP_BRANCH_FIELD_ID")


def repo_root():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def load_env(root):
    values = {k: os.environ.get(k, "") for k in ENV_KEYS}
    for rel in (".env", "backend/.env", "frontend/.env"):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    if key in ENV_KEYS and not values.get(key):
                        values[key] = val.strip().strip('"').strip("'")
        except Exception:
            continue
    return values


def current_branch():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def changed_paths(limit=400):
    for args in (
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        ["git", "show", "--name-only", "--format=", "HEAD"],
    ):
        try:
            out = subprocess.run(args, capture_output=True, text=True, timeout=15)
            paths = [p for p in out.stdout.splitlines() if p.strip()]
            if paths:
                return paths[:limit]
        except Exception:
            continue
    return []


def clickup_get(path, token, params=None):
    url = "https://api.clickup.com/api/v2" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode())
        except Exception:
            return {"err": "HTTP " + str(exc.code)}
    except Exception as exc:
        return {"err": str(exc)}


def resolve_task(env, branch):
    token = env.get("CLICKUP_TOKEN")
    list_id = env.get("CLICKUP_LIST_ID")
    field_id = env.get("CLICKUP_BRANCH_FIELD_ID")
    if not (token and list_id and field_id):
        return None
    flt = json.dumps([{"field_id": field_id, "operator": "=", "value": branch}])
    data = clickup_get(
        "/list/" + list_id + "/task",
        token,
        {"archived": "false", "include_closed": "true", "custom_fields": flt},
    )
    if not isinstance(data, dict) or data.get("err"):
        return None
    tasks = data.get("tasks") or []
    return tasks[0] if tasks else None


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug[:60] or "untitled-feature"


def acquire_lock(root, name):
    lock = os.path.join(root, ".git", name + ".lock")
    if os.path.exists(lock):
        return None
    try:
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        with open(lock, "w") as fh:
            fh.write(str(os.getpid()))
        return lock
    except Exception:
        return None


def run_claude(root, prompt, log_name, label, expect_paths, timeout=1800):
    log_path = os.path.join(root, ".git", log_name)
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    code = -1
    try:
        with open(log_path, "a") as log:
            log.write("\n=== " + started + " " + label + " ===\n")
            log.flush()
            proc = subprocess.run(
                ["claude", "-p", "--output-format", "text", "--permission-mode", "acceptEdits"],
                input=prompt,
                stdout=log,
                stderr=log,
                text=True,
                timeout=timeout,
            )
            code = proc.returncode
    except Exception as exc:
        try:
            with open(log_path, "a") as log:
                log.write("ERROR: " + str(exc) + "\n")
        except Exception:
            pass

    produced = [p for p in expect_paths if os.path.exists(os.path.join(root, p))]
    ok = bool(produced)
    try:
        with open(log_path, "a") as log:
            log.write(
                ("OK " if ok else "FAILED ")
                + label
                + " (exit=" + str(code) + ", produced=" + str(len(produced)) + ")\n"
            )
    except Exception:
        pass
    return ok, produced
