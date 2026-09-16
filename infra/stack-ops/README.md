# stack-ops — Start / Stop the Tone app stack

Cost-saving **start / stop** for the Tone app. Pulumi keeps the app **node pool** defined as code;
starting/stopping is operational. This project does **not** create the cluster/DB/cache — that's the
sibling [`infra/`](../README.md) program. The always-on baseline (cluster control plane, DB, cache) is
never touched here.

Staging runs on **two clouds**, both named `tone-staging`:

| Cloud | Pulumi stack | Cluster | Stop lever |
|-------|--------------|---------|-----------|
| DigitalOcean (DOKS) | `staging` | `tone-staging-doks` | destroy the app node pool (Pulumi) |
| Azure (AKS) | `staging-azure` | `tone-staging-aks` | stop the whole cluster (`az aks stop`) |

The two clouds stop differently: DO has no cluster-pause, so the lever is destroying the **disposable
`apppool`** (a secondary pool the cluster's `cpuapp`/`workers` baseline is untouched by); Azure can
deallocate the entire cluster, so the lever is `az aks stop`.

The node config matches DO on both clouds: DO `s-2vcpu-4gb` (2 vCPU / 4 GB) ↔ Azure `Standard_B2s`
(2 vCPU / 4 GiB), pool counts `cpuapp` 2–3 + `workers` 1–2.

---

## 1. One-time setup

```bash
cd infra/stack-ops
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
pulumi login
```

**DigitalOcean (`staging`):**
```bash
pulumi stack init staging
pulumi config set --secret digitalocean:token <do-api-token>
# Pulumi.staging.yaml already targets clusterName: tone-staging-doks
```

**Azure (`staging-azure`):**
```bash
pulumi stack init staging-azure
az login
pulumi config set --secret azure-native:subscriptionId <subscription-id>
# Pulumi.staging-azure.yaml already targets resourceGroup/clusterName: tone-staging(-aks)
```

Secrets are set with `pulumi config set --secret …` (stored encrypted, never in plaintext).

---

## 2. Switch the cloud (select the stack)

```bash
pulumi stack select staging          # DigitalOcean
pulumi stack select staging-azure    # Azure
pulumi stack ls                      # shows the selected one (*)
```
Every `make` target takes `STACK=` (default `staging`), e.g. `make pool-apply STACK=staging-azure`.

---

## 3. Apply (provision / maintain the app node pool)

```bash
make pool-apply                      # DO      (= pulumi up --stack staging)
make pool-apply STACK=staging-azure  # Azure
make pool-preview [STACK=..]         # dry-run
```

> First provision the cluster itself with the sibling `infra/` program:
> `cd .. && pulumi up --stack staging` (DO) or `pulumi up --stack staging-azure` (Azure).

---

## 4. Start / Stop

### DigitalOcean (`staging`) — destroy/recreate the app pool
```bash
make do-start                        # pulumi up      -> create apppool (droplets on)
make do-stop                         # pulumi destroy -> delete apppool (droplets off, cost off)
```
The cluster's `cpuapp`/`workers` baseline stays up; only the app pool's droplets are removed.

### Azure (`staging-azure`) — pause/resume the whole cluster
```bash
make az-stop                         # az aks stop  -> all nodes deallocated, node cost off
make az-start                        # az aks start -> cluster + pods resume
```
(RG/CLUSTER default to `tone-staging` / `tone-staging-aks`; override with `RG=` / `CLUSTER=`.)

### App-only (either cloud, cluster stays warm)
```bash
make kubeconfig-do                   # or: make kubeconfig-azure
make app-stop                        # scale Deployments -> 0
make app-start                       # scale Deployments -> REPLICAS (default 1)
```

---

## 5. Status

```bash
make status [STACK=..]               # pulumi outputs + kubectl workloads
```

---

## Command reference

| Goal | DigitalOcean (`staging`) | Azure (`staging-azure`) |
|------|--------------------------|-------------------------|
| Select | `pulumi stack select staging` | `pulumi stack select staging-azure` |
| Apply pool | `make pool-apply` | `make pool-apply STACK=staging-azure` |
| **Stop** (nodes off) | `make do-stop` | `make az-stop` |
| **Start** | `make do-start` | `make az-start` |
| App-only pause/resume | `make app-stop` / `app-start` | `make app-stop` / `app-start` |
| Kubeconfig | `make kubeconfig-do` | `make kubeconfig-azure` |

---

## Notes

- **Pin the app to `apppool`** so a stop actually removes its compute:
  - DO: `nodeSelector: { doks.digitalocean.com/node-pool: apppool }`
  - Azure: `nodeSelector: { agentpool: apppool }`
- **Cost:** DO stop removes the app pool's droplets (baseline `cpuapp`/`workers` stays); Azure stop
  deallocates every node. DB + cache are external/managed and stay up on both.
- **Node parity:** DO `s-2vcpu-4gb` ↔ Azure `Standard_B2s` (both 2 vCPU / 4 GB). Change sizes in
  `Pulumi.staging.yaml` / `Pulumi.staging-azure.yaml`, then `make pool-apply`.
- **Sibling project:** the Azure-only equivalent for tone-test lives in `toneloop` (its own `stack-ops`).
- **Add a cloud:** add `pools/<cloud>.py` (subclass `AppNodePool`) + one line in `pools/__init__.py`.
