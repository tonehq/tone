# Kubernetes Cluster Setup — Tone

This document is both a **runbook** and a **prompt for Claude Code**. It walks through provisioning a Kubernetes cluster for Tone and then deploying the **API** and **Call** workloads as two independent deployments. It is interactive: at each phase, ask the user the listed questions, wait for answers, and only then generate manifests / run commands.

It is designed to later be promoted into a Claude Code skill (see "Skill conversion notes" at the bottom).

---

## How to use this document (instructions to Claude)

- **Always ask before acting.** Never assume cloud provider, region, cluster name, namespace, image registry, or secrets. Ask, wait, then proceed.
- **Three phases, in order:**
  1. Cluster provisioning
  2. API deployment (`tone-api`)
  3. Call deployment (`tone-call` — the Pipecat voice workers)
- **One phase at a time.** After finishing a phase, summarize what was created and ask the user "Ready to move to the next phase?" before continuing.
- **Show, then apply.** For every manifest, print it first, ask "Apply this?", and only then run `kubectl apply`.
- **Never invent secrets.** If a secret value is needed (DB URL, JWT keys, provider API keys, Cloudsmith index URL, etc.), ask the user to provide it or to confirm an existing `Secret` name.
- **Respect existing infra.** Run `kubectl config current-context`, `kubectl get ns`, and `kubectl get deploy -A | grep tone` before creating anything that might collide.

---

## Phase 1 — Cluster provisioning

### Questions to ask first

Ask these as a single batched prompt; do not start work until all are answered.

