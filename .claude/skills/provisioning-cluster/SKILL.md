---
name: provisioning_cluster
description: "Provision a Vultr Kubernetes Engine (VKE) cluster with node pools and add-ons. Interactively collects all configuration from the user via AskUserQuestion, then executes the provisioning commands via Bash tool. Use when setting up a new Kubernetes cluster or when the user asks to create/provision a cluster."
---

# Provisioning Cluster

Interactively guide the user through provisioning a Vultr Kubernetes Engine (VKE) cluster. Use `AskUserQuestion` at every step to collect ALL required inputs. After user confirms the configuration, **execute all commands via the `Bash` tool** — do NOT just print them.

## Prerequisites

Before starting, verify prerequisites by running these checks via `Bash`:

```bash
# Check vultr-cli
vultr-cli version

# Check kubectl
kubectl version --client

# Check helm
helm version --short
```

If any tool is missing, tell the user what to install and stop:
- vultr-cli: `brew install vultr/vultr-cli/vultr-cli`
- kubectl: `brew install kubectl`
- helm: `brew install helm`

Also verify Vultr CLI authentication:

```bash
vultr-cli account
```

If authentication fails, ask the user for their Vultr API key via `AskUserQuestion` and run:

```bash
vultr-cli config set api-key {API_KEY}
```

---

## Step 1: Collect Cluster Details

Use `AskUserQuestion` to ask the following. Ask all 3 in a single AskUserQuestion call:

**Question 1 — Environment Name:**
- Question: "What is the environment name for this cluster?"
- Options: `staging`, `production`, `dev`
- Allow custom input (user may type e.g. `staging-vultr`)

**Question 2 — Cluster Label:**
- Question: "What label/name should this cluster have?"
- Options: `tone-staging`, `tone-production`, `tone-dev`
- Allow custom input

**Question 3 — Region:**
- Question: "Which Vultr region should the cluster be provisioned in?"
- Options with descriptions:
  - `blr` — Bangalore, India
  - `del` — Delhi, India
  - `maa` — Chennai (Madras), India
  - `ewr` — New Jersey, US
- Allow custom input (user can type any valid Vultr region ID)

Store all answers as: `ENV_NAME`, `CLUSTER_LABEL`, `REGION`

---

## Step 2: Collect Number of Node Pools

Use `AskUserQuestion`:

**Question — How many node pools do you need?**
- Options with descriptions:
  - `2` — Separate pools for API and Call Worker workloads
  - `3 (Recommended)` — System pool (ingress, cert-manager) + API pool + Call Worker pool
  - `4` — System + API + Call Worker + a custom pool

Store answer as: `NODE_POOL_COUNT`

---

## Step 3: Display Node Options & Collect Pool Configuration

For **each** node pool (from 1 to `NODE_POOL_COUNT`), do the following:

### 3a. Ask the pool purpose

Use `AskUserQuestion`:

**Question — "What is the purpose of node pool {N}?"**
- Options:
  - `System` — Ingress controller, cert-manager, monitoring
  - `API` — Tone API deployments
  - `Call Worker` — Tone Call Worker deployments
  - Allow custom input (e.g. `Redis`, `Monitoring`)

Store as: `POOL_{N}_LABEL`

### 3b. Display available node types

After collecting the purpose, display the Vultr plan options in a table:

