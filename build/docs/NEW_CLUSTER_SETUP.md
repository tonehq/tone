# New Cluster / Environment Setup Guide

End-to-end guide for standing up a new Tone environment on a fresh Kubernetes
cluster — provisioning, base add-ons, database, secrets, manifests, CI/CD,
migrations — with **special focus on the call-worker StatefulSet** and the
per-pod URL pinning, since those are the parts most easily gotten wrong.

Throughout, replace `staging` / `staging-call.trytone.ai` / `staging-tone-*`
with the new environment's names.

---

## 0. Architecture — what runs in a cluster

```
                        ┌────────────────────────── Kubernetes cluster ──────────────────────────┐
 Twilio / browser ──►  ingress-nginx  ──►  api (Deployment)         REST + dashboard + /twiml
                                        ──►  call (StatefulSet)       voice pipeline, /ws, /pod/N/ws
                                             worker (Deployment)      Procrastinate: ingestion + pod_sync
                        cert-manager        TLS certs (Let's Encrypt)
                        Grafana Alloy       logs → Loki, node metrics → Prometheus (Grafana Cloud)
                        └──────────────────────────────────────────────────────────────────────────┘
   External: Neon (Postgres)   Infisical (secrets)   Docker registry (image)   DNS (A records)
```

- **api** — a Deployment; serves the REST API, dashboard backend, and Twilio `/twiml`.
- **call** — a **StatefulSet**; runs the voice pipeline. StatefulSet (not Deployment)
  because pod pinning needs stable ordinal pod names.
- **worker** — a Deployment running Procrastinate; handles document ingestion **and**
  the periodic `pod_sync` job that keeps the `nodes`/`pods` tables current.

---

## 1. Fastest path — the provisioning skill

Most of this is automated. From the repo:

```
/provisioning-environment
```

It runs (per `.claude/skills/provisioning-environment/SKILL.md`):
1. **Stage 1** — collect inputs (env name, provider = Vultr, region, sizes).
2. **Stage 2** — in parallel: provision **Neon DB** + provision **Vultr VKE cluster**.
3. **Stage 3** — configure **Infisical secrets**, generate **K8s manifests** + **GitHub
   Actions CI/CD**, run **migrations**.

Related granular skills if you do it piecewise:
`/provisioning-db`, `/provisioning-cluster` (Vultr), `/generate-kubernetes-deployment`,
`/generate-github-actions`, `/setup-new-deployment`.

The rest of this document explains **what those steps produce**, the **manual
add-ons** they assume, and the **StatefulSet / pinning** specifics to verify.

---

## 2. Manual/base pieces the app assumes exist

These are cluster-level and usually installed once per cluster:

| Add-on | Why | Note |
|--------|-----|------|
| **ingress-nginx** | All HTTP/WS ingress (api, call, `/pod/N`) | The pod-routing ingress needs `use-regex` + `rewrite-target`; snippet annotations are NOT required |
| **cert-manager** | Let's Encrypt TLS for the ingress hosts | `cluster-issuer: letsencrypt-prod` referenced by ingress/certificate manifests |
| **Grafana Alloy** (monitoring ns) | Ships pod **logs → Loki** and **node metrics → Prometheus** (Grafana Cloud) | `tone_active_calls` app metric is NOT scraped unless you add a `prometheus.scrape` block |
| **GPU operator** | Only if self-hosted STT/TTS on GPU nodes | Optional |
| **Procrastinate schema** | Background-job tables | One-time per DB: `PYTHONPATH=. python -m procrastinate --app=core.services.ingestion_queue.app schema --apply` |
| **imagePullSecret** `dockerhub-auth` | Pull the private image | Create in the namespace before deploy |
| **Infisical secret** `infisical-credentials` | App loads config from Infisical | `token` + `project_id` keys |

DNS: create A records for each host (`<env>.trytone.ai`, `<env>-call.trytone.ai`)
pointing at the ingress-nginx load balancer's external IP.

---

## 3. The call-worker StatefulSet — how it works

### Why a StatefulSet
A Deployment gives pods random names (`…-5b79-w9cx7`) that change on every
restart/redeploy. Pod pinning needs to address a specific pod and keep call
attribution meaningful over time, so the call workers run as a **StatefulSet**,
which gives **stable ordinal names** `…-0 / …-1 / …-2` that survive restarts,
crashes, and redeploys. The container is still recreated on a deploy — only the
**name/identity** is stable.