1. **Provider** — GKE / EKS / AKS / DigitalOcean / Linode / k3s on a VM / kind (local) / existing cluster I will point you at?
2. **Cluster name** and **region/zone**?
3. **Node pool sizing** — how many nodes, what instance type? (Tone's voice workers are CPU+RAM heavy; recommend ≥ 4 vCPU / 8 GiB per node, min 2 nodes.)
4. **Kubernetes version** preference, or latest stable for the provider?
5. **Networking** — default CNI ok, or specific (Cilium, Calico)?
6. **Ingress** — NGINX ingress / Traefik / cloud LB only / Istio? Will you need WebSocket + long-lived connections? (Yes — calls use WebRTC/WebSocket, so the ingress must support this.)
7. **TLS** — cert-manager + Let's Encrypt, or BYO certificate?
8. **DNS** — what hostnames will point at the API and the call transport? (e.g. `api.tone.example.com`, `call.tone.example.com`)
9. **Container registry** — GHCR / Docker Hub / GAR / ECR / ACR? Image pull secret needed?
10. **Existing kubeconfig context** to use, or should a new one be set up?

### Actions (after answers)

1. Confirm CLI tooling is installed (`kubectl`, and provider CLI: `gcloud` / `aws` / `az` / `doctl` / `k3sup` / `kind`). If missing, print install instructions; do not auto-install.
2. Provision the cluster using the provider CLI. Print the exact command, ask to run it.
3. After cluster is up, configure kubeconfig and verify with `kubectl get nodes`.
4. Create a namespace: ask "Use namespace `tone`, or a different name?"
5. Install ingress controller and cert-manager. Print Helm commands; ask before running.
6. Create the image pull `Secret` if needed (ask for credentials interactively — never log them).
7. Create a shared `Secret` for application config:
   - Ask the user which values to inject: `DATABASE_URL`, `JWT_SECRET`, `INFISICAL_*` or `.env` contents, provider API keys.
   - Recommend a single `Secret` named `tone-config` consumed via `envFrom` by both deployments.
8. Create a `ConfigMap` for non-secret config (log level, feature flags, default org id, etc.) — ask which values.

### Done check
- `kubectl get nodes` → all Ready
- `kubectl get ns tone` exists
- Ingress controller pods Running
- cert-manager pods Running
- `tone-config` Secret exists

Ask: "Phase 1 complete. Move to API deployment?"

---

## Phase 2 — API deployment (`tone-api`)

This deploys the FastAPI backend (`main.py` / `main_ee.py`) — stateless HTTP, autoscalable.

### Questions to ask first

1. **Edition** — Core (`main.py`) or Enterprise (`main_ee.py`)?
2. **Image** — what is the full image reference? (e.g. `ghcr.io/tonehq/tone-api:<tag>`) Has it been built and pushed already, or should we build it from the repo `Dockerfile` first?
3. **Replicas** — initial replica count? (Default: 2)
4. **Resources** — CPU/memory requests and limits? (Default: 500m / 1Gi requests, 2 / 4Gi limits.)
5. **Autoscaling** — enable HPA? Min/max replicas, target CPU %?
6. **Database** — managed DB URL already in `tone-config`, or do we need to provision one?
7. **Migrations** — should I create a one-shot `Job` to run `alembic upgrade head` before rollout?
8. **Hostname** — confirm the public hostname for the API ingress.
9. **Health checks** — confirm `/health` is the liveness/readiness path (it is, in Tone today).
10. **Private PyPI** — the image already has `tone-pipecat` baked in, OR is the build going to need `PIP_EXTRA_INDEX_URL` (Cloudsmith) at build time? If the latter, confirm BuildKit secret usage as in the repo `Dockerfile`.

### Manifests to generate (in this order)

1. `Deployment` `tone-api`
   - `envFrom: [secretRef: tone-config, configMapRef: tone-config-cm]`
   - `livenessProbe` and `readinessProbe` → `GET /health`
   - `resources` from answers
   - `imagePullSecrets` if needed
2. `Service` `tone-api` — ClusterIP, port 80 → 8000
3. `Ingress` `tone-api` — host from answers, TLS via cert-manager annotation
4. `HorizontalPodAutoscaler` `tone-api` (if enabled)
5. (Optional) `Job` `tone-api-migrate` — runs `alembic upgrade head` against the same image

For each manifest: print → ask → apply → wait for rollout → verify with `kubectl rollout status` and a `curl https://<host>/health`.

### Done check
- `kubectl rollout status deploy/tone-api -n tone` → successful
- `curl https://<api-host>/health` → 200 with `deployed: true`
- HPA reporting metrics (if enabled)

Ask: "Phase 2 complete. Move to Call deployment?"

---

## Phase 3 — Call deployment (`tone-call`)

This deploys the Pipecat voice pipeline workers — long-lived, WebSocket/WebRTC, **stateful per-call**, NOT a typical stateless HTTP service.

### Important constraints to respect (ask user to confirm understanding)

- Calls hold **long-lived connections**. Pod evictions during a call drop users. Use generous `terminationGracePeriodSeconds` (≥ 300) and a `preStop` hook that drains.
- **Do not aggressively autoscale down.** HPA on call workers should scale on active-call count (custom metric) or be disabled. Default to `replicas` only.
- The call pods must be reachable for WebRTC. Either:
  - Use a transport that goes via Daily / LiveKit / Twilio (no inbound media to the cluster, simpler), OR
  - Expose UDP for direct WebRTC (requires `LoadBalancer` with UDP, host networking, or a TURN server). Ask which transport(s) are in use.
- Voice workers may need GPU? Ask. Default no.
- `PodDisruptionBudget` recommended: `minAvailable: 1`.

### Questions to ask first

1. **Transport** — Daily / LiveKit / Twilio / WebSocket / SmallWebRTC / multiple? This decides whether we need UDP exposure.
2. **Image** — same image as API, or a separate `tone-call` image? Tag?
3. **Entrypoint / command** — confirm. (Often `python -m core.bot` or a worker runner; ask which.)
4. **Replicas** — initial count. Default 2.
5. **Resources** — voice pipelines are heavy. Recommend `requests: 1 CPU / 2Gi`, `limits: 2 CPU / 4Gi`. Confirm.
6. **GPU** — needed? If yes, which node selector / toleration?
7. **Concurrency per pod** — how many simultaneous calls per worker? This drives sizing.
8. **Autoscaling** — disable, fixed replicas, or KEDA + custom metric (e.g. active calls from Prometheus)?
9. **Inbound networking** — does the call pod need to be addressable from outside the cluster directly (yes if hosting WebRTC media), or only outbound (yes if using Daily/LiveKit/Twilio)?
10. **Provider secrets** — confirm Daily/LiveKit/Twilio/STT/TTS/LLM API keys are already in `tone-config`.
11. **Metrics** — Prometheus scrape annotations? OpenTelemetry endpoint?

### Manifests to generate

1. `Deployment` `tone-call` (or `StatefulSet` if you need stable identity per worker — ask)
   - `terminationGracePeriodSeconds: 600`
   - `preStop` hook: small script that signals graceful drain (no new calls, wait for current calls to end)
   - `envFrom: tone-config` + call-specific config
   - `resources` from answers
   - `nodeSelector` / `tolerations` if GPU
2. `Service` `tone-call` — only if other in-cluster services need to reach it (often not; the API talks via the transport provider). Ask.
3. `PodDisruptionBudget` `tone-call` — `minAvailable: 1` (or more, based on replicas)
4. (Conditional) `LoadBalancer` Service or Ingress with UDP — only if direct WebRTC media into the cluster
5. (Conditional) `ScaledObject` (KEDA) if custom-metric autoscaling chosen
6. (Conditional) `ServiceMonitor` if Prometheus Operator is in use

For each manifest: print → ask → apply → verify pods Running → check logs for successful pipeline init.

### Done check
- `kubectl rollout status deploy/tone-call -n tone` → successful
- Logs show pipeline initialized and worker registered with the transport provider
- Test call placed end-to-end (ask user to do this manually and confirm)
- PDB present

Ask: "Phase 3 complete. Anything else? (Monitoring, log aggregation, GitOps, runbook docs?)"

---

## Cross-phase reminders

- After every phase, run `kubectl get all -n tone` and show the user the current state.
- Never store secrets in manifests committed to git. If user wants GitOps (Argo/Flux), recommend SealedSecrets or External Secrets Operator and ask which.
- If the user is deploying to a fresh cluster, offer to also install: `metrics-server`, `prometheus`, `loki`/`promtail`, `external-dns`. Ask before installing each.
- Document the hostnames, image tags, and secret names created — print a summary block at the end of each phase the user can paste into their internal docs.

---

## Skill conversion notes (for later)

To turn this document into a Claude Code skill:

1. Create `.claude/skills/k8s-deploy-tone/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: k8s-deploy-tone
   description: |
     Interactively provisions a Kubernetes cluster for Tone and deploys the
     API and Call workloads as separate deployments. Asks the user about
     provider, sizing, ingress, transport, and secrets before generating any
     manifests. Use when the user says "deploy tone to k8s", "set up the
     cluster", "deploy the api on kubernetes", or similar.
   ---
   ```
2. Body of `SKILL.md` = the **"How to use this document"** + **three phase sections** above, with these adaptations:
   - Replace "ask the user" prose with explicit `AskUserQuestion` invocations where multiple discrete options exist (provider, transport, ingress).
   - Add a top-level "Preflight" section that runs `kubectl config current-context`, `kubectl get ns`, `which kubectl helm` and reports findings before any questions.
   - Add a "State file" convention: write a `.tone-k8s-state.yaml` in the working directory recording answers + created resources, so re-running the skill resumes instead of restarting.
   - Add explicit refusal rules: do not run `kubectl delete`, `helm uninstall`, or any destructive op without typed user confirmation.
3. Templates: store reusable manifest templates under `.claude/skills/k8s-deploy-tone/templates/` (`deployment-api.yaml.tmpl`, `deployment-call.yaml.tmpl`, `ingress.yaml.tmpl`, `pdb.yaml.tmpl`, `hpa.yaml.tmpl`) so the skill renders them with the user's answers instead of generating from scratch each time.
4. Test the skill end-to-end against `kind` first, then a real cloud cluster, before using it on prod.
