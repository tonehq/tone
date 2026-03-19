# Subprocess Bot Isolation

## What Problem Does This Solve?

By default, every telephony call (Twilio, Telnyx, Exotel, Plivo) runs inside the main server process. If one call crashes, it can affect all other active calls.

**Subprocess mode** runs each call in its own separate OS process. If one call crashes, the others keep running normally.

## How to Enable

Set this environment variable in your `.env` file:

```
USE_SUBPROCESS_BOT=true
```

Set it to `false` (or remove it) to go back to the default in-process behavior.

## How It Works

### Without Subprocess Mode (Default)

```
Twilio ──WebSocket──> Main Process
                        └── bot() runs directly here
```

The main process handles everything: accepts the WebSocket from Twilio, resolves the agent, and runs the bot pipeline — all in one process.

### With Subprocess Mode

```
Twilio ──WebSocket──> Main Process ──WebSocket (localhost)──> Subprocess
                        (proxy)                                (bot_worker.py)
```

Three things happen:

1. **Main process** accepts the Twilio WebSocket and figures out which agent to use (same as before)
2. **Main process** spawns a new Python process (`bot_worker.py`) and waits for it to be ready
3. **Main process** proxies all WebSocket messages back and forth between Twilio and the subprocess

The subprocess loads the agent from the database and runs `bot()` exactly like the normal flow — it just runs in its own isolated process.

## The Files

### `core/bot_worker.py` — The Subprocess

This is the entry point for each subprocess. It:

- Receives the agent ID, transport type, and call data as command-line arguments
- Starts a tiny local web server with a `/ws` WebSocket endpoint
- When the main process connects to `/ws`, it loads the agent from the database and runs `bot()`
- Prints `WORKER_READY:{port}` to stdout so the main process knows it's ready

### `core/services/subprocess_bot_manager.py` — The Manager

This runs in the main process and manages the subprocess lifecycle:

- **`launch()`** — The main entry point. Spawns the subprocess, waits for it, starts the proxy, and cleans up when done.
- **`_find_free_port()`** — Picks a random available port on localhost for the subprocess to listen on.
- **`_spawn_worker()`** — Starts the subprocess using `python -m core.bot_worker` with the right arguments.
- **`_wait_for_ready()`** — Reads subprocess stdout until it sees the `WORKER_READY` signal.
- **`_proxy_websocket()`** — The core logic. Runs two tasks in parallel:
  - **Telephony to Subprocess**: Reads messages from Twilio's WebSocket and forwards them to the subprocess
  - **Subprocess to Telephony**: Reads messages from the subprocess and sends them back to Twilio
- **`_cleanup()`** — Terminates the subprocess when the call ends.

### `pipecat/src/pipecat/runner/run.py` — The Toggle

The `_run_telephony_bot()` function checks the `USE_SUBPROCESS_BOT` environment variable. If `true`, it calls `SubprocessBotManager.launch()` instead of running `bot()` directly.

## Call Lifecycle

Here's what happens step by step when a call comes in with subprocess mode enabled:

```
1. Phone call arrives via Twilio
2. Twilio connects to /ws on the main process
3. Main process reads the first WebSocket messages to identify the call
4. Main process looks up the agent by phone number (agent_id=52)
5. Main process spawns: python -m core.bot_worker --agent_id 52 --port 54321 ...
6. Subprocess starts a local server on 127.0.0.1:54321
7. Subprocess prints "WORKER_READY:54321" to stdout
8. Main process connects to ws://127.0.0.1:54321/ws
9. Subprocess loads agent 52 from DB and starts the bot pipeline
10. Main process proxies audio frames: Twilio <-> Subprocess
11. Call ends → Twilio disconnects → proxy stops → subprocess is terminated
```

## Key Details

- **Only the agent ID is passed** to the subprocess (not the whole agent object). The subprocess loads the agent fresh from the database.
- **The initial WebSocket messages** (Twilio's "connected" and "start" events) are consumed by the main process to identify the call. The subprocess receives the parsed `call_data` directly, so it skips that parsing step.
- **The local WebSocket runs on 127.0.0.1** (localhost only) — it's not exposed to the network.
- **If subprocess mode fails**, it falls back to running the bot in-process (check logs for errors).

## Troubleshooting

| Symptom | Likely Cause |
|---|---|
| Subprocess errors not visible | Check that `stderr=None` in `_spawn_worker()` (not `subprocess.PIPE`) |
| Subprocess hangs/freezes | The stdout pipe buffer is full. Make sure `_drain_stdout()` task is running in `_proxy_websocket()` |
| "Agent not found" in subprocess | The `agent_id` being passed is wrong. Check `str(agent.id)` in `run.py`, not `str(agent)` |
| 6+ second delay before audio starts | The connection retry loop may be slow. Check that `CONNECT_RETRY_INTERVAL` is 0.3s |
| Call works without subprocess but not with | Compare subprocess logs to normal flow. The bot receives the same `runner_args.body` in both modes |
