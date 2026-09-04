#!/usr/bin/env python3
"""Analyse the repo and derive everything the stepper needs. Nothing is hardcoded.

Reads dev/dev-data.json and core/services/pipeline/service_factory.py and works out,
from what is actually there:

  * which providers exist, per layer, and their wiring state
  * which factory branches exist, including the generic fallback map parsed from source
  * the provider/model/voice schema — required keys, optional keys, enum values —
    inferred from the existing entries rather than a fixed list

    python analyze.py                  # full report
    python analyze.py --schema         # derived schema only
    python analyze.py --provider NAME  # one provider, or a verdict if absent
    python analyze.py --json           # machine-readable
"""
import argparse
import ast
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SEED = os.path.join(ROOT, "dev", "dev-data.json")
FACTORY = os.path.join(ROOT, "core", "services", "pipeline", "service_factory.py")

# The only structural assumption: seed buckets are "<layer>_providers".
# Layers themselves are discovered from the file.
BUCKET_RE = re.compile(r"^(?P<layer>[a-z]+)_providers$")


def seed_buckets(seed):
    return {k: BUCKET_RE.match(k).group("layer")
            for k in seed if BUCKET_RE.match(k) and isinstance(seed[k], list)}


def factory_branches(src):
    """Per builder: the explicit provider_name branches, plus any generic fallback keys.

    Both are parsed from source, so this stays correct as the factory changes.
    """
    tree = ast.parse(src)
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("build_"):
            continue
        kind = node.name[len("build_"):]
        if kind not in ("llm", "stt", "tts"):
            continue
        seg = ast.get_source_segment(src, node) or ""
        explicit = set(re.findall(r'provider_name == "([^"]+)"', seg))
        # A dict literal of provider -> URL inside the builder is a generic fallback:
        # anything keyed there is reachable without its own branch.
        generic = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Dict) and sub.keys:
                keys = [k.value for k in sub.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)]
                vals = [v.value for v in sub.values
                        if isinstance(v, ast.Constant) and isinstance(v.value, str)]
                if keys and len(vals) == len(keys) and \
                   sum(v.startswith("http") for v in vals) >= max(2, len(vals) // 2):
                    generic |= set(keys)
        out[kind] = {"explicit": explicit, "generic": generic,
                     "all": explicit | generic}
    return out


def derive_schema(seed, buckets):
    """Infer the entry schema from existing data instead of asserting one."""
    schema = {}
    for bucket, layer in buckets.items():
        entries = seed[bucket]
        if not entries:
            continue
        n = len(entries)
        key_counts = Counter(k for e in entries for k in e)
        model_counts = Counter(k for e in entries for m in e.get("models", []) for k in m)
        voice_counts = Counter(k for e in entries for v in (e.get("voices") or []) for k in v)
        n_models = sum(len(e.get("models", [])) for e in entries) or 1
        n_voices = sum(len(e.get("voices") or []) for e in entries) or 1

        enums = {}
        for field in ("data_type", "type", "format"):
            vals = set()
            def walk(o):
                if isinstance(o, dict):
                    if "data_type" in o and "type" in o and o.get(field) is not None:
                        vals.add(o[field])
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            walk(entries)
            if vals:
                enums[field] = sorted(vals)
        enums["status"] = sorted({str(e.get("status")) for e in entries if e.get("status")})
        enums["provider_type"] = sorted({e.get("provider_type") for e in entries
                                         if e.get("provider_type")})

        schema[layer] = {
            "bucket": bucket,
            "provider_keys_required": sorted(k for k, c in key_counts.items() if c == n),
            "provider_keys_optional": sorted(k for k, c in key_counts.items() if c < n),
            "model_keys_required": sorted(k for k, c in model_counts.items() if c == n_models),
            "model_keys_optional": sorted(k for k, c in model_counts.items() if c < n_models),
            "voice_keys_required": sorted(k for k, c in voice_counts.items() if c == n_voices),
            "voice_keys_optional": sorted(k for k, c in voice_counts.items() if c < n_voices),
            "enums": enums,
            "provider_count": n,
        }
    return schema


def env_keys():
    keys = {k for k, v in os.environ.items() if v}
    for name in (".env", ".env.example"):
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        for line in open(path, errors="ignore"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if v.strip().strip("\"'"):
                    keys.add(k.strip())
    return keys


def inventory(seed, buckets, branches, env):
    rows = []
    for bucket, layer in buckets.items():
        for prov in seed[bucket]:
            key = prov.get("api_key_env") or ""
            wired = prov["name"] in branches.get(layer, {}).get("all", set())
            rows.append({
                "layer": layer, "name": prov["name"],
                "models": len(prov.get("models") or []),
                "voices": len(prov.get("voices") or []),
                "wired": wired,
                "via_generic": prov["name"] in branches.get(layer, {}).get("generic", set())
                               and prov["name"] not in branches.get(layer, {}).get("explicit", set()),
                "api_key_env": key or None,
                "key_set": bool(key) and key in env,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", action="store_true")
    ap.add_argument("--provider")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    seed = json.load(open(SEED))
    src = open(FACTORY).read()
    buckets = seed_buckets(seed)
    branches = factory_branches(src)
    schema = derive_schema(seed, buckets)
    env = env_keys()
    rows = inventory(seed, buckets, branches, env)

    if args.json:
        print(json.dumps({
            "layers": sorted(buckets.values()),
            "schema": schema,
            "branches": {k: {kk: sorted(vv) for kk, vv in v.items()}
                         for k, v in branches.items()},
            "inventory": rows,
        }, indent=2))
        return 0

    if args.provider:
        name = args.provider
        hits = [r for r in rows if r["name"] == name]
        if hits:
            for r in hits:
                state = ("fully wired" if r["wired"] and r["key_set"]
                         else "seeded + wired, API KEY NOT SET" if r["wired"]
                         else "seeded but NO factory branch")
                via = " (via the generic fallback map, no branch of its own)" if r["via_generic"] else ""
                print(f"{r['layer']}/{name}: {state}{via}")
                print(f"  models={r['models']} voices={r['voices']} "
                      f"env={r['api_key_env']} key_set={r['key_set']}")
            print("\n-> Provider exists. Adding models/voices is a data-only change.")
        else:
            in_code = [k for k, v in branches.items() if name in v["all"]]
            if in_code:
                print(f"{name}: NOT in dev-data.json, but a {'/'.join(in_code)} branch "
                      f"exists.\n-> Data-only change: no code needed.")
            else:
                print(f"{name}: not in dev-data.json and no factory branch.\n"
                      f"-> Full flow: code + data + credential.")
        return 0

    if not args.schema:
        print(f"{'LAYER':5} {'PROVIDER':22} {'MODELS':>6} {'VOICES':>6} {'WIRED':>6} "
              f"{'ENV VAR':26} {'KEY':>4}")
        print("-" * 82)
        for r in sorted(rows, key=lambda r: (r["layer"], r["name"])):
            w = "gen" if r["via_generic"] else ("yes" if r["wired"] else "NO")
            print(f"{r['layer']:5} {r['name']:22} {r['models']:>6} {r['voices']:>6} "
                  f"{w:>6} {(r['api_key_env'] or '-'):26} "
                  f"{'yes' if r['key_set'] else 'NO':>4}")
        seeded = {(r["layer"], r["name"]) for r in rows}
        orphans = sorted((k, b) for k, v in branches.items()
                         for b in v["explicit"] if (k, b) not in seeded)
        if orphans:
            print("\nBranches with no seed row — usable after a data-only change:")
            for layer, name in orphans:
                print(f"  {layer}/{name}")
        print()

    print("Derived schema (inferred from existing entries, not hardcoded):")
    for layer, s in schema.items():
        print(f"\n  [{layer}]  {s['provider_count']} providers in {s['bucket']}")
        print(f"    provider required : {', '.join(s['provider_keys_required'])}")
        print(f"    provider optional : {', '.join(s['provider_keys_optional']) or '-'}")
        print(f"    model required    : {', '.join(s['model_keys_required'])}")
        print(f"    model optional    : {', '.join(s['model_keys_optional']) or '-'}")
        if s["voice_keys_required"]:
            print(f"    voice required    : {', '.join(s['voice_keys_required'])}")
            print(f"    voice optional    : {', '.join(s['voice_keys_optional']) or '-'}")
        for field, vals in s["enums"].items():
            if vals:
                print(f"    {field:17} : {', '.join(vals)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
