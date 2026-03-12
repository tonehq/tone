# Agent Pipeline Execution Architecture

## Overview

This document describes the runtime architecture of the Tone voice agent pipeline, tracing execution from the WebSocket entry point (`/ws`) through pipeline creation, agent initialization, and LLM/STT/TTS provider instantiation.

---

## 1. Call Chain from `/ws` to Pipeline Execution

```
@app.websocket("/ws")                              # run.py:908
  └─ websocket.accept()
  └─ _run_telephony_bot(websocket)                  # run.py:233
       └─ _get_bot_module()                         # run.py:127 → resolves core/bot.py
       └─ BotRunnerService(db)
            .get_bot_for_incoming_call(websocket)    # bot_runner_service.py:126
            ├─ parse_telephony_websocket(websocket)  # Reads first WS messages → (transport_type, call_data)
            ├─ get_to_number_from_call_data_async()  # Resolves "to" phone number (Twilio API)
            └─ get_bot_for_phone_number(to_number)   # DB lookup: phone → ChannelPhoneNumbers → Agent
       └─ WebSocketRunnerArguments(websocket, body={call_data, transport_type, agent})
       └─ bot_module.bot(runner_args)                # core/bot.py:228
            └─ isinstance check → WebSocketRunnerArguments
            └─ TwilioFrameSerializer(stream_sid, call_sid, ...)
            └─ FastAPIWebsocketTransport(websocket, params)  # Transport created
            └─ run_bot(transport, runner_args)        # core/bot.py:124
                 └─ AgentFactoryService(db)
                      .run_bot_for_agent(agent, transport, runner_args)  # agent_factory_service.py:639
                      ├─ get_agent_bot_data(agent)                       # agent_factory_service.py:533
                      │   ├─ _get_agent_config(agent)       # DB: AgentConfig (active)
                      │   ├─ get_llm_for_agent(agent)       # → LLMService instance
                      │   │   ├─ _get_service_and_credentials(llm_service_id, "llm")
                      │   │   │   ├─ DB: Model + ServiceProvider join
                      │   │   │   └─ DB: ApiKey → decrypt()
                      │   │   └─ Provider switch → instantiate (OpenAILLMService, AnthropicLLMService, ...)
                      │   ├─ get_stt_for_agent(agent)       # → STTService instance
                      │   │   └─ Same pattern as LLM
                      │   └─ get_tts_for_agent(agent)       # → TTSService instance
                      │       └─ Same pattern as LLM
                      └─ run_bot_with_components(transport, runner_args, llm, stt, tts, messages)
                           ├─ LLMContext(messages, tools)
                           ├─ LLMContextAggregatorPair(context)
                           ├─ LLMTextProcessor()
                           ├─ RTVIProcessor(config)
                           ├─ Pipeline([                          # agent_factory_service.py:597
                           │    transport.input(),                 # BaseInputTransport
                           │    rtvi,                              # RTVIProcessor
                           │    stt,                               # STTService
                           │    context_aggregator.user(),         # LLMUserAggregator
                           │    llm,                               # LLMService
                           │    llm_text_processor,                # LLMTextProcessor
                           │    tts,                               # TTSService
                           │    transport.output(),                # BaseOutputTransport
                           │    context_aggregator.assistant(),    # LLMAssistantAggregator
                           │ ])
                           ├─ PipelineTask(pipeline, params, observers)
                           ├─ PipelineRunner(handle_sigint=False)
                           └─ runner.run(task)                     # Blocking until pipeline ends
```

---

## 2. High-Level Architecture Diagram (Mermaid)

