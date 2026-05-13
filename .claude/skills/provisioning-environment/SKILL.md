---
name: provisioning_environment
description: "Complete end-to-end environment provisioning — Neon database + Infisical secrets + Kubernetes cluster + manifests + CI/CD + migrations. Single skill that does everything. Supports Vultr (now) and DigitalOcean (future)."
---

# Provisioning Environment

Single skill for complete environment setup. Collects ALL user inputs upfront, then executes DB and Cluster provisioning in parallel via subagents, then integrates outputs (K8s secrets, manifests, migrations).

**Architecture: 3-Stage Flow**
- **Stage 1** — Collect all inputs interactively (AskUserQuestion)
- **Stage 2** — Execute DB + Cluster in parallel (two subagents, no user interaction)
- **Stage 3** — Integrate outputs + generate manifests + run migrations

## Provider Map

```
vultr:
  cluster_skill: .claude/skills/provisioning-cluster/provisioning-vultr/SKILL.md
  cluster_script: .claude/skills/provisioning-cluster/provisioning-vultr/scripts/vultr_api.py
digitalocean:  # FUTURE — add skill + scripts, then add as option in Phase 1
  cluster_skill: .claude/skills/provisioning-digitalocean/SKILL.md
  cluster_script: .claude/skills/provisioning-digitalocean/scripts/do_api.py
```

## Script References

```bash
DB_SKILL=".claude/skills/provisioning-db/scripts"
CLUSTER_SKILL=".claude/skills/provisioning-cluster/provisioning-vultr/scripts"
```

## Variable Handoff

| Variable | Created In | Used In |
|----------|-----------|---------|
| `ENV_NAME` | Phase 1 | All phases |
| `CLUSTER_SCRIPT` | Phase 1 | Phases 2, 5, 7 (provider-specific) |
| `DATABASE_URL`, `DB_*` | Subagent 1 | Subagent 1 (Infisical secrets) |
| `INFISICAL_PROJECT_ID` | Subagent 1 | Phase 7 (K8s secret) |
| `INFISICAL_TOKEN` | Subagent 1 | Phase 7 (K8s secret) |
| `CLUSTER_ID` | Subagent 2 | Subagent 2 (kubeconfig) |
| `EXTERNAL_IP` | Subagent 2 | Phase 7 (DNS instructions) |

---

# STAGE 1: COLLECT ALL INPUTS

## Phase 1: Shared Inputs

Use `AskUserQuestion` — 4 questions in 1 call:

**Q1 — Cloud Provider:**
- Options: `Vultr (Recommended)`, `DigitalOcean (coming soon)`
- If DigitalOcean selected and not implemented, print message and STOP

**Q2 — Environment Name:**
- Options: `staging`, `production`, `dev`
- Allow custom input

**Q3 — API Domain:**
- Options: `Type in notes`, `Skip for now`
- User types domain in notes field

**Q4 — Call Worker Domain:**
- Options: `Type in notes`, `Skip for now`
- User types domain in notes field

Then DockerHub credentials (2 questions in 1 call):
- **Q1:** "DockerHub username" — Options: `Type in notes`, `Skip for now`
- **Q2:** "DockerHub password/token" — Options: `Type in notes`, `Skip for now`

