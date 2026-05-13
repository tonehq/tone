---
name: provisioning_cluster
description: "Provision a Vultr Kubernetes Engine (VKE) cluster with node pools and add-ons. Interactively collects all configuration from the user via AskUserQuestion, then executes the provisioning commands via Bash tool. Use when setting up a new Kubernetes cluster or when the user asks to create/provision a cluster."
---

# Provisioning Cluster

Interactively guide the user through provisioning a Vultr Kubernetes Engine (VKE) cluster. Use `AskUserQuestion` at every step to collect ALL required inputs. After user confirms the configuration, **execute all commands via the `Bash` tool** — do NOT just print them.

**Pattern:**
- Use AskUserQuestion for ALL user choices
- Run all CLI commands via Bash using `vultr_api.py` — chain related commands in a single Bash call to minimize permission prompts
- All output is JSON for easy parsing
- For Infisical secret creation, use the provisioning-db skill's `infisical_api.py` script (at `.claude/skills/provisioning-db/scripts/infisical_api.py`) instead of asking for raw tokens

## Scripts

Helper scripts:
- `scripts/vultr_api.py` — wraps vultr-cli, kubectl, and helm commands, outputs JSON
- Infisical helper (from provisioning-db): `.claude/skills/provisioning-db/scripts/infisical_api.py`

Set script path variables:
```bash
CLUSTER_SKILL=".claude/skills/provisioning-cluster/provisioning-vultr/scripts"
DB_SKILL=".claude/skills/provisioning-db/scripts"
```

## Prerequisites

Check all prerequisites in a single Bash call:

```bash
python3 $CLUSTER_SKILL/vultr_api.py check && python3 $CLUSTER_SKILL/vultr_api.py auth-check
```

- If any tool is missing (vultr-cli, kubectl, helm), show the install command from the output and STOP.
- If Vultr auth fails, ask the user for their Vultr API key via `AskUserQuestion` and run:
  ```bash
  python3 $CLUSTER_SKILL/vultr_api.py set-api-key --key {API_KEY}
  ```

---

## Step 1: Collect Cluster Details

First fetch regions and K8s versions in a single Bash call:

```bash
python3 $CLUSTER_SKILL/vultr_api.py list-regions && echo "---VERSIONS---" && python3 $CLUSTER_SKILL/vultr_api.py list-versions
```

Then use `AskUserQuestion` to ask all 4 questions in a single call:

**Question 1 — Environment Name:**
- Question: "What is the environment name for this cluster?"
- Options: `staging`, `production`, `dev`
- Allow custom input

**Question 2 — Cluster Label:**
- Question: "What label/name should this cluster have?"
- Do NOT hardcode any project-specific names. Derive from environment name:
  - `{ENV_NAME}-cluster`
  - `{ENV_NAME}`
- Allow custom input

**Question 3 — Region:**
- Question: "Which Vultr region should the cluster be provisioned in?"
- Display ALL regions as a numbered table before asking:
  ```
  Available Regions:
  ┌──────┬──────┬───────────────┬─────────┐
  │ S.No │ ID   │ City          │ Country │
  ├──────┼──────┼───────────────┼─────────┤
  │  1   │ ams  │ Amsterdam     │ NL      │
  │  2   │ blr  │ Bangalore     │ IN      │
  │ ...  │ ...  │ ...           │ ...     │
  └──────┴──────┴───────────────┴─────────┘
  ```
- Show top 4 as quick-pick options, allow custom input (user can type S.No or region ID)

**Question 4 — Kubernetes Version:**
- Question: "Which Kubernetes version?"
- Show versions from the fetched list (latest first as Recommended)
- Allow custom input

Store as: `ENV_NAME`, `CLUSTER_LABEL`, `REGION`, `K8S_VERSION`

---

## Step 2: Collect Number of Node Pools

Use `AskUserQuestion`:

**Question — How many node pools do you need?**
- Options:
  - `2` — Separate pools for API and Call Worker workloads
  - `3 (Recommended)` — System pool (ingress, cert-manager) + API pool + Call Worker pool
  - `4` — System + API + Call Worker + a custom pool

Store as: `NODE_POOL_COUNT`

---

## Step 3: Collect Pool Configuration

For **each** node pool (1 to `NODE_POOL_COUNT`), collect purpose, plan, count, and auto-scaling.

### 3a. Ask pool purpose + plan + count + auto-scaling

**IMPORTANT:** Node pool labels MUST be unique across the cluster. If the user picks the same purpose twice (e.g. two "API" pools), auto-suffix with a number (API-1, API-2).

