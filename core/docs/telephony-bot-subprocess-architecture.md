# Telephony Bot: Subprocess Isolation Architecture

## 1. High-Level Overview

Tone handles incoming phone calls by routing them through a voice AI pipeline (STT → LLM → TTS). Each call connects via WebSocket from a telephony provider (Twilio, Telnyx, Exotel, or Plivo).

**Previous design:** Each call ran as an async coroutine inside the main process. A crash in one call could destabilize the entire server.

**Current design:** Each call spawns a **separate OS process**. The main process acts as a thin WebSocket proxy between the telephony provider and the subprocess. This isolates failures, simplifies resource cleanup, and improves stability under load.

The feature is toggled via `USE_SUBPROCESS_BOT=true` (defaults to `false` for backward compatibility).

---

## 2. Architecture Diagram

```
┌──────────────────────┐
│  Telephony Provider   │
│  (Twilio/Telnyx/etc)  │
└──────────┬───────────┘
           │ WebSocket (audio + control frames)
           ▼
┌──────────────────────────────────────────────────┐
│  Main Process (pipecat/runner/run.py)             │
│                                                   │
│  1. Accept WebSocket on /ws                       │
│  2. Identify agent by phone number                │
│  3. Spawn subprocess (bot_worker.py)              │
│  4. Proxy WebSocket ↔ subprocess bidirectionally  │
└──────────┬───────────────────────────────────────┘
           │ Local WebSocket (127.0.0.1:{port}/ws)
           ▼
┌──────────────────────────────────────────────────┐
│  Subprocess (core/bot_worker.py)                  │
│                                                   │
│  - Runs FastAPI + uvicorn on a random local port  │
│  - Loads agent config from DB                     │
│  - Executes voice pipeline: STT → LLM → TTS      │
│  - Sends/receives audio via local WebSocket       │
└──────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Flow

### Incoming Call

1. Telephony provider sends a POST webhook to `/` — server responds with XML pointing the provider to `wss://{host}/ws`.
2. Provider opens a WebSocket to `/ws`.
3. Main process accepts the WebSocket and reads the first 2 messages to auto-detect the provider type (Twilio, Telnyx, etc.) and extract call metadata.

### Agent Resolution

4. `AgentRunnerService.resolve_agent_for_incoming_call()` looks up the destination phone number in the DB and resolves the matching Agent.

### Subprocess Launch

5. `SubprocessBotManager.launch()` finds a free local port and spawns:
   ```
   python -m core.bot_worker --agent_id <uuid> --transport_type <provider> --call_data <json> --port <port>
   ```
6. The subprocess starts a local FastAPI/uvicorn server and prints `WORKER_READY:{port}` to stdout.
7. The main process reads this signal (timeout: 30s) to confirm the subprocess is ready.

### WebSocket Proxy

8. Main process connects to `ws://127.0.0.1:{port}/ws` as a WebSocket client.
9. Two concurrent tasks forward frames bidirectionally:
   - **telephony → subprocess**: Audio and control frames from the provider
   - **subprocess → telephony**: Processed audio and responses back to the provider

### Bot Execution (inside subprocess)

10. On WebSocket connection, the subprocess loads the Agent from the DB, creates the appropriate serializer for the provider, and builds the voice pipeline.
11. The pipeline processes audio: **STT** (speech-to-text) → **LLM** (language model) → **TTS** (text-to-speech).
12. Responses flow back through the WebSocket proxy to the telephony provider.

### Call Termination

13. When either side closes the WebSocket, the proxy detects it and cancels the other direction.
14. The subprocess is terminated (SIGTERM → wait 5s → SIGKILL if needed).
15. All resources are cleaned up.

---

## 4. Key Components

### `_run_telephony_bot` (pipecat/runner/run.py)

The decision point. After resolving the agent, it checks `USE_SUBPROCESS_BOT`:
- **true** → delegates to `SubprocessBotManager.launch()`
- **false** → runs the bot in-process as before

If subprocess launch fails, it falls back to in-process execution.

### `SubprocessBotManager` (core/services/subprocess_bot_manager.py)

Manages the full subprocess lifecycle:
- `launch()` — orchestrates spawn → ready wait → proxy → cleanup
- `_spawn_worker()` — creates the subprocess via `asyncio.create_subprocess_exec`
- `_wait_for_ready()` — reads stdout for the `WORKER_READY` signal
- `_proxy_websocket()` — runs bidirectional frame forwarding
- `_cleanup()` — terminates the subprocess gracefully

### `bot_worker.py` (core/bot_worker.py)