Store: `PROVIDER`, `ENV_NAME`, `API_DOMAIN`, `CALL_DOMAIN`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`

Set `CLUSTER_SCRIPT` based on provider:
- vultr → `.claude/skills/provisioning-cluster/provisioning-vultr/scripts/vultr_api.py`

---

## Phase 2: Prerequisites Check

Single Bash call:

```bash
python3 $DB_SKILL/neon_api.py check && \
python3 $DB_SKILL/infisical_api.py auth-check && \
python3 $CLUSTER_SKILL/vultr_api.py check && \
python3 $CLUSTER_SKILL/vultr_api.py auth-check
```

If any fail, show install/auth instructions and STOP. Handle each failure independently — some may pass while others fail.

For cloud provider auth failure, ask for API key via AskUserQuestion:
```bash
python3 $CLUSTER_SKILL/vultr_api.py set-api-key --key {API_KEY}
```

---

## Phase 3: DB Inputs

> Collect questions only — do NOT execute yet

### 3a: Neon Org

```bash
python3 $DB_SKILL/neon_api.py list-orgs
```

Use AskUserQuestion to show orgs + "Create new". Store `NEON_ORG_ID`.

### 3b: Neon Project

```bash
python3 $DB_SKILL/neon_api.py list-projects --org-id {NEON_ORG_ID}
```

Use AskUserQuestion: show projects + "Create new project". If new, collect (3 questions):
1. Project name
2. Postgres version — `17 (Recommended)`, `16`, `15`
3. Region — fetch via `python3 $DB_SKILL/neon_api.py list-regions`, display numbered table, ask by S.No

Store: `NEON_PROJECT_ACTION` (new/existing), `NEON_PROJECT_ID` or `NEON_PROJECT_NAME`, `NEON_PG_VERSION`, `NEON_REGION`

### 3c: Role + Database

Use AskUserQuestion (2 questions):
1. Role name — suggest `{project}_{ENV_NAME}_user`
2. Database name — suggest `{project}_{ENV_NAME}`

Store: `DB_ROLE_NAME`, `DB_NAME`

---

## Phase 4: Infisical Inputs

> Collect questions only — do NOT execute yet

### 4a: Auth Check

```bash
python3 $DB_SKILL/infisical_api.py auth-check
```

If expired/no_config, ask user to run `! infisical login --domain <DOMAIN>` and re-check.

### 4b: Infisical Org + Project

```bash
python3 $DB_SKILL/infisical_api.py list-orgs
```

AskUserQuestion: pick org. Store `INFISICAL_ORG_ID`.

```bash
python3 $DB_SKILL/infisical_api.py list-projects --org-id {INFISICAL_ORG_ID}
```

AskUserQuestion: pick project or "Create new". Store `INFISICAL_PROJECT_ID` or `INFISICAL_PROJECT_NAME`.

### 4c: Infisical Environment

```bash
python3 $DB_SKILL/infisical_api.py list-envs --project-id {INFISICAL_PROJECT_ID}
```

AskUserQuestion: pick env or "Create new" — suggest `{ENV_NAME}`. Store `INFISICAL_ENV_SLUG`.

---

## Phase 5: Cluster Inputs

> Collect questions only — do NOT execute yet

### 5a: Cluster Details

Fetch regions and K8s versions:
```bash
python3 $CLUSTER_SKILL/vultr_api.py list-regions && echo "---" && python3 $CLUSTER_SKILL/vultr_api.py list-versions
```

Parse the JSON output and **print the regions table as direct text output** (NOT inside a Bash tool call — Bash output gets collapsed and the user cannot see it). Build the table in your response text so it renders visibly in the terminal:

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

Use AskUserQuestion (3 questions):
1. Cluster label — suggest `{ENV_NAME}-cluster`
2. Region — show top 4 as quick-pick, allow custom (S.No or ID from table above)
3. K8s version — show latest as Recommended

Store: `CLUSTER_LABEL`, `REGION`, `K8S_VERSION`

### 5b: Node Pool Count

AskUserQuestion:
- `2` — API + Call Worker
- `3 (Recommended)` — System + API + Call Worker
- `4` — System + API + Call Worker + custom

### 5c: Per-Pool Config

Fetch plans dynamically, filtered to the selected region:
```bash
python3 $CLUSTER_SKILL/vultr_api.py list-plans --region {REGION}
```

Parse the JSON output and **print the plan table as direct text output** (NOT inside a Bash tool call — Bash output gets collapsed and the user cannot see it). Build the table in your response text so it renders visibly in the terminal:

```
VKE-Compatible Node Plans:
┌──────┬─────────────────┬───────┬────────┬─────────────┬──────────┬──────────┐
│ S.No │ Plan ID         │ vCPUs │ RAM    │ Storage     │ $/hour   │ $/month  │
├──────┼─────────────────┼───────┼────────┼─────────────┼──────────┼──────────┤
│  1   │ vc2-1c-2gb      │ 1     │ 2 GB   │ 55 GB SSD   │ $0.0137  │ $10      │
│  2   │ vc2-2c-4gb      │ 2     │ 4 GB   │ 80 GB SSD   │ $0.0274  │ $20      │
│ ...  │ ...             │ ...   │ ...    │ ...         │ ...      │ ...      │
└──────┴─────────────────┴───────┴────────┴─────────────┴──────────┴──────────┘
⚠ Optimized plans (voc-*) are NOT VKE-compatible. Only vc2-* and vhp-* work.
```

For EACH pool, use AskUserQuestion (4 questions):
1. Purpose — `System`, `API`, `Call Worker` + custom
2. Plan — contextual recommendations (select by S.No or plan ID)
3. Node count — `1`, `2 (Recommended)`, `3`, `4`
4. Auto-scaling — `Yes (Recommended)`, `No`

If auto-scaling Yes, ask min/max (2 questions).

**IMPORTANT:** Ensure unique pool labels. If duplicate purposes, auto-suffix (API-1, API-2).

Store all pool configs in a list.

### 5d: Add-ons

AskUserQuestion (multiSelect):
- `nginx-ingress controller (Recommended)`
- `cert-manager (Recommended)`
- `Let's Encrypt ClusterIssuer`

