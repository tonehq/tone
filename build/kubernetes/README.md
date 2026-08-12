# Kubernetes deployment — reusable templates

One shared, env-agnostic template set drives every environment. You do **not**
copy manifests per environment; you add a small config file and render.

## Layout

```
build/kubernetes/
├── _base/            # ONE reusable app manifest set (${VAR} placeholders)
│   ├── api/  call/  worker/  keda/  letsencrypt-prod.yaml
├── monitoring/       # ONE reusable monitoring set (Grafana Alloy) — deployed SEPARATELY
│   ├── namespace.yaml  rbac.yaml  configmap.yaml  daemonset.yaml
├── envs/             # per-environment config — the ONLY thing that differs per env
│   └── staging-do.env
├── render.sh              # renders app (_base) + <env>.env -> .rendered/<env>/
├── render-monitoring.sh   # renders monitoring/ for one cluster (CLUSTER_NAME only)
└── .rendered/             # build artifact (gitignored) — never committed
```

Legacy per-env copies (`staging/`, `staging-aws/`, `dev/`, …) predate this and
are still wired to their own workflows. Migrate them onto `_base` one at a time.

## Two deploy units

| Unit | Templates | Namespace | Workflow | Cadence | Config source |
|------|-----------|-----------|----------|---------|---------------|
| **App** (per env) | `_base/` | `staging-do` | `staging-do.yaml` (push) | every push | `envs/staging-do.env` |
| **Monitoring** (per cluster) | `monitoring/` | `monitoring` | `monitoring.yaml` (manual, **all clusters**) | once per cluster | `envs/<target>.env` + repo secret |

Monitoring is a per-cluster concern (own namespace + cluster-wide RBAC) and its
manifests are identical everywhere, so **one** `monitoring.yaml` serves every
cluster — pick the `target` on dispatch. It reads config from the SAME env files
as the app.

### One env file drives everything (app + monitoring)

`envs/<target>.env` is the single "run file". It holds all non-secret config
AND the *name* of the secret that holds the kubeconfig:

```
CLUSTER_NAME=tonedo-doks
KUBE_CONFIG_SECRET=STAGING_DO_KUBE_CONFIG_JSON   # NAME, not value
```

Both workflows resolve the cluster the same way: they read `KUBE_CONFIG_SECRET`
from the env file and pull that secret's value out of `toJSON(secrets)` (GitHub
can't index secrets by a dynamic name directly; this is the standard way).
The kubeconfig VALUE stays a GitHub secret — it must never be committed.

Grafana Cloud creds (`GRAFANA_*`) are repo-level and shared — one stack ingests
every cluster, keyed by the `cluster` label. Onboard a new cluster =
1. add `envs/<target>.env` (with `CLUSTER_NAME` + `KUBE_CONFIG_SECRET`),
2. add the GitHub secret named by `KUBE_CONFIG_SECRET`,
3. add `<target>` to the `options` list in `monitoring.yaml`.
No per-target secret wiring in the workflow.

## Template variables (all set in `envs/<name>.env`)

Identity/routing: `NAMESPACE`, `RESOURCE_PREFIX`, `ENVIRONMENT`, `APP_ENV`
(app `ENV` → Infisical env/DB), `API_DOMAIN`, `CALL_DOMAIN`, `IMAGE_REPO`,
`INFISICAL_HOST`, `CLUSTER_NAME` (monitoring label).

Capacity/behaviour: `*_REPLICAS`, `INBOUND/OUTBOUND_MAX_CONCURRENT_CALLS`,
per-workload `*_CPU/MEM_REQUEST/LIMIT`, KEDA `DOC/OUTBOUND_MIN/MAX_REPLICAS`,
`LETSENCRYPT_EMAIL`.

Two tokens are intentionally left unrendered: `${IMAGE_TAG}` (filled by CI with
the build sha) and `$(POD_NAME)` (a Kubernetes downward-API fieldRef).

## Add a new environment

1. `cp build/kubernetes/envs/staging-do.env build/kubernetes/envs/<name>.env` and edit values.
2. Copy `.github/workflows/staging-do.yaml` (and `-monitoring.yaml` if wanted) →
   `<name>*.yaml`; change the branch, `ENV_FILE`, `RENDER_DIR`, image tags and
   kubeconfig secret. Namespace + rollout names come from the env file automatically.
3. Provision the cluster prereqs (ingress-nginx, cert-manager, KEDA) and the
   namespace secrets (`infisical-credentials`, `ghcr-auth`, `keda-postgres`).

## Render locally (dry run)

```bash
# App
./build/kubernetes/render.sh build/kubernetes/envs/staging-do.env
kubectl apply --dry-run=client -R -f build/kubernetes/.rendered/staging-do

# Monitoring
./build/kubernetes/render.sh build/kubernetes/envs/staging-do.env \
    build/kubernetes/.rendered/staging-do-monitoring build/kubernetes/monitoring
```
