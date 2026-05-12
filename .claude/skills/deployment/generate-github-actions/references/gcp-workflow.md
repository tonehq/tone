# GCP GKE GitHub Actions Workflow Template

All placeholders use `{PLACEHOLDER}` syntax. Replace before writing.

```yaml
name: {ENV_NAME_TITLE} GCP GKE CI/CD

on:
  push:
    branches: ["{BRANCH_NAME}"]

env:
  GCP_PROJECT_ID: ${{{{ secrets.GCP_PROJECT_ID }}}}
  GCP_REGION: {GCP_REGION}
  GKE_CLUSTER_NAME: {GKE_CLUSTER_NAME}
  GKE_CLUSTER_LOCATION: {GKE_CLUSTER_LOCATION}
  REPOSITORY: {GCP_REPOSITORY}
  IMAGE_NAME: {GCP_IMAGE_NAME}
  NAMESPACE: {ENV_NAME}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{{{ secrets.GCP_SA_KEY }}}}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker ${{{{ env.GCP_REGION }}}}-docker.pkg.dev --quiet

      - uses: docker/setup-buildx-action@v3

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          push: true
          tags: |
            ${{{{ env.GCP_REGION }}}}-docker.pkg.dev/${{{{ env.GCP_PROJECT_ID }}}}/${{{{ env.REPOSITORY }}}}/${{{{ env.IMAGE_NAME }}}}:latest
            ${{{{ env.GCP_REGION }}}}-docker.pkg.dev/${{{{ env.GCP_PROJECT_ID }}}}/${{{{ env.REPOSITORY }}}}/${{{{ env.IMAGE_NAME }}}}:${{{{ github.sha }}}}
          cache-from: type=registry,ref=${{{{ env.GCP_REGION }}}}-docker.pkg.dev/${{{{ env.GCP_PROJECT_ID }}}}/${{{{ env.REPOSITORY }}}}/${{{{ env.IMAGE_NAME }}}}:buildcache
          cache-to: type=registry,ref=${{{{ env.GCP_REGION }}}}-docker.pkg.dev/${{{{ env.GCP_PROJECT_ID }}}}/${{{{ env.REPOSITORY }}}}/${{{{ env.IMAGE_NAME }}}}:buildcache,mode=max
          secrets: |
            pip_extra_index=${{{{ secrets.PIP_EXTRA_INDEX_URL }}}}

      - id: get-credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: ${{{{ env.GKE_CLUSTER_NAME }}}}
          location: ${{{{ env.GKE_CLUSTER_LOCATION }}}}

      - name: Create namespace
        run: kubectl create namespace ${{{{ env.NAMESPACE }}}} --dry-run=client -o yaml | kubectl apply -f -

      - name: Ensure infisical-credentials secret exists
        run: |
          kubectl create secret generic infisical-credentials \
            --namespace=${{{{ env.NAMESPACE }}}} \
            --from-literal=token='${{{{ secrets.INFISICAL_TOKEN }}}}' \
            --from-literal=project_id='${{{{ secrets.INFISICAL_PROJECT_ID }}}}' \
            --dry-run=client -o yaml | kubectl apply -f -

      - name: Substitute IMAGE_TAG in deployment manifests
        run: |
          sed -i "s|\${{IMAGE_TAG}}|${{{{ github.sha }}}}|g" build/kubernetes/{ENV_NAME}/api/deployment.yaml
          sed -i "s|\${{IMAGE_TAG}}|${{{{ github.sha }}}}|g" build/kubernetes/{ENV_NAME}/call/deployment.yaml

      - name: Apply all manifests
        run: |
          kubectl apply -f build/kubernetes/{ENV_NAME}/letsencrypt-prod.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/api/service.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/api/deployment.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/api/certificate.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/api/ingress.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/call/pdb.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/call/service.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/call/deployment.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/call/certificate.yaml
          kubectl apply -f build/kubernetes/{ENV_NAME}/call/ingress.yaml

      - name: Rollout restart deployments
        run: |
          kubectl rollout restart deployment/{RESOURCE_PREFIX}tone-api-deployment -n ${{{{ env.NAMESPACE }}}}
          kubectl rollout restart deployment/{RESOURCE_PREFIX}tone-call-worker -n ${{{{ env.NAMESPACE }}}}

      - name: Wait for rollouts
        run: |
          kubectl rollout status deployment/{RESOURCE_PREFIX}tone-api-deployment -n ${{{{ env.NAMESPACE }}}} --timeout=180s
          kubectl rollout status deployment/{RESOURCE_PREFIX}tone-call-worker -n ${{{{ env.NAMESPACE }}}} --timeout=180s
```

## Notes

- `{ENV_NAME_TITLE}`: Title-cased environment name (e.g., "Staging GCP Kube")
- `{RESOURCE_PREFIX}`: Empty for `dev`, `{ENV_NAME}-` for all other environments
- GCP workflow includes the `infisical-credentials` secret creation step (Azure assumes it already exists in the cluster)
- GCP uses Artifact Registry instead of DockerHub
- GCP uses workload identity via `google-github-actions/get-gke-credentials` instead of kubeconfig secret
