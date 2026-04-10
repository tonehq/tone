---
name: openai-realtime-beta
description: "Skill for the Openai_realtime_beta area of tone. 102 symbols across 15 files."
---

# Openai_realtime_beta

102 symbols | 15 files | Cohesion: 75%

## When to Use

- Working with code in `pipecat/`
- Understanding how upgrade_to_realtime, upgrade_to_realtime, upgrade_to_nova_sonic work
- Modifying openai_realtime_beta-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | ServerEvent, SessionCreatedEvent, SessionUpdatedEvent, ConversationCreated, ConversationItemCreated (+37) |
| `pipecat/src/pipecat/services/openai_realtime_beta/openai.py` | _receive_task_handler, _handle_evt_audio_done, _handle_evt_conversation_item_created, _handle_conversation_item_retrieved, _handle_evt_text_delta (+17) |
| `pipecat/src/pipecat/services/openai_realtime_beta/context.py` | __init__, __setup_local, upgrade_to_realtime, handle_function_call_result, OpenAIRealtimeLLMContext (+3) |
| `pipecat/src/pipecat/services/openai/realtime/context.py` | __init__, __setup_local, upgrade_to_realtime, handle_function_call_result, OpenAIRealtimeLLMContext (+2) |
| `pipecat/src/pipecat/services/aws/nova_sonic/context.py` | __init__, __setup_local, upgrade_to_nova_sonic, handle_function_call_result, AWSNovaSonicLLMContext (+2) |
| `pipecat/src/pipecat/services/openai/llm.py` | handle_function_call_result, OpenAIUserContextAggregator, OpenAIAssistantContextAggregator |
| `pipecat/src/pipecat/services/google/gemini_live/llm.py` | GeminiLiveContext, GeminiLiveUserContextAggregator, GeminiLiveAssistantContextAggregator |
| `pipecat/src/pipecat/processors/aggregators/openai_llm_context.py` | __init__, OpenAILLMContext |
| `pipecat/src/pipecat/services/google/llm.py` | GoogleUserContextAggregator, GoogleAssistantContextAggregator |
| `pipecat/src/pipecat/services/openai_realtime_beta/frames.py` | RealtimeFunctionCallResultFrame |

## Entry Points

Start here when exploring this area:

- **`upgrade_to_realtime`** (Function) — `pipecat/src/pipecat/services/openai_realtime_beta/context.py:60`
- **`upgrade_to_realtime`** (Function) — `pipecat/src/pipecat/services/openai/realtime/context.py:142`
- **`upgrade_to_nova_sonic`** (Function) — `pipecat/src/pipecat/services/aws/nova_sonic/context.py:181`
- **`handle_function_call_result`** (Function) — `pipecat/src/pipecat/services/openai_realtime_beta/context.py:258`
- **`handle_function_call_result`** (Function) — `pipecat/src/pipecat/services/openai/llm.py:187`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ServerEvent` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 388 |
| `SessionCreatedEvent` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 402 |
| `SessionUpdatedEvent` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 414 |
| `ConversationCreated` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 426 |
| `ConversationItemCreated` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 438 |
| `ConversationItemInputAudioTranscriptionDelta` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 452 |
| `ConversationItemInputAudioTranscriptionCompleted` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 468 |
| `ConversationItemInputAudioTranscriptionFailed` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 484 |
| `ConversationItemTruncated` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 500 |
| `ConversationItemDeleted` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 516 |
| `ConversationItemRetrieved` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 528 |
| `ResponseCreated` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 540 |
| `ResponseDone` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 552 |
| `ResponseOutputItemAdded` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 564 |
| `ResponseOutputItemDone` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 580 |
| `ResponseContentPartAdded` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 596 |
| `ResponseContentPartDone` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 616 |
| `ResponseTextDelta` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 636 |
| `ResponseTextDone` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 656 |
| `ResponseAudioTranscriptDelta` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/events.py` | 676 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → Get_time` | cross_community | 5 |
| `Process_frame → FrameProcessed` | cross_community | 5 |
| `Process_frame → On_process_frame` | cross_community | 5 |
| `Process_frame → Start` | cross_community | 5 |
| `Process_frame → Stop` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 5 |
| `Process_frame → Cancel_task` | cross_community | 4 |
| `Process_frame → Create_task` | cross_community | 4 |
| `Process_frame → SessionUpdateEvent` | cross_community | 4 |
| `Process_frame → __setup_local` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cartesia | 17 calls |
| Tests | 8 calls |
| Realtime | 7 calls |
| Whisper | 3 calls |
| Daily | 3 calls |
| Foundational | 3 calls |
| Services | 2 calls |
| Perplexity | 2 calls |

## How to Explore

1. `gitnexus_context({name: "upgrade_to_realtime"})` — see callers and callees
2. `gitnexus_query({query: "openai_realtime_beta"})` — find related execution flows
3. Read key files listed above for implementation details
