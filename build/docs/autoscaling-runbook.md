# Autoscaling runbook — KEDA + node autoscaler on a new cluster

Setting up autoscaling on a Kubernetes cluster from scratch. Follow it top to bottom; every
step has a "Done when" you can check before moving on. Most of the gotchas listed here are
ones we actually hit — they cost hours, and they all fail *quietly*.

Written against EKS. The workload half (KEDA, ScaledObjects) is plain Kubernetes and moves
to GKE/AKS/DigitalOcean unchanged. Only the node half is cloud-specific.

**Read first:** [`NEW_CLUSTER_SETUP.md`](./NEW_CLUSTER_SETUP.md) for standing up the cluster
and its workloads, and [`PROCRASTINATE_SETUP.md`](./PROCRASTINATE_SETUP.md) for the job queue.
This runbook assumes both are done — it only adds autoscaling on top, and the scaler queries
below read the `procrastinate_jobs` table that guide creates.

---

## 1. What you are building

Two independent layers. Nothing orchestrates the handoff between them — it is a closed loop
through the scheduler.

```
work arrives in the queue
        │
        ▼
KEDA reads the queue  ──▶  sets Deployment replicas   (pod layer)
        │
        ▼
new pods don't fit    ──▶  they sit Pending
        │
        ▼
node autoscaler sees Unschedulable  ──▶  adds a node  (node layer)
        │
        ▼
pods schedule, work runs
```

On the way down it reverses: queue empties → KEDA scales pods to zero → nodes go idle →
autoscaler reclaims them.

**KEDA cannot create nodes.** Its operator has no node RBAC and no AWS identity — it only
writes a replica count to a workload's `scale` subresource. If you install KEDA alone, a
burst produces pods that pend forever. You need both halves.

---

## 2. Before you start

| Need | Check |
|---|---|
| Cluster reachable | `kubectl get nodes` |
| Your Kubernetes minor version | `kubectl version -o json \| jq -r .serverVersion.gitVersion` |
| Helm | `helm version` |
| `eksctl` (EKS only) | `eksctl version` |
| IAM OIDC provider (EKS only) | `aws eks describe-cluster --name <CLUSTER> --query cluster.identity.oidc.issuer` |
| Cloud CPU quota | see §7 — this caps everything |

**Write down the Kubernetes minor version now.** You need it twice, and getting it wrong is
the single most confusing failure in this runbook.

---

## 3. Part 1 — KEDA (pod layer)

### Step 1.1 — Install the operator

```sh
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda --namespace keda --create-namespace
kubectl get pods -n keda
```

Check the install output for a version warning. KEDA supports a moving window of Kubernetes
versions; if it says your cluster is unsupported, pin an older chart:

```sh
helm search repo kedacore/keda --versions | head
helm upgrade keda kedacore/keda -n keda --version <OLDER>
```

**Done when:** three pods (`operator`, `metrics-apiserver`, `admission-webhooks`) are
`Running 1/1`, and `kubectl get crd | grep keda` lists `scaledobjects.keda.sh`.

One restart on the operator during startup is normal — that is leader election.

### Step 1.2 — Give KEDA database credentials

KEDA talks to Postgres itself. It **cannot read your secret manager** — not Infisical, not
anything except Kubernetes Secrets and a few native providers. Copy the value in once.

```sh
kubectl create secret generic keda-postgres -n <WORKLOAD_NS> \
  --from-literal=connectionString='postgresql://USER:PASS@HOST:5432/DB?sslmode=require' \
  --dry-run=client -o yaml | kubectl apply -f -
```

`--dry-run=client -o yaml | kubectl apply -f -` makes it create-or-update, so the same
command works for rotation.

Two things that silently break this:

- **Driver prefix.** Application URLs are often SQLAlchemy-style (`postgresql+psycopg://`).
  KEDA uses libpq and does not understand `+driver`. Strip it to plain `postgresql://`.
- **Wrong database.** If your admin tooling has its *own* `procrastinate_jobs` table, pointing
  KEDA at it returns `0` forever and the workload never scales. Verify before you trust it:

