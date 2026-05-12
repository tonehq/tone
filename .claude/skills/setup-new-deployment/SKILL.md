---
name: setup_new_deployment
description: "End-to-end setup for a new deployment environment. Use when the user wants to set up a complete new deployment (e.g., 'set up staging', 'create production deployment', 'add a new environment'). Creates a Git branch, generates Kubernetes manifests (via generate_kubernetes_deployment), and generates GitHub Actions workflow (via generate_github_actions_file). Invoked as /setup_new_deployment."
---

# Setup New Deployment

Orchestrate full environment setup: Git branch + Kubernetes manifests + GitHub Actions workflow.

## Step 1: Get Input from User

Ask the user for these 3 values only:

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

## Step 5: Summary

Print files created and remind user to:
1. Review generated files
2. Add the following GitHub secrets in your repository settings:
   - `DOCKER_USERNAME` — DockerHub username
   - `DOCKER_PASSWORD` — DockerHub password/token
   - `{ENV_NAME_UPPER}_KUBE_CONFIG_JSON` — Azure AKS kubeconfig JSON (used by `azure/k8s-set-context@v4` in the workflow)
   - `PIP_EXTRA_INDEX_URL` — Cloudsmith PyPI URL for the private tone-pipecat package
3. Push the `{BRANCH_NAME}` branch to trigger the workflow

Do NOT commit or push automatically.
