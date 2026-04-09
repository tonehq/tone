---
name: services
description: "Skill for the Services area of tone. 447 symbols across 133 files."
---

# Services

447 symbols | 133 files | Cohesion: 63%

## When to Use

- Working with code in `pipecat/`
- Understanding how migrate_existing_data, load_seed_data, main work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `pipecat/src/pipecat/services/tts_service.py` | __init__, set_voice, update_setting, push_frame, _create_audio_context_task (+19) |
| `pipecat/src/pipecat/services/stt_service.py` | request_finalize, process_frame, _handle_speech_control_params, _reset_stt_ttfb_state, _handle_vad_user_started_speaking (+16) |
| `core/services/auth_service.py` | ensure_default_organization, verify_user_email, get_all_invited_users_for_organization, cancel_invitation, remove_user_from_organization (+14) |
| `ee/services/auth_service.py` | create_slug_from_name, verify_user_email, check_organization_exists, create_organization, remove_user_from_organization (+12) |
| `core/services/agent_factory_service.py` | AgentFactoryService, _get_agent_config, get_agent_bot_data, run_bot_for_agent, _get_telephony_creds_bulk (+10) |
| `pipecat/src/pipecat/adapters/services/gemini_adapter.py` | get_messages_for_logging, ConvertedMessages, MessageConversionParams, _from_universal_context_messages, _merge_parallel_tool_calls_for_thinking (+9) |
| `core/services/subprocess_bot_manager.py` | _proxy_websocket, telephony_to_subprocess, subprocess_to_telephony, _drain_stdout, launch (+7) |
| `pipecat/src/pipecat/services/llm_service.py` | FunctionCallParams, _run_parallel_function_calls, _call_start_function, _run_function_call, FunctionCallRunnerItem (+4) |
| `pipecat/src/pipecat/services/mcp_service.py` | _convert_mcp_schema_to_pipecat, _sse_list_tools, _stdio_list_tools, _streamable_http_list_tools, _list_tools_helper (+4) |
| `core/services/channel_phone_numbers_service.py` | delete_channel_phone_number, get_twilio_phone_numbers, get_phone_number_list_to_buy, buy_phone_number, upsert_channel_phone_number (+3) |

## Entry Points

Start here when exploring this area:

- **`migrate_existing_data`** (Function) — `scripts/migrate_existing_data.py:27`
- **`load_seed_data`** (Function) — `dev/reseed_models_voices.py:32`
- **`main`** (Function) — `dev/reseed_models_voices.py:38`
- **`create_slug_from_name`** (Function) — `ee/services/auth_service.py:25`
- **`verify_user_email`** (Function) — `ee/services/auth_service.py:39`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Voice` | Class | `core/models/voice.py` | 6 |
| `ServiceProvider` | Class | `core/models/service_provider.py` | 7 |
| `PasswordReset` | Class | `core/models/password_reset.py` | 5 |
| `Organization` | Class | `core/models/organization.py` | 9 |
| `Model` | Class | `core/models/models.py` | 9 |
| `TimestampModel` | Class | `core/models/base.py` | 7 |
| `InputParams` | Class | `pipecat/src/pipecat/services/speechmatics/tts.py` | 46 |
| `InputParams` | Class | `pipecat/src/pipecat/services/nvidia/tts.py` | 52 |
| `InputParams` | Class | `pipecat/src/pipecat/services/hume/tts.py` | 63 |
| `InputParams` | Class | `pipecat/src/pipecat/services/groq/tts.py` | 42 |
| `InputParams` | Class | `pipecat/src/pipecat/services/hathora/tts.py` | 53 |
| `InputParams` | Class | `pipecat/src/pipecat/services/gradium/tts.py` | 42 |
| `InputParams` | Class | `pipecat/src/pipecat/services/fish/tts.py` | 55 |
| `InputParams` | Class | `pipecat/src/pipecat/services/camb/tts.py` | 158 |
| `ConvertedMessages` | Class | `pipecat/src/pipecat/adapters/services/grok_realtime_adapter.py` | 93 |
| `ItemContent` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 232 |
| `ConversationItem` | Class | `pipecat/src/pipecat/services/grok/realtime/events.py` | 248 |
| `MockTransport` | Class | `test_minimal.py` | 33 |
| `RunnerArgs` | Class | `test_minimal.py` | 46 |
| `AgentFactoryService` | Class | `core/services/agent_factory_service.py` | 24 |

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
| `Start → _check_started` | cross_community | 8 |
| `Start → _check_started` | cross_community | 8 |
| `Telephony_websocket → Query` | cross_community | 6 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Test-cases | 50 calls |
| Cartesia | 19 calls |
| Foundational | 17 calls |
| Tests | 11 calls |
| V1 | 8 calls |
| Pipeline | 5 calls |
| Database | 4 calls |
| Whisper | 4 calls |

## How to Explore

1. `gitnexus_context({name: "migrate_existing_data"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
