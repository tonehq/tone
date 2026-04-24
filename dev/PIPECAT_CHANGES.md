# Pipecat Changes — Smart Turn Detection

Guide for making changes to the `tonehq/pipecat` fork, publishing a new package, and deploying it.

---

## 1. What was changed

### Problem
- STT (Speechmatics) was sending **multiple finalizations per turn** when the user paused mid-sentence
- This caused LLM and TTS to run multiple times for a single turn, increasing latency
- User-bot latency was **3.2s+ average** with spikes up to 5.7s

### Solution — Smart Turn Analyzer
Added `LocalSmartTurnAnalyzerV3` to the pipeline. It sits between STT and LLM and uses an ML model to decide if the user has **truly finished speaking** before sending text to LLM.

### Files changed in `tonehq/pipecat`

| File | Change |
|------|--------|
| `src/pipecat/audio/turn/smart_turn/local_smart_turn_v3.py` | Added `confidence_threshold` parameter (default 0.5) to make the turn completion threshold configurable |

### Files changed in `tonehq/tone`

| File | Change |
|------|--------|
| `core/services/agent_factory_service.py` | Added smart turn analyzer to the standard pipeline with `confidence_threshold=0.8` and `stop_secs=1.5` |
| `core/services/agent_factory_service.py` | Changed Speechmatics STT endpoint from EU to US (`wss://us2.rt.speechmatics.com/v2`) |
| `requirements.txt` | Updated `tone-pipecat` version |

### Configuration values

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `confidence_threshold` | 0.8 | Model must be 80%+ confident the user is done before completing the turn |
| `stop_secs` (SmartTurnParams) | 1.5 | Fallback — force-complete the turn after 1.5s of silence if model keeps saying INCOMPLETE |
| `stop_secs` (VAD) | 0.2 | Unchanged — VAD silence detection threshold |

### Results

| Metric | Before | After |
|--------|--------|-------|
| User-bot latency (avg) | 3.2s+ | ~1.5s |
| User-bot latency (range) | 1.2s–5.7s | 1.3s–1.7s |
| Duplicate STT finalizations | Yes | No |

---

## 2. How to make changes to pipecat

### 2.1 Edit the code

The pipecat fork lives at: `https://github.com/tonehq/pipecat`

If you have it locally (e.g., inside the Tone repo at `pipecat/`):

```bash
cd pipecat
# Make your changes
git add <changed-files>
git commit -m "Description of changes"
```

### 2.2 Bump the version

Update the version in `pyproject.toml`:

```toml
[project]
name = "tone-pipecat"
version = "0.0.75.dev4"   # increment this
```

Commit the version bump:

```bash
git add pyproject.toml
git commit -m "Bump version to 0.0.75.dev4"
```

### 2.3 Push to trigger package publish

```bash
git push origin main
```

This triggers the `publish-cloudsmith` GitHub Action which:
1. Builds the wheel and sdist
2. Uploads to Cloudsmith (`tonehq/tone` private PyPI)

### 2.4 Verify the publish

Go to: `https://github.com/tonehq/pipecat/actions`

Look for the **`publish-cloudsmith`** workflow run — it should show a green checkmark. Other workflows (tests, coverage, format) may fail — ignore those, only `publish-cloudsmith` matters.

The published version will be shown in the workflow summary (e.g., `tone-pipecat==0.0.75.dev4`).

---

## 3. How to deploy the new package

### 3.1 Update requirements.txt in Tone repo

```bash
cd /path/to/tone
# Edit requirements.txt — change the tone-pipecat version
# From: tone-pipecat==0.0.75.dev3
# To:   tone-pipecat==0.0.75.dev4
```

### 3.2 Push to deploy

```bash
git add requirements.txt
git commit -m "Bump tone-pipecat to 0.0.75.dev4"
git push origin <branch>   # e.g., dev, staging, main
```

This triggers the Tone CI/CD which rebuilds the Docker image with the new pipecat package and deploys to Kubernetes.

### 3.3 Verify deployment

```bash
# Check pods are running
kubectl get pods -n <namespace>

# Check logs for the new version
kubectl logs -n <namespace> <pod-name> | grep "Pipecat"
# Should show: Pipecat 0.0.75.dev4
```

---

## 4. Summary — two pushes, two CI runs

```
1. Push to tonehq/pipecat  -->  publish-cloudsmith  -->  new package on Cloudsmith
2. Push to tonehq/tone     -->  dev/staging CI      -->  Docker build + K8s deploy
```

Both pushes are required. The first publishes the package, the second uses it.

---

## 5. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `TypeError: BaseSmartTurn.__init__() got an unexpected keyword argument 'confidence_threshold'` | Deployed pipecat package doesn't have the change | Publish new pipecat version and update `requirements.txt` |
| `No matching distribution found for tone-pipecat==X.Y.Z` | Version doesn't exist on Cloudsmith | Check `publish-cloudsmith` workflow succeeded, verify exact version string |
| Smart turn always hitting `stop_secs` fallback | `confidence_threshold` too high for the use case | Lower `confidence_threshold` (e.g., 0.7) or increase `stop_secs` |
| Smart turn completing too early on mid-sentence pauses | `confidence_threshold` too low | Increase `confidence_threshold` (e.g., 0.85) |