```
Available Vultr node types for: {POOL_{N}_LABEL} pool

Regular Performance Plans:
┌─────────────────┬───────┬────────┬─────────────┬───────────┬────────────┐
│ Plan ID         │ vCPUs │ RAM    │ Storage     │ Bandwidth │ Price/mo   │
├─────────────────┼───────┼────────┼─────────────┼───────────┼────────────┤
│ vc2-1c-2gb      │ 1     │ 2 GB   │ 55 GB SSD   │ 2 TB      │ $10        │
│ vc2-2c-4gb      │ 2     │ 4 GB   │ 80 GB SSD   │ 3 TB      │ $20        │
│ vc2-4c-8gb      │ 4     │ 8 GB   │ 160 GB SSD  │ 4 TB      │ $40        │
│ vc2-6c-16gb     │ 6     │ 16 GB  │ 320 GB SSD  │ 5 TB      │ $80        │
│ vc2-8c-32gb     │ 8     │ 32 GB  │ 640 GB SSD  │ 6 TB      │ $160       │
└─────────────────┴───────┴────────┴─────────────┴───────────┴────────────┘

High Performance Plans (AMD):
┌─────────────────────┬───────┬────────┬──────────────┬────────────┐
│ Plan ID             │ vCPUs │ RAM    │ Storage      │ Price/mo   │
├─────────────────────┼───────┼────────┼──────────────┼────────────┤
│ vhp-2c-4gb-amd      │ 2     │ 4 GB   │ 60 GB NVMe   │ $24        │
│ vhp-4c-8gb-amd      │ 4     │ 8 GB   │ 120 GB NVMe  │ $48        │
│ vhp-8c-16gb-amd     │ 8     │ 16 GB  │ 240 GB NVMe  │ $96        │
└─────────────────────┴───────┴────────┴──────────────┴────────────┘

Optimized Cloud Compute:
┌─────────────────────────┬───────┬────────┬─────────────┬──────────────────┬────────────┐
│ Plan ID                 │ vCPUs │ RAM    │ Storage     │ Type             │ Price/mo   │
├─────────────────────────┼───────┼────────┼─────────────┼──────────────────┼────────────┤
│ voc-g-2c-8gb-100s       │ 2     │ 8 GB   │ 100 GB SSD  │ General Purpose  │ $60        │
│ voc-c-2c-4gb-75s        │ 2     │ 4 GB   │ 75 GB SSD   │ CPU Optimized    │ $40        │
│ voc-m-1c-8gb-75s        │ 1     │ 8 GB   │ 75 GB SSD   │ Memory Optimized │ $40        │
└─────────────────────────┴───────┴────────┴─────────────┴──────────────────┴────────────┘
```

### 3c. Ask node type selection

Use `AskUserQuestion`:

**Question — "Which node type (plan) do you want for the {POOL_{N}_LABEL} pool?"**

Provide contextual recommendations as options based on the pool purpose:
- If **System**: `vc2-2c-4gb (Recommended)`, `vc2-1c-2gb`, `vhp-2c-4gb-amd`
- If **API**: `vc2-4c-8gb (Recommended)`, `vc2-2c-4gb`, `vhp-4c-8gb-amd`
- If **Call Worker**: `vc2-6c-16gb (Recommended)`, `vc2-4c-8gb`, `vhp-8c-16gb-amd`
- If **Custom**: `vc2-2c-4gb`, `vc2-4c-8gb`, `vc2-6c-16gb`
- Allow custom input (user can type any valid plan ID)

Store as: `POOL_{N}_PLAN`

### 3d. Ask node count

Use `AskUserQuestion`:

**Question — "How many nodes for the {POOL_{N}_LABEL} pool ({POOL_{N}_PLAN})?"**
- Options: `1`, `2 (Recommended)`, `3`, `4`
- Allow custom input

Store as: `POOL_{N}_NODE_COUNT`

### 3e. Ask auto-scaling

Use `AskUserQuestion`:

**Question — "Enable auto-scaling for the {POOL_{N}_LABEL} pool?"**
- Options:
  - `Yes (Recommended)` — Automatically scale nodes based on demand
  - `No` — Fixed node count, no auto-scaling

Store as: `POOL_{N}_AUTOSCALE`

### 3f. If auto-scaling is Yes, ask min/max

Use `AskUserQuestion` (ask both in a single call):

**Question 1 — "Minimum nodes for {POOL_{N}_LABEL} auto-scaler?"**
- Options: `1`, `2`, `3`
- Allow custom input