```mermaid
graph TB
    subgraph "Entry Point"
        WS["@app.websocket('/ws')<br/>run.py:908"]
    end

    subgraph "Call Resolution"
        RTB["_run_telephony_bot()<br/>run.py:233"]
        BRS["BotRunnerService<br/>bot_runner_service.py"]
        PTW["parse_telephony_websocket()<br/>runner/utils.py"]
    end

    subgraph "Bot Entry & Transport"
        BOT["bot(runner_args)<br/>core/bot.py:228"]
        FAWT["FastAPIWebsocketTransport"]
        SWRT["SmallWebRTCTransport"]
        DT["DailyTransport"]
        SER["TwilioFrameSerializer"]
    end

    subgraph "Agent Factory"
        AFS["AgentFactoryService<br/>agent_factory_service.py"]
        GAC["_get_agent_config()"]
        GSC["_get_service_and_credentials()"]
    end

    subgraph "AI Services"
        LLM["LLMService<br/>(OpenAI, Anthropic, Groq, ...)"]
        STT["STTService<br/>(Deepgram, OpenAI, Azure, ...)"]
        TTS["TTSService<br/>(Cartesia, ElevenLabs, OpenAI, ...)"]
    end

    subgraph "Pipeline Runtime"
        PIPE["Pipeline"]
        TASK["PipelineTask"]
        RUNNER["PipelineRunner"]
        CTX["LLMContext /<br/>LLMContextAggregatorPair"]
        RTVI["RTVIProcessor"]
    end

    WS --> RTB
    RTB --> BRS
    BRS --> PTW
    RTB --> BOT
    BOT -->|WebSocket| FAWT
    BOT -->|WebRTC| SWRT
    BOT -->|Daily| DT
    BOT -->|Twilio| SER
    SER --> FAWT
    BOT --> AFS
    AFS --> GAC
    AFS --> GSC
    GSC --> LLM
    GSC --> STT
    GSC --> TTS
    AFS --> CTX
    AFS --> RTVI
    AFS --> PIPE
    PIPE --> TASK
    TASK --> RUNNER
```



---

## 3. UML Class Diagram (Mermaid)

```mermaid
classDiagram
    direction TB

    class BaseObject {
        +event_handler(event_name) decorator
    }

    class FrameProcessor {
        -_prev: FrameProcessor
        -_next: FrameProcessor
        -_clock: BaseClock
        -_task_manager: BaseTaskManager
        -_allow_interruptions: bool
        +process_frame(frame, direction)
        +push_frame(frame, direction)
        +queue_frame(frame, direction)
        +link(processor)
        +setup(setup: FrameProcessorSetup)
        +cleanup()
    }

    class AIService {
        -_model_name: str
        -_settings: dict
        +model_name: str
        +set_model_name(model)
        +start(frame)
        +stop(frame)
        +process_frame(frame, direction)
        +process_generator(generator)
    }

    class LLMService {
        +run_llm(messages)*
        +get_messages()
        +process_frame(frame, direction)
    }

    class STTService {
        +run_stt(audio)*
        +process_frame(frame, direction)
    }

    class TTSService {
        +run_tts(text)*
        +process_frame(frame, direction)
    }

    class BaseTransport {
        -_input_name: str
        -_output_name: str
        +input() FrameProcessor*
        +output() FrameProcessor*
    }

    class FastAPIWebsocketTransport {
        -_websocket: WebSocket
        -_params: FastAPIWebsocketParams
        +input() FrameProcessor
        +output() FrameProcessor
    }

    class SmallWebRTCTransport {
        -_connection: SmallWebRTCConnection
        +input() FrameProcessor
        +output() FrameProcessor
    }

    class DailyTransport {
        -_room_url: str
        -_token: str
        +input() FrameProcessor
        +output() FrameProcessor
    }

    class Pipeline {
        -_processors: List~FrameProcessor~
        -_source: PipelineSource
        -_sink: PipelineSink
        +processors: List
        +setup(setup)
        +cleanup()
        +process_frame(frame, direction)
    }

    class PipelineTask {
        -_pipeline: Pipeline
        -_params: PipelineParams
        -_observer: TaskObserver
        -_finished: bool
        +run(params)
        +cancel(reason)
        +queue_frame(frame)
        +has_finished() bool
        +event_handler(event_name)
    }

    class PipelineRunner {
        -_tasks: dict
        +run(task: PipelineTask)
        +cancel()
        +stop_when_done()
    }

    class AgentFactoryService {
        -db: Session
        +get_llm_for_agent(agent) LLMService
        +get_stt_for_agent(agent) STTService
        +get_tts_for_agent(agent) TTSService
        +get_agent_bot_data(agent) dict
        +run_bot_for_agent(agent, transport, runner_args)
        +run_bot_with_components(transport, runner_args, llm, stt, tts, messages)
        -_get_agent_config(agent) AgentConfig
        -_get_service_and_credentials(provider_id, type) tuple
        -_build_input_params(service_class, metadata)
    }

    class BotRunnerService {
        -db: Session
        +get_bot_for_incoming_call(websocket) tuple
        +get_bot_for_phone_number(phone_number) Agent
        -_fetch_twilio_to_number(call_sid) str
        -_get_twilio_credentials() dict
    }

    class LLMContext {
        -messages: List~dict~
        -tools: Any
    }

    class LLMContextAggregatorPair {
        -_context: LLMContext
        +user() LLMUserAggregator
        +assistant() LLMAssistantAggregator
    }

    BaseObject <|-- FrameProcessor
    BaseObject <|-- BaseTransport
    FrameProcessor <|-- AIService
    AIService <|-- LLMService
    AIService <|-- STTService
    AIService <|-- TTSService
    BaseTransport <|-- FastAPIWebsocketTransport
    BaseTransport <|-- SmallWebRTCTransport
    BaseTransport <|-- DailyTransport
    FrameProcessor <|-- Pipeline

    AgentFactoryService ..> LLMService : creates
    AgentFactoryService ..> STTService : creates
    AgentFactoryService ..> TTSService : creates
    AgentFactoryService ..> Pipeline : creates
    AgentFactoryService ..> PipelineTask : creates
    AgentFactoryService ..> PipelineRunner : creates
    AgentFactoryService ..> LLMContext : creates
    AgentFactoryService ..> LLMContextAggregatorPair : creates
    BotRunnerService ..> AgentFactoryService : precedes

    PipelineRunner --> PipelineTask : runs
    PipelineTask --> Pipeline : orchestrates
    Pipeline --> FrameProcessor : chains
```



