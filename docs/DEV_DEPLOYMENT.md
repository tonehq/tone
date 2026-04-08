# Dev Environment Setup & Deployment

End-to-end guide for deploying **Tone** (API server + voice call worker) to a Kubernetes cluster via GitHub Actions, including the private `tone-pipecat` fork that Tone depends on.

This document is self-contained: a new developer (or Claude) should be able to bootstrap everything in the `dev` namespace by following it top-to-bottom.

---

## 1. Architecture overview

```
                        ┌─────────────────────────────────────────┐
                        │         GitHub (tonehq/tone)            │
                        │  push to dev → .github/workflows/dev    │
                        └──────────────────┬──────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
        ┌───────────────────────┐                     ┌───────────────────────┐
        │  Docker Hub           │                     │  Kubernetes cluster   │
        │  developer390/tone    │                     │  (Vultr VKE)          │
        │  :latest + :<sha>     │                     │                       │
        └───────────────────────┘                     │  namespace: dev       │
                    ▲                                 │  ├─ tone-api          │
                    │                                 │  │  (port 8000)       │
        ┌───────────┴───────────┐                     │  └─ tone-call-worker  │
        │  Cloudsmith (private) │◀──── pip install ───│     (port 8080)       │
        │  tonehq/tone          │                     │                       │
        │  tone-pipecat wheel   │                     │  ingress-nginx        │
        └───────────────────────┘                     │  cert-manager (LE)    │
                    ▲                                 └───────────┬───────────┘
                    │                                             │
        ┌───────────┴───────────┐                                 ▼
        │  GitHub               │                     ┌───────────────────────┐
        │  tonehq/pipecat       │                     │  Cloudflare DNS       │
        │  push → cloudsmith    │                     │  dev-api.trytone.ai   │
        │  workflow publishes   │                     │  dev-call.trytone.ai  │
        └───────────────────────┘                     └───────────────────────┘
```

Two services in the cluster, same Docker image, different startup commands:

| Service           | Port | Host                     | Purpose                                              | Ingress behavior                                                 |
| ----------------- | ---- | ------------------------ | ---------------------------------------------------- | ---------------------------------------------------------------- |
| `tone-api`        | 8000 | `dev-api.trytone.ai`     | HTTP REST API (auth, agents, call logs, etc.)        | Cloudflare proxied (orange cloud) — standard HTTP                |
| `tone-call-worker`| 8080 | `dev-call.trytone.ai`    | Long-lived WebSocket for telephony (Twilio, Telnyx…) | Cloudflare **DNS only** (grey cloud) to avoid 100s idle timeout  |

---

## 2. Repositories

