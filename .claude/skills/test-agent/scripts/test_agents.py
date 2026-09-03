#!/usr/bin/env python3
"""Provision and drive the three swap-test agents.

    test_agents.py status
    test_agents.py provision --stt deepgram/nova-3 --llm openai/gpt-5.4-mini \
                             --tts cartesia/sonic-3.5
    test_agents.py swap --layer stt --provider deepgram --model flux
    test_agents.py teardown

Nothing about any vendor is hardcoded. Providers and models are read from the API at
run time, so the choices always reflect what the target environment actually has.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
LAYERS = {"stt": "stt_settings", "llm": "llm_settings", "tts": "voice_settings"}
AGENT_FOR = {"stt": "swap-stt", "llm": "swap-llm", "tts": "swap-tts"}


DEFAULT_FIRST_MESSAGE = (
    "Hi, thanks for calling. I can help with your booking. What can I do for you?"
)

DEFAULT_PROMPT = """You are a receptionist for a small dental practice taking a phone call.

Your job is to help the caller book, move or cancel an appointment, and to answer basic
questions about opening hours and location.

How to speak:
- One or two sentences per turn. This is a phone call, not an email.
- Plain spoken language. No lists, no markdown, no headings.
- Say numbers the way a person would: "half past two", "the fourteenth of March".
- If you did not catch something, ask them to repeat it rather than guessing.
- Never invent an appointment slot, a price, or a policy. Say you will check instead.

Facts you may use:
- Open Monday to Friday, 9am to 5pm. Closed weekends.
- The practice is on Mill Road, opposite the library.
- A check-up takes 30 minutes, a cleaning takes 45.

