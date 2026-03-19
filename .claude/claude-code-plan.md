# Claude Code Plan: Setup Tone Voice Platform on Kubernetes

## Objective
Deploy the Tone platform as two workloads (API server + Call server) in a single Kubernetes namespace on an existing cluster. Same Docker image, different startup commands and resource profiles. The Call server handles live Twilio WebSocket voice calls and needs 3600s timeouts, capacity-aware readiness, and graceful drain.

## What You Have Access To
- The Tone GitHub repo (cloned locally)
- kubectl CLI configured with cluster access
- The kubernetes/ folder with manifest templates (already in the repo)
- The existing Docker image `developer390/clickshow-api` on Docker Hub

## Important Context
- All manifest files use `${PLACEHOLDER}` syntax. You must sed-replace these before applying.
- The Call server uses the SAME Docker image as the API server — only the uvicorn startup command differs.
- The Call ingress MUST have 3600 second proxy-read-timeout and proxy-send-timeout annotations. Without this, nginx kills WebSocket connections after 60 seconds and every voice call drops after 1 minute. This is the single most critical config.
- The Call deployment runs 1 uvicorn worker (not 4 like API) because call concurrency is managed via asyncio within a single process, and the /ready endpoint tracks active_calls count — this only works correctly with a single worker.

---

## STEP 1: Discover cluster and gather information from user

### 1.1 List available kubectl contexts
```bash
kubectl config get-contexts
```
Present the output to the user. Ask them:
- "Which kubectl context should I use for the dev deployment?"
- Wait for their answer. Then switch to it:
```bash
kubectl config use-context <their-chosen-context>
```

### 1.2 Verify cluster connectivity
```bash
kubectl cluster-info
kubectl get nodes
```
If this fails, STOP and tell the user their kubeconfig is not working.

### 1.3 Check if nginx-ingress is installed
```bash
kubectl get ingressclass
kubectl get pods -A | grep -i nginx-ingress
```
If no ingress controller is found:
- Tell the user "No nginx-ingress controller found. I need to install one. Should I proceed?"
- If yes, install it:
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/cloud/deploy.yaml
```
- Wait for it to be ready:
```bash
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
```

### 1.4 Check if cert-manager is installed (for TLS)
```bash
kubectl get pods -A | grep cert-manager
```
If not installed, note this for the user: "cert-manager is not installed. I'll create the ingress without TLS for now. You can add TLS later."

### 1.5 Ask the user for environment details
Ask the user these questions (one by one, wait for each answer):

1. "What namespace should I use?" (suggest: `dev`)
2. "What hostname for the API ingress?" (suggest: `dev-api.tone.example.com` — they need to provide their real domain)
3. "What hostname for the Call ingress?" (suggest: `dev-call.tone.example.com` — they need to provide their real domain)
4. "What Docker image tag should I deploy?" 
   - Help them find it: `kubectl get deployment -A -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'`
   - Or suggest they use: `latest` or a specific git SHA
5. "Do you already have a secret called `tone-secrets` in this namespace, or should I help you create one?"

### 1.6 Check for existing resources in the target namespace
```bash
kubectl get all -n <namespace> 2>/dev/null
kubectl get ingress -n <namespace> 2>/dev/null
kubectl get secrets -n <namespace> 2>/dev/null
```
Report what already exists. If there are existing deployments, ask: "I see existing resources. Should I proceed? This will create new deployments alongside them."

**STOP. Confirm all gathered values with the user before proceeding:**
```
Cluster context: <context>
Namespace: <namespace>
API hostname: <api-host>
Call hostname: <call-host>
Image tag: <tag>
```
"Does this look correct? Should I proceed?"

---

## STEP 2: Prepare the manifests

### 2.1 Locate the kubernetes/ directory in the repo
```bash
ls kubernetes/
```
Verify these files exist:
- namespace.yaml
- api-deployment.yaml
- api-service.yaml
- api-ingress.yaml
- call-deployment.yaml
- call-service.yaml
- call-ingress.yaml
- call-pdb.yaml
- deploy.sh
- envs/dev.env

If the kubernetes/ directory doesn't exist or is missing files, STOP and tell the user: "The kubernetes/ manifest files are not in the repo. Please add them first."