| Repo                                                | Role                                                                   |
| --------------------------------------------------- | ---------------------------------------------------------------------- |
| [`tonehq/tone`](https://github.com/tonehq/tone)     | Main application (FastAPI backend, Next.js frontend, K8s manifests)    |
| [`tonehq/pipecat`](https://github.com/tonehq/pipecat) | Fork of the upstream Pipecat framework, published as `tone-pipecat`  |

The fork is **not** a git submodule. The `tone` repo installs it from Cloudsmith via pip:

```
# requirements.txt
tone-pipecat==0.0.74+dev.5
```

---

## 3. Prerequisites

### 3.1 Accounts / services

| Service          | What you need                                                           |
| ---------------- | ----------------------------------------------------------------------- |
| **Docker Hub**   | Account + Personal Access Token with **Read & Write** scope             |
| **Cloudsmith**   | Account + a PyPI-format repository (ours: `tonehq/tone`)                |
| **Kubernetes**   | A cluster (we use Vultr VKE). Admin kubeconfig                          |
| **Cloudflare**   | DNS zone for the domain (ours: `trytone.ai`)                            |
| **Infisical**    | Project containing all runtime secrets (DATABASE_URL, JWT_SECRET_KEY, R2 creds, TWILIO creds, etc.) |
| **Let's Encrypt**| Automatic — cert-manager handles issuance                               |

### 3.2 Local tools

```bash
# macOS
brew install kubectl gh cloudsmith-cli docker
```

---

## 4. Cloudsmith setup (private PyPI for `tone-pipecat`)

The `tone-pipecat` wheel is private and published to Cloudsmith every time a branch is pushed in `tonehq/pipecat`.

### 4.1 Create a Cloudsmith repository

1. Log in to [cloudsmith.io](https://cloudsmith.io)
2. Create a repo: **Packages → Create Repository**
   - Name: `tone`
   - Format: `Python (PyPI)`
   - Visibility: `Private`
   - Storage region: whichever is closest
3. Your repo URL is now `https://cloudsmith.io/~tonehq/repos/tone/`

### 4.2 Create an Entitlement Token (read-only, for CI/CD & pip installs)

1. In the repo, sidebar → **Entitlements → + Create Token**
2. Name: `github-actions-read`
3. Leave defaults — you get a token like `aawJ4aCReQyKN7zL`
4. Build the `PIP_EXTRA_INDEX_URL`:

   ```
   https://<token>:@dl.cloudsmith.io/<token>/tonehq/tone/python/simple/
   ```

   Example:
   ```
   https://aawJ4aCReQyKN7zL:@dl.cloudsmith.io/aawJ4aCReQyKN7zL/tonehq/tone/python/simple/
   ```

### 4.3 Create an API Key (write, for publishing from pipecat CI)

1. Top-right avatar → **API Settings → Get My API Key**
2. Copy the key — this is `CLOUDSMITH_API_KEY`
3. Your Cloudsmith username (e.g. `karthikeyans`) is `CLOUDSMITH_USERNAME`

---

## 5. `tonehq/pipecat` — the private fork

### 5.1 Fork layout

- Branch `main` tracks upstream `pipecat-ai/pipecat`
- Branch `dev` contains our customizations, merged from `main` periodically
- Package name in `pyproject.toml` is **`tone-pipecat`** (not `pipecat-ai`)
- `src/pipecat/__init__.py` looks up its version under `tone-pipecat` with a fallback to `pipecat-ai` so it works either way

### 5.2 GitHub secrets on the pipecat repo

Required for the publish workflow:

| Secret                | Value                        |
| --------------------- | ---------------------------- |
| `CLOUDSMITH_USERNAME` | Your Cloudsmith username     |
| `CLOUDSMITH_API_KEY`  | From step 4.3                |

Add them at `Settings → Secrets and variables → Actions → New repository secret`.

### 5.3 `publish-cloudsmith` workflow

File: `pipecat/.github/workflows/publish-cloudsmith.yaml`

Triggered on every push to any branch. It:

1. Computes the version as `<TONE_BASE_VERSION>+<branch-slug>.<run_number>`
   (e.g. `0.0.74+dev.5`, `0.0.74+main.17`)
2. Builds the wheel + sdist with `python -m build`
3. Uploads to `https://python.cloudsmith.io/tonehq/tone/` via twine

To bump the base version (e.g. after merging a significant upstream release):
```yaml
env:
  TONE_BASE_VERSION: '0.0.75'  # edit this, commit, push
```

### 5.4 Pulling upstream updates into the fork

```bash
# One-time: add upstream remote
cd ~/path/to/pipecat-fork
git remote add upstream https://github.com/pipecat-ai/pipecat.git

# Every time you want to sync:
git fetch upstream
git checkout main
git merge upstream/main          # or: git rebase upstream/main
git push origin main

# Then port the changes into dev (our deploy branch):
git checkout dev
git merge main
# Resolve conflicts — especially in pyproject.toml (keep name = "tone-pipecat")
#                    and src/pipecat/__init__.py (keep the tone-pipecat fallback)
git push origin dev              # triggers publish-cloudsmith → new version
```

After the publish workflow succeeds, bump the version pin in `tonehq/tone` `requirements.txt` to the new `0.0.74+dev.N` and push.

### 5.5 Important files you must preserve in the fork

These are the only files we diverge from upstream on. Do **not** let a merge from upstream overwrite them blindly:

| File                          | What it contains                                                              |
| ----------------------------- | ----------------------------------------------------------------------------- |
| `pyproject.toml`              | `name = "tone-pipecat"` — must stay this                                      |
| `src/pipecat/__init__.py`     | Version lookup tries `tone-pipecat` first, falls back to `pipecat-ai`         |
| `.github/workflows/publish-cloudsmith.yaml` | Our custom publish workflow (doesn't exist upstream)           |

---

## 6. `tonehq/tone` — the main repo

### 6.1 GitHub secrets

| Secret                 | Value                                                                          |
| ---------------------- | ------------------------------------------------------------------------------ |
| `DOCKER_USERNAME`      | Docker Hub username (e.g. `developer390` or your email)                        |
| `DOCKER_PASSWORD`      | Docker Hub **PAT with Read/Write** (not your login password)                   |
| `KUBE_CONFIG_JSON`     | Full contents of `~/.kube/config` for the target cluster (raw YAML is fine)    |
| `PIP_EXTRA_INDEX_URL`  | Cloudsmith URL from step 4.2                                                   |

Set them with the `gh` CLI or the GitHub web UI:

```bash
gh secret set DOCKER_USERNAME       --body "developer390"
gh secret set DOCKER_PASSWORD       --body "<docker-hub-pat>"
gh secret set PIP_EXTRA_INDEX_URL   --body "https://<token>:@dl.cloudsmith.io/<token>/tonehq/tone/python/simple/"
gh secret set KUBE_CONFIG_JSON      --body "$(cat ~/.kube/config)"
```

### 6.2 `Dev CI/CD` workflow

File: `.github/workflows/dev.yaml`

Triggered on every push to `dev`. It:

1. Checks out the repo (no submodules needed anymore)
2. Logs in to Docker Hub
3. Builds the image with `PIP_EXTRA_INDEX_URL` passed as a **BuildKit secret** (so it doesn't end up in image layers or `docker history`)
4. Pushes `developer390/tone:latest` and `developer390/tone:<git-sha>`
5. Sets the `kubectl` context from `KUBE_CONFIG_JSON`
6. Creates the `dev` namespace if missing
7. Substitutes `${IMAGE_TAG}` → the git SHA in `deployment.yaml` + `call-deployment.yaml` (traceability: every running pod pins to a specific commit)
8. Applies every manifest in `build/kubernetes/dev/`
9. Rolls out both deployments and waits up to 180s per rollout

### 6.3 Dockerfile

File: `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libpq-dev git \
        libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN --mount=type=secret,id=pip_extra_index \
    PIP_EXTRA_INDEX_URL="$(cat /run/secrets/pip_extra_index 2>/dev/null || true)" \
    pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Notes on the system libs:
- `gcc`, `libpq-dev`: needed to build `psycopg2` wheels
- `git`: needed if any pip dependency is a git URL
- `libxcb1`, `libgl1`, `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender1`: runtime libs that `cv2` (transitive dep of pipecat's SmallWebRTC transport) needs. Without these, **any `/ws` connection crashes** with `libxcb.so.1: cannot open shared object file`.

### 6.4 Local build (for testing before pushing)

```bash
export PIP_EXTRA_INDEX_URL="https://<token>:@dl.cloudsmith.io/<token>/tonehq/tone/python/simple/"
DOCKER_BUILDKIT=1 docker build \
  --secret id=pip_extra_index,env=PIP_EXTRA_INDEX_URL \
  -t tone:local .
```

---

## 7. Kubernetes cluster setup (one-time)

### 7.1 Provision

Create a cluster on your provider (we use Vultr VKE, 3 × 2CPU/4GB nodes). Download the kubeconfig:

```bash
mkdir -p ~/.kube
# Append the new cluster to your existing kubeconfig:
KUBECONFIG=~/.kube/config:~/Downloads/vke-cluster.yaml \
  kubectl config view --flatten > /tmp/merged && mv /tmp/merged ~/.kube/config
kubectl config use-context <new-context-name>
kubectl get nodes   # verify
```

### 7.2 Install ingress-nginx

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/cloud/deploy.yaml
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx --timeout=120s
```

Get the external LoadBalancer IP — you'll use this for DNS:
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
# NAME                       TYPE           EXTERNAL-IP
# ingress-nginx-controller   LoadBalancer   139.84.143.136
```

### 7.3 Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.yaml
kubectl rollout status deployment/cert-manager         -n cert-manager --timeout=120s
kubectl rollout status deployment/cert-manager-webhook -n cert-manager --timeout=120s
```

### 7.4 CoreDNS tweak (Vultr-specific — may apply to other providers too)

The stock Vultr CoreDNS config uses the node's `/etc/resolv.conf` as upstream and caches NXDOMAIN for 30 minutes. This bites you the first time cert-manager tries to self-check the ACME HTTP-01 challenge right after creating a DNS record. Switch to public resolvers and reduce the cache:

```bash
kubectl patch configmap coredns -n kube-system --type merge -p '{"data":{"Corefile":".:53 {\n    errors\n    health {\n      lameduck 5s\n    }\n    ready\n    kubernetes cluster.local in-addr.arpa ip6.arpa {\n      fallthrough in-addr.arpa ip6.arpa\n    }\n    prometheus :9153\n    forward . 1.1.1.1 8.8.8.8 {\n      max_concurrent 1000\n    }\n    cache 30\n    loop\n    reload\n    loadbalance\n}\n"}}'
kubectl rollout restart deployment/coredns -n kube-system
```

### 7.5 DNS records (Cloudflare)

| Type | Name       | Value              | Proxy status          | Why                                                              |
| ---- | ---------- | ------------------ | --------------------- | ---------------------------------------------------------------- |
| A    | `dev-api`  | `<ingress IP>`     | **Proxied** (orange)  | Regular HTTP, Cloudflare CDN / WAF is fine                       |
| A    | `dev-call` | `<ingress IP>`     | **DNS only** (grey)   | WebSockets; Cloudflare free/pro plan has 100s idle timeout which kills live voice calls |

After DNS propagates (a few minutes), cert-manager will automatically issue Let's Encrypt certs via the HTTP-01 challenge.

### 7.6 Create the namespace secrets

These are referenced by `deployment.yaml` / `call-deployment.yaml` via `envFrom` / `secretKeyRef`.

```bash
# Docker Hub pull secret (for pulling developer390/tone from private pulls, if any)
kubectl create secret docker-registry dockerhub-auth \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username='<docker-hub-user>' \
  --docker-password='<docker-hub-pat>' \
  -n dev

# Infisical credentials (the app pulls the rest of its config from Infisical at startup)
kubectl create secret generic infisical-credentials \
  --from-literal=token='<infisical-machine-identity-token>' \
  --from-literal=project_id='<infisical-project-id>' \
  -n dev
```

---

## 8. Kubernetes manifests reference

All in `build/kubernetes/dev/`:

| File                       | Resource                     | Notes                                                                      |
| -------------------------- | ---------------------------- | -------------------------------------------------------------------------- |
| `deployment.yaml`          | `tone-api-deployment`        | 2 replicas, image `:${IMAGE_TAG}` (CI substitutes), port 8000              |
| `service.yaml`             | `tone-api-service`           | ClusterIP, port 80 → 8000                                                  |
| `ingress.yaml`             | `tone-api-ingress`           | Host `dev-api.trytone.ai`, TLS via `tone-api-certificate`                  |
| `certificate.yaml`         | cert-manager `Certificate`   | TLS cert for `dev-api.trytone.ai`, ACME HTTP-01                            |
| `call-deployment.yaml`     | `tone-call-worker`           | 2 replicas, port 8080, uvicorn `--timeout-keep-alive 3600`, preStop drain  |
| `call-service.yaml`        | `tone-call-service`          | ClusterIP, port 80 → 8080                                                  |
| `call-ingress.yaml`        | `tone-call-ingress`          | Host `dev-call.trytone.ai`, **3600s proxy timeouts**, websocket-services   |
| `call-certificate.yaml`    | cert-manager `Certificate`   | TLS cert for `dev-call.trytone.ai`                                         |
| `call-pdb.yaml`            | `PodDisruptionBudget`        | `maxUnavailable: 1` — never evict both call pods at once                   |
| `letsencrypt-prod.yaml`    | `ClusterIssuer`              | Let's Encrypt production ACME endpoint                                     |

### 8.1 Call-worker ingress — critical annotations

```yaml
nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
nginx.ingress.kubernetes.io/proxy-connect-timeout: "10"
nginx.ingress.kubernetes.io/websocket-services: "tone-call-service"
nginx.ingress.kubernetes.io/proxy-http-version: "1.1"
```

**Do NOT use** `nginx.ingress.kubernetes.io/configuration-snippet` — it's blocked by default in stock ingress-nginx installs and applying a manifest that uses it will be rejected by the admission webhook.

### 8.2 Long-lived WebSocket timeout summary (4 layers, all must be covered)

| Layer            | Where                                    | Setting                                              |
| ---------------- | ---------------------------------------- | ---------------------------------------------------- |
| Uvicorn          | `call-deployment.yaml` CMD               | `--timeout-keep-alive 3600`                          |
| K8s pod          | `call-deployment.yaml`                   | `terminationGracePeriodSeconds: 300`                 |
| Ingress-nginx    | `call-ingress.yaml` annotations          | `proxy-read-timeout: 3600`, `proxy-send-timeout: 3600` |
| Cloudflare       | Cloudflare dashboard                     | **DNS only** (grey cloud) on `dev-call`              |

---

## 9. First-time deployment checklist

```bash
# 0. Make sure kubeconfig is pointing to the right cluster
kubectl config current-context
kubectl get nodes

# 1. Cluster prerequisites (only once per cluster)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/cloud/deploy.yaml
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.1/cert-manager.yaml
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx --timeout=120s
kubectl rollout status deployment/cert-manager             -n cert-manager --timeout=120s
kubectl rollout status deployment/cert-manager-webhook     -n cert-manager --timeout=120s

# 2. Apply CoreDNS fix (section 7.4)

# 3. Create namespace + pull secrets + runtime secrets (section 7.6)
kubectl create namespace dev
kubectl create secret docker-registry dockerhub-auth      ... -n dev
kubectl create secret generic          infisical-credentials ... -n dev

# 4. Set up DNS in Cloudflare (section 7.5) — wait a few min for propagation

# 5. Push to dev branch — GitHub Actions does the rest
cd ~/path/to/tone
git push origin dev

# 6. Watch the rollout
kubectl get pods -n dev -w

# 7. Verify certs got issued
kubectl get certificate -n dev
# Both should show READY=True within ~2 min of DNS being live
```

---

## 10. Verifying a deployment

```bash
# HTTP health
curl -sf https://dev-api.trytone.ai/health
curl -sf https://dev-call.trytone.ai/health
curl -sf https://dev-call.trytone.ai/ready

# WebSocket handshake (installs `websockets` if missing)
pip install websockets
python3 -c "
import asyncio, websockets
async def t():
    async with websockets.connect('wss://dev-call.trytone.ai/ws', open_timeout=10) as ws:
        print('OK', ws.state)
asyncio.run(t())
"
```

### Simulating a real Twilio Media Stream call

We have a script at `/tmp/ws-test/twilio_sim.py` (reproduced in `docs/twilio_sim.py` if you want to check it in) that sends the exact frame sequence Twilio sends:

1. `connected` → `start` (with `streamSid`, `callSid`, `customParameters` containing `to`/`from`)
2. Continuous `media` events with base64 mu-law audio every 20ms
3. `stop`

```bash
# One simulated call
python3 twilio_sim.py --duration 10 --to "+15551234567" --from "+15559876543"

# 10 concurrent simulated calls (load test)
python3 twilio_sim.py --concurrent 10 --duration 30
```

---

## 11. Monitoring live connections

```bash
# Live logs from all call-worker replicas (filter noise)
kubectl logs -n dev -l app=tone-call-worker -f --prefix --tail=0 \
  | grep -v -E "GET /(health|ready)"

# Live resource usage
watch -n 2 'kubectl top pods -n dev -l app=tone-call-worker'

# Ingress access log filtered to call host
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller -f --tail=0 \
  | grep dev-call.trytone.ai

# Pod counts
kubectl get pods -n dev -l app=tone-call-worker -o wide

# Describe a stuck pod
kubectl describe pod <pod-name> -n dev
```

---

## 12. Common failures and fixes

| Symptom                                                                       | Cause                                                                 | Fix                                                                                      |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| CI: `pipecat is not a valid editable requirement`                             | Old `requirements.txt` with `-e ./pipecat`                            | Replace with `tone-pipecat==<version>` and configure Cloudsmith index                    |
| CI: `ERROR: No matching distribution found for tone-pipecat`                  | `PIP_EXTRA_INDEX_URL` secret missing or workflow doesn't pass it      | Add the GH secret and the `secrets: pip_extra_index=...` block in `docker/build-push-action` |
| CI: `Could not find version satisfying tone-pipecat==0.0.74+dev.*`            | PEP 440 doesn't allow `*` in local version segments                   | Pin exact version: `tone-pipecat==0.0.74+dev.5`                                          |
| Pod: `libxcb.so.1: cannot open shared object file`                            | Docker image missing OpenCV runtime libs                              | Add `libxcb1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1` to apt-get install         |
| Pod: `PackageNotFoundError: No package metadata was found for pipecat-ai`     | `pipecat/__init__.py` hard-codes lookup to old name                   | Fix the fork's `__init__.py` to use `tone-pipecat` first with a fallback                 |
| Pod: `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL`           | `DATABASE_URL` is empty (Infisical token invalid or project_id wrong) | Recreate `infisical-credentials` secret with valid token/project_id and restart rollout  |
| Pod: `cryptography.fernet.InvalidToken`                                       | `ENCRYPTION_KEY` in Infisical doesn't match the key used to encrypt DB rows (Twilio creds, API keys) | Either restore the old key or re-encrypt the DB rows  |
| cert-manager: Certificate stuck `READY=False`                                 | CoreDNS cached NXDOMAIN before DNS was set up                         | Apply CoreDNS fix (section 7.4), then `kubectl delete certificate <name> -n dev` + re-apply |
| Ingress: admission webhook rejects `configuration-snippet`                    | Annotation disabled by default in stock ingress-nginx                 | Remove the snippet, use standard `websocket-services` + `proxy-http-version: "1.1"`      |
| CI rollout step times out after 180s                                          | Call-worker has `terminationGracePeriodSeconds: 300`, so rolling update > 180s | Either bump the `--timeout` in the workflow, or just ignore — the rollout still completes in the cluster |
| WebSocket drops at ~100s with no error                                        | Cloudflare free/pro idle timeout on proxied records                   | Switch DNS record to **grey cloud** (DNS only) for the call host                         |

---

## 13. The dev→prod flow (for reference)

This doc only covers `dev`. When you add `staging` or `prod`:

1. Create `build/kubernetes/staging/` (or `prod/`) with the same 10 manifests, different hostnames and replica counts
2. Add a `.github/workflows/staging.yaml` that triggers on a different branch (e.g. `staging`) and applies the staging directory
3. Use separate Cloudflare subdomains (`staging-api.trytone.ai`, `staging-call.trytone.ai`)
4. Use separate Infisical environments (`staging`, `prod`) — the app already honors `INFISICAL_ENV`
5. Consider a separate `ENCRYPTION_KEY` per environment — rotating this is painful, so decide upfront

---

## 14. Quick cheat-sheet

| Task                                           | Command                                                                              |
| ---------------------------------------------- | ------------------------------------------------------------------------------------ |
| Deploy latest `dev`                            | `git push origin dev`                                                                |
| Trigger redeploy without code change           | `git commit --allow-empty -m 'redeploy' && git push`                                 |
| Watch CI run                                   | `gh run watch $(gh run list -b dev -L 1 --json databaseId -q '.[0].databaseId')`     |
| Force pod restart (same image)                 | `kubectl rollout restart deployment/tone-api-deployment -n dev`                      |
| Tail logs                                      | `kubectl logs -n dev -l app=tone-call-worker -f`                                     |
| Check cert status                              | `kubectl get certificate -n dev`                                                     |
| Bump `tone-pipecat` after a fork change        | Push to `tonehq/pipecat dev` → wait for `publish-cloudsmith` → update `requirements.txt` pin in `tonehq/tone` → push to `tonehq/tone dev` |
| Update from upstream pipecat                   | `git fetch upstream && git merge upstream/main` on `main`, then merge `main` into `dev` in the fork (preserve `pyproject.toml` name and `__init__.py` version lookup) |
