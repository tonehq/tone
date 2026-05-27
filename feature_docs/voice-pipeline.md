# Voice Pipeline / Bot Runtime — PRD & Implementation Spec

> Reverse-engineered from the codebase on 2026-05-27. Sections marked `_(not specified)_` or `⚠` need human review before treating as authoritative.

## 1. Overview

The **Voice Pipeline** is the runtime that actually answers calls. It is built on top of [Pipecat](https://github.com/pipecat-ai/pipecat) (a real-time AI pipeline framework — `pipecat/` in this repo is a fork at `tonehq/pipecat`), wraps it in three Tone-side layers (factory, subprocess manager, warm worker pool), and exposes it to external transports (Twilio telephony, Daily WebRTC, raw WebSocket).

At a high level, every call spawns (or grabs from the warm pool) a Python subprocess running `core/bot.py:run_bot`, which builds a Pipecat pipeline from the agent's [[agent-configs]] (LLM ↔ STT ↔ TTS), binds [[tools]] + [[mcp-servers]] + [[knowledge-base]] retrieval, and streams audio in/out over a `pipe_ipc` binary channel to the parent FastAPI process.

⚠ This feature is **architecturally complete** — warm pool, pipe IPC, subprocess isolation, full Pipecat integration with ~30 provider switches, S2S support, tool/MCP/KB binding, R2 recording — but the **entry edge has been amputated by the v2 schema migration**: `bot.py` reads agent config fields that no longer exist (`llm_metadata`, `llm_account_id`, etc.) and references `Agent.uuid` columns that aren't on the v2 model. The telephony WebSocket router is also disabled in `main.py:123`.

- **Target users** (indirect): callers (the people on the phone), agent owners (whose config drives the pipeline), operators (who monitor live calls).
- **Problem solved**: turn an agent + a phone call into a real-time conversation with sub-second latency.

Cross-links: [[agents]], [[agent-configs]], [[channels]], [[knowledge-base]], [[tools]], [[mcp-servers]], [[model-providers]], [[call-logs]].

## 2. User stories & use cases

- As a **caller** dialing into a Twilio number, I want my call routed to the right agent and answered within ~1 second.
- As an **agent owner**, I want my agent's first message played within 500ms of pickup.
- As a **tester**, I want to drive a fake call through `/ws/test` from `tools/twilio_load_test.py` without owning a real phone number.
- As an **operator**, I want a recording of every call stored in R2 with the transcript persisted to [[call-logs]].
- As an **analyst**, I want token/latency metrics on each call for cost + quality monitoring.

Typical inbound flow (Twilio):

```
Caller dials +15551234567
   ↓
Twilio webhook hits Tone /telephony/voice (TwiML)
   ↓
TwiML response: <Connect><Stream url="wss://api.tone/ws"/></Connect>
   ↓
Twilio opens WebSocket → /ws
   ↓
Warm pool spawn (or cold spawn) of bot.py subprocess
   ↓
Bot reads agent_bot_data from Redis (or DB if cache miss)
   ↓
Pipecat pipeline: TransportIn → STT → LLM → TTS → TransportOut
   ↓
Bidirectional audio streams over pipe_ipc to FastAPI process → Twilio WS
   ↓
On hangup: bot persists call row, uploads audio to R2, exits
```

## 3. Functional requirements

### Pipeline stages

```
TransportInput
    ↓
SpeechToText (Deepgram / Speechmatics / OpenAI / ...)
    ↓
CallEndDetector (heuristic for "are you still there?")
    ↓
UserContextAggregator (rolling conversation history)
    ↓
LargeLanguageModel (OpenAI / Anthropic / Groq / Google / Deepseek / ...)
    ↓  (with bound tools + MCP servers + KB retrieval)
LLMTextProcessor
    ↓
TextToSpeech (ElevenLabs / Cartesia / Deepgram / OpenAI / ...)
    ↓
TransportOutput
    ↓
AssistantContextAggregator
    ↓
MetricsCollector
    ↓
AudioBufferProcessor (records to R2)
```

For Speech-to-Speech (S2S) providers (OpenAI Realtime, Google Gemini Live, etc.), the pipeline collapses to:

```
TransportInput → S2S service → TransportOutput
```

### Other functional requirements

- **Warm pool**: `core/services/warm_worker_pool.py` keeps a small set of pre-started Python subprocesses ready. On call-start, the pool returns an idle worker; on cold-spawn miss, a new subprocess is launched. Reduces first-audio latency from ~3s to ~500ms.
- **IPC**: `core/services/pipe_ipc.py` uses a binary frame protocol (`length-prefixed | type-byte | payload`) over an OS pipe for audio + control between the FastAPI parent and the bot subprocess.
- **Agent boot data** is bulk-loaded and cached: `agent_factory_service.serialize_agent_bot_data(agent_id, transport)` joins agent + agent_config + provider/keys/voices/tools/mcp_servers/uploads in ~3 queries, decrypts API keys, and writes to Redis (`agent_bot_data:{agent_id}:{transport}`, 30 min TTL).
- **Tool binding**: at boot, `custom_tool_service.py` registers each attached tool as a Pipecat function-call schema; `document_tool_service.py` registers `read_document` if the agent has KB uploads; `mcp_tool_service.py` registers MCP tools.
- **Turn detection**: `core/services/speechmatics_stt.py` integrates a Tone-specific Speechmatics STT with `LocalSmartTurnAnalyzerV3` for low-latency turn detection.
- **Audio buffer recording**: every call's audio is captured to a buffer + uploaded to R2 at end-of-call.
- **Call log write**: on end-of-call, a `calls` row is persisted with `transcript`, `metrics`, `duration_seconds`, `status`. ⚠ Per [[dashboard]] §3, this cut-over may not be complete.

### Edge cases & failure modes ("Known fragile bits")

- **⚠ Schema drift breaks pipeline boot**: `agent_factory_service.serialize_agent_bot_data` reads `agent_config.llm_metadata` / `llm_account_id` / etc., but the v2 model declares `llm_settings` / `voice_settings` / `stt_settings` JSONB. The runtime cannot boot end-to-end against the current schema unless the legacy columns are still in place (see [[agent-configs]]).
- **⚠ `Agent.uuid` is referenced but does not exist**: `bot_worker._reconstruct_agent` and `run_bot_with_components` reference `Agent.uuid` — no such column on the v2 `Agent` model.
- **⚠ Telephony router disabled**: `main.py:123` comments out the include — `/ws` and `/ws/test` are documented in the Postman collection and tested by `test-cases/core/test_telephony.py` but not registered on the live FastAPI app. Only `core/api/v1/__pycache__/telephony.cpython-311.pyc` remains.
- **⚠ No Redis cache invalidation hook** for `agent_bot_data:*` — config / credential updates take up to 30 min to propagate to the next call. The `agent_config` upsert path *does* call `cache_delete_pattern`, but agent/tool/mcp/channel updates don't.
- **⚠ No Twilio signature verification** on the webhook entry. Anyone who can POST to `/telephony/voice` can spoof a call.
- **⚠ No resource limits** on subprocess spawn — a burst of calls could OOM the host or exhaust file descriptors. No cap, no queue, no admission control.
- **⚠ print() statements throughout** (`bot.py`, factory). Should migrate to structured `logger`.
- **⚠ No pipe IPC tests** — binary frame protocol is hand-rolled, lossy edge cases (partial reads, frame size mismatches, hung subprocess) aren't covered.
- **⚠ No warm-worker reaper** — if a worker dies on cleanup (zombie), the pool stays smaller than configured forever.
- **⚠ S2S has no automated tests** — Speech-to-Speech (OpenAI Realtime, etc.) is wired in `bot.py` but never exercised by `test_telephony.py`.
- **No `/calls/active` endpoint** — there's no way for the dashboard to enumerate live calls beyond the `dashboard/stats` count.
- **Provider failures are fatal**: if the LLM provider returns 5xx mid-call, the pipeline doesn't fail over.
- **Trace ID is not propagated to tool webhooks** — when a tool POSTs to a customer's URL, there's no way to correlate that request back to the call.
- **`SmallWebRTC` and `Daily` transports** are coded in `bot.py` but no FastAPI route wires them up.

## 4. Non-functional requirements

### Latency targets (informal)

| Stage             | Target | Notes                                          |
|-------------------|--------|------------------------------------------------|
| Subprocess spawn  | <500ms | With warm pool; cold spawn ~3s                 |
| Provider data load| <50ms  | Redis cache hit                                |
| First STT result  | <300ms | Provider-dependent                             |
| LLM TTFB          | <500ms | Streaming responses; depends on context size   |
| TTS TTFB          | <200ms | Streaming TTS                                  |
| End-to-end first audio | <1000ms | All above stacked                           |

### Concurrency model

- One Python subprocess per call (no thread-per-call). Pipecat's async event loop runs inside the subprocess.
- Warm pool keeps N idle subprocesses (configurable; default likely 2–5).
- Parent FastAPI process handles the WebSocket + spawns workers; no shared mutable state between calls.

### Other

- **Resource limits**: ⚠ none enforced (no CPU/memory cap per subprocess; no max-concurrent-calls).
- **Observability**: `trace_id` is generated at call-start and threaded through. `[TIMING]` log lines emit at each stage. Pipecat observer hooks emit metrics. `MetricsCollectorProcessor` aggregates token + latency counts per turn.
- **Fault tolerance**: subprocess isolation means one crash doesn't kill the parent. No automatic retry on subprocess crash.
- **Multi-tenancy**: each subprocess receives only its own agent's data — no cross-org leak possible (data is loaded fresh per call).
- **Security**: ⚠ no Twilio signature verification on the webhook entry; ⚠ no rate limiting.

## 5. Test cases (as-built)

⚠ **Coverage is thin**:
- `tools/twilio_load_test.py` is a manual driver (not pytest) that POSTs to `/ws/test` to simulate calls.
- `test-cases/core/test_telephony.py` smoke tests the (currently disabled) telephony router.
- No tests for: pipe IPC framing, warm-pool lifecycle, S2S, R2 recording, transcript persistence.

```
TEST: warm_pool_spawn_serves_call
  GIVEN warm pool has 1 idle worker
  WHEN  /ws WebSocket opens
  THEN  worker assigned within <500ms; pool drops to 0 then refills async

TEST: cold_spawn_when_pool_empty
  GIVEN warm pool is empty
  WHEN  /ws opens
  THEN  new Python subprocess spawned; first audio in ~3s

TEST: pipeline_serializes_agent
  GIVEN agent X with config + 2 tools + 1 MCP + 3 KB uploads
  WHEN  serialize_agent_bot_data("X", "twilio") called
  THEN  3 SQL queries; decrypted keys in payload; Redis cache warmed

TEST: cache_hit_round_trip
  GIVEN previous call warmed agent_bot_data:X:twilio
  WHEN  next call for X
  THEN  no DB hit; payload loaded from Redis in <50ms

TEST: pipe_ipc_audio_frame
  GIVEN bot subprocess running
  WHEN  parent sends [len=160 | type=0x01 (audio) | 160 bytes PCM] frame
  THEN  bot's TransportInput receives the audio chunk

TEST: cache_stale_after_agent_update    ⚠ EXPECTED TO FAIL — bug
  GIVEN cached agent_bot_data:X:twilio
  WHEN  PUT /agent/update_agent for X
  THEN  EXPECT cache invalidated; ACTUAL cache stale up to 30 min

TEST: telephony_router_404           ⚠ EXPECTED TO FAIL — router disabled
  WHEN  GET /telephony/voice
  THEN  EXPECT 200 with TwiML; ACTUAL 404 (router not mounted)

TEST: twilio_signature_verified     ⚠ EXPECTED TO FAIL — no verification
  WHEN  POST /telephony/voice with forged signature
  THEN  EXPECT 403; ACTUAL 200 (accepted)
```

## 6. Data model

**This feature does not own any tables.** It READS from many existing tables at boot and WRITES to a few at end-of-call.

### Tables READ at startup (per call)

| Table              | Used for                                                          |
|--------------------|-------------------------------------------------------------------|
| `agents`           | Resolve agent metadata, `agent_type`, `published_config_id`        |
| `agent_configs`    | LLM/STT/TTS provider + model + voice settings, prompts             |
| `phone_numbers`    | Route phone → agent (legacy `agent_channel_phone_numbers` if v1)   |
| `channels`         | Decrypt channel credentials (Twilio/Daily/etc.)                    |
| `api_keys`         | Decrypt provider API keys (LLM, STT, TTS)                          |
| `model_providers`  | Resolve provider metadata                                          |
| `models`           | Resolve model API identifier (e.g. `gpt-4o-2024-08-06`)            |
| `model_voices`     | TTS voice id                                                       |
| `model_languages`  | TTS language metadata                                              |
| `tools`            | Function-call definitions for the LLM                              |
| `agent_tools`      | Many-to-many join (which tools for this agent)                     |
| `mcp_servers`      | External MCP tool servers                                          |
| `agent_mcp_servers`| Per-agent MCP attachments                                          |
| `agent_knowledge_base` | Per-agent KB attachments                                       |
| `uploads`          | KB document metadata                                               |
| `knowledge_base_chunks` | Pipeline reads at *runtime* for cosine-distance RAG          |

### Tables WRITTEN at end-of-call

| Table     | Used for                                                          |
|-----------|-------------------------------------------------------------------|
| `calls`   | Call row with transcript + metrics + duration ⚠ wiring incomplete |
| `uploads` | `purpose='call_audio'` row pointing to R2 blob                    |

### Redis cache keys

- `agent_bot_data:{agent_id}:{transport}` — 30-minute TTL — full materialized boot payload.
- `worker_pool:idle:{transport}` — set of idle subprocess IDs.

## 7. Invocation surface (replaces "API design")

This feature is invoked via **transports**, not REST. The transports below should be registered in `main.py` for the runtime to actually answer calls.

| Method | Path                       | Status         | Purpose                                                            |
|--------|----------------------------|----------------|--------------------------------------------------------------------|
| POST   | `/telephony/voice`         | ⚠ Disabled     | Twilio webhook — returns TwiML with `<Connect><Stream url="wss://..."/></Connect>` |
| WSS    | `/ws`                      | ⚠ Disabled     | Twilio Media Streams WebSocket — bidirectional 8kHz mulaw audio    |
| WSS    | `/ws/test`                 | ⚠ Disabled     | Test/dev WebSocket — used by `tools/twilio_load_test.py`           |
| WSS    | `/daily/{room}`            | ⚠ Not wired    | Daily WebRTC transport — coded in `bot.py`, no FastAPI route       |
| WSS    | `/webrtc/{call_id}`        | ⚠ Not wired    | SmallWebRTC transport — coded in `bot.py`, no FastAPI route        |

### /ws lifecycle (Twilio Media Streams)

```
1. Twilio sends WS upgrade to /ws
2. FastAPI accepts; reads first "start" message to get call_sid + phone numbers
3. Look up agent by to_number via channels + phone_numbers
4. WarmWorkerPool.acquire(transport="twilio") → subprocess
5. Send agent_bot_data + transport config over pipe_ipc to subprocess
6. Bidirectional audio loop:
   - Twilio → parent FastAPI → pipe_ipc → bot's TransportInput
   - Bot's TransportOutput → pipe_ipc → parent → Twilio
7. On Twilio hangup or bot's CallEndDetector firing:
   - Bot flushes audio buffer to R2
   - Bot writes calls row
   - pipe_ipc closed; subprocess returned to pool (or terminated)
8. WS closed
```

### /ws/test lifecycle

Same as `/ws` but the first message includes a synthetic `agent_id` and a path to a WAV file to play instead of live mic input. Used to load-test without real telephony.

## 8. Backend implementation

### Module map

| File                                                  | Purpose                                              |
|-------------------------------------------------------|------------------------------------------------------|
| `core/bot.py`                                         | Subprocess entry; `run_bot()`, `run_bot_with_components()`, `bot_worker()` |
| `core/services/agent_factory_service.py`              | Builds Pipecat pipeline from agent + config; 30+ provider switch |
| `core/services/subprocess_bot_manager.py`             | Spawns/tracks subprocess workers                     |
| `core/services/warm_worker_pool.py`                   | Pre-warmed pool of idle subprocesses                 |
| `core/services/pipe_ipc.py`                           | Binary frame protocol over OS pipe                   |
| `core/services/bot_runner_service.py`                 | Glue between FastAPI WS handler and subprocess pool  |
| `core/services/speechmatics_stt.py`                   | Custom Speechmatics STT with `LocalSmartTurnAnalyzerV3` |
| `core/services/redis_service.py`                      | Redis client for cache + pool state                  |
| `core/services/custom_tool_service.py`                | Registers tools as Pipecat function-call schemas     |
| `core/services/document_tool_service.py`              | Registers `read_document` for KB RAG                 |
| `core/services/mcp_tool_service.py`                   | Registers MCP tools                                  |
| `core/api/v1/telephony.py`                            | Twilio webhook + `/ws` + `/ws/test` ⚠ disabled       |

### Hot-path sequence (warm pool happy case)

```
WS connect → FastAPI handler
  ↓
WarmWorkerPool.acquire(transport)  ──→  Redis SPOP "worker_pool:idle:twilio"
  ↓                                       (returns idle pid)
SubprocessBotManager.send(pid, agent_bot_data + transport_cfg via pipe_ipc)
  ↓
Subprocess wakes:
  - Reads agent_bot_data from pipe
  - Decrypts API keys (already decrypted server-side in factory)
  - Instantiates Pipecat services (LLM/STT/TTS) via agent_factory_service
  - Registers tools/MCP/KB
  - Builds Pipeline
  - Starts pipeline.run()
  ↓
Audio loop (full duplex)
  ↓
Hangup → cleanup → bot returns to warm pool or dies
```

### No Celery, no background jobs

End-of-call cleanup (R2 upload + `calls` write) happens inline in the subprocess before it exits or returns to the pool.

## 9. Frontend implementation

The voice pipeline is **server-side only** — the frontend does not directly invoke the bot. Indirect surfaces:

- [[call-logs]] `/call-history` — shows historical calls after they end.
- [[dashboard]] `/home` — shows `active_calls` count + `minutes_used`.
- "Test agent" UI: ⚠ unclear status. There may be a browser-based test page that opens a `/ws/test` WebSocket from the frontend (verify presence in `frontend/src/app/(dashboard)/agents/.../test/`).

## 10. Webhook examples & sample sequences (replaces "Postman collection")

### Twilio inbound (TwiML response — returned by `/telephony/voice`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://api.tone.dev/ws" />
  </Connect>
</Response>
```

### Twilio Media Streams: first WebSocket message

```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "streamSid": "MZ...",
    "accountSid": "AC...",
    "callSid": "CA...",
    "tracks": ["inbound"],
    "customParameters": {}
  },
  "streamSid": "MZ..."
}
```

### Subprocess launch payload (over pipe_ipc)

```json
{
  "agent_id": "550e8400-...",
  "transport": "twilio",
  "_prefetched_services": {
    "llm": {"provider": "openai", "model": "gpt-4o", "api_key": "sk-..."},
    "stt": {"provider": "deepgram", "model": "nova-2", "api_key": "..."},
    "tts": {"provider": "elevenlabs", "voice_id": "21m00Tcm4TlvDq8ikWAM", "api_key": "..."}
  },
  "system_prompt": "...",
  "first_message": "Hi! How can I help?",
  "tools": [{"name": "post_to_crm", "url": "...", "auth_config": {...}}],
  "mcp_servers": [{"url": "...", "auth_config": {...}}],
  "kb_chunks_query": "SELECT content FROM knowledge_base_chunks WHERE agent_id = ?"
}
```

### pipe_ipc frame (hex)

```
[00 00 00 A0]   ← 4-byte length prefix (160)
[01]            ← 1-byte type (audio)
[XX XX XX ... ] ← 160 bytes PCM payload
```

Types: `0x01=audio`, `0x02=text`, `0x03=control_start`, `0x04=control_hangup`, etc.

### Completed `calls` row

```sql
INSERT INTO calls (id, agent_id, channel_id, from_number, to_number, status,
                   started_at, ended_at, duration_seconds, transcript, metrics)
