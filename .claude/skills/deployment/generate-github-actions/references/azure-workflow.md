# Azure AKS GitHub Actions Workflow Template

All placeholders use `{PLACEHOLDER}` syntax. Replace before writing.

```yaml
name: {ENV_NAME_TITLE} CI/CD

on:
  push:
    branches: ["{BRANCH_NAME}"]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          username: ${{{{ secrets.DOCKER_USERNAME }}}}
          password: ${{{{ secrets.DOCKER_PASSWORD }}}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          push: true
          tags: |
            {DOCKER_REPO}:{DOCKER_TAG_PREFIX}
            {DOCKER_REPO}:${{{{ github.sha }}}}
          cache-from: type=registry,ref={DOCKER_REPO}:{ENV_NAME}-buildcache
          cache-to: type=registry,ref={DOCKER_REPO}:{ENV_NAME}-buildcache,mode=max
          secrets: |
            pip_extra_index=${{{{ secrets.PIP_EXTRA_INDEX_URL }}}}

      - uses: azure/k8s-set-context@v4
        with:
          kubeconfig: ${{{{ secrets.{KUBE_CONFIG_SECRET} }}}}

      - name: Create namespace
        run: kubectl create namespace {ENV_NAME} --dry-run=client -o yaml | kubectl apply -f -

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
          kubectl rollout restart deployment/{RESOURCE_PREFIX}tone-api-deployment -n {ENV_NAME}
          kubectl rollout restart deployment/{RESOURCE_PREFIX}tone-call-worker -n {ENV_NAME}

      - name: Wait for rollouts
        run: |
          kubectl rollout status deployment/{RESOURCE_PREFIX}tone-api-deployment -n {ENV_NAME} --timeout=180s
          kubectl rollout status deployment/{RESOURCE_PREFIX}tone-call-worker -n {ENV_NAME} --timeout=180s
```

## Notes

- `{ENV_NAME_TITLE}`: Title-cased environment name for the workflow display name (e.g., "Staging", "Production")
- `{RESOURCE_PREFIX}`: Empty for `dev`, `{ENV_NAME}-` for all other environments
- `{KUBE_CONFIG_SECRET}`: GitHub secret name holding the Azure kubeconfig JSON
- `{DOCKER_TAG_PREFIX}`: e.g., `staging-latest`, `latest`, `production-latest`