If nginx selected: ask replica count (`1`, `2 (Recommended)`, `3`)
If cert-manager selected: ask replica count
If ClusterIssuer selected: ask email (no hardcoded options, must type)

### 5e: Infisical Service Token Name

AskUserQuestion: token name — suggest `{ENV_NAME}-service-token`

---

## Phase 6: Confirm Everything

Display unified summary of ALL collected inputs with cost estimates (hourly + monthly):

```
Provisioning Summary
=====================
Provider:     {PROVIDER}
Environment:  {ENV_NAME}

DATABASE (Neon):
  Org:        {neon_org_name}
  Project:    {new/existing} — {name}
  PG Version: {version}
  Region:     {region}
  Database:   {DB_NAME}
  Role:       {DB_ROLE_NAME}

SECRETS (Infisical):
  Org:        {infisical_org_name}
  Project:    {infisical_project_name}
  Environment: {INFISICAL_ENV_SLUG}

CLUSTER ({PROVIDER}):
  Label:      {CLUSTER_LABEL}
  Region:     {REGION}
  K8s:        {K8S_VERSION}
  Node Pools:
  ┌───┬────────────┬────────────────┬───────┬──────────────┬──────────┬──────────┐
  │ # │ Label      │ Plan           │ Nodes │ Auto-scale   │ $/hour   │ $/month  │
  ├───┼────────────┼────────────────┼───────┼──────────────┼──────────┼──────────┤
  │ 1 │ {label}    │ {plan}         │ {n}   │ {Yes:m-M/No} │ ${hr}    │ ${mo}    │
  └───┴────────────┴────────────────┴───────┴──────────────┴──────────┴──────────┘
  Add-ons: {list}
  Estimated: ~${total_hourly}/hr | ~${total_monthly}/mo

DOMAINS:
  API:  {API_DOMAIN}
  Call: {CALL_DOMAIN}

DockerHub: {DOCKER_USERNAME}
```

AskUserQuestion: `Yes, provision now` / `No, start over`

If "No" → go back to Phase 1.

---

# STAGE 2: PARALLEL EXECUTION

After user confirms, launch TWO subagents in a **single message** (they run concurrently):

## Subagent 1: DB + Infisical Execution

Launch Agent (type: general-purpose) with this prompt:

> "Execute Neon DB and Infisical provisioning. All user inputs are provided below — do NOT use AskUserQuestion.
>
> **Scripts:** Use scripts at `.claude/skills/provisioning-db/scripts/`
>
> **Step 1: Neon Project**
> - Action: {new/existing}
> - If new: `python3 {DB_SKILL}/neon_api.py create-project --org-id {NEON_ORG_ID} --name {name} --region {region}`
> - If existing: use project ID {NEON_PROJECT_ID}
> - Get branch: `python3 {DB_SKILL}/neon_api.py list-branches --project-id {PROJECT_ID}`
>
> **Step 2: Create Role + Database**
> - `python3 {DB_SKILL}/neon_api.py create-role --project-id {PID} --branch-id {BID} --name {DB_ROLE_NAME}`
> - `python3 {DB_SKILL}/neon_api.py create-database --project-id {PID} --branch-id {BID} --name {DB_NAME} --owner {DB_ROLE_NAME}`
>
> **Step 3: Connection String**
> - `python3 {DB_SKILL}/neon_api.py connection-string --project-id {PID} --database {DB_NAME} --role {DB_ROLE_NAME}`
>
> **Step 4: Infisical Secrets**
> - Generate SECRET_KEY: `python3 -c "import secrets; print(secrets.token_hex(32))"`
> - Set all secrets via infisical CLI:
>   `infisical secrets set DATABASE_URL={url} DB_HOST={host} DB_PORT=5432 DB_NAME={name} DB_USER={user} DB_PASSWORD={pass} SECRET_KEY={key} IS_MULTI_TENANT=false USE_INFISICAL=true --env {INFISICAL_ENV_SLUG} --projectId {INFISICAL_PROJECT_ID} --domain {INFISICAL_DOMAIN}`
>
> **Step 5: Service Token**
> - `python3 {DB_SKILL}/infisical_api.py create-service-token --project-id {INFISICAL_PROJECT_ID} --env {INFISICAL_ENV_SLUG} --name {TOKEN_NAME}`
>
> **Return a single JSON object with:** DATABASE_URL, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, INFISICAL_PROJECT_ID, INFISICAL_TOKEN, SECRET_KEY"