Start by greeting the caller, then let them speak. Keep the call moving, and confirm the
details back to them before you finish."""


def env(name, default=None):
    if os.environ.get(name):
        return os.environ[name]
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, errors="ignore"):
            m = re.match(rf"^{re.escape(name)}=(.*)$", line.strip())
            if m:
                return m.group(1).strip().strip("\"'").split("  #")[0].strip()
    return default


LOCAL_PORTS = (8000, 8080, 3001)


def _local_api():
    """A local server, if one is listening. Preferred over staging so a dev run never
    writes to a shared environment by accident."""
    for port in LOCAL_PORTS:
        url = f"http://localhost:{port}"
        try:
            req = urllib.request.Request(f"{url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=1.5):
                return f"{url}/api/v1"
        except urllib.error.HTTPError:
            return f"{url}/api/v1"
        except Exception:
            continue
    return None


def base_url():
    explicit = env("TONE_API_BASE")
    if explicit:
        return explicit.rstrip("/")
    local = _local_api()
    if local:
        return local
    path = os.path.join(ROOT, "build", "kubernetes", "envs", "staging.env")
    if os.path.exists(path):
        for line in open(path, errors="ignore"):
            m = re.match(r"^API_DOMAIN=(.+)$", line.strip())
            if m:
                return f"https://{m.group(1).strip()}/api/v1"
    raise SystemExit("No API base. Start the local server, set TONE_API_BASE, "
                     "or add API_DOMAIN to staging.env.")


def call(method, path, token=None, body=None, base=None, want_cookies=False,
         timeout=60):
    url = f"{base or base_url()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": env("TONE_USER_AGENT",
                          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"),
    }
    if token:
        headers["Cookie"] = f"access_token={token}"
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            out = json.loads(raw) if raw else {}
            if want_cookies:
                jar = resp.headers.get_all("Set-Cookie") or []
                return out, jar
            return out
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode()[:400]
        except Exception:
            pass
        hint = ""
        if "error code: 1010" in detail or exc.code == 403:
            hint = ("\nCloudflare rejected the request signature. The script sends a "
                    "browser User-Agent; override it with TONE_USER_AGENT if the edge "
                    "still blocks, or run from a network the WAF allows.")
        raise SystemExit(f"{method} {path} -> HTTP {exc.code}{hint}\n{detail}")


def login(base):
    email, password = env("TONE_STAGING_EMAIL"), env("TONE_STAGING_PASSWORD")
    if not email or not password:
        raise SystemExit(
            "TONE_STAGING_EMAIL / TONE_STAGING_PASSWORD not in .env or environment.\n"
            "Ask the user for the account to use — do not guess one."
        )
    out, jar = call("POST", "/auth/login", body={"email": email, "password": password},
                    base=base, want_cookies=True)
    for raw in jar:
        m = re.match(r"\s*access_token=([^;]+)", raw)
        if m and m.group(1) not in ('""', ""):
            return m.group(1)
    for src in (out, out.get("data") or {}):
        for key in ("access_token", "token", "accessToken"):
            if src.get(key):
                return src[key]
    raise SystemExit(
        "Login succeeded but no access_token. The API sets it as an httpOnly cookie; "
        f"none came back. Response keys: {sorted(out)}"
    )


ORG_STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".org-state.json")


def _state():
    try:
        return json.load(open(ORG_STATE))
    except Exception:
        return {}


def save_org(base, org_id, name):
    """Remember which org provision created, keyed by API base.

    Without this only `provision` knows about the org it made; `status`, `swap`
    and `teardown` would log in, land in the account's default org and report the
    agents as missing.
    """
    st = _state()
    st[base] = {"organization_id": str(org_id), "name": name}
    json.dump(st, open(ORG_STATE, "w"), indent=2)


def load_org(base):
    return (_state().get(base) or {}).get("organization_id")


def forget_org(base):
    st = _state()
    st.pop(base, None)
    json.dump(st, open(ORG_STATE, "w"), indent=2)


def switch_org(token, base, org_id):
    """Exchange the token for one scoped to org_id."""
    out, jar = call("POST", "/auth/switch_organization", token,
                    {"organization_id": str(org_id)}, base, want_cookies=True)
    for raw in jar:
        m = re.match(r"\s*access_token=([^;]+)", raw)
        if m and m.group(1) not in ('""', ""):
            return m.group(1)
    for src in (out, out.get("data") or {}):
        for key in ("access_token", "token"):
            if src.get(key):
                return src[key]
    raise SystemExit(
        "switch_organization returned no token. Continuing would read or write the "
        "previous org, which is not what was asked for — stopping."
    )


def session(base, org_override=None):
    """Log in and land in the swap-test org, so every command sees the same agents."""
    token = login(base)
    org_id = org_override or load_org(base)
    if org_id:
        token = switch_org(token, base, org_id)
    return token, org_id


def catalogue(token, base):
    """Provider slug -> {id, display_name, models}.

    Model lists are fetched concurrently: one call per provider done serially takes
    minutes against ~60 providers.
    """
    out = call("POST", "/services/providers/list_providers", token, {"page_size": 200}, base)
    rows = out.get("items") or out.get("rows") or out.get("data") or out.get("providers") or []
    provs = [p for p in (rows if isinstance(rows, list) else []) if p.get("id")]

    def fetch(prov):
        models = call("POST", f"/services/providers/{prov['id']}/models",
                      token, {"page_size": 200}, base)
        mrows = models.get("items") or models.get("rows") or models.get("data") or []
        return prov, [{"id": m.get("id"), "name": m.get("name"), "kind": m.get("kind")}
                      for m in (mrows if isinstance(mrows, list) else [])]

    result = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for prov, models in pool.map(fetch, provs):
            result[prov.get("slug") or prov.get("provider_id")] = {
                "id": prov["id"],
                "display_name": prov.get("display_name"),
                "models": models,
            }
    return result


def agents(token, base):
    out = call("GET", "/agent/get_all_agents", token, base=base)
    rows = out if isinstance(out, list) else (out.get("items") or out.get("data") or [])
    return {a.get("name"): a for a in rows if isinstance(a, dict)}


def cmd_status(args):
    base = base_url()
    token, org_id = session(base, getattr(args, "org", None))
    found = agents(token, base)
    print(f"API: {base}")
    print(f"org: {org_id or '<account default — nothing provisioned here yet>'}\n")
    missing = []
    for layer, name in AGENT_FOR.items():
        a = found.get(name)
        if not a:
            missing.append(name)
            print(f"  {layer:4} {name:12} NOT PROVISIONED")
            continue
        cfg = call("GET", f"/agent/get_agent?agent_id={a['id']}", token, base=base) or {}
        cfg = cfg.get("config") or cfg
        blob = cfg.get(LAYERS[layer]) or {}
        print(f"  {layer:4} {name:12} agent_id={a['id']}")
        print(f"       {LAYERS[layer]}: provider_id={blob.get('provider_id')} "
              f"model_id={blob.get('model_id')}")
    if missing:
        print(f"\n  {len(missing)} agent(s) missing — run: provision")
    return 0


def cmd_catalogue(args):
    base = base_url()
    token, _ = session(base, getattr(args, "org", None))
    cat = catalogue(token, base)
    want = args.layer
    for slug, prov in sorted(cat.items()):
        models = [m for m in prov["models"] if not want or m.get("kind") == want]
        if want and not models:
            continue
        kinds = sorted({m["kind"] for m in prov["models"] if m.get("kind")})
        print(f"  {slug:22} {prov['display_name'] or '':26} {','.join(kinds)}")
        if want:
            for m in sorted(models, key=lambda m: m["name"] or ""):
                print(f"      {slug}/{m['name']}")
    shown = "providers" if not want else f"providers with a {want} model"
    print(f"\n  {len(cat)} {shown}. Pass provider/model to provision or swap.")
    return 0


def _resolve(cat, spec, layer):
    if "/" not in spec:
        raise SystemExit(f"--{layer} must be provider/model, got {spec!r}")
    slug, _, mname = spec.partition("/")
    prov = cat.get(slug)
    if not prov:
        raise SystemExit(f"No provider {slug!r}. Run `catalogue` to see slugs.")
    model = next((m for m in prov["models"] if m["name"] == mname), None)
    if not model:
        names = ", ".join(sorted(m["name"] for m in prov["models"])[:12])
        raise SystemExit(f"No model {mname!r} on {slug}. Have: {names}")
    if model.get("kind") and model["kind"] != layer:
        raise SystemExit(f"{spec} is a {model['kind']} model, but --{layer} expects {layer}")
    return {"provider_id": prov["id"], "model_id": model["id"]}


def switch_token(token, base, org_id):
    out, jar = call("POST", "/auth/switch_organization", token,
                    {"organization_id": str(org_id)}, base, want_cookies=True)
    for raw in jar:
        m = re.match(r"\s*access_token=([^;]+)", raw)
        if m and m.group(1) not in ('""', ""):
            return m.group(1)
    for src in (out, out.get("data") or {}):
        for key in ("access_token", "token"):
            if src.get(key):
                return src[key]
    raise SystemExit("switch_organization returned no token.")


def use_org(token, base, name):
    """Switch into an existing org by name. The agents live in the org provision made,
    not the one you log into, so every command needs this or it reads the wrong org."""
    if not name:
        return token
    out = call("POST", "/organization/get_associated_tenants", token, {"page_size": 200}, base)
    rows = out.get("rows") or out.get("items") or out.get("data") or []
    match = next((o for o in rows if o.get("name") == name), None)
    if not match:
        names = ", ".join(sorted(o.get("name", "?") for o in rows))
        raise SystemExit(f"No org named {name!r} on this account. You have: {names}")
    print(f"using org {name!r} ({match['id']})")
    return switch_token(token, base, match["id"])


def ensure_org(token, base, name):
    """Create the test org under the caller's account and return a token scoped to it."""
    made = call("POST", f"/organization/create_tenants?name={urllib.parse.quote(name)}",
                token, {}, base)
    org = made.get("organization") or made.get("data") or made
    org_id = org.get("id") or org.get("organization_id")
    if not org_id:
        raise SystemExit(f"create_tenants returned no organization id. Keys: {sorted(made)}")
    print(f"created org {name!r}  organization_id={org_id}")
    token = switch_org(token, base, org_id)
    print("switched into the new org")
    save_org(base, org_id, name)
    return token, org_id


