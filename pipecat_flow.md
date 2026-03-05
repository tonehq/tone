# Pipecat Twilio Call Flow — Step by Step

This document explains what happens from the moment a Twilio call hits the `/ws` WebSocket endpoint to when audio flows back to the caller. Written in simple words with actual param structures.

---

## The Big Picture

```
Caller dials your Twilio number
  → Twilio sends HTTP webhook to your server (POST /)
  → Server returns TwiML XML telling Twilio to open a WebSocket
  → Twilio opens WebSocket to /ws
  → Server reads first 2 messages to figure out call details
  → Server looks up which AI agent handles this phone number
  → Server builds an audio pipeline: STT → LLM → TTS
  → Audio flows back and forth until the caller hangs up
```

---

## Step 1: Twilio Sends the HTTP Webhook (POST /)

When someone calls your Twilio phone number, Twilio makes an HTTP POST to your server's root `/` endpoint.

**What the server returns (XML):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://your-proxy-host/ws"></Stream>
  </Connect>
  <Pause length="40"/>
</Response>
```

This tells Twilio: "Open a WebSocket connection to `wss://your-proxy-host/ws` and stream audio through it."

**Code location:** `pipecat/src/pipecat/runner/run.py` → `_setup_telephony_routes()` → `start_call()` (line ~879)

---

## Step 2: Twilio Opens WebSocket → `/ws` Endpoint

Twilio connects to the `/ws` WebSocket endpoint. FastAPI accepts the connection.

**Code location:** `pipecat/src/pipecat/runner/run.py` → `websocket_endpoint()` (line ~896)

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await _run_telephony_bot(websocket)
```

**The `websocket` param is a FastAPI WebSocket object:**
```python
# websocket: fastapi.WebSocket
# It has methods like:
#   await websocket.accept()
#   await websocket.receive_text()  → returns a JSON string
#   await websocket.send_text(data) → sends data back to Twilio
#   await websocket.close()
```

The websocket params for each flow:

Likely websocket params for start call:

{
  "event": "start",
  "start": {
    "callSid": "CA123456789",
    "streamSid": "MZ123456789",
    "tracks": ["inbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  }
}


For media event:
{
  "event": "media",
  "streamSid": "MZ123456789",
  "media": {
    "payload": "base64_encoded_audio_here"
  }
}


For stop event:
{
  "event": "stop",
  "streamSid": "MZ123456789"
}




---

## Step 3: `_run_telephony_bot()` — Resolve the Agent

This function figures out which AI agent should handle this call.

**Code location:** `pipecat/src/pipecat/runner/run.py` → `_run_telephony_bot()` (line ~233)

```python
async def _run_telephony_bot(websocket: WebSocket):
    bot_module = _get_bot_module()   # Finds core/bot.py which has a bot() function

    # Uses BotRunnerService to figure out which agent to use
    with get_db_context() as db:
        agent, transport_type, call_data = await BotRunnerService(db).get_bot_for_incoming_call(websocket)

    body = {
        "call_data": call_data,        # Stream/call IDs from Twilio
        "transport_type": transport_type,  # "twilio"
        "agent_id": agent.id,          # DB ID of the matched agent
        "agent": agent,                # Full Agent ORM object
    }

    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
    await bot_module.bot(runner_args)
```

**`WebSocketRunnerArguments` looks like:**
```python
@dataclass
class WebSocketRunnerArguments(RunnerArguments):
    websocket: WebSocket              # The raw FastAPI WebSocket
    # Inherited from RunnerArguments:
    handle_sigint: bool = False
    handle_sigterm: bool = False
    pipeline_idle_timeout_secs: int = 300
    body: dict = {                    # The body dict we built above
        "call_data": {"stream_id": "MZ...", "call_id": "CA...", "body": {}},
        "transport_type": "twilio",
        "agent_id": 42,
        "agent": <Agent ORM object>,
    }
