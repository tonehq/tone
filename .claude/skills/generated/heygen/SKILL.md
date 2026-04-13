---
name: heygen
description: "Skill for the Heygen area of tone. 70 symbols across 7 files."
---

# Heygen

70 symbols | 7 files | Cohesion: 84%

## When to Use

- Working with code in `pipecat/`
- Understanding how start_capturing_audio, capture_participant_audio, capture_participant_video work
- Modifying heygen-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/heygen/client.py` | capture_participant_audio, capture_participant_video, _process_audio_frames, _process_video_frames, on_track_subscribed (+26) |
| `pipecat/src/pipecat/services/heygen/video.py` | _on_participant_connected, _handle_user_started_speaking, stop, cancel, _end_conversation (+5) |
| `pipecat/src/pipecat/services/heygen/api_liveavatar.py` | LiveAvatarApiError, _request, create_session_token, start_session, stop_session (+4) |
| `pipecat/src/pipecat/transports/heygen/transport.py` | start_capturing_audio, _on_participant_connected, _on_client_connected, push_frame, process_frame (+3) |
| `pipecat/src/pipecat/services/heygen/api_interactive_avatar.py` | HeygenApiError, _request, new_session, _start_session, close_session (+3) |
| `pipecat/src/pipecat/services/heygen/base_api.py` | StandardSessionResponse, BaseAvatarApi |
| `pipecat/src/pipecat/services/ai_service.py` | cancel, _cancel |

## Entry Points

Start here when exploring this area:

- **`start_capturing_audio`** (Function) — `pipecat/src/pipecat/transports/heygen/transport.py:119`
- **`capture_participant_audio`** (Function) — `pipecat/src/pipecat/services/heygen/client.py:444`
- **`capture_participant_video`** (Function) — `pipecat/src/pipecat/services/heygen/client.py:475`
- **`on_track_subscribed`** (Function) — `pipecat/src/pipecat/services/heygen/client.py:579`
- **`push_frame`** (Function) — `pipecat/src/pipecat/transports/heygen/transport.py:217`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `StandardSessionResponse` | Class | `pipecat/src/pipecat/services/heygen/base_api.py` | 17 |
| `HeygenApiError` | Class | `pipecat/src/pipecat/services/heygen/api_interactive_avatar.py` | 124 |
| `LiveAvatarApiError` | Class | `pipecat/src/pipecat/services/heygen/api_liveavatar.py` | 123 |
| `BaseAvatarApi` | Class | `pipecat/src/pipecat/services/heygen/base_api.py` | 41 |
| `LiveAvatarNewSessionRequest` | Class | `pipecat/src/pipecat/services/heygen/api_liveavatar.py` | 48 |
| `LiveAvatarApi` | Class | `pipecat/src/pipecat/services/heygen/api_liveavatar.py` | 139 |
| `NewSessionRequest` | Class | `pipecat/src/pipecat/services/heygen/api_interactive_avatar.py` | 80 |
| `HeyGenApi` | Class | `pipecat/src/pipecat/services/heygen/api_interactive_avatar.py` | 140 |
| `HeyGenParams` | Class | `pipecat/src/pipecat/transports/heygen/transport.py` | 273 |
| `HeyGenCallbacks` | Class | `pipecat/src/pipecat/services/heygen/client.py` | 60 |
| `HeyGenClient` | Class | `pipecat/src/pipecat/services/heygen/client.py` | 72 |
| `start_capturing_audio` | Function | `pipecat/src/pipecat/transports/heygen/transport.py` | 119 |
| `capture_participant_audio` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 444 |
| `capture_participant_video` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 475 |
| `on_track_subscribed` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 579 |
| `push_frame` | Function | `pipecat/src/pipecat/transports/heygen/transport.py` | 217 |
| `process_frame` | Function | `pipecat/src/pipecat/transports/heygen/transport.py` | 236 |
| `interrupt` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 327 |
| `start_agent_listening` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 342 |
| `stop_agent_listening` | Function | `pipecat/src/pipecat/services/heygen/client.py` | 355 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Process_frame → Cancel` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 5 |
| `Process_frame → Cancel` | cross_community | 4 |
| `Process_frame → _reset_audio_timing` | cross_community | 4 |
| `Process_frame → _ws_send` | cross_community | 4 |
| `Process_frame → Cancel_task` | cross_community | 4 |
| `Process_frame → Create_task` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Tavus | 2 calls |
| Pipeline | 2 calls |
| Frames | 2 calls |
| Transports | 1 calls |
| Smallwebrtc | 1 calls |
| Daily | 1 calls |
| Quickstart | 1 calls |
| Cartesia | 1 calls |

## How to Explore

1. `gitnexus_context({name: "start_capturing_audio"})` — see callers and callees
2. `gitnexus_query({query: "heygen"})` — find related execution flows
3. Read key files listed above for implementation details
