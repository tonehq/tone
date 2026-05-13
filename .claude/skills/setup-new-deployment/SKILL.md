---
name: setup_new_deployment
description: "End-to-end setup for a new deployment environment. Use when the user wants to set up a complete new deployment (e.g., 'set up staging', 'create production deployment', 'add a new environment'). Creates a Git branch, generates Kubernetes manifests (via generate_kubernetes_deployment), and generates GitHub Actions workflow (via generate_github_actions_file). Invoked as /setup_new_deployment."
---

# Setup New Deployment

Orchestrate full environment setup: Git branch + Kubernetes manifests + GitHub Actions workflow.

## Step 1: Get Input from User

Ask the user to type these 3 values as free text. Do NOT use preset option lists — let the user type freely:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `ENV_NAME` | Environment name | `production` |
| `API_DOMAIN` | API domain | `production-api.trytone.ai` |
| `CALL_DOMAIN` | Call worker domain | `production-call.trytone.ai` |

## Derived Values

Everything else follows existing project conventions. Do NOT ask the user for these:

| Value | Convention | Example (ENV_NAME=production) |
|-------|-----------|-------------------------------|
| `BRANCH_NAME` | Same as `ENV_NAME` | `production` |
| `CLOUD_PROVIDER` | `azure` (default) | `azure` |
| `DOCKER_REPO` | `developer390/tone` | `developer390/tone` |
| `DOCKER_IMAGE` | `developer390/tone:${IMAGE_TAG}` | `developer390/tone:${IMAGE_TAG}` |
| `DOCKER_TAG_PREFIX` | `{ENV_NAME}-latest` | `production-latest` |
| `KUBE_CONFIG_SECRET` | `{ENV_NAME_UPPER}_KUBE_CONFIG_JSON` | `PRODUCTION_KUBE_CONFIG_JSON` |
| `RESOURCE_PREFIX` | `{ENV_NAME}-` (empty for `dev`) | `production-` |
| `API_REPLICAS` | `2` | `2` |
| `CALL_REPLICAS` | `2` | `2` |
| `LETSENCRYPT_EMAIL` | `karthik@productfusion.co` | `karthik@productfusion.co` |
| Resource limits | Same as existing staging | CPU/mem defaults |

## Step 2: Create Git Branch

```bash
git checkout -b {ENV_NAME}
```

If branch exists, ask user whether to switch to it or abort.

## Step 3: Generate Kubernetes Manifests

Read and follow `.claude/skills/generate-kubernetes-deployment/SKILL.md` using all derived values. Do NOT re-ask the user for parameters.

Output structure:
```
build/kubernetes/{ENV_NAME}/
├── api/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── certificate.yaml
├── call/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── certificate.yaml
│   └── pdb.yaml
└── letsencrypt-prod.yaml
```

## Step 4: Generate GitHub Actions Workflow

Read and follow `.claude/skills/generate-github-actions/SKILL.md` using all derived values.

Output: `.github/workflows/{ENV_NAME}.yaml`

## Step 5: Secrets & Commands Reference

After generating all files, print the complete secrets setup guide. Do NOT attempt to run any `gh`, `kubectl`, or cluster commands yourself. Only display them for the user.

### 5a. GitHub Secrets

Print the required GitHub secrets and the commands to set them:

```
GitHub Secrets required (add in repo Settings > Secrets and variables > Actions):

  DOCKER_USERNAME              — DockerHub username
  DOCKER_PASSWORD              — DockerHub password/token
  {ENV_NAME_UPPER}_KUBE_CONFIG_JSON — Azure AKS kubeconfig JSON (used by azure/k8s-set-context@v4)
  PIP_EXTRA_INDEX_URL          — Cloudsmith PyPI URL for private tone-pipecat package

Commands to set via CLI (if gh is installed):

  gh secret set DOCKER_USERNAME
  gh secret set DOCKER_PASSWORD
  gh secret set {ENV_NAME_UPPER}_KUBE_CONFIG_JSON
  gh secret set PIP_EXTRA_INDEX_URL
```

### 5b. Kubernetes Namespace Secrets

Print the commands the user needs to run once connected to the cluster. Always show these — never attempt to run them:

```
Kubernetes secrets required in namespace "{ENV_NAME}":

1. Create the namespace:

   kubectl create namespace {ENV_NAME} --dry-run=client -o yaml | kubectl apply -f -

2. Create infisical-credentials secret (replace <values>):

   kubectl create secret generic infisical-credentials \
     --namespace={ENV_NAME} \
     --from-literal=token='<YOUR_INFISICAL_TOKEN>' \
     --from-literal=project_id='<YOUR_INFISICAL_PROJECT_ID>' \
     --dry-run=client -o yaml | kubectl apply -f -

3. Create dockerhub-auth pull secret (replace <values>):

   kubectl create secret docker-registry dockerhub-auth \
     --namespace={ENV_NAME} \
     --docker-server=https://index.docker.io/v1/ \
     --docker-username='<YOUR_DOCKER_USERNAME>' \
     --docker-password='<YOUR_DOCKER_PASSWORD>' \
     --dry-run=client -o yaml | kubectl apply -f -

To verify secrets after creation:

   kubectl get secrets -n {ENV_NAME}
```

## Step 6: Summary

Print all files created, then the full secrets reference from Step 5, then remind the user to push the `{BRANCH_NAME}` branch to trigger the workflow.

Do NOT commit, push, or run any cluster/gh commands automatically.