Fetch plans dynamically and display as numbered table with pricing:

```bash
python3 $CLUSTER_SKILL/vultr_api.py list-plans
```

Display the JSON output as a numbered table:

```
VKE-Compatible Node Plans (live from Vultr API):

┌──────┬─────────────────┬───────┬────────┬─────────────┬──────────┬──────────┐
│ S.No │ Plan ID         │ vCPUs │ RAM    │ Storage     │ $/hour   │ $/month  │
├──────┼─────────────────┼───────┼────────┼─────────────┼──────────┼──────────┤
│  1   │ vc2-1c-2gb      │ 1     │ 2 GB   │ 55 GB SSD   │ $0.0137  │ $10      │
│  2   │ vc2-2c-4gb      │ 2     │ 4 GB   │ 80 GB SSD   │ $0.0274  │ $20      │
│ ...  │ ...             │ ...   │ ...    │ ...         │ ...      │ ...      │
└──────┴─────────────────┴───────┴────────┴─────────────┴──────────┴──────────┘

⚠ Optimized plans (voc-*) are NOT compatible with VKE. Only vc2-* and vhp-* plans are shown.
```

Use `AskUserQuestion` with up to 4 questions per pool:

**Q1 — "What is the purpose of node pool {N}?"**
- Options: `System`, `API`, `Call Worker` + custom

**Q2 — "Which plan for the {POOL_LABEL} pool?"**
- Contextual recommendations:
  - System: `vc2-2c-4gb (Recommended)`, `vc2-1c-2gb`, `vhp-2c-4gb-amd`
  - API: `vc2-4c-8gb (Recommended)`, `vc2-2c-4gb`, `vhp-4c-8gb-amd`
  - Call Worker: `vc2-6c-16gb (Recommended)`, `vc2-4c-8gb`, `vhp-8c-16gb-amd`
  - Custom: `vc2-2c-4gb`, `vc2-4c-8gb`, `vc2-6c-16gb`
- Allow custom input

**Q3 — "How many nodes for {POOL_LABEL}?"**
- Options: `1`, `2 (Recommended)`, `3`, `4`

**Q4 — "Enable auto-scaling for {POOL_LABEL}?"**
- Options: `Yes (Recommended)`, `No`

### 3b. If auto-scaling is Yes, ask min/max

Use `AskUserQuestion` (2 questions):

**Q1 — "Minimum nodes for {POOL_LABEL} auto-scaler?"** → Options: `1`, `2`, `3`
**Q2 — "Maximum nodes for {POOL_LABEL} auto-scaler?"** → Options: `3`, `4`, `5`, `6`

**Repeat 3a–3b for each node pool.**

---

## Step 4: Confirm Configuration

Fetch plan prices dynamically for the cost summary:

```bash
python3 $CLUSTER_SKILL/vultr_api.py get-plan-price --plan-id {PLAN_ID}
```

Display summary with both hourly and monthly costs:

```
Cluster Configuration Summary
==============================
Cluster Label:   {CLUSTER_LABEL}
Region:          {REGION}
K8s Version:     {K8S_VERSION}
Environment:     {ENV_NAME}

Node Pools:
┌───┬────────────────┬──────────────────┬───────┬──────────────────────┬──────────┬──────────┐
│ # │ Label          │ Plan             │ Nodes │ Auto-scale           │ $/hour   │ $/month  │
├───┼────────────────┼──────────────────┼───────┼──────────────────────┼──────────┼──────────┤
│ 1 │ {label}        │ {plan}           │ {n}   │ {Yes: min-max / No}  │ ${hr}    │ ${mo}    │
│...│ ...            │ ...              │ ...   │ ...                  │ ...      │ ...      │
└───┴────────────────┴──────────────────┴───────┴──────────────────────┴──────────┴──────────┘

Estimated cost: ~${total_hourly}/hr | ~${total_monthly}/mo
```

Use `AskUserQuestion`:
- `Yes, provision now` — Execute all provisioning commands
- `No, start over` — Re-collect all inputs from Step 1

---

## Step 5: Create Cluster + Node Pools

**vultr-cli creates cluster and first node pool(s) in a single command.** Build the node pools JSON and run:

```bash
python3 $CLUSTER_SKILL/vultr_api.py create-cluster \
  --label "{CLUSTER_LABEL}" \
  --region "{REGION}" \
  --version "{K8S_VERSION}" \
  --node-pools '{POOLS_JSON}'
```

Where `POOLS_JSON` is a JSON array like:
```json
[{"label":"System","plan":"vc2-2c-4gb","quantity":2,"auto_scaler":true,"min_nodes":1,"max_nodes":3}]
```

