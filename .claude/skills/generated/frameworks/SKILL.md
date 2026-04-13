---
name: frameworks
description: "Skill for the Frameworks area of tone. 108 symbols across 9 files."
---

# Frameworks

108 symbols | 9 files | Cohesion: 69%

## When to Use

- Working with code in `pipecat/`
- Understanding how send_rtvi_message, on_push_frame, test_llm_messages_append work
- Modifying frameworks-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/processors/frameworks/rtvi.py` | RTVIBotLLMStartedMessage, RTVIBotLLMStoppedMessage, RTVIBotTTSStartedMessage, RTVIBotTTSStoppedMessage, RTVIBotTranscriptionMessage (+93) |
| `pipecat/src/pipecat/transports/base_input.py` | start_audio_in_streaming, enable_audio_in_stream_on_start |
| `pipecat/src/pipecat/frames/frames.py` | LLMMessagesAppendFrame, LLMConfigureOutputFrame |
| `pipecat/tests/test_context_aggregators_universal.py` | test_llm_messages_append |
| `pipecat/examples/foundational/26-gemini-live.py` | on_client_connected |
| `pipecat/examples/foundational/07m-interruptible-aws-strands.py` | on_client_connected |
| `core/services/agent_factory_service.py` | on_client_ready |
| `pipecat/src/pipecat/pipeline/task.py` | on_client_ready |
| `pipecat/src/pipecat/services/google/rtvi.py` | __init__ |

## Entry Points

Start here when exploring this area:

- **`send_rtvi_message`** (Function) — `pipecat/src/pipecat/processors/frameworks/rtvi.py:1068`
- **`on_push_frame`** (Function) — `pipecat/src/pipecat/processors/frameworks/rtvi.py:1082`
- **`test_llm_messages_append`** (Function) — `pipecat/tests/test_context_aggregators_universal.py:64`
- **`on_client_connected`** (Function) — `pipecat/examples/foundational/26-gemini-live.py:94`
- **`on_client_connected`** (Function) — `pipecat/examples/foundational/07m-interruptible-aws-strands.py:153`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `RTVIBotLLMStartedMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 673 |
| `RTVIBotLLMStoppedMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 680 |
| `RTVIBotTTSStartedMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 687 |
| `RTVIBotTTSStoppedMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 694 |
| `RTVIBotTranscriptionMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 733 |
| `RTVIBotLLMTextMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 744 |
| `RTVIUserTranscriptionMessageData` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 788 |
| `RTVIUserTranscriptionMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 800 |
| `RTVIUserLLMTextMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 811 |
| `RTVIUserStartedSpeakingMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 822 |
| `RTVIUserStoppedSpeakingMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 829 |
| `RTVIBotStartedSpeakingMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 836 |
| `RTVIBotStoppedSpeakingMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 843 |
| `RTVIMetricsMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 850 |
| `RTVIAudioLevelMessageData` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 872 |
| `RTVIUserAudioLevelMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 878 |
| `RTVIBotAudioLevelMessage` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 886 |
| `LLMMessagesAppendFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 793 |
| `LLMConfigureOutputFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 862 |
| `RTVIActionFrame` | Class | `pipecat/src/pipecat/processors/frameworks/rtvi.py` | 284 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `On_push_frame → OutputTransportMessageUrgentFrame` | cross_community | 5 |
| `On_push_frame → RTVIUserStartedSpeakingMessage` | intra_community | 3 |
| `On_push_frame → RTVIUserStoppedSpeakingMessage` | intra_community | 3 |
| `On_push_frame → RTVIBotStartedSpeakingMessage` | intra_community | 3 |
| `On_push_frame → RTVIBotStoppedSpeakingMessage` | intra_community | 3 |
| `On_push_frame → RTVIUserTranscriptionMessage` | intra_community | 3 |
| `On_push_frame → RTVIUserTranscriptionMessageData` | intra_community | 3 |
| `On_push_frame → Get_messages` | cross_community | 3 |
| `On_push_frame → RTVIUserLLMTextMessage` | intra_community | 3 |
| `On_push_frame → RTVITextMessageData` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 8 calls |
| Pipeline | 5 calls |
| Daily | 3 calls |
| Cartesia | 3 calls |
| Tests | 2 calls |
| Aggregators | 1 calls |
| Audio | 1 calls |
| Smallwebrtc | 1 calls |

## How to Explore

1. `gitnexus_context({name: "send_rtvi_message"})` — see callers and callees
2. `gitnexus_query({query: "frameworks"})` — find related execution flows
3. Read key files listed above for implementation details