### Required pieces
- `kind: StatefulSet`, `serviceName: staging-tone-call-headless`,
  `podManagementPolicy: Parallel`, `replicas: N`.
- A **headless Service** (`clusterIP: None`) named as `serviceName` — **mandatory**;
  it gives each pod stable DNS `pod-N.headless.ns.svc.cluster.local`.
- Downward API env on the pod: `POD_NAME`, `NODE_NAME`, `DEPLOYMENT_NAME`(=`app` label).

### On a NEW cluster — NO cutover
`kubectl apply` **cannot** convert a Deployment into a StatefulSet in place. But a
new cluster has **no old Deployment**, so you simply apply the StatefulSet and pods
come up as `…-0/-1/-2` directly. Nothing special.

> Cutover is ONLY needed when migrating an *existing* Deployment-based env:
> apply the StatefulSet, then `kubectl delete deployment staging-tone-call-worker`
> so the old pods free capacity and the StatefulSet pods schedule. New clusters skip
> this entirely.

### Scaling
```
kubectl -n <ns> scale statefulset staging-tone-call-worker --replicas=K
```
Adds/removes the **highest** ordinals; ordinals stay contiguous `0..K-1`; a given
ordinal's pod name never changes. Cold start is ~15–20s per pod (readiness probe
has `initialDelaySeconds: 10`); a fresh node/image pull or cluster autoscale adds
more.

To scale on load instead of by hand — and to have nodes appear when pods no longer
fit — see [`autoscaling-runbook.md`](./autoscaling-runbook.md) (KEDA for pods,
Cluster Autoscaler for nodes).

---

## 4. Pod URL pinning (built on the StatefulSet)

```
Twilio ─POST /twiml─► PodPicker picks freest node+pod ─► wss://<HOST>/pod/<ordinal>/ws
Twilio ─WS /pod/N/ws─► /pod/N ingress (rewrite → /ws) ─► call-pod-N svc ─► worker-N
```

- `PodPicker.get_pod()` reads `nodes`/`pods` (kept current by the `pod_sync`
  Procrastinate job) and returns the freest pod's pinned URL. Freest node = highest
  `vcpu_per_pod`/`ram_per_pod_mb`; freest pod = fewest in-progress calls.
- Per-pod **Services** `call-pod-0..9` select one pod via
  `statefulset.kubernetes.io/pod-name`. The **`/pod/N` ingress** rewrites
  `/pod/N/...` → `/...` (`rewrite-target: /$2`, `use-regex: true`) and routes to that
  Service. Sized to ordinals **0–9** (scale within that with no manifest change).
- `pod_sync` (runs on the worker, every minute) lists all namespace pods + nodes via
  the k8s API, upserts them, and reads **static node capacity** from
  `node.status.allocatable`. Needs the `tone-worker` ServiceAccount RBAC
  (list pods + nodes).

### Infisical keys for pinning
| Key | Value | Rule |
|-----|-------|------|
| `POD_PINNING_ENABLED` | `true` | Off → `/twiml` uses `/ws` |
| `CALL_SERVER_HOST` | `staging-call.trytone.ai` | **Must equal** the call ingress host |
| `CALL_WORKER_PREFIX` | `staging-tone-call-worker` | **Must equal** the StatefulSet name |
| `POD_SYNC_NAMESPACE` | `staging` | Namespace to sync |
| `ENV` | `staging` | Tags rows; separates envs in a shared DB |

---

## 5. Setup order (do it in THIS sequence)

1. **Cluster + add-ons** — provision VKE; install ingress-nginx, cert-manager,
   (Alloy). Create `dockerhub-auth` + `infisical-credentials` secrets in the namespace.
2. **DNS + TLS** — A records → ingress LB IP; confirm cert-manager issues the call cert.
3. **Infisical secrets** — set ALL keys, including §4 pinning keys, **before** pods
   start (read at app startup).
4. **Procrastinate schema** — one-time per DB (command in §2).
5. **Migrations FIRST** — `alembic upgrade head` against the new DB, before the image
   serves traffic (adds `calls.pod_id`, `nodes`, `pods`, node capacity columns).
