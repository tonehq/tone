---
name: smallwebrtc
description: "Skill for the Smallwebrtc area of tone. 108 symbols across 26 files."
---

# Smallwebrtc

108 symbols | 26 files | Cohesion: 75%

## When to Use

- Working with code in `pipecat/`
- Understanding how offer, smallwebrtc_sdp_munging, offer work
- Modifying smallwebrtc-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | SmallWebRTCCallbacks, __init__, SmallWebRTCClient, _convert_frame, read_video_frame (+29) |
| `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | SmallWebRTCConnection, _create_answer, initialize, renegotiate, delayed_task (+28) |
| `pipecat/src/pipecat/transports/smallwebrtc/request_handler.py` | _check_single_connection_constraints, handle_web_request, SmallWebRTCRequest, IceCandidate, SmallWebRTCPatchRequest (+1) |
| `pipecat/src/pipecat/services/speechmatics/stt.py` | __init__, _check_deprecated_args, _deprecation_warning |
| `pipecat/src/pipecat/runner/utils.py` | _smallwebrtc_sdp_cleanup_ice_candidates, _smallwebrtc_sdp_cleanup_fingerprints, smallwebrtc_sdp_munging |
| `pipecat/src/pipecat/runner/run.py` | offer, ice_candidate, proxy_request |
| `pipecat/src/pipecat/transports/websocket/server.py` | WebsocketServerCallbacks, __init__ |
| `pipecat/src/pipecat/services/soniox/stt.py` | SonioxInputParams, __init__ |
| `pipecat/src/pipecat/services/hathora/stt.py` | InputParams, __init__ |
| `pipecat/src/pipecat/services/deepgram/flux/stt.py` | InputParams, __init__ |

## Entry Points

Start here when exploring this area:

- **`offer`** (Function) — `pipecat/examples/foundational/04-transports-small-webrtc.py:139`
- **`smallwebrtc_sdp_munging`** (Function) — `pipecat/src/pipecat/runner/utils.py:404`
- **`offer`** (Function) — `pipecat/src/pipecat/runner/run.py:405`
- **`answer_call_to_whatsapp`** (Function) — `pipecat/src/pipecat/transports/whatsapp/api.py:251`
- **`handle_web_request`** (Function) — `pipecat/src/pipecat/transports/smallwebrtc/request_handler.py:158`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `WebsocketServerCallbacks` | Class | `pipecat/src/pipecat/transports/websocket/server.py` | 65 |
| `SmallWebRTCCallbacks` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 59 |
| `SmallWebRTCClient` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 198 |
| `SonioxInputParams` | Class | `pipecat/src/pipecat/services/soniox/stt.py` | 76 |
| `InputParams` | Class | `pipecat/src/pipecat/services/hathora/stt.py` | 34 |
| `InputParams` | Class | `pipecat/src/pipecat/services/deepgram/flux/stt.py` | 77 |
| `MockSmallWebRTCConnection` | Class | `core/test_case/test_agent_upsert.py` | 45 |
| `SmallWebRTCConnection` | Class | `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | 200 |
| `RawAudioTrack` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 73 |
| `RawVideoTrack` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 151 |
| `SmallWebRTCTrack` | Class | `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | 90 |
| `SmallWebRTCRequest` | Class | `pipecat/src/pipecat/transports/smallwebrtc/request_handler.py` | 24 |
| `IceCandidate` | Class | `pipecat/src/pipecat/transports/smallwebrtc/request_handler.py` | 50 |
| `SmallWebRTCPatchRequest` | Class | `pipecat/src/pipecat/transports/smallwebrtc/request_handler.py` | 65 |
| `Response` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 687 |
| `RenegotiateMessage` | Class | `pipecat/src/pipecat/transports/smallwebrtc/connection.py` | 58 |
| `offer` | Function | `pipecat/examples/foundational/04-transports-small-webrtc.py` | 139 |
| `smallwebrtc_sdp_munging` | Function | `pipecat/src/pipecat/runner/utils.py` | 404 |
| `offer` | Function | `pipecat/src/pipecat/runner/run.py` | 405 |
| `answer_call_to_whatsapp` | Function | `pipecat/src/pipecat/transports/whatsapp/api.py` | 251 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Proxy_request → _run_handler` | cross_community | 6 |
| `Proxy_request → Create_task` | cross_community | 6 |
| `Proxy_request → Stop` | cross_community | 6 |
| `Proxy_request → _cancel_monitoring_connecting_state` | cross_community | 6 |
| `Proxy_request → _setup_listeners` | cross_community | 6 |
| `Proxy_request → Force_transceivers_to_send_recv` | cross_community | 6 |
| `Proxy_request → _check_single_connection_constraints` | cross_community | 4 |
| `Proxy_request → Get` | cross_community | 4 |
| `Proxy_request → SmallWebRTCConnection` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Test-cases | 11 calls |
| Frames | 5 calls |
| Cartesia | 5 calls |
| Daily | 4 calls |
| Foundational | 3 calls |
| Runner | 2 calls |
| Tavus | 1 calls |
| Whatsapp | 1 calls |

## How to Explore

1. `gitnexus_context({name: "offer"})` — see callers and callees
2. `gitnexus_query({query: "smallwebrtc"})` — find related execution flows
3. Read key files listed above for implementation details