def published_config_id(agent_response):
    """The config id create_agent/clone_agent already published.

    ``create_agent`` passes its ``config`` payload through ``_apply_attachments``
    → ``_upsert_new_config``, which writes version 1 AND sets
    ``published_config_id``. There is no separate publish step to make; the
    agent is live the moment it is created. (The old code posted to
    ``/agent_config/upsert_agent_config``, which casts ``agent_id`` to ``int``
    while ``Agent.id`` is a UUID — it always 500s. See the xfail in
    test-cases/ee/test_agent_configs.py.)
    """
    body = agent_response.get("data") or agent_response
    cfg = body.get("config") or {}
    return cfg.get("id")


def cmd_provision(args):
    base = base_url()
    token = login(base)
    token, _ = ensure_org(token, base, args.org)
    existing = agents(token, base)
    already = [n for n in AGENT_FOR.values() if n in existing]
    if already:
        raise SystemExit(
            f"Already provisioned: {', '.join(already)}. Run `teardown` first, or "
            f"`swap` to change a layer without recreating anything."
        )
    cat = catalogue(token, base)
    baseline = {
        "stt_settings": _resolve(cat, args.stt, "stt"),
        "llm_settings": _resolve(cat, args.llm, "llm"),
        "voice_settings": _resolve(cat, args.tts, "tts"),
    }
    if args.voice_id:
        baseline["voice_settings"]["voice_id"] = args.voice_id

    config = {
        "first_message": args.first_message,
        "system_prompt_template": args.prompt,
        "mode": "prompt",
        **baseline,
    }
    created = {}
    seed_layer = "stt"
    seed_name = AGENT_FOR[seed_layer]
    agent = call("POST", "/agent/create_agent", token, {
        "name": seed_name,
        "description": f"swap-test agent: vary {seed_layer} only",
        "agent_type": "both",
        "is_active": True,
        "config": config,
    }, base)
    created[seed_name] = agent.get("id") or (agent.get("data") or {}).get("id")
    cfg_id = published_config_id(agent)
    print(f"created {seed_name}  agent_id={created[seed_name]}")
    if not cfg_id:
        raise SystemExit(
            f"{seed_name} was created with no live config — the clones would copy "
            f"nothing and every agent would resolve an empty pipeline. Stopping."
        )
    print(f"  live config {cfg_id}")

    for layer in ("llm", "tts"):
        name = AGENT_FOR[layer]
        print(f"cloning {name} (deep-copies config, tools, MCP and knowledge-base rows "
              f"— this takes a while)...")
        clone = call("POST", f"/agent/clone_agent?agent_id={created[seed_name]}",
                     token, {"name": name}, base, timeout=600)
        created[name] = clone.get("id") or (clone.get("data") or {}).get("id")
        print(f"cloned  {name:12} agent_id={created[name]}  "
              f"live config {published_config_id(clone)}")

    print("\nAll three share one config, cloned from the same source, so only the layer "
          "you swap differs.")
    for layer, name in AGENT_FOR.items():
        print(f"  {name:12} vary {layer}")
    return 0


