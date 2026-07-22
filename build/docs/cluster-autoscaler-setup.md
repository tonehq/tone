# Cluster Autoscaler on tone-staging

KEDA scales pods; it has no permission to touch nodes and no CRD that describes one. When
it asks for more pods than the cluster can hold they sit `Pending` forever. Cluster
Autoscaler closes that loop: it watches for unschedulable pods and resizes the node group's
Auto Scaling Group, then reclaims nodes once they go empty.

Everything below runs against the node group that already exists (`cpu-app`). Nothing here
touches the workload manifests — that side stays cloud-agnostic.

## State before you start

| item | value |
|---|---|
| cluster | `tone-staging`, us-east-1, account 181486424543 |
| node group | `cpu-app` — c6a.xlarge, min 1, **max 2**, desired 2 |
| ASG discovery tags | already present |
| OIDC provider | already associated |
| Standard vCPU quota (`L-1216C47A`) | **16** → 4 × c6a.xlarge maximum |

## 1. Raise the node group ceiling

Cluster Autoscaler can never exceed a node group's `maxSize`. At `maxSize: 2` with 2 nodes
running it has nowhere to go, so it would install cleanly and silently do nothing.

```sh
aws eks update-nodegroup-config \
  --cluster-name tone-staging \
  --nodegroup-name cpu-app \
  --scaling-config minSize=1,maxSize=4,desiredSize=2 \
  --region us-east-1
```

`maxSize=4` is the quota ceiling: 4 × 4 vCPU = 16. Going higher needs a quota increase on
`L-1216C47A` first, or scale-ups will fail with `VcpuLimitExceeded`.

## 2. Create the IAM role (IRSA)

```sh
aws iam create-policy \
  --policy-name tone-staging-cluster-autoscaler \
  --policy-document file://build/kubernetes/cluster-autoscaler-policy.json

eksctl create iamserviceaccount \
  --cluster tone-staging \
  --region us-east-1 \
  --namespace kube-system \
  --name cluster-autoscaler \
  --attach-policy-arn arn:aws:iam::181486424543:policy/tone-staging-cluster-autoscaler \
  --approve
```

## 3. Install Cluster Autoscaler

```sh
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=tone-staging \
  --set awsRegion=us-east-1 \
  --set rbac.serviceAccount.create=false \
  --set rbac.serviceAccount.name=cluster-autoscaler \
  --set extraArgs.balance-similar-node-groups=true \
  --set extraArgs.expander=least-waste \
  --set extraArgs.skip-nodes-with-system-pods=false
```

Pin the chart's `image.tag` to the Cluster Autoscaler release matching Kubernetes 1.32.

## 4. Verify

```sh
kubectl -n kube-system get pods -l app.kubernetes.io/name=aws-cluster-autoscaler
kubectl -n kube-system logs -l app.kubernetes.io/name=aws-cluster-autoscaler --tail=50
```

Healthy logs mention discovering the `cpu-app` ASG. `AccessDenied` means the IRSA role did
not attach — that is the usual failure, and it fails silently apart from the log line.

## 5. Watch the loop end to end

```sh
kubectl get pods -n staging -w
kubectl get nodes -w
kubectl get events -n staging --sort-by=.lastTimestamp | grep -i triggeredScaleUp
```

Upload enough documents that KEDA scales the doc-worker past what two nodes hold. Pods go
`Pending`, Cluster Autoscaler adds a third node within ~2–5 minutes, the pods schedule.
When the queue drains, KEDA returns the deployment to zero and the node is reclaimed after
its scale-down delay (~10 minutes idle by default).

## Interaction with what we already run

`ensure_node_capacity` in tone asks tone-admin for nodes on the same signal Cluster
Autoscaler uses. Once Cluster Autoscaler is live the two would both react to the same
`Pending` pods and could double-provision. Cluster Autoscaler is the better fit for routine
capacity because it also scales *down*, which `provision_nodes` never does.

So once this is verified, either drop `CAPACITY_CLUSTER_NAME` from Infisical (the periodic
no-ops without `BENCHMARKING_DB_URL`) or remove the periodic. Keep `provision_nodes` in
tone-admin for deliberate provisioning — new GPU pools, benchmarking runs — where its quota
checks and audit trail are the point.

## Gotchas

- Never hand-edit `desiredSize` while Cluster Autoscaler runs; it will fight you.
- Scale-down waits ~10 minutes after a node empties. Not a bug.
- A pod with no resource `requests` makes bin-packing guesswork — every workload here sets
  them, keep it that way.
- Scale-down skips nodes running pods it cannot evict. `staging-tone-outbound-call-worker`
  has `maxUnavailable: 0`, so its node will not be reclaimed while it runs.