6. **Apply manifests** — always with `${IMAGE_TAG}` substituted (CI does `sed`; manual
   uses `envsubst '${IMAGE_TAG}'`). Apply api, call (StatefulSet + headless service +
   pod-routing + ingress + pdb + cert), worker (rbac + deployment).
7. **Wait Ready** — `kubectl rollout status statefulset/staging-tone-call-worker`.
8. **Verify** — §7.

---

## 6. Gotchas — the mistakes to NOT repeat

1. **Never `kubectl apply` a raw manifest with `${IMAGE_TAG}`** → `InvalidImageName`.
   Substitute the tag (CI `sed`, or `envsubst '${IMAGE_TAG}'`).
2. **Deployment→StatefulSet can't convert in place** — only matters when migrating an
   existing env; delete the old Deployment after applying the StatefulSet. New cluster: skip.
3. **Headless Service is mandatory** for the StatefulSet's `serviceName`.
4. **Run migrations before the new code serves calls** (additive → safe on old code).
5. **`worker/rbac.yaml` + `serviceAccountName: tone-worker` both required** — else the
   sync gets `403`, tables stay empty, pinning silently falls back to `/ws`.
6. **Apply `pod-routing.yaml` before enabling pinning** — PodPicker returns `/pod/N/ws`
   regardless; without routing it 404s.
7. **`CALL_SERVER_HOST` = ingress host and `CALL_WORKER_PREFIX` = StatefulSet name** —
   a mismatch = silent fallback to `/ws`.
8. **`pod-routing.yaml` covers ordinals 0–9** — beyond 10, regenerate for a bigger range.
9. **No `upstream-hash-by` on the main call ingress** — it pins all `/ws` to one pod.
10. **`tone_active_calls` needs an Alloy `prometheus.scrape` block** to reach Grafana;
    pinning itself is verifiable via **Loki `[/twiml]` logs** without it.
11. **`POD_PINNING_ENABLED`/`CALL_SERVER_HOST` are read at startup** — changing them in
    Infisical requires a pod restart to take effect.

---

## 7. Verification

```
export KUBECONFIG=<new-cluster-kubeconfig>

# StatefulSet pods stable + Ready
kubectl -n <ns> get pods -l app=staging-tone-call-worker      # …-0/-1/-2 Running

# headless + per-pod services + ingress paths
kubectl -n <ns> get svc | grep -E "headless|call-pod"
kubectl -n <ns> get ingress staging-tone-call-pod-ingress -o \
  jsonpath='{range .spec.rules[*].http.paths[*]}{.path}{"\n"}{end}'

# /twiml returns a pinned URL
curl -s -X POST "https://<CALL_SERVER_HOST>/twiml" -d "From=%2B1555&To=%2B1318"
#   -> <Stream url="wss://<CALL_SERVER_HOST>/pod/0/ws">

# /pod/N routes to the right pod
curl -s "https://<CALL_SERVER_HOST>/pod/0/status"             # served_by pod = …-0

# sync populated nodes with real capacity
kubectl -n <ns> exec staging-tone-call-worker-0 -- python -c \
 "from core.database.session import SessionLocal; from core.models.node import Node; \
  [print(n.name, n.total_vcpu, n.total_ram_mb, n.vcpu_per_pod) for n in SessionLocal().query(Node).all()]"

# /twiml logging (also in Grafana Loki: {app="staging-tone-call-worker"} |= "[/twiml]")
kubectl -n <ns> logs -l app=staging-tone-call-worker -f | grep '\[/twiml\]'
```

**A call is fully pinned when:** `/twiml` returns `/pod/N/ws`, the ingress log shows
`GET /pod/N/ws … 101 → [<ns>-…-call-pod-N-80]`, and the call's `served_by` in the DB
matches `worker-N`.

---

## 8. Reference

- Pod pinning + StatefulSet detail: sections 3–4 of this document
- Provisioning skills: `.claude/skills/provisioning-environment`, `provisioning-cluster`,
  `provisioning-db`, `generate-kubernetes-deployment`, `generate-github-actions`,
  `setup-new-deployment`
- Manifests: `build/kubernetes/<env>/{api,call,worker}/`