def cmd_teardown(args):
    base = base_url()
    token, _ = session(base, getattr(args, "org", None))
    found = agents(token, base)
    targets = [(n, a) for n, a in found.items() if n in AGENT_FOR.values()]
    if not targets:
        print("Nothing to remove.")
        return 0
    print("About to delete:")
    for name, a in targets:
        print(f"  {name:12} {a['id']}")
    if not args.yes:
        print("\nRe-run with --yes to confirm. Deletes are not reversible.")
        return 1
    for name, a in targets:
        call("DELETE", f"/agent/delete_agent?agent_id={a['id']}", token, base=base)
        print(f"deleted {name}")
    forget_org(base)
    print("forgot the saved org — the next provision creates a fresh one")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ORG_HELP = ("organization_id to act in; defaults to the org the last provision "
                "created for this API base")
    st = sub.add_parser("status", help="show the three agents and their current stack")
    st.add_argument("--org", help=ORG_HELP)
    c = sub.add_parser("catalogue", help="list providers and models available in the env")
    c.add_argument("--layer", choices=sorted(LAYERS),
                   help="only providers serving this layer, with model names")
    c.add_argument("--org", help=ORG_HELP)
    q = sub.add_parser("provision", help="create the three agents from one baseline")
    q.add_argument("--org", required=True,
                   help="organisation to create and put the agents in; required, so a "
                        "test run never adds agents to an org you already use")
    q.add_argument("--stt", required=True, metavar="provider/model")
    q.add_argument("--llm", required=True, metavar="provider/model")
    q.add_argument("--tts", required=True, metavar="provider/model")
    q.add_argument("--voice-id", dest="voice_id")
    q.add_argument("--prompt", default=DEFAULT_PROMPT)
    q.add_argument("--first-message", dest="first_message", default=DEFAULT_FIRST_MESSAGE)
    t = sub.add_parser("teardown", help="delete the three agents")
    t.add_argument("--yes", action="store_true")
    t.add_argument("--org", help=ORG_HELP)
    p = sub.add_parser("swap", help="point one agent's layer at a different provider/model")
    p.add_argument("--layer", choices=sorted(LAYERS), required=True)
    p.add_argument("--provider", required=True, help="provider slug, from `catalogue`")
    p.add_argument("--model", required=True, help="model name, from `catalogue`")
    p.add_argument("--org", help=ORG_HELP)
    args = ap.parse_args()
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "catalogue":
        return cmd_catalogue(args)
    if args.cmd == "provision":
        return cmd_provision(args)
    if args.cmd == "teardown":
        return cmd_teardown(args)
    if args.cmd == "swap":
        return cmd_swap(args)
    return 1


