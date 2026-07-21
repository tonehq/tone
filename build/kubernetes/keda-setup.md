# KEDA autoscaling

CI applies `keda/trigger-auth.yaml` and `keda/scaledobjects.yaml`, but both need the KEDA
operator and a database secret that live in the cluster. Do these two steps once per
cluster, before the first deploy that includes them — a `ScaledObject` applied without the
operator installed fails with `no matches for kind "ScaledObject"` and takes the whole
deploy down with it.

## 1. Install the operator

```sh
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
kubectl get pods -n keda
```

## 2. Create the connection secret

The scaler talks to Postgres itself, so it cannot read Infisical. Give it its own secret in
the `staging` namespace, keyed `connectionString`. Use a read-only role — the queries only
ever count rows.

```sh
kubectl create secret generic keda-postgres -n staging \
  --from-literal=connectionString='postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require'
```

Rotate it the same way, with `--dry-run=client -o yaml | kubectl apply -f -`.

## What scales, and what deliberately does not

| Workload | min | max | signal |
|---|---|---|---|
| `staging-tone-worker` (doc-worker) | 0 | 5 | `ingestion` jobs that are `doing`, or `todo` and due |
| `staging-tone-outbound-call-worker` | 0 | 10 | live outbound calls + dialing + calls due within 3 min |
| `staging-tone-orchestrator` | — | — | **not scaled** |

The orchestrator has no `ScaledObject` on purpose. It owns the `@app.periodic` tasks
(`pod_sync`, `reconcile_outbound_calls`), and a periodic task only fires while a worker on
its queue is running — skipped ticks are never backfilled. Scaling it to zero stops
`pod_sync`, the `pods` table goes stale past `PodPicker`'s 180s `last_seen_at` cutoff, and
every call loses pod pinning. It stays at one replica.

Both queries count work that is *already running*, not just work that is waiting. Counting
only the backlog lets KEDA scale a pod away the moment its last job is claimed, killing it
mid-work.

## The outbound ScaledObject is paused

It carries `autoscaling.keda.sh/paused-replicas: "1"`, so it holds at one replica and does
not autoscale yet. Outbound calls currently share the inbound voice pods — `PodPicker`
selects on a single `CALL_WORKER_PREFIX` (`staging-tone-call-worker`), so pods in the
outbound StatefulSet receive no traffic and scaling them would only cost money.

Once outbound routing is split onto its own prefix, remove the annotation to switch it on:

```sh
kubectl annotate scaledobject staging-tone-outbound-call-worker -n staging \
  autoscaling.keda.sh/paused-replicas-
```

## Checking it

```sh
kubectl get scaledobject -n staging
kubectl get hpa -n staging                      # KEDA creates keda-hpa-<name>
kubectl describe scaledobject staging-tone-doc-worker -n staging
kubectl logs -n keda -l app=keda-operator --tail=50
```

`READY=True ACTIVE=False` means the scaler is connected and the queue is empty — that is
the healthy idle state, and the deployment sits at zero replicas.
