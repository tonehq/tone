---
name: generate_kubernetes_deployment
description: "Generate Kubernetes deployment manifests for a new environment. Use when setting up a new deployment environment (dev, staging, production, etc.) that needs Kubernetes manifests for the Tone application. Generates organized manifests under build/kubernetes/{env}/ with api/ and call/ subdirectories. Can also be called by the setup_new_deployment parent skill."
---

# Generate Kubernetes Deployment Manifests

Generate all Kubernetes manifests for a new Tone deployment environment.

## Input

Three values are required: `ENV_NAME`, `API_DOMAIN`, `CALL_DOMAIN`. All other values are derived:

| Value | Convention |
|-------|-----------|
| `RESOURCE_PREFIX` | `{ENV_NAME}-` (empty string for `dev`) |
| `DOCKER_IMAGE` | `developer390/tone:${IMAGE_TAG}` |
| `API_REPLICAS` | `2` |
| `CALL_REPLICAS` | `2` |
| `API_CPU_REQUEST/LIMIT` | `100m` / `256m` |
| `API_MEM_REQUEST/LIMIT` | `512Mi` / `1Gi` |
| `CALL_CPU_REQUEST/LIMIT` | `1` / `2` |
| `CALL_MEM_REQUEST/LIMIT` | `1Gi` / `2Gi` |
| `MAX_CONCURRENT_CALLS` | `5` |
| `LETSENCRYPT_EMAIL` | `karthik@productfusion.co` |

## Output Folder Structure

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

## Generation Steps

1. Create directories: `build/kubernetes/{ENV_NAME}/api/` and `build/kubernetes/{ENV_NAME}/call/`
2. Read templates from `references/api-templates.md` and `references/call-templates.md`
3. Substitute all `{PLACEHOLDER}` values using the derived conventions above
4. Write the 10 manifest files

## GCP Override

If caller specifies `CLOUD_PROVIDER=gcp`, read `references/gcp-overrides.md` and apply changes (different image format, no `imagePullSecrets`).

## Naming Convention

For `dev` environment: no prefix (e.g., `tone-api-deployment`).
For all others: `{ENV_NAME}-` prefix (e.g., `production-tone-api-deployment`).
