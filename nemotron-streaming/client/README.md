# STT WebSocket test client

Streams a wav to the `/ws/asr` endpoint in real-time chunks and prints partial
transcripts plus timing (TTF = time-to-first-response).

## Setup (venv)

From this `client/` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
pip install -r requirements.txt
```

(In VS Code: open this folder, Cmd-Shift-P → "Python: Select Interpreter" →
pick `client/.venv`. Then the file runs with the venv automatically.)

## Get a sample wav (16 kHz mono)

```bash
curl -L -o sample.wav https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav
```

## Run

1. Port-forward the service (in a separate terminal, repo root):
   ```bash
   kubectl port-forward -n staging svc/staging-stt-nemotron-service 8000:80
   ```
2. Run the client (venv active):
   ```bash
   python test_ws.py ws://localhost:8000/ws/asr sample.wav
   # smaller chunks = lower pacing granularity:
   python test_ws.py ws://localhost:8000/ws/asr sample.wav --chunk-ms 100
   ```

Expected output:
```
--- TTF: first response at 540 ms ---
[    540 ms] {"type":"partial","text":"and so my fellow","ms":...,"ttf":true}
[   1050 ms] {"type":"partial","text":"and so my fellow americans ask not", ...}
[   2100 ms] {"type":"final","text":"...full transcript...","ms":...}
```

The first-response time is your TTF for the current (v1 buffered) server.

## Check GPU memory while streaming

In another terminal:
```bash
kubectl exec -n staging deploy/staging-stt-nemotron-deployment -- nvidia-smi
```
Look at the python process's `Memory-Usage` (~1.5–2.5 GB expected for the 0.6B model).

> Note: the v1 server re-decodes the whole buffer each tick, so per-update latency
> and VRAM grow with utterance length. True cache-aware streaming (constant
> latency/memory) is the planned next iteration.