```sh
psql "$CONN" -c "SELECT queue_name, count(*) FROM procrastinate_jobs GROUP BY 1;"
```

You should see your application's queue names. Use a **read-only role** — the scaler only
ever counts rows.

### Step 1.3 — TriggerAuthentication

```yaml
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: keda-postgres-auth
  namespace: <WORKLOAD_NS>
spec:
  secretTargetRef:
    - parameter: connection
      name: keda-postgres
      key: connectionString
```

**Done when:** `kubectl get triggerauthentication -n <WORKLOAD_NS>` lists it.

### Step 1.4 — Write the ScaledObject

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: <NAME>
  namespace: <WORKLOAD_NS>
spec:
  scaleTargetRef:
    kind: Deployment
    name: <DEPLOYMENT>
  pollingInterval: 15
  cooldownPeriod: 300
  minReplicaCount: 0
  maxReplicaCount: <SEE §7>
  advanced:
    restoreToOriginalReplicaCount: true
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300
  triggers:
    - type: postgresql
      authenticationRef:
        name: keda-postgres-auth
      metadata:
        targetQueryValue: "1"           # units of work one pod handles
        activationTargetQueryValue: "0" # any work at all wakes the first pod
        query: >-
          SELECT count(*) FROM procrastinate_jobs
          WHERE queue_name = '<QUEUE>'
            AND (
                  status = 'doing'
               OR (status = 'todo' AND (scheduled_at IS NULL OR scheduled_at <= now()))
            )
```

KEDA computes `replicas = ceil(queryValue / targetQueryValue)`. Return **raw demand** from
SQL and let `targetQueryValue` do the division — don't divide in the query.

#### The query has three rules. All three are load-bearing.

**1. Count `doing`, not just `todo`.** If you count only waiting work, the metric drops to
zero the instant the last job is claimed, and KEDA deletes the pod *mid-job*. For a queue
that holds long-running work this is the classic footgun. `cooldownPeriod` softens it but
cannot save a job longer than the cooldown.

**2. Filter on `scheduled_at`.** Procrastinate stores future work as `status='todo'` with a
future `scheduled_at`. Without the filter, a job scheduled for next week spins up a pod now
and holds it. Note `scheduled_at IS NULL` must also pass — periodic jobs have no schedule
and would otherwise be invisible.

**3. Count what occupies capacity.** The rule generalises: the metric must include work
*currently running* plus work *about to need capacity*. For workloads where the queue is a
proxy rather than the real thing (e.g. live phone calls served over WebSockets), count the
real resource instead — live rows plus imminent ones — not the queue depth.

#### Latency-sensitive workloads

You cannot provision inside a request that must be answered in seconds. A pod takes ~10–60s;
a node takes minutes. Scale on **lookahead**, not backlog — count work due in the next N
minutes so capacity is warm before it is needed. KEDA also supports several triggers on one
ScaledObject and takes the **maximum**, so a `cron` trigger can hold a floor during known
busy hours while the Postgres trigger handles bursts above it.

#### Workloads that must not scale to zero

A deployment running **periodic/cron tasks must keep `minReplicaCount: 1`**. Periodic tasks
only fire while a worker is alive, and skipped ticks are never backfilled. Scaling such a
worker to zero silently stops the schedule — and if one of those tasks feeds a table other
systems read, they go stale with no error anywhere.

### Step 1.5 — Verify

```sh
kubectl get scaledobject -n <WORKLOAD_NS>
kubectl get hpa -n <WORKLOAD_NS>          # KEDA creates keda-hpa-<name>
```

**Done when:** `READY=True`. `ACTIVE=False` with an empty queue is the healthy idle state,
and the deployment sitting at `0/0` is success, not failure.

If `READY=False`, read the reason — it is specific:

```sh
kubectl describe scaledobject <NAME> -n <WORKLOAD_NS>
kubectl logs -n keda -l app=keda-operator --tail=50 | grep -i error
```

`no host given` means the secret is missing or unparseable — KEDA resolved the auth ref to an
empty string. A real connection problem reads as a dial or auth error instead.

---

## 4. Part 2 — Node autoscaler (node layer)

Two options. **Cluster Autoscaler** resizes node groups you already have and is the
cloud-agnostic standard. **Karpenter** replaces node groups and picks instance types itself —
faster and smarter on AWS, but AWS-only and a bigger change. This runbook uses Cluster
Autoscaler.

### Step 2.1 — Set the node group min and max

This is the step people skip, and it makes everything downstream look broken.

```sh
aws eks update-nodegroup-config \
  --cluster-name <CLUSTER> --nodegroup-name <NODEGROUP> \
  --scaling-config minSize=<MIN>,maxSize=<MAX>,desiredSize=<CURRENT> \
  --region <REGION>