---

## 4. UML Sequence Diagram (Mermaid)

```mermaid
sequenceDiagram
    participant Client as Twilio/Client
    participant WS as WebSocket /ws
    participant RTB as _run_telephony_bot
    participant BRS as BotRunnerService
    participant Bot as bot()
    participant Transport as FastAPIWebsocketTransport
    participant AFS as AgentFactoryService
    participant DB as Database
    participant LLM as LLMService
    participant STT as STTService
    participant TTS as TTSService
    participant Pipe as Pipeline
    participant Task as PipelineTask
    participant Runner as PipelineRunner

    Client->>WS: WebSocket connect
    WS->>WS: websocket.accept()
    WS->>RTB: _run_telephony_bot(websocket)

    RTB->>RTB: _get_bot_module() → core/bot.py

    RTB->>BRS: get_bot_for_incoming_call(websocket)
    BRS->>BRS: parse_telephony_websocket(ws)
    Note over BRS: Reads first WS messages<br/>→ transport_type, call_data
    BRS->>BRS: get_to_number_from_call_data_async()
    BRS->>DB: Query ChannelPhoneNumbers by phone
    DB-->>BRS: Agent
    BRS-->>RTB: (agent, transport_type, call_data)

    RTB->>Bot: bot(WebSocketRunnerArguments)

    Bot->>Bot: Create TwilioFrameSerializer
    Bot->>Transport: new FastAPIWebsocketTransport(ws, params)
    Bot->>AFS: run_bot_for_agent(agent, transport, args)

    AFS->>DB: Query AgentConfig (active)
    DB-->>AFS: AgentConfig (system_prompt, llm/stt/tts IDs)

    rect rgb(240, 248, 255)
        Note over AFS,DB: Build LLM Service
        AFS->>DB: Query Model + ServiceProvider + ApiKey (LLM)
        DB-->>AFS: (model_name, provider_name, api_key)
        AFS->>AFS: decrypt(api_key)
        AFS->>LLM: new OpenAILLMService(api_key, model)
    end

    rect rgb(240, 255, 240)
        Note over AFS,DB: Build STT Service
        AFS->>DB: Query Model + ServiceProvider + ApiKey (STT)
        DB-->>AFS: (model_name, provider_name, api_key)
        AFS->>STT: new DeepgramSTTService(api_key)
    end

    rect rgb(255, 248, 240)
        Note over AFS,DB: Build TTS Service
        AFS->>DB: Query Model + ServiceProvider + ApiKey (TTS)
        DB-->>AFS: (model_name, provider_name, api_key)
        AFS->>TTS: new CartesiaTTSService(api_key, voice_id)
    end

    AFS->>AFS: LLMContext(messages, tools)
    AFS->>AFS: LLMContextAggregatorPair(context)
    AFS->>AFS: RTVIProcessor(config)

    AFS->>Pipe: new Pipeline([<br/>  transport.input(),<br/>  rtvi, stt,<br/>  context_aggregator.user(),<br/>  llm, llm_text_processor, tts,<br/>  transport.output(),<br/>  context_aggregator.assistant()<br/>])

    AFS->>Task: new PipelineTask(pipeline, params, observers)
    AFS->>Runner: new PipelineRunner()
    AFS->>Runner: runner.run(task)

    Runner->>Task: task.run()
    Note over Task: Pushes StartFrame<br/>→ initializes all processors

    loop Audio Processing Loop
        Transport->>STT: AudioRawFrame
        STT->>STT: Speech → Text
        STT->>LLM: TranscriptionFrame
        LLM->>LLM: Generate response
        LLM->>TTS: LLMTextFrame
        TTS->>TTS: Text → Audio
        TTS->>Transport: TTSAudioRawFrame
        Transport->>Client: Audio output
    end

    Client->>WS: Disconnect
    Transport->>Task: task.cancel()
    Task->>Runner: Pipeline finished
```