def cmd_swap(args):
    base = base_url()
    token, _ = session(base, getattr(args, "org", None))
    name = AGENT_FOR[args.layer]
    found = agents(token, base)
    if name not in found:
        raise SystemExit(f"{name} is not provisioned. Run provision first.")
    cat = catalogue(token, base)
    prov = cat.get(args.provider)
    if not prov:
        raise SystemExit(f"No provider {args.provider!r}. Run `catalogue` to see slugs.")
    model = next((m for m in prov["models"] if m["name"] == args.model), None)
    if not model:
        names = ", ".join(sorted(m["name"] for m in prov["models"])[:12])
        raise SystemExit(f"No model {args.model!r} on {args.provider}. Have: {names}")
    if model.get("kind") and model["kind"] != args.layer:
        raise SystemExit(
            f"{args.model} is a {model['kind']} model but --layer is {args.layer}. "
            f"Swapping it would leave the agent with no working {args.layer}."
        )
    agent = found[name]
    cfg = call("GET", f"/agent/get_agent?agent_id={agent['id']}", token, base=base) or {}
    cfg = cfg.get("config") or cfg
    blob = dict(cfg.get(LAYERS[args.layer]) or {})
    before = (blob.get("provider_id"), blob.get("model_id"))
    blob["provider_id"] = prov["id"]
    blob["model_id"] = model["id"]
    # Partial config write: _apply_config_fields only touches keys present in the
    # payload, so the other two layers and the prompt are left exactly as they were.
    call("PUT", f"/agent/update_agent?agent_id={agent['id']}", token,
         {"config": {LAYERS[args.layer]: blob}}, base)
    print(f"{name}.{LAYERS[args.layer]}")
    print(f"  before: provider_id={before[0]} model_id={before[1]}")
    print(f"  after : provider_id={prov['id']} model_id={model['id']}  "
          f"({args.provider}/{args.model})")
    print("\nThe other two agents are unchanged — any difference on a call is this swap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
