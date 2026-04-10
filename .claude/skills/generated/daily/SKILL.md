---
name: daily
description: "Skill for the Daily area of tone. 183 symbols across 26 files."
---

# Daily

183 symbols | 26 files | Cohesion: 71%

## When to Use

- Working with code in `pipecat/`
- Understanding how push_error_frame, push_frame, broadcast_frame work
- Modifying daily-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/transports/daily/transport.py` | _on_active_speaker_changed, _on_left, _on_call_state_updated, _on_client_connected, _on_client_disconnected (+97) |
| `pipecat/src/pipecat/transports/daily/utils.py` | DailyRoomSipParams, DailyRoomProperties, DailyRoomParams, DailyMeetingTokenProperties, DailyMeetingTokenParams (+9) |
| `pipecat/src/pipecat/transports/livekit/transport.py` | _on_track_subscribed_wrapper, _on_connected, _on_disconnected, _on_before_disconnect, _on_participant_connected (+7) |
| `pipecat/scripts/daily/test_tavus_transport.py` | completion_callback, update_subscriptions, capture_participant_audio, send_audio, on_participant_joined (+5) |
| `pipecat/src/pipecat/transports/websocket/server.py` | set_client_connection, _on_client_connected, _on_client_disconnected, _on_session_timeout, _on_websocket_ready |
| `pipecat/src/pipecat/turns/user_turn_controller.py` | _on_push_frame, _on_broadcast_frame, _on_user_turn_started, _trigger_user_turn_start |
| `pipecat/src/pipecat/transports/websocket/fastapi.py` | _on_client_connected, _on_client_disconnected, _on_session_timeout |
| `pipecat/src/pipecat/audio/vad/vad_controller.py` | _handle_audio, _handle_vad, _maybe_speech_activity |
| `pipecat/src/pipecat/utils/base_object.py` | _call_event_handler, _run_handler |
| `pipecat/src/pipecat/turns/user_turn_processor.py` | _on_user_turn_stop_timeout, _on_user_turn_idle |

## Entry Points

Start here when exploring this area:

- **`push_error_frame`** (Function) — `pipecat/src/pipecat/processors/frame_processor.py:707`
- **`push_frame`** (Function) — `pipecat/src/pipecat/turns/user_start/base_user_turn_start_strategy.py:113`
- **`broadcast_frame`** (Function) — `pipecat/src/pipecat/turns/user_start/base_user_turn_start_strategy.py:122`
- **`set_client_connection`** (Function) — `pipecat/src/pipecat/transports/websocket/server.py:279`
- **`on_track`** (Function) — `pipecat/src/pipecat/transports/smallwebrtc/connection.py:339`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `DailyAudioTrack` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 408 |
| `DailyRoomConfig` | Class | `pipecat/src/pipecat/runner/daily.py` | 55 |
| `DailyRoomSipParams` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 19 |
| `DailyRoomProperties` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 79 |
| `DailyRoomParams` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 133 |
| `DailyMeetingTokenProperties` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 169 |
| `DailyMeetingTokenParams` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 210 |
| `DailyRESTHelper` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 223 |
| `DailyRoomObject` | Class | `pipecat/src/pipecat/transports/daily/utils.py` | 147 |
| `DailyOutputTransportMessageFrame` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 75 |
| `DailyOutputTransportMessageUrgentFrame` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 86 |
| `DailyTransportMessageFrame` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 97 |
| `DailyTransportMessageUrgentFrame` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 123 |
| `push_error_frame` | Function | `pipecat/src/pipecat/processors/frame_processor.py` | 707 |
| `push_frame` | Function | `pipecat/src/pipecat/turns/user_start/base_user_turn_start_strategy.py` | 113 |
| `broadcast_frame` | Function | `pipecat/src/pipecat/turns/user_start/base_user_turn_start_strategy.py` | 122 |
| `set_client_connection` | Function | `pipecat/src/pipecat/transports/websocket/server.py` | 279 |
| `on_track` | Function | `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | 339 |
| `on_ended` | Function | `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | 344 |
| `analyze_audio` | Function | `pipecat/src/pipecat/audio/vad/vad_analyzer.py` | 173 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → _run_handler` | cross_community | 10 |
| `Process_frame → Create_task` | cross_community | 10 |
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Start → _run_handler` | cross_community | 9 |
| `Start → Create_task` | cross_community | 9 |
| `Process_frame → _run_handler` | cross_community | 8 |
| `Process_frame → Create_task` | cross_community | 8 |
| `Run_tts → _run_handler` | cross_community | 8 |
| `Run_tts → Create_task` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cartesia | 5 calls |
| Pipeline | 3 calls |
| Runner | 3 calls |
| Foundational | 2 calls |
| Test-cases | 2 calls |
| Tests | 2 calls |
| Evals | 1 calls |
| Frames | 1 calls |

## How to Explore

1. `gitnexus_context({name: "push_error_frame"})` — see callers and callees
2. `gitnexus_query({query: "daily"})` — find related execution flows
3. Read key files listed above for implementation details