```

- **`maxSize`** — the hard ceiling. **Cluster Autoscaler can never exceed it.** If `maxSize`
  equals your current node count, CAS installs cleanly, logs happily, and never scales. Size
  it from your cloud quota (§7).
- **`minSize`** — the floor, and your cheapest warm-capacity trick. CAS never scales below it,
  so `minSize = steady state + 1` keeps one node of slack for bursts. Worth it for
  latency-sensitive work, where a burst would otherwise wait minutes for a node to boot.
  For batch workloads, `minSize: 0` lets the group scale to zero.

**Done when:** `aws eks describe-nodegroup` shows the new `scalingConfig` and status `ACTIVE`.

### Step 2.2 — Tag the Auto Scaling Group

CAS discovers node groups by tag:

```
k8s.io/cluster-autoscaler/enabled          = true
k8s.io/cluster-autoscaler/<CLUSTER_NAME>   = owned
```

Managed node groups usually get these automatically. Verify rather than assume:

```sh
aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?contains(AutoScalingGroupName,'<NODEGROUP>')].Tags[?contains(Key,'cluster-autoscaler')]"
```

### Step 2.3 — IAM role (IRSA)

CAS needs permission to read and resize ASGs. Policy is in
[`cluster-autoscaler-policy.json`](./cluster-autoscaler-policy.json) — the resize actions are
scoped by tag so it can only touch groups belonging to this cluster.

```sh
aws iam create-policy \
  --policy-name <CLUSTER>-cluster-autoscaler \
  --policy-document file://build/docs/cluster-autoscaler-policy.json

eksctl create iamserviceaccount \
  --cluster <CLUSTER> --region <REGION> \
  --namespace kube-system --name cluster-autoscaler \
  --attach-policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/<CLUSTER>-cluster-autoscaler \
  --approve
```

**Done when:** the service account carries a role annotation:

```sh
kubectl get sa cluster-autoscaler -n kube-system \
  -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
```

### Step 2.4 — Install Cluster Autoscaler, pinned to your Kubernetes version

**Read this step twice.** Cluster Autoscaler is versioned to match Kubernetes minor
versions: `v1.32.x` for Kubernetes 1.32, `v1.33.x` for 1.33. The Helm chart defaults to the
newest build, which will be **ahead of your cluster**.

A too-new CAS fails in the worst way: the pod is `Running 1/1`, logs look busy, and it sits
at `autoscalerStatus: Initializing` with **zero nodes registered**, forever. It cannot watch
API types your cluster does not have, so its informers never sync. Nothing says "wrong
version".

```sh
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=<CLUSTER> \
  --set awsRegion=<REGION> \
  --set rbac.serviceAccount.create=false \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set image.tag=v<K8S_MINOR>.1 \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.expander=least-waste \
  --set extraArgs.skip-nodes-with-system-pods=false
```

Flags worth knowing: `expander=least-waste` picks the node group that leaves the least idle
capacity; `balance-similar-node-groups` spreads across AZs; `skip-nodes-with-system-pods=false`
lets CAS reclaim nodes running only DaemonSet/system pods, which otherwise stay up forever.

### Step 2.5 — Verify

```sh
kubectl -n kube-system get configmap cluster-autoscaler-status -o jsonpath='{.data.status}'
```

**Done when** you see `autoscalerStatus: Running`, your node group listed, and node counts
matching reality:

```
autoscalerStatus: Running
nodeGroups:
- name: eks-<nodegroup>-...
  health:
    status: Healthy
    nodeCounts: { registered: { total: 2, ready: 2 } }
  minSize: 1
  maxSize: 4