**Parse `cluster_id` from the JSON output.** Store as `CLUSTER_ID`.

**If the command fails:**
- "Node pool labels must be unique" → Ensure all labels are distinct (suffix with -1, -2)
- "Invalid NodePool ID" → The selected plan is not VKE-compatible. Ask user to pick a `vc2-*` or `vhp-*` plan instead
- Other errors → Show error and ask whether to retry or abort

---

## Step 6: Configure kubectl & Wait for Nodes

Download kubeconfig (handles base64 decoding automatically):

```bash
python3 $CLUSTER_SKILL/vultr_api.py get-config --cluster-id {CLUSTER_ID} --env-name {ENV_NAME}
```

Then wait for nodes to join the cluster. Calculate expected node count from all pools:

```bash
python3 $CLUSTER_SKILL/vultr_api.py wait-for-nodes --env-name {ENV_NAME} --expected-nodes {TOTAL_NODES} --timeout 300
```

- If status=ok: print the node list and continue
- If status=timeout: inform the user that nodes are still provisioning (Vultr can take 5-10 min), but proceed with add-ons since those only need one ready node
- **Do NOT block indefinitely** — if wait-for-nodes times out, continue to Step 7

---

## Step 7: Install Add-ons

Use `AskUserQuestion`:

**Question — "Which cluster add-ons should be installed?"**
- multiSelect: true
- Options:
  - `nginx-ingress controller (Recommended)` — Load balancer and ingress routing
  - `cert-manager (Recommended)` — Automatic TLS certificate management
  - `Let's Encrypt ClusterIssuer` — Production certificate issuer (requires cert-manager)

### 7a. nginx-ingress (if selected)

Ask replica count, then execute:

```bash
python3 $CLUSTER_SKILL/vultr_api.py install-nginx --env-name {ENV_NAME} --replicas {N}
```

Print EXTERNAL-IP from JSON output. If `<pending>` or `None`, tell user it takes 1-2 min.

### 7b. cert-manager (if selected)

Ask replica count, then execute:

```bash
python3 $CLUSTER_SKILL/vultr_api.py install-cert-manager --env-name {ENV_NAME} --replicas {N}
```

### 7c. Let's Encrypt ClusterIssuer (if selected)

Ask email via AskUserQuestion (no hardcoded options), then:

```bash
python3 $CLUSTER_SKILL/vultr_api.py apply-cluster-issuer \
  --env-name {ENV_NAME} \
  --manifest-path build/kubernetes/{ENV_NAME}/letsencrypt-prod.yaml
```

---

## Step 8: Create Namespace & Secrets

### 8a. Namespace

Use `AskUserQuestion` — suggest `{ENV_NAME}` as default. Then:

```bash
python3 $CLUSTER_SKILL/vultr_api.py create-namespace --env-name {ENV_NAME} --namespace {NAMESPACE}
```

### 8b. Select secrets to create

Use `AskUserQuestion` (multiSelect):
- `infisical-credentials (Recommended)` — Use provisioning-db's Infisical flow
- `dockerhub-auth (Recommended)` — Docker registry pull credentials

### 8c. infisical-credentials (if selected)

**Use the provisioning-db skill's `infisical_api.py`** to get/create the Infisical service token properly instead of asking for raw tokens:

1. Check Infisical auth:
   ```bash
   python3 $DB_SKILL/infisical_api.py auth-check
   ```

2. If auth ok, list orgs → select org → list projects → select project → list envs → select env → create service token:
   ```bash
   python3 $DB_SKILL/infisical_api.py list-orgs
   python3 $DB_SKILL/infisical_api.py list-projects --org-id {ORG_ID}
   python3 $DB_SKILL/infisical_api.py list-envs --project-id {PROJECT_ID}
   python3 $DB_SKILL/infisical_api.py create-service-token --project-id {PROJECT_ID} --env {ENV_SLUG} --name {TOKEN_NAME}
   ```
   Use `AskUserQuestion` at each step to let user pick org, project, env, and token name.

3. Create K8s secret with the token and project ID:
   ```bash
   python3 $CLUSTER_SKILL/vultr_api.py create-secret-generic \
     --env-name {ENV_NAME} \
     --namespace {NAMESPACE} \
     --name infisical-credentials \
     --literals "token={INFISICAL_TOKEN}" "project_id={INFISICAL_PROJECT_ID}"
   ```

4. If auth fails, ask user to run `! infisical login --domain <DOMAIN>` and retry.

### 8d. dockerhub-auth (if selected)