---

## 5. Data Flow Through the Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Pipeline Frame Flow                          │
│                                                                     │
│  ┌─────────────┐    ┌──────┐    ┌─────┐    ┌───────────────┐       │
│  │ transport    │───▶│ RTVI │───▶│ STT │───▶│ context_agg   │       │
│  │  .input()   │    │      │    │     │    │   .user()     │       │
│  │             │    │      │    │     │    │               │       │
│  │ AudioRaw    │    │      │    │Trans│    │ LLMContext    │       │
│  │ Frame       │    │      │    │crip.│    │ (messages)    │       │
│  └─────────────┘    └──────┘    └─────┘    └───────┬───────┘       │
│                                                     │               │
│                                                     ▼               │
│  ┌─────────────┐    ┌──────────┐    ┌─────┐    ┌───────────┐       │
│  │ context_agg │◀───│transport │◀───│ TTS │◀───│    LLM    │       │
│  │ .assistant()│    │ .output()│    │     │    │           │       │
│  │             │    │          │    │     │    │ LLMText   │       │
│  │ Updates     │    │ TTSAudio │    │Audio│    │ Frame     │       │
│  │ context     │    │ RawFrame │    │     │    │           │       │
│  └─────────────┘    └──────────┘    └─────┘    └───────────┘       │
│                          │                                          │
│                          ▼                                          │
│                    WebSocket/Client                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Class Hierarchy

```
BaseObject
├── FrameProcessor
│   ├── AIService
│   │   ├── LLMService
│   │   │   ├── OpenAILLMService / BaseOpenAILLMService
│   │   │   ├── AnthropicLLMService
│   │   │   ├── GroqLLMService
│   │   │   ├── GoogleLLMService
│   │   │   ├── OLLamaLLMService
│   │   │   ├── AWSBedrockLLMService
│   │   │   └── OpenRouterLLMService
│   │   ├── STTService
│   │   │   ├── DeepgramSTTService
│   │   │   ├── OpenAISTTService
│   │   │   ├── GroqSTTService
│   │   │   ├── AzureSTTService
│   │   │   ├── GoogleSTTService
│   │   │   ├── CartesiaSTTService
│   │   │   ├── ElevenLabsRealtimeSTTService
│   │   │   ├── AssemblyAISTTService
│   │   │   └── SpeechmaticsSTTService, SonioxSTTService, ...
│   │   └── TTSService
│   │       ├── CartesiaTTSService
│   │       ├── ElevenLabsTTSService
│   │       ├── OpenAITTSService
│   │       ├── DeepgramHttpTTSService
│   │       ├── AzureTTSService
│   │       ├── PlayHTTTSService
│   │       ├── HumeTTSService
│   │       └── RimeHttpTTSService, SarvamHttpTTSService, ...
│   ├── LLMTextProcessor
│   ├── LLMUserAggregator
│   ├── LLMAssistantAggregator
│   ├── RTVIProcessor
│   ├── PipelineSource
│   └── PipelineSink
├── BaseTransport
│   ├── FastAPIWebsocketTransport   (Telephony: Twilio, Telnyx, Plivo)
│   ├── SmallWebRTCTransport        (Browser WebRTC)
│   └── DailyTransport              (Daily.co rooms)
├── Pipeline (extends FrameProcessor)
├── PipelineTask (extends BasePipelineTask)
└── PipelineRunner
```

