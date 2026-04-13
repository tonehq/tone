---
name: realtime
description: "Skill for the Realtime area of tone. 194 symbols across 26 files."
---

# Realtime

194 symbols | 26 files | Cohesion: 71%

## When to Use

- Working with code in `pipecat/`
- Understanding how process_frame, function_call_result_callback, push_interruption_task_frame_and_wait work
- Modifying realtime-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/openai/realtime/events.py` | ServerEvent, SessionCreatedEvent, SessionUpdatedEvent, ConversationCreated, ConversationItemAdded (+42) |
| `pipecat/src/pipecat/services/openai/realtime/llm.py` | _calculate_audio_duration_ms, _truncate_current_audio_response, _handle_evt_speech_started, stop, cancel (+30) |
| `pipecat/src/pipecat/services/grok/realtime/events.py` | ServerEvent, SessionUpdatedEvent, ConversationCreated, ConversationItemAdded, ConversationItemInputAudioTranscriptionCompleted (+29) |
| `pipecat/src/pipecat/services/grok/realtime/llm.py` | _truncate_current_audio_response, _handle_evt_speech_started, stop, cancel, _disconnect (+23) |
| `pipecat/src/pipecat/services/openai_realtime_beta/openai.py` | _calculate_audio_duration_ms, _truncate_current_audio_response, _handle_evt_speech_started, retrieve_conversation_item, __init__ (+1) |
| `pipecat/src/pipecat/services/llm_service.py` | function_call_result_callback, stop, cancel, _cancel_sequential_runner_task, __init__ |
| `pipecat/src/pipecat/services/ultravox/llm.py` | stop, cancel, _disconnect, __init__ |
| `pipecat/src/pipecat/turns/user_turn_processor.py` | _on_broadcast_frame, _on_user_turn_started, _on_user_turn_stopped |
| `pipecat/src/pipecat/processors/frame_processor.py` | push_interruption_task_frame_and_wait, broadcast_frame, broadcast_frame_instance |
| `pipecat/src/pipecat/services/deepgram/stt.py` | _start_metrics, _on_speech_started, _on_utterance_end |

## Entry Points

Start here when exploring this area:

- **`process_frame`** (Function) — `pipecat/tests/test_frame_processor.py:86`
- **`function_call_result_callback`** (Function) — `pipecat/src/pipecat/services/llm_service.py:601`
- **`push_interruption_task_frame_and_wait`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:750`
- **`broadcast_frame`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:773`
- **`broadcast_frame_instance`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:786`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ServerEvent` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 485 |
| `SessionCreatedEvent` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 499 |
| `SessionUpdatedEvent` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 511 |
| `ConversationCreated` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 523 |
| `ConversationItemAdded` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 535 |
| `ConversationItemDone` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 549 |
| `ConversationItemInputAudioTranscriptionDelta` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 563 |
| `ConversationItemInputAudioTranscriptionCompleted` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 579 |
| `ConversationItemInputAudioTranscriptionFailed` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 595 |
| `ConversationItemTruncated` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 611 |
| `ConversationItemDeleted` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 627 |
| `ConversationItemRetrieved` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 639 |
| `ResponseCreated` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 651 |
| `ResponseDone` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 663 |
| `ResponseOutputItemAdded` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 675 |
| `ResponseOutputItemDone` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 691 |
| `ResponseContentPartAdded` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 707 |
| `ResponseContentPartDone` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 727 |
| `ResponseTextDelta` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 747 |
| `ResponseTextDone` | Class | `pipecat/src/pipecat/services/openai/realtime/events.py` | 767 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Start → Get_time` | cross_community | 9 |
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Start → Get_time` | cross_community | 9 |
| `Start → FramePushed` | cross_community | 9 |
| `Process_frame → _run_handler` | cross_community | 8 |
| `Process_frame → Create_task` | cross_community | 8 |
| `Process_frame → Get_time` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cartesia | 41 calls |
| Tests | 14 calls |
| Daily | 13 calls |
| Services | 11 calls |
| Foundational | 6 calls |
| Processors | 5 calls |
| Smallwebrtc | 4 calls |
| Whisper | 4 calls |

## How to Explore

1. `gitnexus_context({name: "process_frame"})` — see callers and callees
2. `gitnexus_query({query: "realtime"})` — find related execution flows
3. Read key files listed above for implementation details