```

---

## Step 4: `BotRunnerService.get_bot_for_incoming_call()` — Parse Twilio Messages & Find Agent

This is the key function that reads the initial Twilio WebSocket messages and finds the right agent.

**Code location:** `core/services/bot_runner_service.py`

### Step 4a: Parse the first 2 WebSocket messages

Calls `parse_telephony_websocket(websocket)` which reads the first two messages Twilio sends:

**Message 1 — "connected" event:**
```json
{
  "event": "connected",
  "protocol": "Call",
  "version": "1.0.0"
}
```

**Message 2 — "start" event (the important one):**
```json
{
  "event": "start",
  "sequenceNumber": "1",
  "start": {
    "accountSid": "AC...",
    "streamSid": "MZ...",
    "callSid": "CA...",
    "tracks": ["inbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    },
    "customParameters": {
      "agent_id": "123",
      "any_other_param": "value"
    }
  },
  "streamSid": "MZ..."
}
```

**What `parse_telephony_websocket` returns:**
```python
transport_type = "twilio"    # Auto-detected from the message structure

call_data = {
    "stream_id": "MZ...",    # start.streamSid — identifies the media stream
    "call_id": "CA...",      # start.callSid — identifies the phone call
    "body": {                # start.customParameters — any extra params you passed
        "agent_id": "123"
    }
}
```

**How it detects "twilio":** Checks if `event == "start"` AND the message has `start.streamSid` AND `start.callSid`.

### Step 4b: Get the "to" phone number

Twilio's WebSocket messages don't include which number was dialed. So the service calls the Twilio REST API:

```python
# GET https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json
# Auth: HTTP Basic (account_sid, auth_token)
#
# Response (simplified):
{
    "from": "+15551234567",     # Caller's number
    "to": "+15559876543",       # YOUR Twilio number (the one that was dialed)
    "status": "in-progress",
    ...
}
```

### Step 4c: Look up the Agent in the database

```python
# Queries: AgentPhoneNumbers where phone_number == "+15559876543"
# Joins to Agent table to get the full agent config
# Returns: Agent ORM object (or None if no agent is assigned to this number)
```

**Final return value:**
```python
(agent, "twilio", {"stream_id": "MZ...", "call_id": "CA...", "body": {...}})
```

---

## Step 5: `bot()` in `core/bot.py` — Create the Transport

The `bot()` function receives the `runner_args` and creates the right transport.

**Code location:** `core/bot.py` → `bot()` (line ~159)

Since `runner_args` is a `WebSocketRunnerArguments`, it goes into the Twilio branch:

```python
async def bot(runner_args: RunnerArguments):
    if isinstance(runner_args, WebSocketRunnerArguments):
        body = runner_args.body or {}
        call_data = body.get("call_data")       # {"stream_id": "MZ...", "call_id": "CA..."}
        transport_type = body.get("transport_type")  # "twilio"
        agent = body.get("agent")               # Agent ORM object

        # If call_data wasn't pre-parsed, parse it now (fallback)
        if call_data is None:
            _, call_data = await parse_telephony_websocket(runner_args.websocket)

        # Create the Twilio serializer (converts between Twilio's audio format and Pipecat's)
        serializer = TwilioFrameSerializer(
            stream_sid=call_data["stream_id"],   # "MZ..."
            call_sid=call_data["call_id"],        # "CA..."
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        )

        # Create the WebSocket transport
        transport = FastAPIWebsocketTransport(
            websocket=runner_args.websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,             # Twilio doesn't use WAV headers
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
                serializer=serializer,
            ),
        )

    await run_bot(transport, runner_args)