Ask both via `AskUserQuestion` (2 questions):
- "Enter your DockerHub username:" (2 options: "Type in notes" + "Skip for now")
- "Enter your DockerHub password/token:" (2 options: "Type in notes" + "Skip for now")

If user skips, tell them to create the secret manually later.

Then execute:
```bash
python3 $CLUSTER_SKILL/vultr_api.py create-secret-docker \
  --env-name {ENV_NAME} \
  --namespace {NAMESPACE} \
  --username '{DOCKER_USERNAME}' \
  --password '{DOCKER_PASSWORD}'
```

---

## Step 9: Domain Details

Use `AskUserQuestion` (2 questions — no hardcoded domain options):

- "What is the API domain for this environment?" (2 options: "Type in notes" + "Skip for now")
- "What is the Call Worker domain for this environment?" (2 options: "Type in notes" + "Skip for now")

Print DNS instructions with the ingress EXTERNAL-IP:
```
Point these DNS records to the ingress EXTERNAL-IP:
  {API_DOMAIN}  → {EXTERNAL_IP}
  {CALL_DOMAIN} → {EXTERNAL_IP}
```

---

## Step 10: Final Summary & Verification

Run verification:

```bash
python3 $CLUSTER_SKILL/vultr_api.py verify-cluster --env-name {ENV_NAME} --namespace {NAMESPACE}
```

Print the complete summary:

```
Cluster Provisioning — Complete
=================================
Cluster Label:    {CLUSTER_LABEL}
Cluster ID:       {CLUSTER_ID}
Region:           {REGION}
K8s Version:      {K8S_VERSION}
Environment:      {ENV_NAME}
Namespace:        {NAMESPACE}

Node Pools:
┌─────┬────────────────┬──────────────────┬───────┬──────────────────────┬────────────┐
│  #  │ Label          │ Plan             │ Nodes │ Auto-scale           │ Cost/mo    │
├─────┼────────────────┼──────────────────┼───────┼──────────────────────┼────────────┤
│  1  │ {label}        │ {plan}           │ {n}   │ {yes: min-max / no}  │ ${cost}    │
│ ... │ ...            │ ...              │ ...   │ ...                  │ ...        │
└─────┴────────────────┴──────────────────┴───────┴──────────────────────┴────────────┘

Estimated base cost: ~${total}/mo

Add-ons:
  [{x| }] nginx-ingress controller
  [{x| }] cert-manager
  [{x| }] Let's Encrypt ClusterIssuer

Domains:
  API:  {API_DOMAIN}  → {EXTERNAL_IP}
  Call: {CALL_DOMAIN} → {EXTERNAL_IP}

Secrets in namespace {NAMESPACE}:
  [{x| }] infisical-credentials
  [{x| }] dockerhub-auth

Kubeconfig: ~/.kube/{ENV_NAME}-config

Next steps:
  - Run /provisioning-db to set up the database for this environment
  - Run /setup-new-deployment to generate K8s manifests and GitHub Actions workflow
  - Or run /generate-kubernetes-deployment if manifests already exist
```

---

## Important Rules

- **MUST use `AskUserQuestion`** for every input — never assume, derive, or skip any value.
- **MUST NOT hardcode** any project-specific names, domains, or emails. All values must come from the user.
- **MUST use only VKE-compatible plans** — `vc2-*` and `vhp-*` only. Optimized plans (`voc-*`) are NOT supported by VKE.
- **MUST ensure unique node pool labels** — If duplicate purposes are selected, auto-suffix with numbers (API-1, API-2).
- **MUST create cluster + pools in a single `create-cluster` command** — vultr-cli requires `--version` and `--node-pools` flags.
- **MUST use `wait-for-nodes`** after kubeconfig download instead of manual polling. If it times out, proceed anyway.
- **MUST use provisioning-db's `infisical_api.py`** for Infisical authentication and service token creation — do NOT ask for raw tokens.
- **MUST confirm the full configuration** (Step 4) before executing any provisioning commands.
- **MUST display tables (regions, plans, confirmation summary) as direct text output** — NOT inside Bash tool calls. Bash output gets collapsed in the terminal and the user cannot see it. Fetch data via Bash, then render the table in your response text.
- **MUST execute** all commands via the `Bash` tool using helper scripts — do NOT just print them.
- **MUST handle errors** — if a command fails, show the error and ask whether to retry or abort.
- **MUST batch questions** — use up to 4 questions per AskUserQuestion call to minimize prompts.
- **AskUserQuestion options need minimum 2 items** — always include at least 2 options per question.
- If user selects "No, start over" at confirmation, re-ask everything from Step 1.