## Subagent 2: Cluster Execution

Launch Agent (type: general-purpose) with this prompt:

> "Execute VKE cluster provisioning. All user inputs are provided below — do NOT use AskUserQuestion.
>
> **Scripts:** Use scripts at `.claude/skills/provisioning-cluster/provisioning-vultr/scripts/`
>
> **Step 1: Create Cluster**
> - `python3 {CLUSTER_SKILL}/vultr_api.py create-cluster --label {CLUSTER_LABEL} --region {REGION} --version {K8S_VERSION} --node-pools '{POOLS_JSON}'`
> - Parse CLUSTER_ID from output
>
> **Step 2: Download Kubeconfig**
> - `python3 {CLUSTER_SKILL}/vultr_api.py get-config --cluster-id {CLUSTER_ID} --env-name {ENV_NAME}`
>
> **Step 3: Wait for ALL Nodes**
> - `python3 {CLUSTER_SKILL}/vultr_api.py wait-for-nodes --env-name {ENV_NAME} --expected-nodes {TOTAL_NODES} --timeout 600`
> - MUST wait until ALL expected nodes show Ready — do NOT proceed with partial results
> - If timeout after 10 min, report the status and ask whether to continue or wait more
>
> **Step 4: Install Add-ons** (if selected)
> - nginx: `python3 {CLUSTER_SKILL}/vultr_api.py install-nginx --env-name {ENV_NAME} --replicas {N}`
> - cert-manager: `python3 {CLUSTER_SKILL}/vultr_api.py install-cert-manager --env-name {ENV_NAME} --replicas {N}`
> - ClusterIssuer: `python3 {CLUSTER_SKILL}/vultr_api.py apply-cluster-issuer --env-name {ENV_NAME} --manifest-path build/kubernetes/{ENV_NAME}/letsencrypt-prod.yaml`
>
> **Return a single JSON object with:** CLUSTER_ID, CLUSTER_LABEL, EXTERNAL_IP, KUBECONFIG_PATH"

---

# STAGE 3: INTEGRATION

After both subagents return their results:

## Phase 7: K8s Namespace + Secrets

### 7a: Create Namespace

```bash
python3 $CLUSTER_SKILL/vultr_api.py create-namespace --env-name {ENV_NAME} --namespace {ENV_NAME}
```

### 7b: Infisical Credentials Secret (auto-fill from Subagent 1)

```bash
python3 $CLUSTER_SKILL/vultr_api.py create-secret-generic \
  --env-name {ENV_NAME} \
  --namespace {ENV_NAME} \
  --name infisical-credentials \
  --literals "token={INFISICAL_TOKEN}" "project_id={INFISICAL_PROJECT_ID}"
```

### 7c: DockerHub Secret (from Phase 1)

If DockerHub credentials were provided (not skipped):

```bash
python3 $CLUSTER_SKILL/vultr_api.py create-secret-docker \
  --env-name {ENV_NAME} \
  --namespace {ENV_NAME} \
  --username '{DOCKER_USERNAME}' \
  --password '{DOCKER_PASSWORD}'
```

---

## Phase 8: Setup Deployment (Branch + Manifests + CI/CD)

> **Delegate to:** `/setup-new-deployment` skill (`.claude/skills/setup-new-deployment/SKILL.md`)
> Pass: `ENV_NAME`, `API_DOMAIN`, `CALL_DOMAIN`

This single skill handles everything:
- Creates Git branch `{ENV_NAME}`
- Generates K8s manifests at `build/kubernetes/{ENV_NAME}/` (10 files: deployments, services, ingress, certificates, PDB, ClusterIssuer)
- Generates GitHub Actions workflow at `.github/workflows/{ENV_NAME}.yaml`
- Prints secrets reference (GitHub secrets + K8s namespace secrets)

**IMPORTANT:** Since we already created the K8s namespace and secrets (infisical-credentials, dockerhub-auth) in Phase 7, the secrets commands from setup-new-deployment's Step 5b are already done — mention this when printing the summary.

Do NOT re-ask for `ENV_NAME`, `API_DOMAIN`, or `CALL_DOMAIN` — pass them directly from Phase 1 inputs.

---

## Phase 9: Run Migrations + Seed Data

```bash
export DATABASE_URL='{DATABASE_URL}' && alembic upgrade head && python dev/seed.py
```

If this fails, show error and ask: `Retry` / `Skip migrations` / `Abort`

---

## Phase 10: Verification + Summary

Run verification:
```bash
python3 $CLUSTER_SKILL/vultr_api.py verify-cluster --env-name {ENV_NAME} --namespace {ENV_NAME}
```