---

## 7. Core Class Responsibilities

### Entry & Routing Layer


| Class                  | File                                     | Responsibility                                                            |
| ---------------------- | ---------------------------------------- | ------------------------------------------------------------------------- |
| `_run_telephony_bot()` | `pipecat/src/pipecat/runner/run.py:233`  | Receives WebSocket, resolves agent via BotRunnerService, invokes `bot()`  |
| `BotRunnerService`     | `core/services/bot_runner_service.py:15` | Parses telephony WebSocket messages, resolves phone number → Agent via DB |
| `bot()`                | `core/bot.py:228`                        | Creates transport based on runner argument type, calls `run_bot()`        |


### Factory Layer


| Class                            | File                                        | Responsibility                                                                                              |
| -------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `AgentFactoryService`            | `core/services/agent_factory_service.py:22` | Central factory: reads agent config from DB, builds LLM/STT/TTS instances, constructs and runs the pipeline |
| `_get_agent_config()`            | `agent_factory_service.py:25`               | Queries `AgentConfig` table for the active config of an agent                                               |
| `_get_service_and_credentials()` | `agent_factory_service.py:37`               | Joins Model + ServiceProvider + ApiKey, decrypts API key                                                    |
| `get_llm_for_agent()`            | `agent_factory_service.py:101`              | Maps provider name → concrete LLMService subclass                                                           |
| `get_stt_for_agent()`            | `agent_factory_service.py:183`              | Maps provider name → concrete STTService subclass                                                           |
| `get_tts_for_agent()`            | `agent_factory_service.py:255`              | Maps provider name → concrete TTSService subclass                                                           |


### Transport Layer


| Class                       | File                                              | Responsibility                                                                    |
| --------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------- |
| `BaseTransport`             | `pipecat/.../transports/base_transport.py:163`    | Abstract base: defines `input()` and `output()` methods returning FrameProcessors |
| `FastAPIWebsocketTransport` | `pipecat/.../transports/websocket/fastapi.py`     | WebSocket transport for telephony (Twilio, Telnyx, Plivo). Uses frame serializers |
| `SmallWebRTCTransport`      | `pipecat/.../transports/smallwebrtc/transport.py` | Browser-based WebRTC transport                                                    |
| `DailyTransport`            | `pipecat/.../transports/daily/transport.py`       | Daily.co video conferencing transport                                             |
| `TwilioFrameSerializer`     | `pipecat/.../serializers/twilio.py`               | Serializes/deserializes Twilio media stream frames (mulaw audio)                  |


### Pipeline Runtime


| Class            | File                                            | Responsibility                                                                                  |
| ---------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `FrameProcessor` | `pipecat/.../processors/frame_processor.py:143` | Base processing unit. Receives frames, processes, pushes downstream/upstream. Linked list chain |
| `AIService`      | `pipecat/.../services/ai_service.py:28`         | Base for all AI services. Handles start/stop lifecycle, settings, model name                    |
| `LLMService`     | `pipecat/.../services/llm_service.py`           | Receives LLMContext, generates text via `run_llm()`, pushes LLMTextFrames                       |
| `STTService`     | `pipecat/.../services/stt_service.py`           | Receives AudioRawFrames, converts to text via `run_stt()`, pushes TranscriptionFrames           |
| `TTSService`     | `pipecat/.../services/tts_service.py`           | Receives TextFrames, converts to audio via `run_tts()`, pushes TTSAudioRawFrames                |
| `Pipeline`       | `pipecat/.../pipeline/pipeline.py:91`           | Chains FrameProcessors in sequence. Links source → processors → sink                            |
| `PipelineTask`   | `pipecat/.../pipeline/task.py:152`              | Manages pipeline lifecycle: setup, run, idle timeout, interruptions, cancellation, metrics      |
| `PipelineRunner` | `pipecat/.../pipeline/runner.py:26`             | Top-level executor. Runs PipelineTask, handles signals (SIGINT/SIGTERM)                         |