### 2.2 Create a working copy and substitute placeholders

```bash
# Create temp working directory
WORK_DIR=$(mktemp -d)
echo "Working directory: $WORK_DIR"

# Copy all manifests
cp kubernetes/*.yaml "$WORK_DIR/"

# Substitute all placeholders with the values gathered in Step 1
NAMESPACE="<namespace from step 1>"
IMAGE_TAG="<tag from step 1>"
API_HOST="<api host from step 1>"
CALL_HOST="<call host from step 1>"
API_REPLICAS="2"
CALL_REPLICAS="2"

for f in "$WORK_DIR"/*.yaml; do
  sed -i "s|\${NAMESPACE}|${NAMESPACE}|g" "$f"
  sed -i "s|\${IMAGE_TAG}|${IMAGE_TAG}|g" "$f"
  sed -i "s|\${API_HOST}|${API_HOST}|g" "$f"
  sed -i "s|\${CALL_HOST}|${CALL_HOST}|g" "$f"
  sed -i "s|\${API_REPLICAS}|${API_REPLICAS}|g" "$f"
  sed -i "s|\${CALL_REPLICAS}|${CALL_REPLICAS}|g" "$f"
done
```

### 2.3 Verify the substituted manifests look correct
```bash
echo "=== Namespace ==="
cat "$WORK_DIR/namespace.yaml"

echo "=== API Deployment (image line) ==="
grep "image:" "$WORK_DIR/api-deployment.yaml"

echo "=== Call Deployment (image line) ==="
grep "image:" "$WORK_DIR/call-deployment.yaml"

echo "=== API Ingress (host) ==="
grep "host:" "$WORK_DIR/api-ingress.yaml"

echo "=== Call Ingress (host + timeouts) ==="
grep -E "host:|proxy-read-timeout|proxy-send-timeout" "$WORK_DIR/call-ingress.yaml"
```

Show the output to the user. Confirm no `${...}` placeholders remain:
```bash
grep -r '${' "$WORK_DIR/" && echo "WARNING: Unsubstituted placeholders found!" || echo "All placeholders substituted."
```

**STOP. Show the user the key values (image, hosts, timeouts) and ask "Ready to apply?"**

---

## STEP 3: Create namespace and secrets

### 3.1 Create the namespace
```bash
kubectl apply -f "$WORK_DIR/namespace.yaml"
kubectl get namespace $NAMESPACE
```

### 3.2 Create secrets

If the user said they need secrets created (from Step 1.5):

Ask the user for each value one at a time:
1. "What is your DATABASE_URL? (e.g. postgresql://user:pass@host:5432/dbname)"
2. "What is your DEEPGRAM_API_KEY?"
3. "What is your OPENAI_API_KEY?"
4. "What is your CARTESIA_API_KEY?"
5. "What is your TWILIO_ACCOUNT_SID?"
6. "What is your TWILIO_AUTH_TOKEN?"
7. "Any other env vars your app needs? (enter as KEY=VALUE, or 'none')"

Then create the secret:
```bash
kubectl create secret generic tone-secrets -n $NAMESPACE \
  --from-literal=DATABASE_URL='<value>' \
  --from-literal=DEEPGRAM_API_KEY='<value>' \
  --from-literal=OPENAI_API_KEY='<value>' \
  --from-literal=CARTESIA_API_KEY='<value>' \
  --from-literal=TWILIO_ACCOUNT_SID='<value>' \
  --from-literal=TWILIO_AUTH_TOKEN='<value>' \
  --dry-run=client -o yaml | kubectl apply -f -
```

Verify:
```bash
kubectl get secret tone-secrets -n $NAMESPACE
```

If the user already has secrets, verify they exist:
```bash
kubectl get secret tone-secrets -n $NAMESPACE
```
If not found, STOP and tell the user the deployments will fail without this secret.

---

## STEP 4: Deploy the API workload

### 4.1 Apply API manifests in order

```bash
echo "Deploying API service..."
kubectl apply -f "$WORK_DIR/api-service.yaml"

echo "Deploying API deployment..."
kubectl apply -f "$WORK_DIR/api-deployment.yaml"

echo "Deploying API ingress..."
kubectl apply -f "$WORK_DIR/api-ingress.yaml"
```

