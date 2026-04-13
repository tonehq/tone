---
name: frames
description: "Skill for the Frames area of tone. 94 symbols across 34 files."
---

# Frames

94 symbols | 34 files | Cohesion: 59%

## When to Use

- Working with code in `pipecat/`
- Understanding how audio_transformer, push_audio_frame, read_next_audio_frame work
- Modifying frames-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/frames/frames.py` | AudioRawFrame, InputAudioRawFrame, UserAudioRawFrame, DataFrame, SpriteFrame (+38) |
| `pipecat/src/pipecat/transports/daily/transport.py` | read_next_audio_frame, _on_participant_audio_data, _audio_in_task_handler, _on_participant_video_frame, DailyUpdateRemoteParticipantsFrame (+2) |
| `pipecat/src/pipecat/transports/livekit/transport.py` | get_next_audio_frame, _audio_in_task_handler, _convert_livekit_audio_to_pipecat, get_next_video_frame, _video_in_task_handler (+1) |
| `pipecat/examples/foundational/45-before-and-after-events.py` | CustomBeforeProcessFrame, CustomAfterPushFrame, on_client_connected |
| `pipecat/src/pipecat/transports/base_input.py` | push_audio_frame, push_video_frame |
| `pipecat/src/pipecat/services/aws/nova_sonic/context.py` | AWSNovaSonicMessagesUpdateFrame, process_frame |
| `pipecat/src/pipecat/pipeline/service_switcher.py` | process_frame, ServiceSwitcherFilterFrame |
| `pipecat/src/pipecat/utils/utils.py` | obj_id, obj_count |
| `pipecat/src/pipecat/utils/time.py` | nanoseconds_to_seconds, nanoseconds_to_str |
| `pipecat/tests/test_producer_consumer.py` | audio_transformer |

## Entry Points

Start here when exploring this area:

- **`audio_transformer`** (Function) — `pipecat/tests/test_producer_consumer.py:80`
- **`push_audio_frame`** (Function) — `pipecat/src/pipecat/transports/base_input.py:288`
- **`read_next_audio_frame`** (Function) — `pipecat/src/pipecat/transports/daily/transport.py:583`
- **`get_next_audio_frame`** (Function) — `pipecat/src/pipecat/transports/livekit/transport.py:587`
- **`on_client_connected`** (Function) — `pipecat/examples/foundational/45-before-and-after-events.py:131`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `AudioRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 203 |
| `InputAudioRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1498 |
| `UserAudioRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1544 |
| `TestInterruptibleFrame` | Class | `pipecat/tests/test_frame_processor.py` | 129 |
| `CustomBeforeProcessFrame` | Class | `pipecat/examples/foundational/45-before-and-after-events.py` | 39 |
| `CustomAfterPushFrame` | Class | `pipecat/examples/foundational/45-before-and-after-events.py` | 44 |
| `MonthFrame` | Class | `pipecat/examples/foundational/05-sync-speech-and-image.py` | 39 |
| `DataFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 158 |
| `SpriteFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 315 |
| `LLMSetToolsFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 825 |
| `LLMSetToolChoiceFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 840 |
| `LLMEnablePromptCachingFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 851 |
| `RealtimeMessagesUpdateFrame` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/frames.py` | 18 |
| `RealtimeMessagesUpdateFrame` | Class | `pipecat/src/pipecat/services/openai/realtime/frames.py` | 39 |
| `AWSNovaSonicMessagesUpdateFrame` | Class | `pipecat/src/pipecat/services/aws/nova_sonic/context.py` | 327 |
| `ImageRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 223 |
| `InputImageRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1516 |
| `UserImageRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1561 |
| `ServiceSwitcherFilterFrame` | Class | `pipecat/src/pipecat/pipeline/service_switcher.py` | 162 |
| `ControlFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 170 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → InterruptionTaskFrame` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Foundational | 16 calls |
| Cartesia | 4 calls |
| Pipeline | 3 calls |
| Test-cases | 3 calls |
| Daily | 2 calls |
| Smallwebrtc | 1 calls |
| Serializers | 1 calls |
| Tests | 1 calls |

## How to Explore

1. `gitnexus_context({name: "audio_transformer"})` — see callers and callees
2. `gitnexus_query({query: "frames"})` — find related execution flows
3. Read key files listed above for implementation details