```

Still `Initializing` after a couple of minutes → go back to Step 2.4, it is the image tag.

Check for permission problems, ignoring known-harmless noise:

```sh
kubectl -n kube-system logs -l app.kubernetes.io/name=aws-cluster-autoscaler --tail=100 \
  | grep -viE "DeviceClass|ResourceSlice|ResourceClaim" | grep -i error
```

`AccessDenied` means IRSA did not attach — CAS keeps running and silently never scales.

Those `DeviceClass` / `ResourceSlice` / `ResourceClaim` errors are Dynamic Resource
Allocation APIs that don't exist on older clusters. Cosmetic, but they will drown your log
grep, so filter them out.

---

## 5. Part 3 — Test the whole loop

Test the layers separately, then together. **Design the load deliberately** — an
underpowered test looks exactly like a broken setup.

### Test A — pods scale

Enqueue N jobs. Expect `ceil(N / targetQueryValue)` replicas within one polling interval.
Drain, expect a return to zero after the cooldown.

### Test B — scale from zero

With the deployment at 0, enqueue one job. Exactly one pod should start.

### Test C — nodes scale (the real test)

Two conditions must both hold, or nothing pends and CAS never fires:

1. **`maxReplicaCount` must exceed what current nodes can hold.** If the cap is 2 and two
   nodes fit two pods, no pod ever pends. You will conclude CAS is broken; it is idle
   because you never asked it for anything.
2. **Jobs must run longer than `pollingInterval`.** We first tested with jobs taking ~14s
   against a 15s poll — the queue drained before KEDA saw it. Use jobs of a minute or more,
   and enough of them to keep the queue deep.

```sh
kubectl get pods -n <WORKLOAD_NS> -w
kubectl get nodes -w
kubectl -n kube-system logs -l app.kubernetes.io/name=aws-cluster-autoscaler -f \
  | grep -iE "TriggeredScaleUp|Scale-up|max node group"