### 4.2 Wait for API pods to be ready

```bash
echo "Waiting for API rollout..."
kubectl rollout status deployment/tone-api -n $NAMESPACE --timeout=180s
```

If this times out, debug:
```bash
kubectl get pods -n $NAMESPACE -l app=tone-api
kubectl describe pods -n $NAMESPACE -l app=tone-api
kubectl logs -n $NAMESPACE -l app=tone-api --tail=30
```
Common failures:
- ImagePullBackOff → image tag is wrong, run: `kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10`
- CrashLoopBackOff → check logs, likely missing env vars or bad startup command
- Pending → not enough resources, check: `kubectl describe pod -n $NAMESPACE -l app=tone-api | grep -A5 Events`

### 4.3 Verify API is healthy

```bash
kubectl exec -n $NAMESPACE deploy/tone-api -- curl -sf http://localhost:8000/health
```

Expected output: `{"status": "ok", ...}`

Show the user: "API deployment is running and healthy."

---

## STEP 5: Deploy the Call workload

### 5.1 Apply Call manifests in order

```bash
echo "Deploying Call PDB..."
kubectl apply -f "$WORK_DIR/call-pdb.yaml"

echo "Deploying Call service..."
kubectl apply -f "$WORK_DIR/call-service.yaml"

echo "Deploying Call deployment..."
kubectl apply -f "$WORK_DIR/call-deployment.yaml"

echo "Deploying Call ingress..."
kubectl apply -f "$WORK_DIR/call-ingress.yaml"
```

### 5.2 Wait for Call pods to be ready

```bash
echo "Waiting for Call rollout..."
kubectl rollout status deployment/tone-call-worker -n $NAMESPACE --timeout=180s
```

If this times out, debug the same way as API (step 4.2 but with `-l app=tone-call-worker`).

### 5.3 Verify Call is healthy

```bash
# Health check
kubectl exec -n $NAMESPACE deploy/tone-call-worker -- curl -sf http://localhost:8080/health

# Readiness check (should show ready: true, active_calls: 0)
kubectl exec -n $NAMESPACE deploy/tone-call-worker -- curl -sf http://localhost:8080/ready
```

If `/ready` returns a 404, it means the /ready endpoint hasn't been added to main_ee.py yet. Tell the user:
"The /ready endpoint doesn't exist yet. The Call deployment is running but capacity-aware routing won't work until you add the /ready and /drain endpoints to main_ee.py. The deployment will still function — Kubernetes will just treat it as always-ready. Do you want me to add these endpoints now?"

If yes, follow the code changes in the execution plan (add _active_calls counter, /ready, /drain endpoints, wrap /ws handler).

---

## STEP 6: Verify the complete setup

### 6.1 Show all resources

```bash
echo "============================================"
echo "Deployment summary for namespace: $NAMESPACE"
echo "============================================"

echo ""
echo "--- Pods ---"
kubectl get pods -n $NAMESPACE -o wide

echo ""
echo "--- Services ---"
kubectl get services -n $NAMESPACE

echo ""
echo "--- Ingresses ---"
kubectl get ingress -n $NAMESPACE

echo ""
echo "--- PDB ---"
kubectl get pdb -n $NAMESPACE

echo ""
echo "--- Secrets ---"
kubectl get secrets -n $NAMESPACE
```

### 6.2 Verify ingress details (CRITICAL — check the timeouts)

```bash
echo "--- API Ingress annotations ---"
kubectl get ingress tone-api-ingress -n $NAMESPACE -o jsonpath='{.metadata.annotations}' | python3 -m json.tool 2>/dev/null || kubectl get ingress tone-api-ingress -n $NAMESPACE -o yaml | grep -A2 annotations

echo ""
echo "--- Call Ingress annotations ---"
kubectl get ingress tone-call-ingress -n $NAMESPACE -o jsonpath='{.metadata.annotations}' | python3 -m json.tool 2>/dev/null || kubectl get ingress tone-call-ingress -n $NAMESPACE -o yaml | grep -A5 annotations
```

Verify the Call ingress has:
- `nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"`
- `nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"`

If these are missing, the deployment is BROKEN for voice calls. Fix immediately.

