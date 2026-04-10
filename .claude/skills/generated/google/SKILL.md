---
name: google
description: "Skill for the Google area of tone. 76 symbols across 31 files."
---

# Google

76 symbols | 31 files | Cohesion: 70%

## When to Use

- Working with code in `pipecat/`
- Understanding how get_tts_for_agent, set_voice, default work
- Modifying google-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/google/llm.py` | GoogleLLMContext, upgrade_to_google, set_messages, add_messages, from_standard_message (+13) |
| `pipecat/src/pipecat/services/google/stt.py` | __init__, language_to_google_stt_language, language_to_service_language, _reconnect_if_needed, set_language (+5) |
| `pipecat/src/pipecat/services/google/tts.py` | GoogleHttpTTSService, GoogleBaseTTSService, GeminiTTSService, InputParams, __init__ (+2) |
| `pipecat/src/pipecat/services/google/rtvi.py` | RTVISearchResponseMessageData, RTVIBotLLMSearchResponseMessage, on_push_frame, _handle_llm_search_response_frame, GoogleRTVIObserver (+1) |
| `pipecat/src/pipecat/services/azure/tts.py` | AzureBaseTTSService, AzureTTSService, AzureHttpTTSService |
| `pipecat/src/pipecat/services/google/llm_vertex.py` | InputParams, __init__, _get_credentials |
| `pipecat/src/pipecat/processors/aggregators/openai_llm_context.py` | default, get_messages_for_logging, create_wav_header |
| `pipecat/src/pipecat/services/google/image.py` | InputParams, __init__ |
| `pipecat/src/pipecat/processors/frameworks/rtvi.py` | RTVIObserver, create_rtvi_observer |
| `core/services/agent_factory_service.py` | get_tts_for_agent |

## Entry Points

Start here when exploring this area:

- **`get_tts_for_agent`** (Function) — `core/services/agent_factory_service.py:608`
- **`set_voice`** (Function) — `pipecat/src/pipecat/services/google/tts.py:1269`
- **`default`** (Function) — `pipecat/src/pipecat/processors/aggregators/openai_llm_context.py:48`
- **`language_to_google_stt_language`** (Function) — `pipecat/src/pipecat/services/google/stt.py:57`
- **`language_to_service_language`** (Function) — `pipecat/src/pipecat/services/google/stt.py:530`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `TTSService` | Class | `pipecat/src/pipecat/services/tts_service.py` | 60 |
| `XTTSService` | Class | `pipecat/src/pipecat/services/xtts/tts.py` | 70 |
| `SpeechmaticsTTSService` | Class | `pipecat/src/pipecat/services/speechmatics/tts.py` | 37 |
| `SarvamHttpTTSService` | Class | `pipecat/src/pipecat/services/sarvam/tts.py` | 70 |
| `PlayHTHttpTTSService` | Class | `pipecat/src/pipecat/services/playht/tts.py` | 448 |
| `RimeHttpTTSService` | Class | `pipecat/src/pipecat/services/rime/tts.py` | 470 |
| `OpenAITTSService` | Class | `pipecat/src/pipecat/services/openai/tts.py` | 50 |
| `NvidiaTTSService` | Class | `pipecat/src/pipecat/services/nvidia/tts.py` | 44 |
| `NeuphonicHttpTTSService` | Class | `pipecat/src/pipecat/services/neuphonic/tts.py` | 383 |
| `MyTTSService` | Class | `pipecat/src/pipecat/services/my_service/tts.py` | 3 |
| `MiniMaxHttpTTSService` | Class | `pipecat/src/pipecat/services/minimax/tts.py` | 87 |
| `KokoroTTSService` | Class | `pipecat/src/pipecat/services/kokoro/tts.py` | 89 |
| `GroqTTSService` | Class | `pipecat/src/pipecat/services/groq/tts.py` | 34 |
| `HathoraTTSService` | Class | `pipecat/src/pipecat/services/hathora/tts.py` | 47 |
| `GoogleHttpTTSService` | Class | `pipecat/src/pipecat/services/google/tts.py` | 476 |
| `GoogleBaseTTSService` | Class | `pipecat/src/pipecat/services/google/tts.py` | 786 |
| `GeminiTTSService` | Class | `pipecat/src/pipecat/services/google/tts.py` | 1111 |
| `CambTTSService` | Class | `pipecat/src/pipecat/services/camb/tts.py` | 135 |
| `DeepgramHttpTTSService` | Class | `pipecat/src/pipecat/services/deepgram/tts.py` | 320 |
| `AzureBaseTTSService` | Class | `pipecat/src/pipecat/services/azure/tts.py` | 67 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Get_tts_for_agent → _get_fernet` | cross_community | 4 |
| `Process_frame → Get_messages_for_logging` | cross_community | 3 |
| `Get_tts_for_agent → Query` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Services | 11 calls |
| Tests | 6 calls |
| Foundational | 5 calls |
| Test-cases | 2 calls |
| Speechmatics | 2 calls |
| Cartesia | 2 calls |
| Frameworks | 2 calls |
| Serializers | 1 calls |

## How to Explore

1. `gitnexus_context({name: "get_tts_for_agent"})` — see callers and callees
2. `gitnexus_query({query: "google"})` — find related execution flows
3. Read key files listed above for implementation details
