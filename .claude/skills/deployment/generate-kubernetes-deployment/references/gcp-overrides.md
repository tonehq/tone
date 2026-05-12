# GCP Overrides for Kubernetes Manifests

When `CLOUD_PROVIDER=gcp`, apply these changes to the templates:

## Docker Image Format

Replace the Docker image reference in both `api/deployment.yaml` and `call/deployment.yaml`:

```
{GCP_REGION}-docker.pkg.dev/{GCP_PROJECT_ID}/{GCP_REPOSITORY}/{GCP_IMAGE_NAME}:${IMAGE_TAG}
```

### Additional GCP parameters to collect

| Parameter | Description | Example |
|-----------|-------------|---------|
| `GCP_REGION` | GCP Artifact Registry region | `us-central1` |
| `GCP_PROJECT_ID` | GCP project ID | `my-project-id` |
| `GCP_REPOSITORY` | Artifact Registry repository name | `tone` |
| `GCP_IMAGE_NAME` | Image name in the repository | `tone-staging-gke` |

## Remove imagePullSecrets

For GCP deployments, **remove** the `imagePullSecrets` block from both deployment files. GKE uses workload identity or node service accounts for Artifact Registry auth, not Docker pull secrets.

## No other changes

All other manifests (service, ingress, certificate, pdb, letsencrypt-prod) remain identical regardless of cloud provider.