### Context & Aggregation


| Class                      | File                                                           | Responsibility                                                                 |
| -------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `LLMContext`               | `pipecat/.../processors/aggregators/llm_context.py`            | Holds conversation messages and tools for LLM calls                            |
| `LLMContextAggregatorPair` | `pipecat/.../processors/aggregators/llm_response_universal.py` | Creates paired user/assistant aggregators that accumulate conversation context |
| `LLMTextProcessor`         | `pipecat/.../processors/aggregators/llm_text_processor.py`     | Processes LLM text output (parsing, formatting) before passing to TTS          |
| `RTVIProcessor`            | `pipecat/.../processors/frameworks/rtvi.py`                    | Real-Time Voice Interaction protocol handler for client communication          |


---

## 8. Key Frame Types in the Pipeline


| Frame                      | Direction  | Source → Destination    | Purpose                      |
| -------------------------- | ---------- | ----------------------- | ---------------------------- |
| `StartFrame`               | DOWNSTREAM | PipelineTask → All      | Initialize all processors    |
| `AudioRawFrame`            | DOWNSTREAM | Transport.input → STT   | Raw audio from caller        |
| `TranscriptionFrame`       | DOWNSTREAM | STT → LLMUserAggregator | Transcribed user speech      |
| `LLMTextFrame`             | DOWNSTREAM | LLM → TTS               | Generated response text      |
| `TTSAudioRawFrame`         | DOWNSTREAM | TTS → Transport.output  | Synthesized speech audio     |
| `UserStartedSpeakingFrame` | DOWNSTREAM | VAD → Pipeline          | User barge-in (interruption) |
| `EndFrame`                 | DOWNSTREAM | Task → All              | Graceful shutdown            |
| `CancelFrame`              | DOWNSTREAM | Task → All              | Forced cancellation          |


---

## 9. Database Tables in the Pipeline Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     Agent        │     │   AgentConfig     │     │ ServiceProvider  │
│─────────────────│     │──────────────────│     │─────────────────│
│ id              │◀────│ agent_id          │     │ id              │
│ name            │     │ status            │     │ name            │
│                 │     │ system_prompt     │  ┌─▶│ provider_type   │
│                 │     │ first_message     │  │  │                 │
│                 │     │ llm_service_id  ──┼──┘  └────────┬────────┘
│                 │     │ stt_service_id  ──┼──┘           │
│                 │     │ tts_service_id  ──┼──┘           │
│                 │     │ llm_metadata      │     ┌────────▼────────┐
│                 │     │ stt_metadata      │     │     Model        │
│                 │     │ tts_metadata      │     │─────────────────│
└─────────────────┘     └──────────────────┘     │ id              │
                                                  │ name            │
┌─────────────────┐                               │ service_type    │
│ChannelPhoneNums │                               │ service_provider│
│─────────────────│                               │ api_key_id    ──┼──┐
│ phone_number    │                               │ meta_data       │  │
│ agent_id ───────┼──▶ Agent                      │ status          │  │
│ channel_id      │                               └─────────────────┘  │
└─────────────────┘                                                    │
                                                  ┌────────────────────▼┐
                                                  │      ApiKey          │
                                                  │─────────────────────│
                                                  │ id                   │
                                                  │ service_provider_id  │
                                                  │ api_key_encrypted    │
                                                  │ status               │
                                                  └──────────────────────┘
