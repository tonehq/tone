---
name: websocket
description: "Skill for the Websocket area of tone. 88 symbols across 16 files."
---

# Websocket

88 symbols | 16 files | Cohesion: 72%

## When to Use

- Working with code in `pipecat/`
- Understanding how input, input, input work
- Modifying websocket-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/transports/websocket/client.py` | WebsocketClientInputTransport, input, WebsocketClientOutputTransport, output, WebsocketClientParams (+18) |
| `pipecat/src/pipecat/transports/websocket/fastapi.py` | process_frame, send_message, write_audio_frame, _write_frame, _write_audio_sleep (+16) |
| `pipecat/src/pipecat/transports/websocket/server.py` | WebsocketServerInputTransport, input, WebsocketServerOutputTransport, output, stop (+9) |
| `pipecat/src/pipecat/transports/tavus/transport.py` | TavusInputTransport, input, TavusOutputTransport, output, TavusTransport |
| `pipecat/src/pipecat/transports/heygen/transport.py` | HeyGenInputTransport, input, HeyGenOutputTransport, output, HeyGenTransport |
| `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | SmallWebRTCInputTransport, input, SmallWebRTCOutputTransport, output |
| `pipecat/src/pipecat/transports/livekit/transport.py` | LiveKitInputTransport, input, LiveKitOutputTransport |
| `pipecat/src/pipecat/transports/daily/transport.py` | DailyInputTransport, DailyOutputTransport |
| `pipecat/src/pipecat/transports/local/tk.py` | TkInputTransport, input |
| `pipecat/src/pipecat/transports/local/audio.py` | LocalAudioInputTransport, LocalAudioOutputTransport |

## Entry Points

Start here when exploring this area:

- **`input`** (Function) — `pipecat/src/pipecat/transports/websocket/server.py:464`
- **`input`** (Function) — `pipecat/src/pipecat/transports/websocket/client.py:506`
- **`input`** (Function) — `pipecat/src/pipecat/transports/smallwebrtc/transport.py:910`
- **`input`** (Function) — `pipecat/src/pipecat/transports/tavus/transport.py:754`
- **`input`** (Function) — `pipecat/src/pipecat/transports/heygen/transport.py:355`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `BaseInputTransport` | Class | `pipecat/src/pipecat/transports/base_input.py` | 53 |
| `WebsocketServerInputTransport` | Class | `pipecat/src/pipecat/transports/websocket/server.py` | 81 |
| `WebsocketClientInputTransport` | Class | `pipecat/src/pipecat/transports/websocket/client.py` | 208 |
| `SmallWebRTCInputTransport` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 551 |
| `TavusInputTransport` | Class | `pipecat/src/pipecat/transports/tavus/transport.py` | 425 |
| `HeyGenInputTransport` | Class | `pipecat/src/pipecat/transports/heygen/transport.py` | 46 |
| `DailyInputTransport` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 1554 |
| `TkInputTransport` | Class | `pipecat/src/pipecat/transports/local/tk.py` | 59 |
| `LocalAudioInputTransport` | Class | `pipecat/src/pipecat/transports/local/audio.py` | 46 |
| `LiveKitInputTransport` | Class | `pipecat/src/pipecat/transports/livekit/transport.py` | 613 |
| `BaseOutputTransport` | Class | `pipecat/src/pipecat/transports/base_output.py` | 54 |
| `WebsocketServerOutputTransport` | Class | `pipecat/src/pipecat/transports/websocket/server.py` | 246 |
| `WebsocketClientOutputTransport` | Class | `pipecat/src/pipecat/transports/websocket/client.py` | 307 |
| `SmallWebRTCOutputTransport` | Class | `pipecat/src/pipecat/transports/smallwebrtc/transport.py` | 773 |
| `TavusOutputTransport` | Class | `pipecat/src/pipecat/transports/tavus/transport.py` | 528 |
| `HeyGenOutputTransport` | Class | `pipecat/src/pipecat/transports/heygen/transport.py` | 141 |
| `DailyOutputTransport` | Class | `pipecat/src/pipecat/transports/daily/transport.py` | 1862 |
| `LocalAudioOutputTransport` | Class | `pipecat/src/pipecat/transports/local/audio.py` | 116 |
| `LiveKitOutputTransport` | Class | `pipecat/src/pipecat/transports/livekit/transport.py` | 805 |
| `ProtobufFrameSerializer` | Class | `pipecat/src/pipecat/serializers/protobuf.py` | 38 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Transports | 4 calls |
| Tests | 4 calls |
| Processors | 3 calls |
| Frames | 3 calls |
| Realtime | 3 calls |
| Foundational | 3 calls |
| Cartesia | 2 calls |
| Smallwebrtc | 2 calls |

## How to Explore

1. `gitnexus_context({name: "input"})` — see callers and callees
2. `gitnexus_query({query: "websocket"})` — find related execution flows
3. Read key files listed above for implementation details
