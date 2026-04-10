---
name: foundational
description: "Skill for the Foundational area of tone. 1237 symbols across 347 files."
---

# Foundational

1237 symbols | 347 files | Cohesion: 78%

## When to Use

- Working with code in `pipecat/`
- Understanding how create_llm_service, get_llm_for_agent, test_pipeline_start_metadata work
- Modifying foundational-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/tests/test_pipeline.py` | test_pipeline_start_metadata, test_task_single, test_task_observers, CustomObserver, test_task_add_observer (+16) |
| `pipecat/examples/foundational/22d-natural-conversation-gemini-audio.py` | TurnDetectionLLM, run_bot, on_client_disconnected, bot, AudioAccumulator (+14) |
| `pipecat/examples/foundational/22c-natural-conversation-mixed-llms.py` | TurnDetectionLLM, run_bot, on_client_disconnected, bot, on_client_connected (+11) |
| `pipecat/examples/foundational/22b-natural-conversation-proposal.py` | TurnDetectionLLM, run_bot, on_client_disconnected, bot, on_client_connected (+11) |
| `pipecat/src/pipecat/pipeline/task.py` | PipelineParams, PipelineTask, event_handler, set_reached_upstream_filter, set_reached_downstream_filter (+9) |
| `pipecat/examples/foundational/25-google-audio-in.py` | run_bot, on_client_disconnected, bot, on_client_connected, UserAudioCollector (+7) |
| `pipecat/examples/foundational/07s-interruptible-google-audio-in.py` | run_bot, on_client_disconnected, bot, on_client_connected, UserAudioCollector (+6) |
| `pipecat/examples/foundational/28-user-assistant-turns.py` | TranscriptHandler, run_bot, on_client_disconnected, bot, on_client_connected (+5) |
| `pipecat/examples/foundational/17-detect-user-idle.py` | IdleHandler, run_bot, on_client_disconnected, bot, on_client_connected (+4) |
| `pipecat/examples/foundational/39c-multiple-mcp.py` | run_bot, on_client_disconnected, bot, on_client_connected, process_frame (+3) |

## Entry Points

Start here when exploring this area:

- **`create_llm_service`** (Function) — `dev/test_llm_models.py:78`
- **`get_llm_for_agent`** (Function) — `core/services/agent_factory_service.py:366`
- **`test_pipeline_start_metadata`** (Function) — `pipecat/tests/test_pipeline.py:59`
- **`test_task_single`** (Function) — `pipecat/tests/test_pipeline.py:100`
- **`test_task_observers`** (Function) — `pipecat/tests/test_pipeline.py:109`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `CustomObserver` | Class | `pipecat/tests/test_pipeline.py` | 112 |
| `TranscriptHandler` | Class | `pipecat/examples/foundational/28-user-assistant-turns.py` | 40 |
| `TurnDetectionLLM` | Class | `pipecat/examples/foundational/22d-natural-conversation-gemini-audio.py` | 630 |
| `TurnDetectionLLM` | Class | `pipecat/examples/foundational/22c-natural-conversation-mixed-llms.py` | 399 |
| `TurnDetectionLLM` | Class | `pipecat/examples/foundational/22b-natural-conversation-proposal.py` | 200 |
| `TurnDetectionLLM` | Class | `pipecat/examples/foundational/22-natural-conversation.py` | 44 |
| `IdleHandler` | Class | `pipecat/examples/foundational/17-detect-user-idle.py` | 44 |
| `UserTurnStrategies` | Class | `pipecat/src/pipecat/turns/user_turn_strategies.py` | 25 |
| `ExternalUserTurnStrategies` | Class | `pipecat/src/pipecat/turns/user_turn_strategies.py` | 52 |
| `MCPClient` | Class | `pipecat/src/pipecat/services/mcp_service.py` | 34 |
| `LLMService` | Class | `pipecat/src/pipecat/services/llm_service.py` | 144 |
| `PipelineParams` | Class | `pipecat/src/pipecat/pipeline/task.py` | 101 |
| `PipelineTask` | Class | `pipecat/src/pipecat/pipeline/task.py` | 151 |
| `PipelineRunner` | Class | `pipecat/src/pipecat/pipeline/runner.py` | 25 |
| `Pipeline` | Class | `pipecat/src/pipecat/pipeline/pipeline.py` | 90 |
| `LLMSwitcher` | Class | `pipecat/src/pipecat/pipeline/llm_switcher.py` | 16 |
| `PipelineTaskParams` | Class | `pipecat/src/pipecat/pipeline/base_task.py` | 22 |
| `TurnAnalyzerUserTurnStopStrategy` | Class | `pipecat/src/pipecat/turns/user_stop/turn_analyzer_user_turn_stop_strategy.py` | 28 |
| `LocalAudioTransportParams` | Class | `pipecat/src/pipecat/transports/local/audio.py` | 34 |
| `LocalAudioTransport` | Class | `pipecat/src/pipecat/transports/local/audio.py` | 191 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → _run_handler` | cross_community | 10 |
| `Process_frame → Create_task` | cross_community | 10 |
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Start → Get_time` | cross_community | 9 |
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Start → Get_time` | cross_community | 9 |
| `Start → FramePushed` | cross_community | 9 |
| `Process_frame → _run_handler` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tests | 65 calls |
| Services | 42 calls |
| Google | 25 calls |
| Processors | 21 calls |
| Cartesia | 20 calls |
| Websocket | 15 calls |
| Pipeline | 12 calls |
| Frames | 12 calls |

## How to Explore

1. `gitnexus_context({name: "create_llm_service"})` — see callers and callees
2. `gitnexus_query({query: "foundational"})` — find related execution flows
3. Read key files listed above for implementation details