```

---

## 10. Supported Providers

### LLM Providers (agent_factory_service.py:101-180)


| Provider                                                                                               | Class                  | Default Model           |
| ------------------------------------------------------------------------------------------------------ | ---------------------- | ----------------------- |
| openai                                                                                                 | `OpenAILLMService`     | gpt-4.1                 |
| anthropic                                                                                              | `AnthropicLLMService`  | claude-sonnet-4-5       |
| groq                                                                                                   | `GroqLLMService`       | llama-3.3-70b-versatile |
| openrouter                                                                                             | `OpenRouterLLMService` | openai/gpt-4o           |
| google                                                                                                 | `GoogleLLMService`     | gemini-2.5-flash        |
| aws_bedrock                                                                                            | `AWSBedrockLLMService` | amazon.nova-pro-v1:0    |
| ollama                                                                                                 | `OLLamaLLMService`     | llama2                  |
| azure, cerebras, nvidia_nim, fireworks, together, perplexity, qwen, deepseek, mistral, sambanova, grok | `BaseOpenAILLMService` | varies                  |


### STT Providers (agent_factory_service.py:183-253)


| Provider                                   | Class                          |
| ------------------------------------------ | ------------------------------ |
| deepgram                                   | `DeepgramSTTService`           |
| openai                                     | `OpenAISTTService`             |
| groq                                       | `GroqSTTService`               |
| azure                                      | `AzureSTTService`              |
| google                                     | `GoogleSTTService`             |
| cartesia                                   | `CartesiaSTTService`           |
| elevenlabs                                 | `ElevenLabsRealtimeSTTService` |
| assemblyai                                 | `AssemblyAISTTService`         |
| speechmatics                               | `SpeechmaticsSTTService`       |
| soniox                                     | `SonioxSTTService`             |
| nvidia, sarvam, gladia, hathora, sambanova | various                        |


### TTS Providers (agent_factory_service.py:255-531)


| Provider                                                                                                                                   | Class                    |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| cartesia                                                                                                                                   | `CartesiaTTSService`     |
| openai                                                                                                                                     | `OpenAITTSService`       |
| elevenlabs                                                                                                                                 | `ElevenLabsTTSService`   |
| deepgram                                                                                                                                   | `DeepgramHttpTTSService` |
| azure                                                                                                                                      | `AzureTTSService`        |
| playht                                                                                                                                     | `PlayHTTTSService`       |
| hume                                                                                                                                       | `HumeTTSService`         |
| groq                                                                                                                                       | `GroqTTSService`         |
| rime, sarvam, speechmatics, nvidia, fish, lmnt, resemble, neuphonic, minimax, camb, aws_polly, google_base, asyncai_http, hathora, inworld | various                  |


---

## 11. PlantUML Sequence Diagram

```plantuml
@startuml Agent Pipeline Execution

skinparam sequenceArrowThickness 2
skinparam sequenceParticipantPadding 20

actor "Twilio\nClient" as Client
participant "WebSocket\n/ws" as WS
participant "_run_telephony_bot" as RTB
participant "BotRunnerService" as BRS
participant "bot()" as Bot
participant "FastAPIWebsocket\nTransport" as Transport
participant "AgentFactory\nService" as AFS
database "Database" as DB
participant "LLMService" as LLM
participant "STTService" as STT
participant "TTSService" as TTS
participant "Pipeline" as Pipe
participant "PipelineTask" as Task
participant "PipelineRunner" as Runner

Client -> WS : WebSocket connect
activate WS
WS -> WS : accept()
WS -> RTB : _run_telephony_bot(ws)
activate RTB

RTB -> BRS : get_bot_for_incoming_call(ws)
activate BRS
BRS -> BRS : parse_telephony_websocket()
BRS -> DB : Query ChannelPhoneNumbers
DB --> BRS : Agent
BRS --> RTB : (agent, transport_type, call_data)
deactivate BRS

RTB -> Bot : bot(WebSocketRunnerArguments)
activate Bot
Bot -> Transport : new FastAPIWebsocketTransport()
Bot -> AFS : run_bot_for_agent()
activate AFS

AFS -> DB : Query AgentConfig
DB --> AFS : config