### 6.3 Test internal service connectivity

```bash
# API via service
kubectl run curl-test --rm -it --restart=Never --image=curlimages/curl -n $NAMESPACE -- \
  curl -sf http://tone-api-service/health

# Call via service
kubectl run curl-test2 --rm -it --restart=Never --image=curlimages/curl -n $NAMESPACE -- \
  curl -sf http://tone-call-service/health
```

### 6.4 Test external connectivity (if DNS is configured)

```bash
# API
curl -sf https://$API_HOST/health

# Call
curl -sf https://$CALL_HOST/health
curl -sf https://$CALL_HOST/ready
```

If DNS is not configured yet, test with port-forwarding:
```bash
# API
kubectl port-forward -n $NAMESPACE svc/tone-api-service 8000:80 &
curl -sf http://localhost:8000/health
kill %1

# Call
kubectl port-forward -n $NAMESPACE svc/tone-call-service 8080:80 &
curl -sf http://localhost:8080/health
curl -sf http://localhost:8080/ready
kill %1
```

### 6.5 Test WebSocket connectivity on Call server

```bash
kubectl port-forward -n $NAMESPACE svc/tone-call-service 8080:80 &

# If wscat is available:
echo "Testing WebSocket connection to /ws..."
timeout 5 wscat -c ws://localhost:8080/ws 2>&1 || echo "WebSocket connected (timed out waiting for Twilio messages, which is expected)"

kill %1
```

---

## STEP 7: Show the user next steps

Print this summary:

```
============================================
DEPLOYMENT COMPLETE
============================================

Namespace: $NAMESPACE

API Server:
  Pods:     kubectl get pods -n $NAMESPACE -l app=tone-api
  Health:   curl https://$API_HOST/health
  Ingress:  $API_HOST (standard 60s timeout)

Call Server:
  Pods:     kubectl get pods -n $NAMESPACE -l app=tone-call-worker
  Health:   curl https://$CALL_HOST/health
  Ready:    curl https://$CALL_HOST/ready
  Ingress:  $CALL_HOST (3600s WebSocket timeout)

NEXT STEPS:

1. DNS: Point $API_HOST and $CALL_HOST to your cluster's 
   ingress controller external IP:
   kubectl get svc -n ingress-nginx

2. TLS: Install cert-manager and uncomment the TLS sections
   in api-ingress.yaml and call-ingress.yaml, then re-apply.

3. Twilio: Create a TwiML Bin in Twilio Console:
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Connect>
       <Stream url="wss://$CALL_HOST/ws" />
     </Connect>
   </Response>
   Then assign it to your phone number.

4. Test a call: Dial your Twilio number and watch logs:
   kubectl logs -n $NAMESPACE -l app=tone-call-worker -f

USEFUL COMMANDS:
  View all:      kubectl get all -n $NAMESPACE
  API logs:      kubectl logs -n $NAMESPACE -l app=tone-api -f
  Call logs:     kubectl logs -n $NAMESPACE -l app=tone-call-worker -f
  Scale API:     kubectl scale deployment/tone-api -n $NAMESPACE --replicas=3
  Scale Call:    kubectl scale deployment/tone-call-worker -n $NAMESPACE --replicas=4
  Redeploy:      ./kubernetes/deploy.sh dev <new-image-tag>
============================================
```

---

## Error Recovery

If anything goes wrong during deployment, here's how to clean up and retry:

### Delete everything and start over
```bash
kubectl delete deployment tone-api tone-call-worker -n $NAMESPACE --ignore-not-found
kubectl delete service tone-api-service tone-call-service -n $NAMESPACE --ignore-not-found
kubectl delete ingress tone-api-ingress tone-call-ingress -n $NAMESPACE --ignore-not-found
kubectl delete pdb tone-call-pdb -n $NAMESPACE --ignore-not-found
```

### Delete just Call workload (keep API running)
```bash
kubectl delete deployment tone-call-worker -n $NAMESPACE
kubectl delete service tone-call-service -n $NAMESPACE
kubectl delete ingress tone-call-ingress -n $NAMESPACE
kubectl delete pdb tone-call-pdb -n $NAMESPACE
```

### Check events for debugging
```bash
kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -20
```
