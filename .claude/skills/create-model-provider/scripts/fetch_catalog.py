#!/usr/bin/env python3
"""Call a vendor's catalogue endpoint and turn the response into seed rows.

Knows NOTHING about any specific vendor. Every detail — URL, how the key is sent, where
the list sits in the response — comes from the caller, who got it from the user. If the
user does not have those details, do not guess and do not go hunting for docs: collect
the model and voice ids from them directly and skip this script.

    # the common case: an OpenAI-shaped endpoint
    python fetch_catalog.py --url https://api.x.ai/v1/models --env GROK_API_KEY

    # anything else: say how the key is sent and where the list is
    python fetch_catalog.py --url https://api.acme.io/v1/voices \
        --env ACME_API_KEY --auth-header X-API-Key --json-path data \
        --id-field voice_id --label-field display_name

    # inspect an unfamiliar response before committing to a shape
    python fetch_catalog.py --url ... --env ... --raw

Options
  --auth-header NAME   header carrying the key      (default: Authorization)
  --auth-prefix STR    prefix before the key        (default: "Bearer " for
                       Authorization, empty otherwise)
  --auth-query NAME    send the key as a query param instead of a header
  --header K=V         extra header, repeatable (API versions etc.)
  --json-path a.b      dotted path to the list; omitted = auto-detect
  --id-field / --label-field   which keys to read; omitted = auto-detect
  --emit-seed LAYER    print a paste-ready dev-data.json block
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# Ordered guesses used only when the caller does not say. Never vendor-specific.
LIST_KEYS = ("data", "models", "voices", "items", "results", "value")
ID_KEYS = ("id", "model_id", "voice_id", "name", "model", "slug", "canonical_name")
LABEL_KEYS = ("display_name", "displayName", "name", "title", "label", "description")


def load_key(var):
    if os.environ.get(var):
        return os.environ[var]
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, errors="ignore"):
            line = line.strip()
            if line.startswith(f"{var}="):
                return line.partition("=")[2].strip().strip("\"'")
    return None


def find_list(payload, path):
    """Locate the list of entries: explicit path first, else the first list of dicts."""
    if path:
        for part in path.split("."):
            if not isinstance(payload, dict):
                return []
            payload = payload.get(part, [])
        return payload if isinstance(payload, list) else []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in LIST_KEYS:
            if isinstance(payload.get(key), list):
                return payload[key]
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
    return []


def pick(entry, explicit, candidates):
    if explicit:
        return entry.get(explicit)
    for key in candidates:
        val = entry.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--env", required=True, help="env var holding the key")
    ap.add_argument("--auth-header", default="Authorization")
    ap.add_argument("--auth-prefix")
    ap.add_argument("--auth-query")
    ap.add_argument("--header", action="append", default=[], metavar="K=V")
    ap.add_argument("--json-path", default="")
    ap.add_argument("--id-field")
    ap.add_argument("--label-field")
    ap.add_argument("--raw", action="store_true", help="dump the response and stop")
    ap.add_argument("--emit-seed", metavar="LAYER")
    ap.add_argument("--name", help="provider slug for --emit-seed")
    args = ap.parse_args()

    key = load_key(args.env)
    if not key:
        print(f"{args.env} is not set in .env or the environment.")
        print("Ask the user for the credential and add it before calling the vendor —")
        print("a provider seeded without a working key resolves to no service at all.")
        return 2
    print(f"# key: {args.env} ({len(key)} chars)", file=sys.stderr)

    url, headers = args.url, {"Accept": "application/json"}
    for raw in args.header:
        k, _, v = raw.partition("=")
        headers[k.strip()] = v.strip()
    if args.auth_query:
        url += f"{'&' if '?' in url else '?'}{args.auth_query}={key}"
    else:
        prefix = args.auth_prefix
        if prefix is None:
            prefix = "Bearer " if args.auth_header.lower() == "authorization" else ""
        headers[args.auth_header] = f"{prefix}{key}"

    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode()[:300]
        except Exception:
            pass
        print(f"HTTP {exc.code} from {args.url}")
        if exc.code in (401, 403):
            print("  The key was rejected. Confirm the value and how it is sent "
                  "(--auth-header / --auth-prefix / --auth-query) with the user.")
        elif exc.code == 404:
            print("  Endpoint not found. Confirm the exact catalogue URL with the user.")
        if body:
            print(f"  {body}")
        return 2
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2

    if args.raw:
        print(json.dumps(payload, indent=2)[:6000])
        return 0

    entries = find_list(payload, args.json_path)
    if not entries:
        print("No list found in the response. Re-run with --raw to see its shape, then "
              "pass --json-path.")
        print(json.dumps(payload, indent=2)[:1500])
        return 2

    rows, skipped = [], 0
    for entry in entries:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        ident = pick(entry, args.id_field, ID_KEYS)
        if not ident:
            skipped += 1
            continue
        rows.append({"id": ident, "label": pick(entry, args.label_field, LABEL_KEYS)})

    print(f"{len(rows)} entries" + (f" ({skipped} unusable)" if skipped else ""))
    if rows and not args.id_field:
        print(f"# id field auto-detected; verify against: "
              f"{', '.join(sorted(entries[0].keys())[:12])}", file=sys.stderr)

    if args.emit_seed:
        name = args.name or "REPLACE_ME"
        block = {
            "name": name,
            "provider_type": args.emit_seed,
            "display_name": name.replace("-", " ").replace("_", " ").title(),
            "description": name.replace("-", " ").title(),
            "api_key_env": args.env,
            "models": [{"name": r["id"], "meta_data": {"model": r["id"]}} for r in rows],
            "meta_data_schema": [],
            "status": "active",
        }
        print("\n" + json.dumps(block, indent=2))
        print("\n# Confirm with the user which of these to keep, then run "
              "validate_provider.py before seeding.", file=sys.stderr)
    else:
        print("\n" + json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