The subprocess entry point:
- Parses CLI args (`--agent_id`, `--transport_type`, `--call_data`, `--port`)
- Starts a local FastAPI app with a `/ws` endpoint
- On connection: loads the Agent, detaches it from the DB session, and calls `bot()`
- Signals readiness via `WORKER_READY:{port}` on stdout

### WebSocket Proxy

Two async tasks inside `_proxy_websocket()`:
- `telephony_to_subprocess()` — forwards text/binary frames from provider to subprocess
- `subprocess_to_telephony()` — forwards frames from subprocess back to provider
- `_drain_stdout()` — continuously reads subprocess stdout to prevent pipe buffer deadlock

---

## 5. Data Flow

| Data | From | To | Format |
|------|------|----|--------|
| `agent_id` | Main process | Subprocess | CLI argument (UUID string) |
| `transport_type` | Main process | Subprocess | CLI argument (`twilio`, `telnyx`, etc.) |
| `call_data` | Main process | Subprocess | CLI argument (JSON string) |
| Audio frames (inbound) | Telephony provider | Subprocess | Binary WebSocket frames |
| Control messages | Telephony provider | Subprocess | Text/JSON WebSocket frames |
| Audio frames (outbound) | Subprocess | Telephony provider | Binary WebSocket frames |
| Readiness signal | Subprocess | Main process | Stdout: `WORKER_READY:{port}` |

---

## 6. Process Lifecycle

```
Main Process                          Subprocess
─────────────                         ──────────
find_free_port()
spawn subprocess ──────────────────→  Start
                                      Initialize FastAPI app
                                      Start uvicorn on 127.0.0.1:{port}
                                      Print "WORKER_READY:{port}" to stdout
Read stdout, detect ready signal
Connect to ws://127.0.0.1:{port}/ws
                                      Accept WebSocket connection
                                      Load Agent from DB
                                      Build voice pipeline
Start bidirectional proxy ←─────────→ Process audio (STT → LLM → TTS)
   ...call in progress...                ...call in progress...
WebSocket closed (either side)
Cancel proxy tasks
Send SIGTERM ──────────────────────→  Receive SIGTERM, shut down
Wait 5 seconds
(if still alive) Send SIGKILL ─────→  Force killed
Log exit, cleanup complete
```

---

## 7. Why the WebSocket Proxy is Needed

WebSocket connections are file descriptors bound to a specific process. They **cannot be transferred** to a child process — the OS does not support passing an established WebSocket across process boundaries.

**Solution:** The main process keeps the telephony WebSocket open and acts as a transparent proxy. It opens a second, local WebSocket to the subprocess and forwards all frames between the two. From the subprocess's perspective, it receives a normal WebSocket connection. From the telephony provider's perspective, nothing has changed.

This keeps the subprocess code identical to the in-process code path — `bot()` receives a `WebSocketRunnerArguments` object either way.

---

## 8. Advantages

- **Fault isolation** — A crash in one call's bot (OOM, unhandled exception, segfault in a native library) does not affect the main process or other calls.
- **Clean resource cleanup** — When a subprocess exits, the OS reclaims all its memory, file descriptors, and threads automatically.
- **Scalability** — Each call gets its own process with independent CPU scheduling. No GIL contention between calls.
- **Stability** — Memory leaks in AI service clients are contained to a single call's lifetime.
- **Backward compatible** — Toggled via environment variable. The in-process path remains fully functional.

---

## 9. Edge Cases and Error Handling

### Subprocess fails to start
- `_wait_for_ready()` times out after 30 seconds and raises `RuntimeError`.
- Main process catches the error and falls back to in-process execution.

### Subprocess crashes mid-call
- The local WebSocket closes, which the proxy detects immediately.
- The other proxy direction is cancelled, the telephony WebSocket is closed, and the provider handles call teardown.
- `_cleanup()` reaps the dead process.

### Telephony WebSocket disconnects
- The `telephony_to_subprocess` task exits.
- The `subprocess_to_telephony` task is cancelled.
- The subprocess receives a WebSocket close and shuts down its pipeline.
- Main process terminates the subprocess if it doesn't exit on its own.

### Stdout pipe buffer fills up
- If the subprocess writes logs to stdout without the main process reading them, the 64KB OS pipe buffer fills and the subprocess blocks.
- `_drain_stdout()` runs continuously in the background to prevent this.

### Agent not found for phone number
- `resolve_agent_for_incoming_call()` returns `None` for the agent.
- Subprocess mode is skipped (requires a resolved agent).
- Falls back to in-process execution with default services.