group Build Services
    AFS -> DB : Query LLM Model + Provider + ApiKey
    DB --> AFS : credentials
    AFS -> LLM ** : new OpenAILLMService()

    AFS -> DB : Query STT Model + Provider + ApiKey
    DB --> AFS : credentials
    AFS -> STT ** : new DeepgramSTTService()

    AFS -> DB : Query TTS Model + Provider + ApiKey
    DB --> AFS : credentials
    AFS -> TTS ** : new CartesiaTTSService()
end

AFS -> Pipe ** : new Pipeline([input, rtvi, stt, ctx.user, llm, txt, tts, output, ctx.asst])
AFS -> Task ** : new PipelineTask(pipeline, params)
AFS -> Runner ** : new PipelineRunner()
AFS -> Runner : run(task)
activate Runner
Runner -> Task : run()
activate Task

loop Audio Processing
    Transport -> STT : AudioRawFrame
    STT -> LLM : TranscriptionFrame
    LLM -> TTS : LLMTextFrame
    TTS -> Transport : TTSAudioRawFrame
    Transport -> Client : Audio
end

Client -> Transport : disconnect
Transport -> Task : cancel()
deactivate Task
deactivate Runner
deactivate AFS
deactivate Bot
deactivate RTB
deactivate WS

@enduml
```

---

## 12. PlantUML Class Diagram

```plantuml
@startuml Agent Pipeline Classes

skinparam classAttributeIconSize 0

abstract class BaseObject {
    +event_handler(name)
}

abstract class FrameProcessor {
    -_prev: FrameProcessor
    -_next: FrameProcessor
    -_allow_interruptions: bool
    +process_frame(frame, direction)
    +push_frame(frame, direction)
    +link(processor)
    +setup(setup)
    +cleanup()
}

abstract class AIService {
    -_model_name: str
    +model_name: str
    +start(frame)
    +stop(frame)
    +process_generator(gen)
}

abstract class LLMService {
    +{abstract} run_llm(messages)
}

abstract class STTService {
    +{abstract} run_stt(audio)
}

abstract class TTSService {
    +{abstract} run_tts(text)
}

abstract class BaseTransport {
    +{abstract} input(): FrameProcessor
    +{abstract} output(): FrameProcessor
}

class FastAPIWebsocketTransport {
    -_websocket: WebSocket
    +input(): FrameProcessor
    +output(): FrameProcessor
}

class Pipeline {
    -_processors: List<FrameProcessor>
    +setup(setup)
    +process_frame(frame, dir)
}

class PipelineTask {
    -_pipeline: Pipeline
    -_params: PipelineParams
    +run(params)
    +cancel()
    +queue_frame(frame)
}

class PipelineRunner {
    +run(task)
    +cancel()
}

class AgentFactoryService {
    -db: Session
    +get_llm_for_agent(agent)
    +get_stt_for_agent(agent)
    +get_tts_for_agent(agent)
    +run_bot_for_agent(agent, transport, args)
    +run_bot_with_components(...)
}

class BotRunnerService {
    -db: Session
    +get_bot_for_incoming_call(ws)
    +get_bot_for_phone_number(phone)
}

class LLMContext {
    -messages: List
    -tools: Any
}

class LLMContextAggregatorPair {
    +user(): LLMUserAggregator
    +assistant(): LLMAssistantAggregator
}

BaseObject <|-- FrameProcessor
BaseObject <|-- BaseTransport
FrameProcessor <|-- AIService
FrameProcessor <|-- Pipeline
AIService <|-- LLMService
AIService <|-- STTService
AIService <|-- TTSService
BaseTransport <|-- FastAPIWebsocketTransport

AgentFactoryService ..> LLMService : creates
AgentFactoryService ..> STTService : creates
AgentFactoryService ..> TTSService : creates
AgentFactoryService ..> Pipeline : creates
AgentFactoryService ..> PipelineTask : creates
AgentFactoryService ..> PipelineRunner : creates
AgentFactoryService ..> LLMContext : creates
AgentFactoryService ..> LLMContextAggregatorPair : creates

BotRunnerService ..> AgentFactoryService : resolves agent for

PipelineRunner --> PipelineTask : runs
PipelineTask --> Pipeline : orchestrates
Pipeline o-- FrameProcessor : chains [1..*]

@enduml
```

