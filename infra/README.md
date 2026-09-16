# Tone Infrastructure (Pulumi)

Infrastructure-as-code for Tone environments. A single, provider-agnostic Pulumi
program stands up the cloud services an environment needs (Kubernetes, database,
cache, file storage, VM) and can tear them all back down.

## How it fits together

```
Pulumi.<stack>.yaml   secrets + provider credentials for a stack (encrypted)
environments/<stack>.json   which services to build + their config, per env
        │
        ▼
   __main__.py   reads environments/<stack>.json, runs the component builders
        │
        ▼
   components/*.py   one ComponentResource per service; dispatches on `provider`
        │                (e.g. db → neon | digitalocean | azure) and returns outputs
        ▼
   catalog/<service>/<provider>.json   reference/default config presets per provider
```

Stacks (`environments/*.json` + `Pulumi.<stack>.yaml`): **`do`** (DigitalOcean),
`dev`, `infisical`, `demo`.

### What the `do` (DigitalOcean) stack creates

- **Kubernetes** — DOKS cluster with `cpuapp` + `workers` node pools
- **Database** — managed PostgreSQL cluster + `tone` database
- **Cache** — managed Valkey cluster
- **File storage** — Cloudflare R2 bucket

## Prerequisites

- **Pulumi CLI** — `brew install pulumi` (already declares its Python runtime via
  `Pulumi.yaml` → `virtualenv: venv`; `make bootstrap` provisions it).
- **A Pulumi backend** — `pulumi login` (Pulumi Cloud, or `pulumi login s3://…` /
  `pulumi login --local` for a self-managed backend).
- **Secrets decryption** — stack secrets in `Pulumi.<stack>.yaml` are encrypted.
  With Pulumi Cloud this is automatic; with a self-managed backend, export
  `PULUMI_CONFIG_PASSPHRASE` before running.
- The **DigitalOcean token** is already stored (encrypted) in `Pulumi.do.yaml` —
  no extra env var needed for the `do` stack.

## Quickstart

Run everything from this `infra/` directory:

```bash
make bootstrap                 # one-time: venv + deps + plugins
make preview STACK=do          # dry-run — read-only, creates nothing
make up      STACK=do          # bring the DigitalOcean stack UP
make down    STACK=do          # tear it back DOWN
```

`STACK` defaults to `do`, so `make preview` / `make up` / `make down` target
DigitalOcean unless you override it (`make up STACK=dev`).

## Make targets

| Target | Description |
|--------|-------------|
| `make help` | List all targets (default) |
| `make bootstrap` | Create the venv, install deps (incl. vendored `sdks/*`) and plugins |
| `make select` | Select `STACK`, creating it from `Pulumi.<stack>.yaml` if missing |
| `make preview` | Dry-run — show what `up` would change |
| `make up` | Bring the stack up (create/update resources) |
| `make down` / `make destroy` | Tear the stack down (destroy all resources) |
| `make refresh` | Reconcile Pulumi state with real cloud resources (drift check) |
| `make outputs` | Show stack outputs |
| `make config` | Show stack config |
| `make whoami` | Show the active Pulumi backend / user |

Every stateful target selects `STACK` first, so you can't accidentally act on the
wrong environment. `up` / `down` prompt for confirmation by default; pass `CI=1`
(`make up CI=1`) to auto-confirm in a pipeline.

## Maintenance

- **Add an environment/stack** — create `environments/<name>.json` (see `do.json`)
  and `Pulumi.<name>.yaml` with the provider credentials, then
  `make up STACK=<name>`.
- **Switch a service's provider** — change the `provider` key for that service in
  `environments/<stack>.json`; the matching `components/<service>.py` branch
  handles it. Reference defaults live in `catalog/<service>/<provider>.json`.
- **Add a provider to a service** — add a `_<provider>` method to the component's
  dispatch table in `components/<service>.py`, plus a `catalog/<service>/<provider>.json`.
- **Rotate the DigitalOcean token** —
  `pulumi config set --secret digitalocean:token <new-token> --stack do`.
- **Check for drift** — `make refresh STACK=do` (add `CI=1` to skip the prompt).
- **Upgrade a vendored SDK** — regenerate under `sdks/<name>/` and bump the version
  in `Pulumi.yaml` `packages:`, then `make bootstrap`.

## References

- Pulumi docs: https://www.pulumi.com/docs/
- DigitalOcean provider: https://www.pulumi.com/registry/packages/digitalocean/