```

**`TwilioFrameSerializer` params:**
```python
TwilioFrameSerializer(
    stream_sid="MZ...",           # Required — identifies the stream for sending audio back
    call_sid="CA...",             # Required for auto hang-up
    account_sid="AC...",          # From env var, for hang-up API call
    auth_token="abc123...",       # From env var, for hang-up API call
    # Internal defaults:
    #   twilio_sample_rate=8000   (Twilio always uses 8kHz μ-law)
    #   auto_hang_up=True         (call Twilio API to end call on EndFrame)
)
```

**`FastAPIWebsocketParams` looks like:**
```python
FastAPIWebsocketParams(
    audio_in_enabled=True,        # Accept incoming audio
    audio_out_enabled=True,       # Send outgoing audio
    add_wav_header=False,         # No WAV header (Twilio uses raw μ-law)
    vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    serializer=TwilioFrameSerializer(...),   # The codec bridge
    # Inherited defaults:
    #   audio_in_sample_rate=16000
    #   audio_out_sample_rate=16000
    #   camera_in_enabled=False
    #   camera_out_enabled=False
)
```

**`FastAPIWebsocketTransport` internally creates:**
- `FastAPIWebsocketInputTransport` — reads from WebSocket, deserializes μ-law → PCM
- `FastAPIWebsocketOutputTransport` — serializes PCM → μ-law, writes to WebSocket
- `FastAPIWebsocketClient` — manages raw WebSocket send/receive

---

## Step 6: `run_bot()` — Get AI Services from Agent Config

**Code location:** `core/bot.py` → `run_bot()` (line ~54)

```python
async def run_bot(transport, runner_args):
    body = runner_args.body or {}
    agent = body.get("agent")

    if agent:
        # Agent found — use its config to build LLM/STT/TTS
        with get_db_context() as db:
            await AgentFactoryService(db).run_bot_for_agent(agent, transport, runner_args)
    else:
        # No agent — use default env-based services (fallback)
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")
        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
        tts = CartesiaTTSService(api_key=os.getenv("CARTESIA_API_KEY"), voice_id="...")
        messages = [{"role": "system", "content": "You are a polite assistant..."}]
        await AgentFactoryService(db).run_bot_with_components(transport, runner_args, llm, stt, tts, messages)
```

---

## Step 7: `AgentFactoryService.run_bot_for_agent()` — Build AI Services

**Code location:** `core/services/agent_factory_service.py`

### Step 7a: `get_agent_bot_data(agent)` — Assemble everything from DB

```python
# 1. Fetch AgentConfig from DB
config = self._get_agent_config(agent)
# config looks like:
# AgentConfig(
#     system_prompt="You are a hotel booking assistant...",
#     first_message="Hello! How can I help you today?",
#     llm_service_id=5,      # FK to Model table
#     stt_service_id=12,
#     tts_service_id=8,
#     voice_id="abc123",
#     language="en",
#     ...
# )

# 2. For each service (LLM, STT, TTS), look up Model + ServiceProvider + decrypt API key
model, provider, api_key = self._get_service_and_credentials(config.llm_service_id, "llm")
# model: Model(name="gpt-4o", model_id="gpt-4o", ...)
# provider: ServiceProvider(provider_name="openai", ...)
# api_key: "sk-proj-..." (decrypted from AES-encrypted DB value)

# 3. Instantiate the right Pipecat service based on provider name
llm = OpenAILLMService(api_key="sk-proj-...", model="gpt-4o")
stt = DeepgramSTTService(api_key="dg-...", model="nova-2")
tts = CartesiaTTSService(api_key="ct-...", voice_id="abc123")

# 4. Build messages list
messages = [
    {"role": "system", "content": "You are a hotel booking assistant..."},
    {"role": "assistant", "content": "Hello! How can I help you today?"},  # first_message
]
```

**Return value of `get_agent_bot_data()`:**
```python
{
    "llm": OpenAILLMService(...),
    "stt": DeepgramSTTService(...),
    "tts": CartesiaTTSService(...),
    "messages": [
        {"role": "system", "content": "You are a hotel booking assistant..."},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
    ],
    "config": AgentConfig(...),
}
```

---

## Step 8: `run_bot_with_components()` — Build & Run the Pipeline

This is where everything comes together. The voice pipeline is assembled and started.

**Code location:** `core/services/agent_factory_service.py` → `run_bot_with_components()`

### Step 8a: Create the context and aggregators

```python
# LLMContext holds the conversation history (messages accumulate here)
context = OpenAILLMContext(messages=messages)
# context.messages = [
#     {"role": "system", "content": "You are a hotel booking assistant..."},
#     {"role": "assistant", "content": "Hello! How can I help you today?"},
# ]