```

**Pass when** the logs name the pod that caused it:

```
TriggeredScaleUp  pod triggered scale-up: [{eks-<nodegroup> 2->4 (max: 4)}]
Scale-up: setting group eks-<nodegroup> size to 4 instead of 2 (max: 4)
```

New nodes reach `Ready` in roughly 90s–5min. Then pods schedule and drain.

### Test D — scale down

Let it idle. KEDA returns pods to zero; CAS reclaims empty nodes after ~10 minutes. The
delay is deliberate, not a bug.

### Test E — drain safety (only for long-running work)

While a job is running, scale down or delete the pod. It must finish or requeue cleanly and
never be duplicated. See §6 on graceful shutdown.

---

## 6. Graceful shutdown

The Deployment controller — not KEDA — chooses which pod to delete on scale-down, and it has
no idea which pods are busy. StatefulSets remove the **highest ordinal** first. Three things
protect in-flight work:

- **`terminationGracePeriodSeconds`** ≥ your longest unit of work.
- **A `preStop` hook** that stops accepting new work and waits for current work to finish.
- **A PodDisruptionBudget** so voluntary disruptions cannot take out everything at once.

Three traps we hit, all of which pass code review:

- **Grace period shorter than the drain.** The grace period covers `preStop` *plus*
  SIGTERM→SIGKILL. A `preStop` that sleeps 280s under a 20s grace period is killed at 20s,
  silently truncating the drain.
- **A `preStop` that cannot run.** Ours called `curl` — which was not installed in the image
  — against an endpoint that did not exist, with `|| true` swallowing both failures. It had
  never drained anything. **Exec into a real pod and run your preStop command by hand.**
- **A fixed `sleep` blows up deploy time.** A blind `sleep 280` waits the full duration even
  with zero work in flight, so every rollout costs ~5 minutes per pod and CI
  `rollout status --timeout` starts failing. Poll a real readiness/drain endpoint and exit
  early instead; if you keep the sleep, raise the CI timeout above the grace period.

---

## 7. Sizing: work backwards from quota

Autoscaling limits form a chain. The smallest link decides everything.

```
maxReplicaCount   →   node capacity   →   node group maxSize   →   cloud vCPU quota
```

Setting `maxReplicaCount` above what nodes can ever provide does not buy throughput — it
manufactures permanently `Pending` pods.

**Work it out before you pick numbers:**

1. **Quota.** On AWS, CPU instances are governed by *Running On-Demand Standard instances*
   (`L-1216C47A`) measured in **vCPUs, not instances**. GPU families have separate quotas
   (`L-DB2E81BA` for G/VT, `L-417A185B` for P). Check them — defaults are low, and we found
   our CPU quota was **three times smaller** than our GPU quota.

   ```sh
   aws service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A
   ```

2. **Max nodes** = quota vCPUs ÷ vCPUs per instance. Set `maxSize` to that.

3. **Pods per node** = allocatable ÷ pod request. Usually **memory-bound, not CPU-bound**.
   Subtract everything already running — DaemonSets and system pods take a real slice.

4. **`maxReplicaCount`** = pods per node × max nodes − room for other workloads.

**All ScaledObjects share one pool.** Size them together against one budget. Two workloads
each independently sized to "reasonable" can add up to more than the cluster can ever hold,
and they will starve each other.

**The cheapest lever is the pod's memory request.** It decides pods per node directly. If a
pod requests 3 GiB but uses 1 GiB under load, right-sizing the request triples throughput
for free — better than adding nodes and better than raising quota. Measure actual usage
before you buy capacity.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| ScaledObject `READY=False`, `no host given` | Secret missing/unparseable | Create `keda-postgres`; strip `+psycopg` from the URL |
| Scaler connects but always returns 0 | Pointed at the wrong database | Verify queue names with `psql` |
| Pods scale, nodes never appear | No node autoscaler installed | Part 2 |
| CAS `Running` but `Initializing`, 0 nodes | Image newer than the cluster | Pin `image.tag` to your K8s minor |
| CAS healthy, never scales | `maxSize` already reached | Raise `maxSize` (check quota first) |
| Nothing ever pends | `maxReplicaCount` ≤ what nodes hold | Raise the cap, or accept there's nothing to test |
| CAS logs `AccessDenied` | IRSA not attached | Recheck the SA annotation |
| Pods pend forever, `max node group size reached` | Cloud quota | Request an increase |
| Pod killed mid-job | Query counts `todo` only | Add `status = 'doing'` |
| Scales up days early | No `scheduled_at` filter | Add the due-time predicate |
| Periodic tasks stop running | Worker scaled to zero | `minReplicaCount: 1` for periodic workers |
| Deployment applies `replicas: N`, KEDA overrides | Expected | KEDA owns replicas; brief churn is normal |
| Rollout times out in CI | Grace period > CI timeout | Raise the timeout or shorten the drain |

Order to debug in: **ScaledObject status → KEDA operator logs → HPA → pod events → CAS status
configmap → CAS logs.** Each layer only sees the one below it.

---

## 9. Quick reference

```sh
# pod layer
kubectl get scaledobject -n <NS>
kubectl get hpa -n <NS>
kubectl describe scaledobject <NAME> -n <NS>
kubectl logs -n keda -l app=keda-operator --tail=50

# node layer
kubectl -n kube-system get configmap cluster-autoscaler-status -o jsonpath='{.data.status}'
kubectl -n kube-system logs -l app.kubernetes.io/name=aws-cluster-autoscaler --tail=100 \
  | grep -viE "DeviceClass|ResourceSlice|ResourceClaim"
kubectl get events -n <NS> --sort-by=.lastTimestamp | grep -i TriggeredScaleUp

# temporarily change a ceiling (reverted by the next deploy)
kubectl patch scaledobject <NAME> -n <NS> --type merge -p '{"spec":{"maxReplicaCount":5}}'

# pause autoscaling without deleting the ScaledObject
kubectl annotate scaledobject <NAME> -n <NS> autoscaling.keda.sh/paused-replicas="1"
kubectl annotate scaledobject <NAME> -n <NS> autoscaling.keda.sh/paused-replicas-
```