**Question 2 — "Maximum nodes for {POOL_{N}_LABEL} auto-scaler?"**
- Options: `3`, `4`, `5`, `6`
- Allow custom input

Store as: `POOL_{N}_MIN_NODES`, `POOL_{N}_MAX_NODES`

**Repeat Steps 3a–3f for each node pool.**

---

## Step 4: Confirm Configuration

Before executing, display a summary table and ask for confirmation.

Print:

```
Cluster Configuration Summary
==============================
Cluster Label:  {CLUSTER_LABEL}
Region:         {REGION}
Environment:    {ENV_NAME}

Node Pools:
┌─────┬────────────────┬──────────────────┬───────┬──────────────────────────┬────────────┐
│  #  │ Label          │ Plan             │ Nodes │ Auto-scale               │ Cost/mo    │
├─────┼────────────────┼──────────────────┼───────┼──────────────────────────┼────────────┤
│  1  │ {POOL_1_LABEL} │ {POOL_1_PLAN}    │ {N}   │ {Yes: min-max / No}      │ ${cost}    │
│  2  │ {POOL_2_LABEL} │ {POOL_2_PLAN}    │ {N}   │ {Yes: min-max / No}      │ ${cost}    │
│ ... │ ...            │ ...              │ ...   │ ...                      │ ...        │
└─────┴────────────────┴──────────────────┴───────┴──────────────────────────┴────────────┘

Estimated base cost: ~${total}/mo
```

Use `AskUserQuestion`:

**Question — "Does this configuration look correct? This will CREATE real resources and incur costs."**
- Options:
  - `Yes, provision now` — Execute all provisioning commands
  - `No, start over` — Re-collect all inputs from Step 1

If "No", go back to Step 1 and re-ask everything.

---

## Step 5: Execute Cluster Provisioning

**IMPORTANT: Execute each command via the `Bash` tool. Show the output to the user after each step.**

### 5a. Create the VKE cluster

Run via `Bash`:

```bash
vultr-cli kubernetes create --label "{CLUSTER_LABEL}" --region "{REGION}"
```

**Parse the CLUSTER_ID from the output** — it is needed for all subsequent commands. Store it.

Print: "Cluster created successfully. Cluster ID: {CLUSTER_ID}"

### 5b. Create node pools

For **each** node pool, run via `Bash`:

If auto-scaling is **enabled**:

```bash
vultr-cli kubernetes node-pool create {CLUSTER_ID} \
  --label "{POOL_{N}_LABEL}" \
  --plan "{POOL_{N}_PLAN}" \
  --quantity {POOL_{N}_NODE_COUNT} \
  --auto-scaler true \
  --min-nodes {POOL_{N}_MIN_NODES} \
  --max-nodes {POOL_{N}_MAX_NODES}
```

If auto-scaling is **disabled**:

```bash
vultr-cli kubernetes node-pool create {CLUSTER_ID} \
  --label "{POOL_{N}_LABEL}" \
  --plan "{POOL_{N}_PLAN}" \
  --quantity {POOL_{N}_NODE_COUNT}
```

Print: "Node pool '{POOL_{N}_LABEL}' created successfully."

**If any command fails, show the error to the user and ask whether to retry or abort.**

---

## Step 6: Configure kubectl

Run via `Bash`:

```bash
# Create .kube directory if it doesn't exist
mkdir -p ~/.kube

# Download kubeconfig
vultr-cli kubernetes config {CLUSTER_ID} > ~/.kube/tone-{ENV_NAME}-config

# Set as current context
export KUBECONFIG=~/.kube/tone-{ENV_NAME}-config

# Verify connectivity
kubectl get nodes
```

Print the node list output to confirm all nodes are visible.

**Note:** Nodes may take a few minutes to become Ready. If nodes show NotReady, inform the user and suggest waiting. You can poll with:

```bash
kubectl get nodes --watch
```

---

## Step 7: Ask About Add-ons

Use `AskUserQuestion`:

**Question — "Which cluster add-ons should be installed?"**
- multiSelect: true
- Options:
  - `nginx-ingress controller (Recommended)` — Load balancer and ingress routing
  - `cert-manager (Recommended)` — Automatic TLS certificate management via Let's Encrypt
  - `Let's Encrypt ClusterIssuer` — Production certificate issuer (requires cert-manager)

Store selected add-ons as: `ADDONS` list

### 7a. nginx-ingress (if selected)

Ask with `AskUserQuestion`:

**Question — "How many ingress controller replicas?"**
- Options: `1`, `2 (Recommended)`, `3`

Then **execute** via `Bash`:

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount={REPLICAS} \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.type=LoadBalancer
```

Then verify via `Bash`:

```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

Print the EXTERNAL-IP from the service output. If it shows `<pending>`, inform the user it may take 1-2 minutes and poll:

```bash
kubectl get svc -n ingress-nginx --watch
```

### 7b. cert-manager (if selected)

Ask with `AskUserQuestion`:

**Question — "How many cert-manager replicas?"**
- Options: `1`, `2 (Recommended)`, `3`

Then **execute** via `Bash`:

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set crds.enabled=true \
  --set replicaCount={REPLICAS}
```

Then verify via `Bash`:

```bash
kubectl wait --for=condition=Ready pods --all -n cert-manager --timeout=120s
kubectl get pods -n cert-manager
```

### 7c. Let's Encrypt ClusterIssuer (if selected)

Ask with `AskUserQuestion`:

**Question — "What email should be used for Let's Encrypt certificate notifications?"**
- Options: `karthik@productfusion.co (Recommended)`
- Allow custom input

Then **execute** via `Bash`:

```bash
kubectl apply -f build/kubernetes/{ENV_NAME}/letsencrypt-prod.yaml
```

Verify via `Bash`:

```bash
kubectl get clusterissuer letsencrypt-prod
```

---

## Step 8: Ask About Namespace & Secrets

Use `AskUserQuestion`:

**Question — "What Kubernetes namespace should be created for this environment?"**
- Options: `{ENV_NAME} (Recommended)`
- Allow custom input

Store as: `NAMESPACE`

**Execute** namespace creation via `Bash`:

```bash
kubectl create namespace {NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
```

Then ask with `AskUserQuestion`:

**Question — "Which secrets need to be created in the namespace?"**
- multiSelect: true
- Options:
  - `infisical-credentials (Recommended)` — Infisical token + project ID for secrets management
  - `dockerhub-auth (Recommended)` — Docker registry pull credentials

Store as: `SECRETS` list

### If infisical-credentials selected:

Ask with `AskUserQuestion` (both in a single call):

**Question 1 — "Enter your Infisical token:"**
- No predefined options — user must type the value

**Question 2 — "Enter your Infisical project ID:"**
- No predefined options — user must type the value

Then **execute** via `Bash`:

```bash
kubectl create secret generic infisical-credentials \
  --namespace={NAMESPACE} \
  --from-literal=token='{INFISICAL_TOKEN}' \
  --from-literal=project_id='{INFISICAL_PROJECT_ID}' \
  --dry-run=client -o yaml | kubectl apply -f -
```

### If dockerhub-auth selected:

Ask with `AskUserQuestion` (both in a single call):

**Question 1 — "Enter your DockerHub username:"**
- No predefined options — user must type the value

**Question 2 — "Enter your DockerHub password/token:"**
- No predefined options — user must type the value

Then **execute** via `Bash`:

```bash
kubectl create secret docker-registry dockerhub-auth \
  --namespace={NAMESPACE} \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username='{DOCKER_USERNAME}' \
  --docker-password='{DOCKER_PASSWORD}' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Verify secrets via `Bash`:

```bash
kubectl get secrets -n {NAMESPACE}
```

---

## Step 9: Ask for Domain Details

Use `AskUserQuestion` (ask both in a single call):

**Question 1 — "What is the API domain for this environment?"**
- Options: `{ENV_NAME}-api.trytone.ai (Recommended)`
- Allow custom input

**Question 2 — "What is the Call Worker domain for this environment?"**
- Options: `{ENV_NAME}-call.trytone.ai (Recommended)`
- Allow custom input

Store as: `API_DOMAIN`, `CALL_DOMAIN`

Print DNS instructions:
```
Point these DNS records to the ingress EXTERNAL-IP:
  {API_DOMAIN}  → {EXTERNAL_IP}
  {CALL_DOMAIN} → {EXTERNAL_IP}
```

---

## Step 10: Final Summary & Verification

Run a final verification via `Bash`:

```bash
echo "=== Cluster Status ==="
vultr-cli kubernetes list

echo "=== Nodes ==="
kubectl get nodes

echo "=== Namespaces ==="
kubectl get namespaces

echo "=== Ingress ==="
kubectl get svc -n ingress-nginx 2>/dev/null || echo "nginx-ingress not installed"

echo "=== Cert-Manager ==="
kubectl get pods -n cert-manager 2>/dev/null || echo "cert-manager not installed"

echo "=== Secrets ==="
kubectl get secrets -n {NAMESPACE} 2>/dev/null || echo "Namespace not found"
```

Then print the complete cluster configuration summary:

```
Cluster Provisioning — Complete
=================================
Cluster Label:    {CLUSTER_LABEL}
Cluster ID:       {CLUSTER_ID}
Region:           {REGION}
Environment:      {ENV_NAME}
Namespace:        {NAMESPACE}

Node Pools:
┌─────┬────────────────┬──────────────────┬───────┬──────────────────────────┬────────────┐
│  #  │ Label          │ Plan             │ Nodes │ Auto-scale               │ Cost/mo    │
├─────┼────────────────┼──────────────────┼───────┼──────────────────────────┼────────────┤
│  1  │ {label}        │ {plan}           │ {n}   │ {yes: min-max / no}      │ ${cost}    │
│  2  │ {label}        │ {plan}           │ {n}   │ {yes: min-max / no}      │ ${cost}    │
│ ... │ ...            │ ...              │ ...   │ ...                      │ ...        │
└─────┴────────────────┴──────────────────┴───────┴──────────────────────────┴────────────┘

Estimated base cost: ~${total}/mo

Add-ons:
  [{x| }] nginx-ingress controller (ingress-nginx namespace)
  [{x| }] cert-manager (cert-manager namespace)
  [{x| }] Let's Encrypt ClusterIssuer

Domains:
  API:  {API_DOMAIN}  → {EXTERNAL_IP}
  Call: {CALL_DOMAIN} → {EXTERNAL_IP}

Secrets in namespace {NAMESPACE}:
  [{x| }] infisical-credentials
  [{x| }] dockerhub-auth

Kubeconfig: ~/.kube/tone-{ENV_NAME}-config

Next steps:
  - Run /provisioning-db to set up the database for this environment
  - Run /setup-new-deployment to generate K8s manifests and GitHub Actions workflow
  - Or run /generate-kubernetes-deployment if manifests already exist
```

---

## Important Rules

- **MUST use `AskUserQuestion`** for every input — never assume, derive, or skip any value.
- **MUST display node option tables** before asking the user to pick a plan for each pool.
- **MUST confirm the full configuration** (Step 4) before executing any provisioning commands.
- **MUST execute** all provisioning commands via the `Bash` tool — do NOT just print them.
- **MUST show command output** to the user after each execution step.
- **MUST parse and store the CLUSTER_ID** from the cluster creation output for use in subsequent commands.
- **MUST handle errors** — if a command fails, show the error and ask the user whether to retry or abort.
- **MUST repeat** Steps 3a–3f for every node pool the user requested.
- **MUST ask for secret values** (Infisical token, DockerHub credentials) via AskUserQuestion before creating secrets.
- If user selects "No, start over" at confirmation, re-ask everything from Step 1.
- **NEVER hard-code or assume** secret values — always ask the user.