Print unified summary:

```
Environment Provisioning — Complete
=====================================
Environment:     {ENV_NAME}
Cloud Provider:  {PROVIDER}

DATABASE (Neon):
  Project:       {name} ({id})
  Region:        {region}
  Database:      {DB_NAME}
  Role:          {DB_USER}
  DATABASE_URL:  {DATABASE_URL}

SECRETS (Infisical):
  Project:       {name} ({INFISICAL_PROJECT_ID})
  Environment:   {INFISICAL_ENV_SLUG}
  Secrets:       9 secrets set
  Service Token: {INFISICAL_TOKEN}

CLUSTER ({PROVIDER}):
  Label:         {CLUSTER_LABEL}
  Cluster ID:    {CLUSTER_ID}
  Region:        {REGION}
  K8s Version:   {K8S_VERSION}
  Node Pools:
  ┌───┬────────────┬────────────────┬───────┬──────────────┬──────────┬──────────┐
  │ # │ Label      │ Plan           │ Nodes │ Auto-scale   │ $/hour   │ $/month  │
  ├───┼────────────┼────────────────┼───────┼──────────────┼──────────┼──────────┤
  │ 1 │ {label}    │ {plan}         │ {n}   │ {Yes:m-M/No} │ ${hr}    │ ${mo}    │
  └───┴────────────┴────────────────┴───────┴──────────────┴──────────┴──────────┘
  Estimated: ~${total_hourly}/hr | ~${total_monthly}/mo

ADD-ONS:
  [{x| }] nginx-ingress → {EXTERNAL_IP}
  [{x| }] cert-manager
  [{x| }] Let's Encrypt ClusterIssuer

DOMAINS:
  API:  {API_DOMAIN}  → {EXTERNAL_IP}
  Call: {CALL_DOMAIN} → {EXTERNAL_IP}

K8S SECRETS (namespace: {ENV_NAME}):
  [{x| }] infisical-credentials
  [{x| }] dockerhub-auth

MANIFESTS:
  [x] build/kubernetes/{ENV_NAME}/ (K8s deployment YAMLs)
  [x] .github/workflows/{ENV_NAME}.yaml (CI/CD pipeline)

MIGRATIONS:
  [x] alembic upgrade head — schema applied
  [x] python dev/seed.py — seed data loaded

Kubeconfig: ~/.kube/{ENV_NAME}-config

Setup complete! Your environment is ready.
```

---

## Error Handling

Each phase on failure → AskUserQuestion:
- `Retry this step` — Re-run the failed command
- `Skip and continue` — **Only for:** add-ons, DockerHub secret, domains, migrations
- `Abort provisioning` — Stop entirely

**Skip NOT allowed for:** Neon DB creation, Infisical secrets, cluster creation, infisical-credentials K8s secret, manifests generation.

---

## Important Rules

- **MUST collect ALL user inputs in Stage 1** before executing anything — this enables parallel subagent execution in Stage 2.
- **MUST launch both subagents in a SINGLE message** so they run concurrently.
- **MUST NOT use AskUserQuestion in subagent prompts** — all inputs must be pre-collected.
- **MUST NOT hardcode** any project-specific names, domains, emails, or prices. Everything comes from user input or API calls.
- **MUST display tables as direct text output** — NOT inside Bash tool calls. Bash output gets collapsed in the terminal and the user cannot see it. After fetching data via Bash, parse the JSON and render the table in your response text (regions table, plan table, confirmation summary, final summary).
- **MUST delegate to `/setup-new-deployment`** in Phase 8 — it handles git branch creation, K8s manifests, GitHub Actions workflow, and secrets reference in one step.
- **MUST display plans and regions as numbered tables** with S.No for selection. Plans must include $/hour and $/month columns.
- **MUST fetch plan pricing dynamically** from Vultr API — no hardcoded prices.
- **MUST ensure unique node pool labels** — auto-suffix with numbers if duplicates.
- **MUST use only VKE-compatible plans** — `vc2-*` and `vhp-*` only. Warn about `voc-*`.
- **MUST auto-fill Infisical values** in Phase 7 from Subagent 1 output — do NOT re-ask.
- **MUST delegate** to `/setup-new-deployment` for branch creation + manifests + CI/CD — do NOT duplicate their logic. This single skill handles git branch, K8s manifests, and GitHub Actions.
- **MUST handle Infisical auth** via `infisical_api.py` from provisioning-db scripts — do NOT ask for raw tokens.
- AskUserQuestion requires **minimum 2 options** per question, **maximum 4 questions** per call.