# Aggregators manage turn-taking (when user speaks vs when bot speaks)
context_aggregator = llm.create_context_aggregator(context)
# Returns an LLMContextAggregatorPair with:
#   .user()      → collects user's transcribed speech into context
#   .assistant() → collects bot's LLM response into context
```

### Step 8b: Build the pipeline

```python
pipeline = Pipeline([
    transport.input(),               # Reads audio from Twilio WebSocket
                                     #   → TwilioFrameSerializer.deserialize()
                                     #   → μ-law 8kHz → PCM 16kHz
                                     #   → InputAudioRawFrame

    rtvi,                            # RTVIProcessor (real-time voice interface protocol)

    stt,                             # Speech-to-Text (e.g., Deepgram)
                                     #   → Receives InputAudioRawFrame
                                     #   → Sends audio to Deepgram API
                                     #   → Returns TranscriptionFrame("Hello, I need a room")

    context_aggregator.user(),       # Collects transcription into LLM context
                                     #   → Adds {"role": "user", "content": "Hello, I need a room"}
                                     #   → Triggers LLM when user stops speaking

    llm,                             # Large Language Model (e.g., OpenAI GPT-4o)
                                     #   → Receives full message history
                                     #   → Streams response tokens
                                     #   → Returns TextFrame("Sure! Let me help...")

    tts,                             # Text-to-Speech (e.g., Cartesia)
                                     #   → Receives TextFrame
                                     #   → Returns AudioRawFrame (PCM audio)

    transport.output(),              # Sends audio back to Twilio WebSocket
                                     #   → TwilioFrameSerializer.serialize()
                                     #   → PCM 16kHz → μ-law 8kHz → base64
                                     #   → {"event":"media","streamSid":"MZ...","media":{"payload":"..."}}

    context_aggregator.assistant(),  # Records bot's response in conversation history
                                     #   → Adds {"role": "assistant", "content": "Sure! Let me help..."}
])
```

### Step 8c: Create the task and runner

```python
# PipelineTask wraps the pipeline with interruption handling and metrics
task = PipelineTask(
    pipeline,
    params=PipelineParams(
        allow_interruptions=True,    # User can interrupt the bot mid-sentence
        enable_metrics=True,
        enable_usage_metrics=True,
    ),
)

# When Twilio disconnects the WebSocket (caller hangs up), cancel the pipeline
@transport.event_handler("on_client_disconnected")
async def on_disconnected(transport, client):
    await task.cancel()

# PipelineRunner manages the async event loop for the pipeline
runner = PipelineRunner(handle_sigint=False)  # False because we're inside a server
await runner.run(task)   # ← BLOCKS HERE until the call ends
```

**`PipelineRunner.run(task)` does:**
1. Calls `task.run()` which starts all processors
2. Each processor runs its own async loop, processing frames from its input queue
3. Blocks until the task completes (caller hangs up, EndFrame, or cancellation)
4. Cleans up resources

---

## Step 9: Audio Flows Back and Forth (The Main Loop)

Once the pipeline is running, here's what happens for each chunk of audio:

### Incoming Audio (Caller → Bot):

```
Twilio sends WebSocket message:
{
  "event": "media",
  "sequenceNumber": "42",
  "media": {
    "track": "inbound",
    "chunk": "42",
    "timestamp": "1234",
    "payload": "base64-encoded-mulaw-audio..."    ← 20ms of 8kHz μ-law audio
  },
  "streamSid": "MZ..."
}

  ↓ FastAPIWebsocketInputTransport receives this
  ↓ TwilioFrameSerializer.deserialize(data)
  ↓   → Decodes base64 → μ-law bytes
  ↓   → Converts μ-law 8kHz → PCM 16kHz (linear16)
  ↓   → Returns InputAudioRawFrame(audio=pcm_bytes, sample_rate=16000, num_channels=1)

  ↓ SileroVADAnalyzer processes the audio
  ↓   → Detects if someone is speaking
  ↓   → After 0.2s of silence → pushes UserStoppedSpeakingFrame

  ↓ DeepgramSTTService receives audio chunks
  ↓   → Streams to Deepgram API over WebSocket
  ↓   → Returns TranscriptionFrame(text="I need to book a hotel room")

  ↓ context_aggregator.user() receives transcription
  ↓   → Appends {"role": "user", "content": "I need to book a hotel room"} to context
  ↓   → Pushes LLMMessagesFrame to trigger the LLM

  ↓ OpenAILLMService receives the full context
  ↓   → Calls OpenAI API with all messages
  ↓   → Streams response tokens: "Sure", "!", " Let", " me", " help", ...
  ↓   → Pushes TextFrame for each chunk

  ↓ CartesiaTTSService receives text chunks
  ↓   → Calls Cartesia API to synthesize speech
  ↓   → Returns AudioRawFrame(audio=pcm_bytes, sample_rate=16000)