VALUES (gen_random_uuid(), '...', '...', '+15551234567', '+15559876543',
        'completed', '2026-05-27T10:00:00Z', '2026-05-27T10:03:45Z', 225,
        '[{"role":"agent","text":"Hi"},{"role":"user","text":"Hello"}]'::jsonb,
        '{"llm_tokens_in":412,"ttfb_ms":320}'::jsonb);
```

### /ws/test smoke command

```bash
python tools/twilio_load_test.py --agent-id 550e8400-... --wav fixtures/test.wav --ws-url ws://localhost:8000/ws/test
```

## 11. Next steps

- [ ] ⚠ **Re-enable telephony router** in `main.py:123` after reconciling the schema drift below.
- [ ] ⚠ **Reconcile [[agent-configs]] schema**: `agent_factory_service.py` reads legacy column names; v2 model declares new names. Pick one set.
- [ ] ⚠ **Drop or add `Agent.uuid`**: `bot_worker._reconstruct_agent` references it; v2 model doesn't have it.
- [ ] ⚠ **Add Twilio signature verification** to the `/telephony/voice` webhook entry.
- [ ] ⚠ **Wire cache invalidation hooks** for `agent_bot_data:*` on agent/tool/MCP/channel updates (today only `agent_config` upsert invalidates).
- [ ] ⚠ **Add resource limits**: max-concurrent-calls cap, per-subprocess memory/CPU quotas, admission control queue.
- [ ] ⚠ **Migrate `print()` → `logger`** throughout `bot.py` and `agent_factory_service.py`.
- [ ] ⚠ **Split `agent_factory_service.py`**: 898 lines is too big — break into LLM/STT/TTS factories.
- [ ] ⚠ **Add pipe IPC tests** (partial reads, frame size mismatches, hung subprocess simulation).
- [ ] ⚠ **Add a warm-worker reaper**: if a worker dies during cleanup, the pool should detect and respawn.
- [ ] ⚠ **Add `GET /calls/active`** endpoint for the dashboard to enumerate live calls.
- [ ] ⚠ **Add Daily/SmallWebRTC FastAPI routes** to expose the transports `bot.py` already supports.
- [ ] ⚠ **Add S2S tests** (OpenAI Realtime, Google Gemini Live).
- [ ] ⚠ **Propagate `trace_id` to tool webhooks** for end-to-end correlation.

## 12. Change Log

- **2026-05-27** — Initial PRD reverse-engineered from code. Flagged: (1) Schema drift breaks pipeline boot — `agent_factory_service` reads legacy column names that don't exist in v2; (2) `Agent.uuid` referenced by `bot_worker` but not on v2 model; (3) Telephony router disabled in `main.py:123` — `/ws` and `/ws/test` return 404; (4) No Twilio signature verification on webhook entry; (5) Cache invalidation hooks missing for agent/tool/MCP/channel updates (only `agent_config` invalidates); (6) No resource limits on subprocess spawn — OOM/FD-exhaustion risk under load; (7) `print()` statements throughout — should migrate to `logger`; (8) Pipe IPC binary framing has no tests; (9) No warm-worker reaper — pool can shrink permanently on cleanup death; (10) S2S has no automated tests; (11) Daily and SmallWebRTC transports coded but no FastAPI route wires them up; (12) Trace ID not propagated to tool webhook calls. Architecturally complete; entry edge amputated by v2 migration.
