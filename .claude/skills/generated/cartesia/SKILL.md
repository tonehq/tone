---
name: cartesia
description: "Skill for the Cartesia area of tone. 347 symbols across 72 files."
---

# Cartesia

347 symbols | 72 files | Cohesion: 69%

## When to Use

- Working with code in `pipecat/`
- Understanding how test_exponential_backoff_time, process_frame, version work
- Modifying cartesia-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/cartesia/tts.py` | GenerationConfig, _is_cjk_language, _process_word_timestamps_for_language, _build_msg, start (+12) |
| `pipecat/src/pipecat/services/openai_realtime_beta/openai.py` | CurrentAudioResponse, _is_modality_enabled, start, stop, cancel (+10) |
| `pipecat/src/pipecat/services/elevenlabs/tts.py` | calculate_word_times, set_model, _update_settings, stop, cancel (+10) |
| `pipecat/src/pipecat/services/sarvam/tts.py` | start, run_tts, stop, cancel, _connect (+9) |
| `pipecat/src/pipecat/services/rime/tts.py` | _build_msg, _build_clear_msg, _build_eos_msg, start, _connect (+9) |
| `pipecat/src/pipecat/services/cartesia/stt.py` | start, run_stt, _connect, _connect_websocket, _get_websocket (+9) |
| `pipecat/src/pipecat/services/resembleai/tts.py` | _build_msg, start, stop, cancel, _connect (+8) |
| `pipecat/src/pipecat/services/grok/realtime/llm.py` | CurrentAudioResponse, _get_configured_sample_rate, _get_output_sample_rate, _handle_interruption, _calculate_audio_duration_ms (+7) |
| `pipecat/src/pipecat/services/tts_service.py` | _stream_audio_frames_from_iterator, start_word_timestamps, reset_word_timestamps, add_word_timestamps, _create_words_task (+6) |
| `pipecat/src/pipecat/services/playht/tts.py` | start, stop, cancel, _connect, _disconnect (+6) |

## Entry Points

Start here when exploring this area:

- **`test_exponential_backoff_time`** (Function) — `pipecat/tests/test_utils_network.py:12`
- **`process_frame`** (Function) — `pipecat/tests/test_pipeline.py:475`
- **`version`** (Function) — `pipecat/src/pipecat/__init__.py:22`
- **`on_voice_tag`** (Function) — `pipecat/examples/foundational/35-pattern-pair-voice-switching.py:121`
- **`load_conversation`** (Function) — `pipecat/examples/foundational/20b-persistent-context-openai-realtime-beta.py:83`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `TTSAudioRawFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 275 |
| `ErrorFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1050 |
| `FatalErrorFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1074 |
| `TTSStartedFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1903 |
| `TTSStoppedFrame` | Class | `pipecat/src/pipecat/frames/frames.py` | 1917 |
| `CurrentAudioResponse` | Class | `pipecat/src/pipecat/services/openai_realtime_beta/openai.py` | 77 |
| `GenerationConfig` | Class | `pipecat/src/pipecat/services/cartesia/tts.py` | 51 |
| `CurrentAudioResponse` | Class | `pipecat/src/pipecat/services/openai/realtime/llm.py` | 76 |
| `CurrentAudioResponse` | Class | `pipecat/src/pipecat/services/grok/realtime/llm.py` | 71 |
| `ClientEvent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 326 |
| `SessionUpdateEvent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 336 |
| `InputAudioBufferAppendEvent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 348 |
| `InputAudioBufferClearEvent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 372 |
| `ResponseCancelEvent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 408 |
| `test_exponential_backoff_time` | Function | `pipecat/tests/test_utils_network.py` | 12 |
| `process_frame` | Function | `pipecat/tests/test_pipeline.py` | 475 |
| `version` | Function | `pipecat/src/pipecat/__init__.py` | 22 |
| `on_voice_tag` | Function | `pipecat/examples/foundational/35-pattern-pair-voice-switching.py` | 121 |
| `load_conversation` | Function | `pipecat/examples/foundational/20b-persistent-context-openai-realtime-beta.py` | 83 |
| `seconds_to_nanoseconds` | Function | `pipecat/src/pipecat/utils/time.py` | 25 |

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
| `Process_frame → Create_task` | cross_community | 8 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Daily | 35 calls |
| Services | 17 calls |
| Tests | 15 calls |
| Pipeline | 13 calls |
| Realtime | 12 calls |
| Processors | 9 calls |
| Foundational | 7 calls |
| Test-cases | 5 calls |

## How to Explore

1. `gitnexus_context({name: "test_exponential_backoff_time"})` — see callers and callees
2. `gitnexus_query({query: "cartesia"})` — find related execution flows
3. Read key files listed above for implementation details
