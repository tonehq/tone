---
name: generate_github_actions_file
description: "Generate GitHub Actions CI/CD workflow YAML for a new deployment environment. Use when setting up a new environment that needs a GitHub Actions pipeline for building Docker images and deploying to Kubernetes (Azure AKS or GCP GKE). Can also be called by the setup_new_deployment parent skill."
---

# Generate GitHub Actions Workflow

Generate a GitHub Actions CI/CD workflow for a new Tone deployment environment.

## Input

Only `ENV_NAME` is required. All other values are derived:

| Value | Convention |
|-------|-----------|
| `BRANCH_NAME` | Same as `ENV_NAME` |
| `ENV_NAME_TITLE` | Title-cased `ENV_NAME` (e.g., `Production CI/CD`) |
| `DOCKER_REPO` | `developer390/tone` |
| `DOCKER_TAG_PREFIX` | `{ENV_NAME}-latest` |
| `KUBE_CONFIG_SECRET` | `{ENV_NAME_UPPER}_KUBE_CONFIG_JSON` |
| `RESOURCE_PREFIX` | `{ENV_NAME}-` (empty for `dev`) |
| `CLOUD_PROVIDER` | `azure` (default) |

## Output

Single file: `.github/workflows/{ENV_NAME}.yaml`

## Generation Steps

1. Default to Azure. Read `references/azure-workflow.md` template.
2. If caller specifies `CLOUD_PROVIDER=gcp`, read `references/gcp-workflow.md` instead.
3. Substitute all `{PLACEHOLDER}` values.
4. Write to `.github/workflows/{ENV_NAME}.yaml`.

## Key: New Folder Structure

The workflow references `api/` and `call/` subdirectories:

```yaml
# Manifests are under build/kubernetes/{ENV_NAME}/api/ and call/
kubectl apply -f build/kubernetes/{ENV_NAME}/api/deployment.yaml
kubectl apply -f build/kubernetes/{ENV_NAME}/call/deployment.yaml
```