```

### Outgoing Audio (Bot → Caller):

```
  ↓ FastAPIWebsocketOutputTransport receives AudioRawFrame
  ↓ TwilioFrameSerializer.serialize(frame)
  ↓   → Resamples PCM 16kHz → 8kHz
  ↓   → Converts PCM → μ-law
  ↓   → Base64 encodes
  ↓   → Returns JSON string:

{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "payload": "base64-encoded-mulaw-audio..."
  }
}

  ↓ Sent over WebSocket to Twilio
  ↓ Twilio plays audio to the caller's phone
```

### Interruption (Caller speaks while bot is talking):

```
VAD detects speech → UserStartedSpeakingFrame
  ↓ Pipeline clears all queued audio frames
  ↓ TwilioFrameSerializer sends clear event:
    {"event": "clear", "streamSid": "MZ..."}
  ↓ Twilio stops playing current audio
  ↓ LLM/TTS stop generating
  ↓ New user speech is processed normally
```

---

## Step 10: Call Ends

When the caller hangs up:

1. **Twilio closes the WebSocket** connection
2. **`FastAPIWebsocketTransport`** detects disconnect → fires `on_client_disconnected` event
3. **Event handler** calls `task.cancel()` → pipeline starts shutdown
4. **`TwilioFrameSerializer`** (if `auto_hang_up=True`) calls Twilio REST API:
   ```
   POST https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json
   Body: Status=completed
   ```
5. **`PipelineRunner.run(task)`** returns — the `await` in `run_bot_with_components` unblocks
6. **Control returns** up through `run_bot()` → `bot()` → `_run_telephony_bot()` → `websocket_endpoint()`
7. **FastAPI** cleans up the WebSocket connection

---

## Complete Call Stack (Summary)

```
Twilio HTTP POST /
  → Returns TwiML XML with <Stream url="wss://host/ws">

Twilio WebSocket /ws
  → websocket_endpoint(websocket)
    → _run_telephony_bot(websocket)
      → BotRunnerService.get_bot_for_incoming_call(websocket)
        → parse_telephony_websocket(websocket)        # reads first 2 WS messages
        → _fetch_twilio_to_number(call_sid)            # Twilio REST API
        → get_bot_for_phone_number(to_number)          # DB lookup
      → bot_module.bot(runner_args)                    # core/bot.py
        → TwilioFrameSerializer(stream_sid, call_sid)
        → FastAPIWebsocketTransport(websocket, params)
        → run_bot(transport, runner_args)
          → AgentFactoryService.run_bot_for_agent(agent, transport, runner_args)
            → get_agent_bot_data(agent)                # DB: config + decrypt API keys
            → run_bot_with_components(transport, ...)
              → Pipeline([input → stt → llm → tts → output])
              → PipelineTask(pipeline, allow_interruptions=True)
              → PipelineRunner().run(task)              # BLOCKS until call ends
```

---

## Key Files Reference

| File | What it does |
|------|-------------|
| `pipecat/src/pipecat/runner/run.py` | FastAPI server, `/ws` endpoint, telephony routes |
| `pipecat/src/pipecat/runner/types.py` | `WebSocketRunnerArguments`, `RunnerArguments` dataclasses |
| `pipecat/src/pipecat/runner/utils.py` | `parse_telephony_websocket()` — reads first 2 Twilio messages |
| `core/bot.py` | `bot()` entry point — creates transport, calls `run_bot()` |
| `core/services/bot_runner_service.py` | Resolves phone number → Agent from DB |
| `core/services/agent_factory_service.py` | Builds LLM/STT/TTS from agent config, assembles pipeline |
| `pipecat/src/pipecat/serializers/twilio.py` | μ-law ↔ PCM codec bridge for Twilio audio |
| `pipecat/src/pipecat/transports/websocket/fastapi.py` | WebSocket transport (input + output) |
| `pipecat/src/pipecat/pipeline/pipeline.py` | Chains processors together |
| `pipecat/src/pipecat/pipeline/runner.py` | Runs the pipeline event loop |
